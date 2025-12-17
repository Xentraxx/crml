"""
Core Monte Carlo simulation engine for CRML.
"""
import time
import numpy as np
from typing import Union, Optional, Dict, List

from crml_lang.models.crml_model import load_crml_from_yaml_str, CRMLSchema
from ..models.result_model import SimulationResult, Metrics, Distribution, Metadata
from ..models.fx_model import FXConfig, convert_currency, get_currency_symbol, normalize_fx_config
from ..models.constants import DEFAULT_FX_RATES
from ..controls import apply_control_effectiveness

from .frequency import FrequencyEngine
from .severity import SeverityEngine

def run_monte_carlo(
    yaml_content: Union[str, dict],
    n_runs: int = 10000,
    seed: int = None,
    fx_config: Optional[FXConfig] = None,
    cardinality: int = 1,
    frequency_rate_multiplier: Optional[object] = None,
    severity_loss_multiplier: Optional[object] = None,
    raw_data_limit: Optional[int] = 1000,
) -> SimulationResult:
    """
    Orchestrates the Monte Carlo simulation.
    """
    start_time = time.time()
    
    # 1. Configuration Setup
    fx_config = normalize_fx_config(fx_config)
    output_symbol = get_currency_symbol(fx_config.output_currency)

    if seed is not None:
        np.random.seed(seed)
        
    result = SimulationResult(
        success=False,
        metrics=Metrics(),
        distribution=Distribution(),
        metadata=Metadata(
            runs=n_runs, seed=seed, 
            currency=output_symbol, 
            currency_code=fx_config.output_currency
        ),
        errors=[]
    )

    # 2. Parsing & Validation
    try:
        if isinstance(yaml_content, str):
            import os
            if os.path.isfile(yaml_content):
                with open(yaml_content, 'r', encoding='utf-8') as f:
                    yaml_str = f.read()
                crml_obj = load_crml_from_yaml_str(yaml_str)
            else:
                crml_obj = load_crml_from_yaml_str(yaml_content)
        elif isinstance(yaml_content, dict):
            crml_obj = CRMLSchema.model_validate(yaml_content)
        else:
            result.errors.append("Invalid input type")
            return result
    except Exception as e:
        result.errors.append(f"Parsing error: {str(e)}")
        return result

    scenario = crml_obj.scenario

    # Populating Metadata
    meta = crml_obj.meta
    result.metadata.model_name = meta.name
    result.metadata.model_version = meta.version or 'N/A'
    result.metadata.description = meta.description or ''

    # 3. Execution Setup
    # Single CRML document == one scenario.
    # Portfolio / multi-file execution (if desired) lives above this function.
    
    freq = scenario.frequency
    sev = scenario.severity
    
    # Cardinality is a portfolio/runtime concern (e.g. per-asset-unit basis).
    # Scenario documents do not contain assets/exposure, so the default remains 1.
    try:
        cardinality = int(cardinality) if cardinality is not None else 1
    except Exception:
        cardinality = 1
    if cardinality < 1:
        cardinality = 1

    # Optional per-run multipliers (portfolio/runtime concern)
    freq_mult = None
    if frequency_rate_multiplier is not None:
        if isinstance(frequency_rate_multiplier, (int, float, np.floating)):
            freq_mult = float(frequency_rate_multiplier)
        else:
            arr = np.asarray(frequency_rate_multiplier, dtype=np.float64)
            if arr.shape != (n_runs,):
                result.errors.append("frequency_rate_multiplier must be a scalar or shape (n_runs,)")
                return result
            freq_mult = arr

    sev_mult = None
    if severity_loss_multiplier is not None:
        if isinstance(severity_loss_multiplier, (int, float, np.floating)):
            sev_mult = float(severity_loss_multiplier)
        else:
            arr = np.asarray(severity_loss_multiplier, dtype=np.float64)
            if arr.shape != (n_runs,):
                result.errors.append("severity_loss_multiplier must be a scalar or shape (n_runs,)")
                return result
            sev_mult = arr
        
    # Controls Application (Heuristic/Multiplicative)
    freq_model = freq.model if freq else ''
    lambda_val = None
    if freq_model == 'poisson' and freq.parameters:
        lambda_val = float(freq.parameters.lambda_) if freq.parameters.lambda_ is not None else 0.0
        
    # Scenario-first controls are references, not executable effectiveness configs.
    # Control application is handled at portfolio/runtime level.

    # 4. Asset-Model Extraction
    # We identify per-asset simulation units as (FrequencyModel, SeverityModel) pairs.
    # Grouping logic:
    # - If freq.models and sev.models exist, match by asset name.
    # - Fall back to global models if asset-specific ones not found.
    # - If no models list, use single global model logic.

    scenarios = [
        {
            'name': 'global',
            'freq_model': freq.model,
            'freq_params': freq.parameters,
            'sev_model': sev.model,
            'sev_params': sev.parameters,
            'sev_comps': sev.components,
        }
    ]

    # 5. Simulation Loop (Aggregated)
    try:
        # Initialize total annual losses accumulator
        total_annual_losses = np.zeros(n_runs)

        supported_frequency_models = {"poisson", "gamma", "hierarchical_gamma_poisson"}
        supported_severity_models = {"lognormal", "gamma", "mixture"}
        
        for sc in scenarios:
            f_model = sc['freq_model']
            asset_name = sc['name']

            if not f_model or f_model not in supported_frequency_models:
                result.errors.append(f"Unsupported frequency model: {f_model}")
                return result

            s_model = sc.get('sev_model')
            if not s_model or s_model not in supported_severity_models:
                result.errors.append(f"Unsupported severity model: {s_model}")
                return result
            
            # ... (Control logic omitted for brevity) ...

            uniforms = None

            # Using specific parameters for this scenario
            if f_model == 'poisson' and sc['freq_params']:
                 lambda_val = float(sc['freq_params'].lambda_) if sc['freq_params'].lambda_ is not None else 0.0
            
            # A. Frequency Generation
            counts = FrequencyEngine.generate_frequency(
                freq_model=f_model,
                params=sc['freq_params'],
                n_runs=n_runs,
                cardinality=cardinality,
                seed=seed,
                uniforms=uniforms,
                rate_multiplier=freq_mult,
            )
            
            scenario_losses = np.zeros(n_runs)
            total_events = int(np.sum(counts))
            
            if total_events > 0:
                # B. Severity Generation
                severities = SeverityEngine.generate_severity(
                    sev_model=sc['sev_model'],
                    params=sc['sev_params'],
                    components=sc['sev_comps'],
                    total_events=total_events,
                    fx_config=fx_config
                )
                
                # Check for length mismatch
                if len(severities) != total_events:
                     severities = np.zeros(total_events)

                # C. Aggregation for this scenario
                current_idx = 0
                temp_losses = []
                for c in counts:
                    if c > 0:
                       loss = np.sum(severities[current_idx : current_idx + c])
                       temp_losses.append(loss)
                       current_idx += c
                    else:
                       temp_losses.append(0.0)
                scenario_losses = np.array(temp_losses)
            
            # Add to total
            if sev_mult is not None:
                scenario_losses = scenario_losses * sev_mult
            total_annual_losses += scenario_losses

        annual_losses = total_annual_losses

        # 5. Reporting Currency Conversion
        annual_losses = np.asarray(total_annual_losses, dtype=np.float64)
        
        if fx_config.base_currency != fx_config.output_currency:
            factor = convert_currency(1.0, fx_config.base_currency, fx_config.output_currency, fx_config)
            annual_losses = annual_losses * factor

        # 6. Metrics Calculation
        eal = float(np.mean(annual_losses))
        result.metrics = Metrics(
            eal=eal,
            var_95=float(np.percentile(annual_losses, 95)),
            var_99=float(np.percentile(annual_losses, 99)),
            var_999=float(np.percentile(annual_losses, 99.9)),
            min=float(np.min(annual_losses)),
            max=float(np.max(annual_losses)),
            median=float(np.median(annual_losses)),
            std_dev=float(np.std(annual_losses))
        )

        hist, bin_edges = np.histogram(annual_losses, bins=50)
        if raw_data_limit is None:
            raw = annual_losses.tolist()
        else:
            raw = annual_losses.tolist()[: int(raw_data_limit)]

        result.distribution = Distribution(
            bins=bin_edges.tolist(),
            frequencies=hist.tolist(),
            raw_data=raw
        )

        result.metadata.runtime_ms = (time.time() - start_time) * 1000
        result.success = True

    except Exception as e:
        result.errors.append(f"Simulation execution error: {str(e)}")
        # Raise for debugging? No, capture in result object for API consistency.
        
    return result
