"""Pydantic schemas for request/response validation."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Priority(str, Enum):
    """Request priority levels."""

    NORMAL = "normal"
    HIGH = "high"


class RequestStatus(str, Enum):
    """Request processing status."""

    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


# Request schemas
class LabRequestCreate(BaseModel):
    """Schema for creating a new lab request."""

    text: str = Field(..., min_length=1, max_length=10000, description="The request text")
    priority: Priority = Field(default=Priority.NORMAL, description="Request priority")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "text": "How do I handle a database connection timeout?",
                    "priority": "high",
                }
            ]
        }
    }


class LabRequestResponse(BaseModel):
    """Schema for request creation response."""

    request_id: str = Field(..., description="Unique request identifier")
    status: RequestStatus = Field(..., description="Current request status")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "request_id": "550e8400-e29b-41d4-a716-446655440000",
                    "status": "queued",
                }
            ]
        }
    }


class AgentResult(BaseModel):
    """Schema for the agent's final result."""

    summary: str = Field(..., description="Summary of the answer")
    steps: list[str] = Field(default_factory=list, description="Steps taken or recommended")
    sources: list[str] = Field(
        default_factory=list, description="Source citations (file names or incident IDs)"
    )


class LabRequestStatus(BaseModel):
    """Schema for request status response."""

    request_id: str = Field(..., description="Unique request identifier")
    status: RequestStatus = Field(..., description="Current request status")
    result: AgentResult | None = Field(None, description="Agent result when done")
    error: str | None = Field(None, description="Error message if failed")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "request_id": "550e8400-e29b-41d4-a716-446655440000",
                    "status": "done",
                    "result": {
                        "summary": "To handle database connection timeouts...",
                        "steps": [
                            "Check connection pool settings",
                            "Verify network connectivity",
                            "Review application logs",
                        ],
                        "sources": ["database_troubleshooting.md", "INC-001"],
                    },
                    "error": None,
                }
            ]
        }
    }


# Health check schemas
class HealthResponse(BaseModel):
    """Schema for health check response."""

    status: str = Field(..., description="Service health status")
    timestamp: datetime = Field(..., description="Current timestamp")
    services: dict[str, str] = Field(..., description="Status of dependent services")


# Agent internal schemas
class PlanStep(BaseModel):
    """Schema for a single step in the agent's plan."""

    step_number: int = Field(..., description="Step sequence number")
    action: str = Field(..., description="Description of the action")
    tool: str | None = Field(None, description="Tool to use (search_docs or query_incidents)")
    tool_input: str | None = Field(None, description="Input for the tool")


class AgentPlan(BaseModel):
    """Schema for the agent's execution plan."""

    reasoning: str = Field(..., description="Reasoning behind the plan")
    steps: list[PlanStep] = Field(..., description="List of steps to execute")


class ToolCall(BaseModel):
    """Schema for recording a tool call."""

    tool: str = Field(..., description="Tool name")
    input: str = Field(..., description="Tool input")
    output: Any = Field(..., description="Tool output")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
