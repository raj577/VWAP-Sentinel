"""Owner-level FYERS OAuth performed from the admin panel.

The admin starts the flow, FYERS redirects to this backend, and the access token
is stored server-side exactly like the legacy Streamlit login. The OAuth state
is HMAC-signed so the callback works without a session cookie and cannot be
forged.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import time
from dataclasses import dataclass, replace
from functools import lru_cache

from fyers_apiv3 import fyersModel

from backend.core.config import Settings as BackendSettings
from backend.core.config import get_settings
from config import Settings as LegacySettings
from login import exchange_auth_code
from backend.services.fyers_status import get_fyers_status_service

logger = logging.getLogger("vwap_sentinel.fyers_auth")


class FyersAuthError(RuntimeError):
    """The FYERS login flow cannot start or the callback is invalid."""


@dataclass(frozen=True)
class FyersLoginUrl:
    login_url: str
    redirect_uri: str
    state_expires_at: float


class FyersAuthService:
    def __init__(
        self,
        settings: BackendSettings,
        legacy_settings: LegacySettings,
    ) -> None:
        self.settings = settings
        self.legacy = legacy_settings

    # ------------------------------------------------------------------ state
    def _sign(self, issued: float, nonce: str) -> str:
        secret = self.settings.admin_api_key
        message = f"{issued:.0f}.{nonce}".encode("utf-8")
        digest = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
        return f"{issued:.0f}.{nonce}.{digest[:40]}"

    def _verify(self, state: str, now: float | None = None) -> bool:
        if not self.settings.admin_api_key or not state:
            return False
        parts = state.split(".")
        if len(parts) != 3:
            return False
        issued_text, nonce, signature = parts
        try:
            issued = float(issued_text)
        except ValueError:
            return False
        current = time.time() if now is None else now
        if issued > current + 60:
            return False
        if current - issued > self.settings.fyers_login_state_ttl_seconds:
            return False
        expected = self._sign(issued, nonce)
        return hmac.compare_digest(expected, state)

    def create_state(self) -> str:
        if not self.settings.admin_api_key:
            raise FyersAuthError(
                "ADMIN_API_KEY must be configured to start the FYERS login flow."
            )
        return self._sign(time.time(), secrets.token_urlsafe(8))

    # ------------------------------------------------------------------ login
    def create_login_url(self) -> FyersLoginUrl:
        if not self.legacy.client_id or not self.legacy.secret_key:
            raise FyersAuthError(
                "FYERS_CLIENT_ID and FYERS_SECRET_KEY must be configured."
            )
        state = self.create_state()
        redirect_uri = self.settings.fyers_backend_redirect_uri

        session = fyersModel.SessionModel(
            client_id=self.legacy.client_id,
            secret_key=self.legacy.secret_key,
            redirect_uri=redirect_uri,
            response_type="code",
            grant_type="authorization_code",
            state=state,
        )
        try:
            login_url = session.generate_authcode()
        except Exception as exc:
            raise FyersAuthError(
                f"Could not build the FYERS login URL: {type(exc).__name__}"
            ) from exc

        return FyersLoginUrl(
            login_url=login_url,
            redirect_uri=redirect_uri,
            state_expires_at=time.time() + self.settings.fyers_login_state_ttl_seconds,
        )

    def exchange(self, auth_code: str, state: str) -> None:
        if not self._verify(state):
            raise FyersAuthError(
                "Invalid or expired OAuth state. Start the login again from the admin panel."
            )
        legacy = replace(
            self.legacy, redirect_uri=self.settings.fyers_backend_redirect_uri
        )
        exchange_auth_code(legacy, auth_code)
        get_fyers_status_service().mark_success()
        logger.info("Central FYERS token refreshed through the admin panel")


@lru_cache(maxsize=1)
def get_fyers_auth_service() -> FyersAuthService:
    return FyersAuthService(get_settings(), LegacySettings.from_env())
