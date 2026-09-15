"""Streamlit building blocks: theme CSS plus slider, card and chart helpers."""

import streamlit as st

CSS = """
<style>
  /* Streamlit chrome: keep the header (it holds the sidebar toggle) but make it
     invisible; hide everything else. */
  header[data-testid="stHeader"] { background: rgba(0, 0, 0, 0); }
  [data-testid="stToolbar"] { visibility: hidden; }
  [data-testid="stAppDeployButton"] { display: none; }
  #MainMenu { visibility: hidden; }
  footer { visibility: hidden; }
  /* The collapse/expand chevron is hover-only by default - keep the *relevant*
     one rendered so the sidebar can always be recovered. Visibility is scoped
     to the sidebar's live aria-expanded state, so mid-collapse (when both
     buttons are briefly mounted) only one is ever forced visible - forcing
     both is what showed two chevrons during the animation. Only visibility
     and color are touched; opacity/transform stay native. */
  div:has(section[data-testid="stSidebar"][aria-expanded="true"])
    [data-testid="stSidebarCollapseButton"] {
    visibility: visible !important;
  }
  div:has(section[data-testid="stSidebar"][aria-expanded="false"])
    [data-testid="stExpandSidebarButton"] {
    visibility: visible !important;
  }
  [data-testid="stSidebarCollapseButton"],
  [data-testid="stSidebarCollapseButton"] button,
  [data-testid="stExpandSidebarButton"] {
    color: #0E7C6B !important;
    background: transparent !important;
  }
  [data-testid="stSidebarCollapseButton"] span,
  [data-testid="stExpandSidebarButton"] span {
    color: #0E7C6B !important;
  }
  .block-container { max-width: 1120px; padding-top: 3rem; }
  .eyebrow { letter-spacing: .14em; font-size: 11px; font-weight: 700;
    color: #0E7C6B; margin-bottom: 2px; }
  h1 { font-size: 2.1rem !important; line-height: 1.15 !important;
    margin-top: 0 !important; }
  .lede { color: #5B6871; font-size: 1.02rem; max-width: 760px; }
  [data-testid="stMetric"] { background: #fff; border: 1px solid #E7EAE6;
    border-radius: 14px; padding: 14px 16px;
    box-shadow: 0 1px 2px rgba(26,35,50,.05); overflow: visible; }
  [data-testid="stMetricLabel"] { color: #5B6871 !important; font-size: 12px !important;
    letter-spacing: .04em; text-transform: uppercase; }
  [data-testid="stMetricValue"] { color: #1A2332 !important;
    font-size: 1.45rem !important; white-space: nowrap; }
  .insight { background: #EFF2EE; border: 1px solid #CFE3DC; border-radius: 14px;
    padding: 14px 18px; color: #1A2332; margin: 6px 0 18px 0; }
  .stTabs [data-baseweb="tab"] { font-size: 15px; }
  section[data-testid="stSidebar"] { background: #EFF2EE; }
</style>
"""

_PLOT_CONFIG = {"displayModeBar": False}


def pct_slider(label, value_pct, min_pct, max_pct, step, help_text):
    """Sidebar percent slider returning a fraction (6.0% -> 0.06)."""
    return st.slider(label, min_pct, max_pct, value_pct, step, help=help_text) / 100


def kpi(column, label, value, note, highlight=False):
    """One summary card. All pills share the same neutral tone except the one
    deliberately highlighted insight - the growth share, which stays green."""
    column.metric(label, value, delta=note, delta_color="normal" if highlight else "off")


def show_chart(fig) -> None:
    """Render a chart full-width without Plotly's modebar."""
    st.plotly_chart(fig, width="stretch", config=_PLOT_CONFIG)


def footer() -> None:
    """Render the bottom-page copyright notice."""
    st.caption(
        "© 2026 Mariusz Wisniewski - Snowball · [MIT license](https://github.com/mwisniewski/snowball)"
    )
