"""SQLAlchemy models for Phase 2: futures instruments, candles and jobs."""

from __future__ import annotations

from datetime import date, datetime
import uuid
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base, TimestampMixin

BigIntPK = BigInteger().with_variant(Integer, "sqlite")


class Instrument(Base, TimestampMixin):
    """One NSE futures contract, keyed by its exact FYERS trading symbol."""

    __tablename__ = "instruments"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    fyers_symbol: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    underlying_symbol: Mapped[str] = mapped_column(String(64), index=True)
    exchange: Mapped[str] = mapped_column(String(16), default="NSE", nullable=False)
    instrument_type: Mapped[str] = mapped_column(
        String(16), default="FUT", nullable=False
    )
    expiry_date: Mapped[date] = mapped_column(Date, index=True)
    lot_size: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    tick_size: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    first_available_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    candles: Mapped[list[MarketCandle]] = relationship(
        back_populates="instrument", cascade="all, delete-orphan"
    )


class MarketCandle(Base, TimestampMixin):
    """Completed 1-hour candle. ``timestamp`` is the candle open time in UTC."""

    __tablename__ = "market_candles"
    __table_args__ = (
        UniqueConstraint(
            "instrument_id",
            "timeframe",
            "timestamp",
            name="uq_market_candles_instrument_timeframe_timestamp",
        ),
        Index("ix_market_candles_instrument_id_timestamp", "instrument_id", "timestamp"),
        Index("ix_market_candles_timeframe_timestamp", "timeframe", "timestamp"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    instrument_id: Mapped[int] = mapped_column(
        ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False, default="60")
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    open: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    volume: Mapped[Decimal] = mapped_column(Numeric(24, 4), nullable=False)

    instrument: Mapped[Instrument] = relationship(back_populates="candles")


class IngestionJob(Base, TimestampMixin):
    """One market-data ingestion execution."""

    __tablename__ = "ingestion_jobs"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    job_type: Mapped[str] = mapped_column(
        String(32), default="MARKET_DATA", nullable=False
    )
    status: Mapped[str] = mapped_column(String(24), default="PENDING", index=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    total_instruments: Mapped[int] = mapped_column(Integer, default=0)
    successful_instruments: Mapped[int] = mapped_column(Integer, default=0)
    failed_instruments: Mapped[int] = mapped_column(Integer, default=0)
    candles_inserted: Mapped[int] = mapped_column(Integer, default=0)
    candles_updated: Mapped[int] = mapped_column(Integer, default=0)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    triggered_by: Mapped[str] = mapped_column(String(64), default="system")
    pipeline_job_id: Mapped[int | None] = mapped_column(
        ForeignKey("pipeline_jobs.id", ondelete="SET NULL"), nullable=True
    )

    items: Mapped[list[IngestionJobItem]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )



class IngestionJobItem(Base, TimestampMixin):
    """Per-instrument outcome inside an ingestion job."""

    __tablename__ = "ingestion_job_items"
    __table_args__ = (
        UniqueConstraint("job_id", "symbol", name="uq_ingestion_job_items_job_symbol"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("ingestion_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    instrument_id: Mapped[int | None] = mapped_column(
        ForeignKey("instruments.id", ondelete="SET NULL"), nullable=True
    )
    symbol: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    candles_seen: Mapped[int] = mapped_column(Integer, default=0)
    candles_inserted: Mapped[int] = mapped_column(Integer, default=0)
    candles_updated: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    job: Mapped[IngestionJob] = relationship(back_populates="items")


class ScanRun(Base, TimestampMixin):
    """One immutable scanner execution over stored market data."""

    __tablename__ = "scan_runs"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    scan_type: Mapped[str] = mapped_column(
        String(16), default="MANUAL", nullable=False
    )
    status: Mapped[str] = mapped_column(String(24), default="RUNNING", index=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    instruments_scanned: Mapped[int] = mapped_column(Integer, default=0)
    failed_instruments: Mapped[int] = mapped_column(Integer, default=0)
    matches_count: Mapped[int] = mapped_column(Integer, default=0)
    config_version: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    data_freshness_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    triggered_by: Mapped[str] = mapped_column(String(64), default="admin")
    pipeline_job_id: Mapped[int | None] = mapped_column(
        ForeignKey("pipeline_jobs.id", ondelete="SET NULL"), nullable=True
    )
    ingestion_job_id: Mapped[int | None] = mapped_column(
        ForeignKey("ingestion_jobs.id", ondelete="SET NULL"), nullable=True
    )

    results: Mapped[list[ScanResult]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class ScanResult(Base, TimestampMixin):
    """Frozen snapshot of one matching contract inside a scan run."""

    __tablename__ = "scan_results"
    __table_args__ = (
        UniqueConstraint("scan_run_id", "symbol", name="uq_scan_results_run_symbol"),
        Index("ix_scan_results_run_classification", "scan_run_id", "classification"),
        Index("ix_scan_results_run_distance", "scan_run_id", "distance_pct"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    scan_run_id: Mapped[int] = mapped_column(
        ForeignKey("scan_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    instrument_id: Mapped[int | None] = mapped_column(
        ForeignKey("instruments.id", ondelete="SET NULL"), nullable=True
    )
    symbol: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    last_price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    avwap: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    session_vwap: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    distance_pct: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    candle_count: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_body_ratio: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    max_body_ratio: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    classification: Mapped[str] = mapped_column(String(32), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    pattern_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    pattern_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    latest_atr: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)

    run: Mapped[ScanRun] = relationship(back_populates="results")
    candles: Mapped[list[ScanResultCandle]] = relationship(
        back_populates="result", cascade="all, delete-orphan"
    )


class ScanResultCandle(Base, TimestampMixin):
    """Exact pattern-window OHLCV preserved with the scan result."""

    __tablename__ = "scan_result_candles"
    __table_args__ = (
        UniqueConstraint(
            "scan_result_id", "timestamp", name="uq_scan_result_candles_result_ts"
        ),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    scan_result_id: Mapped[int] = mapped_column(
        ForeignKey("scan_results.id", ondelete="CASCADE"), nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    volume: Mapped[Decimal] = mapped_column(Numeric(24, 4), nullable=False)

    result: Mapped[ScanResult] = relationship(back_populates="candles")


class PipelineJob(Base, TimestampMixin):
    """One ingestion and/or scanner pipeline execution."""

    __tablename__ = "pipeline_jobs"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    job_type: Mapped[str] = mapped_column(
        String(24), default="FULL_PIPELINE", index=True
    )
    trigger_source: Mapped[str] = mapped_column(
        String(16), default="MANUAL", index=True
    )
    status: Mapped[str] = mapped_column(String(24), default="PENDING", index=True)
    stage: Mapped[str | None] = mapped_column(String(32), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_seconds: Mapped[float | None] = mapped_column(
        Numeric(12, 3), nullable=True
    )
    total_instruments: Mapped[int] = mapped_column(Integer, default=0)
    processed_instruments: Mapped[int] = mapped_column(Integer, default=0)
    failed_instruments: Mapped[int] = mapped_column(Integer, default=0)
    candles_fetched: Mapped[int] = mapped_column(Integer, default=0)
    candles_inserted: Mapped[int] = mapped_column(Integer, default=0)
    candles_updated: Mapped[int] = mapped_column(Integer, default=0)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancellation_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    owner: Mapped[str | None] = mapped_column(String(64), nullable=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ingestion_job_id: Mapped[int | None] = mapped_column(
        ForeignKey("ingestion_jobs.id", ondelete="SET NULL"), nullable=True
    )
    scan_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("scan_runs.id", ondelete="SET NULL"), nullable=True
    )

    logs: Mapped[list[PipelineJobLog]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class PipelineJobLog(Base, TimestampMixin):
    """Per-instrument pipeline outcome."""

    __tablename__ = "pipeline_job_logs"
    __table_args__ = (
        Index("ix_pipeline_job_logs_job_status", "job_id", "status"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("pipeline_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    instrument_id: Mapped[int | None] = mapped_column(
        ForeignKey("instruments.id", ondelete="SET NULL"), nullable=True
    )
    symbol: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    candles_processed: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    job: Mapped[PipelineJob] = relationship(back_populates="logs")


class SchedulerSettings(Base, TimestampMixin):
    """Singleton row (id=1) controlling the scheduler."""

    __tablename__ = "scheduler_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    scheduler_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    scan_interval_minutes: Mapped[int] = mapped_column(Integer, default=56)
    market_open_time: Mapped[str] = mapped_column(String(5), default="09:15")
    market_close_time: Mapped[str] = mapped_column(String(5), default="15:30")
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata")
    allow_manual_outside_market_hours: Mapped[bool] = mapped_column(
        Boolean, default=True
    )
    market_holidays: Mapped[list] = mapped_column(JSON, default=list)
    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_by: Mapped[str | None] = mapped_column(String(64), nullable=True)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    account_status: Mapped[str] = mapped_column(
        String(24), default="PENDING_VERIFICATION", index=True
    )
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    role_links: Mapped[list[UserRole]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="UserRole.user_id",
    )
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    sessions: Mapped[list[UserSession]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    user_links: Mapped[list[UserRole]] = relationship(back_populates="role")


class UserRole(Base, TimestampMixin):
    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    user: Mapped[User] = relationship(
        back_populates="role_links", foreign_keys=[user_id]
    )
    role: Mapped[Role] = relationship(back_populates="user_links")


class RefreshToken(Base, TimestampMixin):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    token_family_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )
    device_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    replaced_by_token_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("refresh_tokens.id", ondelete="SET NULL"), nullable=True
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped[User] = relationship(back_populates="refresh_tokens")


class UserSession(Base, TimestampMixin):
    __tablename__ = "user_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    refresh_token_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("refresh_tokens.id", ondelete="SET NULL"), nullable=True
    )
    device_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_activity_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped[User] = relationship(back_populates="sessions")


class EmailVerificationToken(Base, TimestampMixin):
    __tablename__ = "email_verification_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class PasswordResetToken(Base, TimestampMixin):
    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    target_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    meta: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)


__all__ = [
    "AuditLog",
    "EmailVerificationToken",
    "IngestionJob",
    "IngestionJobItem",
    "Instrument",
    "MarketCandle",
    "PasswordResetToken",
    "PipelineJob",
    "PipelineJobLog",
    "RefreshToken",
    "Role",
    "ScanResult",
    "ScanResultCandle",
    "ScanRun",
    "SchedulerSettings",
    "User",
    "UserRole",
    "UserSession",
]

