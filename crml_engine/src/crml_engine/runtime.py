import json
from typing import Union, Optional
from crml_lang.models.crml_model import load_crml_from_yaml_str, CRMLSchema
from .models.result_model import SimulationResult, print_result
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

def run_simulation(
    yaml_content: Union[str, dict], 
    n_runs: int = 10000, 
    seed: int = None, 
    fx_config: Optional[FXConfig] = None
) -> SimulationResult:
    """
    Backward compatible wrapper for run_monte_carlo.
    
    See crml_engine.simulation.engine.run_monte_carlo for documentation.
    """
    return run_monte_carlo(yaml_content, n_runs, seed, fx_config)


def run_simulation_envelope(
    yaml_content: Union[str, dict],
    n_runs: int = 10000,
    seed: int = None,
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
        success=result.success,
        errors=list(result.errors or []),
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

    metrics = result.metrics
    if metrics is not None:
        envelope.results.measures.extend(
            [
                Measure(id="loss.eal", label="Expected Annual Loss", value=metrics.eal, unit=currency_unit),
                Measure(id="loss.min", label="Minimum Loss", value=metrics.min, unit=currency_unit),
                Measure(id="loss.max", label="Maximum Loss", value=metrics.max, unit=currency_unit),
                Measure(id="loss.median", label="Median Loss", value=metrics.median, unit=currency_unit),
                Measure(id="loss.std_dev", label="Standard Deviation", value=metrics.std_dev, unit=currency_unit),
            ]
        )

        envelope.results.measures.extend(
            [
                Measure(
                    id="loss.var",
                    label="Value at Risk",
                    value=metrics.var_95,
                    unit=currency_unit,
                    parameters={"level": 0.95},
                ),
                Measure(
                    id="loss.var",
                    label="Value at Risk",
                    value=metrics.var_99,
                    unit=currency_unit,
                    parameters={"level": 0.99},
                ),
                Measure(
                    id="loss.var",
                    label="Value at Risk",
                    value=metrics.var_999,
                    unit=currency_unit,
                    parameters={"level": 0.999},
                ),
            ]
        )

    distribution = result.distribution
    if distribution is not None:
        if distribution.bins and distribution.frequencies:
            envelope.results.artifacts.append(
                HistogramArtifact(
                    id="loss.annual",
                    unit=currency_unit,
                    bin_edges=list(distribution.bins),
                    counts=list(distribution.frequencies),
                    binning={"method": "fixed_bins", "bin_count": max(len(distribution.bins) - 1, 0)},
                )
            )
        if distribution.raw_data:
            envelope.results.artifacts.append(
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
    Backward compatible wrapper for severity calibration.
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
    result = run_simulation(file_path, n_runs, fx_config=fx_config)

    if output_format == 'json':
        # Use model_dump for pretty JSON output
        print(json.dumps(result.model_dump(), indent=2))
        return result.success

    # Text output
    print_result(result)
    return result.success
