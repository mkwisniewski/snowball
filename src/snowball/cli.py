"""CLI: deterministic plan + scenarios + Monte Carlo + exports."""

from __future__ import annotations

import argparse
import os

import numpy as np
import pandas as pd

from snowball.charts import (
    fig_allocation_growth,
    fig_fan,
    fig_histogram,
    fig_scenarios,
    fig_stacked_contrib_growth,
    save_html,
)
from snowball.config import load_config
from snowball.engine import (
    max_drawdown,
    simulate_deterministic,
    simulate_monte_carlo,
    simulate_scenarios,
    withdrawal_plan,
)
from snowball.reporting import export_csv, export_workbook

try:
    from rich.console import Console
    from rich.table import Table

    _RICH = True
    console = Console()
except Exception:  # rich optional
    _RICH = False
    console = None  # type: ignore


def _print_table(df: pd.DataFrame, title: str) -> None:
    if _RICH:
        assert console is not None
        t = Table(title=title, show_lines=False)
        for c in df.columns:
            t.add_column(c, justify="right")
        for _, row in df.tail(10).iterrows():
            t.add_row(*[f"{v:,.0f}" if isinstance(v, float) else str(v) for v in row])
        console.print(t)
    else:
        print(f"\n{title}")
        print(df.tail(10).to_string(index=False))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Snowball: taxable brokerage + cash + pillar 2/3a.")
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--years", type=int, default=None)
    # legacy overrides (kept)
    p.add_argument("--investment-return-rate", type=float, default=None)
    p.add_argument("--savings-interest-rate", type=float, default=None)
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--no-plot", action="store_true")
    # new
    p.add_argument("--inflation", type=float, default=None)
    p.add_argument("--monthly-investment", type=float, default=None)
    p.add_argument("--salary-growth", type=float, default=None, help="Yearly raise, e.g. 0.03.")
    p.add_argument("--monte-carlo", type=int, default=2000, help="0 to disable.")
    p.add_argument("--vol", type=float, default=None, help="Annual vol for Monte Carlo.")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--fx-shock", type=float, default=None, help="e.g. -0.15 = foreign leg -15%.")
    p.add_argument("--export-csv", default=None, help="Path for yearly projection CSV.")
    p.add_argument("--export-xlsx", default=None, help="Path for workbook export.")
    p.add_argument("--html-dir", default="reports", help="Where to write Plotly HTML.")
    p.add_argument("--withdrawal-rate", type=float, default=0.04)
    return p


def main() -> None:
    args = build_parser().parse_args()
    cfg, raw = load_config(args.config)

    if args.years is not None:
        cfg.years = args.years
    if args.investment_return_rate is not None:
        cfg.investment_return_annual = args.investment_return_rate
    if args.savings_interest_rate is not None:
        cfg.savings_interest_annual = args.savings_interest_rate
    if args.inflation is not None:
        cfg.inflation_annual = args.inflation
    if args.monthly_investment is not None:
        cfg.monthly_investment = args.monthly_investment
    if args.salary_growth is not None:
        cfg.salary_growth_annual = args.salary_growth
    if args.vol is not None:
        cfg.volatility_annual = args.vol
    if args.fx_shock is not None:
        cfg.fx_shock_total = args.fx_shock

    header = (
        f"Plan: {cfg.years}y | Brokerage {cfg.initial_investment:,.0f} + "
        f"{cfg.monthly_investment:,.0f}/mo @ {cfg.investment_return_annual:.2%} nom | "
        f"cash {cfg.initial_savings:,.0f} | "
        f"p2 {cfg.pillar2_balance:,.0f} | 3a {cfg.pillar3a_annual_contrib:,.0f}/yr | "
        f"infl {cfg.inflation_annual:.2%} | vol {cfg.volatility_annual:.0%}"
    )
    if _RICH:
        assert console is not None
        console.rule("Finance plan")
        console.print(header)
    else:
        print(header)

    base = simulate_deterministic(cfg)
    last = base.iloc[-1]
    real_cagr_note = (
        f"real ≈ {(1 + cfg.investment_return_annual) / (1 + cfg.inflation_annual) - 1:.2%}"
    )
    summary = (
        f"\nFinal (year {cfg.years}): total {last['total_nominal']:,.0f} CHF nominal "
        f"({last['total_real']:,.0f} in today's CHF), "
        f"paid in {last['contributions_cum']:,.0f}, "
        f"growth {last['growth_cum']:,.0f}. "
        f"Brokerage {last['brokerage']:,.0f} / 3a {last['pillar3a']:,.0f} / "
        f"p2 {last['pillar2']:,.0f} / cash {last['cash']:,.0f}. "
        f"Blended brokerage {cfg.investment_return_annual:.2%} nom, {real_cagr_note}. "
        f"FX-adj total @ {cfg.fx_shock_total:+.0%}: {last['total_fx_adj']:,.0f}."
    )
    if _RICH:
        assert console is not None
        console.print(summary)
    else:
        print(summary)

    if args.verbose:
        show = base[
            ["year", "brokerage", "pillar3a", "pillar2", "cash", "total_nominal", "total_real"]
        ].copy()
        _print_table(show, "Yearly projection (last 10 rows)")

    # Scenarios: bear / base / bull
    scen_cfg = raw.get("scenarios", {}) or {}
    scen_overrides: dict[str, float | None] = {
        "bear": scen_cfg.get("bear", {}).get("investment_return_annual", 0.03),
        "base": None,
        "bull": scen_cfg.get("bull", {}).get("investment_return_annual", 0.07),
    }
    scen = simulate_scenarios(cfg, scen_overrides)
    for name, df in scen.items():
        r = df.iloc[-1]["total_nominal"]
        print(f"  scenario {name:<4}: {r:,.0f} CHF")

    # Monte Carlo
    if args.monte_carlo and args.monte_carlo > 0:
        pct, finals = simulate_monte_carlo(cfg, n_paths=args.monte_carlo, seed=args.seed)
        print(
            f"Monte Carlo ({args.monte_carlo} paths, vol {cfg.volatility_annual:.0%}): "
            f"P10 {np.percentile(finals, 10):,.0f} / P50 {np.percentile(finals, 50):,.0f} / "
            f"P90 {np.percentile(finals, 90):,.0f} CHF. "
            f"P(fail below paid-in) {(finals < base.iloc[-1]['contributions_cum']).mean():.1%}"
        )
    else:
        pct, finals = None, None  # type: ignore

    # Withdrawal sketch at retirement
    wd = withdrawal_plan(
        float(last["total_nominal"]),
        rate_annual=args.withdrawal_rate,
        inflation_annual=cfg.inflation_annual,
    )
    print(
        f"Withdrawal @ {args.withdrawal_rate:.0%}: "
        f"year-1 spend {wd.iloc[0]['spend_nominal']:,.0f} CHF, "
        f"lasts {len(wd)}y in sketch (3% post-ret return)."
    )
    print(f"Deterministic max drawdown of total line: {max_drawdown(base['total_nominal']):.1%}")

    # Exports
    if args.export_csv:
        print(f"CSV -> {export_csv(base, args.export_csv)}")
    if args.export_xlsx:
        # Base scenario intentionally omitted (matches historical output).
        variants = {"bear": scen["bear"], "bull": scen["bull"]}
        print(f"XLSX -> {export_workbook(base, variants, pct, args.export_xlsx)}")

    # Interactive charts
    if not args.no_plot:
        os.makedirs(args.html_dir, exist_ok=True)
        paths = [
            save_html(fig_stacked_contrib_growth(base), f"{args.html_dir}/stacked.html"),
            save_html(fig_allocation_growth(base), f"{args.html_dir}/wrappers.html"),
            save_html(fig_scenarios(scen), f"{args.html_dir}/scenarios.html"),
        ]
        if pct is not None:
            paths.append(save_html(fig_fan(pct), f"{args.html_dir}/fan.html"))
            paths.append(save_html(fig_histogram(finals), f"{args.html_dir}/histogram.html"))
        print("HTML charts -> " + ", ".join(paths))


if __name__ == "__main__":
    main()
