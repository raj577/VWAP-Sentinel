"""Create the initial SUPER_ADMIN once.

Usage:
    python -m backend.cli.bootstrap_admin
    python -m backend.cli.bootstrap_admin --email you@example.com --password '...'

Reads SUPER_ADMIN_EMAIL / SUPER_ADMIN_PASSWORD when flags are omitted. Refuses
to run if a SUPER_ADMIN already exists.
"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import select

from backend.core.config import get_settings
from backend.core.time import utcnow
from backend.db.models import Role, User, UserRole
from backend.db.session import get_session_factory
from backend.services.security import (
    ROLE_SUPER_ADMIN,
    STATUS_ACTIVE,
    hash_password,
    normalize_email,
    record_audit,
    validate_password,
)


def main(argv: list[str] | None = None) -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Bootstrap the first SUPER_ADMIN")
    parser.add_argument("--email", default=settings.super_admin_email)
    parser.add_argument("--password", default=settings.super_admin_password)
    args = parser.parse_args(argv)

    from email_validator import EmailNotValidError, validate_email

    raw_email = (args.email or "").strip()
    try:
        email = validate_email(raw_email, check_deliverability=False).normalized.lower()
    except EmailNotValidError as exc:
        print(f"Invalid email: {exc}", file=sys.stderr)
        return 2
    password = args.password or ""
    if not email or not password:
        print(
            "SUPER_ADMIN_EMAIL and SUPER_ADMIN_PASSWORD (or --email/--password) are required.",
            file=sys.stderr,
        )
        return 2

    try:
        validate_password(password)
    except ValueError as exc:
        print(f"Weak password: {exc}", file=sys.stderr)
        return 2

    factory = get_session_factory()
    db = factory()
    try:
        role = db.scalar(select(Role).where(Role.name == ROLE_SUPER_ADMIN))
        if role is None:
            print(
                "Roles are missing. Run `alembic upgrade head` first.",
                file=sys.stderr,
            )
            return 3

        existing_super = db.scalar(
            select(User)
            .join(UserRole, UserRole.user_id == User.id)
            .where(UserRole.role_id == role.id)
            .limit(1)
        )
        if existing_super is not None:
            print("A SUPER_ADMIN already exists; bootstrap skipped.")
            return 0

        if db.scalar(select(User).where(User.email == email)) is not None:
            print("Email already belongs to another account.", file=sys.stderr)
            return 4

        user = User(
            full_name="Platform Super Admin",
            email=email,
            password_hash=hash_password(password),
            account_status=STATUS_ACTIVE,
            email_verified_at=utcnow(),
        )
        db.add(user)
        db.flush()
        db.add(UserRole(user_id=user.id, role_id=role.id))
        record_audit(
            db,
            action="super_admin.bootstrapped",
            target_user_id=user.id,
            entity_type="user",
            entity_id=str(user.id),
        )
        db.commit()
        print(f"SUPER_ADMIN created: {email}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
