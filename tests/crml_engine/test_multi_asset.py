import pytest
import numpy as np
from crml_engine.simulation.engine import run_monte_carlo

# Synthetic YAML for a single scenario (scenario-only schema)
SINGLE_SCENARIO_YAML = """
crml_scenario: "1.0"
meta:
  name: "Single-Scenario Test"
scenario:
  frequency:
    basis: per_organization_per_year
    model: "poisson"
    parameters:
      lambda: 2.0
  severity:
    model: "lognormal"
    parameters:
      median: 1000
      sigma: 0.5
"""


def test_multi_asset_eal_aggregation():
    """
    Scenario-only schema supports a single frequency+severity pair.

    Frequency: Poisson(2.0)
    Severity: Lognormal(median=1000, sigma=0.5)
    Mean Severity ~= exp(ln(1000) + 0.5^2/2) = 1000 * exp(0.125) ~= 1133
    Expected Annual Loss ~= 2.0 * 1133 = 2266
    """
    result = run_monte_carlo(SINGLE_SCENARIO_YAML, n_runs=10000, seed=42)

    assert result.success, f"Simulation failed: {result.errors}"

    eal = result.metrics.eal
    print(f"Calculated EAL: {eal}")

    # Allow 5% margin of error for MC variability
    expected_eal = 2266.0
    margin = expected_eal * 0.05

    assert expected_eal - margin <= eal <= expected_eal + margin, \
        f"EAL {eal} not within 5% of expected {expected_eal}"


def test_fallback_to_global_severity():
    """
    Scenario-only schema always uses a single global severity.
    This test ensures the engine runs with a valid global severity.
    """
    yaml_fallback = """
    crml_scenario: "1.0"
    meta: {name: "Fallback Test"}
    scenario:
      frequency:
        basis: per_organization_per_year
        model: "poisson"
        parameters: {lambda: 10}
      severity:
        model: "lognormal"
        parameters: {median: 50, sigma: 0.1}
    """
    result = run_monte_carlo(yaml_fallback, n_runs=1000, seed=42)
    assert result.success
    # Should run with global severity
    assert result.metrics.eal > 0
