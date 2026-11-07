"""Admin user management and audit-log access."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from backend.api.deps import AuthPrincipal, require_admin_key
from backend.core.time import utcnow
from backend.db.models import AuditLog, RefreshToken, Role, User, UserRole, UserSession
from backend.db.session import get_db
from backend.schemas.auth import (
    AdminUserPage,
    AuditLogOut,
    MessageResponse,
    UserOut,
    UserRoleUpdate,
    UserStatusUpdate,
)
from backend.services.security import (
    ROLE_ADMIN,
    ROLE_CUSTOMER,
    ROLE_SUPER_ADMIN,
    STATUS_ACTIVE,
    STATUS_DISABLED,
    STATUS_SUSPENDED,
    record_audit,
)

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin_key)],
)

VALID_STATUSES = {STATUS_ACTIVE, STATUS_SUSPENDED, STATUS_DISABLED}


def _roles(db: Session, user_id: uuid.UUID) -> set[str]:
    return set(
        db.scalars(
            select(Role.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        )
    )


def _out(db: Session, user: User) -> UserOut:
    return UserOut(
        id=str(user.id),
        full_name=user.full_name,
        email=user.email,
        account_status=user.account_status,
        email_verified_at=user.email_verified_at,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        roles=sorted(_roles(db, user.id)),
    )


def _target(db: Session, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )
    return user


def _ensure_actor_can_manage(
    actor: AuthPrincipal, target_roles: set[str], actor_user_id: uuid.UUID | None
) -> None:
    if actor.is_service:
        return
    if actor_user_id is not None and actor.user_id == actor_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot change your own account through this endpoint.",
        )
    if ROLE_SUPER_ADMIN in target_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SUPER_ADMIN accounts cannot be managed here.",
        )
    if ROLE_ADMIN in target_roles and not actor.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SUPER_ADMIN can manage administrators.",
        )


@router.get("/users", response_model=AdminUserPage)
def list_users(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, max_length=120),
    role: str | None = Query(None, max_length=32),
    account_status: str | None = Query(None, max_length=24),
    sort: str = Query("created_at"),
) -> AdminUserPage:
    filters = []
    if search:
        pattern = f"%{search.strip().lower()}%"
        filters.append(
            or_(
                func.lower(User.email).like(pattern),
                func.lower(User.full_name).like(pattern),
            )
        )
    if account_status:
        filters.append(User.account_status == account_status)
    if role:
        filters.append(
            User.role_links.any(UserRole.role.has(Role.name == role))
        )

    total = int(
        db.scalar(select(func.count()).select_from(User).where(*filters)) or 0
    )

    order_column = {
        "created_at": User.created_at.asc(),
        "-created_at": User.created_at.desc(),
        "last_login_at": User.last_login_at.asc(),
        "-last_login_at": User.last_login_at.desc(),
        "email": User.email.asc(),
        "-email": User.email.desc(),
    }.get(sort, User.created_at.desc())

    rows = db.scalars(
        select(User)
        .where(*filters)
        .order_by(order_column)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return AdminUserPage(
        items=[_out(db, user) for user in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: uuid.UUID, db: Session = Depends(get_db)) -> UserOut:
    return _out(db, _target(db, user_id))


@router.patch("/users/{user_id}/status", response_model=UserOut)
def update_status(
    user_id: uuid.UUID,
    payload: UserStatusUpdate,
    principal: AuthPrincipal = Depends(require_admin_key),
    db: Session = Depends(get_db),
) -> UserOut:
    if payload.account_status not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status. Allowed: {sorted(VALID_STATUSES)}",
        )
    user = _target(db, user_id)
    _ensure_actor_can_manage(principal, _roles(db, user.id), user.id)

    previous = user.account_status
    user.account_status = payload.account_status
    if payload.account_status in {STATUS_SUSPENDED, STATUS_DISABLED}:
        now = utcnow()
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
        action="user.status_changed",
        actor_user_id=principal.user_id,
        target_user_id=user.id,
        entity_type="user",
        entity_id=str(user.id),
        metadata={"from": previous, "to": payload.account_status},
    )
    db.commit()
    db.refresh(user)
    return _out(db, user)


@router.patch("/users/{user_id}/role", response_model=UserOut)
def update_role(
    user_id: uuid.UUID,
    payload: UserRoleUpdate,
    principal: AuthPrincipal = Depends(require_admin_key),
    db: Session = Depends(get_db),
) -> UserOut:
    role_name = payload.role.upper()
    if role_name == ROLE_SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SUPER_ADMIN is created only through the bootstrap command.",
        )
    if role_name not in {ROLE_ADMIN, ROLE_CUSTOMER}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Role must be ADMIN or CUSTOMER.",
        )

    user = _target(db, user_id)
    _ensure_actor_can_manage(principal, _roles(db, user.id), user.id)

    if role_name == ROLE_ADMIN and not principal.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SUPER_ADMIN can assign ADMIN.",
        )

    admin_role = db.scalar(select(Role).where(Role.name == ROLE_ADMIN))
    customer_role = db.scalar(select(Role).where(Role.name == ROLE_CUSTOMER))
    if admin_role is None or customer_role is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Role catalogue is not initialized.",
        )

    db.execute(
        update(UserRole)
        .where(UserRole.user_id == user.id)
        .values(role_id=admin_role.id if role_name == ROLE_ADMIN else customer_role.id)
    )
    existing = db.scalar(
        select(UserRole).where(UserRole.user_id == user.id)
    )
    if existing is None:
        db.add(
            UserRole(
                user_id=user.id,
                role_id=admin_role.id if role_name == ROLE_ADMIN else customer_role.id,
                assigned_by=principal.user_id,
            )
        )

    record_audit(
        db,
        action="user.role_changed",
        actor_user_id=principal.user_id,
        target_user_id=user.id,
        entity_type="user",
        entity_id=str(user.id),
        metadata={"role": role_name},
    )
    db.commit()
    db.refresh(user)
    return _out(db, user)


@router.post("/users/{user_id}/revoke-sessions", response_model=MessageResponse)
def revoke_user_sessions(
    user_id: uuid.UUID,
    principal: AuthPrincipal = Depends(require_admin_key),
    db: Session = Depends(get_db),
) -> MessageResponse:
    user = _target(db, user_id)
    _ensure_actor_can_manage(principal, _roles(db, user.id), user.id)

    now = utcnow()
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
        action="user.sessions_revoked",
        actor_user_id=principal.user_id,
        target_user_id=user.id,
        entity_type="user",
        entity_id=str(user.id),
    )
    db.commit()
    return MessageResponse(message="All sessions revoked for the account.")


@router.get("/audit-logs", response_model=list[AuditLogOut])
def audit_logs(
    principal: AuthPrincipal = Depends(require_admin_key),
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
) -> list[AuditLogOut]:
    if not principal.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SUPER_ADMIN can read audit logs.",
        )
    rows = db.scalars(
        select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    ).all()
    return [
        AuditLogOut(
            id=str(row.id),
            actor_user_id=str(row.actor_user_id) if row.actor_user_id else None,
            target_user_id=str(row.target_user_id) if row.target_user_id else None,
            action=row.action,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            meta=row.meta or {},
            ip_address=row.ip_address,
            created_at=row.created_at,
        )
        for row in rows
    ]
