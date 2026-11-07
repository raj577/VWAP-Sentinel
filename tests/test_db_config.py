"""Database configuration tests: Neon placeholder resolution and encoding."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.core.config import Settings

TEMPLATE = (
    "postgresql+psycopg://neondb_owner:${NEON_DB_PASSWORD}"
    "@ep-example-pooler.us-east-2.aws.neon.tech/neondb"
    "?sslmode=require&channel_binding=require"
)


def test_neon_placeholder_is_resolved_and_url_encoded() -> None:
    settings = Settings(
        database_url=TEMPLATE,
        neon_db_password="p@ss:w/ord",
        db_pool_size=3,
        db_max_overflow=2,
        database_require_ssl=True,
    )
    assert "${NEON_DB_PASSWORD}" not in settings.database_url
    assert "p%40ss%3Aw%2Ford" in settings.database_url
    assert "sslmode=require" in settings.database_url
    assert "channel_binding=require" in settings.database_url


def test_escaped_placeholder_from_compose_is_resolved() -> None:
    settings = Settings(
        database_url=TEMPLATE.replace("${NEON_DB_PASSWORD}", "$${NEON_DB_PASSWORD}"),
        neon_db_password="secret",
    )
    assert "NEON_DB_PASSWORD" not in settings.database_url
    assert "secret" in settings.database_url


def test_missing_neon_password_raises_clear_error() -> None:
    with pytest.raises(ValidationError) as error:
        Settings(database_url=TEMPLATE, neon_db_password="")
    assert "NEON_DB_PASSWORD" in str(error.value)


def test_literal_database_urls_are_untouched() -> None:
    literal = "postgresql+psycopg://scanner:local@postgres:5432/avwap_scanner"
    settings = Settings(database_url=literal)
    assert settings.database_url == literal
    assert settings.db_pool_size == 5
    assert settings.db_max_overflow == 2
