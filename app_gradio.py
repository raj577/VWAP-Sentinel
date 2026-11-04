"""Gradio dashboard for VWAP Sentinel.

This is the Hugging Face Space entry point. It reuses the same configuration,
FYERS client, indicators and detector as the Streamlit app (``app.py``), so both
interfaces can run side by side:

    python app_gradio.py          # http://localhost:7860
    streamlit run app.py          # http://localhost:8501
"""

from __future__ import annotations

import os
import tempfile
from datetime import date
from functools import lru_cache
from typing import Any

import gradio as gr
import pandas as pd

from config import Settings, setup_logging
from dashboard.charts import plot_pattern_chart
from data.cache import HistoricalCache
from data.fyers_client import AuthenticationError, FyersClient, FyersError
from data.historical_data import HistoricalDataService
from data.instrument_master import (
    InstrumentMasterError,
    InstrumentMasterProvider,
    to_instruments,
)
from login import (
    TokenStore,
    check_authentication,
    exchange_auth_code,
    extract_auth_code,
    generate_auth_url,
)
from scanner.models import PATTERN_TYPES, PatternConfig, ScanReport
from scanner.scan_engine import ScanEngine

settings = Settings.from_env()
setup_logging(settings)
settings.ensure_directories()

TIMEFRAMES: dict[str, str] = {
    "1 hour (60 min)": "60",
    "2 hours (120 min)": "120",
    "4 hours (240 min)": "240",
}
EXPIRY_OPTIONS = ["Current active expiry", "All active expiries"]

RESULT_COLUMNS = [
    "Symbol",
    "Underlying",
    "Expiry",
    "Last price",
    "Contract AVWAP",
    "Distance from AVWAP (%)",
    "Candles",
    "Body ratio",
    "Pattern classification",
    "Pattern timestamp",
    "Pattern range (%)",
    "ATR",
]
ERROR_COLUMNS = ["Symbol", "Reason"]

_processed_auth_codes: set[str] = set()


@lru_cache(maxsize=1)
def _provider() -> InstrumentMasterProvider:
    return InstrumentMasterProvider(settings)


def _status_markdown() -> str:
    status = check_authentication(settings, verify=False)
    if status.authenticated:
        age = TokenStore(settings).age_hours()
        suffix = f" Stored {age:.1f} hour(s) ago." if age is not None else ""
        return f"**Connected.** Access token loaded.{suffix}"
    return f"**Not connected.** {status.message}"


def _handle_redirect(request: gr.Request) -> str:
    """Exchange a FYERS ``auth_code`` delivered to this Space URL, once."""
    params = dict(getattr(request, "query_params", {}) or {})
    code = extract_auth_code(params)
    if not code or code in _processed_auth_codes:
        return _status_markdown()

    _processed_auth_codes.add(code)
    try:
        exchange_auth_code(settings, code)
    except AuthenticationError as exc:
        return f"**FYERS login failed:** {exc}"
    return "**Connected.** FYERS login successful; access token stored."


def _login_url() -> str:
    try:
        return generate_auth_url(settings)
    except AuthenticationError as exc:
        return f"Configuration error: {exc}"


def _exchange_manual_code(code: str) -> str:
    if not (code or "").strip():
        return "Paste the `auth_code` value from the FYERS redirect URL."
    try:
        exchange_auth_code(settings, code)
    except AuthenticationError as exc:
        return f"**FYERS login failed:** {exc}"
    return "**Connected.** FYERS login successful; access token stored."


def _verify_connection() -> str:
    status = check_authentication(settings, verify=True)
    if status.authenticated:
        profile = status.profile or {}
        name = profile.get("display_name") or profile.get("name")
        return "**Connected to FYERS.**" + (f" Account: {name}." if name else "")
    return f"**Connection problem.** {status.message}"


def _load_contracts(
    include_index: bool, expiry_label: str
) -> tuple[gr.Dropdown, str]:
    try:
        frame = _provider().active_futures(
            current_expiry_only=expiry_label == EXPIRY_OPTIONS[0],
            include_index=bool(include_index),
        )
    except InstrumentMasterError as exc:
        return gr.Dropdown(choices=[], value=[]), f"**Instrument master error:** {exc}"

    choices = sorted(frame["symbol"].astype(str).tolist())
    underlying_count = int(frame["underlying"].nunique()) if not frame.empty else 0
    info = (
        f"{len(frame)} active contract(s) across {underlying_count} underlying(s). "
        "Leave the selection empty to scan all of them."
    )
    return gr.Dropdown(choices=choices, value=[]), info


def _refresh_and_load(
    include_index: bool, expiry_label: str
) -> tuple[gr.Dropdown, str]:
    try:
        _provider().load(force=True)
    except InstrumentMasterError as exc:
        return gr.Dropdown(choices=[], value=[]), f"**Instrument master error:** {exc}"
    return _load_contracts(include_index, expiry_label)


def _build_config(
    min_candles: float,
    max_candles: float,
    max_above: float,
    max_below: float,
    max_low_below: float,
    max_body: float,
    max_range: float,
    use_atr: bool,
    atr_multiple: float,
    consolidation_range: float,
    classifications: list[str],
    close_above_avwap: bool,
    close_above_vwap: bool,
) -> PatternConfig:
    minimum = int(min_candles)
    maximum = int(max_candles)
    if minimum > maximum:
        raise ValueError("Minimum candles cannot exceed maximum candles.")
    if not classifications:
        raise ValueError("Select at least one pattern classification.")
    return PatternConfig(
        max_close_above_pct=float(max_above) / 100.0,
        max_close_below_pct=float(max_below) / 100.0,
        max_low_below_pct=float(max_low_below) / 100.0,
        max_body_ratio=float(max_body),
        min_candles=minimum,
        max_candles=maximum,
        max_window_range_pct=float(max_range) / 100.0,
        max_candle_range_atr=float(atr_multiple) if use_atr else None,
        consolidation_range_pct=float(consolidation_range) / 100.0,
        allowed_patterns=tuple(classifications),
        require_close_above_avwap=bool(close_above_avwap),
        require_close_above_vwap=bool(close_above_vwap),
    )


def _results_frame(report: ScanReport) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for match in report.sorted_matches():
        pattern = match.pattern
        rows.append(
            {
                "Symbol": match.symbol,
                "Underlying": match.instrument.underlying,
                "Expiry": f"{match.expiry:%d %b %Y}",
                "Last price": pattern.last_price,
                "Contract AVWAP": pattern.avwap,
                "Distance from AVWAP (%)": pattern.distance_pct,
                "Candles": pattern.candle_count,
                "Body ratio": pattern.avg_body_ratio,
                "Pattern classification": pattern.pattern_type,
                "Pattern timestamp": (
                    pattern.pattern_end.strftime("%d %b %Y %H:%M")
                    if pattern.pattern_end is not None
                    else ""
                ),
                "Pattern range (%)": pattern.window_range_pct * 100.0,
                "ATR": pattern.latest_atr,
            }
        )
    return pd.DataFrame(rows, columns=RESULT_COLUMNS)


def _errors_frame(report: ScanReport) -> pd.DataFrame:
    return pd.DataFrame(
        [{"Symbol": error.symbol, "Reason": error.message} for error in report.errors],
        columns=ERROR_COLUMNS,
    )


def _summary_markdown(report: ScanReport) -> str:
    summary = report.summary()
    return (
        f"**{summary['matches']} match(es)** from **{summary['scanned']}** contract(s) "
        f"scanned. Touches: {summary['touches']} · Hugging: {summary['hugging']} · "
        f"Consolidations: {summary['consolidations']} · Reclaims: {summary['reclaims']} · "
        f"Skipped: {summary['errors']}."
    )


def _empty_results(message: str):
    return (
        message,
        pd.DataFrame(columns=RESULT_COLUMNS),
        None,
        pd.DataFrame(columns=ERROR_COLUMNS),
        gr.Dropdown(choices=[], value=None),
        None,
        None,
    )


def _run_scan(
    include_index: bool,
    expiry_label: str,
    selected_symbols: list[str] | None,
    timeframe_label: str,
    min_candles: float,
    max_candles: float,
    max_above: float,
    max_below: float,
    max_low_below: float,
    max_body: float,
    max_range: float,
    use_atr: bool,
    atr_multiple: float,
    consolidation_range: float,
    classifications: list[str] | None,
    close_above_avwap: bool,
    close_above_vwap: bool,
    progress=gr.Progress(),
):
    try:
        config = _build_config(
            min_candles,
            max_candles,
            max_above,
            max_below,
            max_low_below,
            max_body,
            max_range,
            use_atr,
            atr_multiple,
            consolidation_range,
            list(classifications or []),
            close_above_avwap,
            close_above_vwap,
        )
    except ValueError as exc:
        return _empty_results(f"**Filter error:** {exc}")

    resolution = TIMEFRAMES.get(timeframe_label, "60")

    try:
        universe = _provider().active_futures(
            current_expiry_only=expiry_label == EXPIRY_OPTIONS[0],
            include_index=bool(include_index),
        )
    except InstrumentMasterError as exc:
        return _empty_results(f"**Instrument master error:** {exc}")

    if selected_symbols:
        universe = universe.loc[universe["symbol"].isin(selected_symbols)]
    instruments = to_instruments(universe)
    if not instruments:
        return _empty_results("Select at least one contract, or leave the selection empty.")

    token = TokenStore(settings).load_token()
    if not token:
        return _empty_results(
            "**Not connected to FYERS.** Generate a login URL and exchange the auth code."
        )

    client = FyersClient(settings, token)
    cache = HistoricalCache(
        settings.cache_dir,
        settings.history_cache_ttl_seconds,
        settings.timezone,
    )
    history_service = HistoricalDataService(client, cache, settings)
    engine = ScanEngine(history_service, settings)

    def on_progress(position: int, total: int, symbol: str) -> None:
        progress(
            position / max(total, 1),
            desc=f"Scanning {symbol} ({position}/{total})",
        )

    try:
        report = engine.scan(
            instruments,
            pattern_config=config,
            resolution=resolution,
            progress_callback=on_progress,
        )
    except AuthenticationError as exc:
        return _empty_results(
            f"**FYERS authentication failed:** {exc}. Please login again."
        )
    except FyersError as exc:
        return _empty_results(f"**FYERS request failed:** {exc}")

    results = _results_frame(report)
    errors = _errors_frame(report)

    csv_path = None
    if not results.empty:
        handle, csv_path = tempfile.mkstemp(
            prefix=f"avwap_scan_{date.today():%Y%m%d}_", suffix=".csv"
        )
        os.close(handle)
        results.to_csv(csv_path, index=False)

    labels = [
        f"{index}: {match.symbol} · {match.pattern.pattern_type} · "
        f"{match.pattern.distance_pct:+.2f}%"
        for index, match in enumerate(report.sorted_matches())
    ]
    figure = None
    if labels:
        figure = _chart_for(report, labels[0])

    return (
        _summary_markdown(report),
        results,
        csv_path,
        errors,
        gr.Dropdown(choices=labels, value=labels[0] if labels else None),
        figure,
        report,
    )


def _chart_for(report: ScanReport, label: str | None):
    if not label:
        return None
    try:
        index = int(str(label).split(":", 1)[0])
    except ValueError:
        return None
    matches = report.sorted_matches()
    if not 0 <= index < len(matches):
        return None
    match = matches[index]
    frame = report.histories.get(match.symbol)
    if frame is None or frame.empty:
        return None
    return plot_pattern_chart(
        frame,
        match,
        lookback=settings.chart_lookback_candles,
    )


def _update_chart(label: str | None, report: ScanReport | None):
    if not isinstance(report, ScanReport):
        return None
    return _chart_for(report, label)


def build_demo() -> gr.Blocks:
    with gr.Blocks(title="VWAP Sentinel") as demo:
        gr.Markdown(
            "# VWAP Sentinel\n"
            "Contract-start Anchored VWAP consolidation scanner for NSE futures. "
            "Read-only: no orders are placed."
        )

        report_state = gr.State(None)

        with gr.Accordion("FYERS connection", open=True):
            connection_md = gr.Markdown(_status_markdown())
            with gr.Row():
                login_button = gr.Button("Generate FYERS login URL")
                verify_button = gr.Button("Check connection")
            login_url_box = gr.Textbox(
                label="Authorization URL",
                interactive=False,
            )
            with gr.Row():
                auth_code_box = gr.Textbox(
                    label="Authorization code",
                    type="password",
                    placeholder="Paste auth_code from the FYERS redirect URL",
                )
                exchange_button = gr.Button("Exchange code")
            auth_message_md = gr.Markdown()

        with gr.Tabs():
            with gr.Tab("Scanner"):
                with gr.Row():
                    include_index = gr.Checkbox(
                        label="Include index futures",
                        value=settings.include_index_futures,
                    )
                    expiry_scope = gr.Radio(
                        choices=EXPIRY_OPTIONS,
                        value=EXPIRY_OPTIONS[0],
                        label="Expiry scope",
                    )
                    refresh_button = gr.Button("Refresh instrument master")
                contracts = gr.Dropdown(
                    label="Contracts (empty = all active)",
                    choices=[],
                    multiselect=True,
                    value=[],
                )
                universe_md = gr.Markdown()

                with gr.Accordion("Pattern filters", open=True):
                    timeframe = gr.Dropdown(
                        label="Timeframe",
                        choices=list(TIMEFRAMES.keys()),
                        value="1 hour (60 min)",
                    )
                    with gr.Row():
                        min_candles = gr.Slider(
                            label="Minimum candles",
                            minimum=1,
                            maximum=5,
                            step=1,
                            value=1,
                        )
                        max_candles = gr.Slider(
                            label="Maximum candles",
                            minimum=1,
                            maximum=5,
                            step=1,
                            value=5,
                        )
                    with gr.Row():
                        max_above = gr.Number(
                            label="Max close above AVWAP (%)", value=0.50
                        )
                        max_below = gr.Number(
                            label="Max close below AVWAP (%)", value=0.20
                        )
                    with gr.Row():
                        max_low_below = gr.Number(
                            label="Max candle low below AVWAP (%)", value=0.30
                        )
                        max_body = gr.Number(
                            label="Maximum candle body ratio", value=0.35
                        )
                    with gr.Accordion("Advanced pattern constraints", open=False):
                        with gr.Row():
                            max_range = gr.Number(
                                label="Maximum pattern range (% of AVWAP)",
                                value=2.0,
                            )
                            consolidation_range = gr.Number(
                                label="Consolidation classification range (%)",
                                value=1.0,
                            )
                        with gr.Row():
                            use_atr = gr.Checkbox(
                                label="Cap each candle range at an ATR multiple",
                                value=True,
                            )
                            atr_multiple = gr.Number(
                                label="ATR range multiple", value=2.0
                            )
                    classifications = gr.CheckboxGroup(
                        label="Pattern classification filter",
                        choices=list(PATTERN_TYPES),
                        value=list(PATTERN_TYPES),
                    )
                    gr.Markdown("**Last candle confirmation**")
                    with gr.Row():
                        close_above_avwap = gr.Checkbox(
                            label="Close above AVWAP", value=False
                        )
                        close_above_vwap = gr.Checkbox(
                            label="Close above session VWAP", value=False
                        )

                run_button = gr.Button("Run AVWAP scan", variant="primary")
                summary_md = gr.Markdown()
                results_table = gr.Dataframe(
                    label="Matching contracts",
                    wrap=True,
                    interactive=False,
                )
                csv_file = gr.File(label="Download results CSV")
                match_dropdown = gr.Dropdown(
                    label="Open a matching contract chart",
                    choices=[],
                    value=None,
                )
                chart = gr.Plot(label="Pattern chart")
                errors_table = gr.Dataframe(
                    label="Scan log / skipped contracts",
                    wrap=True,
                    interactive=False,
                )

            with gr.Tab("Methodology"):
                gr.Markdown(
                    """
                    - The red line is the **contract-start AVWAP**: cumulative
                      typical price `(high+low+close)/3` weighted by volume from
                      the contract's first available candle. It is **never reset
                      daily**.
                    - The blue line is the regular **session VWAP**, reset each
                      trading day. It is chart context and an optional filter.
                    - Only completed candles are used. The currently forming
                      candle is discarded.
                    - Optional last-candle confirmation requires a strict close
                      above AVWAP and/or session VWAP.
                    - The scanner is read-only and never calls any order endpoint.
                    """
                )

        login_button.click(_login_url, outputs=login_url_box)
        exchange_button.click(
            _exchange_manual_code,
            inputs=auth_code_box,
            outputs=auth_message_md,
        )
        verify_button.click(_verify_connection, outputs=connection_md)
        demo.load(_handle_redirect, outputs=connection_md)

        include_index.change(
            _load_contracts,
            inputs=[include_index, expiry_scope],
            outputs=[contracts, universe_md],
        )
        expiry_scope.change(
            _load_contracts,
            inputs=[include_index, expiry_scope],
            outputs=[contracts, universe_md],
        )
        refresh_button.click(
            _refresh_and_load,
            inputs=[include_index, expiry_scope],
            outputs=[contracts, universe_md],
        )

        run_button.click(
            _run_scan,
            inputs=[
                include_index,
                expiry_scope,
                contracts,
                timeframe,
                min_candles,
                max_candles,
                max_above,
                max_below,
                max_low_below,
                max_body,
                max_range,
                use_atr,
                atr_multiple,
                consolidation_range,
                classifications,
                close_above_avwap,
                close_above_vwap,
            ],
            outputs=[
                summary_md,
                results_table,
                csv_file,
                errors_table,
                match_dropdown,
                chart,
                report_state,
            ],
        )
        match_dropdown.change(
            _update_chart,
            inputs=[match_dropdown, report_state],
            outputs=chart,
        )

        demo.load(
            _load_contracts,
            inputs=[include_index, expiry_scope],
            outputs=[contracts, universe_md],
        )

    return demo


demo = build_demo()

if __name__ == "__main__":
    demo.launch(
        server_name=os.getenv("GRADIO_SERVER_NAME", "0.0.0.0"),
        server_port=int(
            os.getenv("GRADIO_SERVER_PORT") or os.getenv("PORT") or "7860"
        ),
    )
