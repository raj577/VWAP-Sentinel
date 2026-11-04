"""Interactive Plotly candlestick chart for a matched AVWAP setup."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from scanner.models import ScanMatch

RED = "#ff3b30"
BLUE = "#2f80ed"
GREEN = "#26a69a"
CANDLE_RED = "#ef5350"


def _pattern_window(
    frame: pd.DataFrame, match: ScanMatch, offset: int
) -> tuple[int, int]:
    start = max(match.pattern.start_idx - offset, 0)
    end = min(match.pattern.end_idx - offset, len(frame) - 1)
    if end < start:
        start, end = 0, len(frame) - 1
    return start, end


def plot_pattern_chart(
    candles: pd.DataFrame,
    match: ScanMatch,
    lookback: int = 120,
) -> go.Figure:
    """Candles + contract AVWAP (red) + session VWAP (blue) + pattern highlight."""

    if candles is None or candles.empty:
        raise ValueError("No candles available for chart.")

    required = {"timestamp", "open", "high", "low", "close", "avwap"}
    missing = required - set(candles.columns)
    if missing:
        raise ValueError(f"Chart data missing columns: {sorted(missing)}")

    lookback = max(int(lookback), 20)
    offset = max(len(candles) - lookback, 0)
    view = candles.iloc[offset:].reset_index(drop=True).copy()
    pattern_start, pattern_end = _pattern_window(view, match, offset)

    figure = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.035,
        row_heights=[0.78, 0.22],
    )

    candle_label = (
        f"{match.resolution} min candles"
        if str(match.resolution).isdigit()
        else f"{match.resolution} candles"
    )
    figure.add_trace(
        go.Candlestick(
            x=view["timestamp"],
            open=view["open"],
            high=view["high"],
            low=view["low"],
            close=view["close"],
            name=candle_label,
            increasing_line_color=GREEN,
            increasing_fillcolor=GREEN,
            decreasing_line_color=CANDLE_RED,
            decreasing_fillcolor=CANDLE_RED,
            whiskerwidth=0.35,
        ),
        row=1,
        col=1,
    )

    figure.add_trace(
        go.Scatter(
            x=view["timestamp"],
            y=view["avwap"],
            mode="lines",
            name="Contract-start AVWAP",
            line={"color": RED, "width": 2.4},
            hovertemplate="AVWAP %{y:.2f}<extra></extra>",
        ),
        row=1,
        col=1,
    )

    if "session_vwap" in view.columns:
        figure.add_trace(
            go.Scatter(
                x=view["timestamp"],
                y=view["session_vwap"],
                mode="lines",
                name="Session VWAP",
                line={"color": BLUE, "width": 1.7},
                hovertemplate="Session VWAP %{y:.2f}<extra></extra>",
            ),
            row=1,
            col=1,
        )

    spacing = view["timestamp"].diff().median()
    if pd.isna(spacing) or spacing <= pd.Timedelta(0):
        spacing = pd.Timedelta(minutes=60)
    highlight_start = view["timestamp"].iloc[pattern_start] - spacing / 2
    highlight_end = view["timestamp"].iloc[pattern_end] + spacing / 2
    figure.add_vrect(
        x0=highlight_start,
        x1=highlight_end,
        fillcolor="rgba(255, 193, 7, 0.14)",
        line_width=1,
        line_color="rgba(255, 193, 7, 0.55)",
        layer="below",
        row=1,
        col=1,
    )
    figure.add_trace(
        go.Scatter(
            x=view["timestamp"].iloc[pattern_start : pattern_end + 1],
            y=view["low"].iloc[pattern_start : pattern_end + 1],
            mode="markers",
            name="Pattern candles",
            marker={
                "symbol": "diamond-open",
                "size": 9,
                "color": "#ffc107",
                "line": {"width": 2, "color": "#ffc107"},
            },
            hovertemplate="Pattern low %{y:.2f}<extra></extra>",
        ),
        row=1,
        col=1,
    )
    figure.add_annotation(
        x=view["timestamp"].iloc[pattern_start],
        y=view["high"].iloc[pattern_start: pattern_end + 1].max(),
        text=f"{match.pattern.pattern_type} · {match.pattern.candle_count} candle(s)",
        showarrow=True,
        arrowhead=2,
        arrowcolor="#ffc107",
        font={"color": "#ffc107", "size": 11},
        bgcolor="rgba(17,24,39,0.75)",
        bordercolor="rgba(255,193,7,0.5)",
        ax=0,
        ay=-28,
        row=1,
        col=1,
    )

    colors = np.where(view["close"] >= view["open"], GREEN, CANDLE_RED)
    figure.add_trace(
        go.Bar(
            x=view["timestamp"],
            y=view["volume"],
            name="Volume",
            marker_color=colors,
            opacity=0.55,
        ),
        row=2,
        col=1,
    )

    last = view.iloc[-1]
    avwap_value = float(last["avwap"])
    last_price = float(last["close"])
    distance = (last_price / avwap_value - 1.0) * 100.0 if avwap_value else float("nan")
    figure.add_annotation(
        x=last["timestamp"],
        y=last_price,
        text=f"LTP {last_price:,.2f}",
        showarrow=True,
        arrowhead=2,
        arrowcolor="#e5e7eb",
        font={"color": "#f9fafb", "size": 11},
        bgcolor="rgba(31,41,55,0.9)",
        borderpad=4,
        ay=-32,
        row=1,
        col=1,
    )
    figure.add_annotation(
        xref="paper",
        yref="paper",
        x=0.01,
        y=1.055,
        text=(
            f"<b>{match.symbol}</b>  ·  expiry {match.expiry:%d %b %Y}  ·  "
            f"AVWAP {avwap_value:,.2f}  ·  distance {distance:+.2f}%"
        ),
        showarrow=False,
        font={"color": "#d1d5db", "size": 12},
        align="left",
    )

    figure.update_layout(
        template="plotly_dark",
        height=650,
        margin={"l": 10, "r": 24, "t": 52, "b": 16},
        hovermode="x unified",
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.01,
            "xanchor": "right",
            "x": 1,
            "font": {"size": 11},
        },
        bargap=0.15,
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
    )
    figure.update_xaxes(
        rangeslider_visible=False,
        showgrid=True,
        gridcolor="rgba(148,163,184,0.10)",
        zeroline=False,
        row=1,
        col=1,
    )
    figure.update_xaxes(
        showgrid=True,
        gridcolor="rgba(148,163,184,0.10)",
        zeroline=False,
        row=2,
        col=1,
    )
    figure.update_yaxes(
        title_text="Price",
        showgrid=True,
        gridcolor="rgba(148,163,184,0.10)",
        zeroline=False,
        row=1,
        col=1,
    )
    figure.update_yaxes(
        title_text="Vol",
        showgrid=False,
        zeroline=False,
        row=2,
        col=1,
    )
    return figure
