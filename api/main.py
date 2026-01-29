"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router

app = FastAPI(
    title="Agentic Lab Assistant",
    description="A local-first agentic workflow system for processing lab requests",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router)


@app.get("/")
def root():
    """Root endpoint with API info."""
    return {
        "name": "Agentic Lab Assistant",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }
