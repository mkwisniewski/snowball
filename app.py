"""Snowball - taxable brokerage + cash + pillar 2/3a.

Run:  streamlit run app.py
"""

import os
from dataclasses import dataclass

import numpy as np
import streamlit as st

from snowball.charts import (
    fig_allocation_growth,
    fig_fan,
    fig_final_mix,
    fig_histogram,
    fig_stacked_contrib_growth,
)
from snowball.config import load_config
from snowball.engine import simulate_deterministic, simulate_monte_carlo
from snowball.formatting import chf, chf_short
from snowball.ui import CSS, footer, kpi, pct_slider, show_chart

st.set_page_config(
    page_title="Snowball",
    page_icon="assets/favicon.svg",
    layout="wide",
)
st.markdown(CSS, unsafe_allow_html=True)


@dataclass(frozen=True)
class SimulationInputs:
    """Everything _run() needs: slider values plus the config cache-buster."""

    years: int
    monthly: float
    ret: float
    vol: float
    infl: float
    fx: float
    paths: int
    cfg_stamp: float  # config.yaml mtime: editing the config busts the cache
    contrib3a: float
    contrib_p2: float
    raise_: float
    seed: int = 42


@st.cache_data(show_spinner=False)
def _run(inputs: SimulationInputs):
    cfg0, _ = load_config("config.yaml")
    cfg = cfg0.model_copy(
        update={
            "years": inputs.years,
            "monthly_investment": inputs.monthly,
            "investment_return_annual": inputs.ret,
            "volatility_annual": inputs.vol,
            "inflation_annual": inputs.infl,
            "fx_shock_total": inputs.fx,
            "pillar3a_annual_contrib": inputs.contrib3a,
            "pillar2_monthly_contrib": inputs.contrib_p2,
            "salary_growth_annual": inputs.raise_,
        }
    )
    base = simulate_deterministic(cfg)
    pct, finals = simulate_monte_carlo(cfg, n_paths=inputs.paths, seed=inputs.seed)
    return cfg, base, pct, finals


# ---- Header ----
st.markdown('<div class="eyebrow">SNOWBALL · BROKERAGE + PILLARS</div>', unsafe_allow_html=True)
st.title("Will compounding do the heavy lifting?")
st.markdown(
    '<p class="lede">One honest projection of your savings - what you put in, what markets add, '
    "and how bumpy the ride can be. Tune the left panel; everything updates.</p>",
    unsafe_allow_html=True,
)

cfg_default, _ = load_config("config.yaml")

with st.sidebar:
    st.header("Your plan")
    years = st.slider(
        "Horizon (years)",
        1,
        50,
        min(max(cfg_default.years, 1), 50),
        help="How long you keep saving before touching the money.",
    )
    monthly = st.slider(
        "Monthly into brokerage (CHF)",
        0,
        10_000,
        int(cfg_default.monthly_investment),
        100,
        help="New savings after rent, food and bills.",
    )
    with st.expander("Returns & prices", expanded=True):
        ret = pct_slider(
            "Yearly return, before inflation (%)",
            cfg_default.investment_return_annual * 100,
            0.0,
            30.0,
            0.1,
            "Blended portfolio expectation. 6% nominal ≈ 5% after 1% inflation.",
        )
        infl = pct_slider(
            "Yearly inflation (%)",
            cfg_default.inflation_annual * 100,
            0.0,
            10.0,
            0.1,
            "Converts the future into today's francs. Swiss norm ≈ 1%.",
        )
    with st.expander("Contributions", expanded=True):
        contrib3a = st.slider(
            "Pillar 3a per year (CHF)",
            0,
            8000,
            int(cfg_default.pillar3a_annual_contrib),
            50,
            help="Legal max ~7,258 if employed with a pension fund. Capped, so no growth applies.",
        )
        contrib_p2 = st.slider(
            "Pillar 2 per month (CHF)",
            0,
            2500,
            int(cfg_default.pillar2_monthly_contrib),
            10,
            help="You + employer combined: yearly savings credits ÷ 12.",
        )
        raise_ = pct_slider(
            "Yearly raise (%)",
            cfg_default.salary_growth_annual * 100,
            0.0,
            5.0,
            0.1,
            "Grows monthly brokerage, cash and pillar 2 flows each year. 3a stays flat (capped).",
        )
    with st.expander("Risk: bumps & currency", expanded=True):
        vol = pct_slider(
            "Yearly ups & downs (%)",
            cfg_default.volatility_annual * 100,
            0.0,
            30.0,
            0.5,
            "100% equities ≈ 16%. Higher = wider fan, same middle.",
        )
        fx = pct_slider(
            "Dollar shock on foreign part (%)",
            cfg_default.fx_shock_total * 100,
            -40.0,
            20.0,
            1.0,
            "Brokerage accounts here hold ~85% foreign currency. -15% = a sustained weak dollar.",
        )
    paths = st.selectbox(
        "Simulated futures",
        [500, 2000, 5000],
        index=1,
        help="More paths = smoother bands, slower refresh.",
    )

cfg_stamp = os.path.getmtime("config.yaml")
cfg, base, pct, finals = _run(
    SimulationInputs(
        years=years,
        monthly=float(monthly),
        ret=ret,
        vol=vol,
        infl=infl,
        fx=fx,
        paths=int(paths),
        cfg_stamp=cfg_stamp,
        contrib3a=float(contrib3a),
        contrib_p2=float(contrib_p2),
        raise_=raise_,
    )
)
last = base.iloc[-1]
growth = float(last["growth_cum"])
growth_share = growth / last["total_nominal"] if last["total_nominal"] else 0

# ---- KPI cards (compact values; exact francs live in the insight bar) ----
k1, k2, k3, k4 = st.columns(4)
growth_note = f"{growth_share:.0%} is growth" if growth >= 0 else "markets underwater"
kpi(k1, "Projected total", chf_short(last["total_nominal"]), growth_note, highlight=True)
kpi(k2, "In today's money", chf_short(last["total_real"]), "after inflation")
kpi(k3, "You paid in", chf_short(last["contributions_cum"]), "deposits + pillars")
kpi(k4, "If dollar falls", chf_short(last["total_fx_adj"]), f"{fx:+.0%} shock")

if growth >= 0:
    insight_growth = f"and compounding adds <b>{chf(growth)}</b>."
else:
    insight_growth = f"but markets are underwater by <b>{chf(-growth)}</b>."
st.markdown(
    f'<div class="insight">Of <b>{chf(last["total_nominal"])}</b>, '
    f"you deposit <b>{chf(last['contributions_cum'])}</b> {insight_growth} "
    f"In today's francs that future is worth <b>{chf(last['total_real'])}</b>.</div>",
    unsafe_allow_html=True,
)

tab_overview, tab_home, tab_risk, tab_data = st.tabs(
    ["Overview", "Where it lives", "How bumpy?", "Details & download"]
)

with tab_overview:
    show_chart(fig_stacked_contrib_growth(base))
    st.caption(
        "Deposits climb with your savings habit; growth accelerates with time. "
        "Once growth outweighs deposits, compounding does most of the work."
    )

with tab_home:
    c_left, c_right = st.columns([3, 2])
    with c_left:
        show_chart(fig_allocation_growth(base))
    with c_right:
        show_chart(fig_final_mix(last))
    st.caption(
        "Pillars grow on fixed contributions. Cash is an emergency buffer, "
        "so it stays flat by design."
    )

with tab_risk:
    p10, p50, p90 = (float(np.percentile(finals, q)) for q in (10, 50, 90))
    r1, r2, r3 = st.columns(3)
    r1.metric("Bad luck (1 in 10)", chf_short(p10))
    r2.metric("Middle path", chf_short(p50))
    r3.metric("Good luck (1 in 10)", chf_short(p90))
    show_chart(fig_fan(pct))
    show_chart(fig_histogram(finals))
    st.caption(
        f"The fan shows the journey, the histogram the destination - both from "
        f"the same {len(finals):,} simulated futures. A wider band means more "
        f"uncertainty, not higher returns."
    )

with tab_data:
    friendly = (
        base.rename(
            columns={
                "year": "Year",
                "brokerage": "Brokerage",
                "pillar3a": "Pillar 3a",
                "pillar2": "Pillar 2",
                "cash": "Cash",
                "total_nominal": "Total",
                "total_real": "Total (today's CHF)",
                "contributions_cum": "Paid in",
                "growth_cum": "Growth",
                "brokerage_fx_adj": "Brokerage (FX shock)",
                "total_fx_adj": "Total (FX shock)",
            }
        )
        # Year as the row label: drops pandas' redundant 0-based index column.
        .set_index("Year")
    )
    # Exact-fit height for up to 10 rows (~35px each + header); beyond that the
    # grid scrolls instead of growing. So a 10-year horizon fits fully and the
    # scrollbar only appears from 11 years on.
    table_height = 48 + 34 * min(len(friendly), 10)
    st.dataframe(
        friendly.style.format("{:,.0f}"),
        width="stretch",
        height=table_height,
    )
    st.download_button(
        "Download table (CSV)", base.to_csv(index=False), "projection.csv", "text/csv"
    )
    with st.expander("Assumptions & method"):
        st.markdown(
            f"* Brokerage starts CHF {cfg.initial_investment:,.0f}, "
            f"pillar 2 CHF {cfg.pillar2_balance:,.0f}, "
            f"3a CHF {cfg.pillar3a_balance:,.0f}.\n"
            f"* 3a: CHF {cfg.pillar3a_annual_contrib:,.0f}/yr at "
            f"~{cfg.pillar3a_return_annual:.1%} minus {cfg.pillar3a_fee_annual:.2%} "
            "fee, each January.\n"
            f"* Pillar 2 at {cfg.pillar2_interest_annual:.2%} + "
            f"CHF {cfg.pillar2_monthly_contrib:,.0f}/mo.\n"
            "* Monte Carlo shakes only the brokerage sleeve; pillars stay steady.\n"
            "* FX shock fades in linearly over the horizon."
        )

st.caption("Educational model, not advice. Lines flatter reality - trust the band.")
footer()
