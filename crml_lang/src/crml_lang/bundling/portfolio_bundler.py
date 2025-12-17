from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Literal, Mapping, Optional

from crml_lang.models.control_assessment_model import CRControlAssessmentSchema
from crml_lang.models.control_catalog_model import CRControlCatalogSchema
from crml_lang.models.crml_model import CRScenarioSchema
from crml_lang.models.portfolio_bundle import (
    BundleMessage,
    BundledScenario,
    CRPortfolioBundle,
    PortfolioBundlePayload,
)
from crml_lang.models.portfolio_model import CRPortfolioSchema


@dataclass(frozen=True)
class BundleReport:
    """Structured bundle output (errors/warnings + bundle when successful)."""

    ok: bool
    errors: list[BundleMessage]
    warnings: list[BundleMessage]
    bundle: Optional[CRPortfolioBundle] = None


def _load_yaml_file(path: str) -> dict[str, Any]:
    try:
        import yaml
    except Exception as e:
        raise ImportError("PyYAML is required: pip install pyyaml") from e

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError("YAML document must be a mapping/object at top-level")
    return data


def _resolve_path(base_dir: str | None, p: str) -> str:
    if base_dir and not os.path.isabs(p):
        return os.path.join(base_dir, p)
    return p


def bundle_portfolio(
    source: str | dict[str, Any] | CRPortfolioSchema,
    *,
    source_kind: Literal["path", "yaml", "data", "model"] = "path",
    scenarios: Mapping[str, CRScenarioSchema] | None = None,
    control_catalogs: list[CRControlCatalogSchema] | None = None,
    control_assessments: list[CRControlAssessmentSchema] | None = None,
) -> BundleReport:
    """Build an engine-agnostic CRPortfolioBundle from a portfolio input.

    Bundling is intentionally *not* planning:
    - it inlines referenced documents (scenarios and optionally control packs)
    - it does not compute planning-derived fields (e.g., cardinality, resolved control effects)

        Engines should be able to run a bundle without filesystem access.

        Notes
        -----
        - The first argument (`source`) is the *portfolio input*.
        - When `source_kind="path"|"yaml"|"data"`, referenced scenarios/packs are loaded from disk.
        - When `source_kind="model"`, you must provide referenced scenario documents via `scenarios`
            (keyed by scenario id or path), and optionally provide `control_catalogs` / `control_assessments`.
    """

    errors: list[BundleMessage] = []
    warnings: list[BundleMessage] = []

    base_dir: str | None = None
    data: dict[str, Any]

    if source_kind == "model":
        if not isinstance(source, CRPortfolioSchema):
            errors.append(
                BundleMessage(
                    level="error",
                    path="(input)",
                    message="source_kind='model' requires a CRPortfolio/CRPortfolioSchema instance",
                )
            )
            return BundleReport(ok=False, errors=errors, warnings=warnings, bundle=None)

        portfolio_doc = source
    elif source_kind == "path":
        assert isinstance(source, str)
        base_dir = os.path.dirname(os.path.abspath(source))
        try:
            data = _load_yaml_file(source)
        except Exception as e:
            errors.append(BundleMessage(level="error", path="(io)", message=str(e)))
            return BundleReport(ok=False, errors=errors, warnings=warnings, bundle=None)
    elif source_kind == "yaml":
        assert isinstance(source, str)
        try:
            import yaml
        except Exception as e:
            errors.append(BundleMessage(level="error", path="(io)", message=f"PyYAML is required: {e}"))
            return BundleReport(ok=False, errors=errors, warnings=warnings, bundle=None)

        loaded = yaml.safe_load(source)
        if not isinstance(loaded, dict):
            errors.append(BundleMessage(level="error", path="(root)", message="YAML must be a mapping"))
            return BundleReport(ok=False, errors=errors, warnings=warnings, bundle=None)
        data = loaded
    else:
        assert isinstance(source, dict)
        data = source

    if source_kind != "model":
        try:
            portfolio_doc = CRPortfolioSchema.model_validate(data)
        except Exception as e:
            errors.append(BundleMessage(level="error", path="(schema)", message=str(e)))
            return BundleReport(ok=False, errors=errors, warnings=warnings, bundle=None)

    # Inline packs referenced by the portfolio.
    control_catalogs_out: list[CRControlCatalogSchema] = list(control_catalogs or [])
    control_assessments_out: list[CRControlAssessmentSchema] = list(control_assessments or [])

    for idx, p in enumerate(portfolio_doc.portfolio.control_catalogs or []):
        if not isinstance(p, str) or not p:
            continue
        if source_kind == "model":
            warnings.append(
                BundleMessage(
                    level="warning",
                    path=f"portfolio.control_catalogs[{idx}]",
                    message=(
                        "Portfolio references a control catalog path, but bundling is in model-mode; "
                        "provide `control_catalogs` to inline pack content."
                    ),
                )
            )
            continue

        rp = _resolve_path(base_dir, p)
        try:
            control_catalogs_out.append(CRControlCatalogSchema.model_validate(_load_yaml_file(rp)))
        except Exception as e:
            warnings.append(
                BundleMessage(
                    level="warning",
                    path=f"portfolio.control_catalogs[{idx}]",
                    message=f"Failed to inline control catalog '{p}': {e}",
                )
            )

    for idx, p in enumerate(portfolio_doc.portfolio.control_assessments or []):
        if not isinstance(p, str) or not p:
            continue
        if source_kind == "model":
            warnings.append(
                BundleMessage(
                    level="warning",
                    path=f"portfolio.control_assessments[{idx}]",
                    message=(
                        "Portfolio references a control assessment path, but bundling is in model-mode; "
                        "provide `control_assessments` to inline pack content."
                    ),
                )
            )
            continue

        rp = _resolve_path(base_dir, p)
        try:
            control_assessments_out.append(CRControlAssessmentSchema.model_validate(_load_yaml_file(rp)))
        except Exception as e:
            warnings.append(
                BundleMessage(
                    level="warning",
                    path=f"portfolio.control_assessments[{idx}]",
                    message=f"Failed to inline control assessment '{p}': {e}",
                )
            )

    # Inline scenarios referenced by the portfolio.
    bundled_scenarios: list[BundledScenario] = []
    for idx, sref in enumerate(portfolio_doc.portfolio.scenarios):
        if source_kind == "model":
            if not scenarios:
                errors.append(
                    BundleMessage(
                        level="error",
                        path="(input)",
                        message="source_kind='model' requires `scenarios` to be provided",
                    )
                )
                return BundleReport(ok=False, errors=errors, warnings=warnings, bundle=None)

            scenario_doc = scenarios.get(sref.id) or scenarios.get(sref.path)
            if scenario_doc is None:
                errors.append(
                    BundleMessage(
                        level="error",
                        path=f"portfolio.scenarios[{idx}]",
                        message=(
                            f"Missing inlined scenario for reference id='{sref.id}', path='{sref.path}'. "
                            "Provide it via the `scenarios` mapping (key by id or path)."
                        ),
                    )
                )
                return BundleReport(ok=False, errors=errors, warnings=warnings, bundle=None)
        else:
            scenario_path = _resolve_path(base_dir, sref.path)
            try:
                scenario_doc = CRScenarioSchema.model_validate(_load_yaml_file(scenario_path))
            except Exception as e:
                errors.append(
                    BundleMessage(
                        level="error",
                        path=f"portfolio.scenarios[{idx}].path",
                        message=f"Failed to inline scenario '{sref.id}' from '{sref.path}': {e}",
                    )
                )
                return BundleReport(ok=False, errors=errors, warnings=warnings, bundle=None)

        bundled_scenarios.append(
            BundledScenario(
                id=sref.id,
                weight=sref.weight,
                source_path=sref.path,
                scenario=scenario_doc,
            )
        )

    payload = PortfolioBundlePayload(
        portfolio=portfolio_doc,
        scenarios=bundled_scenarios,
        control_catalogs=control_catalogs_out,
        control_assessments=control_assessments_out,
        warnings=warnings,
        metadata={
            "source_kind": source_kind,
            **({"source_path": os.path.abspath(source)} if source_kind == "path" and isinstance(source, str) else {}),
        },
    )

    bundle = CRPortfolioBundle(portfolio_bundle=payload)

    return BundleReport(ok=True, errors=[], warnings=warnings, bundle=bundle)
