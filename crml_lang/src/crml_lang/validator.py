"""CRML JSON Schema validator.

This module provides programmatic, structured validation APIs for CRML documents.

Design goals:
- Library-first API: functions return structured results and do not print.
- Flexible inputs: validate from a file path, a YAML string, or an in-memory dict.
- Spec contract: JSON Schema (Draft 2020-12) is the primary validation surface.
- Optional runtime check: opt-in Pydantic validation can be enabled to ensure the
  reference runtime model can parse the document.

Usage examples
--------------

Validate a file path (typical CLI/library usage)::

    from crml_lang import validate

    report = validate("model.yaml", source_kind="path")
    if not report.ok:
        # Structured access
        for err in report.errors:
            print(err.path, err.message)

Validate YAML content from a string::

    from crml_lang import validate

    yaml_text = '''
    crml: "1.1"
    meta: {name: "example"}
    model: {assets: [{name: "Servers", cardinality: 10}], frequency: {model: poisson, parameters: {lambda: 0.5}}, severity: {model: lognormal, parameters: {mu: 10, sigma: 1}}}
    '''
    report = validate(yaml_text, source_kind="yaml")
    print(report.ok)

Validate already-parsed data (dict)::

    from crml_lang import validate

    data = {"crml": "1.1", "meta": {"name": "example"}, "model": {"assets": [{"name": "Servers", "cardinality": 10}], "frequency": {"model": "poisson", "parameters": {"lambda": 0.5}}, "severity": {"model": "lognormal", "parameters": {"mu": 10, "sigma": 1}}}}
    report = validate(data, source_kind="data")

Enable strict runtime-model validation (optional)::

    report = validate("model.yaml", source_kind="path", strict_model=True)
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any, Literal, Optional

from jsonschema import Draft202012Validator


SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema", "crml-schema.json")


@dataclass(frozen=True)
class ValidationMessage:
    """A single validation message (error or warning)."""

    level: Literal["error", "warning"]
    message: str
    path: str = "(root)"
    source: Literal["schema", "semantic", "pydantic", "io"] = "schema"
    validator: Optional[str] = None


@dataclass(frozen=True)
class ValidationReport:
    """Structured validation output.

    Attributes:
        ok:
            True if schema validation passed (no errors). Warnings do not affect
            `ok`.
        errors:
            List of schema/model/IO errors.
        warnings:
            List of semantic warnings.
    """

    ok: bool
    errors: list[ValidationMessage]
    warnings: list[ValidationMessage]

    def render_text(self, *, source_label: Optional[str] = None) -> str:
        """Render a human-friendly validation summary (used by the CLI)."""

        label = source_label or "(input)"
        lines: list[str] = []

        if self.ok:
            lines.append(f"[OK] {label} is a valid CRML document.")
            for w in self.warnings:
                lines.append(f"[WARNING] {w.message}")
            return "\n".join(lines)

        lines.append(f"[ERROR] {label} failed CRML validation with {len(self.errors)} error(s):")
        for i, e in enumerate(self.errors, 1):
            lines.append(f"  {i}. [{e.path}] {e.message}")
        for w in self.warnings:
            lines.append(f"[WARNING] {w.message}")
        return "\n".join(lines)


def _load_schema() -> dict[str, Any]:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _looks_like_yaml_text(s: str) -> bool:
    # Heuristic: YAML documents almost always contain either newlines or
    # key separators. Callers can override via `source_kind`.
    return "\n" in s or ":" in s


def _load_input(
    source: str | dict[str, Any],
    *,
    source_kind: Literal["path", "yaml", "data"] | None,
) -> tuple[Optional[dict[str, Any]], list[ValidationMessage]]:
    errors: list[ValidationMessage] = []

    if source_kind == "data" or isinstance(source, dict):
        if not isinstance(source, dict):
            return None, [ValidationMessage(level="error", source="io", path="(root)", message="Expected a dict for source_kind='data'.")]
        return source, errors

    if not isinstance(source, str):
        return None, [ValidationMessage(level="error", source="io", path="(root)", message=f"Unsupported source type: {type(source).__name__}")]

    if source_kind == "path" or (source_kind is None and (os.path.exists(source) or not _looks_like_yaml_text(source))):
        if not os.path.exists(source):
            return None, [ValidationMessage(level="error", source="io", path="(root)", message=f"File not found: {source}")]
        try:
            with open(source, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            return None, [ValidationMessage(level="error", source="io", path="(root)", message=f"Failed to read file {source}: {e}")]
    else:
        text = source

    try:
        import yaml
    except Exception as e:
        return None, [ValidationMessage(level="error", source="io", path="(root)", message="PyYAML is required to parse YAML: pip install pyyaml")]

    try:
        data = yaml.safe_load(text)
    except Exception as e:
        return None, [ValidationMessage(level="error", source="io", path="(root)", message=f"Failed to parse YAML: {e}")]

    if not isinstance(data, dict):
        return None, [ValidationMessage(level="error", source="io", path="(root)", message="CRML document must parse to a YAML mapping (object/dict) at the root.")]

    return data, errors


def _jsonschema_path(error) -> str:
    try:
        if error.path:
            return " -> ".join(map(str, error.path))
    except Exception:
        pass
    return "(root)"


def _format_jsonschema_error(error) -> str:
    # Provide human-friendly error messages (keeps parity with earlier CLI output).
    if getattr(error, "validator", None) == "const":
        return f"Expected '{error.validator_value}', got '{error.instance}'"

    if getattr(error, "validator", None) == "oneOf":
        instance = getattr(error, "instance", None)
        if isinstance(instance, dict):
            if "mu" in instance and "median" in instance:
                return "Cannot use both 'median' and 'mu'. Choose one (median is recommended)."
            if "single_losses" in instance and any(k in instance for k in ("median", "mu", "sigma")):
                return "When using 'single_losses', do not also set 'median', 'mu', or 'sigma'."
            if "single_losses" in instance:
                return "'single_losses' must be an array with at least 2 positive values. It replaces median/mu/sigma by auto-calibration."
        return error.message

    if getattr(error, "validator", None) == "required":
        missing = None
        try:
            missing = error.validator_value[0]
        except Exception:
            pass
        if missing:
            return f"Missing required property: '{missing}'"
        return error.message

    if getattr(error, "validator", None) == "enum":
        try:
            values = ", ".join(map(str, error.validator_value))
            return f"Value must be one of: {values}"
        except Exception:
            return error.message

    return error.message


def _semantic_warnings(data: dict[str, Any]) -> list[ValidationMessage]:
    warnings: list[ValidationMessage] = []

    # Warn if using old CRML version
    if data.get("crml") != "1.1":
        warnings.append(
            ValidationMessage(
                level="warning",
                source="semantic",
                path="crml",
                message=f"CRML version '{data.get('crml')}' is not current. Consider upgrading to '1.1'.",
            )
        )

    meta = data.get("meta", {}) if isinstance(data.get("meta"), dict) else {}
    for key in ["version", "description", "author", "industries"]:
        if key not in meta or meta.get(key) in ([], ""):
            warnings.append(
                ValidationMessage(
                    level="warning",
                    source="semantic",
                    path=f"meta -> {key}",
                    message=f"'meta.{key}' is missing or empty. It is not required, but strongly recommended for documentation and context.",
                )
            )

    # regions is inside meta.locale.regions
    locale = meta.get("locale", {}) if isinstance(meta.get("locale"), dict) else {}
    if "regions" not in locale or locale.get("regions") in ([], ""):
        warnings.append(
            ValidationMessage(
                level="warning",
                source="semantic",
                path="meta -> locale -> regions",
                message="'meta.locale.regions' is missing or empty. It is not required, but strongly recommended for documentation and context.",
            )
        )

    # Warn if mixture weights don't sum to 1
    model = data.get("model", {}) if isinstance(data.get("model"), dict) else {}
    severity = model.get("severity", {}) if isinstance(model.get("severity"), dict) else {}
    if severity.get("model") == "mixture" and isinstance(severity.get("components"), list):
        total_weight = 0.0
        for comp in severity.get("components", []):
            if not isinstance(comp, dict) or not comp:
                continue
            dist_key = list(comp.keys())[0]
            if isinstance(comp.get(dist_key), dict):
                total_weight += float(comp[dist_key].get("weight", 0) or 0)
        if abs(total_weight - 1.0) > 0.001:
            warnings.append(
                ValidationMessage(
                    level="warning",
                    source="semantic",
                    path="model -> severity -> components",
                    message=f"Mixture weights sum to {total_weight:.3f}, should sum to 1.0",
                )
            )

    # Warn if severity node appears to contain monetary values but no currency property
    params = severity.get("parameters", {}) if isinstance(severity.get("parameters"), dict) else {}
    if any(k in params for k in ("median", "mu", "mean", "single_losses")) and "currency" not in params:
        warnings.append(
            ValidationMessage(
                level="warning",
                source="semantic",
                path="model -> severity -> parameters",
                message="Severity node has monetary values but no 'currency' property. Specify the currency to avoid implicit assumptions.",
            )
        )

    # Warn if no output metrics specified
    output = data.get("output", {}) if isinstance(data.get("output"), dict) else {}
    if not output.get("metrics"):
        warnings.append(
            ValidationMessage(
                level="warning",
                source="semantic",
                path="output -> metrics",
                message="No output metrics specified. Consider adding 'EAL', 'VaR_95', etc.",
            )
        )

    return warnings


def validate(
    source: str | dict[str, Any],
    *,
    source_kind: Literal["path", "yaml", "data"] | None = None,
    strict_model: bool = False,
) -> ValidationReport:
    """Validate a CRML document.

    Args:
        source:
            One of:
            - file path to a CRML YAML file
            - YAML content as a string
            - in-memory dict (already parsed)
        source_kind:
            Optional disambiguation for string inputs:
            - "path": treat `source` as a file path
            - "yaml": treat `source` as YAML text
            - "data": treat `source` as a dict
        strict_model:
            If True, additionally validates the document against the reference
            Pydantic runtime model (useful to catch spec/runtime drift).

    Returns:
        ValidationReport with `ok`, `errors`, and `warnings`.

    Examples:
        Validate a path::

            report = validate("model.yaml", source_kind="path")
            assert report.ok

        Validate YAML string::

            report = validate("crml: '1.1'\nmeta: {name: x}\nmodel: {...}", source_kind="yaml")

        Validate a dict::

            report = validate({"crml": "1.1", "meta": {"name": "x"}, "model": {...}}, source_kind="data")
    """

    data, io_errors = _load_input(source, source_kind=source_kind)
    if io_errors:
        return ValidationReport(ok=False, errors=io_errors, warnings=[])
    assert data is not None

    try:
        schema = _load_schema()
    except FileNotFoundError:
        return ValidationReport(
            ok=False,
            errors=[ValidationMessage(level="error", source="io", path="(root)", message=f"Schema file not found at {SCHEMA_PATH}")],
            warnings=[],
        )

    validator = Draft202012Validator(schema)
    errors: list[ValidationMessage] = []
    for err in validator.iter_errors(data):
        errors.append(
            ValidationMessage(
                level="error",
                source="schema",
                path=_jsonschema_path(err),
                message=_format_jsonschema_error(err),
                validator=getattr(err, "validator", None),
            )
        )

    warnings = _semantic_warnings(data) if not errors else []

    if strict_model and not errors:
        try:
            from .models.crml_model import CRMLSchema

            CRMLSchema.model_validate(data)
        except Exception as e:
            # Prefer detailed Pydantic errors if available.
            try:
                pydantic_errors = e.errors()  # type: ignore[attr-defined]
            except Exception:
                pydantic_errors = None

            if isinstance(pydantic_errors, list):
                for pe in pydantic_errors:
                    loc = pe.get("loc", ())
                    path = " -> ".join(map(str, loc)) if loc else "(root)"
                    errors.append(
                        ValidationMessage(
                            level="error",
                            source="pydantic",
                            path=path,
                            message=str(pe.get("msg", "Pydantic validation failed")),
                            validator="pydantic",
                        )
                    )
            else:
                errors.append(
                    ValidationMessage(
                        level="error",
                        source="pydantic",
                        path="(root)",
                        message=f"Pydantic validation failed: {e}",
                        validator="pydantic",
                    )
                )

    return ValidationReport(ok=(len(errors) == 0), errors=errors, warnings=warnings)
