"""Versioned API router.

Every future module (auth, scanner, admin, ...) mounts here so web and Flutter
clients share one stable contract.
"""

from __future__ import annotations

from fastapi import APIRouter

from backend.api.v1.admin_market_data import router as admin_market_data_router
from backend.api.v1.admin_pipeline import router as admin_pipeline_router
from backend.api.v1.admin_scans import router as admin_scans_router
from backend.api.v1.admin_users import router as admin_users_router
from backend.api.v1.auth import router as auth_router
from backend.api.v1.fyers_auth import router as fyers_auth_router
from backend.api.v1.health import router as health_router
from backend.api.v1.market_data import router as market_data_router
from backend.api.v1.scanner import router as scanner_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(market_data_router)
api_router.include_router(scanner_router)
api_router.include_router(admin_market_data_router)
api_router.include_router(admin_scans_router)
api_router.include_router(admin_users_router)
api_router.include_router(admin_pipeline_router)
api_router.include_router(fyers_auth_router)


@api_router.get("/", tags=["meta"], summary="API index")
def index() -> dict[str, str]:
    return {
        "service": "vwap-sentinel-api",
        "version": "v1",
        "docs": "/docs",
        "health_live": "/api/v1/health/live",
        "health_ready": "/api/v1/health/ready",
        "market_data_status": "/api/v1/market-data/status",
    }
