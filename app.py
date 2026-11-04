"""Streamlit dashboard for the FYERS NSE futures contract-start AVWAP scanner."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="FYERS Futures AVWAP Scanner",
    layout="wide",
)

from config import Settings, setup_logging  # noqa: E402
from dashboard.charts import plot_pattern_chart  # noqa: E402
from dashboard.components import (  # noqa: E402
    render_match_metrics,
    render_results_table,
    render_scan_errors,
    render_summary,
    select_match,
)
from dashboard.presets_ui import render_preset_manager  # noqa: E402
from data.cache import HistoricalCache  # noqa: E402
from data.fyers_client import (  # noqa: E402
    AuthenticationError,
    FyersClient,
    FyersError,
)
from data.historical_data import HistoricalDataService  # noqa: E402
from data.instrument_master import (  # noqa: E402
    InstrumentMasterError,
    InstrumentMasterProvider,
    to_instruments,
)
from login import (  # noqa: E402
    AuthStatus,
    TokenStore,
    check_authentication,
    exchange_auth_code,
    extract_auth_code,
    generate_auth_url,
)
from scanner.models import PATTERN_TYPES, PatternConfig, ScanReport  # noqa: E402
from scanner.presets import PresetStore  # noqa: E402
from scanner.scan_engine import ScanEngine  # noqa: E402

logger = logging.getLogger("fyers_avwap.app")

TIMEFRAMES: dict[str, str] = {
    "1 hour (60 min)": "60",
    "2 hours (120 min)": "120",
    "4 hours (240 min)": "240",
}

FILTER_DEFAULTS: dict[str, Any] = {
    "f_timeframe": "1 hour (60 min)",
    "f_min": 1,
    "f_max": 5,
    "f_above": 0.50,
    "f_below": 0.20,
    "f_low": 0.30,
    "f_body": 0.35,
    "f_range": 2.0,
    "f_use_atr": True,
    "f_atr": 2.0,
    "f_cons_range": 1.0,
    "f_classes": list(PATTERN_TYPES),
    "f_close_above_avwap": False,
    "f_close_above_vwap": False,
}


def init_filter_defaults() -> None:
    """Seed widget state once so presets can update widgets without warnings."""
    for key, value in FILTER_DEFAULTS.items():
        st.session_state.setdefault(key, list(value) if isinstance(value, list) else value)


@st.cache_resource(show_spinner=False)
def get_instrument_provider(settings: Settings) -> InstrumentMasterProvider:
    return InstrumentMasterProvider(settings)


def _query_params() -> dict[str, Any]:
    try:
        return st.query_params.to_dict()
    except Exception:
        try:
            return st.experimental_get_query_params()
        except Exception:
            return {}


def _clear_query_params() -> None:
    try:
        st.query_params.clear()
    except Exception:
        try:
            st.experimental_set_query_params()
        except Exception:
            pass


def handle_oauth_callback(settings: Settings) -> None:
    """Handle FYERS redirect (?auth_code=...) exactly once and hide it from the URL."""
    code = extract_auth_code(_query_params())
    if not code:
        return
    if st.session_state.get("_processed_auth_code") == code:
        _clear_query_params()
        return

    st.session_state["_processed_auth_code"] = code
    try:
        exchange_auth_code(settings, code)
        st.session_state["auth_flash"] = "FYERS login successful. Access token stored locally."
    except AuthenticationError as exc:
        st.session_state["auth_flash_error"] = str(exc)
    finally:
        _clear_query_params()
        st.session_state.pop("auth_status", None)
        st.session_state.pop("auth_token_mtime", None)
    st.rerun()


def resolve_auth_status(settings: Settings) -> AuthStatus:
    """Reuse the verified status until the token file changes."""
    store = TokenStore(settings)
    try:
        mtime = store.token_path.stat().st_mtime_ns
    except OSError:
        mtime = None

    cached = st.session_state.get("auth_status")
    if cached is not None and st.session_state.get("auth_token_mtime") == mtime:
        return cached

    status = check_authentication(settings, verify=True)
    st.session_state["auth_status"] = status
    st.session_state["auth_token_mtime"] = mtime
    return status


def render_login_sidebar(settings: Settings, status: AuthStatus) -> None:
    st.header("FYERS connection")

    if not settings.credentials_configured:
        st.error("FYERS credentials are not configured.")
        missing = ", ".join(settings.missing_credentials())
        st.caption(f"Missing: {missing}")
        st.code(
            "FYERS_CLIENT_ID=...\nFYERS_SECRET_KEY=...\nFYERS_REDIRECT_URI=http://localhost:8501",
            language="ini",
        )
        st.caption("Copy .env.example to .env, fill it in, then restart Streamlit.")
        return

    if status.authenticated:
        st.success("Connected to FYERS")
        profile = status.profile or {}
        display_name = profile.get("display_name") or profile.get("name")
        if display_name:
            st.caption(f"Account: {display_name}")
        age = TokenStore(settings).age_hours()
        if age is not None:
            st.caption(f"Token stored {age:.1f} hour(s) ago.")
        if st.button("Logout / clear token", width="stretch"):
            TokenStore(settings).clear()
            for key in (
                "auth_status",
                "auth_token_mtime",
                "auth_url",
                "_processed_auth_code",
                "scan_report",
                "scan_signature",
                "selected_avwap_match",
                "scan_error",
            ):
                st.session_state.pop(key, None)
            st.rerun()
        return

    if status.token_present:
        st.warning("The stored FYERS token is invalid or expired.")
        st.caption(status.message)

    if st.button("1. Generate FYERS login URL", width="stretch"):
        try:
            st.session_state["auth_url"] = generate_auth_url(settings)
        except AuthenticationError as exc:
            st.error(str(exc))

    auth_url = st.session_state.get("auth_url")
    if auth_url:
        st.link_button("2. Open FYERS login", auth_url, width="stretch")
        with st.expander("Copy the authorization URL"):
            st.code(auth_url, language="text")
        st.caption(
            "After FYERS redirects back to your redirect URI, the app exchanges "
            "the auth code automatically. If the redirect does not land here, "
            "paste the auth_code below."
        )

    auth_code = st.text_input(
        "Authorization code",
        type="password",
        key="manual_auth_code",
        help="Paste the auth_code value from the FYERS redirect URL.",
    )
    if st.button("3. Exchange authorization code", width="stretch"):
        try:
            exchange_auth_code(settings, auth_code)
            st.session_state["auth_flash"] = "FYERS login successful. Access token stored locally."
            st.session_state.pop("auth_status", None)
            st.session_state.pop("auth_token_mtime", None)
            st.rerun()
        except AuthenticationError as exc:
            st.error(str(exc))


def build_pattern_config() -> tuple[PatternConfig | None, str | None, str]:
    min_candles = int(
        st.number_input(
            "Minimum candles in pattern",
            min_value=1,
            max_value=5,
            step=1,
            key="f_min",
        )
    )
    max_candles = int(
        st.number_input(
            "Maximum candles in pattern",
            min_value=1,
            max_value=5,
            step=1,
            key="f_max",
        )
    )
    if min_candles > max_candles:
        return None, "Minimum candles cannot exceed maximum candles.", ""

    max_above = float(
        st.number_input(
            "Max close above AVWAP (%)",
            min_value=0.0,
            max_value=10.0,
            step=0.05,
            key="f_above",
        )
    )
    max_below = float(
        st.number_input(
            "Max close below AVWAP (%)",
            min_value=0.0,
            max_value=10.0,
            step=0.05,
            key="f_below",
        )
    )
    max_low_below = float(
        st.number_input(
            "Max candle low below AVWAP (%)",
            min_value=0.0,
            max_value=10.0,
            step=0.05,
            key="f_low",
        )
    )
    max_body = float(
        st.number_input(
            "Maximum candle body ratio",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            key="f_body",
            help="|close-open| / (high-low). Lower values mean smaller/doji candles.",
        )
    )

    with st.expander("Advanced pattern constraints", expanded=False):
        max_range = float(
            st.number_input(
                "Maximum pattern range (% of AVWAP)",
                min_value=0.1,
                max_value=10.0,
                step=0.1,
                key="f_range",
                help="High-low range across all candles in the detected window.",
            )
        )
        use_atr = st.checkbox(
            "Cap each candle range at an ATR multiple",
            key="f_use_atr",
            help="ATR is used only as a small-candle sanity check.",
        )
        atr_multiple = float(
            st.number_input(
                "ATR range multiple",
                min_value=0.1,
                max_value=10.0,
                step=0.1,
                key="f_atr",
                disabled=not use_atr,
            )
        )
        consolidation_range = float(
            st.number_input(
                "Consolidation classification range (%)",
                min_value=0.1,
                max_value=10.0,
                step=0.1,
                key="f_cons_range",
                help="Patterns at least 3 candles wide below this range are labelled AVWAP CONSOLIDATION.",
            )
        )

    st.caption("Last candle confirmation")
    confirmation_column, vwap_column = st.columns(2)
    require_close_above_avwap = confirmation_column.checkbox(
        "Close above AVWAP",
        key="f_close_above_avwap",
        help=(
            "Keep only contracts whose most recent completed candle closed "
            "strictly above the contract-start AVWAP."
        ),
    )
    require_close_above_vwap = vwap_column.checkbox(
        "Close above session VWAP",
        key="f_close_above_vwap",
        help=(
            "Keep only contracts whose most recent completed candle closed "
            "strictly above the daily-reset session VWAP."
        ),
    )

    classifications = st.multiselect(
        "Pattern classification filter",
        options=list(PATTERN_TYPES),
        key="f_classes",
    )
    if not classifications:
        return None, "Select at least one pattern classification.", ""

    try:
        config = PatternConfig(
            max_close_above_pct=max_above / 100.0,
            max_close_below_pct=max_below / 100.0,
            max_low_below_pct=max_low_below / 100.0,
            max_body_ratio=max_body,
            min_candles=min_candles,
            max_candles=max_candles,
            max_window_range_pct=max_range / 100.0,
            max_candle_range_atr=atr_multiple if use_atr else None,
            consolidation_range_pct=consolidation_range / 100.0,
            allowed_patterns=tuple(classifications),
            require_close_above_avwap=require_close_above_avwap,
            require_close_above_vwap=require_close_above_vwap,
        )
    except ValueError as exc:
        return None, str(exc), ""

    summary = (
        f"{max_above:.2f}% above / {max_below:.2f}% below · "
        f"low {max_low_below:.2f}% · body {max_body:.2f} · "
        f"{min_candles}-{max_candles} candles"
    )
    if require_close_above_avwap and require_close_above_vwap:
        summary += " · close > AVWAP & VWAP"
    elif require_close_above_avwap:
        summary += " · close > AVWAP"
    elif require_close_above_vwap:
        summary += " · close > VWAP"
    return config, None, summary


def execute_scan(
    settings: Settings,
    status: AuthStatus,
    instruments: list,
    config: PatternConfig,
    resolution: str,
) -> ScanReport:
    client = status.client
    if client is None:
        token = TokenStore(settings).load_token()
        if not token:
            raise AuthenticationError("No stored FYERS token. Please login.")
        client = FyersClient(settings, token)

    cache = HistoricalCache(
        settings.cache_dir,
        settings.history_cache_ttl_seconds,
        settings.timezone,
    )
    history_service = HistoricalDataService(client, cache, settings)
    engine = ScanEngine(history_service, settings)

    progress = st.progress(0.0, text=f"Preparing {len(instruments)} contracts...")

    def on_progress(position: int, total: int, symbol: str) -> None:
        progress.progress(
            min(position / max(total, 1), 1.0),
            text=f"Scanning {symbol} ({position}/{total})",
        )

    report = engine.scan(
        instruments,
        pattern_config=config,
        resolution=resolution,
        progress_callback=on_progress,
    )
    progress.progress(1.0, text="Scan complete")
    return report


def render_scan_report(settings: Settings, report: ScanReport, resolution: str) -> None:
    generated = pd.Timestamp(report.generated_at)
    if generated.tzinfo is None:
        generated = generated.tz_localize("UTC")
    generated = generated.tz_convert(settings.timezone)
    st.caption(
        f"Scan finished {generated:%d %b %Y %H:%M} IST · "
        f"{report.scanned_count} contracts · {TIMEFRAMES.get(resolution, resolution)}"
    )
    render_summary(report)
    st.subheader("Matching contracts")
    table = render_results_table(report)

    if not table.empty:
        selected = select_match(report)
        if selected is not None:
            render_match_metrics(selected)
            frame = report.histories.get(selected.symbol)
            if frame is not None and not frame.empty:
                figure = plot_pattern_chart(
                    frame,
                    selected,
                    lookback=settings.chart_lookback_candles,
                )
                st.plotly_chart(
                    figure,
                    width="stretch",
                    key=f"chart_{selected.symbol}_{report.resolution}",
                )

        export = table.copy()
        for column in ("Contract expiry", "Pattern timestamp"):
            if column in export.columns:
                export[column] = export[column].astype(str)
        st.download_button(
            "Download results as CSV",
            data=export.to_csv(index=False).encode("utf-8"),
            file_name=f"avwap_scan_{date.today():%Y%m%d}.csv",
            mime="text/csv",
        )

    render_scan_errors(report)


def render_connection_help(settings: Settings) -> None:
    st.info("Connect your FYERS account from the sidebar to run the scanner.")
    st.markdown(
        """
        **Setup**
        1. Copy `.env.example` to `.env` and fill in `FYERS_CLIENT_ID`, `FYERS_SECRET_KEY`
           and a redirect URI registered in the FYERS API dashboard.
        2. Ensure the redirect URI matches the Streamlit URL, e.g. `http://localhost:8501`.
        3. Restart Streamlit, then use **Generate FYERS login URL** in the sidebar.
        4. After login the app stores the access token locally in `access_token.txt`
           (ignored by git) and verifies it with the FYERS profile endpoint.

        The scanner only reads market data. It never places orders.
        """
    )
    missing = settings.missing_credentials()
    if missing:
        st.warning("Missing configuration: " + ", ".join(missing))


def main() -> None:
    settings = Settings.from_env()
    setup_logging(settings)
    settings.ensure_directories()
    init_filter_defaults()

    if st.session_state.get("auth_flash"):
        st.success(st.session_state.pop("auth_flash"))
    if st.session_state.get("auth_flash_error"):
        st.error(st.session_state.pop("auth_flash_error"))
    if st.session_state.get("scan_error"):
        st.error(st.session_state.pop("scan_error"))
    if st.session_state.get("preset_flash"):
        st.success(st.session_state.pop("preset_flash"))
    if st.session_state.get("preset_error"):
        st.error(st.session_state.pop("preset_error"))

    handle_oauth_callback(settings)
    status = resolve_auth_status(settings)
    provider = get_instrument_provider(settings)

    active_frame = pd.DataFrame()
    instrument_error: str | None = None
    config: PatternConfig | None = None
    config_error: str | None = None
    config_summary = ""
    resolution = "60"
    selected_frame = pd.DataFrame()
    selected_instruments: list = []
    universe_label = ""
    scan_clicked = False

    with st.sidebar:
        st.title("AVWAP Scanner")
        render_login_sidebar(settings, status)
        st.divider()

        if status.authenticated:
            st.subheader("Futures universe")
            include_index = st.checkbox(
                "Include index futures",
                value=settings.include_index_futures,
                key="u_index",
            )
            expiry_mode = st.radio(
                "Expiry scope",
                options=["Current active expiry", "All active expiries"],
                index=0,
                key="u_expiry",
            )
            current_only = expiry_mode == "Current active expiry"

            if st.button("Refresh instrument master", width="stretch"):
                try:
                    with st.spinner("Downloading FYERS NSE_FO master..."):
                        provider.load(force=True)
                    st.rerun()
                except InstrumentMasterError as exc:
                    st.error(str(exc))

            try:
                with st.spinner("Loading NSE futures master..."):
                    active_frame = provider.active_futures(
                        current_expiry_only=current_only,
                        include_index=include_index,
                    )
            except InstrumentMasterError as exc:
                instrument_error = str(exc)

            if instrument_error is None:
                st.caption(
                    f"{len(active_frame)} active contracts across "
                    f"{active_frame['underlying'].nunique()} underlyings."
                )
                universe_mode = st.radio(
                    "Scan scope",
                    options=["All active contracts", "Selected contracts"],
                    index=0,
                    key="u_scope",
                )
                if universe_mode == "Selected contracts":
                    label_map = {
                        str(row.symbol): f"{row.symbol}  ·  {row.expiry:%d %b %Y}"
                        for row in active_frame.itertuples(index=False)
                    }
                    choices = active_frame["symbol"].tolist()
                    selected_symbols = st.multiselect(
                        "Select contracts",
                        options=choices,
                        format_func=lambda symbol: label_map.get(symbol, symbol),
                        key="u_symbols",
                    )
                    selected_frame = active_frame.loc[
                        active_frame["symbol"].isin(selected_symbols)
                    ].copy()
                else:
                    selected_frame = active_frame.copy()

                st.divider()
                st.subheader("Pattern filters")
                timeframe_label = st.selectbox(
                    "Timeframe",
                    options=list(TIMEFRAMES.keys()),
                    key="f_timeframe",
                )
                resolution = TIMEFRAMES[timeframe_label]
                config, config_error, config_summary = build_pattern_config()

                if config is not None:
                    selected_instruments = to_instruments(selected_frame)
                    universe_label = (
                        f"{len(selected_instruments)} selected contract(s)"
                        if universe_mode == "Selected contracts"
                        else f"all {len(selected_instruments)} active contract(s)"
                    )

                st.divider()
                render_preset_manager(
                    PresetStore(settings.presets_file),
                    config,
                    config_error,
                    resolution,
                    TIMEFRAMES,
                )

                st.divider()
                if st.button("Clear historical cache", width="stretch"):
                    HistoricalCache(
                        settings.cache_dir,
                        settings.history_cache_ttl_seconds,
                        settings.timezone,
                    ).clear()
                    st.success("Historical candle cache cleared.")
            else:
                st.error(instrument_error)

    st.title("NSE Futures AVWAP Consolidation Scanner")
    st.caption(
        "1-hour contract-start AVWAP support scan. Looks for 1-5 small candles "
        "touching, hugging or consolidating around the red AVWAP line. "
        "Read-only: no orders are placed."
    )

    if not status.authenticated:
        render_connection_help(settings)
        return

    if instrument_error is not None:
        st.error(instrument_error)
        return

    if active_frame.empty:
        st.warning("No active NSE futures contracts matched the current universe filters.")
        return

    if config_error:
        st.error(config_error)

    left, right = st.columns([1.2, 3.8])
    with left:
        scan_disabled = (
            config is None
            or not selected_instruments
            or not status.authenticated
        )
        scan_clicked = st.button(
            "Run AVWAP scan",
            type="primary",
            width="stretch",
            disabled=scan_disabled,
        )
    with right:
        if config_summary:
            st.caption(f"Universe: {universe_label} · {config_summary}")
        else:
            st.caption("Choose at least one contract to scan.")

    signature = None
    if config is not None and selected_instruments:
        signature = (
            resolution,
            tuple(sorted(instrument.symbol for instrument in selected_instruments)),
            config,
        )

    if scan_clicked and signature is not None and config is not None:
        st.session_state.pop("selected_avwap_match", None)
        try:
            with st.spinner("Fetching historical candles and scanning AVWAP..."):
                report = execute_scan(
                    settings,
                    status,
                    selected_instruments,
                    config,
                    resolution,
                )
            st.session_state["scan_report"] = report
            st.session_state["scan_signature"] = signature
            st.session_state["scan_flash"] = (
                f"Scan complete: {len(report.matches)} matching contract(s)."
            )
            st.rerun()
        except AuthenticationError as exc:
            TokenStore(settings).clear()
            st.session_state.pop("auth_status", None)
            st.session_state.pop("auth_token_mtime", None)
            st.session_state["scan_error"] = (
                f"FYERS authentication failed: {exc}. Please login again."
            )
            st.rerun()
        except FyersError as exc:
            st.error(f"FYERS request failed: {exc}")
        except Exception as exc:
            logger.exception("Scan failed")
            st.error(f"Scan failed: {exc}")

    flash = st.session_state.pop("scan_flash", None)
    if flash:
        st.success(flash)

    report = st.session_state.get("scan_report")
    if isinstance(report, ScanReport):
        if signature is not None and st.session_state.get("scan_signature") != signature:
            st.info("Filters or contract selection changed since this scan. Run the scan again to refresh.")
        render_scan_report(settings, report, report.resolution)

    with st.expander("Methodology and data notes", expanded=False):
        st.markdown(
            """
            - The red line is the **contract-start AVWAP**: cumulative typical price
              `(high+low+close)/3` weighted by volume from the contract's first
              available candle. It is **never reset daily**.
            - The blue line is the regular **session VWAP**, reset each trading day.
              It is chart context only; the scanner uses the contract-start AVWAP.
            - Only completed candles are used for final pattern detection. The
              currently forming candle is discarded.
            - A match requires every candle in its window to be close to AVWAP,
              have a low within the configured distance below AVWAP, and have a
              small body. The whole window must also be narrow relative to AVWAP.
            - Patterns with 1, 2, 3, 4 or 5 candles are eligible. No breakout or
              fixed 6-10 candle requirement is applied.
            - The scanner is read-only and never calls any order endpoint.
            """
        )


if __name__ == "__main__":
    main()
