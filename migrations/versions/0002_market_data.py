"""Phase 2: instruments, market candles and ingestion job tracking.

Revision ID: 0002_market_data
Revises: 0001_baseline
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_market_data"
down_revision: Union[str, None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "instruments",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("fyers_symbol", sa.String(length=64), nullable=False),
        sa.Column("underlying_symbol", sa.String(length=64), nullable=False),
        sa.Column("exchange", sa.String(length=16), nullable=False, server_default="NSE"),
        sa.Column(
            "instrument_type", sa.String(length=16), nullable=False, server_default="FUT"
        ),
        sa.Column("expiry_date", sa.Date(), nullable=False),
        sa.Column("lot_size", sa.Numeric(18, 4), nullable=True),
        sa.Column("tick_size", sa.Numeric(18, 6), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("first_available_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_instruments_fyers_symbol", "instruments", ["fyers_symbol"], unique=True
    )
    op.create_index(
        "ix_instruments_underlying_symbol", "instruments", ["underlying_symbol"]
    )
    op.create_index("ix_instruments_expiry_date", "instruments", ["expiry_date"])
    op.create_index("ix_instruments_is_active", "instruments", ["is_active"])

    op.create_table(
        "market_candles",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("instrument_id", sa.BigInteger(), nullable=False),
        sa.Column("timeframe", sa.String(length=8), nullable=False, server_default="60"),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(18, 6), nullable=False),
        sa.Column("high", sa.Numeric(18, 6), nullable=False),
        sa.Column("low", sa.Numeric(18, 6), nullable=False),
        sa.Column("close", sa.Numeric(18, 6), nullable=False),
        sa.Column("volume", sa.Numeric(24, 4), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["instrument_id"],
            ["instruments.id"],
            name="fk_market_candles_instrument_id_instruments",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "instrument_id",
            "timeframe",
            "timestamp",
            name="uq_market_candles_instrument_timeframe_timestamp",
        ),
    )
    op.create_index(
        "ix_market_candles_instrument_id", "market_candles", ["instrument_id"]
    )
    op.create_index("ix_market_candles_timestamp", "market_candles", ["timestamp"])
    op.create_index(
        "ix_market_candles_instrument_id_timestamp",
        "market_candles",
        ["instrument_id", "timestamp"],
    )
    op.create_index(
        "ix_market_candles_timeframe_timestamp",
        "market_candles",
        ["timeframe", "timestamp"],
    )

    op.create_table(
        "ingestion_jobs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("job_type", sa.String(length=32), nullable=False, server_default="MARKET_DATA"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="PENDING"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_instruments", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("successful_instruments", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_instruments", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("candles_inserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("candles_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("triggered_by", sa.String(length=64), nullable=False, server_default="system"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_ingestion_jobs_status", "ingestion_jobs", ["status"])
    op.create_index(
        "ix_ingestion_jobs_started_at", "ingestion_jobs", ["started_at"]
    )

    op.create_table(
        "ingestion_job_items",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("job_id", sa.BigInteger(), nullable=False),
        sa.Column("instrument_id", sa.BigInteger(), nullable=True),
        sa.Column("symbol", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("candles_seen", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("candles_inserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("candles_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["ingestion_jobs.id"],
            name="fk_ingestion_job_items_job_id_ingestion_jobs",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["instrument_id"],
            ["instruments.id"],
            name="fk_ingestion_job_items_instrument_id_instruments",
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("job_id", "symbol", name="uq_ingestion_job_items_job_symbol"),
    )
    op.create_index(
        "ix_ingestion_job_items_job_id", "ingestion_job_items", ["job_id"]
    )
    op.create_index(
        "ix_ingestion_job_items_symbol", "ingestion_job_items", ["symbol"]
    )


def downgrade() -> None:
    op.drop_index("ix_ingestion_job_items_symbol", table_name="ingestion_job_items")
    op.drop_index("ix_ingestion_job_items_job_id", table_name="ingestion_job_items")
    op.drop_table("ingestion_job_items")

    op.drop_index("ix_ingestion_jobs_started_at", table_name="ingestion_jobs")
    op.drop_index("ix_ingestion_jobs_status", table_name="ingestion_jobs")
    op.drop_table("ingestion_jobs")

    op.drop_index("ix_market_candles_timeframe_timestamp", table_name="market_candles")
    op.drop_index(
        "ix_market_candles_instrument_id_timestamp", table_name="market_candles"
    )
    op.drop_index("ix_market_candles_timestamp", table_name="market_candles")
    op.drop_index("ix_market_candles_instrument_id", table_name="market_candles")
    op.drop_table("market_candles")

    op.drop_index("ix_instruments_is_active", table_name="instruments")
    op.drop_index("ix_instruments_expiry_date", table_name="instruments")
    op.drop_index("ix_instruments_underlying_symbol", table_name="instruments")
    op.drop_index("ix_instruments_fyers_symbol", table_name="instruments")
    op.drop_table("instruments")
