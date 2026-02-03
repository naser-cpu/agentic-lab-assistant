"""Executor module that runs the plan and produces results."""

import logging
import os
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from api.schemas import AgentPlan, AgentResult, ToolCall
from worker.agent.tools import query_incidents, search_docs

logger = logging.getLogger(__name__)


def _synthesize_deterministic(
    text: str,
    doc_results: list[dict],
    incident_results: list[dict],
) -> AgentResult:
    """
    Synthesize results using deterministic logic.
    This is the default stub that doesn't require an LLM.
    """
    summary_parts = []
    steps = []
    sources = []

    # Process documentation results
    if doc_results:
        summary_parts.append("Based on the documentation:")
        for doc in doc_results[:3]:
            summary_parts.append(f"- {doc['title']}: {doc['snippet'][:100]}...")
            steps.extend(doc.get("key_points", [])[:2])
            sources.append(doc["filename"])

    # Process incident results
    if incident_results:
        summary_parts.append("\nRelevant past incidents:")
        for inc in incident_results[:3]:
            summary_parts.append(f"- {inc['id']}: {inc['title']}")
            if inc.get("resolution"):
                steps.append(f"From {inc['id']}: {inc['resolution'][:100]}")
            sources.append(inc["id"])

    # Default fallback if no results
    if not summary_parts:
        summary_parts = ["No specific documentation or incidents found for this query."]
        steps = ["Please provide more details about your request."]

    summary = " ".join(summary_parts) if summary_parts else "Unable to find relevant information."

    # Ensure we have at least one step
    if not steps:
        steps = ["Review the sources listed below for more details."]

    return AgentResult(
        summary=summary,
        steps=steps[:5],  # Limit to 5 steps
        sources=list(set(sources)),  # Deduplicate sources
    )


def _synthesize_llm(
    text: str,
    doc_results: list[dict],
    incident_results: list[dict],
) -> AgentResult:
    """
    Synthesize results using an LLM.
    Requires LLM_API_KEY environment variable.
    """
    api_key = os.getenv("LLM_API_KEY")
    model = os.getenv("LLM_MODEL", "gpt-4")

    if not api_key:
        logger.warning("LLM_API_KEY not set, falling back to deterministic synthesis")
        return _synthesize_deterministic(text, doc_results, incident_results)

    context = f"""User question: {text}

Documentation results:
{doc_results}

Incident results:
{incident_results}

Based on this information, provide:
1. A clear summary answering the user's question
2. Actionable steps they can take
3. List the sources (filenames and incident IDs) you used

Respond with JSON:
{{
  "summary": "...",
  "steps": ["step1", "step2", ...],
  "sources": ["filename.md", "INC-XXX", ...]
}}"""

    def _extract_output_text(payload: dict) -> str:
        for item in payload.get("output", []):
            if item.get("type") == "message":
                for part in item.get("content", []):
                    if part.get("type") == "output_text":
                        return part.get("text", "")
        output_text = payload.get("output_text")
        return output_text if isinstance(output_text, str) else ""

    try:
        response = httpx.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "input": context,
                "temperature": 0.3,
                "text": {"format": {"type": "json_object"}},
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        content = _extract_output_text(data)
        if not content:
            raise ValueError("Empty response content from LLM synthesis")
        import json

        result_data = json.loads(content)
        return AgentResult(**result_data)
    except Exception as e:
        logger.error(f"LLM synthesis failed: {e}, falling back to deterministic")
        return _synthesize_deterministic(text, doc_results, incident_results)


def execute_plan(
    text: str,
    plan: AgentPlan,
    db: Session,
) -> tuple[AgentResult, list[ToolCall]]:
    """
    Execute the plan and produce a result.

    Args:
        text: Original request text
        plan: The execution plan from the planner
        db: Database session for incident queries

    Returns:
        Tuple of (AgentResult, list of ToolCall records)
    """
    tool_calls = []
    doc_results = []
    incident_results = []

    # Execute each step in the plan
    for step in plan.steps:
        if step.tool == "search_docs" and step.tool_input:
            logger.info(f"Executing search_docs: {step.tool_input}")
            results = search_docs(step.tool_input)
            doc_results.extend(results)
            tool_calls.append(
                ToolCall(
                    tool="search_docs",
                    input=step.tool_input,
                    output=results,
                    timestamp=datetime.utcnow(),
                )
            )

        elif step.tool == "query_incidents" and step.tool_input:
            logger.info(f"Executing query_incidents: {step.tool_input}")
            results = query_incidents(step.tool_input, db)
            incident_results.extend(results)
            tool_calls.append(
                ToolCall(
                    tool="query_incidents",
                    input=step.tool_input,
                    output=results,
                    timestamp=datetime.utcnow(),
                )
            )

        elif step.tool is None:
            # Synthesis step - no tool call needed
            logger.info("Synthesis step - combining results")

    # Synthesize final result
    use_llm = os.getenv("USE_REAL_LLM", "false").lower() == "true"

    if use_llm:
        result = _synthesize_llm(text, doc_results, incident_results)
    else:
        result = _synthesize_deterministic(text, doc_results, incident_results)

    return result, tool_calls
