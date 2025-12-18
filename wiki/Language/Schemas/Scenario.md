# Scenario Schema (`crml_scenario: "1.0"`)

This page documents the CRML **Scenario** document shape and how to use it.

- JSON Schema: `crml_lang/src/crml_lang/schemas/crml-scenario-schema.json`
- Pydantic model: `crml_lang/src/crml_lang/models/crml_model.py` (`CRScenarioSchema`)

---

## What a scenario is

A scenario is a **threat/risk model** (frequency + severity) that is portable and can be validated on its own.

A scenario is not directly executable by itself: execution happens in a **portfolio**, which provides exposure (assets/cardinalities) and binds scenarios to that exposure.

---

## Top-level structure

Required:

```yaml
crml_scenario: "1.0"
meta: { ... }
scenario: { ... }
```

Optional:

- `data:` (data sources and feature mapping for tools/engines)

---

## `data` (data sources and feature mapping)

The optional top-level `data` section is an **integration hook** for tools and engines.

It is designed for workflows where:

- a scenario is authored from threat intelligence as a baseline, and/or
- an organization wants to attach internal datasets (incident logs, ticket exports, loss accounting, telemetry) that can be used to **calibrate** or **validate** the scenario.

Important constraints:

- The CRML language validates the *shape* of `data`, but **does not standardize** the meaning of source `type` strings or feature names.
- Engines and UIs SHOULD treat `data` as **optional** and ignore unknown feature names.
- Do not put secrets (API keys, credentials) into CRML documents.

### `data.sources`

`data.sources` is an optional map of named sources. Each source has:

- `type`: engine/UI-defined identifier (e.g. `csv`, `parquet`, `snowflake`, `servicenow_export`, `siem_incidents`)
- `data_schema` (optional): a free-form mapping describing fields available in that source

Example:

```yaml
crml_scenario: "1.0"
meta:
  name: "Phishing -> account takeover"

data:
  sources:
    org_incidents_2022_2025:
      type: incident_log_csv
      data_schema:
        occurred_at: datetime
        loss_usd: money
        scenario_label: string
        business_unit: string

scenario:
  frequency:
    basis: per_organization_per_year
    model: poisson
    parameters: { lambda: 0.8 }
  severity:
    model: lognormal
    parameters: { median: 22000, sigma: 1.0, currency: USD }
```

Notes:

- `sources` deliberately does not include a portable `path`/`uri` field. Tools that need locations should handle that out-of-band (workspace context, UI uploads, or tool-specific config) to avoid embedding environment-specific paths into portable CRML.

### `data.feature_mapping`

`data.feature_mapping` is an optional mapping from **engine/tool feature names** to source columns/fields.

This supports scenarios where engines expect canonical feature names (e.g. `loss_amount`, `incident_timestamp`) but your dataset uses different column names.

Example:

```yaml
data:
  sources:
    org_incidents_2022_2025:
      type: incident_log_csv
      data_schema:
        occurred_at: datetime
        loss_usd: money
  feature_mapping:
    incident_timestamp: occurred_at
    incident_loss_amount: loss_usd
```

Recommended convention:

- Feature names should be stable within a tool/engine, and tools should document the feature names they understand.
- If multiple sources are used, tools can adopt a qualified convention (e.g. `source_name.field`) in their own feature naming.

---

## Minimal example

```yaml
crml_scenario: "1.0"
meta:
  name: "Phishing -> account takeover"
scenario:
  controls:
    - id: "org:iam.mfa"
      implementation_effectiveness: 0.85
  frequency:
    basis: per_organization_per_year
    model: poisson
    parameters:
      lambda: 0.8
  severity:
    model: lognormal
    parameters:
      mu: 10
      sigma: 1.2
      currency: USD
```

See also: `examples/scenarios/scenario-phishing.yaml`.

---

## `meta` (document metadata)

`meta` is shared across CRML document types.

Common fields:

- `name` (required): human-friendly name
- `version`, `description`, `author`, `organization` (optional)
- `tags`, `industries`, `company_sizes`, `regulatory_frameworks` (optional)
- `locale` (optional object): free-form locale/region metadata

---

## `scenario.frequency`

Structure:

```yaml
frequency:
  basis: per_organization_per_year | per_asset_unit_per_year
  model: <engine-defined>
  parameters: { ... }
```

Notes:

- `basis` controls exposure scaling in portfolios. See the normative section “Exposure scaling and frequency basis” in `wiki/Reference/CRML-Specification.md`.
- `model` is **engine-defined** (the language validates it as a string).
- `parameters` is model-specific. The language provides some standardized parameter names used by common models:
  - `lambda` (serialized as `lambda`, stored as `lambda_` internally)
  - `p`, `alpha_base`, `beta_base`, `r`, …

Number parsing:

- Some numeric parameters accept “numberish” inputs (e.g. strings like `"700 000"`). Tools should prefer plain numbers, but the language is permissive for human authing.

---

## `scenario.severity`

Structure:

```yaml
severity:
  model: <engine-defined>
  parameters: { ... }
  components: [ ... ]  # optional
```

Notes:

- `model` is **engine-defined**.
- `parameters` supports several common distribution parameter styles:
  - Human-friendly: `median` (often preferred)
  - Distribution-specific: `mu`, `sigma`, `shape`, `scale`, etc.
  - `currency` is optional and is primarily a hint to engines/tools
- `components` is an optional engine/tool-defined breakdown.

### Calibration-friendly inputs (`single_losses`)

The language supports an optional `single_losses` list under `scenario.severity.parameters`.

This enables a calibration workflow where you attach observed per-incident loss amounts and allow an engine/tool to infer severity distribution parameters.

Example (engine/tool may calibrate `mu`/`sigma` from losses):

```yaml
severity:
  model: lognormal
  parameters:
    currency: USD
    single_losses: [12000, 5000, 90000, 18000, 24000]
```

Notes:

- `single_losses` is intended to represent **per-incident** losses (one value per event), not annual totals.
- Tools SHOULD validate that it contains at least 2 positive values.
- In the reference engine shipped in this repository, `lognormal` severity supports auto-calibration from `single_losses`.

---

## `scenario.controls` (threat-centric relevant controls)

`scenario.controls` is optional and expresses the set of controls that can mitigate this scenario.

Each entry can be either:

- a canonical control id string (e.g. `org:iam.mfa`), or
- an object with scenario-scoped overrides:

```yaml
- id: "org:iam.mfa"
  implementation_effectiveness: 0.8  # optional
  notes: "..."                       # optional
```

Semantics (recommended):

- `implementation_effectiveness` is an optional threat-specific effectiveness factor for this control against this scenario.
  Organization-specific deployment/posture (coverage, inventory effectiveness) belongs in portfolio inventory and/or assessments.

Engines combine this threat-specific factor with portfolio/assessment posture during planning.

---

## Validation

CLI / tooling validation routes through `crml_lang`.

Python:

```python
from crml_lang import validate_scenario
report = validate_scenario("examples/scenarios/scenario-phishing.yaml", source_kind="path")
assert report.ok
```

For field-by-field constraints, consult `crml_lang/src/crml_lang/schemas/crml-scenario-schema.json`.

---

## How calibration works (recommended workflow)

CRML separates:

- the **model** (a scenario’s `frequency` + `severity`), from
- the **evidence** (incident observations) used to fit or adjust that model.

This keeps scenarios portable while still enabling organization-specific calibration.

### 1) Decide what your incident data represents

For a given scenario type (e.g. “phishing → account takeover”), your incident log typically provides one or both of:

- **frequency evidence**: incident counts over a time window (e.g. 7 events over 3 years)
- **severity evidence**: per-incident loss amounts (e.g. loss per event)

You may also have segmentation fields (business unit, asset class, region, control posture), which can be used by engine-specific fitting workflows.

### 2) Map incident data into the scenario

Use the optional `data` section to describe where the data comes from (`data.sources`) and how fields map to engine/tool feature names (`data.feature_mapping`).

This step does not change the executable model; it only makes the data discoverable for calibration tools.

### 3) Fit severity

If your dataset contains per-incident loss samples, a simple portable approach is to populate:

- `scenario.severity.parameters.single_losses`

Then an engine/tool can derive distribution parameters (for example, lognormal `mu`/`sigma`) from those samples.

Practical guidance:

- Use consistent currency and document it with `currency`.
- Prefer net loss values that match your reporting intent (e.g. include/exclude recovery, insurance) and note that in `meta.description`.

### 4) Fit frequency (and respect exposure basis)

Frequency calibration should set `scenario.frequency.parameters`.

For a Poisson model, a common baseline estimate is:

- `basis: per_organization_per_year` → set `lambda` to incidents per year for the organization.
- `basis: per_asset_unit_per_year` → set `lambda` to incidents per year per exposure unit, where the exposure units come from the portfolio asset cardinalities and bindings.

Because exposure scaling depends on portfolio bindings, frequency calibration often needs:

- the scenario document, and
- the portfolio (or at least the relevant exposure totals).

### 5) Write back a calibrated scenario

Calibration tools typically output a normal CRML scenario document by updating:

- `scenario.frequency.parameters` (e.g. `lambda`), and/or
- `scenario.severity.parameters` (either explicit parameters like `median`/`sigma` or calibration inputs like `single_losses`).

The resulting calibrated scenario can then be validated and simulated like any other CRML scenario.
