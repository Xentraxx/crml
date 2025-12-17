# Maintainer Brief: Why accepting this PR moves CRML forward

This note summarizes the work between commit `de7cba0` and current `HEAD` on branch `crml-dev-1.2`, with a focus on **why the architectural direction (language vs engine split)** is a net-positive for the project.

It is intentionally concise, technical, and honest about trade-offs.

---

## Executive Summary

This change turns CRML from a *monolithic Python package* into a **modular, multi-package architecture**:

- **`crml_lang`**: the CRML *language layer* (schemas, models, validation, planning, API for tools)
- **`crml_engine`**: the *execution layer* (simulation runtime, copula logic, CLI, results)

This is a foundational shift that enables:

- Better **modularity** (clear separation of concerns and ownership)
- Better **portability** (schema-first contracts, easier non-engine tooling)
- Safer and faster **evolution** of the language without entangling simulation internals

---

## What changed (high level)

### 1) Package split (monolith → `crml_lang` + `crml_engine`)

- The previous code under `src/crml/` was decomposed and reorganized into two installable packages.
- Each package has its own `pyproject.toml`, `README.md`, and changelog entries.

**What this accomplishes**

- The CRML *specification surface area* (schemas/models/validators) is no longer coupled to simulation code.
- Downstream consumers can depend on the language package without pulling the entire engine.

### 2) Schema-first language definition

- Introduced/expanded JSON Schemas for core document types (scenario, portfolio, controls, results).
- Added schema generation tooling.

**What this accomplishes**

- CRML becomes a more “portable language” (clear, machine-readable contracts).
- Enables editor tooling, CI validation, and alternative runtimes to target the same contracts.

### 3) Validation and semantics modularization

- Validators refactored into focused modules.
- Validator API evolved to return **structured reports**, not just pass/fail.
- Added cross-pack semantic checks (e.g., portfolio/control pack consistency).

**What this accomplishes**

- Validation is now a reusable subsystem for:
  - CLI validation
  - Web API endpoints
  - IDE integrations
  - CI pipelines
- Structured reports make it easier to present user-friendly diagnostics.

### 4) Language expansion (portfolio + controls + planning)

- Added support for portfolios.
- Added control catalogs/assessments and “control packs”.
- Added a portfolio planning module.

**What this accomplishes**

- CRML is no longer limited to “scenario-only” workflows.
- The language now supports organizational-scale modeling patterns.

### 5) Engine alignment and improvements

- Engine-agnostic “result envelope” introduced to standardize outputs.
- Simulation enhancements added (e.g., Monte Carlo cardinality, copula-based control state dependencies, FX config updates).

**What this accomplishes**

- A stable output contract for the web app / downstream reporting.
- A clearer boundary: engine produces results that conform to language-defined envelopes.

### 6) Tests, examples, and docs updated

- Tests reorganized by package responsibility (engine vs language), with substantial new coverage.
- Examples reorganized into clearer subfolders.
- Wiki/docs updated to reflect new conceptual model and installation paths.

---

## Why this is the best direction (architectural justification)

### Modularity

This architecture explicitly separates:

- **Language correctness** (models/schemas/validation/planning) from
- **Execution** (simulation runtime, numerical methods, CLI operations)

Benefits:

- Contributors can work on the language without understanding Monte Carlo internals.
- Engine changes are less likely to accidentally break the schema/validation contract.
- Clearer ownership and review boundaries (language PRs vs engine PRs).

### Portability

CRML becomes portable in two dimensions:

1) **Across tools**: schema-first + structured validation reports enable
   - editor tooling
   - CI checks
   - web services
   - import/export pipelines

2) **Across runtimes**: the engine is now *one implementation* that consumes CRML.
   - Other engines (or simplified runtimes) can be built later without rewriting the language.

### Future evolution without rewrite cycles

Historically, monoliths force “big bang” rewrites when they outgrow initial structure.

This split reduces the risk of future rewrites by making CRML’s evolution incremental:

- language changes can be versioned at the schema level
- engine can adopt language features gradually

---

## Downsides and how they are managed

### 1) Version coordination overhead

**Downside:** two packages means version compatibility becomes a concern.

**Mitigation:**

- document supported version pairs
- maintain a small compatibility matrix in release notes
- use semver discipline: breaking schema changes → major bumps

### 2) Higher maintenance surface

**Downside:** more modules, more schemas, more tests.

**Mitigation:**

- the additional surface area is purposeful: it replaces implicit behavior with explicit contracts
- schema generation tooling reduces manual duplication

### 3) Migration friction for existing users

**Downside:** imports, file locations, and conceptual boundaries changed.

**Mitigation:**

- provide a short migration guide (imports and entrypoints)
- preserve stable user-facing formats where possible (YAML/JSON shape through schemas)

### 4) Risk of spec/engine drift

**Downside:** schema and engine behavior can diverge if not kept aligned.

**Mitigation:**

- validate engine output against result-envelope schema in tests
- keep schemas and validators in `crml_lang` as the single source of truth

---

## Maintainer value (why accepting this PR is pragmatic)

Accepting this PR:

- **reduces long-term maintainer burden** by clarifying boundaries and responsibilities
- **enables more contributors** (language work becomes accessible without simulation expertise)
- **unblocks tooling** (structured validation, stable schemas, predictable outputs)
- **lays a sustainable foundation** for new features (controls/packs/planning) without accruing unmanageable coupling

The alternative (keeping CRML monolithic) risks:

- continued coupling between spec, validation, and runtime
- slower iteration and harder reviews
- difficulty supporting multiple consumers (web app, CLI, validators, external tools) consistently

---

## Suggested acceptance criteria (to keep risk low)

If you want to de-risk acceptance, here are concrete checkpoints:

- Confirm that existing core workflows still run via CLI/API.
- Run unit tests for both packages.
- Ensure docs/installation instructions match the release packaging.
- Confirm schema versions and language/engine API boundaries are clear.

---

## Closing

This refactor is not “architecture for architecture’s sake”. It converts CRML into a **real language platform**: explicit contracts, modular validation, and an engine that is one consumer of the language.

That is the best long-term posture for maintainability, extensibility, and portability.
