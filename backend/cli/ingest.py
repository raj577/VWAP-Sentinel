"""Run one centralized market-data ingestion.

Usage:
    python -m backend.cli.ingest --triggered-by cli
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from backend.db.session import get_session_factory
from backend.services.ingestion import (
    IngestionAlreadyRunning,
    IngestionError,
    MarketDataIngestionService,
    ProviderAuthenticationError,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run FYERS market-data ingestion")
    parser.add_argument("--triggered-by", default="cli")
    args = parser.parse_args(argv)

    service = MarketDataIngestionService(get_session_factory())
    try:
        result = service.run(triggered_by=args.triggered_by)
    except ProviderAuthenticationError as exc:
        print(f"FYERS authentication failed: {exc}", file=sys.stderr)
        return 2
    except IngestionAlreadyRunning as exc:
        print(f"Ingestion already running: {exc}", file=sys.stderr)
        return 3
    except IngestionError as exc:
        print(f"Ingestion failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(asdict(result), indent=2))
    return 0 if result.status in {"COMPLETED", "PARTIALLY_COMPLETED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
