"""Interactive Plotly charts - one shared design system."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

INK = "#1A2332"
MUTED = "#5B6871"
TEAL = "#0E7C6B"
GREEN = "#2E9E5B"
GREEN_DARK = "#1E7A44"
NAVY = "#2B4A6F"
SAGE = "#7FA89B"
CASH = "#B9C4BC"
CONTRIB_FILL = "#DCE5E1"
ROSE = "#C4745A"
GRID = "#E7EAE6"
BAND = "rgba(14,124,107,0.14)"

FONT = "Inter, -apple-system, 'Segoe UI', sans-serif"

WRAPPER_COLORS = {
    "Brokerage": INK,
    "Pillar 3a": TEAL,
    "Pillar 2": NAVY,
    "Cash buffer": CASH,
}


def _chf_tip(label: str) -> str:
    """One shared-hover row: 'Label: <b>1,234 CHF</b>' with no extra box."""
    return f"{label}: <b>%{{y:,.0f}} CHF</b><extra></extra>"


HOVER_LABEL = {
    "bgcolor": "#FFFFFF",
    "bordercolor": SAGE,
    "font": {"family": FONT, "color": INK, "size": 13},
}

COMMON_LAYOUT = {
    "font": {"family": FONT, "color": INK, "size": 13},
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "hovermode": "x unified",
    "hoverlabel": HOVER_LABEL,
}

# Shared hover box header already reads "Year N" (x values are "Year N"
# strings), so each trace template carries ONLY its own "Name: value" line.
# <extra></extra> hides Plotly's default second box (which would repeat it).

_MAX_TICKS = 9


def _sparse_markers(fig: go.Figure, n: int) -> go.Figure:
    """With 1-2 points, line/area segments collapse to nothing, leaving the
    chart looking empty. Show dots instead - skipped for invisible helpers
    (zero-width lines) and traces that opted out of hover."""
    if n > 2:
        return fig
    for trace in fig.data:
        if getattr(trace, "hoverinfo", None) == "skip" or trace.type != "scatter":
            continue
        width = trace.line.width if trace.line else None
        if width == 0:
            continue
        mode = trace.mode or "lines"
        if "lines" in mode and "markers" not in mode:
            line_color = trace.line.color if trace.line and trace.line.color else INK
            trace.mode = mode + "+markers"
            trace.marker = {"size": 7, "color": line_color}
    return fig


def _year_labels(years) -> list[str]:
    return [f"Year {int(y)}" for y in years]


def _thin_ticks(fig: go.Figure, labels: list[str]) -> go.Figure:
    step = max(1, -(-len(labels) // _MAX_TICKS))  # ceil division
    fig.update_xaxes(tickmode="array", tickvals=labels[::step])
    return fig


def _base(fig: go.Figure, title: str, subtitle: str, ytitle: str = "CHF", **extra) -> go.Figure:
    fig.update_layout(
        title={
            "text": (
                f"<b>{title}</b><br><span style='color:{MUTED};font-size:12px'>{subtitle}</span>"
            )
        },
        **COMMON_LAYOUT,
        **extra,
    )
    return fig


def fig_stacked_contrib_growth(df: pd.DataFrame) -> go.Figure:
    """Stacked area: cumulative contributions vs compounding growth."""
    xl = _year_labels(df["year"])
    fig = go.Figure()
    fig.add_trace(
        # Invisible total line: contributes only the "Total" row to the shared
        # hover box. Added FIRST because unified hover renders traces in
        # reverse order - first trace lands at the bottom, below the parts.
        go.Scatter(
            x=xl,
            y=df["total_nominal"],
            mode="lines",
            name="Total",
            line={"width": 0, "color": "rgba(0,0,0,0)"},
            showlegend=False,
            hovertemplate=_chf_tip("Total"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=xl,
            y=df["contributions_cum"],
            stackgroup="one",
            groupnorm="",
            name="You paid in",
            fillcolor=CONTRIB_FILL,
            line={"width": 0.5, "color": SAGE},
            hovertemplate=_chf_tip("You paid in"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=xl,
            y=df["growth_cum"].clip(lower=0),
            stackgroup="one",
            name="Markets added",
            fillcolor=GREEN,
            line={"width": 0.5, "color": GREEN_DARK},
            hovertemplate=_chf_tip("Markets added"),
        )
    )
    fig = _base(
        fig,
        "Who did the work - you or compounding?",
        "Lower band: everything you paid in. Upper band: growth on top.",
    )
    fig = _thin_ticks(fig, xl)
    return _sparse_markers(fig, len(xl))


def fig_allocation_growth(df: pd.DataFrame) -> go.Figure:
    """Stacked brokerage / 3a / pillar 2 / cash over time."""
    xl = _year_labels(df["year"])
    fig = go.Figure()
    fig.add_trace(
        # Invisible total line: contributes only the "Total" row to the shared
        # hover box. Added FIRST because unified hover renders traces in
        # reverse order - first trace lands at the bottom, below the parts.
        go.Scatter(
            x=xl,
            y=df["total_nominal"],
            mode="lines",
            name="Total",
            line={"width": 0, "color": "rgba(0,0,0,0)"},
            showlegend=False,
            hovertemplate=_chf_tip("Total"),
        )
    )
    for col, name in [
        ("brokerage", "Brokerage"),
        ("pillar3a", "Pillar 3a"),
        ("pillar2", "Pillar 2"),
        ("cash", "Cash buffer"),
    ]:
        fig.add_trace(
            go.Scatter(
                x=xl,
                y=df[col],
                stackgroup="one",
                name=name,
                fillcolor=WRAPPER_COLORS[name],
                line={"width": 0.5, "color": WRAPPER_COLORS[name]},
                hovertemplate=_chf_tip(name),
            )
        )
    fig = _base(
        fig,
        "Where the money lives over time",
        "Brokerage, pillar 3a, pillar 2 and cash, stacked per year.",
    )
    fig = _thin_ticks(fig, xl)
    return _sparse_markers(fig, len(xl))


def fig_final_mix(last_row) -> go.Figure:
    """Horizontal bar: final split across wrappers. Takes df.iloc[-1]."""
    items = [
        ("Brokerage", float(last_row["brokerage"]), WRAPPER_COLORS["Brokerage"]),
        ("Pillar 3a", float(last_row["pillar3a"]), WRAPPER_COLORS["Pillar 3a"]),
        ("Pillar 2", float(last_row["pillar2"]), WRAPPER_COLORS["Pillar 2"]),
        ("Cash buffer", float(last_row["cash"]), WRAPPER_COLORS["Cash buffer"]),
    ]
    fig = go.Figure(
        go.Bar(
            x=[v for _, v, _ in items],
            y=[n for n, _, _ in items],
            orientation="h",
            marker_color=[c for _, _, c in items],
            text=[f"{v:,.0f}" for _, v, _ in items],
            textposition="auto",
            insidetextanchor="middle",
            hovertemplate="%{y}: <b>%{x:,.0f} CHF</b><extra></extra>",
        )
    )
    fig = _base(
        fig,
        f"Final mix at year {int(last_row['year'])}",
        f"Total {float(last_row['total_nominal']):,.0f} CHF, split by account.",
        margin={"l": 8, "r": 16, "t": 70, "b": 8},
        height=280,
        xaxis={"tickformat": ",.0f", "gridcolor": GRID, "tickfont": {"color": MUTED}},
        yaxis={"tickfont": {"color": INK}},
        showlegend=False,
    )
    return fig


def fig_scenarios(scen: dict[str, pd.DataFrame]) -> go.Figure:
    styles = {
        "bear": {"color": ROSE, "dash": "dot"},
        "base": {"color": INK, "dash": "solid"},
        "bull": {"color": TEAL, "dash": "dash"},
    }
    fig = go.Figure()
    labels: list[str] = []
    for name, df in scen.items():
        labels = _year_labels(df["year"])
        s = styles.get(name, {"color": NAVY, "dash": "solid"})
        width = 3 if name == "base" else 2
        fig.add_trace(
            go.Scatter(
                x=labels,
                y=df["total_nominal"],
                mode="lines+markers",
                name=name.capitalize(),
                line={"color": s["color"], "dash": s["dash"], "width": width},
                marker={"size": 5 if name == "base" else 4},
                hovertemplate=_chf_tip(name.capitalize()),
            )
        )
    fig = _base(
        fig,
        "What if returns disappoint - or surprise?",
        "Same savings, three return worlds. Drag the slider below to zoom into any period.",
    )
    fig.update_xaxes(rangeslider_visible=True, rangeslider_thickness=0.06)
    # Range slider occupies the bottom slot, so push the legend further down.
    # NOTE: pass the full dict - a partial dict would reset orientation/anchors.
    fig.update_layout(
        margin={"l": 8, "r": 8, "t": 88, "b": 118},
        legend={
            "orientation": "h",
            "yanchor": "top",
            "y": -0.32,
            "xanchor": "left",
            "x": 0,
        },
    )
    fig = _thin_ticks(fig, labels)
    return _sparse_markers(fig, len(labels))


def fig_fan(pct: pd.DataFrame) -> go.Figure:
    xl = _year_labels(pct["year"])
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=xl,
            y=pct["p90"],
            mode="lines",
            line={"width": 0},
            showlegend=False,
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=xl,
            y=pct["p10"],
            mode="lines",
            line={"width": 0},
            fill="tonexty",
            fillcolor=BAND,
            name="8 in 10 paths land here",
            hovertemplate=_chf_tip("Lower bound (P10)"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=xl,
            y=pct["p50"],
            mode="lines+markers",
            name="Median path",
            line={"color": INK, "width": 2.5},
            marker={"size": 5, "color": INK},
            hovertemplate=_chf_tip("Median"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=xl,
            y=pct["p90"],
            mode="lines",
            name="Top 10%",
            line={"color": TEAL, "dash": "dash", "width": 2},
            hovertemplate=_chf_tip("Upper bound (P90)"),
        )
    )
    fig = _base(
        fig,
        "The honest version: a range, not a line",
        "Band: 10th–90th percentile of simulated futures. Line: median.",
    )
    fig = _thin_ticks(fig, xl)
    return _sparse_markers(fig, len(xl))


def fig_histogram(finals) -> go.Figure:
    p50 = float(np.median(finals))
    fig = px.histogram(
        pd.DataFrame({"Final total": finals}),
        x="Final total",
        nbins=50,
        labels={"Final total": "Final total (CHF)"},
        color_discrete_sequence=[TEAL],
    )
    fig.update_traces(hovertemplate="Around <b>%{x:,.0f} CHF</b><br>%{y} futures<extra></extra>")
    fig.add_vline(
        x=p50,
        line_dash="dash",
        line_color=INK,
        annotation_text=f"Median {p50:,.0f} CHF",
        annotation_position="top right",
    )
    fig = _base(
        fig,
        "How wide is the future?",
        "Each bar counts futures ending in that range. Dashed line: median.",
        margin={"l": 8, "r": 8, "t": 84, "b": 8},
        height=360,
        xaxis={"tickformat": ",.0f", "gridcolor": GRID, "tickfont": {"color": MUTED}},
        yaxis={"title": "Futures", "gridcolor": GRID, "tickfont": {"color": MUTED}},
        showlegend=False,
    )
    return fig


def save_html(fig: go.Figure, path: str) -> str:
    fig.write_html(path, include_plotlyjs="cdn", full_html=True, config={"displayModeBar": False})
    return path
