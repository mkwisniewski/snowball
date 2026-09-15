import numpy as np

from snowball.config import PlanConfig
from snowball.engine import simulate_deterministic, simulate_monte_carlo


def _cfg(**kw):
    base = PlanConfig(
        years=10,
        inflation_annual=0.01,
        investment_return_annual=0.05,
        savings_interest_annual=0.01,
        initial_investment=110_000.0,
        monthly_investment=5_000.0,
        initial_savings=17_000.0,
        monthly_savings=0.0,
        pillar2_balance=0.0,
        pillar2_monthly_contrib=0.0,
        pillar3a_balance=0.0,
        pillar3a_annual_contrib=0.0,
    )
    for k, v in kw.items():
        setattr(base, k, v)
    return base


def test_zero_return_equals_contributions():
    cfg = _cfg(investment_return_annual=0.0, savings_interest_annual=0.0)
    df = simulate_deterministic(cfg)
    last = df.iloc[-1]
    expected = 110_000 + 17_000 + 10 * 12 * 5_000
    assert abs(last["total_nominal"] - expected) < 1.0
    assert abs(last["growth_cum"]) < 1.0


def test_known_fv_matches_closed_form():
    # Monthly compounding FV: P*(1+r)^n + PMT*[((1+r)^n - 1)/r]*(1+r) (payment at start of month,
    # matching engine's (bal + pmt)*(1+r) convention).
    cfg = _cfg(
        years=10,
        investment_return_annual=0.05,
        monthly_investment=1_000.0,
        initial_investment=0.0,
        initial_savings=0.0,
        pillar2_balance=0.0,
    )
    df = simulate_deterministic(cfg)
    r = (1.05) ** (1 / 12) - 1
    n = 120
    expected = 1_000 * (((1 + r) ** n - 1) / r) * (1 + r)
    assert abs(df.iloc[-1]["brokerage"] - expected) / expected < 1e-9


def test_real_is_nominal_deflated():
    cfg = _cfg()
    df = simulate_deterministic(cfg)
    last = df.iloc[-1]
    assert abs(last["total_real"] - last["total_nominal"] / (1.01**10)) < 1.0


def test_salary_growth_raises_total_and_paid_in():
    flat = simulate_deterministic(_cfg())
    grown = simulate_deterministic(_cfg(salary_growth_annual=0.03))
    assert grown.iloc[-1]["total_nominal"] > flat.iloc[-1]["total_nominal"]
    assert grown.iloc[-1]["contributions_cum"] > flat.iloc[-1]["contributions_cum"]
    # Pillars stay deterministic: accounting must balance exactly.
    last = grown.iloc[-1]
    assert abs(last["total_nominal"] - last["contributions_cum"] - last["growth_cum"]) < 1e-6


def test_monte_carlo_percentiles_ordered_and_shaped():
    cfg = _cfg(years=10)
    pct, finals = simulate_monte_carlo(cfg, n_paths=300, seed=7)
    assert finals.shape == (300,)
    assert (pct["p10"] <= pct["p50"]).all() and (pct["p50"] <= pct["p90"]).all()
    # median of stochastic ≈ deterministic when vol is symmetric in linear space (rough check)
    det = simulate_deterministic(cfg).iloc[-1]["total_nominal"]
    assert abs(np.median(finals) - det) / det < 0.15
