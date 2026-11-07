"""Phase 3: immutable scan runs, results and preserved pattern candles.

Revision ID: 0003_scan_snapshots
Revises: 0002_market_data
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_scan_snapshots"
down_revision: Union[str, None] = "0002_market_data"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scan_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("scan_type", sa.String(length=16), nullable=False, server_default="MANUAL"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="RUNNING"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("instruments_scanned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("matches_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("config_version", sa.String(length=16), nullable=False, server_default=""),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("data_freshness_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("triggered_by", sa.String(length=64), nullable=False, server_default="admin"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_scan_runs_status", "scan_runs", ["status"])
    op.create_index("ix_scan_runs_completed_at", "scan_runs", ["completed_at"])

    op.create_table(
        "scan_results",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("scan_run_id", sa.BigInteger(), nullable=False),
        sa.Column("instrument_id", sa.BigInteger(), nullable=True),
        sa.Column("symbol", sa.String(length=64), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=False),
        sa.Column("last_price", sa.Numeric(18, 6), nullable=False),
        sa.Column("avwap", sa.Numeric(18, 6), nullable=False),
        sa.Column("session_vwap", sa.Numeric(18, 6), nullable=True),
        sa.Column("distance_pct", sa.Numeric(12, 6), nullable=False),
        sa.Column("candle_count", sa.Integer(), nullable=False),
        sa.Column("avg_body_ratio", sa.Numeric(8, 6), nullable=False),
        sa.Column("max_body_ratio", sa.Numeric(8, 6), nullable=False),
        sa.Column("classification", sa.String(length=32), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("pattern_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pattern_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latest_atr", sa.Numeric(18, 6), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["scan_run_id"],
            ["scan_runs.id"],
            name="fk_scan_results_scan_run_id_scan_runs",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["instrument_id"],
            ["instruments.id"],
            name="fk_scan_results_instrument_id_instruments",
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("scan_run_id", "symbol", name="uq_scan_results_run_symbol"),
    )
    op.create_index("ix_scan_results_scan_run_id", "scan_results", ["scan_run_id"])
    op.create_index("ix_scan_results_symbol", "scan_results", ["symbol"])
    op.create_index(
        "ix_scan_results_run_classification",
        "scan_results",
        ["scan_run_id", "classification"],
    )
    op.create_index(
        "ix_scan_results_run_distance",
        "scan_results",
        ["scan_run_id", "distance_pct"],
    )

    op.create_table(
        "scan_result_candles",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("scan_result_id", sa.BigInteger(), nullable=False),
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
            ["scan_result_id"],
            ["scan_results.id"],
            name="fk_scan_result_candles_scan_result_id_scan_results",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "scan_result_id", "timestamp", name="uq_scan_result_candles_result_ts"
        ),
    )
    op.create_index(
        "ix_scan_result_candles_scan_result_id",
        "scan_result_candles",
        ["scan_result_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_scan_result_candles_scan_result_id", table_name="scan_result_candles"
    )
    op.drop_table("scan_result_candles")

    op.drop_index("ix_scan_results_run_distance", table_name="scan_results")
    op.drop_index("ix_scan_results_run_classification", table_name="scan_results")
    op.drop_index("ix_scan_results_symbol", table_name="scan_results")
    op.drop_index("ix_scan_results_scan_run_id", table_name="scan_results")
    op.drop_table("scan_results")

    op.drop_index("ix_scan_runs_completed_at", table_name="scan_runs")
    op.drop_index("ix_scan_runs_status", table_name="scan_runs")
    op.drop_table("scan_runs")
