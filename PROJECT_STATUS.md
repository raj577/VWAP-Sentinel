# VWAP Sentinel - Build Status

Last updated: 2026-11-07
Repo: https://github.com/raj577/VWAP-Sentinel
HF Space: https://smartrobotw-vwap-sentinel.hf.space

Living document: what exists today, what is pending, and why decisions were made.

---

## 1. What the app does

Scans NSE futures contracts listed by FYERS and finds contracts whose price is
sitting at (or reclaiming) the contract-start AVWAP, using small-candle and
volatility filters. Results are shown in a Streamlit dashboard with a chart per
match.

Pipeline:

```
FYERS API -> normalize candles -> indicators (AVWAP, session VWAP, ATR)
          -> pattern detector -> scan report -> Streamlit UI
```

---

## 2. Architecture

```
app.py (Streamlit UI)
  dashboard/ (charts, tables, presets UI)
    scanner/scan_engine.py        orchestration, per-contract error isolation
      indicators/                 avwap, vwap, atr (pure functions)
      scanner/pattern_detector.py eligibility mask -> contiguous run -> classify
      data/historical_data.py     fetch, normalize, drop forming candle, cache
        data/fyers_client.py      rate limit, retries, error classification
          fyers_apiv3 SDK
    scanner/models.py             frozen dataclasses (Instrument, PatternConfig, ...)
    scanner/presets.py            JSON preset store (atomic writes)
    login.py                      OAuth code flow, token persistence

app_gradio.py                     deployment shell (Hugging Face only)
```

Dependency rule: upper layers may import lower layers, never the reverse.
`indicators/` and `scanner/` have no Streamlit dependency, so they are unit
testable and reusable.

---

## 3. Built - scanner core

- [x] FYERS instrument master download, parse, cache (667 NSE futures)
- [x] Contract filtering by live expiry, optional index futures
- [x] OAuth2 authorization-code login with token + non-sensitive metadata files
- [x] Atomic token writes (temp file + `os.replace`, `0600` on POSIX)
- [x] Historical candle fetch with chunked ranges and disk cache
- [x] Candle normalization: epoch unit detection, IST conversion, dedupe, sorting
- [x] Forming-candle removal so signals never repaint
- [x] Contract-start AVWAP (cumulative from first contract candle, never resets)
- [x] Session VWAP (daily reset)
- [x] ATR(14) for volatility-scaled candle size checks
- [x] Rate limiter (minimum spacing between API calls)
- [x] Retries with exponential backoff + jitter for transient/5xx/429
- [x] Fail-fast on authentication errors (no pointless retries)
- [x] Per-contract error isolation; one bad symbol does not abort the scan
- [x] Progress callback wired to the UI progress bar

## 4. Built - pattern detection

Detector evaluates the right edge of the completed-candle series.

Eligibility per candle:
- close within `max_close_above_pct` / `max_close_below_pct` of AVWAP
- low not below `max_low_below_pct`
- body ratio at or below `max_body_ratio`
- candle range at or below `max_candle_range_atr` x ATR (optional)

Windowing:
- longest contiguous eligible run ending at the last candle, capped at
  `max_candles`; run must reach `min_candles`
- if the run is wider than `max_window_range_pct`, drop candles from the oldest
  side until it fits

Classifications:
- `AVWAP RECLAIM` - earlier close below AVWAP, last close above
- `AVWAP CONSOLIDATION` - >= 3 candles and range <= consolidation threshold
- `AVWAP HUGGING` - >= 2 candles
- `AVWAP TOUCH` - single candle or wick touched AVWAP

Confirmation filters (all optional):
- [x] Last candle close above AVWAP
- [x] Last candle close above session VWAP
- [x] Earlier candle close below AVWAP and/or session VWAP
      - reference: AVWAP / session VWAP / either
      - candle: previous / second previous / either
      - added 2026-11-07

## 5. Built - UI and UX

- [x] Streamlit wide dashboard with dark theme
- [x] Timeframe selection (1h / 2h / 4h)
- [x] Filter controls for every detector threshold
- [x] Pattern classification multiselect
- [x] Contract multiselect from the filtered universe
- [x] Results table sorted by absolute distance from AVWAP
- [x] Metrics summary and error list
- [x] Plotly chart per selected match with AVWAP and session VWAP overlays
- [x] Preset save / load / delete (JSON, atomic writes)
- [x] OAuth callback handling via query params, cleared after exchange
- [x] Auth status cached keyed on token file mtime

## 6. Built - deployment

- [x] Hugging Face Space on Gradio SDK (free account constraint)
- [x] ZeroGPU preflight satisfied by an internal Gradio launch + hidden probe
- [x] Streamlit subprocess reverse-proxied at the site root over HTTP and
      WebSocket (`app_gradio.py`)
- [x] HF Space secrets configured and Space `RUNNING`
- [x] Verified public HTTP 200 and WebSocket handshake on the Space
- [x] Streamlit Community Cloud readiness
      - `runtime.txt` pins Python 3.12
      - `config.py` falls back to `st.secrets` when env vars are absent
      - README documents secrets and redirect URI
- [x] Local scheduled tasks: `VWAPSentinelStreamlit` (8501),
      `VWAPSentinelGradio` (7860)
- [x] Watchdog task `VWAPSentinelWatchdog` restarts a service when its port is
      closed (every 5 minutes)

## 7. Built - quality

- [x] 60 pytest tests (indicators, client, history, detector, presets, scanner)
- [x] Deterministic synthetic candle fixtures for detector tests
- [x] Legacy preset compatibility (missing keys default to off)
- [x] No secrets in git; `.env`, tokens, caches, logs, presets are ignored

---

## 8. Pending - user actions

- [ ] Finish Streamlit Community Cloud deploy
      1. share.streamlit.io -> Create app -> `raj577/VWAP-Sentinel`, `main`, `app.py`
      2. Add secrets (TOML) from README
      3. Set `FYERS_REDIRECT_URI` to the final `https://<app>.streamlit.app`
      4. Register the same URL as the redirect URI in the FYERS API dashboard
- [ ] Decide the HF Space's long-term redirect URI (already
      `https://smartrobotw-vwap-sentinel.hf.space`); confirm it is registered in
      the FYERS dashboard
- [ ] Decide whether the public Streamlit Cloud app needs a password gate
      (currently one stored FYERS token would serve every visitor)
- [ ] Remove/rotate any credentials that were ever pasted into chat or logs
- [ ] Choose whether presets should be seeded in the repo or created at runtime

## 9. Pending - engineering work

- [ ] Add a simple access gate (password from secrets) for public deployments
- [ ] Persist Cloud presets/cache outside the ephemeral container (or accept loss)
- [ ] Add structured "scan finished" notification (optional webhook/email)
- [ ] Backtest mode: replay historical scans and measure hit rate
- [ ] Parallel data fetch with a global rate-limit budget (currently sequential)
- [ ] Surface detected pattern overlay markers directly on the chart
- [ ] Add a CI workflow running pytest on push
- [ ] Pin dependency versions for reproducible builds
- [ ] Investigate why local scheduled processes occasionally exit (watchdog is
      a mitigation, not a diagnosis)

## 10. Known issues and limitations

- Cloud filesystems are ephemeral: token, cache and presets disappear on
  restart, so a fresh FYERS login is required.
- A single stored token is shared by all visitors on a public deployment.
- Scanner is sequential; a full run over ~219 contracts takes roughly 1-2
  minutes depending on cache state.
- FYERS rate limits are the hard constraint; parallelism has limited upside.
- The HF Space runs ZeroGPU hardware because free accounts cannot downgrade the
  existing Space to `cpu-basic` or switch SDK without PRO.
- Local service processes have twice been found dead despite scheduled tasks;
  the port-based watchdog now self-heals within 5 minutes.
- Stop-ScheduledTask does not always kill the child process tree; orphaned
  internal Streamlit processes may linger until the port is freed.

## 11. Key decisions

| Decision | Rationale |
|---|---|
| Streamlit for UI | Python-only, fastest path; heavy compute kept out of the UI layer |
| AVWAP anchored at contract start | Matches the trading thesis; never resets intraday |
| Detection on completed candles only | Avoids repaint; accepts slightly later signals |
| Sequential scanning | FYERS rate limits make parallel fetching risky for little gain |
| Per-contract error isolation | One bad symbol must not invalidate 200+ contracts |
| Gradio shell for HF | Only way to run Streamlit on a free HF Space (ZeroGPU requires Gradio) |
| Disk cache | Cuts API quota use and scan time |
| Atomic writes for token/presets | Crash safety without a database |

## 12. How to run

Local Streamlit:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Local proxy (same code path as HF):

```powershell
.\.venv\Scripts\python.exe app_gradio.py
```

Tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Scheduled tasks:

```powershell
Start-ScheduledTask -TaskName VWAPSentinelStreamlit
Start-ScheduledTask -TaskName VWAPSentinelGradio
Start-ScheduledTask -TaskName VWAPSentinelWatchdog
```

## 13. Configuration surface

Environment variables (or Streamlit Cloud secrets):

```
FYERS_CLIENT_ID, FYERS_SECRET_KEY, FYERS_REDIRECT_URI
FYERS_TOKEN_FILE, FYERS_TOKEN_META_FILE
FYERS_CACHE_DIR, FYERS_LOG_DIR, FYERS_PRESETS_FILE
FYERS_INSTRUMENT_MASTER_URL, FYERS_INSTRUMENT_CACHE_TTL
FYERS_RESOLUTION, FYERS_HISTORY_CACHE_TTL, FYERS_HISTORY_CHUNK_DAYS
FYERS_CONTRACT_LOOKBACK_DAYS, FYERS_HISTORY_CONT_FLAG
FYERS_REQUEST_RATE_PER_SEC, FYERS_REQUEST_MAX_RETRIES, FYERS_RETRY_BASE_SECONDS
FYERS_INCLUDE_INDEX_FUTURES, FYERS_INDEX_UNDERLYINGS
FYERS_TIMEZONE, FYERS_CHART_LOOKBACK, FYERS_LOG_LEVEL
```

---

## 14. SaaS migration (in progress)

Plan and ER diagram: `docs/SAAS_PLAN.md`.

- [x] Phase 1 - FastAPI backend foundation
      - `backend/` package, settings, logging, UTC/IST helpers
      - lazy SQLAlchemy engine + session dependency
      - Alembic chain with empty `0001_baseline`
      - `/api/v1/health/live` and `/api/v1/health/ready`
      - `docker-compose.yml` (PostgreSQL 16 + Redis 7)
      - `requirements-backend.txt`
      - 5 backend tests; full suite 65 passed
- [ ] Phase 2 - central FYERS ingestion into PostgreSQL
- [ ] Phase 3 - scanner service and immutable scan snapshots
- [ ] Phase 4 - 56-minute scheduler, manual refresh, job tracking
- [ ] Phase 5 - auth, JWT refresh rotation, roles
- [ ] Phase 6 - plans, trials, entitlements, usage limits
- [ ] Phase 7 - admin APIs
- [ ] Phase 8 - Next.js customer app
- [ ] Phase 9 - mobile readiness
- [ ] Phase 10 - production packaging

Phase 1 verification gap: PostgreSQL connectivity was not exercised because the
Docker daemon was not running locally. Alembic was verified against SQLite for
the upgrade/downgrade chain; run `docker compose up -d` before Phase 2.

---

## 15. Phase 2 - centralized ingestion (done, with caveats)

- [x] PostgreSQL 16 + Redis 7 via `docker-compose.yml` (Docker Desktop)
- [x] `instruments`, `market_candles`, `ingestion_jobs`,
      `ingestion_job_items` tables (migration `0002_market_data`)
- [x] Central ingestion service: discover -> fetch -> clean -> upsert ->
      per-instrument result -> job counters
- [x] Dialect-aware upsert (PostgreSQL `ON CONFLICT`, SQLite for tests)
- [x] PostgreSQL advisory lock prevents concurrent ingestion
- [x] Contract-specific storage: one row per symbol/expiry, never mixed
- [x] AVWAP and session VWAP computed from stored candles on request
- [x] Read APIs: status, instruments, instrument detail, candles, AVWAP
- [x] Admin diagnostics: job list/detail/summary behind `X-Admin-Key`
- [x] Ingestion CLI: `scripts\ingest.cmd`
- [x] Next.js 15 (App Router, TypeScript, Tailwind) app shell with dashboard,
      active contracts, API health indicator and admin job table
- [x] Backend tests (11 new) + PostgreSQL upsert integration test
- [x] Full suite: 77 passed (with `TEST_DATABASE_URL`)

Caveats:
- Live FYERS ingestion not yet executed: the stored token is expired
  (26+ hours old), so `/market-data/status` reports
  `AUTHENTICATION_EXPIRED`. Log in through the legacy Streamlit app once, then
  run `scripts\ingest.cmd`.
- No scheduler or manual-refresh endpoint yet (Phase 4).
- Admin endpoints use an interim API key; JWT roles arrive in Phase 5.
- Local services run through scheduled tasks:
  `VWAPSentinelAPI` (8000), `VWAPSentinelWeb` (3000), plus the legacy
  Streamlit (8501) and Gradio proxy (7860). `VWAPSentinelWatchdog` covers all
  four ports.

### Phase 2 addendum - owner FYERS re-login from the admin panel

- [x] `GET /api/v1/admin/fyers/login-url` (admin key) builds a FYERS auth URL
      with an HMAC-signed, 10-minute OAuth state
- [x] `GET /api/v1/fyers/callback` verifies state, exchanges the code and
      stores the token server-side; no token is returned to clients
- [x] Admin panel shows FYERS status, token age and a **Connect / Re-login
      FYERS** button (Next.js route handler keeps the admin key server-side)
- [x] 7 new tests; full suite still green
- [ ] User must register `FYERS_BACKEND_REDIRECT_URI`
      (`http://localhost:8000/api/v1/fyers/callback`) in the FYERS dashboard

---

## 16. Phase 3 (partial) - admin can run scans and inspect results

- [x] `scan_runs`, `scan_results`, `scan_result_candles` (migration
      `0003_scan_snapshots`)
- [x] Scanner service over stored PostgreSQL candles (reuses legacy detector)
- [x] Immutable snapshots: every run appends; history never mutates
- [x] Pattern-window OHLCV preserved per result
- [x] Config hash stored per run; no scanner settings UI yet
- [x] PostgreSQL advisory lock blocks overlapping scans (HTTP 409)
- [x] Admin APIs: POST run, list, latest, detail
- [x] Admin UI `/admin/scans`: Run scan now, latest results table, run history
- [x] Verified end-to-end through the Next.js route: run #1 created via UI
- [x] 5 new tests; full suite 89 passed

Caveats:
- Live results require FYERS login + ingestion. The verification run completed
  against an empty market-data database (0 instruments, 0 matches).
- No scheduler/automatic scan yet (Phase 4); no customer scan views (Phase 8).
- Scanner config is the default `PatternConfig`; admin settings UI is pending.

### Phase 3 completion - public scanner APIs and scan UI

- [x] Public endpoints: `/scanner/current`, `/history`,
      `/history/{id}`, `/results/{id}`, `/chart/{symbol}`,
      `/comparison`, `/symbols/{symbol}/appearances`
- [x] History filters: symbol, classification, distance band, expiry, date
      range, pagination
- [x] Forming candles excluded before indicator calculation
- [x] Per-instrument failures counted (`failed_instruments`) with error summary
- [x] Next.js pages: `/current`, `/scans`, `/scans/{id}` (with
      `?compare_to=<run>`), `/chart/{symbol}`
- [x] Custom SVG candlestick chart: AVWAP red, session VWAP blue,
      detected-pattern highlight, legend and timestamps
- [x] Verified end-to-end with temporary demo data (run #3, 1 match):
      chart rendered `<svg>`, AVWAP/VWAP lines, classification and highlights;
      demo instrument and run deleted afterwards
- [x] Full suite: 97 passed (including PostgreSQL integration)

Remaining:
- Customer auth/RBAC (Phase 5) - scanner endpoints are currently open.
- Admin scanner settings UI and configurable thresholds (later phase).
- Scheduler / automatic scans (Phase 4).

---

## 17. Phase 4 - scheduler, automated pipeline and admin controls

- [x] `scheduler_settings` singleton (enabled, interval, market hours,
      timezone, holidays, manual-outside-hours, next/last run)
- [x] `pipeline_jobs` + `pipeline_job_logs` (migration `0005_scheduler_pipeline`)
- [x] Ingestion jobs link to pipeline jobs; scan runs record pipeline and
      ingestion job ids
- [x] Dedicated scheduler process with PostgreSQL advisory single-instance lock
- [x] Dedicated worker process: `FOR UPDATE SKIP LOCKED` claims, heartbeats,
      cooperative cancellation, stale-job recovery
- [x] Pipeline executor: ingestion -> scan, partial/failed handling, immutable
      snapshots preserved
- [x] Market calendar (Asia/Kolkata weekends + configurable holidays, session
      hours) and stale-scan confirmation
- [x] Admin APIs: status, settings, pause/resume, refresh, run-scanner, cancel,
      jobs, logs, summary (admin key protected)
- [x] Next.js `/admin/pipeline` live status, controls, polling jobs table and
      per-job detail with logs
- [x] Dockerfiles for backend/web; compose adds migrate, backend, worker,
      scheduler, web; images built successfully
- [x] Tests: 117 passed

Live verification:
- Pipeline job #1 (MANUAL FULL_PIPELINE) via worker:
  ingestion job #2, 651/652 instruments, 1 failed (no data), scan run #14
  (14 matches), 652 per-instrument logs, PARTIALLY_COMPLETED in 147.5s.
- Scan-only job #2: COMPLETED in 9.7s, scan run #15 (14 matches).
- Scheduler runs and correctly skips on a closed market (Saturday); decision
  gate unit-tested for Monday open, paused, not-due and weekend cases.
- Admin pause/resume and settings PATCH verified against PostgreSQL.

Notes:
- No Redis/Celery: a dedicated worker + scheduler with DB locks was simpler and
  is already running locally; Redis remains available for future fan-out.
- Automatic market-hours enqueue needs a trading day to fire live.

---

## 18. Phase 5 - authentication, authorization and user management

- [x] UUID users, roles, user_roles, refresh_tokens, user_sessions,
      email_verification_tokens, password_reset_tokens, audit_logs
      (migration `0006_auth`, roles seeded)
- [x] Argon2id hashing, password policy, normalized unique emails
- [x] Registration + email verification + resend (rate limited)
- [x] JWT access tokens (issuer/audience/expiry validated) and opaque refresh
      tokens stored hashed
- [x] Refresh rotation, token-family reuse detection and revocation
- [x] Sessions list/revoke, logout, logout-all, password reset/change
- [x] RBAC dependencies; scanner APIs require active accounts; admin APIs
      accept JWT admin or service key
- [x] Admin user search/filter/sort, status, role and session controls with
      privilege-escalation guards
- [x] Audit logging and SUPER_ADMIN-only audit endpoint
- [x] Secure bootstrap CLI (idempotent, audited)
- [x] Next.js auth pages, route guards, profile and security screens,
      cookie/CSRF-aware client and server auth helpers
- [x] Tests: 136 passed

Live verification:
- SUPER_ADMIN bootstrapped and logged in through the Next.js auth proxy.
- Admin pages (`/admin`, `/admin/pipeline`) 200 with admin cookie.
- Customer registered, verified via dev token, logged in; `/current`, `/scans`,
  profile 200; customer `/api/v1/admin/users` 403; `/admin` redirects to `/`.
- Unauthenticated `/admin` redirects to `/login`.
- Known setup note: bootstrap email must use a real domain (e.g.
  `admin@yourdomain.dev`); `.local` is rejected by email validation.

---

## 19. Premium landing page and login redesign

- [x] Public landing page at `/` with premium fintech visual system
      (dark navy, mint/sky accents, Inter, glass navbar, fine borders)
- [x] Navbar with anchor navigation, mobile menu, Login and Get Started
- [x] Hero with illustrative candlestick chart (contract AVWAP red,
      session VWAP blue, highlighted consolidation window)
- [x] Features, workflow, scanner preview, strategy, comparison, pricing
      preview (Coming Soon), accessible FAQ, final CTA and footer
- [x] Pricing buttons disabled with explicit Coming Soon state
- [x] Two-column login page with branded illustration, validation,
      show/hide password and role-based redirects
- [x] Register/verify/forgot/reset pages aligned to the same design system
- [x] Middleware renews expired access cookies via refresh rotation
- [x] Customer dashboard moved to `/dashboard`; public landing owns `/`
- [x] Server/client API base split (`API_INTERNAL_URL` vs
      `NEXT_PUBLIC_API_BASE_URL`)
- [x] Production build succeeds; web Docker image rebuilt
- [x] Verified: landing/login/register 200, protected routes redirect,
      customer pages 200, refresh-only cookie renewal works

Notes:
- Sample chart/table values are illustrative and labelled as such.
- No automated browser/E2E suite yet; verification used build + HTTP flows.
- Pricing remains a preview until the subscription phase.

---

## 20. Admin panel and customer workspace UI

- [x] Role-aware collapsible sidebar with customer/admin sections and mobile menu
- [x] Admin overview from live APIs: users, market data, scheduler, pipeline,
      latest scan, audit (SUPER_ADMIN)
- [x] Admin market data with FYERS status, coverage and searchable/filterable
      instrument table + pagination
- [x] Admin scheduler/jobs aliases; job detail with logs and cancellation
- [x] Admin scan history with snapshot links; legacy routes redirect
- [x] Admin users UI: search, role/status filters, pagination, suspend/reactivate,
      promote/demote (SUPER_ADMIN), revoke sessions
- [x] Roles page and explicit monetization/feature-flag integration placeholders
- [x] Audit log table (SUPER_ADMIN) and settings page for implemented settings
- [x] Customer dashboard redesign using real scan/market APIs
- [x] Customer scanner with search, pattern/expiry filters, sorting, pagination
- [x] Scanner detail page explaining stored match fields
- [x] Chart alias with AVWAP/VWAP; history list/detail aliases; profile/security
- [x] Watchlist/strategies/subscription/billing clearly marked unavailable
- [x] Backend: instrument search `q` filter
- [x] Legacy routes redirect to the new application routes
- [x] Production build succeeds; Docker web image rebuilt
- [x] Backend regression suite: 136 passed

Verified HTTP flows:
- All admin routes 200 for SUPER_ADMIN; customer `/admin` redirects to `/`.
- Customer pages 200; customer nav does not expose admin sections.
- Admin users table lists real accounts; audit logs show real events.
- Legacy redirects verified.

Limitations:
- Shared `(app)` route group with role-aware navigation instead of physically
  separate `(customer)`/`(admin)` groups.
- No automated browser/E2E tests; verification used HTTP/build checks.
- Missing modules render integration placeholders listing required endpoints.

---

## 21. Docker development and Neon production configuration

- [x] Compose split: `compose.yaml`, `compose.dev.yaml`, `compose.prod.yaml`
- [x] Dev PostgreSQL (`scanner`/`local_dev_password`/`avwap_scanner`) on a
      dedicated `postgres_dev_data` volume, Redis, API hot reload, Next dev
- [x] Production overlay: Neon via `.env.production`, no PostgreSQL container,
      redis internal, restart policies, health checks, small pools
- [x] Runtime Neon placeholder resolution with URL-encoded password
      (`${NEON_DB_PASSWORD}` and escaped Compose `$${...}`)
- [x] Pool/SSL settings: `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`,
      `DB_POOL_RECYCLE`, `DATABASE_REQUIRE_SSL`
- [x] `APP_ENV` alias for environment selection
- [x] Frontend Dockerfile dev target; migration stays a one-shot service
- [x] Env examples: `.env.example`, `.env.development.example`,
      `.env.production.example`; `.gitignore` exceptions
- [x] Existing local data migrated into Docker dev DB via pg_dump/restore
      (652 instruments, 117,425 candles, 2 users, 15 scans)
- [x] Dev verification: health 200, Alembic head, customer login/pages, manual
      scan job completed by worker, no password in logs
- [x] Production images built; Neon target/SSL/pool resolution verified without
      connecting (password not available to the agent)
- [x] Tests: 140 passed

Manual/remaining:
- Set the real `NEON_DB_PASSWORD` and public URLs in `.env.production`.
- Push images to Docker Hub with real tags and deploy with
  `docker compose --env-file .env.production -f compose.yaml -f compose.prod.yaml up -d`.
- Old `postgres_data` volume is preserved; dev uses new `postgres_dev_data`.

---

## 22. Free PaaS deployment (Vercel + Render + Neon)

- [x] Optional in-process worker and scheduler (`RUN_WORKER_INPROCESS`,
      `RUN_SCHEDULER_INPROCESS`) started via FastAPI lifespan
- [x] `render.yaml` free Docker web service with Alembic-on-boot, health check,
      current-expiry ingestion, SSL and small Neon pools
- [x] Vercel frontend configuration documented
- [x] Keep-alive instructions for Render free sleep and 56-minute scheduler
- [x] No Redis requirement on the free plan (in-memory rate limits)
- [x] Tests: 139 passed, 1 skipped

Manual: create Render/Vercel services, set secrets, register FYERS callback,
bootstrap SUPER_ADMIN and add a keep-alive monitor.
