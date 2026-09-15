import numpy as np
from yaml import safe_load

from snowball.config import Assumptions, Balances, Person, PlanConfig, load_config
from snowball.engine import simulate_deterministic


def _small_cfg() -> PlanConfig:
    return PlanConfig(
        years=1,
        monthly_investment=1_000.0,
        pillar2_monthly_contrib=100.0,
        pillar3a_annual_contrib=2_000.0,
    )


def test_example_config_parses():
    with open("config.example.yaml", encoding="utf-8") as f:
        raw = safe_load(f)
    Assumptions(**raw.get("assumptions", {}))  # schema-valid without returns


def test_assemble_passes_expected_return_through():
    assumptions = Assumptions(expected_return_annual=0.055)
    cfg = PlanConfig.assemble(Person(), Balances(), assumptions)
    assert cfg.investment_return_annual == 0.055


def test_example_config_loads_end_to_end():
    cfg, raw = load_config("config.example.yaml")
    assert cfg.years > 0
    assert cfg.investment_return_annual > 0
    assert "assumptions" in raw


def test_config_defaults_are_neutral():
    cfg = PlanConfig()
    assert cfg.initial_investment == 0.0
    assert cfg.monthly_investment == 0.0
    assert cfg.pillar2_balance == 0.0
    assert cfg.pillar3a_annual_contrib == 0.0
    assert simulate_deterministic(_small_cfg()).iloc[-1]["total_nominal"] > 0
    assert np.isfinite(simulate_deterministic(cfg)).all().all()
