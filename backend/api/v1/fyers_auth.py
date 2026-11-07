"""Owner-level FYERS OAuth endpoints.

- Admin (API key) asks for a login URL.
- FYERS redirects the browser to the public callback, which stores the token
  server-side. No customer ever uses these endpoints.
"""

from __future__ import annotations

import html
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse

from backend.api.deps import require_admin_key
from backend.core.config import get_settings
from backend.schemas.market_data import FyersLoginUrlOut
from backend.services.fyers_auth import (
    FyersAuthError,
    FyersAuthService,
    get_fyers_auth_service,
)
from login import extract_auth_code

logger = logging.getLogger("vwap_sentinel.fyers_auth")

router = APIRouter(tags=["fyers"])


def _page(title: str, message: str, success: bool) -> HTMLResponse:
    settings = get_settings()
    admin_url = f"{settings.frontend_base_url.rstrip('/')}/admin"
    color = "#34d399" if success else "#f87171"
    refresh = (
        f'<meta http-equiv="refresh" content="3;url={html.escape(admin_url, quote=True)}">'
        if success
        else ""
    )
    body = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">{refresh}
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
body{{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
background:#0e1117;color:#e6edf3;font-family:system-ui,sans-serif}}
.card{{max-width:520px;padding:32px;border:1px solid #26303d;border-radius:12px;background:#161b22}}
h1{{margin:0 0 8px;font-size:20px;color:{color}}}
p{{margin:0 0 16px;line-height:1.5;color:#9aa7b8}}
a{{color:#e6edf3}}
</style></head>
<body><div class="card"><h1>{html.escape(title)}</h1>
<p>{html.escape(message)}</p>
<a href="{html.escape(admin_url, quote=True)}">Open the admin panel</a>
</div></body></html>"""
    return HTMLResponse(
        content=body,
        status_code=200 if success else 400,
    )


@router.get(
    "/admin/fyers/login-url",
    response_model=FyersLoginUrlOut,
    summary="Create an owner-level FYERS login URL",
    dependencies=[Depends(require_admin_key)],
)
def create_fyers_login_url(
    service: FyersAuthService = Depends(get_fyers_auth_service),
) -> FyersLoginUrlOut:
    try:
        result = service.create_login_url()
    except FyersAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    return FyersLoginUrlOut(
        login_url=result.login_url,
        redirect_uri=result.redirect_uri,
        state_expires_at=result.state_expires_at,
    )


@router.get(
    "/fyers/callback",
    response_class=HTMLResponse,
    summary="FYERS OAuth callback (owner only)",
)
def fyers_callback(
    auth_code: str | None = Query(default=None),
    code: str | None = Query(default=None),
    state: str = Query(default=""),
    service: FyersAuthService = Depends(get_fyers_auth_service),
) -> HTMLResponse:
    params = {"auth_code": auth_code, "code": code}
    extracted = extract_auth_code({key: value for key, value in params.items() if value})
    if not extracted:
        return _page(
            "FYERS login failed",
            "No authorization code was returned. Start the login again from the admin panel.",
            success=False,
        )

    try:
        service.exchange(extracted, state)
    except FyersAuthError as exc:
        logger.warning("FYERS OAuth callback rejected: %s", exc)
        return _page("FYERS login failed", str(exc), success=False)
    except Exception as exc:
        logger.exception("FYERS OAuth exchange failed")
        return _page(
            "FYERS login failed",
            f"Token exchange failed ({type(exc).__name__}). Check the API logs.",
            success=False,
        )

    return _page(
        "FYERS connected",
        "The access token was stored on the server. Ingestion can now run.",
        success=True,
    )
