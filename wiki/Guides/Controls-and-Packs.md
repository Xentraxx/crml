# Controls & Packs (Guide)

This guide shows the practical workflow for using control IDs, catalogs, assessments, portfolios, and scenarios.

---

## Recommended workflow

1. Define your organization specific control IDs in one or more **Control Catalog Packs** (or download one of the reference packs)
2. Record your org posture in a **Control Assessment Pack**.
3. Build a **Portfolio** with a `controls[]` inventory (derived from your assessment pack).
4. Write (or download one of the reference) portable **Scenarios** that reference controls by ID (optionally with scenario-specific overrides).
5. Validate documents using the CLI (CRML Studio support is coming).

---

## Validate with the CLI

Validate any CRML YAML document:

- `crml validate path/to/file.yaml`

Typical usage:

- Validate a catalog pack before adopting it.
- Validate an assessment pack (optionally against catalogs).
- Validate a portfolio (which may load scenarios and enforce cross-document control-ID consistency).

---

## What to put where

- Catalog pack: the list of allowed IDs (+ optional metadata like `title`/`url`).
- Assessment pack: org-wide `implementation_effectiveness` and `coverage` per control.
- Portfolio: the executable set of assets/exposure + a `controls[]` inventory used for simulation and for validating scenarios.
- Scenario: threat-centric description + `scenario.controls[]` references (string IDs or objects for scenario-specific assumptions).

For normative merge/override rules, see: [Controls & Packs (Reference)](../Reference/Controls-and-Packs)
