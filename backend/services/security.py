"""Password hashing, JWT access tokens, opaque refresh tokens and audit helpers."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.core.time import utcnow
from backend.db.models import AuditLog, RefreshToken, User

ROLE_SUPER_ADMIN = "SUPER_ADMIN"
ROLE_ADMIN = "ADMIN"
ROLE_CUSTOMER = "CUSTOMER"
ROLES = (ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_CUSTOMER)

STATUS_ACTIVE = "ACTIVE"
STATUS_PENDING = "PENDING_VERIFICATION"
STATUS_SUSPENDED = "SUSPENDED"
STATUS_DISABLED = "DISABLED"

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
CSRF_COOKIE = "csrf_token"

_hasher = PasswordHasher()


class AuthError(RuntimeError):
    """Base authentication/authorization error."""


class TokenError(AuthError):
    """A token is invalid, expired or reused."""


@dataclass(frozen=True)
class IssuedTokens:
    access_token: str
    refresh_token: str
    csrf_token: str
    access_expires_at: datetime
    refresh_expires_at: datetime


def normalize_email(email: str) -> str:
    return str(email).strip().lower()


def validate_password(password: str) -> None:
    """Enforce a practical password policy; raise ValueError with a safe message."""

    if not isinstance(password, str) or len(password) < 10:
        raise ValueError("Password must be at least 10 characters long.")
    classes = sum(
        (
            any(character.islower() for character in password),
            any(character.isupper() for character in password),
            any(character.isdigit() for character in password),
            any(not character.isalnum() for character in password),
        )
    )
    if classes < 3:
        raise ValueError(
            "Password must include at least three of: lowercase, uppercase, "
            "digit, symbol."
        )


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, ValueError):
        return False


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def new_raw_token() -> str:
    return secrets.token_urlsafe(48)


def new_csrf_token() -> str:
    return secrets.token_urlsafe(24)


def create_access_token(user_id: uuid.UUID | str) -> tuple[str, datetime]:
    settings = get_settings()
    now = datetime.now(tz=timezone.utc)
    expires = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "jti": str(uuid.uuid4()),
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }
    token = jwt.encode(
        payload, settings.auth_secret_key, algorithm=settings.jwt_algorithm
    )
    return token, expires


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    if not token:
        raise TokenError("Missing access token.")
    try:
        return jwt.decode(
            token,
            settings.auth_secret_key,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "iat", "sub", "iss", "aud"]},
        )
    except jwt.PyJWTError as exc:
        raise TokenError("Invalid or expired access token.") from exc


def issue_refresh_token(
    db: Session,
    user: User,
    *,
    family_id: uuid.UUID | None = None,
    device_name: str | None = None,
    user_agent: str | None = None,
    ip_address: str | None = None,
    replaces: RefreshToken | None = None,
) -> tuple[str, RefreshToken]:
    settings = get_settings()
    raw = new_raw_token()
    now = utcnow()
    record = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(raw),
        token_family_id=family_id or uuid.uuid4(),
        device_name=(device_name or "web")[:120],
        user_agent=(user_agent or "")[:1000] or None,
        ip_address=ip_address,
        expires_at=now + timedelta(days=settings.refresh_token_expire_days),
        last_used_at=now,
    )
    db.add(record)
    db.flush()
    if replaces is not None:
        replaces.revoked_at = now
        replaces.replaced_by_token_id = record.id
    return raw, record


def issue_tokens(
    db: Session,
    user: User,
    *,
    device_name: str | None = None,
    user_agent: str | None = None,
    ip_address: str | None = None,
    family_id: uuid.UUID | None = None,
    replaces: RefreshToken | None = None,
) -> IssuedTokens:
    access, access_expires = create_access_token(user.id)
    raw_refresh, record = issue_refresh_token(
        db,
        user,
        family_id=family_id,
        device_name=device_name,
        user_agent=user_agent,
        ip_address=ip_address,
        replaces=replaces,
    )
    return IssuedTokens(
        access_token=access,
        refresh_token=raw_refresh,
        csrf_token=new_csrf_token(),
        access_expires_at=access_expires,
        refresh_expires_at=record.expires_at,
    )


def csrf_matches(cookie_value: str | None, header_value: str | None) -> bool:
    if not cookie_value or not header_value:
        return False
    return hmac.compare_digest(cookie_value, header_value)


def record_audit(
    db: Session,
    *,
    action: str,
    actor_user_id: uuid.UUID | None = None,
    target_user_id: uuid.UUID | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    metadata: dict | None = None,
    ip_address: str | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            meta=metadata or {},
            ip_address=ip_address,
        )
    )
