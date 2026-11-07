# VWAP Sentinel - SaaS Migration Plan

Status: Phase 1 implemented
Date: 2026-11-07
Legacy app: Streamlit (`app.py`) - kept working, not modified by Phase 1.
New backend: `backend/` (FastAPI, SQLAlchemy 2, Alembic).

---

## 1. Existing project architecture

```
app.py                      Streamlit UI, auth gate, scan orchestration, charts
app_gradio.py               HF deployment shell (Gradio + Streamlit proxy)
config.py                   Settings.from_env, logging, directories
login.py                    FYERS OAuth code flow, token store, verification
dashboard/charts.py         Plotly candlestick + AVWAP/VWAP overlays (no Streamlit)
dashboard/components.py     Tables, metrics, match selection (Streamlit)
dashboard/presets_ui.py     Preset save/load/delete (Streamlit)
data/fyers_client.py        Rate limiter, retries, backoff, error classification
data/historical_data.py     Fetch, normalize, chunking, incomplete-candle removal
data/instrument_master.py   NSE_FO CSV parse, futures discovery, expiry handling
data/cache.py               TTL text cache + per-contract CSV candle cache
indicators/avwap.py         Contract-start AVWAP (cumulative, never resets)
indicators/vwap.py          Session VWAP (daily reset)
indicators/atr.py           Wilder ATR(14)
scanner/models.py           Frozen dataclasses and pattern constants
scanner/pattern_detector.py Eligibility mask -> contiguous run -> classification
scanner/scan_engine.py      Sequential orchestration, per-contract error isolation
scanner/presets.py          Atomic JSON preset store
tests/                      60 tests over indicators, data, detector, presets, engine
```

Data flow today: FYERS API -> `HistoricalDataService` -> indicators -> detector ->
`ScanReport` -> Streamlit tables/charts. The FYERS token is stored locally and the
scanner runs inside the UI process.

Current limitations for SaaS:
- One FYERS token per deployment; every visitor shares it.
- No database; presets are JSON files and candles are CSV cache.
- No users, roles, trials, plans or entitlements.
- Scan results exist only in memory for the current session, so no history.
- Scanning is triggered by the UI, not by a central scheduler.

---

## 2. Reusable components

| Existing component | Reuse in SaaS | Notes |
|---|---|---|
| `indicators/avwap.py` | AVWAP engine | Pure pandas/numpy, move without changes |
| `indicators/vwap.py` | Session VWAP | Pure, unchanged |
| `indicators/atr.py` | ATR filter | Pure, unchanged |
| `scanner/pattern_detector.py` | Pattern scanner | Pure; feed DataFrames from DB |
| `scanner/models.py` | Domain models | Keep dataclasses; add ORM models separately |
| `data/fyers_client.py` | Central FYERS client | Worker-only; rate limit and retries stay |
| `data/historical_data.py` | Candle normalization | Reuse; replace cache read with DB read |
| `data/instrument_master.py` | Futures discovery | Reuse; persist results to DB |
| `data/cache.py` | Optimisation only | PostgreSQL becomes authoritative |
| `login.py` | Owner-level FYERS OAuth | Admin-only; never exposed to customers |
| `dashboard/charts.py` | Chart rendering | No Streamlit import; can serve figure JSON |
| `scanner/presets.py` | Strategy presets | Schema migrates to `strategy_presets` tables |
| `tests/helpers.py` | Detector fixtures | Reuse for scanner regression tests |

Deprecated after migration: `app.py`, `dashboard/components.py`,
`dashboard/presets_ui.py`, `scanner/presets.py` (file store). They stay in place
until the web client reaches feature parity.

---

## 3. Proposed SaaS architecture

```
                    FYERS API (owner credentials, server-side only)
                                   |
                                   v
                 Ingestion worker (Celery/worker + Beat scheduler)
                   - instrument discovery
                   - 1h candle fetch + upsert
                   - AVWAP/VWAP computation
                   - pattern scan
                                   |
                                   v
        PostgreSQL (source of truth)  <---- Redis (locks, cache, queues)
                                   |
                                   v
                    FastAPI /api/v1  (auth, entitlements, scans, admin)
                    /            \
                   v              v
            Next.js web      Flutter mobile
```

Hard rules:
- Only backend components hold FYERS credentials.
- Customers authenticate with email/password, never FYERS.
- Every protected endpoint checks role + entitlement server-side.
- Scan snapshots are immutable; new runs append, old runs never change.

Process split for production:
- `api` - FastAPI workers (stateless, scales horizontally)
- `worker` - ingestion/scan jobs (single writer per job, Redis lock)
- `scheduler` - one instance only (Beat or APScheduler with a DB/Redis lease)
- `web` - Next.js
- `postgres`, `redis`

Scheduler safety: never start a scheduler in each API worker. Run it as its own
container with replicas=1, and still guard jobs with a Redis/DB lock.

---

## 4. Database ER diagram

```mermaid
erDiagram
    roles ||--o{ users : assigns
    users ||--o{ refresh_tokens : owns
    users ||--o{ email_verification_tokens : owns
    users ||--o{ password_reset_tokens : owns
    users ||--o{ subscriptions : has
    users ||--o{ watchlists : owns
    users ||--o{ user_feature_overrides : has
    users ||--o{ feature_usage : consumes
    users ||--o{ devices : registers
    users ||--o{ notifications : receives
    users ||--o{ user_activity : generates
    users ||--o{ audit_logs : acts
    users ||--o{ strategy_presets : saves

    plans ||--o{ plan_features : includes
    features ||--o{ plan_features : mapped
    plans ||--o{ subscriptions : sold_as
    subscriptions ||--o{ payments : billed

    instruments ||--o{ futures_contracts : lists
    futures_contracts ||--o{ market_candles : has
    futures_contracts ||--o{ avwap_values : computes
    futures_contracts ||--o{ vwap_values : computes
    futures_contracts ||--o{ watchlist_items : tracked

    scanner_configs ||--o{ scan_runs : configures
    scan_runs ||--o{ scan_results : contains
    scan_results ||--o{ scan_result_candles : preserves
    futures_contracts ||--o{ scan_results : matched

    ingestion_jobs ||--o{ job_logs : logs
    scheduler_settings ||--o{ ingestion_jobs : schedules

    strategy_presets ||--o{ strategy_legs : contains
```

Key table shapes (all timestamps `timestamptz`, stored UTC):

| Table | Critical columns and constraints |
|---|---|
| `users` | `id`, `email` unique (citext/lower), `password_hash`, `role_id`, `is_active`, `email_verified_at`, soft delete |
| `roles` | `name` unique: SUPER_ADMIN, ADMIN, CUSTOMER |
| `refresh_tokens` | `token_hash` unique, `family_id`, `expires_at`, `revoked_at`, `replaced_by_id` |
| `plans` | `code` unique, `price_cents`, `currency`, `billing_interval`, `duration_days`, `is_active` |
| `features` | `key` unique, `is_global_enabled`, `default_limit`, `unit` |
| `plan_features` | unique (`plan_id`, `feature_id`), `is_enabled`, `limit_value` |
| `user_feature_overrides` | unique (`user_id`, `feature_id`), `expires_at` |
| `feature_usage` | unique (`user_id`, `feature_id`, `period_start`), `used_count` |
| `subscriptions` | `status` (NOT_STARTED/ACTIVE/EXPIRED/CANCELLED/CONVERTED_TO_PAID), `trial_ends_at`, `current_period_end` |
| `payments` | `provider`, `provider_payment_id` unique, `status`, `paid_at` |
| `instruments` | `symbol` unique, `underlying`, `is_index` |
| `futures_contracts` | `symbol` unique, `expiry_date`, unique (`instrument_id`, `expiry_date`) |
| `market_candles` | unique (`contract_id`, `timeframe`, `candle_ts_utc`), OHLCV numeric |
| `avwap_values` | unique (`contract_id`, `timeframe`, `candle_ts_utc`), `anchor_ts_utc` |
| `vwap_values` | unique (`contract_id`, `timeframe`, `candle_ts_utc`, `session_date`) |
| `scanner_configs` | `version` unique, `config` JSONB, `is_active` |
| `scan_runs` | `scan_type`, `status`, `started_at`, `completed_at`, counts, `data_freshness_at` |
| `scan_results` | unique (`scan_run_id`, `contract_id`), denormalised symbol/expiry/price snapshots |
| `scan_result_candles` | unique (`scan_result_id`, `candle_ts_utc`) - exact OHLCV at detection |
| `ingestion_jobs` | `status`, `trigger` (SCHEDULED/MANUAL), counters, `started_at`, `completed_at` |
| `job_logs` | `job_id`, `level`, `message`, `context` JSONB |
| `scheduler_settings` | single row: `interval_minutes`, `enabled`, `last_run_at`, `next_run_at` |
| `watchlists` / `watchlist_items` | unique (`watchlist_id`, `contract_id`) |
| `notifications` / `devices` | unread index, unique (`user_id`, `push_token`) |
| `audit_logs` | `actor_id`, `action`, `entity_type`, `entity_id`, `before`/`after` JSONB |
| `admin_settings` | `key` primary key, `value` JSONB |
| `strategy_presets` / `strategy_legs` | user-owned or global presets |
| `guides` | `slug` unique, `plan_min`, `is_published` |

Indexing plan: `market_candles` (`contract_id`, `candle_ts_utc`), `scan_runs`
(`completed_at` desc), `scan_results` (`scan_run_id`, `classification`,
`distance_pct`), `users` (`lower(email)`), `audit_logs` (`created_at` desc).

Storage rules: candles are rows, never JSON blobs. Upserts use
`ON CONFLICT (contract_id, timeframe, candle_ts_utc) DO UPDATE`.
Scan publication wraps `scan_runs` + `scan_results` + `scan_result_candles` in a
single transaction; a failed run is stored with `status=FAILED` and no partial
results, leaving the previous successful snapshot untouched.

---

## 5. Migration plan

Guiding rules:
- Keep the legacy Streamlit app runnable until parity.
- Add new code side by side; never fork the AVWAP/pattern logic.
- Database first, UI later.
- Each phase ends with migrations and passing tests.

| Phase | Scope | Reuses | Exit criteria |
|---|---|---|---|
| 1 | Backend foundation, config, DB session, Alembic, health | `config.py` patterns | `/api/v1/health/live` and `/ready` green, tests pass |
| 2 | Central FYERS ingestion into PostgreSQL | `fyers_client`, `instrument_master`, `historical_data`, `indicators` | Candles stored, upsert idempotent, AVWAP matches legacy output |
| 3 | Scanner service + immutable snapshots | `pattern_detector`, `scan_engine` | Two runs produce two snapshots; old snapshot unchanged |
| 4 | Scheduler + manual refresh + job tracking | new | 56-minute job, Redis lock, overlap blocked, failure preserves last scan |
| 5 | Auth: register/login/JWT/refresh rotation/roles | new | Auth and RBAC tests pass |
| 6 | Plans, trials, features, overrides, usage limits | new | Entitlement tests pass for FREE/TRIAL/PRO/PREMIUM |
| 7 | Admin APIs for dashboard, users, plans, features, settings, audit | new | Admin endpoints return 403 to customers |
| 8 | Next.js customer app (current scan, history, charts, watchlist, billing screen) | chart JSON from `dashboard/charts.py` | Parity with legacy scan viewing |
| 9 | Mobile readiness (devices, notifications, pagination, stable errors) | new | OpenAPI contract documented and exercised |
| 10 | Production packaging (compose, nginx, HTTPS, backups, monitoring) | new | Staging deploy with restore drill |

Data migration:
1. Backfill `instruments` and `futures_contracts` from the FYERS master.
2. Import existing CSV cache into `market_candles` (idempotent upsert).
3. Keep CSV cache as a read-through optimisation, not truth.
4. Presets JSON imports into `strategy_presets` with a one-time script.
5. Legacy `presets/` and `cache/` stay gitignored.

Rollback: the legacy app remains untouched; if a phase fails, the Space and local
Streamlit keep serving from the old code path.

---

## 6. Phase 1 delivered

Files created:

```
backend/__init__.py
backend/main.py                     app factory, CORS, uvicorn entry
backend/core/config.py              pydantic-settings (DB, Redis, CORS, interval)
backend/core/logging.py             single logging configuration
backend/core/time.py                UTC storage + IST display helpers
backend/db/base.py                  DeclarativeBase, naming convention, TimestampMixin
backend/db/session.py               lazy engine, session factory, get_db, reset_engine
backend/db/models.py                model registry for Alembic (no tables yet)
backend/schemas/health.py           liveness/readiness response models
backend/api/v1/health.py            /health/live, /health/ready
backend/api/v1/router.py            /api/v1 router and index
backend/api/__init__.py, backend/api/v1/__init__.py, backend/schemas/__init__.py,
backend/db/__init__.py, backend/core/__init__.py
alembic.ini
migrations/env.py
migrations/script.py.mako
migrations/versions/0001_baseline.py  empty baseline (chain established)
requirements-backend.txt
docker-compose.yml                  postgres 16 + redis 7 (local dev)
tests/test_backend_health.py        5 tests
```

Design notes:
- The engine is lazy, so the app starts and serves liveness without a database.
- `/health/ready` executes `SELECT 1` and returns 503 when the DB is down.
- CORS origins come from `CORS_ORIGINS` (comma separated).
- Timezone policy is centralised: store UTC, display `Asia/Kolkata`.
- No business tables yet by design; later phases add small migrations.

### Run

```powershell
# 1. dependencies
.\.venv\Scripts\python.exe -m pip install -r requirements-backend.txt

# 2. PostgreSQL + Redis (requires Docker Desktop running)
docker compose up -d postgres redis

# 3. configure
$env:DATABASE_URL="postgresql+psycopg://avwap:avwap@localhost:5432/avwap"
$env:REDIS_URL="redis://localhost:6379/0"

# 4. migrate and run
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
```

Endpoints:
- `GET /api/v1/health/live`
- `GET /api/v1/health/ready`
- `GET /api/v1/`
- `GET /docs` (OpenAPI UI)

### Verification performed

- `pytest -q`: 65 passed (60 legacy + 5 backend)
- `alembic upgrade head` then `downgrade base` on SQLite: clean
- Live server smoke test on port 8010: live 200, ready 200 with
  `{"status":"ok","database":"ok"}`, index 200
- Real PostgreSQL not yet exercised: Docker Desktop daemon was not running on
  this machine, so Postgres connectivity remains unverified until
  `docker compose up -d` is executed.

### Unfinished in Phase 1

- No business tables or models yet (introduced per phase).
- No auth, JWT, rate limiting or audit tables yet.
- No CI workflow.
- No production Dockerfile for the backend (Phase 10).
- Database backups/monitoring not configured.
- `paths`/`migrations` not yet wired into deployment.

---

## 7. Security notes carried forward

- Never return FYERS credentials or tokens from any API.
- Customers never see FYERS login or SDK errors; map provider failures to
  generic service errors.
- Secrets only via environment variables or a secrets manager.
- Refresh tokens stored hashed, rotated, revocable per family.
- Entitlements enforced in the backend for every protected route.
- Admin actions write audit rows with actor, before/after and IP.
- Rotate any FYERS credential that has ever been shared outside the server.

---

## 8. Phase 2 delivered - centralized ingestion + Next.js foundation

Files created:

```
backend/db/models.py                     instruments, market_candles,
                                         ingestion_jobs, ingestion_job_items
migrations/versions/0002_market_data.py  tables, FKs, unique constraints, indexes
backend/services/fyers_status.py         cached centralized FYERS status probe
backend/services/analytics.py            AVWAP/session VWAP from stored candles
backend/services/ingestion.py            discovery, fetch, validate, upsert, jobs
backend/api/deps.py                      interim admin key dependency
backend/api/v1/market_data.py            status/instruments/candles/avwap
backend/api/v1/admin_market_data.py      job history/detail/summary
backend/schemas/market_data.py           response models
backend/cli/ingest.py                    ingestion CLI
scripts/run_api.cmd, scripts/ingest.cmd  local orchestration
scripts/run_web.cmd                      Next.js production server
tests/test_market_data.py                11 ingestion/API tests
tests/test_postgres_integration.py       PostgreSQL upsert check (opt-in)
frontend/                                Next.js 15 + TypeScript + Tailwind
frontend/app/(app)/page.tsx              dashboard: status, counters, contracts
frontend/app/(app)/admin/page.tsx        ingestion job table (server-side key)
frontend/app/login/page.tsx              placeholder
frontend/lib/api.ts, services/marketData.ts, types/api.ts
frontend/components/*                    shell, health indicator, table, cards
docker-compose.yml                       postgres:16 + redis:7
```

Files modified: `backend/core/config.py` (admin key, timeframe, batch, lock,
FYERS cache), `backend/db/session.py` (connect timeout), `backend/api/v1/router.py`,
`.env.example`, `.gitignore`, `requirements-backend.txt`, `README.md`,
`PROJECT_STATUS.md`.

Endpoints implemented: `GET /market-data/status`, `/instruments`,
`/instruments/{symbol}`, `/candles/{symbol}`, `/avwap/{symbol}`;
`GET /admin/market-data/jobs`, `/jobs/{id}`, `/ingestion-summary`.

Ingestion guarantees: token checked before work, active stock futures only,
expired contracts excluded, index futures excluded, completed candles only,
dedupe + OHLC validation, dialect-aware upsert on
(instrument, timeframe, timestamp), per-instrument isolation, advisory lock,
job counters and per-instrument results, failed run preserves prior data.

Verification:

- `alembic upgrade head` against PostgreSQL 16 (Docker) -> `0002_market_data`
- `pytest -q` -> 77 passed with `TEST_DATABASE_URL` set
- Live API against PostgreSQL: `/health/ready` 200, `/market-data/status` 200
- Next.js production build: compiled successfully, 7 routes
- Dashboard renders live API values (`AUTHENTICATION_EXPIRED`, counts)
- Admin page renders job table through the server-side admin key

Not done (later phases): scheduler (4), manual refresh API (4), scanner
snapshots (3), auth/JWT (5), entitlements (6), admin UI for users/plans (7),
charts in Next.js (8), partitioning/retention.

### Phase 2 addendum - admin-driven FYERS OAuth

`backend/services/fyers_auth.py` and `backend/api/v1/fyers_auth.py` add the
owner login flow: admin-key-protected login URL generation, HMAC-signed state
with TTL, public callback that validates state and writes the token through the
existing `TokenStore`, plus a Next.js server route so the admin key never
reaches the browser. The legacy Streamlit login remains functional.

### Phase 3 (partial) - scan execution and immutable snapshots

Added `backend/services/scanner.py` (stored candles -> pattern detector ->
`scan_runs` / `scan_results` / `scan_result_candles`), migration
`0003_scan_snapshots`, admin APIs (`POST /admin/scans/run`, list/latest/detail)
and the `/admin/scans` Next.js page with a Run button and result/history tables.
Runs are append-only; pattern-window OHLCV is frozen per result; a PostgreSQL
advisory lock prevents concurrent runs. Customer-facing scan APIs and views
remain for Phase 8.

### Phase 3 completion - public scan reads, comparisons and charts

Added `backend/api/v1/scanner.py` (current/history/detail/results/chart/
comparison/appearances), `backend/services/scan_read.py`, migration
`0004_scan_failed_count`, forming-candle exclusion and failed-instrument
counting in the scanner, plus Next.js pages for current scan, history, detail
with run comparison, and a dependency-free SVG candlestick chart with AVWAP,
VWAP and pattern highlighting. Verified against temporary seeded data and
cleaned up afterwards. Tests: 97 passing.

### Phase 4 delivered - scheduler, worker and admin data controls

Added `scheduler_settings`, `pipeline_jobs`, `pipeline_job_logs`
(migration `0005_scheduler_pipeline`), a dedicated `backend/scheduler_main.py`
with a PostgreSQL singleton lock and market-calendar gate, a dedicated
`backend/worker_main.py` using `FOR UPDATE SKIP LOCKED`, heartbeat recovery and
cooperative cancellation, and `backend/services/pipeline.py` orchestration.
Admin scheduler/pipeline APIs and the Next.js `/admin/pipeline` pages provide
status, controls, polling jobs, cancellation and per-instrument logs. Docker
images for backend and web build successfully; compose adds migrate, api,
worker, scheduler and web services.

### Phase 5 delivered - authentication, RBAC and user management

Added users/roles/user_roles/refresh tokens/sessions/verification and reset
tokens/audit logs (migration `0006_auth`), Argon2id hashing, JWT access tokens,
rotating refresh-token families with reuse detection, cookie+CSRF web auth,
Bearer-compatible mobile auth, rate limiting, admin user management with
privilege-escalation guards, audit logging and an idempotent SUPER_ADMIN
bootstrap CLI. Next.js gained public auth pages, guarded app routes, profile and
session/security screens, and server-side cookie forwarding for protected
scanner APIs.

### Premium landing and login experience

Added a public marketing site at `/` (navbar, hero dashboard preview, features,
workflow, scanner preview, strategy, comparison, pricing preview, FAQ, CTA,
footer) and a redesigned `/login` with a branded two-column layout, accessible
form validation, show/hide password and role-based redirects. Register, verify,
forgot and reset pages share the same auth layout. `frontend/middleware.ts`
renews expired access cookies through refresh-token rotation. The customer
dashboard moved to `/dashboard` so `/` can serve the public landing page.

### Admin and customer application UI

Added a role-aware application shell (collapsible sidebar, mobile menu), an
admin overview built from user/market/scheduler/pipeline/scan/audit APIs, admin
market-data, scheduler/jobs aliases, scan-history, user management, roles,
audit and settings screens, and explicit integration placeholders for
monetization modules without backend APIs. The customer workspace gained an
overview, scanner with filters/sorting/search/pagination, match detail,
chart alias, history list/detail, profile/security and clearly marked
unavailable modules (watchlist, strategies, subscription, billing). A `q`
search filter was added to the instruments API.
