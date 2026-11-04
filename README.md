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
