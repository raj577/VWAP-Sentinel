"""Reusable Streamlit UI components for the AVWAP scanner."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from scanner.models import ScanMatch, ScanReport


def render_summary(report: ScanReport) -> None:
    summary = report.summary()
    columns = st.columns(5)
    columns[0].metric("Contracts scanned", summary["scanned"])
    columns[1].metric("Matching patterns", summary["matches"])
    columns[2].metric("AVWAP touches", summary["touches"])
    columns[3].metric("AVWAP consolidations", summary["consolidations"])
    columns[4].metric("AVWAP reclaims", summary["reclaims"])
    if summary["errors"]:
        st.caption(f"{summary['errors']} contract(s) skipped — see the scan log below.")


def results_dataframe(report: ScanReport) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for match in report.sorted_matches():
        pattern = match.pattern
        rows.append(
            {
                "Symbol": match.symbol,
                "AVWAP": pattern.avwap,
                "Underlying": match.instrument.underlying,
                "Contract expiry": match.expiry,
                "Last price": pattern.last_price,
                "Distance from AVWAP (%)": pattern.distance_pct,
                "Number of candles": pattern.candle_count,
                "Candle body ratio": pattern.avg_body_ratio,
                "Pattern classification": pattern.pattern_type,
                "Pattern timestamp": pattern.pattern_end,
                "Pattern range (%)": pattern.window_range_pct * 100.0,
                "ATR": pattern.latest_atr,
            }
        )
    return pd.DataFrame(rows)


def render_results_table(report: ScanReport) -> pd.DataFrame:
    table = results_dataframe(report)
    if table.empty:
        st.info("No contracts currently match the configured AVWAP pattern.")
        return table

    st.dataframe(
        table,
        width="stretch",
        hide_index=True,
        height=min(620, 38 * len(table) + 42),
        column_config={
            "Symbol": st.column_config.TextColumn(width="medium"),
            "AVWAP": st.column_config.NumberColumn(
                format="%.2f",
                help="Contract-start AVWAP from the first available contract candle.",
            ),
            "Contract expiry": st.column_config.DateColumn(format="DD MMM YYYY"),
            "Last price": st.column_config.NumberColumn(format="%.2f"),
            "Distance from AVWAP (%)": st.column_config.NumberColumn(
                format="%.2f%%",
                help="Signed percentage distance from the contract-start AVWAP.",
            ),
            "Number of candles": st.column_config.NumberColumn(format="%d"),
            "Candle body ratio": st.column_config.NumberColumn(
                format="%.3f",
                help="Average |close-open| / (high-low). Lower is more doji-like.",
            ),
            "Pattern classification": st.column_config.TextColumn(width="medium"),
            "Pattern timestamp": st.column_config.DatetimeColumn(
                format="DD MMM YYYY HH:mm"
            ),
            "Pattern range (%)": st.column_config.NumberColumn(format="%.2f%%"),
            "ATR": st.column_config.NumberColumn(format="%.2f"),
        },
    )
    st.caption("Sorted by absolute distance from the contract-start AVWAP (closest first).")
    return table


def render_scan_errors(report: ScanReport) -> None:
    if not report.errors:
        return
    with st.expander(f"Scan log / skipped contracts ({len(report.errors)})", expanded=False):
        errors = pd.DataFrame(
            [{"Symbol": error.symbol, "Reason": error.message} for error in report.errors]
        )
        st.dataframe(errors, width="stretch", hide_index=True, height=220)


def select_match(report: ScanReport) -> ScanMatch | None:
    matches = report.sorted_matches()
    if not matches:
        return None

    labels = [
        (
            f"{match.symbol}  ·  {match.pattern.pattern_type}  ·  "
            f"{match.pattern.distance_pct:+.2f}%  ·  "
            f"{match.pattern.candle_count} candle(s)"
        )
        for match in matches
    ]
    choice = st.selectbox(
        "Open a matching contract chart",
        options=range(len(matches)),
        format_func=lambda index: labels[index],
        key="selected_avwap_match",
    )
    return matches[int(choice)]


def render_match_metrics(match: ScanMatch) -> None:
    pattern = match.pattern
    columns = st.columns(6)
    columns[0].metric("Last price", f"{pattern.last_price:,.2f}")
    columns[1].metric("Contract AVWAP", f"{pattern.avwap:,.2f}")
    columns[2].metric("Distance", f"{pattern.distance_pct:+.2f}%")
    columns[3].metric("Candles", pattern.candle_count)
    columns[4].metric("Avg body ratio", f"{pattern.avg_body_ratio:.3f}")
    columns[5].metric("Classification", pattern.pattern_type)
