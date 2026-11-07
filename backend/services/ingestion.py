"""Centralized market-data ingestion.

The service is transport-agnostic: it can be called by a scheduler, an admin
endpoint or a test. Only this service touches the FYERS SDK.

Guarantees:
- One FYERS token, server-side only.
- Contract-specific candles never mix across expiries.
- Repeated ingestion upserts instead of duplicating.
- One failed instrument never aborts the whole job.
- A PostgreSQL advisory lock prevents concurrent ingestion runs.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd
from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session, sessionmaker

from backend.core.config import Settings as BackendSettings
from backend.core.config import get_settings
from backend.core.time import utcnow
from backend.db.models import IngestionJob, IngestionJobItem, Instrument, MarketCandle
from config import Settings as LegacySettings
from data.cache import HistoricalCache
from data.fyers_client import AuthenticationError, FyersClient
from data.historical_data import HistoricalDataService
from data.instrument_master import InstrumentMasterProvider, select_active_futures
from login import TokenStore
from scanner.models import Instrument as InstrumentModel

logger = logging.getLogger("vwap_sentinel.ingestion")

STATUS_COMPLETED = "COMPLETED"
STATUS_PARTIALLY_COMPLETED = "PARTIALLY_COMPLETED"
STATUS_FAILED = "FAILED"
STATUS_RUNNING = "RUNNING"
STATUS_CANCELLED = "CANCELLED"

JobStatus = str

REQUIRED_COLUMNS = ("timestamp", "open", "high", "low", "close", "volume")


class IngestionError(RuntimeError):
    """The ingestion job could not run at all."""


class IngestionAlreadyRunning(IngestionError):
    """Another ingestion job holds the database lock."""


class IngestionCancelled(IngestionError):
    """Cancellation was requested before the job finished."""


class ProviderAuthenticationError(IngestionError):
    """The centralized FYERS token is missing, invalid or expired."""


@dataclass(frozen=True)
class IngestionResult:
    job_id: int
    status: JobStatus
    total_instruments: int
    successful_instruments: int
    failed_instruments: int
    candles_inserted: int
    candles_updated: int
    duration_seconds: float
    error_summary: str | None


def _as_utc(value: Any) -> datetime:
    stamp = pd.Timestamp(value)
    if stamp.tzinfo is None:
        stamp = stamp.tz_localize("UTC")
    else:
        stamp = stamp.tz_convert("UTC")
    return stamp.to_pydatetime()


def _comparison_key(value: datetime) -> datetime:
    """Normalise to naive UTC so SQLite and PostgreSQL compare identically."""

    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _optional_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if pd.notna(number) else None


def clean_candles(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalise OHLCV rows before they touch the database."""

    if frame is None or frame.empty:
        return pd.DataFrame(columns=list(REQUIRED_COLUMNS))
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Candle data is missing columns: {missing}")

    frame = frame.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
    for column in ("open", "high", "low", "close", "volume"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    frame = frame.dropna(subset=["timestamp", "open", "high", "low", "close"])
    frame = frame.loc[
        (frame["open"] > 0)
        & (frame["high"] > 0)
        & (frame["low"] > 0)
        & (frame["close"] > 0)
        & (frame["high"] >= frame["low"])
    ]
    frame["volume"] = frame["volume"].fillna(0.0).clip(lower=0.0)
    frame = (
        frame.sort_values("timestamp")
        .drop_duplicates(subset=["timestamp"], keep="last")
        .reset_index(drop=True)
    )
    return frame[list(REQUIRED_COLUMNS)]


class MarketDataIngestionService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        backend_settings: BackendSettings | None = None,
        legacy_settings: LegacySettings | None = None,
        instrument_source: Callable[[], pd.DataFrame] | None = None,
        candle_source: Callable[[InstrumentModel], pd.DataFrame] | None = None,
        clock: Callable[[], datetime] = utcnow,
        timeframe: str | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.settings = backend_settings or get_settings()
        self.legacy = legacy_settings or LegacySettings.from_env()
        self._instrument_source = instrument_source
        self._candle_source = candle_source
        self._clock = clock
        self.timeframe = str(timeframe or self.settings.market_data_timeframe)
        self._lock_connection: Any | None = None

    # ------------------------------------------------------------------ run
    def run(
        self,
        triggered_by: str = "system",
        *,
        pipeline_job_id: int | None = None,
        should_cancel: Callable[[], bool] | None = None,
        progress_callback: Callable[[int, int, int, int], None] | None = None,
    ) -> IngestionResult:
        started = perf_counter()
        db = self.session_factory()
        job = IngestionJob(
            job_type="MARKET_DATA",
            status=STATUS_RUNNING,
            started_at=self._clock(),
            triggered_by=triggered_by,
            pipeline_job_id=pipeline_job_id,
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        if not self._acquire_lock(db, job):
            db.close()
            raise IngestionAlreadyRunning("Another ingestion job is already running.")

        try:
            summary = self._execute(
                db, job, should_cancel=should_cancel, progress_callback=progress_callback
            )
        except IngestionCancelled:
            db.rollback()
            self._finish(db, job, STATUS_CANCELLED, "Cancellation requested")
            raise
        except ProviderAuthenticationError as exc:
            self._finish(db, job, STATUS_FAILED, str(exc))
            raise
        except Exception as exc:
            logger.exception("Ingestion job %s failed", job.id)
            self._finish(db, job, STATUS_FAILED, f"{type(exc).__name__}: {exc}")
            raise IngestionError(str(exc)) from exc
        finally:
            self._release_lock()
            db.close()


        return IngestionResult(
            job_id=job.id,
            status=summary["status"],
            total_instruments=summary["total"],
            successful_instruments=summary["successful"],
            failed_instruments=summary["failed"],
            candles_inserted=summary["inserted"],
            candles_updated=summary["updated"],
            duration_seconds=round(perf_counter() - started, 3),
            error_summary=summary["error_summary"],
        )

    # -------------------------------------------------------------- execute
    def _execute(
        self,
        db: Session,
        job: IngestionJob,
        *,
        should_cancel: Callable[[], bool] | None = None,
        progress_callback: Callable[[int, int, int, int], None] | None = None,
    ) -> dict[str, Any]:
        instrument_source, candle_source = self._resolve_sources()


        try:
            master = instrument_source()
        except AuthenticationError as exc:
            raise ProviderAuthenticationError(str(exc)) from exc

        today = self._clock().astimezone(ZoneInfo(self.legacy.timezone)).date()
        active = select_active_futures(
            master,
            as_of=today,
            current_expiry_only=False,
            include_index=False,
        )
        if active is None or active.empty:
            raise IngestionError("No active NSE stock futures found in the master.")

        contracts = self._sync_instruments(db, active)
        job.total_instruments = len(contracts)
        db.commit()

        successful = 0
        failed = 0
        inserted = 0
        updated = 0
        errors: list[str] = []

        for position, (record, instrument_model) in enumerate(contracts, start=1):
            if should_cancel is not None and should_cancel():
                raise IngestionCancelled("Cancellation requested")
            symbol = instrument_model.symbol

            try:
                frame = candle_source(instrument_model)
                candles = clean_candles(frame)
                if candles.empty:
                    raise ValueError("No completed candles available")

                inserted_rows, updated_rows = self._upsert_candles(
                    db, record.id, candles
                )
                first_timestamp = _as_utc(candles["timestamp"].iloc[0])
                if (
                    record.first_available_timestamp is None
                    or _comparison_key(first_timestamp)
                    < _comparison_key(record.first_available_timestamp)
                ):
                    record.first_available_timestamp = first_timestamp

                db.add(
                    IngestionJobItem(
                        job_id=job.id,
                        instrument_id=record.id,
                        symbol=symbol,
                        status="OK",
                        candles_seen=len(candles),
                        candles_inserted=inserted_rows,
                        candles_updated=updated_rows,
                    )
                )
                successful += 1
                inserted += inserted_rows
                updated += updated_rows
                job.successful_instruments = successful
                job.failed_instruments = failed
                job.candles_inserted = inserted
                job.candles_updated = updated
                db.commit()

                if progress_callback is not None:
                    try:
                        progress_callback(position, len(contracts), successful, failed)
                    except Exception:
                        logger.debug("Ingestion progress callback failed", exc_info=True)

                if position % 25 == 0 or position == len(contracts):

                    logger.info(
                        "Ingestion %s/%s contracts (%s ok, %s failed)",
                        position,
                        len(contracts),
                        successful,
                        failed,
                    )
            except AuthenticationError as exc:
                db.rollback()
                raise ProviderAuthenticationError(str(exc)) from exc
            except Exception as exc:
                db.rollback()
                message = f"{symbol}: {type(exc).__name__}: {exc}"
                logger.warning("Ingestion failed for %s: %s", symbol, exc)
                errors.append(message[:500])
                db.add(
                    IngestionJobItem(
                        job_id=job.id,
                        instrument_id=record.id,
                        symbol=symbol,
                        status="FAILED",
                        error=str(exc)[:1000],
                    )
                )
                failed += 1
                job.failed_instruments = failed
                db.commit()

                if progress_callback is not None:
                    try:
                        progress_callback(position, len(contracts), successful, failed)
                    except Exception:
                        logger.debug("Ingestion progress callback failed", exc_info=True)


        status = (
            STATUS_COMPLETED
            if failed == 0
            else STATUS_FAILED
            if successful == 0
            else STATUS_PARTIALLY_COMPLETED
        )
        error_summary = "\n".join(errors[:10])[:2000] or None
        self._finish(db, job, status, error_summary)

        return {
            "status": status,
            "total": len(contracts),
            "successful": successful,
            "failed": failed,
            "inserted": inserted,
            "updated": updated,
            "error_summary": error_summary,
        }

    # ---------------------------------------------------------- instruments
    def _sync_instruments(
        self, db: Session, active: pd.DataFrame
    ) -> list[tuple[Instrument, InstrumentModel]]:
        existing = {
            instrument.fyers_symbol: instrument
            for instrument in db.scalars(select(Instrument))
        }
        contracts: list[tuple[Instrument, InstrumentModel]] = []
        seen: set[str] = set()

        for row in active.itertuples(index=False):
            symbol = str(row.symbol)
            seen.add(symbol)
            record = existing.get(symbol)
            if record is None:
                record = Instrument(fyers_symbol=symbol)
                db.add(record)
                existing[symbol] = record

            record.underlying_symbol = str(row.underlying)
            record.exchange = "NSE"
            record.instrument_type = "FUT"
            record.expiry_date = row.expiry
            record.lot_size = _optional_float(getattr(row, "lot_size", None))
            record.tick_size = _optional_float(getattr(row, "tick_size", None))
            record.is_active = True

            contracts.append(
                (
                    record,
                    InstrumentModel(
                        symbol=symbol,
                        underlying=str(row.underlying),
                        expiry=row.expiry,
                        lot_size=_optional_float(getattr(row, "lot_size", None)),
                        is_index=False,
                    ),
                )
            )

        for symbol, record in existing.items():
            if symbol not in seen:
                record.is_active = False

        db.commit()
        for record, _ in contracts:
            db.refresh(record)
        return contracts

    # --------------------------------------------------------------- upsert
    def _upsert_candles(
        self, db: Session, instrument_id: int, candles: pd.DataFrame
    ) -> tuple[int, int]:
        records = [
            {
                "instrument_id": instrument_id,
                "timeframe": self.timeframe,
                "timestamp": _as_utc(row.timestamp),
                "open": float(row.open),
                "high": float(row.high),
                "low": float(row.low),
                "close": float(row.close),
                "volume": float(row.volume),
            }
            for row in candles.itertuples(index=False)
        ]
        if not records:
            return 0, 0

        timestamps = [record["timestamp"] for record in records]
        existing: set[datetime] = set()
        for chunk in _chunks(timestamps, 1000):
            rows = db.scalars(
                select(MarketCandle.timestamp).where(
                    MarketCandle.instrument_id == instrument_id,
                    MarketCandle.timeframe == self.timeframe,
                    MarketCandle.timestamp.in_(chunk),
                )
            )
            existing.update(_comparison_key(value) for value in rows)

        inserted = sum(
            1
            for record in records
            if _comparison_key(record["timestamp"]) not in existing
        )
        updated = len(records) - inserted

        dialect = db.get_bind().dialect.name
        batch_size = max(int(self.settings.candle_upsert_batch_size), 1)
        for batch in _chunks(records, batch_size):
            if dialect == "postgresql":
                statement = pg_insert(MarketCandle).values(batch)
                statement = statement.on_conflict_do_update(
                    index_elements=["instrument_id", "timeframe", "timestamp"],
                    set_={
                        "open": statement.excluded.open,
                        "high": statement.excluded.high,
                        "low": statement.excluded.low,
                        "close": statement.excluded.close,
                        "volume": statement.excluded.volume,
                        "updated_at": func.now(),
                    },
                )
                db.execute(statement)
            elif dialect == "sqlite":
                statement = sqlite_insert(MarketCandle).values(batch)
                statement = statement.on_conflict_do_update(
                    index_elements=["instrument_id", "timeframe", "timestamp"],
                    set_={
                        "open": statement.excluded.open,
                        "high": statement.excluded.high,
                        "low": statement.excluded.low,
                        "close": statement.excluded.close,
                        "volume": statement.excluded.volume,
                        "updated_at": func.now(),
                    },
                )
                db.execute(statement)
            else:
                for record in batch:
                    self._slow_upsert(db, record)
        db.flush()
        return inserted, updated

    def _slow_upsert(self, db: Session, record: dict[str, Any]) -> None:
        existing = db.scalar(
            select(MarketCandle).where(
                MarketCandle.instrument_id == record["instrument_id"],
                MarketCandle.timeframe == record["timeframe"],
                MarketCandle.timestamp == record["timestamp"],
            )
        )
        if existing is None:
            db.add(MarketCandle(**record))
        else:
            for key in ("open", "high", "low", "close", "volume"):
                setattr(existing, key, record[key])

    # ---------------------------------------------------------------- lock
    def _acquire_lock(self, db: Session, job: IngestionJob) -> bool:
        bind = db.get_bind()
        if bind.dialect.name != "postgresql":
            return True
        connection = bind.connect()
        try:
            acquired = bool(
                connection.execute(
                    text("SELECT pg_try_advisory_lock(:key)"),
                    {"key": self.settings.ingestion_lock_key},
                ).scalar()
            )
        except Exception:
            connection.close()
            raise
        if not acquired:
            connection.close()
            self._finish(db, job, STATUS_FAILED, "Another ingestion job is running.")
            return False
        self._lock_connection = connection
        return True

    def _release_lock(self) -> None:
        if self._lock_connection is None:
            return
        try:
            self._lock_connection.execute(
                text("SELECT pg_advisory_unlock(:key)"),
                {"key": self.settings.ingestion_lock_key},
            )
        finally:
            self._lock_connection.close()
            self._lock_connection = None

    # -------------------------------------------------------------- helpers
    def _finish(
        self, db: Session, job: IngestionJob, status: str, error: str | None
    ) -> None:
        try:
            job.status = status
            job.completed_at = self._clock()
            job.error_summary = error[:2000] if error else None
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Could not finalise ingestion job %s", job.id)

    def _resolve_sources(
        self,
    ) -> tuple[Callable[[], pd.DataFrame], Callable[[InstrumentModel], pd.DataFrame]]:
        if self._instrument_source is not None and self._candle_source is not None:
            return self._instrument_source, self._candle_source

        provider = InstrumentMasterProvider(self.legacy)
        token = TokenStore(self.legacy).load_token()
        if not token:
            raise ProviderAuthenticationError(
                "No stored FYERS access token; the owner must log in again."
            )
        self._validate_token(token)

        client = FyersClient(self.legacy, token)
        cache = HistoricalCache(
            self.legacy.cache_dir,
            self.legacy.history_cache_ttl_seconds,
            self.legacy.timezone,
        )
        history = HistoricalDataService(client, cache, self.legacy)

        return (
            lambda: provider.load(force=True),
            lambda instrument: history.fetch(instrument, resolution=self.timeframe),
        )

    def _validate_token(self, token: str) -> None:
        try:
            FyersClient(self.legacy, token).verify_connection()
        except AuthenticationError as exc:
            raise ProviderAuthenticationError(str(exc)) from exc
        except Exception as exc:
            raise IngestionError(
                f"FYERS API unavailable: {type(exc).__name__}"
            ) from exc


def _chunks(items: Sequence[Any], size: int) -> Iterable[Sequence[Any]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]
