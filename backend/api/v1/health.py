"""Health endpoints.

``live`` answers whether the process is up. ``ready`` additionally verifies the
database so orchestrators do not route traffic to a process that cannot serve.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend import __version__
from backend.core.config import get_settings
from backend.core.time import utcnow
from backend.db.session import get_db
from backend.schemas.health import LivenessResponse, ReadinessResponse

logger = logging.getLogger("vwap_sentinel.api.health")

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", response_model=LivenessResponse, summary="Liveness probe")
def live() -> LivenessResponse:
    settings = get_settings()
    return LivenessResponse(
        service=settings.app_name,
        version=__version__,
        environment=settings.environment,
        time_utc=utcnow(),
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness probe",
    responses={503: {"description": "Database is unreachable"}},
)
def ready(db: Session = Depends(get_db)) -> ReadinessResponse:
    try:
        db.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError) as exc:
        logger.warning("Readiness check failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "error", "database": "unavailable"},
        ) from exc

    return ReadinessResponse(status="ok", database="ok", time_utc=utcnow())
