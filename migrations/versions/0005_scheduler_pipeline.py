"""Phase 4: scheduler settings, pipeline jobs and per-instrument logs.

Revision ID: 0005_scheduler_pipeline
Revises: 0004_scan_failed_count
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_scheduler_pipeline"
down_revision: Union[str, None] = "0004_scan_failed_count"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scheduler_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scheduler_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "scan_interval_minutes", sa.Integer(), nullable=False, server_default="56"
        ),
        sa.Column(
            "market_open_time", sa.String(length=5), nullable=False, server_default="09:15"
        ),
        sa.Column(
            "market_close_time", sa.String(length=5), nullable=False, server_default="15:30"
        ),
        sa.Column(
            "timezone", sa.String(length=64), nullable=False, server_default="Asia/Kolkata"
        ),
        sa.Column(
            "allow_manual_outside_market_hours",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column("market_holidays", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_by", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "pipeline_jobs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column(
            "job_type", sa.String(length=24), nullable=False, server_default="FULL_PIPELINE"
        ),
        sa.Column(
            "trigger_source", sa.String(length=16), nullable=False, server_default="MANUAL"
        ),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="PENDING"),
        sa.Column("stage", sa.String(length=32), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Numeric(12, 3), nullable=True),
        sa.Column("total_instruments", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_instruments", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_instruments", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("candles_fetched", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("candles_inserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("candles_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("cancellation_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("owner", sa.String(length=64), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ingestion_job_id", sa.BigInteger(), nullable=True),
        sa.Column("scan_run_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["ingestion_job_id"],
            ["ingestion_jobs.id"],
            name="fk_pipeline_jobs_ingestion_job_id_ingestion_jobs",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["scan_run_id"],
            ["scan_runs.id"],
            name="fk_pipeline_jobs_scan_run_id_scan_runs",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_pipeline_jobs_job_type", "pipeline_jobs", ["job_type"])
    op.create_index("ix_pipeline_jobs_trigger_source", "pipeline_jobs", ["trigger_source"])
    op.create_index("ix_pipeline_jobs_status", "pipeline_jobs", ["status"])
    op.create_index("ix_pipeline_jobs_started_at", "pipeline_jobs", ["started_at"])

    op.create_table(
        "pipeline_job_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("job_id", sa.BigInteger(), nullable=False),
        sa.Column("instrument_id", sa.BigInteger(), nullable=True),
        sa.Column("symbol", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("candles_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["pipeline_jobs.id"],
            name="fk_pipeline_job_logs_job_id_pipeline_jobs",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["instrument_id"],
            ["instruments.id"],
            name="fk_pipeline_job_logs_instrument_id_instruments",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_pipeline_job_logs_job_id", "pipeline_job_logs", ["job_id"])
    op.create_index("ix_pipeline_job_logs_symbol", "pipeline_job_logs", ["symbol"])
    op.create_index(
        "ix_pipeline_job_logs_job_status", "pipeline_job_logs", ["job_id", "status"]
    )

    op.add_column(
        "ingestion_jobs", sa.Column("pipeline_job_id", sa.BigInteger(), nullable=True)
    )
    op.create_foreign_key(
        "fk_ingestion_jobs_pipeline_job_id_pipeline_jobs",
        "ingestion_jobs",
        "pipeline_jobs",
        ["pipeline_job_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "scan_runs", sa.Column("pipeline_job_id", sa.BigInteger(), nullable=True)
    )
    op.add_column(
        "scan_runs", sa.Column("ingestion_job_id", sa.BigInteger(), nullable=True)
    )
    op.create_foreign_key(
        "fk_scan_runs_pipeline_job_id_pipeline_jobs",
        "scan_runs",
        "pipeline_jobs",
        ["pipeline_job_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_scan_runs_ingestion_job_id_ingestion_jobs",
        "scan_runs",
        "ingestion_jobs",
        ["ingestion_job_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_scan_runs_ingestion_job_id_ingestion_jobs", "scan_runs", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_scan_runs_pipeline_job_id_pipeline_jobs", "scan_runs", type_="foreignkey"
    )
    op.drop_column("scan_runs", "ingestion_job_id")
    op.drop_column("scan_runs", "pipeline_job_id")

    op.drop_constraint(
        "fk_ingestion_jobs_pipeline_job_id_pipeline_jobs",
        "ingestion_jobs",
        type_="foreignkey",
    )
    op.drop_column("ingestion_jobs", "pipeline_job_id")

    op.drop_index("ix_pipeline_job_logs_job_status", table_name="pipeline_job_logs")
    op.drop_index("ix_pipeline_job_logs_symbol", table_name="pipeline_job_logs")
    op.drop_index("ix_pipeline_job_logs_job_id", table_name="pipeline_job_logs")
    op.drop_table("pipeline_job_logs")

    op.drop_index("ix_pipeline_jobs_started_at", table_name="pipeline_jobs")
    op.drop_index("ix_pipeline_jobs_status", table_name="pipeline_jobs")
    op.drop_index("ix_pipeline_jobs_trigger_source", table_name="pipeline_jobs")
    op.drop_index("ix_pipeline_jobs_job_type", table_name="pipeline_jobs")
    op.drop_table("pipeline_jobs")

    op.drop_table("scheduler_settings")
