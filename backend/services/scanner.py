"""Central scanner over stored market data.

Each call creates an immutable scan run. Results store a denormalised snapshot
plus the exact pattern-window OHLCV, so history never changes when instruments,
candles or scanner settings evolve later.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime
from time import perf_counter
from typing import Any
 
import pandas as pd

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, sessionmaker

from backend.core.config import Settings as BackendSettings
from backend.core.config import get_settings
from backend.core.time import utcnow
from backend.db.models import (
    Instrument,
    MarketCandle,
    ScanResult,
    ScanResultCandle,
    ScanRun,
)
from backend.services.analytics import AnalyticsService
from data.historical_data import drop_incomplete_candles
from scanner.models import PatternConfig
from scanner.pattern_detector import PatternDetector

logger = logging.getLogger("vwap_sentinel.scanner")

STATUS_RUNNING = "RUNNING"
STATUS_COMPLETED = "COMPLETED"
STATUS_FAILED = "FAILED"
STATUS_CANCELLED = "CANCELLED"


class ScanAlreadyRunning(RuntimeError):
    """Another scan currently holds the scan lock."""


class ScanCancelled(RuntimeError):
    """Cancellation was requested before the scan finished."""


class ScanError(RuntimeError):
    """The scan could not run at all."""


@dataclass(frozen=True)
class ScanRunSummary:
    scan_run_id: int
    status: str
    instruments_scanned: int
    failed_instruments: int
    matches_count: int
    duration_seconds: float
    config_version: str



def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _utc(value: Any) -> datetime | None:
    if value is None:
        return None
    stamp = pd.Timestamp(value)

    if stamp.tzinfo is None:
        stamp = stamp.tz_localize("Asia/Kolkata")
    return stamp.tz_convert("UTC").to_pydatetime()


class ScannerService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        backend_settings: BackendSettings | None = None,
        pattern_config: PatternConfig | None = None,
        clock: Callable[[], datetime] = utcnow,
    ) -> None:
        self.session_factory = session_factory
        self.settings = backend_settings or get_settings()
        self.config = pattern_config or PatternConfig()
        self._clock = clock
        self.analytics = AnalyticsService()
        self._lock_connection: Any | None = None

    def run(
        self,
        triggered_by: str = "admin",
        scan_type: str = "MANUAL",
        *,
        pipeline_job_id: int | None = None,
        ingestion_job_id: int | None = None,
        should_cancel: Callable[[], bool] | None = None,
        progress_callback: Callable[[int, int, int, int], None] | None = None,
    ) -> ScanRunSummary:
        started_perf = perf_counter()
        config_payload = _jsonable(asdict(self.config))
        config_version = hashlib.sha256(
            json.dumps(config_payload, sort_keys=True).encode("utf-8")
        ).hexdigest()[:12]

        db = self.session_factory()
        if not self._acquire_lock(db):
            db.close()
            raise ScanAlreadyRunning("Another scan is already running.")

        run = ScanRun(
            scan_type=scan_type,
            status=STATUS_RUNNING,
            started_at=self._clock(),
            triggered_by=triggered_by,
            config=config_payload,
            config_version=config_version,
            pipeline_job_id=pipeline_job_id,
            ingestion_job_id=ingestion_job_id,
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        try:
            self._execute(
                db,
                run,
                should_cancel=should_cancel,
                progress_callback=progress_callback,
            )
        except ScanCancelled:
            db.rollback()
            self._mark_cancelled(run.id)
            raise
        except Exception as exc:
            db.rollback()
            logger.exception("Scan run %s failed", run.id)
            self._fail(run.id, f"{type(exc).__name__}: {exc}")
            raise ScanError(str(exc)) from exc
        finally:
            self._release_lock()
            db.close()


        return ScanRunSummary(
            scan_run_id=run.id,
            status=STATUS_COMPLETED,
            instruments_scanned=run.instruments_scanned,
            failed_instruments=run.failed_instruments,
            matches_count=run.matches_count,

            duration_seconds=round(perf_counter() - started_perf, 3),
            config_version=config_version,
        )

    def _execute(
        self,
        db: Session,
        run: ScanRun,
        *,
        should_cancel: Callable[[], bool] | None = None,
        progress_callback: Callable[[int, int, int, int], None] | None = None,
    ) -> None:
        timeframe = self.settings.market_data_timeframe
        now_ist = pd.Timestamp.now(tz=self.analytics.timezone)
        freshness = db.scalar(select(func.max(MarketCandle.timestamp)))

        instruments = list(
            db.scalars(
                select(Instrument)
                .where(
                    Instrument.is_active,
                    Instrument.instrument_type == "FUT",
                )
                .order_by(Instrument.fyers_symbol)
            )
        )

        detector = PatternDetector(self.config)
        scanned = 0
        matches = 0
        failed = 0
        errors: list[str] = []

        for instrument in instruments:
            if should_cancel is not None and should_cancel():
                raise ScanCancelled("Cancellation requested")
            scanned += 1
            try:
                candles = self.analytics.load_candles(db, instrument.id, timeframe)
                frame = self.analytics.frame_from_candles(candles)
                if frame.empty:
                    failed += 1
                    errors.append(f"{instrument.fyers_symbol}: no stored candles")
                    continue

                # A candle whose closing time is in the future is still forming.
                frame = drop_incomplete_candles(
                    frame,
                    timeframe,
                    now=now_ist,
                    timezone=self.analytics.timezone,
                )
                if frame.empty:
                    failed += 1
                    errors.append(
                        f"{instrument.fyers_symbol}: only incomplete candles"
                    )
                    continue

                frame = self.analytics.compute(frame)
                detected = detector.detect(frame)
                if detected is None:
                    continue

                window = frame.iloc[detected.start_idx : detected.end_idx + 1]
                last_row = frame.iloc[-1]
                detected_at = _utc(detected.pattern_end or last_row["timestamp"])
                if detected_at is None:
                    continue

                result = ScanResult(
                    scan_run_id=run.id,
                    instrument_id=instrument.id,
                    symbol=instrument.fyers_symbol,
                    expiry_date=instrument.expiry_date,
                    last_price=float(detected.last_price),
                    avwap=float(detected.avwap),
                    session_vwap=(
                        float(last_row["session_vwap"])
                        if pd.notna(last_row["session_vwap"])
                        else None
                    ),
                    distance_pct=float(detected.distance_pct),
                    candle_count=int(detected.candle_count),
                    avg_body_ratio=float(detected.avg_body_ratio),
                    max_body_ratio=float(detected.max_body_ratio),
                    classification=detected.pattern_type,
                    detected_at=detected_at,
                    pattern_start=_utc(detected.pattern_start),
                    pattern_end=_utc(detected.pattern_end),
                    latest_atr=(
                        float(detected.latest_atr)
                        if detected.latest_atr is not None
                        else None
                    ),
                )
                db.add(result)
                db.flush()

                for row in window.itertuples(index=False):
                    db.add(
                        ScanResultCandle(
                            scan_result_id=result.id,
                            timestamp=_utc(row.timestamp),
                            open=float(row.open),
                            high=float(row.high),
                            low=float(row.low),
                            close=float(row.close),
                            volume=float(row.volume),
                        )
                    )
                matches += 1
            except ScanCancelled:
                raise
            except Exception as exc:
                failed += 1
                message = f"{instrument.fyers_symbol}: {type(exc).__name__}: {exc}"
                errors.append(message[:500])
                logger.warning("Scan skipped %s: %s", instrument.fyers_symbol, exc)
            finally:
                if progress_callback is not None:
                    try:
                        progress_callback(scanned, len(instruments), matches, failed)
                    except Exception:
                        logger.debug("Scan progress callback failed", exc_info=True)

        run.instruments_scanned = scanned
        run.failed_instruments = failed
        run.matches_count = matches
        run.error_summary = "\n".join(errors[:10])[:2000] or None
        run.data_freshness_at = freshness
        run.status = STATUS_COMPLETED
        run.completed_at = self._clock()
        db.commit()

        logger.info(
            "Scan run %s complete: %s instruments, %s matches, %s failed",
            run.id,
            scanned,
            matches,
            failed,
        )


    def _mark_cancelled(self, run_id: int) -> None:
        db = self.session_factory()
        try:
            run = db.get(ScanRun, run_id)
            if run is not None:
                run.status = STATUS_CANCELLED
                run.completed_at = self._clock()
                run.error_summary = "Cancellation requested"
                db.commit()
        except Exception:
            db.rollback()
            logger.exception("Could not mark scan run %s cancelled", run_id)
        finally:
            db.close()

    def _fail(self, run_id: int, message: str) -> None:

        db = self.session_factory()
        try:
            run = db.get(ScanRun, run_id)
            if run is not None:
                run.status = STATUS_FAILED
                run.completed_at = self._clock()
                run.error_summary = message[:2000]
                db.commit()
        except Exception:
            db.rollback()
            logger.exception("Could not mark scan run %s failed", run_id)
        finally:
            db.close()

    def _acquire_lock(self, db: Session) -> bool:
        bind = db.get_bind()
        if bind.dialect.name != "postgresql":
            return True
        connection = bind.connect()
        try:
            acquired = bool(
                connection.execute(
                    text("SELECT pg_try_advisory_lock(:key)"),
                    {"key": self.settings.scan_lock_key},
                ).scalar()
            )
            if acquired:
                connection.commit()
        except Exception:
            connection.close()
            raise
        if not acquired:
            connection.close()
            return False
        self._lock_connection = connection
        return True

    def _release_lock(self) -> None:
        if self._lock_connection is None:
            return
        try:
            self._lock_connection.execute(
                text("SELECT pg_advisory_unlock(:key)"),
                {"key": self.settings.scan_lock_key},
            )
            self._lock_connection.commit()
        except Exception:
            logger.warning("Could not release scan advisory lock", exc_info=True)
        finally:
            try:
                self._lock_connection.close()
            except Exception:
                pass
            self._lock_connection = None
