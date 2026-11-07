"""Central authentication and authorization dependencies."""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.db.models import Role, User, UserRole
from backend.db.session import get_db
from backend.services.rate_limit import check_rate_limit
from backend.services.security import (
    ACCESS_COOKIE,
    CSRF_COOKIE,
    ROLE_ADMIN,
    ROLE_SUPER_ADMIN,
    STATUS_ACTIVE,
    TokenError,
    csrf_matches,
    decode_access_token,
)


@dataclass(frozen=True)
class AuthPrincipal:
    user: User | None
    roles: frozenset[str]
    source: str  # "cookie" | "bearer" | "api_key"

    @property
    def is_service(self) -> bool:
        return self.source == "api_key"

    @property
    def is_admin(self) -> bool:
        return self.is_service or bool(
            self.roles & {ROLE_ADMIN, ROLE_SUPER_ADMIN}
        )

    @property
    def is_super_admin(self) -> bool:
        return self.is_service or ROLE_SUPER_ADMIN in self.roles

    @property
    def user_id(self) -> uuid.UUID | None:
        return self.user.id if self.user else None


def _bearer_token(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip() or None
    return None


def _roles_for(db: Session, user_id: uuid.UUID) -> frozenset[str]:
    rows = db.scalars(
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
    )
    return frozenset(rows)


def get_principal(
    request: Request, db: Session = Depends(get_db)
) -> AuthPrincipal:
    token = _bearer_token(request)
    source = "bearer"
    if not token:
        token = request.cookies.get(ACCESS_COOKIE)
        source = "cookie"
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    try:
        payload = decode_access_token(token)
        user_id = uuid.UUID(str(payload["sub"]))
    except (TokenError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account not found.",
        )
    if user.account_status != STATUS_ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active. Verify your email or contact support.",
        )

    request.state.auth_source = source
    return AuthPrincipal(user=user, roles=_roles_for(db, user.id), source=source)


def get_current_user(
    principal: AuthPrincipal = Depends(get_principal),
) -> User:
    assert principal.user is not None
    return principal.user


def require_authenticated_user(
    principal: AuthPrincipal = Depends(get_principal),
) -> AuthPrincipal:
    return principal


def require_active_account(
    principal: AuthPrincipal = Depends(get_principal),
) -> AuthPrincipal:
    return principal


def require_role(*allowed: str):
    allowed_set = frozenset(allowed)

    def dependency(
        principal: AuthPrincipal = Depends(get_principal),
    ) -> AuthPrincipal:
        if not (principal.roles & allowed_set):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions.",
            )
        return principal

    return dependency


require_admin = require_role(ROLE_ADMIN, ROLE_SUPER_ADMIN)
require_super_admin = require_role(ROLE_SUPER_ADMIN)


def require_admin_key(
    request: Request,
    x_admin_key: str = Header(default=""),
    db: Session = Depends(get_db),
) -> AuthPrincipal:
    """Admin access via JWT role or the server-side service key.

    The API key path exists for operational tooling and is never exposed to the
    browser; interactive admins authenticate with JWT.
    """

    configured = get_settings().admin_api_key
    if configured and x_admin_key and secrets.compare_digest(x_admin_key, configured):
        return AuthPrincipal(user=None, roles=frozenset(), source="api_key")

    try:
        principal = get_principal(request, db)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_403_FORBIDDEN:
            raise
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required.",
        ) from exc

    if not (principal.roles & {ROLE_ADMIN, ROLE_SUPER_ADMIN}):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator role required.",
        )
    return principal


def enforce_csrf(request: Request, principal: AuthPrincipal) -> None:
    """Double-submit CSRF check for cookie-authenticated mutations."""

    if principal.source != "cookie":
        return
    if not csrf_matches(
        request.cookies.get(CSRF_COOKIE), request.headers.get("x-csrf-token")
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing or invalid.",
        )


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(scope: str, setting_name: str = "auth_rate_limit_per_minute"):
    def dependency(request: Request) -> None:
        limit = int(getattr(get_settings(), setting_name))
        allowed, retry_after = check_rate_limit(
            f"{scope}:{_client_ip(request)}", limit, 60
        )
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Try again later.",
                headers={"Retry-After": str(retry_after)},
            )

    return dependency
