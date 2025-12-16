"""Portfolio planning / resolution helpers.

This package lives in `crml_lang` on purpose: it resolves CRML documents
(portfolios + scenarios + packs) into an execution-friendly plan, without
running any simulation.

The runtime/simulation step belongs in `crml_engine`.
"""

from .portfolio_planner import (
    PlanMessage,
    PlanReport,
    PortfolioExecutionPlan,
    ResolvedScenario,
    ResolvedScenarioControl,
    plan_portfolio,
)

__all__ = [
    "PlanMessage",
    "PlanReport",
    "PortfolioExecutionPlan",
    "ResolvedScenario",
    "ResolvedScenarioControl",
    "plan_portfolio",
]
