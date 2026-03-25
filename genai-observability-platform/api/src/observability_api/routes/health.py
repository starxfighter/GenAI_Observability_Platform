"""Health check endpoints."""

from datetime import datetime

from fastapi import APIRouter

from ..models.common import HealthCheck

router = APIRouter()


@router.get("/health", response_model=HealthCheck)
async def health_check() -> HealthCheck:
    """Check API health status."""
    # In production, would check actual service connectivity
    return HealthCheck(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow(),
        components={
            "api": "healthy",
            "dynamodb": "healthy",
            "timestream": "healthy",
            "opensearch": "healthy",
        },
    )


@router.get("/")
async def root() -> dict:
    """API root endpoint."""
    return {
        "name": "GenAI Observability Platform API",
        "version": "1.0.0",
        "docs": "/docs",
    }
