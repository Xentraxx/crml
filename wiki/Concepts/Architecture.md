# CRML System Architecture

CRML is organized into three layers:

- **Language/spec (`crml_lang`)**: schemas, models, validation, YAML IO
- **Runtime/engine (`crml_engine`)**: CLI + simulation runtime + portfolio execution + result serialization
- **Web UI (`web/`)**: CRML Studio (Next.js UI + API routes that call the CLI/runtime)

In addition to these layers, most real deployments also use **calibration tooling**:

- **Calibration tools (seperate tool responsibility but might be part of an engine)**: ingest organization-specific evidence (e.g., incident logs) and write back calibrated CRML scenarios/portfolios.

For the detailed architecture, see:

- [Architecture-Language](Architecture-Language)
- [Architecture-Engine](Architecture-Engine)

## Document types

- Scenario documents: `crml_scenario: "1.0"` (top-level `scenario:`)
- Portfolio documents: `crml_portfolio: "1.0"` (top-level `portfolio:`; if `portfolio.assessments` is used, `portfolio.control_catalogs` must also be provided)
- Control cataloges documents: `crml_control_catalog: "1.0"` (top-level `catalog:`)
- Assessment documents: `crml_assessment: "1.0"` (top-level `assessment:`)
- Control relationships documents: `crml_control_relationships: "1.0"` (top-level `relationships:`; control-to-control mappings with overlap metadata)
- FX config documents: `crml_fx_config: "1.0"` (top-level `base_currency`, `output_currency`, `rates`, optional `as_of`; engine-owned config document)
- Portfolio bundle artifacts: `crml_portfolio_bundle: "1.0"` (top-level `portfolio_bundle:`)
- Simulation result artifacts: `crml_simulation_result: "1.0"` (top-level `result:`)

## System-level data flow

```mermaid
flowchart TD
    DOC["CRML YAML/JSON"]
    ORGDATA["Org evidence<br/>(incident logs, telemetry)"]

    subgraph L["crml_lang (language/spec responsibility)<br/>Ends after validation + bundling"]
        LANG["crml_lang<br/>validate"]
        BUNDLE["crml_lang<br/>bundle"]
    end

    subgraph T["Tooling (engine/tool responsibility)<br/>Optional calibration step"]
        CAL["calibrate<br/>(fit/update scenario params)"]
    end

    subgraph E["crml_engine (engine responsibility)<br/>Planning + execution"]
        PIPE["crml_engine.pipeline<br/>plan"]
        ENG["crml_engine<br/>execute"]
    end

    subgraph W["web/ (UI responsibility)"]
        WEB[CRML Studio UI]
    end

    DOC --> LANG
    LANG -->|ValidationReport| TOOL[CLI/CI/Web tooling]

    ORGDATA -.-> CAL
    DOC -.-> CAL
    CAL -.->|updated CRML YAML/JSON| DOC

    DOC --> BUNDLE
    BUNDLE -->|CRPortfolioBundle| PIPE
    PIPE -->|PortfolioExecutionPlan| ENG
    ENG --> RES[SimulationResultEnvelope]
    RES --> WEB
```

## Ecosystem data flow

CRML is designed so that organizations can assemble *auditable, portable* input artifacts from common upstream sources, and so that any compliant engine can emit results in a shared format that downstream tools can visualize.

In practice:

- **Threat intelligence** produces or informs *scenario documents* (frequency, severity, narratives, assumptions).
- **Organization evidence** (incident logs, internal loss data, telemetry) can be used by *calibration tools* to fit scenario parameters and reduce reliance on purely external priors.
- **Portfolios** describe the organization's relatively stable assets, business units, and exposure structure. They can be updated via internal tooling (e.g., CMDB/asset inventory imports), but the portfolio document remains the central reference.
- **Control catalogs** come from recognized authorities and frameworks (e.g., NIS, CIS) or can be commonly defined by the community. These catalogs define the canonical control set and their semantics.
- **Assessments** come from assessment/scan tools and audits. They capture which controls exist, how effective they are, and can optionally be used to populate or update the portfolio's control mapping.
- **Mappings** (control-to-control relationships) can come from public sources (e.g., Secure Controls Framework) and from community or organization-specific mapping work.

The language layer then provides a deterministic bundling step that inlines the referenced material into a self-contained `CRPortfolioBundle`, which can be handed to any risk engine without requiring filesystem access.

Engines are expected to return results using the **language-owned result envelope** (`SimulationResultEnvelope`). This creates a stable interface for any visualization tool (web UI, BI dashboards, reporting pipelines) to consume outputs without being coupled to a specific engine implementation.

```mermaid
flowchart LR
    TI["Threat intelligence<br/>feeds"] -->|publish| S["Scenario documents<br/>CRScenario"]

    EVID["Organization evidence<br/>(incident logs, telemetry)"] -->|calibrate| CAL

    subgraph T2["Calibration tooling<br/>(engine/tool responsibility)"]
        CAL["calibrate<br/>(fit/update scenarios)"]
    end

    CAL -->|write back| S

    ORG["Organization asset inventory<br/>(relatively static)"] -->|generate| P["Portfolio document<br/>CRPortfolio"]
    TOOL["Tooling (e.g. SIEM)<br/>imports and updates assets"] -.->|optional| P

    AUTH["Recognized authorities<br/>NIS, CIS"] -->|publish| CC["Control catalog<br/>CRControlCatalog"]
    SCAN["Assessment and scan tools"] -->|generate| CA["Assessment catalog<br/>CRAssessment"]

    COMM["Community / org mappings"] -->|publish| CR["Control relationships pack<br/>CRControlRelationships"]

    CC -.->|basis| CA
    CC -.->|ids| CR

    subgraph L2["crml_lang (language/spec responsibility)<br/>Ends after bundling"]
        B["Bundle step<br/>bundle_portfolio"]
        PB["CRPortfolioBundle<br/>inlined artifact"]
    end

    S --> B
    P --> B
    CC --> B
    CA --> B
    CR --> B
    B --> PB

    subgraph E2["Engines + tools (outside language responsibility)"]
        ENG["Risk engines<br/>engine A, engine B"]
        OUT["SimulationResultEnvelope<br/>standard contract"]
        VIZ["Visualization tools<br/>dashboards and reports"]
    end

    PB --> ENG
    ENG --> OUT
    OUT --> VIZ
```
