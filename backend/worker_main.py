"""Dedicated pipeline worker.

Claims PENDING pipeline jobs and executes ingestion and/or scanning. Safe to
run as a single process; multiple instances are supported because claims use
``FOR UPDATE SKIP LOCKED`` on PostgreSQL.
"""

from __future__ import annotations

import logging
import os
import socket
import time
from time import monotonic

from backend.core.config import get_settings
from backend.core.logging import configure_logging
from backend.db.session import get_session_factory
from backend.services.pipeline import (
    PipelineExecutor,
    claim_next_job,
    recover_abandoned_jobs,
)

logger = logging.getLogger("vwap_sentinel.worker")


def main() -> int:
    settings = get_settings()
    configure_logging(settings.log_level)
    factory = get_session_factory()
    owner = f"worker-{socket.gethostname()}-{os.getpid()}"

    recovered = recover_abandoned_jobs(
        factory, settings.job_heartbeat_timeout_seconds
    )
    if recovered:
        logger.warning("Recovered abandoned jobs at startup: %s", recovered)

    last_recovery = monotonic()
    logger.info(
        "Worker %s started (poll=%ss, heartbeat timeout=%ss)",
        owner,
        settings.worker_poll_seconds,
        settings.job_heartbeat_timeout_seconds,
    )

    while True:
        try:
            now = monotonic()
            if now - last_recovery >= 60:
                recover_abandoned_jobs(
                    factory, settings.job_heartbeat_timeout_seconds
                )
                last_recovery = now

            job_id = claim_next_job(factory, owner)
            if job_id is None:
                time.sleep(max(settings.worker_poll_seconds, 1))
                continue

            PipelineExecutor(factory).execute(job_id, owner=owner)
        except KeyboardInterrupt:
            logger.info("Worker %s interrupted; exiting", owner)
            return 0
        except Exception:
            logger.exception("Worker loop error; continuing")
            time.sleep(max(settings.worker_poll_seconds, 1))


if __name__ == "__main__":
    raise SystemExit(main())
