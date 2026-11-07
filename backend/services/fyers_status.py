"""Central FYERS connection status.

The platform owner stores one token server-side. Customers never see FYERS
credentials; the API only reports a coarse connection state.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from time import monotonic

from backend.core.time import utcnow
from config import Settings as LegacySettings
from data.fyers_client import AuthenticationError, FyersClient, FyersError
from login import TokenStore

logger = logging.getLogger("vwap_sentinel.fyers")

STATUS_NOT_CONFIGURED = "NOT_CONFIGURED"
STATUS_CONNECTED = "CONNECTED"
STATUS_AUTH_EXPIRED = "AUTHENTICATION_EXPIRED"
STATUS_AUTH_FAILED = "AUTHENTICATION_FAILED"
STATUS_API_UNAVAILABLE = "API_UNAVAILABLE"


@dataclass(frozen=True)
class FyersStatus:
    status: str
    message: str
    token_present: bool
    token_age_hours: float | None
    last_success_at: datetime | None
    checked_at: datetime


class FyersStatusService:
    """Verifies the centralized FYERS token, cached briefly to avoid hammering."""

    def __init__(self, legacy_settings: LegacySettings, cache_seconds: int = 30) -> None:
        self.settings = legacy_settings
        self.cache_seconds = max(int(cache_seconds), 0)
        self._cached: tuple[float, FyersStatus] | None = None
        self._last_success_at: datetime | None = None

    def mark_success(self) -> None:
        self._last_success_at = utcnow()
        self._cached = None

    def check(self, force: bool = False) -> FyersStatus:
        now = monotonic()
        if (
            not force
            and self._cached is not None
            and now - self._cached[0] < self.cache_seconds
        ):
            return self._cached[1]

        status = self._probe()
        self._cached = (now, status)
        return status

    def _probe(self) -> FyersStatus:
        store = TokenStore(self.settings)
        token = store.load_token()
        token_present = bool(token)
        token_age = store.age_hours()

        if self.settings.missing_credentials():
            return self._result(
                STATUS_NOT_CONFIGURED,
                "FYERS credentials are not configured on the server.",
                token_present,
                token_age,
            )
        if not token:
            return self._result(
                STATUS_AUTH_EXPIRED,
                "No stored FYERS access token. The owner must log in again.",
                token_present,
                token_age,
            )

        try:
            FyersClient(self.settings, token).verify_connection()
        except AuthenticationError:
            return self._result(
                STATUS_AUTH_EXPIRED,
                "FYERS access token is invalid or expired.",
                token_present,
                token_age,
            )
        except FyersError as exc:
            logger.warning("FYERS status probe failed: %s", exc)
            return self._result(
                STATUS_AUTH_FAILED,
                "FYERS authentication check failed.",
                token_present,
                token_age,
            )
        except Exception as exc:  # network/SDK failures must not crash the API
            logger.warning("FYERS API unavailable: %s", type(exc).__name__)
            return self._result(
                STATUS_API_UNAVAILABLE,
                "FYERS API is currently unreachable.",
                token_present,
                token_age,
            )

        self._last_success_at = utcnow()
        return self._result(
            STATUS_CONNECTED,
            "FYERS connection is healthy.",
            token_present,
            token_age,
        )

    def _result(
        self,
        status: str,
        message: str,
        token_present: bool,
        token_age: float | None,
    ) -> FyersStatus:
        return FyersStatus(
            status=status,
            message=message,
            token_present=token_present,
            token_age_hours=token_age,
            last_success_at=self._last_success_at,
            checked_at=utcnow(),
        )


@lru_cache(maxsize=1)
def get_fyers_status_service() -> FyersStatusService:
    settings = LegacySettings.from_env()
    return FyersStatusService(settings)
