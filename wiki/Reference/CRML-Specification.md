# CRML Specification

This section is an index for CRML specification and validation artifacts.

- Full CRML 1.1 specification (canonical): [CRML-1.1](CRML-1.1)
- JSON Schema reference: [CRML-Schema](CRML-Schema)
- Controls & packs semantics (CRML 1.2+): [Controls-and-Packs](Controls-and-Packs)
- CLI validation: [CLI-Commands](CLI-Commands)

If you’re looking for a quick practical walkthrough instead of the formal spec:

- [Getting Started](../Getting-Started)
- [Writing CRML Models](../Guides/Writing-CRML)
- [Controls & Packs](../Guides/Controls-and-Packs)

---

## `model` block

This is the **core of CRML**. It defines how risk is modeled mathematically.

### Assets

```yaml
model:
  assets:
    cardinality: 18000
    criticality_index:
      type: entropy-weighted
      inputs:
        - pam_entropy
        - dlp_entropy
      weights:
        pam_entropy: 0.6
        dlp_entropy: 0.4
      transform: "clip(1 + total_entropy * 3, 1, 5)"
```

The `criticality_index` maps entropy-like features into a **1–5 ordinal** or continuous score.

### Frequency models

```yaml
  frequency:
    model: gamma_poisson   # or poisson, hierarchical_gamma_poisson
    parameters:
      alpha_base: 1.2
      beta_base: 1.5
```

Semantics:

- `poisson`: events per asset ~ Poisson(λ)
- `gamma_poisson`: λ ~ Gamma(α, β), events ~ Poisson(λ) (i.e. Negative Binomial marginal)
- `hierarchical_gamma_poisson`: structured variant (simplified in the reference runtime)

### Severity models

```yaml
  severity:
    model: mixture
    components:
      - lognormal:
          weight: 0.7
          mu: 12.0
          sigma: 1.25
      - gamma:
          weight: 0.3
          shape: 2.8
          scale: 15000.0
```

Severity distributions are applied **per event**.

### Dependencies (optional)

```yaml
  dependency:
    copula:
      type: gaussian
      dim: 4
      rho: 0.65       # Toeplitz structure
```

This allows modeling correlated risk factors (e.g., different threat classes).

---

## `pipeline` block

Describes simulation controls:

```yaml
pipeline:
  simulation:
    monte_carlo:
      enabled: true
      runs: 30000
    mcmc:
      enabled: true
      algorithm: metropolis_hastings
      iterations: 15000
      burn_in: 3000
```

The reference runtime uses `runs` but ignores MCMC controls for now (or uses them only in optional modules).

---

## `output` block

Controls which metrics and artifacts are produced:

```yaml
output:
  metrics:
    - EAL
    - VaR_95
    - VaR_99
    - VaR_999
  distributions:
    annual_loss: true
    monthly_loss: false
  export:
    csv: "enterprise_results.csv"
    json: "enterprise_posterior.json"
```

CRML itself is **model-centric**, not GUI-centric. It assumes consumers can:

- read CSV
- read JSON
- ingest metrics into risk dashboards
