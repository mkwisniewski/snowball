"""Simulation math: deterministic growth, scenarios, Monte Carlo, FX, withdrawal.

Pure functions over PlanConfig (see config.py) - no file I/O in here.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from snowball.config import PlanConfig


def _monthly_rate(annual: float) -> float:
    return (1.0 + annual) ** (1.0 / 12.0) - 1.0


def simulate_deterministic(cfg: PlanConfig) -> pd.DataFrame:
    """Yearly deterministic projection with pillars, real values and FX shock.

    Returns DataFrame with columns: year, brokerage, cash, pillar2, pillar3a,
    total_nominal, contributions_cum, growth_cum, total_real, brokerage_fx_adj.
    """
    r_inv = _monthly_rate(cfg.investment_return_annual)
    r_cash = _monthly_rate(cfg.savings_interest_annual)
    r_p2 = _monthly_rate(cfg.pillar2_interest_annual)
    # 3a: 99% equities + 1% cash, minus flat fee
    r_3a = _monthly_rate(cfg.pillar3a_return_annual * 0.99 - cfg.pillar3a_fee_annual)

    brokerage, cash, p2, p3a = (
        cfg.initial_investment,
        cfg.initial_savings,
        cfg.pillar2_balance,
        cfg.pillar3a_balance,
    )
    contrib0 = (
        cfg.initial_investment + cfg.initial_savings + cfg.pillar2_balance + cfg.pillar3a_balance
    )
    contrib_cum = contrib0
    rows = []
    for year in range(1, cfg.years + 1):
        pay_raise = (1 + cfg.salary_growth_annual) ** (year - 1)
        monthly_investment = cfg.monthly_investment * pay_raise
        monthly_savings = cfg.monthly_savings * pay_raise
        pillar2_contrib = cfg.pillar2_monthly_contrib * pay_raise
        for m in range(12):
            brokerage = (brokerage + monthly_investment) * (1 + r_inv)
            cash = (cash + monthly_savings) * (1 + r_cash)
            p2 = (p2 + pillar2_contrib) * (1 + r_p2)
            # 3a is contributed once a year in January (front-loads compounding
            # slightly vs monthly; documented in README).
            january_topup = cfg.pillar3a_annual_contrib if m == 0 else 0.0
            p3a = (p3a + january_topup) * (1 + r_3a)
        total = brokerage + cash + p2 + p3a
        contrib_cum += (
            12 * (monthly_investment + monthly_savings + pillar2_contrib)
            + cfg.pillar3a_annual_contrib
        )
        # Linear FX shock: foreign share of brokerage drifts with fx_shock_total
        fx_factor = 1.0 + cfg.fx_shock_total * (year / cfg.years) if cfg.years else 1.0
        brokerage_fx = brokerage * (
            1 - cfg.foreign_share_brokerage + cfg.foreign_share_brokerage * fx_factor
        )
        rows.append(
            {
                "year": year,
                "brokerage": brokerage,
                "cash": cash,
                "pillar2": p2,
                "pillar3a": p3a,
                "total_nominal": total,
                "contributions_cum": contrib_cum,
                "growth_cum": total - contrib_cum,
                "total_real": total / ((1 + cfg.inflation_annual) ** year),
                "brokerage_fx_adj": brokerage_fx,
                "total_fx_adj": brokerage_fx + cash + p2 + p3a,
            }
        )
    return pd.DataFrame(rows)


def simulate_scenarios(
    cfg: PlanConfig, scenarios: dict[str, float | None]
) -> dict[str, pd.DataFrame]:
    """Run one deterministic projection per scenario.

    scenarios: name -> annual return override (None = use cfg blended return).
    """
    out: dict[str, pd.DataFrame] = {}
    for name, override in scenarios.items():
        c = cfg.model_copy()
        if override is not None:
            c.investment_return_annual = float(override)
        out[name] = simulate_deterministic(c)
    return out


def simulate_monte_carlo(
    cfg: PlanConfig,
    n_paths: int = 2_000,
    seed: int = 42,
    mean_annual: float | None = None,
) -> tuple[pd.DataFrame, np.ndarray]:
    """Monte Carlo on the brokerage sleeve; pillars stay deterministic.

    Returns (percentiles_df with p10/p50/p90 of total, finals array of total_nominal).
    Monthly lognormal-ish draws: r ~ N(mean_m, vol_m). Contributions added monthly.
    """
    rng = np.random.default_rng(seed)
    mean = cfg.investment_return_annual if mean_annual is None else mean_annual
    mean_m = mean / 12.0
    vol_m = cfg.volatility_annual / np.sqrt(12.0)
    months = cfg.years * 12

    shocks = rng.normal(loc=mean_m, scale=vol_m, size=(n_paths, months))
    brokerage_paths = np.empty((n_paths, cfg.years))
    for i in range(n_paths):
        bal = cfg.initial_investment
        for m in range(months):
            year = m // 12  # 0-based: contributions grow with salary each year
            pmt = cfg.monthly_investment * (1 + cfg.salary_growth_annual) ** year
            bal = (bal + pmt) * (1 + shocks[i, m])
            if (m + 1) % 12 == 0:
                brokerage_paths[i, (m + 1) // 12 - 1] = bal

    # Deterministic non-brokerage sleeves (same every path)
    base = simulate_deterministic(cfg)
    non_brokerage = (base["cash"] + base["pillar2"] + base["pillar3a"]).to_numpy()
    totals = brokerage_paths + non_brokerage[None, :]
    pct = pd.DataFrame(
        {
            "year": np.arange(1, cfg.years + 1),
            "p10": np.percentile(totals, 10, axis=0),
            "p50": np.percentile(totals, 50, axis=0),
            "p90": np.percentile(totals, 90, axis=0),
        }
    )
    return pct, totals[:, -1]


def max_drawdown(series: pd.Series) -> float:
    """Max peak-to-trough drawdown as a fraction (e.g. 0.25 = -25%)."""
    peak = series.cummax()
    dd = (series - peak) / peak.replace(0, np.nan)
    return float(dd.min(skipna=True))


def withdrawal_plan(
    capital_at_retirement: float,
    rate_annual: float = 0.04,
    years_retired: int = 25,
    return_annual: float = 0.03,
    inflation_annual: float = 0.01,
) -> pd.DataFrame:
    """Simple post-retirement drawdown: real spending kept constant."""
    spend0 = capital_at_retirement * rate_annual
    rows, bal = [], capital_at_retirement
    for y in range(1, years_retired + 1):
        spend = spend0 * ((1 + inflation_annual) ** (y - 1))
        bal = bal * (1 + return_annual) - spend
        rows.append({"year_retired": y, "spend_nominal": spend, "balance": max(bal, 0.0)})
        if bal <= 0:
            break
    return pd.DataFrame(rows)
