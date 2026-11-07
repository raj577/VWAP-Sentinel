"""Authentication endpoints: registration, login, refresh, sessions, passwords."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.api.deps import (
    AuthPrincipal,
    enforce_csrf,
    get_principal,
    rate_limit,
    require_active_account,
)
from backend.core.config import get_settings
from backend.core.time import utcnow
from backend.db.models import (
    EmailVerificationToken,
    PasswordResetToken,
    RefreshToken,
    Role,
    User,
    UserRole,
    UserSession,
)
from backend.db.session import get_db
from backend.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    ProfileUpdateRequest,
    RefreshRequest,
    RegisterRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    SessionListResponse,
    SessionOut,
    TokenResponse,
    UserOut,
    VerifyEmailRequest,
)
from backend.services.email import (
    send_password_reset_email,
    send_verification_email,
)
from backend.services.security import (
    ACCESS_COOKIE,
    CSRF_COOKIE,
    REFRESH_COOKIE,
    ROLE_ADMIN,
    ROLE_CUSTOMER,
    ROLE_SUPER_ADMIN,
    STATUS_ACTIVE,
    STATUS_DISABLED,
    STATUS_PENDING,
    STATUS_SUSPENDED,
    hash_password,
    hash_token,
    issue_tokens,
    new_raw_token,
    normalize_email,
    record_audit,
    validate_password,
    verify_password,
)

logger = logging.getLogger("vwap_sentinel.auth")

router = APIRouter(prefix="/auth", tags=["auth"])

_DUMMY_HASH = hash_password("dummy-password-value-for-timing")


def _is_past(value: datetime) -> bool:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value < utcnow()
VERIFICATION_TTL = timedelta(hours=24)
RESET_TTL = timedelta(minutes=30)


def _roles(db: Session, user_id: uuid.UUID) -> list[str]:
    return list(
        db.scalars(
            select(Role.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        )
    )


def _user_out(db: Session, user: User) -> UserOut:
    return UserOut(
        id=str(user.id),
        full_name=user.full_name,
        email=user.email,
        account_status=user.account_status,
        email_verified_at=user.email_verified_at,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        roles=_roles(db, user.id),
    )


def _ensure_role(db: Session, user: User, name: str) -> None:
    role = db.scalar(select(Role).where(Role.name == name))
    if role is None:
        role = Role(name=name)
        db.add(role)
        db.flush()
    exists = db.scalar(
        select(UserRole).where(
            UserRole.user_id == user.id, UserRole.role_id == role.id
        )
    )
    if exists is None:
        db.add(UserRole(user_id=user.id, role_id=role.id))


def _client_meta(request: Request) -> tuple[str | None, str | None, str | None]:
    device = request.headers.get("x-device-name")
    agent = request.headers.get("user-agent")
    forwarded = request.headers.get("x-forwarded-for")
    ip = (
        forwarded.split(",")[0].strip()
        if forwarded
        else (request.client.host if request.client else None)
    )
    return device, agent, ip


def _set_auth_cookies(response: Response, tokens: TokenResponse) -> None:
    settings = get_settings()
    secure = settings.cookie_secure
    response.set_cookie(
        ACCESS_COOKIE,
        tokens.access_token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
    )
    response.set_cookie(
        REFRESH_COOKIE,
        tokens.refresh_token,
        max_age=settings.refresh_token_expire_days * 86400,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
    )
    response.set_cookie(
        CSRF_COOKIE,
        tokens.csrf_token,
        max_age=settings.refresh_token_expire_days * 86400,
        httponly=False,
        samesite="lax",
        secure=secure,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    for name in (ACCESS_COOKIE, REFRESH_COOKIE, CSRF_COOKIE):
        response.delete_cookie(name, path="/")


def _token_response(db: Session, user: User, issued) -> TokenResponse:
    return TokenResponse(
        access_token=issued.access_token,
        refresh_token=issued.refresh_token,
        expires_in=get_settings().access_token_expire_minutes * 60,
        csrf_token=issued.csrf_token,
        user=_user_out(db, user),
    )


def _issue_session_tokens(
    db: Session,
    user: User,
    request: Request,
    *,
    family_id: uuid.UUID | None = None,
    replaces: RefreshToken | None = None,
    session: UserSession | None = None,
):
    device, agent, ip = _client_meta(request)
    issued = issue_tokens(
        db,
        user,
        device_name=device,
        user_agent=agent,
        ip_address=ip,
        family_id=family_id,
        replaces=replaces,
    )
    if session is None:
        session = UserSession(
            user_id=user.id,
            device_name=device or "web",
            user_agent=agent,
            last_activity_at=utcnow(),
        )
        db.add(session)
    session.last_activity_at = utcnow()
    session.revoked_at = None
    db.flush()
    session.refresh_token_id = (
        db.scalar(
            select(RefreshToken).where(
                RefreshToken.token_hash == hash_token(issued.refresh_token)
            )
        ).id
    )
    return issued


# ------------------------------------------------------------------ register
@router.post(
    "/register",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("register"))],
)
def register(
    payload: RegisterRequest, db: Session = Depends(get_db)
) -> MessageResponse:
    email = normalize_email(payload.email)
    try:
        validate_password(payload.password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    if db.scalar(select(User).where(User.email == email)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to register with this email.",
        )

    user = User(
        full_name=payload.full_name,
        email=email,
        password_hash=hash_password(payload.password),
        account_status=STATUS_PENDING,
    )
    db.add(user)
    db.flush()
    _ensure_role(db, user, ROLE_CUSTOMER)

    raw_token = new_raw_token()
    db.add(
        EmailVerificationToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=utcnow() + VERIFICATION_TTL,
        )
    )
    record_audit(db, action="user.registered", target_user_id=user.id)
    db.commit()

    try:
        send_verification_email(user.email, user.full_name, raw_token)
    except Exception:
        logger.exception("Could not send verification email")

    dev_token = raw_token if get_settings().auth_dev_expose_tokens else None
    return MessageResponse(
        message="Registration received. Check your email to verify the account.",
        dev_token=dev_token,
    )


# ------------------------------------------------------------------- verify
@router.post(
    "/verify-email",
    response_model=MessageResponse,
    dependencies=[Depends(rate_limit("verify"))],
)
def verify_email(
    payload: VerifyEmailRequest, db: Session = Depends(get_db)
) -> MessageResponse:
    record = db.scalar(
        select(EmailVerificationToken)
        .where(EmailVerificationToken.token_hash == hash_token(payload.token))
        .with_for_update()
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification link is invalid or expired.",
        )
    if record.used_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification link has already been used.",
        )
    if _is_past(record.expires_at):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification link has expired.",
        )

    user = db.get(User, record.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification link is invalid.",
        )

    record.used_at = utcnow()
    user.email_verified_at = utcnow()
    if user.account_status == STATUS_PENDING:
        user.account_status = STATUS_ACTIVE
    record_audit(db, action="email.verified", target_user_id=user.id)
    db.commit()
    return MessageResponse(message="Email verified. You can sign in now.")


@router.post(
    "/resend-verification",
    response_model=MessageResponse,
    dependencies=[Depends(rate_limit("resend"))],
)
def resend_verification(
    payload: ResendVerificationRequest, db: Session = Depends(get_db)
) -> MessageResponse:
    generic = MessageResponse(
        message="If the account exists and needs verification, an email was sent."
    )
    user = db.scalar(select(User).where(User.email == normalize_email(payload.email)))
    if user is None or user.account_status != STATUS_PENDING:
        return generic

    raw_token = new_raw_token()
    db.add(
        EmailVerificationToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=utcnow() + VERIFICATION_TTL,
        )
    )
    db.commit()
    try:
        send_verification_email(user.email, user.full_name, raw_token)
    except Exception:
        logger.exception("Could not send verification email")
    if get_settings().auth_dev_expose_tokens:
        generic.dev_token = raw_token
    return generic


# -------------------------------------------------------------------- login
@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit("login", "login_rate_limit_per_minute"))],
)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    email = normalize_email(payload.email)
    user = db.scalar(select(User).where(User.email == email))

    if user is None:
        verify_password(_DUMMY_HASH, payload.password)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if not verify_password(user.password_hash, payload.password):
        record_audit(db, action="login.failed")
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if user.account_status == STATUS_PENDING:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verify your email before signing in.",
        )
    if user.account_status in {STATUS_SUSPENDED, STATUS_DISABLED}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active.",
        )
    if user.account_status != STATUS_ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account is not active."
        )

    issued = _issue_session_tokens(db, user, request)
    if payload.device_name:
        session = db.scalar(
            select(UserSession)
            .where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
            .order_by(UserSession.created_at.desc())
        )
        if session is not None:
            session.device_name = payload.device_name[:120]

    user.last_login_at = utcnow()
    record_audit(
        db,
        action="login.succeeded",
        actor_user_id=user.id,
        target_user_id=user.id,
    )
    db.commit()

    tokens = _token_response(db, user, issued)
    _set_auth_cookies(response, tokens)
    return tokens


# ------------------------------------------------------------------ refresh
@router.post(
    "/refresh",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit("refresh"))],
)
def refresh(
    payload: RefreshRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    raw = payload.refresh_token or request.cookies.get(REFRESH_COOKIE)
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required.",
        )
    if payload.refresh_token is None:
        from backend.api.deps import enforce_csrf as _enforce
        from backend.api.deps import AuthPrincipal as _Principal

        _enforce(
            request,
            _Principal(user=None, roles=frozenset(), source="cookie"),
        )

    record = db.scalar(
        select(RefreshToken)
        .where(RefreshToken.token_hash == hash_token(raw))
        .with_for_update()
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please sign in again.",
        )

    now = utcnow()
    if record.revoked_at is not None:
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.token_family_id == record.token_family_id)
            .values(revoked_at=now)
        )
        db.execute(
            update(UserSession)
            .where(UserSession.refresh_token_id == record.id)
            .values(revoked_at=now)
        )
        record_audit(
            db,
            action="refresh.reuse_detected",
            target_user_id=record.user_id,
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please sign in again.",
        )

    if _is_past(record.expires_at):
        record.revoked_at = now
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please sign in again.",
        )

    user = db.get(User, record.user_id)
    if user is None or user.account_status != STATUS_ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please sign in again.",
        )

    session = db.scalar(
        select(UserSession).where(UserSession.refresh_token_id == record.id)
    )
    issued = _issue_session_tokens(
        db,
        user,
        request,
        family_id=record.token_family_id,
        replaces=record,
        session=session,
    )
    db.commit()

    tokens = _token_response(db, user, issued)
    _set_auth_cookies(response, tokens)
    return tokens


# ------------------------------------------------------------- logout/sessions
@router.post("/logout", response_model=MessageResponse)
def logout(
    payload: LogoutRequest,
    request: Request,
    response: Response,
    principal: AuthPrincipal = Depends(require_active_account),
    db: Session = Depends(get_db),
) -> MessageResponse:
    enforce_csrf(request, principal)
    raw = payload.refresh_token or request.cookies.get(REFRESH_COOKIE)
    if raw:
        record = db.scalar(
            select(RefreshToken).where(
                RefreshToken.token_hash == hash_token(raw)
            )
        )
        if record is not None and record.user_id == principal.user.id:
            now = utcnow()
            record.revoked_at = now
            db.execute(
                update(UserSession)
                .where(UserSession.refresh_token_id == record.id)
                .values(revoked_at=now)
            )
            record_audit(
                db,
                action="logout",
                actor_user_id=principal.user.id,
                target_user_id=principal.user.id,
            )
            db.commit()
    _clear_auth_cookies(response)
    return MessageResponse(message="Signed out.")


@router.post("/logout-all", response_model=MessageResponse)
def logout_all(
    request: Request,
    response: Response,
    principal: AuthPrincipal = Depends(require_active_account),
    db: Session = Depends(get_db),
) -> MessageResponse:
    enforce_csrf(request, principal)
    now = utcnow()
    db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == principal.user.id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    db.execute(
        update(UserSession)
        .where(
            UserSession.user_id == principal.user.id,
            UserSession.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    record_audit(
        db,
        action="logout.all",
        actor_user_id=principal.user.id,
        target_user_id=principal.user.id,
    )
    db.commit()
    _clear_auth_cookies(response)
    return MessageResponse(message="Signed out from all sessions.")


@router.get("/sessions", response_model=SessionListResponse)
def list_sessions(
    request: Request,
    principal: AuthPrincipal = Depends(require_active_account),
    db: Session = Depends(get_db),
) -> SessionListResponse:
    current_hash = None
    raw = request.cookies.get(REFRESH_COOKIE)
    if raw:
        current_hash = hash_token(raw)

    rows = db.execute(
        select(UserSession, RefreshToken)
        .join(RefreshToken, RefreshToken.id == UserSession.refresh_token_id)
        .where(
            UserSession.user_id == principal.user.id,
            UserSession.revoked_at.is_(None),
            RefreshToken.revoked_at.is_(None),
        )
        .order_by(UserSession.created_at.desc())
    ).all()

    sessions = [
        SessionOut(
            id=str(session.id),
            device_name=session.device_name,
            user_agent=session.user_agent,
            ip_address=token.ip_address,
            created_at=session.created_at,
            last_activity_at=session.last_activity_at,
            current=token.token_hash == current_hash,
        )
        for session, token in rows
    ]
    return SessionListResponse(sessions=sessions)


@router.delete("/sessions/{session_id}", response_model=MessageResponse)
def revoke_session(
    session_id: uuid.UUID,
    request: Request,
    principal: AuthPrincipal = Depends(require_active_account),
    db: Session = Depends(get_db),
) -> MessageResponse:
    enforce_csrf(request, principal)
    session = db.get(UserSession, session_id)
    if session is None or session.user_id != principal.user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found."
        )
    now = utcnow()
    session.revoked_at = now
    if session.refresh_token_id is not None:
        token = db.get(RefreshToken, session.refresh_token_id)
        if token is not None:
            token.revoked_at = now
    record_audit(
        db,
        action="session.revoked",
        actor_user_id=principal.user.id,
        target_user_id=principal.user.id,
        entity_type="session",
        entity_id=str(session_id),
    )
    db.commit()
    return MessageResponse(message="Session revoked.")


# ----------------------------------------------------------------- passwords
@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    dependencies=[Depends(rate_limit("forgot"))],
)
def forgot_password(
    payload: ForgotPasswordRequest, db: Session = Depends(get_db)
) -> MessageResponse:
    generic = MessageResponse(
        message="If the account exists, a password reset email was sent."
    )
    user = db.scalar(select(User).where(User.email == normalize_email(payload.email)))
    if user is None or user.account_status in {STATUS_DISABLED}:
        return generic

    raw_token = new_raw_token()
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=utcnow() + RESET_TTL,
        )
    )
    record_audit(db, action="password.reset_requested", target_user_id=user.id)
    db.commit()
    try:
        send_password_reset_email(user.email, user.full_name, raw_token)
    except Exception:
        logger.exception("Could not send password reset email")
    if get_settings().auth_dev_expose_tokens:
        generic.dev_token = raw_token
    return generic


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    dependencies=[Depends(rate_limit("reset"))],
)
def reset_password(
    payload: ResetPasswordRequest, db: Session = Depends(get_db)
) -> MessageResponse:
    try:
        validate_password(payload.new_password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    record = db.scalar(
        select(PasswordResetToken)
        .where(PasswordResetToken.token_hash == hash_token(payload.token))
        .with_for_update()
    )
    if record is None or record.used_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset link is invalid or has already been used.",
        )
    if _is_past(record.expires_at):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset link has expired.",
        )

    user = db.get(User, record.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Reset link is invalid."
        )

    now = utcnow()
    record.used_at = now
    user.password_hash = hash_password(payload.new_password)
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    db.execute(
        update(UserSession)
        .where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    record_audit(
        db,
        action="password.reset",
        target_user_id=user.id,
    )
    db.commit()
    return MessageResponse(message="Password updated. Sign in with the new password.")


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    principal: AuthPrincipal = Depends(require_active_account),
    db: Session = Depends(get_db),
) -> MessageResponse:
    enforce_csrf(request, principal)
    user = principal.user
    if not verify_password(user.password_hash, payload.current_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )
    try:
        validate_password(payload.new_password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    user.password_hash = hash_password(payload.new_password)
    now = utcnow()
    raw = request.cookies.get(REFRESH_COOKIE)
    current_hash = hash_token(raw) if raw else None
    current = (
        db.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == current_hash)
        )
        if current_hash
        else None
    )
    other_tokens = db.scalars(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.id != (current.id if current else uuid.uuid4()),
        )
    ).all()
    for token in other_tokens:
        token.revoked_at = now
    if other_tokens:
        db.execute(
            update(UserSession)
            .where(
                UserSession.user_id == user.id,
                UserSession.revoked_at.is_(None),
                UserSession.refresh_token_id.in_([token.id for token in other_tokens]),
            )
            .values(revoked_at=now)
        )
    record_audit(
        db,
        action="password.changed",
        actor_user_id=user.id,
        target_user_id=user.id,
    )
    db.commit()
    return MessageResponse(message="Password changed. Other sessions were revoked.")


# ----------------------------------------------------------------------- me
@router.get("/me", response_model=UserOut)
def me(
    principal: AuthPrincipal = Depends(require_active_account),
    db: Session = Depends(get_db),
) -> UserOut:
    return _user_out(db, principal.user)


@router.patch("/me", response_model=UserOut)
def update_me(
    payload: ProfileUpdateRequest,
    request: Request,
    principal: AuthPrincipal = Depends(require_active_account),
    db: Session = Depends(get_db),
) -> UserOut:
    enforce_csrf(request, principal)
    principal.user.full_name = payload.full_name
    record_audit(
        db,
        action="profile.updated",
        actor_user_id=principal.user.id,
        target_user_id=principal.user.id,
    )
    db.commit()
    db.refresh(principal.user)
    return _user_out(db, principal.user)
