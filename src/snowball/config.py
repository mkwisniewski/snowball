"""Plan configuration as Pydantic models plus YAML loading.

Neutral defaults only - real numbers come from config.yaml (git-ignored).
"""

from __future__ import annotations

import yaml
from pydantic import BaseModel, ConfigDict


class _Strict(BaseModel):
    """Reject unknown keys - a typo'd field must fail loudly, not load as zero."""

    model_config = ConfigDict(extra="forbid")


class Person(_Strict):
    age_now: int = 0
    retirement_age: int = 65
    net_salary_monthly: float = 0.0
    rent_monthly: float = 0.0
    groceries_monthly: float = 0.0
    transport_monthly: float = 0.0
    other_monthly: float = 0.0
    monthly_investment_override: float | None = None
    monthly_savings_override: float | None = None
    investment_share: float = 1.0


class Balances(_Strict):
    brokerage_taxable: float = 0.0
    cash_buffer: float = 0.0
    pillar2: float = 0.0
    pillar3a: float = 0.0


class Assumptions(_Strict):
    years: int = 30
    inflation_annual: float = 0.01
    # The single forecasting belief: what the brokerage portfolio earns per
    # year, AFTER fund costs, BEFORE inflation. Bound it with bull/bear
    # scenarios instead of decomposing it per holding.
    expected_return_annual: float = 0.06
    savings_interest_annual: float = 0.0
    pillar2_interest_annual: float = 0.0125
    pillar2_monthly_contrib: float = 0.0
    pillar3a_annual_max: float = 0.0
    pillar3a_fee_annual: float = 0.0039
    pillar3a_equity_return_nominal: float = 0.065
    salary_growth_annual: float = 0.0
    volatility_annual: float = 0.16
    foreign_share_brokerage: float = 0.85
    fx_shock_total: float = 0.0


class PlanConfig(BaseModel):
    years: int = 30
    inflation_annual: float = 0.01
    investment_return_annual: float = 0.06  # nominal, net of fund costs
    savings_interest_annual: float = 0.0
    initial_investment: float = 0.0
    monthly_investment: float = 0.0
    initial_savings: float = 0.0
    monthly_savings: float = 0.0
    pillar2_balance: float = 0.0
    pillar2_interest_annual: float = 0.0125
    pillar2_monthly_contrib: float = 0.0
    pillar3a_balance: float = 0.0
    pillar3a_annual_contrib: float = 0.0
    pillar3a_fee_annual: float = 0.0039
    pillar3a_return_annual: float = 0.065
    # Yearly growth applied to monthly brokerage, cash and pillar 2 flows.
    # Pillar 3a is legally capped, so it stays flat.
    salary_growth_annual: float = 0.0
    volatility_annual: float = 0.16
    foreign_share_brokerage: float = 0.85
    fx_shock_total: float = 0.0

    @classmethod
    def assemble(cls, person: Person, balances: Balances, assumptions: Assumptions) -> PlanConfig:
        """Combine the YAML sections into one validated simulation config."""
        net_savings = (
            person.net_salary_monthly
            - person.rent_monthly
            - person.groceries_monthly
            - person.transport_monthly
            - person.other_monthly
        )
        monthly_investment = (
            person.monthly_investment_override
            if person.monthly_investment_override is not None
            else net_savings * person.investment_share
        )
        monthly_savings = (
            person.monthly_savings_override
            if person.monthly_savings_override is not None
            else net_savings * (1 - person.investment_share)
        )
        return cls(
            years=assumptions.years,
            inflation_annual=assumptions.inflation_annual,
            investment_return_annual=assumptions.expected_return_annual,
            savings_interest_annual=assumptions.savings_interest_annual,
            initial_investment=balances.brokerage_taxable,
            monthly_investment=monthly_investment,
            initial_savings=balances.cash_buffer,
            monthly_savings=monthly_savings,
            pillar2_balance=balances.pillar2,
            pillar2_interest_annual=assumptions.pillar2_interest_annual,
            pillar2_monthly_contrib=assumptions.pillar2_monthly_contrib,
            pillar3a_balance=balances.pillar3a,
            pillar3a_annual_contrib=assumptions.pillar3a_annual_max,
            pillar3a_fee_annual=assumptions.pillar3a_fee_annual,
            pillar3a_return_annual=assumptions.pillar3a_equity_return_nominal,
            salary_growth_annual=assumptions.salary_growth_annual,
            volatility_annual=assumptions.volatility_annual,
            foreign_share_brokerage=assumptions.foreign_share_brokerage,
            fx_shock_total=assumptions.fx_shock_total,
        )


def load_config(path: str = "config.yaml") -> tuple[PlanConfig, dict]:
    """Load YAML config into a PlanConfig + raw dict (for scenarios/withdrawal)."""
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    cfg = PlanConfig.assemble(
        Person(**raw.get("person", {})),
        Balances(**raw.get("starting_balances", {})),
        Assumptions(**raw.get("assumptions", {})),
    )
    return cfg, raw
