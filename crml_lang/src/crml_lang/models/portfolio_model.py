from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, ConfigDict, field_validator

from .crml_model import Meta
from .control_ref import ControlId
from .coverage_model import Coverage
from .numberish import parse_intish


class CriticalityIndex(BaseModel):
    type: Optional[str] = None
    inputs: Optional[Dict[str, str]] = None
    weights: Optional[Dict[str, float]] = None
    transform: Optional[str] = None


class Asset(BaseModel):
    name: str
    cardinality: int = Field(..., ge=1)
    criticality_index: Optional[CriticalityIndex] = None
    tags: Optional[List[str]] = None

    @field_validator("cardinality", mode="before")
    @classmethod
    def _parse_cardinality(cls, v):
        return parse_intish(v)


PortfolioMethod = Literal["sum", "mixture", "choose_one", "max"]


class PortfolioConstraints(BaseModel):
    require_paths_exist: bool = False
    validate_scenarios: bool = True


class PortfolioSemantics(BaseModel):
    method: PortfolioMethod
    constraints: PortfolioConstraints = Field(default_factory=PortfolioConstraints)


class ScenarioBinding(BaseModel):
    # Minimal binding surface: explicit list of portfolio asset names.
    # If a scenario is per-asset-unit, this defines its exposure set.
    applies_to_assets: Optional[List[str]] = None


class ScenarioRef(BaseModel):
    id: str
    path: str
    weight: Optional[float] = None
    binding: ScenarioBinding = Field(default_factory=ScenarioBinding)
    tags: Optional[List[str]] = None


class CorrelationRelationship(BaseModel):
    type: Literal["correlation"]
    between: List[str] = Field(..., min_length=2, max_length=2)
    value: float = Field(..., ge=-1.0, le=1.0)
    method: Optional[Literal["gaussian_copula", "rank_correlation"]] = None


class ConditionalRelationship(BaseModel):
    type: Literal["conditional"]
    given: str
    then: str
    probability: float = Field(..., ge=0.0, le=1.0)


Relationship = CorrelationRelationship | ConditionalRelationship


class PortfolioControl(BaseModel):
    # Canonical unique control id, e.g. "cis.v8.2.3" or "iso27001:2022:A.5.1".
    id: ControlId
    implementation_effectiveness: Optional[float] = Field(None, ge=0.0, le=1.0)
    coverage: Optional[Coverage] = None
    # Reliability/uptime of the control as a probability of being effective in a given period.
    # This is a portfolio/inventory attribute; runtimes may treat it as a stochastic state.
    reliability: Optional[float] = Field(None, ge=0.0, le=1.0)

    # Effect surface for this control. Default is frequency-first.
    affects: Optional[Literal["frequency", "severity", "both"]] = "frequency"
    notes: Optional[str] = None


class DependencyCopula(BaseModel):
    """Engine-independent copula dependency specification.

    The copula operates over `targets` in the given order.
    This version is intentionally minimal and supports Gaussian copulas.

    Targets are language-level references. Currently supported targets:
    - control:<id>:state  (a control availability/performance state)
    """

    type: Literal["gaussian"] = "gaussian"

    # Ordered list of target references; length defines the copula dimension.
    targets: List[str] = Field(..., min_length=1)

    # Correlation specification: either Toeplitz (rho) or an explicit matrix.
    structure: Optional[Literal["toeplitz"]] = None
    rho: Optional[float] = Field(None, ge=-1.0, le=1.0)
    matrix: Optional[List[List[float]]] = None


class PortfolioDependency(BaseModel):
    copula: Optional[DependencyCopula] = None


class Portfolio(BaseModel):
    assets: List[Asset] = Field(default_factory=list)
    controls: Optional[List[PortfolioControl]] = None

    # Optional pack references (paths). These allow portfolios to point at
    # portable catalogs/assessments without duplicating their contents.
    control_catalogs: Optional[List[str]] = None
    control_assessments: Optional[List[str]] = None

    scenarios: List[ScenarioRef]
    semantics: PortfolioSemantics
    relationships: Optional[List[Relationship]] = None
    dependency: Optional[PortfolioDependency] = None
    context: Dict[str, Any] = Field(default_factory=dict)


class CRPortfolioSchema(BaseModel):
    crml_portfolio: Literal["1.0"]
    meta: Meta
    portfolio: Portfolio

    model_config: ConfigDict = ConfigDict(populate_by_name=True)
