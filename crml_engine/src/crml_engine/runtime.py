import json
from typing import Union, Optional
from crml_engine.pipeline import plan_portfolio
import numpy as np

from .models.result_model import SimulationResult, Metrics, Distribution, Metadata, print_result
from crml_lang.models.result_envelope import (
    CurrencyUnit,
    EngineInfo,
    HistogramArtifact,
    InputInfo,
    Measure,
    RunInfo,
    SamplesArtifact,
    SimulationResultEnvelope,
    Units,
    now_utc,
)
from .models.fx_model import (
    FXConfig, 
    load_fx_config, 
    normalize_fx_config, 
    convert_currency, 
    get_currency_symbol
)
from .models.constants import DEFAULT_FX_RATES
from .simulation.engine import run_monte_carlo
from .simulation.severity import SeverityEngine
from .copula import gaussian_copula_uniforms


LOSS_VAR_ID = "loss.var"
VALUE_AT_RISK_LABEL = "Value at Risk"


def _portfolio_error_result(msg: str) -> SimulationResult:
    return SimulationResult(
        success=False,
        metrics=None,
        distribution=None,
        metadata=None,
        errors=[msg],
    )


def _collect_control_info(scenarios: list[object]) -> dict[str, dict[str, object]]:
    control_info: dict[str, dict[str, object]] = {}
    for sc in scenarios:
        for c in sc.controls:
            control_info.setdefault(
                c.id,
                {
                    "reliability": float(c.combined_reliability) if c.combined_reliability is not None else 1.0,
                    "affects": str(c.affects) if c.affects is not None else "frequency",
                },
            )
    return control_info


def _extract_copula_targets(dependency: object) -> tuple[list[str], np.ndarray | None]:
    dep = dependency if isinstance(dependency, dict) else {}
    cop = (dep.get("copula") if isinstance(dep, dict) else None) or None

    target_controls: list[str] = []
    corr = None
    if isinstance(cop, dict):
        targets = cop.get("targets")
        matrix = cop.get("matrix")
        if isinstance(targets, list) and isinstance(matrix, list):
            for t in targets:
                if isinstance(t, str) and t.startswith("control:") and t.endswith(":state"):
                    target_controls.append(t[len("control:") : -len(":state")])
            corr = np.asarray(matrix, dtype=np.float64)
    return target_controls, corr


def _sample_control_state(
    *,
    control_info: dict[str, dict[str, object]],
    target_controls: list[str],
    corr: np.ndarray | None,
    n_runs: int,
    seed: int | None,
) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    control_state: dict[str, np.ndarray] = {}

    if target_controls and corr is not None:
        u = gaussian_copula_uniforms(corr=corr, n=n_runs, seed=seed)
        for i, cid in enumerate(target_controls):
            rel = float(control_info.get(cid, {}).get("reliability", 1.0))
            control_state[cid] = (u[:, i] <= rel).astype(np.float64)
        return control_state

    for cid, info in control_info.items():
        rel = float(info.get("reliability", 1.0))
        control_state[cid] = (rng.random(n_runs) <= rel).astype(np.float64)
    return control_state


def _load_text_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _control_multipliers_for_scenario(sc: object, control_state: dict[str, np.ndarray], n_runs: int) -> tuple[np.ndarray, np.ndarray]:
    freq_mult = np.ones(n_runs, dtype=np.float64)
    sev_mult = np.ones(n_runs, dtype=np.float64)

    for ctrl in sc.controls:
        eff = float(ctrl.combined_implementation_effectiveness or 0.0)
        cov = float(ctrl.combined_coverage_value if ctrl.combined_coverage_value is not None else 1.0)
        state = control_state.get(ctrl.id)
        if state is None:
            state = np.ones(n_runs, dtype=np.float64)
        reduction = eff * cov * state
        affects = (ctrl.affects or "frequency").lower()
        if affects in ("frequency", "both"):
            freq_mult = freq_mult * (1.0 - reduction)
        if affects in ("severity", "both"):
            sev_mult = sev_mult * (1.0 - reduction)

    return freq_mult, sev_mult


def _aggregate_portfolio_losses(
    *,
    semantics: str,
    scenario_losses: list[np.ndarray],
    scenario_weights: list[float],
    n_runs: int,
    seed: int | None,
) -> np.ndarray:
    stacked = np.vstack(scenario_losses)  # shape: (n_scen, n_runs)

    if semantics == "sum":
        return np.sum(stacked, axis=0)
    if semantics == "max":
        return np.max(stacked, axis=0)

    if semantics in ("mixture", "choose_one"):
        weights = np.asarray(scenario_weights, dtype=np.float64)
        if np.isnan(weights).any():
            weights = np.ones(len(scenario_losses), dtype=np.float64)
        wsum = float(np.sum(weights))
        if wsum <= 0:
            weights = np.ones(len(scenario_losses), dtype=np.float64)
            wsum = float(np.sum(weights))
        weights = weights / wsum

        rng = np.random.default_rng(seed)
        pick = rng.choice(len(scenario_losses), size=n_runs, replace=True, p=weights)
        return stacked[pick, np.arange(n_runs)]

    raise ValueError(f"Unsupported portfolio semantics '{semantics}'")


def _run_single_portfolio_scenario(
    *,
    sc: object,
    idx: int,
    control_state: dict[str, np.ndarray],
    n_runs: int,
    seed: int | None,
    fx_config: FXConfig,
) -> tuple[np.ndarray, float]:
    scenario_path = sc.resolved_path or sc.path
    if not scenario_path:
        raise ValueError(f"Scenario '{sc.id}' has no path")

    try:
        scenario_yaml = _load_text_file(scenario_path)
    except Exception as e:
        raise ValueError(f"Failed to read scenario '{sc.id}': {e}") from e

    freq_mult, sev_mult = _control_multipliers_for_scenario(sc, control_state, n_runs)

    scenario_seed = None if seed is None else int(seed + idx * 1000)
    res = run_monte_carlo(
        scenario_yaml,
        n_runs=n_runs,
        seed=scenario_seed,
        fx_config=fx_config,
        cardinality=int(sc.cardinality or 1),
        frequency_rate_multiplier=freq_mult,
        severity_loss_multiplier=sev_mult,
        raw_data_limit=n_runs,
    )
    if not res.success or res.distribution is None:
        errors = list(res.errors or [f"Scenario '{sc.id}' failed"])
        raise RuntimeError("; ".join(errors))

    losses = np.asarray(res.distribution.raw_data, dtype=np.float64)
    if losses.shape != (n_runs,):
        raise ValueError(f"Scenario '{sc.id}' did not return {n_runs} samples")

    weight = float(sc.weight) if sc.weight is not None else float("nan")
    return losses, weight


def _run_portfolio_scenarios(
    *,
    scenarios: list[object],
    control_state: dict[str, np.ndarray],
    n_runs: int,
    seed: int | None,
    fx_config: FXConfig,
) -> tuple[list[np.ndarray], list[float]]:
    scenario_losses: list[np.ndarray] = []
    scenario_weights: list[float] = []

    for idx, sc in enumerate(scenarios):
        losses, weight = _run_single_portfolio_scenario(
            sc=sc,
            idx=idx,
            control_state=control_state,
            n_runs=n_runs,
            seed=seed,
            fx_config=fx_config,
        )
        scenario_losses.append(losses)
        scenario_weights.append(weight)

    return scenario_losses, scenario_weights


def _compute_metrics_and_distribution(total: np.ndarray, *, bin_count: int = 50) -> tuple[Metrics, Distribution]:
    total = np.asarray(total, dtype=np.float64)
    metrics = Metrics(
        eal=float(np.mean(total)),
        var_95=float(np.percentile(total, 95)),
        var_99=float(np.percentile(total, 99)),
        var_999=float(np.percentile(total, 99.9)),
        min=float(np.min(total)),
        max=float(np.max(total)),
        median=float(np.median(total)),
        std_dev=float(np.std(total)),
    )

    hist, bin_edges = np.histogram(total, bins=bin_count)
    distribution = Distribution(
        bins=bin_edges.tolist(),
        frequencies=hist.tolist(),
        raw_data=total.tolist()[:1000],
    )
    return metrics, distribution


def run_portfolio_simulation(
    portfolio_source: Union[str, dict],
    *,
    source_kind: str = "path",
    n_runs: int = 10000,
    seed: int | None = None,
    fx_config: Optional[FXConfig] = None,
) -> SimulationResult:
    """Run a CRML portfolio with optional copula-dependent control states.

    This is a reference implementation intended to demonstrate the spec.
    Portfolio semantics supported: sum, mixture, choose_one, max.

    Copula support (v1): Gaussian copula over control:<id>:state targets.
    """

    fx_config = normalize_fx_config(fx_config)
    output_symbol = get_currency_symbol(fx_config.output_currency)

    report = plan_portfolio(portfolio_source, source_kind=source_kind)  # type: ignore[arg-type]
    if not report.ok or report.plan is None:
        errors = [e.message for e in (report.errors or [])]
        return SimulationResult(success=False, errors=errors)

    plan = report.plan
    semantics = plan.semantics_method
    scenarios = list(plan.scenarios)
    if not scenarios:
        return _portfolio_error_result("Portfolio contains no scenarios")

    control_info = _collect_control_info(scenarios)
    target_controls, corr = _extract_copula_targets(plan.dependency)
    control_state = _sample_control_state(
        control_info=control_info,
        target_controls=target_controls,
        corr=corr,
        n_runs=n_runs,
        seed=seed,
    )

    try:
        scenario_losses, scenario_weights = _run_portfolio_scenarios(
            scenarios=scenarios,
            control_state=control_state,
            n_runs=n_runs,
            seed=seed,
            fx_config=fx_config,
        )
    except (ValueError, RuntimeError) as e:
        return _portfolio_error_result(str(e))

    try:
        total = _aggregate_portfolio_losses(
            semantics=semantics,
            scenario_losses=scenario_losses,
            scenario_weights=scenario_weights,
            n_runs=n_runs,
            seed=seed,
        )
    except ValueError as e:
        return _portfolio_error_result(str(e))

    metrics, distribution = _compute_metrics_and_distribution(total, bin_count=50)
    return SimulationResult(
        success=True,
        metrics=metrics,
        distribution=distribution,
        metadata=Metadata(
            runs=n_runs,
            seed=seed,
            currency=output_symbol,
            currency_code=fx_config.output_currency,
            model_name=plan.portfolio_name,
            model_version="N/A",
            description="",
            controls_applied=True,
        ),
        errors=[],
    )

def run_simulation(
    yaml_content: Union[str, dict], 
    n_runs: int = 10000, 
    seed: int | None = None, 
    fx_config: Optional[FXConfig] = None
) -> SimulationResult:
    """
    Run a Monte Carlo simulation for a CRML scenario.

    This is a convenience wrapper around
    `crml_engine.simulation.engine.run_monte_carlo`.
    """
    return run_monte_carlo(yaml_content, n_runs, seed, fx_config)


def run_simulation_envelope(
    yaml_content: Union[str, dict],
    n_runs: int = 10000,
    seed: int | None = None,
    fx_config: Optional[FXConfig] = None,
) -> SimulationResultEnvelope:
    """Runs a simulation and returns the engine-agnostic result envelope."""

    result = run_simulation(yaml_content, n_runs=n_runs, seed=seed, fx_config=fx_config)

    try:
        from importlib import metadata as importlib_metadata

        engine_version = importlib_metadata.version("crml_engine")
    except Exception:
        engine_version = None

    currency_code = None
    currency_symbol = None
    model_name = None
    model_version = None
    description = None
    runtime_ms = None
    runs = None

    if result.metadata is not None:
        currency_code = result.metadata.currency_code
        currency_symbol = result.metadata.currency
        model_name = result.metadata.model_name
        model_version = result.metadata.model_version
        description = result.metadata.description
        runtime_ms = result.metadata.runtime_ms
        runs = result.metadata.runs

    currency_unit = None
    if currency_code is not None:
        currency_unit = CurrencyUnit(code=currency_code, symbol=currency_symbol)

    envelope = SimulationResultEnvelope(
        result=SimulationResult(
            success=result.success,
            errors=list(result.errors or []),
            warnings=list(result.warnings or []),
            engine=EngineInfo(name="crml_engine", version=engine_version),
            run=RunInfo(
                runs=runs,
                seed=seed,
                runtime_ms=runtime_ms,
                started_at=now_utc(),
            ),
            inputs=InputInfo(model_name=model_name, model_version=model_version, description=description),
            units=Units(
                currency=CurrencyUnit(code=currency_code or "USD", symbol=currency_symbol),
                horizon="annual",
            ),
        )
    )

    metrics = result.metrics
    if metrics is not None:
        envelope.result.results.measures.extend(
            [
                Measure(id="loss.eal", label="Expected Annual Loss", value=metrics.eal, unit=currency_unit),
                Measure(id="loss.min", label="Minimum Loss", value=metrics.min, unit=currency_unit),
                Measure(id="loss.max", label="Maximum Loss", value=metrics.max, unit=currency_unit),
                Measure(id="loss.median", label="Median Loss", value=metrics.median, unit=currency_unit),
                Measure(id="loss.std_dev", label="Standard Deviation", value=metrics.std_dev, unit=currency_unit),
            ]
        )

        envelope.result.results.measures.extend(
            [
                Measure(
                    id=LOSS_VAR_ID,
                    label=VALUE_AT_RISK_LABEL,
                    value=metrics.var_95,
                    unit=currency_unit,
                    parameters={"level": 0.95},
                ),
                Measure(
                    id=LOSS_VAR_ID,
                    label=VALUE_AT_RISK_LABEL,
                    value=metrics.var_99,
                    unit=currency_unit,
                    parameters={"level": 0.99},
                ),
                Measure(
                    id=LOSS_VAR_ID,
                    label=VALUE_AT_RISK_LABEL,
                    value=metrics.var_999,
                    unit=currency_unit,
                    parameters={"level": 0.999},
                ),
            ]
        )

    distribution = result.distribution
    if distribution is not None:
        if distribution.bins and distribution.frequencies:
            envelope.result.results.artifacts.append(
                HistogramArtifact(
                    id="loss.annual",
                    unit=currency_unit,
                    bin_edges=list(distribution.bins),
                    counts=list(distribution.frequencies),
                    binning={"method": "fixed_bins", "bin_count": max(len(distribution.bins) - 1, 0)},
                )
            )
        if distribution.raw_data:
            envelope.result.results.artifacts.append(
                SamplesArtifact(
                    id="loss.annual",
                    unit=currency_unit,
                    values=list(distribution.raw_data),
                    sample_count_total=runs,
                    sample_count_returned=len(distribution.raw_data),
                    sampling={"method": "first_n"},
                )
            )

    return envelope

def calibrate_lognormal_from_single_losses(
    single_losses: list,
    currency: Optional[str],
    base_currency: str,
    fx_config: FXConfig,
) -> tuple[float, float]:
    """
    Convenience wrapper for severity calibration.
    """
    return SeverityEngine.calibrate_lognormal_from_single_losses(
        single_losses, currency, base_currency, fx_config
    )

def run_simulation_cli(file_path: str, n_runs: int = 10000, output_format: str = 'text', fx_config_path: Optional[str] = None):
    """
    CLI wrapper for run_simulation that prints results.
    """
    # Load FX config
    fx_config = load_fx_config(fx_config_path)
    # Detect portfolio vs scenario
    try:
        import yaml
        with open(file_path, "r", encoding="utf-8") as f:
            root = yaml.safe_load(f)
    except Exception:
        root = None

    if isinstance(root, dict) and "crml_portfolio" in root:
        result = run_portfolio_simulation(file_path, source_kind="path", n_runs=n_runs, seed=None, fx_config=fx_config)
    else:
        result = run_simulation(file_path, n_runs, fx_config=fx_config)

    if output_format == 'json':
        # Use model_dump for pretty JSON output
        print(json.dumps(result.model_dump(), indent=2))
        return result.success

    # Text output
    print_result(result)
    return result.success
