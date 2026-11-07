---
title: VWAP Sentinel
sdk: gradio
app_file: app_gradio.py
pinned: false
---

# VWAP Sentinel

Anchored VWAP consolidations scanner for NSE futures.

A read-only Streamlit scanner for NSE futures that finds 1-hour candles
touching, hugging or consolidating around the **contract-start Anchored VWAP**
(the red line in the reference chart). Session VWAP is shown as a separate blue
line for context.

The application connects to FYERS API v3, discovers the current NSE futures
universe from the FYERS instrument master, downloads historical candles, and
classifies setups as **AVWAP TOUCH**, **AVWAP HUGGING**, **AVWAP CONSOLIDATION**
or **AVWAP RECLAIM**. It never places orders.

## Features

- FYERS OAuth login with local token storage and profile verification.
- Automatic NSE futures discovery from the public FYERS `NSE_FO` symbol master.
- No hardcoded futures symbols or expiry assumptions.
- Completed 1-hour candles only (the forming candle is discarded).
- Contract-start AVWAP, cumulative from the first available contract candle,
  never reset at session boundaries.
- Separate daily session VWAP for chart context.
- Configurable proximity, body ratio, candle count (1-5), classification and
  optional ATR range cap.
- Optional confirmation that the latest completed candle closed above the
  contract-start AVWAP and/or the session VWAP.
- Chunked historical requests, retry/backoff, rate limiting, disk cache.
- Streamlit summary, filterable/sortable results and interactive Plotly charts
  with pattern highlighting, price labels and AVWAP distance.
- Save, load and delete named scanner presets for the timeframe and all pattern
  filters.

## Project structure

```text
fyers-avwap-scanner/
    app.py                      Streamlit dashboard
    login.py                    OAuth, token store, auth verification
    config.py                   env settings, paths, logging

    data/
        fyers_client.py         FYERS SDK wrapper, retries, rate limits
        instrument_master.py    NSE_FO download/parse/filter
        historical_data.py      chunked history, normalization, cache integration
        cache.py                instrument + OHLCV disk caches

    indicators/
        avwap.py                contract-start AVWAP
        vwap.py                 daily-reset session VWAP
        atr.py                  Wilder ATR

    scanner/
        pattern_detector.py     AVWAP touch/hugging/consolidation/reclaim logic
        scan_engine.py          scan orchestration
        models.py               instruments, config, matches, report
        presets.py              JSON preset storage and validation

    dashboard/
        charts.py               Plotly candlestick chart
        components.py           summary, table, selection, errors
        presets_ui.py           sidebar save/load/delete controls

    tests/
        test_avwap.py
        test_fyers_client.py
        test_historical_data.py
        test_pattern_detector.py
        test_presets.py
        test_scanner.py

    presets/                    saved scanner presets (git-ignored)
        scanner_presets.json

    .streamlit/
        config.toml             dark theme

    .env.example
    .gitignore
    requirements.txt
    pytest.ini
    README.md
```

## Requirements

- Python 3.11 or newer
- A FYERS API app with the **Market Data** permission
- `fyers-apiv3`, pandas, numpy, Streamlit, Plotly, python-dotenv, requests

## Setup

### Windows PowerShell

```powershell
cd fyers-avwap-scanner
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
python -m streamlit run app.py
```

If script activation is blocked by execution policy, run the venv Python
directly:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

### macOS / Linux

```bash
cd fyers-avwap-scanner
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
$EDITOR .env
python -m streamlit run app.py
```

## Configuration

Fill in `.env`:

```ini
FYERS_CLIENT_ID=your-client-id
FYERS_SECRET_KEY=your-secret-key
FYERS_REDIRECT_URI=http://localhost:8501
```

Register the exact redirect URI in the FYERS API dashboard. It must match the
URL where Streamlit is running. The default is `http://localhost:8501`.

Never commit `.env` or token files. `.gitignore` already excludes `.env`,
`access_token.txt`, `token_meta.json`, token files, caches and logs.

### Optional environment settings

| Variable | Default | Purpose |
| --- | --- | --- |
| `FYERS_TIMEZONE` | `Asia/Kolkata` | Candle timezone / session dates |
| `FYERS_RESOLUTION` | `60` | Default scan resolution |
| `FYERS_HISTORY_CHUNK_DAYS` | `60` | Chunk size, keep below FYERS 100-day intraday cap |
| `FYERS_CONTRACT_LOOKBACK_DAYS` | `120` | History fetched before scan date; first returned candle is the anchor |
| `FYERS_HISTORY_CONT_FLAG` | `0` | Keep `0` for a single contract. `1` requests continuous futures and would mix expiries |
| `FYERS_HISTORY_CACHE_TTL` | `900` | OHLCV cache freshness in seconds |
| `FYERS_INSTRUMENT_CACHE_TTL` | `21600` | Symbol master cache freshness in seconds |
| `FYERS_PRESETS_FILE` | `presets/scanner_presets.json` | Local JSON file for saved scanner presets |
| `FYERS_REQUEST_RATE_PER_SEC` | `5` | Client-side request spacing |
| `FYERS_REQUEST_MAX_RETRIES` | `3` | Retries for transient/rate-limit responses |
| `FYERS_INCLUDE_INDEX_FUTURES` | `false` | Include index futures by default |
| `FYERS_CHART_LOOKBACK` | `120` | Candles shown in the interactive chart |
| `FYERS_LOG_LEVEL` | `INFO` | Application log level |

## Login flow

1. Start Streamlit.
2. In the sidebar click **Generate FYERS login URL**.
3. Open the FYERS login URL and authenticate.
4. FYERS redirects to the configured redirect URI with an `auth_code`.
5. The app exchanges the code, stores the access token in `access_token.txt`,
   stores non-sensitive issuance metadata in `token_meta.json`, and verifies the
   token with `get_profile()`.
6. If the redirect does not land back in the app, paste the `auth_code` value
   into the sidebar field and click **Exchange authorization code**.

FYERS access tokens are short-lived (typically expiring daily). If verification
fails, the app prompts for login again. **Logout / clear token** removes the
local token files.

## Using the scanner

1. Connect to FYERS.
2. Choose the futures universe:
   - **Current active expiry** (nearest non-expired expiry per underlying) or
     **All active expiries**.
   - Include/exclude index futures.
   - Scan **all active contracts** or select specific contracts.
3. Choose the timeframe. The default is **1 hour (60 min)**.
4. Configure:
   - minimum/maximum candles (1-5),
   - maximum close distance above/below AVWAP,
   - maximum candle low distance below AVWAP,
   - maximum candle body ratio,
   - pattern classifications,
   - optional last-candle confirmation: close above AVWAP and/or close above
     session VWAP (enable either, both, or neither),
   - advanced pattern range / optional ATR cap.
5. Optionally save the current timeframe and pattern filters as a named preset
   under **Scanner presets**. Presets can be loaded or deleted later; universe
   and contract selection are not stored.
6. Click **Run AVWAP scan**.
7. Review the summary and results table. Results are sorted by absolute
   distance from AVWAP, closest first.
8. Select a result to open its chart. The red line is contract-start AVWAP, the
   blue line is session VWAP, and the detected candles are highlighted.
9. Download the result table as CSV if needed.

The first scan of the entire universe can take a few minutes because each
contract needs historical requests. Subsequent scans use the disk cache and are
much faster. Use **Clear historical cache** after changing data assumptions.

### Scanner presets

The preset section stores the selected timeframe and every pattern filter. The
preset name is chosen in the sidebar; saving with an existing name overwrites it.
Presets are stored locally in `presets/scanner_presets.json` (configurable with
`FYERS_PRESETS_FILE`) and are ignored by git. Deleting a preset never deletes
market data or scan results.

## AVWAP and pattern logic

### Contract-start AVWAP

For every completed candle:

```text
Typical Price = (High + Low + Close) / 3
AVWAP = cumulative(Typical Price × Volume) / cumulative(Volume)
```

The cumulative calculation begins at the contract's **first available candle**
and continues through the latest completed candle. It is **not reset daily**.
The historical fetch starts well before the contract listing date and uses the
first returned candle as the anchor. The default 120-day lookback comfortably
covers the maximum NSE futures contract tenure.

Session VWAP is calculated separately and resets each trading day. It is shown
on the chart and can optionally be used as a last-candle close filter.

### Default detector thresholds

| Rule | Default |
| --- | --- |
| Max close above AVWAP | 0.50% |
| Max close below AVWAP | 0.20% |
| Max candle low below AVWAP | 0.30% |
| Max candle body ratio `|close-open|/(high-low)` | 0.35 |
| Pattern candle count | 1 to 5 |
| Max high-low range across the pattern | 2.0% of AVWAP |
| Optional ATR candle range cap | 2.0 × ATR(14) |
| Touch tolerance | 0.10% of AVWAP |
| Consolidation classification | >= 3 candles and <= 1.0% window range |
| Hugging classification | >= 2 candles near/touching AVWAP |
| Last candle close above AVWAP | Off (optional) |
| Last candle close above session VWAP | Off (optional) |

Every candle in the detected window must satisfy the proximity and small-body
conditions. The detector takes the longest eligible contiguous run ending at
the latest completed candle, then shortens it from the oldest side if the total
range is too wide.

The two optional close filters look only at the most recent completed candle.
Each enabled filter requires a **strict** close above its reference line; when
both are enabled the close must be above AVWAP **and** session VWAP.

### Classifications

- **AVWAP TOUCH** - price or a candle low reached the AVWAP.
- **AVWAP HUGGING** - multiple small candles are clustered near the AVWAP.
- **AVWAP CONSOLIDATION** - three or more small candles in a narrow range near
  the AVWAP.
- **AVWAP RECLAIM** - an earlier candle in the pattern closed below AVWAP and
  the latest candle closed back above it.

There is no breakout requirement and no minimum of 6-10 candles. A single
qualifying small candle at AVWAP is eligible.

## Historical data and caching

- FYERS intraday history is requested in chunks (default 60 days) because the
  API caps each intraday request at 100 days.
- Requests go through retry/backoff and a client-side rate limiter.
- Raw instrument master: `cache/instruments/NSE_FO.csv`.
- Contract history: `cache/history/<symbol>_<resolution>_<cont_flag>.csv` plus a
  small JSON metadata file.
- Fresh cache hits make no API request.
- Stale cache is refreshed incrementally from the last cached date (with a
  one-day overlap), then merged and de-duplicated.
- If a transient history refresh fails and cached candles exist, the scanner
  falls back to the cached data and logs a warning. Authentication failures are
  never hidden.
- Missing candles are tolerated; duplicate timestamps are removed and candles
  are sorted chronologically.
- The currently forming candle is removed before AVWAP/pattern calculation.

## Tests

```bash
python -m pytest -q
```

The suite uses synthetic candles only and covers:

- AVWAP formula, typical price, contract-start anchoring, no daily reset,
  zero-volume handling, session VWAP reset;
- incomplete-candle removal;
- small-candle body ratio and ATR range cap;
- AVWAP proximity rejection above and below;
- pattern detection with exactly 1, 2, 3, 4 and 5 candles;
- candle low touching AVWAP;
- AVWAP reclaim classification;
- optional last-candle close above AVWAP and/or session VWAP;
- missing market data;
- expired futures exclusion and current-expiry preference;
- instrument master parsing (options, invalid symbols, duplicates);
- history cache timestamp round-trip;
- scan engine matching, error handling and distance sorting;
- preset JSON round-trip, overwrite, delete, invalid files and invalid values;
- FYERS auth-error detection, rate-limit retry and invalid-symbol fast failure.

## Streamlit Community Cloud

The app deploys unchanged to [share.streamlit.io](https://share.streamlit.io):
`app.py` is the entry point, `requirements.txt` installs dependencies and
`runtime.txt` pins Python 3.12.

1. Sign in at share.streamlit.io with GitHub and choose **Create app**.
2. Repository `raj577/VWAP-Sentinel`, branch `main`, main file `app.py`.
3. Under **Advanced settings -> Secrets**, paste (TOML):

   ```toml
   FYERS_CLIENT_ID = "your-client-id"
   FYERS_SECRET_KEY = "your-secret-key"
   FYERS_REDIRECT_URI = "https://<your-app>.streamlit.app"
   FYERS_TOKEN_FILE = "data/access_token.txt"
   FYERS_TOKEN_META_FILE = "data/token_meta.json"
   FYERS_CACHE_DIR = "data/cache"
   FYERS_LOG_DIR = "data/logs"
   FYERS_PRESETS_FILE = "data/presets.json"
   ```

   Secrets are read with `st.secrets` when the matching environment variable
   is absent (`config.py`). Relative paths resolve against the repository root.
4. Register `https://<your-app>.streamlit.app` as the redirect URI in the FYERS
   API dashboard, then deploy and log in through the app.

Cloud containers are ephemeral: the token, cache and presets disappear on
reboot, so log in again afterwards. Community Cloud apps are public and one
stored token serves every visitor - deploy it for personal use or add a
password gate before sharing the URL.

## Hugging Face Space (Gradio)

The repository ships two entry points that share the same scanner code:

- `app.py` - Streamlit, for local use (`streamlit run app.py`, port 8501) and
  for Streamlit Community Cloud.
- `app_gradio.py` - deployment shell for the Hugging Face Space
  (`python app_gradio.py`, port 7860). Gradio starts internally only because
  ZeroGPU requires a launched Gradio app; the Streamlit UI is reverse-proxied
  at the site root over HTTP and WebSocket.

The Space metadata lives in the YAML header above (`sdk: gradio`,
`app_file: app_gradio.py`). To deploy:

1. Create a Gradio Space and add these repository secrets under
   **Settings -> Variables and secrets**:
   - `FYERS_CLIENT_ID`
   - `FYERS_SECRET_KEY`
   - `FYERS_REDIRECT_URI=https://<owner>-<space>.hf.space`
   - `FYERS_TOKEN_FILE=/home/user/data/access_token.txt`
   - `FYERS_TOKEN_META_FILE=/home/user/data/token_meta.json`
   - `FYERS_CACHE_DIR=/home/user/data/cache`
   - `FYERS_LOG_DIR=/home/user/data/logs`
   - `FYERS_PRESETS_FILE=/home/user/data/presets.json`
2. Register the same HTTPS URL as the redirect URI in the FYERS API dashboard.
3. Push this repository to the Space remote
   (`git remote add space https://huggingface.co/spaces/<owner>/<space>`).

Open the Space, click **Generate FYERS login URL**, complete the FYERS login,
and the `auth_code` is exchanged automatically when FYERS redirects back.
Space storage is ephemeral, so the saved token and cache disappear on restart
and you simply log in again. Keep `.env` and `access_token.txt` out of git.

The live scanner does not use synthetic data.

## Implementation phases

1. **Authentication** - OAuth URL generation, auth-code exchange, token store,
   profile verification, safe error handling.
2. **Universe discovery** - live `NSE_FO` master download, validated futures
   symbols, expiry filtering, current-expiry preference.
3. **Historical data** - 60-minute candles, chunking, retries, normalization,
   duplicate handling, cache.
4. **AVWAP** - first-available-candle anchor, cumulative typical-price VWAP,
   separate daily session VWAP.
5. **Pattern detector** - proximity, small bodies, ATR sanity check, 1-5 candle
   windows, classification.
6. **Dashboard** - filters, summary, results table, interactive chart.
7. **Hardening** - caching, rate limits, logging, token expiry handling, tests.

During development the instrument-master parser was validated against the live
FYERS master (667 futures contracts, 219 current-expiry stock futures at the
time of validation). Live OAuth/profile verification and real candle downloads
require your FYERS credentials and Market Data entitlement; without them the
application stops at the login screen rather than substituting fake data.

## Troubleshooting

- **Missing credentials** - fill `.env`, ensure the file is in the project root,
  and restart Streamlit.
- **Redirect URI mismatch** - register the exact URI in the FYERS dashboard and
  match `FYERS_REDIRECT_URI`.
- **Token invalid/expired** - use **Logout / clear token**, then login again.
- **Market Data permission error** - enable historical data/market data access
  for your FYERS API app.
- **Rate limit** - lower `FYERS_REQUEST_RATE_PER_SEC` or wait and rerun; cached
  contracts are skipped.
- **Instrument master download failure** - the app reuses a stale cached master
  when available; otherwise check network access to `public.fyers.in`.
- **No results** - widen proximity/body thresholds, scan all active expiries, or
  confirm the contracts have enough completed history.

## Safety and limitations

- This is a **market scanner only**. No order placement or trading code is
  called.
- The pattern detector is a configurable technical heuristic, not investment
  advice. Validate results independently.
- FYERS API data availability, entitlements and rate limits are outside this
  application's control.
- Use a dedicated local machine/environment for token storage and never commit
  credentials.

## SaaS backend (Phases 1-2)

A FastAPI service backs the multi-user SaaS platform. The legacy Streamlit app
above stays runnable until the Next.js client reaches parity.

```
FYERS API (owner token, server-side only)
  -> ingestion service (backend/services/ingestion.py)
  -> PostgreSQL (instruments, market_candles, ingestion_jobs)
  -> FastAPI /api/v1
  -> Next.js (frontend/) and future Flutter
```

### Prerequisites

- Docker Desktop (PostgreSQL 16 + Redis 7)
- Python 3.11+
- Node.js 20+ (for the web app)

### Backend setup

```powershell
.\.venv-backend\Scripts\python.exe -m pip install -r requirements-backend.txt
docker compose up -d postgres redis
$env:DATABASE_URL="postgresql+psycopg://avwap:avwap@127.0.0.1:5432/avwap"
.\.venv-backend\Scripts\python.exe -m alembic upgrade head
.\scripts\run_api.cmd
```

Environment variables (see `.env.example`):

```
DATABASE_URL, DATABASE_ECHO, REDIS_URL, ENVIRONMENT, LOG_LEVEL
CORS_ORIGINS, SCHEDULER_INTERVAL_MINUTES
ADMIN_API_KEY, MARKET_DATA_TIMEFRAME
FYERS_BACKEND_REDIRECT_URI, FRONTEND_BASE_URL, FYERS_LOGIN_STATE_TTL

FYERS_CLIENT_ID, FYERS_SECRET_KEY, FYERS_REDIRECT_URI
FYERS_TOKEN_FILE, FYERS_TOKEN_META_FILE
```

FYERS credentials and the access token are read by the backend through the
existing `config.py` / `login.py` integration. They are never returned by an
API. Customers never authenticate with FYERS.

### Market data ingestion

```powershell
.\scripts\ingest.cmd
# or
.\.venv-backend\Scripts\python.exe -m backend.cli.ingest --triggered-by cli
```

The job verifies the FYERS token, discovers active NSE stock futures, fetches
1-hour candles, upserts them (unique on instrument + timeframe + timestamp),
records per-instrument results and stores job counters. Expired contracts and
index futures are excluded. Different expiries are separate instruments, so
contract-start AVWAP never mixes them.

### Owner FYERS re-login (admin panel)

The platform owner refreshes FYERS from the admin panel; customers never log in
to FYERS.

1. Register `FYERS_BACKEND_REDIRECT_URI` (default
   `http://localhost:8000/api/v1/fyers/callback`) in the FYERS API dashboard.
2. Open `http://localhost:3000/admin` and click **Connect / Re-login FYERS**.
3. Complete the FYERS login. FYERS redirects to the backend callback, which
   validates the HMAC-signed OAuth state, exchanges the code and stores the
   token server-side with the same `TokenStore` as the Streamlit app.
4. The callback page redirects back to the admin panel, which shows
   `CONNECTED`; ingestion can now run.

The login URL endpoint requires the admin key, and the callback is protected by
a short-lived signed state (10 minutes by default). The token itself is never
returned by any API. The legacy Streamlit re-login still works, but is no longer
required for the SaaS.

### API overview


| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/health/live` | process liveness |
| GET | `/api/v1/health/ready` | database readiness |
| GET | `/api/v1/market-data/status` | FYERS status, counts, last job |
| GET | `/api/v1/market-data/instruments` | paginated futures list |
| GET | `/api/v1/market-data/instruments/{symbol}` | one contract |
| GET | `/api/v1/market-data/candles/{symbol}` | stored candles |
| GET | `/api/v1/market-data/avwap/{symbol}` | AVWAP / session VWAP series |
| GET | `/api/v1/admin/market-data/jobs` | job history (admin key) |
| GET | `/api/v1/admin/market-data/jobs/{id}` | job + instrument results |
| GET | `/api/v1/admin/market-data/ingestion-summary` | aggregate health |
| POST | `/api/v1/admin/scans/run` | run the scanner now (admin key) |
| GET | `/api/v1/admin/scans` | scan run history |
| GET | `/api/v1/admin/scans/latest` | latest completed scan with results |
| GET | `/api/v1/admin/scans/{id}` | one immutable scan snapshot |
| GET | `/api/v1/scanner/current` | latest completed scan with results |
| GET | `/api/v1/scanner/history` | paginated history with filters |
| GET | `/api/v1/scanner/history/{id}` | one historical scan |
| GET | `/api/v1/scanner/results/{id}` | result plus preserved candles |
| GET | `/api/v1/scanner/chart/{symbol}` | chart-ready AVWAP/VWAP series |
| GET | `/api/v1/scanner/comparison` | two-run symbol comparison |
| GET | `/api/v1/scanner/symbols/{symbol}/appearances` | first/latest appearance |
| GET | `/api/v1/admin/scheduler/status` | scheduler + data status |
| GET/PATCH | `/api/v1/admin/scheduler/settings` | read/update interval, hours, holidays |
| POST | `/api/v1/admin/scheduler/pause` | pause automatic runs |
| POST | `/api/v1/admin/scheduler/resume` | resume automatic runs |
| POST | `/api/v1/admin/pipeline/refresh` | queue ingestion + scan (manual) |
| POST | `/api/v1/admin/pipeline/run-scanner` | queue a scan only |
| POST | `/api/v1/admin/pipeline/jobs/{id}/cancel` | cooperative cancellation |
| GET | `/api/v1/admin/pipeline/jobs` | job history with filters |
| GET | `/api/v1/admin/pipeline/jobs/{id}` | one job |
| GET | `/api/v1/admin/pipeline/jobs/{id}/logs` | per-instrument logs |
| GET | `/api/v1/admin/pipeline/summary` | pipeline health counts |
| POST | `/api/v1/auth/register` | create a customer account |
| POST | `/api/v1/auth/login` | JWT + refresh cookies/tokens |
| POST | `/api/v1/auth/refresh` | rotate refresh token |
| POST | `/api/v1/auth/logout` / `logout-all` | revoke one/all sessions |
| GET/DELETE | `/api/v1/auth/sessions[/{id}]` | list/revoke sessions |
| POST | `/api/v1/auth/verify-email` / `resend-verification` | email verification |
| POST | `/api/v1/auth/forgot-password` / `reset-password` | password reset |
| POST | `/api/v1/auth/change-password` | authenticated password change |
| GET/PATCH | `/api/v1/auth/me` | profile |
| GET | `/api/v1/admin/users` | user search/filter/sort |
| PATCH | `/api/v1/admin/users/{id}/status` / `role` | suspend/role change |
| POST | `/api/v1/admin/users/{id}/revoke-sessions` | revoke user sessions |
| GET | `/api/v1/admin/audit-logs` | SUPER_ADMIN audit view |
| GET | `/api/v1/admin/fyers/login-url` | start owner FYERS login (admin key) |
| GET | `/api/v1/fyers/callback` | FYERS OAuth callback (public) |


Example:

```powershell
curl.exe "http://localhost:8000/api/v1/market-data/status"
curl.exe "http://localhost:8000/api/v1/market-data/instruments?page=1&page_size=5&active=true"
curl.exe "http://localhost:8000/api/v1/market-data/avwap/NSE:RELIANCE26NOVFUT?limit=50"
curl.exe -H "X-Admin-Key: dev-admin-key" "http://localhost:8000/api/v1/admin/market-data/jobs"
```

Sample status response:

```json
{
  "timeframe": "60",
  "instruments_total": 219,
  "instruments_active": 219,
  "candles_total": 18240,
  "latest_candle_at": "2026-11-07T09:15:00Z",
  "fyers": {"status": "CONNECTED", "message": "FYERS connection is healthy."},
  "last_job": {"id": 1, "status": "COMPLETED", "candles_inserted": 18240}
}
```

Admin endpoints accept the interim `X-Admin-Key` header. An empty
`ADMIN_API_KEY` disables them (503) rather than leaving them open. JWT roles
replace this in Phase 5.

### Next.js web app

```powershell
cd frontend
npm install
npm run build
npm run start      # http://localhost:3000 (or npm run dev)
```

`frontend/.env.local`:

```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
ADMIN_API_KEY=dev-admin-key
```

Only `NEXT_PUBLIC_*` values reach the browser. The admin key is read by the
Next.js server component and is never shipped to the client. The app shell
includes sidebar navigation, dashboard metrics, active contracts, an API health
indicator and an admin ingestion table. Login, scan history and subscriptions
are placeholders until their phases land.

### Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

PostgreSQL upsert integration check (optional, against the Docker database):

```powershell
$env:TEST_DATABASE_URL="postgresql+psycopg://avwap:avwap@127.0.0.1:5432/avwap"
.\.venv\Scripts\python.exe -m pytest -q tests\test_postgres_integration.py
```

### Landing page and customer scans

The public product landing page is `/` (hero, features, workflow, scanner
preview, strategy, pricing preview, FAQ, final CTA, footer). It links to
`/login` and `/register`.

Authenticated customer pages:

- `/dashboard` - customer dashboard (market data status, counters, contracts).
- `/current` - latest completed scan, counters and matching contracts.
- `/scans` - paginated history with symbol/classification filters.
- `/scans/{id}` - immutable snapshot, results and two-run comparison
  (`?compare_to=<run_id>`).
- `/chart/{symbol}` - 1-hour candlesticks with contract-start AVWAP (red),
  session VWAP (blue), highlighted detected candles and pattern metadata.

The API is the single source for both the web app and the future Flutter app:

```powershell
curl.exe "http://localhost:8000/api/v1/scanner/current"
curl.exe "http://localhost:8000/api/v1/scanner/history?page=1&page_size=20&symbol=NSE:RELIANCE26NOVFUT"
curl.exe "http://localhost:8000/api/v1/scanner/comparison?base_run_id=1&compare_run_id=2"
curl.exe "http://localhost:8000/api/v1/scanner/chart/NSE:RELIANCE26NOVFUT?limit=240"
```

Scanner behaviour: reads PostgreSQL candles only, drops forming candles,
skips expired/inactive contracts, reuses the contract-start AVWAP and pattern
detector from the legacy app, and stores one immutable run per execution with
the exact pattern-window OHLCV.

### Admin and customer applications

Both applications use one authenticated shell with role-aware navigation and
backend-enforced authorization.

Admin routes:

```
/admin                 operational overview (users, market data, scheduler, jobs, scan)
/admin/market-data     FYERS status, coverage and instrument table
/admin/scheduler       pause/resume, interval, refresh, run scanner
/admin/jobs            pipeline jobs, polling, details and cancellation
/admin/jobs/{id}       stage, counters and per-instrument logs
/admin/scanner         active config version (publishing API pending)
/admin/scan-history    immutable scan runs and links to snapshots
/admin/users           search/filter users, suspend, roles, revoke sessions
/admin/roles           role catalogue and permission descriptions
/admin/plans|trials|entitlements|payments|feature-flags
/admin/audit-logs      SUPER_ADMIN audit view (API available)
/admin/settings        implemented scheduler/market-data settings
```

Customer routes:

```
/dashboard             overview, latest results, history, freshness
/dashboard/scanner     filter/sort/search current scan results
/dashboard/scanner/{symbol}  stored match fields and explanation
/dashboard/chart/{symbol}    candlestick + AVWAP/VWAP chart
/dashboard/history     immutable scan history
/dashboard/history/{id}      snapshot detail and run comparison
/dashboard/watchlist|strategies|subscription|billing  integration placeholders
/dashboard/profile     profile
/dashboard/security    sessions and password
```

Legacy paths redirect: `/current` → `/dashboard/scanner`, `/scans` →
`/dashboard/history`, `/chart/{symbol}` → `/dashboard/chart/{symbol}`,
`/admin/pipeline` → `/admin/scheduler`, `/admin/scans` → `/admin/scan-history`.

Implemented with real APIs: market-data status/instruments (including a new
`q` search filter), scanner current/history/chart, scheduler status and
settings, pipeline jobs/logs/summary and actions, admin user management,
audit logs, authentication and sessions.

Backend APIs still missing (shown as explicit placeholders, never fake data):

```
plans, trials, entitlements, payments, feature flags
watchlists, strategy guides, subscription/billing for customers
scanner configuration publishing and admin role CRUD
admin user session details, audit filtering/pagination
```

UI note: rather than duplicating route groups, the existing authenticated
`(app)` group hosts both applications; the sidebar renders customer or admin
sections based on the backend-returned roles. This keeps one guard and one
middleware while keeping navigation distinct.

### Landing page and login experience

The public site (`/`) is a dark, premium fintech landing page with:

- Sticky navbar (Features, How It Works, Strategies, Pricing) and mobile menu.
- Hero with an illustrative candlestick/AVWAP dashboard preview.
- Feature cards, three-step workflow, scanner result preview, strategy
  methodology, comparison section, pricing preview and accessible FAQ.
- Clear "illustrative preview, not live market data" labels and a risk
  disclaimer in the footer.
- Pricing cards intentionally show a **Coming Soon** state; no fake purchase
  flow.

`/login` is a two-column auth experience with branding, chart illustration,
show/hide password, inline validation, generic credential errors and role-aware
redirects (`CUSTOMER → /dashboard`, `ADMIN/SUPER_ADMIN → /admin`). Register,
verify, forgot-password and reset-password pages share the same layout.

Session renewal: `frontend/middleware.ts` detects a missing (expired) access
cookie on protected routes, rotates it via `/auth/refresh` using the refresh and
CSRF cookies, then re-requests the page. If rotation fails, cookies are cleared
and the user is redirected to `/login`.

Server-side rendering uses `API_INTERNAL_URL` (defaults to the public API URL)
while the browser uses `NEXT_PUBLIC_API_BASE_URL`; this keeps Docker networking
correct without exposing secrets.

Metadata includes title, description, Open Graph and Twitter cards. Animations
respect `prefers-reduced-motion`.

### Authentication and users (Phase 5)

Roles: `SUPER_ADMIN`, `ADMIN`, `CUSTOMER`. Authorization is enforced in FastAPI
dependencies; the frontend guards only improve UX.

- Registration creates a `PENDING_VERIFICATION` customer with the CUSTOMER role.
- Passwords are hashed with Argon2id; the policy requires 10+ characters and
  three of lowercase/uppercase/digit/symbol.
- Email verification and password-reset tokens are stored only as SHA-256
  hashes, single-use and expiring (24h / 30m).
- Login returns a 15-minute access JWT and a 7-day opaque refresh token.
  Refresh tokens are hashed, grouped in families and rotated on every refresh.
  Reuse of a rotated token revokes the whole family.
- Web clients use HTTP-only `access_token`/`refresh_token` cookies plus a
  readable `csrf_token` cookie; state-changing cookie requests require the
  `X-CSRF-Token` header. Mobile clients can use the Bearer tokens returned by
  `/auth/login` and `/auth/refresh`.
- Sessions are listed and revocable per device; `logout-all` revokes every
  session for the user.
- Rate limits apply to register, login, refresh, verification, resend and
  password-reset endpoints (Redis when reachable, in-process fallback).
- Audit events are written for registration, login, logout, verification,
  password changes, role/status changes and session revocation. Only
  SUPER_ADMIN can read `/admin/audit-logs`.
- Scanner read APIs now require an authenticated, active account. Admin APIs
  accept an administrator JWT or the server-side service key.

Frontend pages: `/` (landing), `/register`, `/login`, `/verify-email`,
`/forgot-password`, `/reset-password`, `/dashboard`, `/dashboard/profile`,
`/dashboard/security/sessions`. Customer login redirects to `/dashboard`,
admin roles redirect to `/admin`; customer routes redirect to `/login`, and
admin routes additionally require ADMIN/SUPER_ADMIN.

#### SUPER_ADMIN bootstrap

There is no public bootstrap API. Run the CLI once against the migrated
database:

```powershell
$env:DATABASE_URL="postgresql+psycopg://avwap:avwap@127.0.0.1:5432/avwap"
.\.venv-backend\Scripts\python.exe -m backend.cli.bootstrap_admin `
  --email "admin@yourdomain.com" --password "Use-A-Strong!Passphrase123"
```

Or set `SUPER_ADMIN_EMAIL` / `SUPER_ADMIN_PASSWORD` and run it without flags.
The command refuses to create a second SUPER_ADMIN and records an audit event.
Docker equivalent:

```powershell
docker compose up -d --build
docker compose exec backend python -m backend.cli.bootstrap_admin `
  --email "admin@yourdomain.com" --password "Use-A-Strong!Passphrase123"
```

Change the bootstrap password after first login from
`/dashboard/security/sessions`.

### Scheduler and pipeline (Phase 4)

```
Scheduler process (one instance, advisory lock)
  -> PENDING pipeline_jobs (SCHEDULED)
      |
Worker process (FOR UPDATE SKIP LOCKED claims)
  -> ingestion (FYERS -> PostgreSQL) -> scanner -> immutable scan_run
      |
API / Next.js admin  (status, controls, progress, logs, cancel)
```

- Automatic refresh default: **56 minutes**, `Asia/Kolkata` scheduling, UTC
  storage. Interval, market hours, holidays and manual-outside-hours are stored
  in `scheduler_settings` and editable from the admin UI/API.
- Scheduled runs only enqueue while the market is open (weekends, configured
  holidays and outside 09:15–15:30 IST are skipped). Manual runs still work.
- Only one pipeline job may be PENDING/RUNNING at a time.
- A dedicated worker executes ingestion first, then scanning; the scan records
  `pipeline_job_id` and `ingestion_job_id`.
- Ingestion failures skip the scan and never touch the last successful
  snapshot. Cancellation is cooperative: the worker acknowledges it between
  instruments and marks the job CANCELLED.
- Every RUNNING job updates `heartbeat_at`; stale jobs are marked FAILED (or
  CANCELLED if cancellation was requested) by the worker recovery sweep.
- Per-instrument outcomes are copied into `pipeline_job_logs` for the job
  detail page.

Admin UI: `http://localhost:3000/admin/pipeline`

- Pause / resume, change interval, Update Market Data Now, Run Scanner Now.
- Live status cards (stage, processed/total, failures) poll every 5 seconds.
- Jobs table with status filter, pagination, cancel and per-job logs at
  `/admin/pipeline/{job_id}`.
- Stale data: `Run Scanner Now` first warns; the dialog offers
  `confirm_stale=true` to scan anyway.

Local commands (scheduled tasks already run these):

```powershell
.\scripts\run_worker.cmd        # pipeline worker
.\scripts\run_scheduler.cmd     # single scheduler instance
.\scripts\run_api.cmd
.\scripts\run_web.cmd
```

Docker (all services, images built):

```powershell
# stop the local Windows tasks first if ports 3000/8000/5432 are in use
docker compose up -d --build
docker compose ps
```

Environment variables (new in Phase 4):

```
SCHEDULER_ENABLED=true
SCHEDULER_INTERVAL_MINUTES=56
SCHEDULER_TICK_SECONDS=15
WORKER_POLL_SECONDS=2
JOB_HEARTBEAT_TIMEOUT_SECONDS=900
SCAN_STALE_WARNING_HOURS=24
MARKET_HOLIDAYS=2026-01-26,2026-03-04   # ISO dates, configuration only
```

Troubleshooting:

- Job stuck PENDING: worker not running (`VWAPSentinelWorker` / container).
- Job RUNNING with no progress: worker crashed; recovery marks it FAILED after
  the heartbeat timeout, then requeue.
- Scheduler does nothing: paused, market closed, or a job is already active.
  Check `/admin/scheduler/status` and `logs/scheduler.out.log`.
- FYERS auth errors: refresh the token from `/admin`; ingestion fails without
  touching stored candles.
- 409 on refresh: another pipeline is pending/running. Use the existing job.
- Stale scan warning: run ingestion or confirm stale scanning explicitly.

### Admin scans

Open `http://localhost:3000/admin/scans` to run the scanner on stored candles and
inspect results. Each run is an immutable snapshot: `scan_runs` stores the run
metadata and scanner config hash, `scan_results` stores the denormalised match
row, and `scan_result_candles` preserves the exact pattern-window OHLCV. Running
again creates a new run and never mutates history. A PostgreSQL advisory lock
prevents overlapping scans (second request gets HTTP 409).

```powershell
curl.exe -X POST -H "X-Admin-Key: dev-admin-key" "http://localhost:8000/api/v1/admin/scans/run"
curl.exe -H "X-Admin-Key: dev-admin-key" "http://localhost:8000/api/v1/admin/scans/latest"
```

### Known limitations

- FYERS access tokens expire daily; refresh them from the admin panel
  (**Connect / Re-login FYERS**). Register
  `FYERS_BACKEND_REDIRECT_URI` (default
  `http://localhost:8000/api/v1/fyers/callback`) in the FYERS API dashboard
  once. Until the callback URL is registered, FYERS rejects the login.
- Authentication defaults are development-only: `AUTH_SECRET_KEY` has a
  placeholder value, `AUTH_DEV_EXPOSE_TOKENS=true` returns verification/reset
  tokens, `COOKIE_SECURE=false` and email uses the console provider. Harden
  these before any public deployment (strong secret, HTTPS cookies, SMTP).
- Access JWTs stay valid until they expire even after logout; logout revokes
  refresh tokens and sessions, not already-issued access tokens.
- Tokens are returned in the JSON response for future mobile clients; the web
  app relies on HttpOnly cookies and never stores tokens in browser storage.
- The `csrf_token` cookie is intentionally readable by JavaScript
  (double-submit pattern).
- Admin endpoints accept either an administrator JWT or the server-side
  `ADMIN_API_KEY` for operational tooling; rotate that key outside development.
- Docker images build and all containers start, but this Windows Docker Desktop
  instance did not publish host port 8000 for the API container, so the verified
  local path uses the scheduled tasks/scripts.
- Scanner thresholds currently use the default `PatternConfig`; an admin
  settings UI is pending.
- The scheduler was verified through its decision gate and live worker/API
  runs, but an automatic market-hours enqueue cannot fire on a weekend. On a
  trading day it enqueues at the configured interval.


- AVWAP values are computed on request, not materialised, to avoid drift.
- No table partitioning yet; revisit if candle volume grows substantially.
