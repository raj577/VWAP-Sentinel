"""Database engine and session management.

The engine is created lazily so importing the API never requires a reachable
database (tests, container build, OpenAPI generation). PostgreSQL is the
authoritative store; SQLite is supported only so tests can run offline.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.core.config import get_settings

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def _engine_kwargs(url: str, settings) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"pool_pre_ping": True, "future": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs["pool_size"] = max(int(settings.db_pool_size), 1)
        kwargs["max_overflow"] = max(int(settings.db_max_overflow), 0)
        kwargs["pool_timeout"] = max(int(settings.db_pool_timeout), 1)
        kwargs["pool_recycle"] = max(int(settings.db_pool_recycle), 1)
        connect_args: dict[str, Any] = {"connect_timeout": 5}
        if settings.database_require_ssl and "sslmode=" not in url:
            connect_args["sslmode"] = "require"
        kwargs["connect_args"] = connect_args
    return kwargs


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            echo=settings.database_echo,
            **_engine_kwargs(settings.database_url, settings),
        )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_engine(), autoflush=False, expire_on_commit=False
        )
    return _session_factory


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a request-scoped session."""

    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def reset_engine() -> None:
    """Dispose and forget the cached engine. Used by tests and workers."""

    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None
