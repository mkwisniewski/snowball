import pandas as pd

from snowball.charts import (
    fig_allocation_growth,
    fig_fan,
    fig_final_mix,
    fig_histogram,
    fig_scenarios,
    fig_stacked_contrib_growth,
    save_html,
)
from snowball.config import PlanConfig
from snowball.engine import simulate_deterministic, simulate_monte_carlo


def _frame(years: int) -> pd.DataFrame:
    return simulate_deterministic(PlanConfig(years=years, monthly_investment=500.0))


def _all_figs(years: int):
    base = _frame(years)
    pct, finals = simulate_monte_carlo(
        PlanConfig(years=years, monthly_investment=500.0), n_paths=50, seed=1
    )
    scen = {"bear": base, "base": base, "bull": base}
    return [
        fig_stacked_contrib_growth(base),
        fig_allocation_growth(base),
        fig_final_mix(base.iloc[-1]),
        fig_scenarios(scen),
        fig_fan(pct),
        fig_histogram(finals),
    ]


def test_every_figure_builds_at_1_and_10_years():
    for years in (1, 10):
        for fig in _all_figs(years):
            assert len(fig.data) > 0


def test_tooltips_carry_values_not_raw_templates():
    for fig in _all_figs(5):
        for trace in fig.data:
            template = getattr(trace, "hovertemplate", None)
            if template:
                assert "%{" in template
                assert "Year %{" not in template  # year lives in the shared header


def test_save_html_roundtrip(tmp_path):
    path = save_html(fig_stacked_contrib_growth(_frame(3)), str(tmp_path / "x.html"))
    with open(path, encoding="utf-8") as f:
        assert f.read().count("plotly") > 0
