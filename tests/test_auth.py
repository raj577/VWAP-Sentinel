"""Phase 5 tests: auth flows, RBAC, sessions, audit, bootstrap and limits."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from backend.cli import bootstrap_admin
from backend.core.config import Settings, get_settings
from backend.core.time import utcnow
from backend.db.base import Base
from backend.db.models import (
    AuditLog,
    EmailVerificationToken,
    Role,
    User,
    UserRole,
)
from backend.db.session import get_db, get_engine, reset_engine
from backend.main import app
from backend.services.rate_limit import reset_rate_limits
from backend.services.security import (
    ROLE_ADMIN,
    ROLE_CUSTOMER,
    ROLE_SUPER_ADMIN,
    STATUS_ACTIVE,
    STATUS_SUSPENDED,
    create_access_token,
    hash_password,
    hash_token,
    normalize_email,
)

PASSWORD = "Str0ng!Passw0rd"
NEW_PASSWORD = "N3w!Passw0rdX"


def _factory(tmp_path) -> sessionmaker[Session]:
    engine = create_engine(
        f"sqlite+pysqlite:///{tmp_path / 'auth.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _seed_roles(factory: sessionmaker[Session]) -> None:
    with factory() as db:
        if db.scalar(select(func.count()).select_from(Role)):
            return
        for name in (ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_CUSTOMER):
            db.add(Role(name=name))
        db.commit()


@pytest.fixture()
def client(tmp_path, monkeypatch) -> Iterator[TestClient]:
    factory = _factory(tmp_path)
    _seed_roles(factory)
    reset_rate_limits()

    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")
    monkeypatch.setenv("AUTH_RATE_LIMIT_PER_MINUTE", "1000")
    monkeypatch.setenv("LOGIN_RATE_LIMIT_PER_MINUTE", "1000")
    monkeypatch.setenv("AUTH_DEV_EXPOSE_TOKENS", "true")
    get_settings.cache_clear()

    def override_db() -> Iterator[Session]:
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        test_client.factory = factory  # type: ignore[attr-defined]
        yield test_client
    app.dependency_overrides.clear()
    get_settings.cache_clear()
    reset_rate_limits()


def _register(
    client: TestClient, email: str = "user@example.com", password: str = PASSWORD
) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Test User", "email": email, "password": password},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _verify(client: TestClient, token: str) -> None:
    response = client.post("/api/v1/auth/verify-email", json={"token": token})
    assert response.status_code == 200, response.text


def _activate(client: TestClient, email: str = "user@example.com") -> dict:
    registration = _register(client, email)
    _verify(client, registration["dev_token"])
    login = client.post(
        "/api/v1/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert login.status_code == 200, login.text
    return login.json()


def _make_user(
    factory: sessionmaker[Session],
    email: str,
    role_name: str,
    password: str = PASSWORD,
) -> uuid.UUID:
    with factory() as db:
        role = db.scalar(select(Role).where(Role.name == role_name))
        user = User(
            full_name=f"{role_name.title()} User",
            email=normalize_email(email),
            password_hash=hash_password(password),
            account_status=STATUS_ACTIVE,
            email_verified_at=utcnow(),
        )
        db.add(user)
        db.flush()
        db.add(UserRole(user_id=user.id, role_id=role.id))
        db.commit()
        return user.id


def _login(client: TestClient, email: str = "user@example.com", password: str = PASSWORD) -> dict:
    response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200, response.text
    return response.json()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------- registration
def test_registration_hashes_password_and_assigns_customer(client: TestClient) -> None:
    body = _register(client)
    assert body["dev_token"]

    with client.factory() as db:  # type: ignore[attr-defined]
        user = db.scalar(select(User).where(User.email == "user@example.com"))
        assert user is not None
        assert user.password_hash != PASSWORD
        assert user.account_status == "PENDING_VERIFICATION"
        roles = set(
            db.scalars(
                select(Role.name)
                .join(UserRole, UserRole.role_id == Role.id)
                .where(UserRole.user_id == user.id)
            )
        )
        assert roles == {ROLE_CUSTOMER}
        assert db.scalar(select(func.count()).select_from(AuditLog)) >= 1


def test_duplicate_email_and_weak_password_are_rejected(client: TestClient) -> None:
    _register(client)
    duplicate = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Other", "email": "USER@example.com", "password": PASSWORD},
    )
    assert duplicate.status_code == 409

    weak = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Other", "email": "weak@example.com", "password": "short"},
    )
    assert weak.status_code == 422


def test_verification_is_single_use(client: TestClient) -> None:
    token = _register(client)["dev_token"]
    _verify(client, token)
    reuse = client.post("/api/v1/auth/verify-email", json={"token": token})
    assert reuse.status_code == 400

    with client.factory() as db:  # type: ignore[attr-defined]
        user = db.scalar(select(User).where(User.email == "user@example.com"))
        assert user.account_status == STATUS_ACTIVE
        assert user.email_verified_at is not None


def test_expired_verification_token_is_rejected(client: TestClient) -> None:
    _register(client)
    with client.factory() as db:  # type: ignore[attr-defined]
        record = db.scalar(select(EmailVerificationToken))
        record.expires_at = utcnow() - timedelta(minutes=1)
        db.commit()
    expired = client.post(
        "/api/v1/auth/verify-email", json={"token": "x" * 30}
    )
    assert expired.status_code == 400


# ---------------------------------------------------------------------- login
def test_login_me_and_cookies(client: TestClient) -> None:
    tokens = _activate(client)
    assert tokens["access_token"]
    assert client.cookies.get("access_token")
    assert client.cookies.get("refresh_token")
    assert client.cookies.get("csrf_token")

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "user@example.com"
    assert me.json()["roles"] == [ROLE_CUSTOMER]

    bearer = client.get("/api/v1/auth/me", headers=_auth(tokens["access_token"]))
    assert bearer.status_code == 200


def test_login_rejects_bad_unverified_and_suspended(client: TestClient) -> None:
    registration = _register(client)
    unverified = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": PASSWORD},
    )
    assert unverified.status_code == 403

    _verify(client, registration["dev_token"])
    bad = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "Wrong!Pass123"},
    )
    assert bad.status_code == 401

    with client.factory() as db:  # type: ignore[attr-defined]
        user = db.scalar(select(User).where(User.email == "user@example.com"))
        user.account_status = STATUS_SUSPENDED
        db.commit()

    suspended = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": PASSWORD},
    )
    assert suspended.status_code == 403


def test_invalid_and_expired_jwt_are_rejected(client: TestClient) -> None:
    assert client.get("/api/v1/auth/me", headers=_auth("not-a-jwt")).status_code == 401

    settings = get_settings()
    now = utcnow()
    expired = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "jti": "x",
            "iat": int((now - timedelta(hours=2)).timestamp()),
            "exp": int((now - timedelta(hours=1)).timestamp()),
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
        },
        settings.auth_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    assert client.get("/api/v1/auth/me", headers=_auth(expired)).status_code == 401

    wrong_secret = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "jti": "x",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=5)).timestamp()),
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
        },
        "wrong-secret-but-long-enough-for-warning-free-hmac",
        algorithm=settings.jwt_algorithm,
    )
    assert (
        client.get("/api/v1/auth/me", headers=_auth(wrong_secret)).status_code == 401
    )


# ---------------------------------------------------------------- refresh/CSRF
def test_refresh_rotation_and_reuse_detection(client: TestClient) -> None:
    tokens = _activate(client)
    csrf = client.cookies.get("csrf_token")
    rotated = client.post(
        "/api/v1/auth/refresh",
        headers={"X-CSRF-Token": csrf},
        json={},
    )
    assert rotated.status_code == 200, rotated.text
    new_tokens = rotated.json()
    assert new_tokens["refresh_token"] != tokens["refresh_token"]

    # Old refresh token reuse is detected and revokes the family.
    reuse = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert reuse.status_code == 401

    family_dead = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": new_tokens["refresh_token"]}
    )
    assert family_dead.status_code == 401


def test_csrf_required_for_cookie_mutations(client: TestClient) -> None:
    _activate(client)
    missing = client.post("/api/v1/auth/logout", json={})
    assert missing.status_code == 403

    csrf = client.cookies.get("csrf_token")
    allowed = client.post(
        "/api/v1/auth/logout", headers={"X-CSRF-Token": csrf}, json={}
    )
    assert allowed.status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 401


# ------------------------------------------------------------------- sessions
def test_sessions_list_revoke_and_ownership(client: TestClient) -> None:
    first = _activate(client)
    second = _login(client)

    listing = client.get(
        "/api/v1/auth/sessions", headers=_auth(second["access_token"])
    )
    assert listing.status_code == 200
    sessions = listing.json()["sessions"]
    assert len(sessions) == 2

    target = next(session for session in sessions if not session["current"])
    revoked = client.delete(
        f"/api/v1/auth/sessions/{target['id']}",
        headers=_auth(second["access_token"]),
    )
    assert revoked.status_code == 200

    after = client.get(
        "/api/v1/auth/sessions", headers=_auth(second["access_token"])
    ).json()["sessions"]
    assert len(after) == 1

    # Another user cannot revoke this session.
    other = _activate(client, "other@example.com")
    forbidden = client.delete(
        f"/api/v1/auth/sessions/{after[0]['id']}",
        headers=_auth(other["access_token"]),
    )
    assert forbidden.status_code == 404


def test_logout_all_revokes_every_session(client: TestClient) -> None:
    first = _activate(client)
    second = _login(client)

    response = client.post(
        "/api/v1/auth/logout-all",
        headers={**_auth(second["access_token"]), "X-CSRF-Token": client.cookies.get("csrf_token")},
        json={},
    )
    assert response.status_code == 200

    refresh = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]}
    )
    assert refresh.status_code == 401


# ------------------------------------------------------------------ passwords
def test_password_reset_flow_and_single_use(client: TestClient) -> None:
    _activate(client)
    forgot = client.post(
        "/api/v1/auth/forgot-password", json={"email": "user@example.com"}
    )
    assert forgot.status_code == 200
    token = forgot.json()["dev_token"]
    assert token

    reset = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": NEW_PASSWORD},
    )
    assert reset.status_code == 200

    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": "user@example.com", "password": PASSWORD},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": "user@example.com", "password": NEW_PASSWORD},
        ).status_code
        == 200
    )

    reuse = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": NEW_PASSWORD},
    )
    assert reuse.status_code == 400


def test_change_password_revokes_other_sessions(client: TestClient) -> None:
    tokens = _activate(client)
    _login(client)  # second session

    response = client.post(
        "/api/v1/auth/change-password",
        headers={
            **_auth(tokens["access_token"]),
            "X-CSRF-Token": client.cookies.get("csrf_token"),
        },
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
    )
    assert response.status_code == 200

    sessions = client.get(
        "/api/v1/auth/sessions", headers=_auth(tokens["access_token"])
    ).json()["sessions"]
    assert len(sessions) <= 1

    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": "user@example.com", "password": NEW_PASSWORD},
        ).status_code
        == 200
    )


# ------------------------------------------------------------------------ RBAC
def test_rbac_admin_user_management(client: TestClient) -> None:
    customer_tokens = _activate(client, "customer@example.com")
    admin_id = _make_user(client.factory, "admin@example.com", ROLE_ADMIN)  # type: ignore[attr-defined]
    super_id = _make_user(client.factory, "super@example.com", ROLE_SUPER_ADMIN)  # type: ignore[attr-defined]
    admin = _login(client, "admin@example.com")
    super_admin = _login(client, "super@example.com")

    assert (
        client.get(
            "/api/v1/admin/users", headers=_auth(customer_tokens["access_token"])
        ).status_code
        == 403
    )

    listing = client.get(
        "/api/v1/admin/users",
        headers=_auth(admin["access_token"]),
        params={"search": "customer"},
    )
    assert listing.status_code == 200
    assert listing.json()["total"] == 1

    # Admin cannot assign ADMIN, cannot modify admins, cannot self-edit.
    customer_id = listing.json()["items"][0]["id"]
    promote = client.patch(
        f"/api/v1/admin/users/{customer_id}/role",
        headers=_auth(admin["access_token"]),
        json={"role": ROLE_ADMIN},
    )
    assert promote.status_code == 403

    touch_admin = client.patch(
        f"/api/v1/admin/users/{admin_id}/status",
        headers=_auth(admin["access_token"]),
        json={"account_status": STATUS_SUSPENDED},
    )
    assert touch_admin.status_code == 403

    self_change = client.patch(
        f"/api/v1/admin/users/{admin_id}/role",
        headers=_auth(admin["access_token"]),
        json={"role": ROLE_CUSTOMER},
    )
    assert self_change.status_code == 403

    # SUPER_ADMIN can promote a customer to ADMIN.
    promoted = client.patch(
        f"/api/v1/admin/users/{customer_id}/role",
        headers=_auth(super_admin["access_token"]),
        json={"role": ROLE_ADMIN},
    )
    assert promoted.status_code == 200
    assert ROLE_ADMIN in promoted.json()["roles"]

    # SUPER_ADMIN cannot be created through the API.
    bootstrap_attempt = client.patch(
        f"/api/v1/admin/users/{customer_id}/role",
        headers=_auth(super_admin["access_token"]),
        json={"role": ROLE_SUPER_ADMIN},
    )
    assert bootstrap_attempt.status_code == 403


def test_super_admin_audit_access(client: TestClient) -> None:
    _activate(client)
    super_id = _make_user(client.factory, "super@example.com", ROLE_SUPER_ADMIN)  # type: ignore[attr-defined]
    super_tokens = _login(client, "super@example.com")

    response = client.get(
        "/api/v1/admin/audit-logs", headers=_auth(super_tokens["access_token"])
    )
    assert response.status_code == 200
    actions = {row["action"] for row in response.json()}
    assert "user.registered" in actions
    assert "login.succeeded" in actions


# --------------------------------------------------------------------- limits
def test_registration_rate_limiting(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("AUTH_RATE_LIMIT_PER_MINUTE", "2")
    get_settings.cache_clear()
    reset_rate_limits()

    assert (
        client.post(
            "/api/v1/auth/register",
            json={"full_name": "One", "email": "one@example.com", "password": PASSWORD},
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/auth/register",
            json={"full_name": "Two", "email": "two@example.com", "password": PASSWORD},
        ).status_code
        == 201
    )
    limited = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Three", "email": "three@example.com", "password": PASSWORD},
    )
    assert limited.status_code == 429
    assert limited.headers.get("Retry-After")


def test_scanner_endpoints_require_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/scanner/current").status_code == 401


# ------------------------------------------------------------------ bootstrap
def test_bootstrap_creates_one_super_admin(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{tmp_path / 'bootstrap.db'}")
    get_settings.cache_clear()
    reset_engine()
    try:
        Base.metadata.create_all(get_engine())
        factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
        _seed_roles(factory)

        code = bootstrap_admin.main(
            ["--email", "root@example.com", "--password", PASSWORD]
        )
        assert code == 0
        again = bootstrap_admin.main(
            ["--email", "second@example.com", "--password", PASSWORD]
        )
        assert again == 0

        with factory() as db:
            super_count = db.scalar(
                select(func.count())
                .select_from(UserRole)
                .join(Role, Role.id == UserRole.role_id)
                .where(Role.name == ROLE_SUPER_ADMIN)
            )
            assert super_count == 1
            audit = db.scalar(
                select(AuditLog).where(
                    AuditLog.action == "super_admin.bootstrapped"
                )
            )
            assert audit is not None
    finally:
        reset_engine()
        get_settings.cache_clear()

def test_profile_update(client: TestClient) -> None:
    tokens = _activate(client)
    response = client.patch(
        "/api/v1/auth/me",
        headers=_auth(tokens["access_token"]),
        json={"full_name": "Updated Name"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["full_name"] == "Updated Name"
