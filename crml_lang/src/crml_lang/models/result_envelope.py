from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class CurrencyUnit(BaseModel):
    kind: Literal["currency"] = "currency"
    code: str
    symbol: Optional[str] = None


class Units(BaseModel):
    currency: CurrencyUnit
    horizon: Optional[Literal["annual", "monthly", "daily", "event", "unknown"]] = "unknown"


class EngineInfo(BaseModel):
    name: str
    version: Optional[str] = None


class RunInfo(BaseModel):
    runs: Optional[int] = None
    seed: Optional[int] = None
    runtime_ms: Optional[float] = None
    started_at: Optional[datetime] = None


class InputInfo(BaseModel):
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    description: Optional[str] = None


class Measure(BaseModel):
    id: str
    value: Optional[float] = None
    unit: Optional[CurrencyUnit] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    label: Optional[str] = None


class HistogramArtifact(BaseModel):
    kind: Literal["histogram"] = "histogram"
    id: str
    unit: Optional[CurrencyUnit] = None
    bin_edges: List[float] = Field(default_factory=list)
    counts: List[int] = Field(default_factory=list)
    binning: Dict[str, Any] = Field(default_factory=dict)


class SamplesArtifact(BaseModel):
    kind: Literal["samples"] = "samples"
    id: str
    unit: Optional[CurrencyUnit] = None
    values: List[float] = Field(default_factory=list)
    sample_count_total: Optional[int] = None
    sample_count_returned: Optional[int] = None
    sampling: Dict[str, Any] = Field(default_factory=dict)


Artifact = HistogramArtifact | SamplesArtifact


class ResultPayload(BaseModel):
    measures: List[Measure] = Field(default_factory=list)
    artifacts: List[Artifact] = Field(default_factory=list)


class SimulationResultEnvelope(BaseModel):
    """Engine-agnostic, visualization-agnostic simulation result envelope.

    This model lives in `crml_lang` so engines and UIs can share a stable contract.
    """

    schema_id: Literal["crml.simulation.result"] = "crml.simulation.result"
    schema_version: str = "1.0.0"

    success: bool = False
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    engine: EngineInfo
    run: RunInfo = Field(default_factory=RunInfo)
    inputs: InputInfo = Field(default_factory=InputInfo)
    units: Optional[Units] = None

    results: ResultPayload = Field(default_factory=ResultPayload)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
