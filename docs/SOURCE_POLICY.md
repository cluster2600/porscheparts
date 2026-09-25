# Source policy

## Trust hierarchy

| Level | Type | Use |
|---|---|---|
| A | Traceable direct measurement or official document | Reference dimension or specification |
| B | Manufacturer, OEM supplier or standard | Material, process, component |
| C | Reproducible community measurement | Cross-check or secondary geometry |
| D | Third-party model with a license but unproven accuracy | Visual reference only |
| E | Estimate from a photograph or rendering | Explicitly flagged assumption |

```mermaid
flowchart TD
    S["Candidate source"] --> PD{"Protected document?"}
    PD -- yes --> OUT["Stays out of the repository;<br/>the record keeps its reference"]:::stop
    PD -- no --> LV{"Trust level"}
    LV --> A["A · traceable direct measurement or official document<br/>→ reference dimension or specification"]
    LV --> B["B · manufacturer, OEM supplier or standard<br/>→ material, process, component"]
    LV --> C["C · reproducible community measurement<br/>→ cross-check or secondary geometry"]
    LV --> D["D · licensed third-party model, unproven accuracy<br/>→ visual reference only"]
    LV --> E["E · estimate from a photograph or rendering<br/>→ explicitly flagged assumption"]
    N1["Screenshot or scan without scale"] --> N1X["Not a measurement"]:::stop
    N2["Two sources that copy each other"] --> N2X["Not two confirmations"]:::stop
    classDef stop fill:#fde2e1,stroke:#c0392b,color:#1a1a1a;
    classDef ok fill:#e3f1e6,stroke:#2e7d32,color:#1a1a1a;
    classDef open fill:#fff4d6,stroke:#b7791f,color:#1a1a1a;
```

## Rules

- Public data is not automatically royalty-free.
- A screenshot or a scan without scale is not a measurement.
- An exploded view informs the assembly, not necessarily the dimensions.
- Two sources that copy each other are not two confirmations.
- Protected documents stay out of the repository; the record keeps their
  reference.
- Every contradiction stays visible until it is resolved.

## Auditing a 3D model

Record: author, URL, license, format, variant, number of parts, whether the
interior or the underbody is present, units, declared dimensions, whether it may
be modified and redistributed, and the results of comparison with known
dimensions.
