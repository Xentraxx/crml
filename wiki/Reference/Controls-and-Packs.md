# Controls & Packs (Reference)

This page defines the **normative** semantics for controls in CRML 1.2+ and how control-related “packs” interact.

> Note: The CRML 1.1 spec pages describe an older, runtime-centric “layers” model. This page documents the newer packs-based approach.

---

## Concepts

### Control ID

A control is identified by a stable, portable **Control ID**.

- Format: `namespace:key`
- Example: `cis:4.1`, `iso27001:a.8.12`, `org:iam.mfa`
- Purpose: a short identifier that can be referenced from scenarios, portfolios, catalogs, and assessments.

Control IDs are **identifiers only**. Avoid embedding copyrighted control text inside CRML artifacts.

### Control Catalog Pack

A **Control Catalog Pack** declares the universe of control IDs (and optional metadata) that a team agrees to use.

- Document header: `crml_control_catalog: "1.0"`
- Core content: `catalog.controls[]` with at least `id`

Catalogs are intended for:

- Validation (“is this ID known?”)
- Tooling/UI mapping (“show title/url/tags for an ID”)

Catalogs do **not** provide organization-specific posture values.

### Control Assessment Pack

A **Control Assessment Pack** records organization posture for a set of controls.

- Document header: `crml_control_assessment: "1.0"`
- Core content: `assessments[]`

Each assessment is scoped to a control ID and includes:

- `implementation_effectiveness`: $[0,1]$
- Optional `coverage` object

Assessments are the preferred place to store org-wide posture.

### Portfolio Control Inventory

A **Portfolio** is the executable context for scenarios. The portfolio contains a control inventory that can be used for simulation.

- Document header: `crml_portfolio: "1.0"`
- Control inventory: `controls[]`

A portfolio’s `controls[]` list is also used for **cross-document validation**: scenarios included in the portfolio may only reference controls that exist in the portfolio control inventory.

### Scenario Control References

A **Scenario** may reference controls in a lightweight way, so scenarios remain portable.

- Document header: `crml_scenario: "1.2"`
- Controls live under `scenario.controls[]`

A scenario control reference can be:

- A string Control ID: `"org:iam.mfa"`
- An object: `{ id, implementation_effectiveness?, coverage?, notes? }`

The object form is for scenario-specific assumptions.

---

## Coverage

Coverage is represented as a structured object:

```yaml
coverage:
  value: 0.8
  basis: asset_fraction
  notes: "Covers most endpoints, not OT"
```

Normative rules:

- `coverage.value` MUST be in $[0,1]$.
- `coverage.basis` MUST be an allowed enum value.
- Coverage is interpreted as a **multiplier-like** concept (how broadly the control applies), distinct from `implementation_effectiveness` (how well the control works where applied).

---

## Effective Control Parameters (Merge / Override)

When multiple sources provide parameters for the same control ID, tools MUST derive “effective” parameters using this precedence order:

1. Scenario-specific control object (`scenario.controls[]` object fields)
2. Portfolio control inventory (`portfolio.controls[]` entry)
3. Control Assessment Pack (`assessments[]` entry)
4. Control Catalog Pack (no numeric values; metadata only)

Normative details:

- If a scenario reference is a string ID (no object fields), it does not override anything.
- If a scenario reference is an object, any provided fields override lower-precedence sources field-by-field.
- If a control ID is referenced by a scenario and **no portfolio control inventory entry exists**, portfolio validation MUST fail.

> Implementation note: today the validator enforces the “scenario controls must exist in portfolio.controls” rule when validating a portfolio that loads scenarios. Portfolio-to-pack auto-loading/merging may be implemented by tooling/runtime.

### Example: same control appears in multiple sources

Assume control `org:iam.mfa` is present in an assessment pack and referenced by a scenario.

Assessment pack (org-wide posture):

```yaml
crml_control_assessment: "1.0"
meta: {name: "Org assessment"}
assessment:
  framework: "Org"
  assessments:
    - id: "org:iam.mfa"
      implementation_effectiveness: 0.7
      coverage: {value: 0.9, basis: employees}
```

Portfolio control inventory (optional executable overrides):

```yaml
crml_portfolio: "1.0"
meta: {name: "Org portfolio"}
portfolio:
  semantics: {method: sum}
  controls:
    - id: "org:iam.mfa"
      implementation_effectiveness: 0.5
```

Scenario-specific assumption (highest precedence):

```yaml
crml_scenario: "1.2"
meta: {name: "Phishing"}
scenario:
  controls:
    - id: "org:iam.mfa"
      implementation_effectiveness: 0.3
      notes: "Assume limited MFA enforcement for this scenario"
```

Effective value (for `implementation_effectiveness`) is `0.3` because scenario overrides portfolio and assessment.

### Example: field-by-field override

If the scenario only overrides coverage, the assessment’s implementation effectiveness remains in effect.

```yaml
scenario:
  controls:
    - id: "org:iam.mfa"
      coverage: {value: 0.6, basis: employees}
```

Effective `implementation_effectiveness` comes from portfolio (if present) else assessment; effective `coverage` comes from the scenario.

---

## Validation Rules

### Schema vs semantic validation

- JSON Schema validates document structure.
- Semantic validation enforces cross-field and cross-document rules.

### Catalog validation

A Control Catalog Pack MUST be rejected if:

- Any control ID is duplicated within the same catalog.

### Assessment validation

A Control Assessment Pack MUST be rejected if:

- Any assessment ID is duplicated within the same assessment pack.

If catalogs are supplied alongside validation, an assessment pack MUST also be rejected if:

- Any assessment control ID does not exist in the supplied catalogs.

### Portfolio cross-document validation

When validating a portfolio that references scenario documents:

- Every control referenced by each scenario MUST exist in `portfolio.controls[]`.

---

## Minimal Examples

### Catalog pack

```yaml
crml_control_catalog: "1.0"
catalog:
  name: "Org control IDs"
  controls:
    - id: "org:iam.mfa"
    - id: "org:edr"
```

### Assessment pack

```yaml
crml_control_assessment: "1.0"
assessments:
  - id: "org:iam.mfa"
    implementation_effectiveness: 0.7
    coverage:
      value: 0.9
      basis: user_fraction
```

### Scenario control references

```yaml
crml_scenario: "1.2"
scenario:
  name: "Phishing -> account takeover"
  controls:
    - "org:iam.mfa"
    - id: "org:edr"
      implementation_effectiveness: 0.5
      notes: "Assume partial tuning against this TTP"
```
