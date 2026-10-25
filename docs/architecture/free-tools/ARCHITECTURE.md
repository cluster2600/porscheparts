# Free tools architecture

This is an implemented batch-tool integration with separately recorded native
execution status. Allocation diagrams describe the target Mac/Kali deployment;
they do not assert that either host is currently reachable.

The [existing architecture conventions](../README.md) apply: stable element
IDs, named relationships and clear business/application/technology boundaries.
These Mermaid views are project viewpoints, not a full ArchiMate exchange model.

## Infrastructure architecture

```mermaid
flowchart TB
    GIT["D-GIT<br/>Source, locks and sanitized receipts"]
    CI["T-CI<br/>Software verification"]
    subgraph MAC["T-MAC : Mac controller"]
        CONTROL["A-CONTROL<br/>Make, Python, FTS5 and local Qwen"]
        STORE["D-PRIMARY<br/>Private DVC artifact store"]
        CONTROL -->|"local artifact management"| STORE
    end
    subgraph KALI["T-KALI : Native Linux worker"]
        WORKER["A-WORKER<br/>CloudCompare, SALOME, CalculiX<br/>OpenTURNS and OpenMDAO"]
        COPY["D-COPY<br/>Independent private artifact copy"]
        WORKER -->|"verified job inputs"| COPY
    end
    REVIEW["B-REVIEW<br/>Engineering review"]
    GIT -->|"reviewed inputs"| CONTROL
    GIT -->|"synthetic controls"| CI
    CONTROL -->|"bounded SSH jobs"| WORKER
    STORE -->|"DVC objects over strict SSH"| COPY
    WORKER -->|"results and receipts"| REVIEW
    CONTROL -->|"collected evidence"| REVIEW
```

The Mac holds the primary store and metadata outside any Git checkout. Kali
holds an independent store, on a native Linux filesystem, outside disposable
caches. Successful SSH transfer is insufficient: restoration into a fresh empty
cache and SHA-256 verification are required for each store.

Use existing SSH identities with strict host-key checking. Thunderbolt link
activity does not establish an SSH identity. Only owned jobs and containers may
be terminated. Geometry control containers have no network, no capabilities,
a read-only root, bounded CPU/RAM/PIDs and a finite deadline. Images contain
tool code and synthetic fixtures, not project scans or credentials.

## Software architecture

```mermaid
flowchart TB
    PF["D-PF<br/>Authorized PorscheFanatics snapshot"]
    CAT["D-CAT<br/>Authoritative catalogue"]
    IDX["A-SEARCH<br/>FTS5 index"]
    AI["A-QWEN<br/>Documentary draft"]
    GATE["A-GATE<br/>Independent units and interface checks"]
    GEO["A-CAD<br/>Existing CAD and PicoGK recipes"]
    CC["A-METRO<br/>CloudCompare diagnostics"]
    SM["A-MESH<br/>Existing mesher or SALOME comparison"]
    CAE["A-CAE<br/>CalculiX"]
    OT["A-UQ<br/>OpenTURNS sensitivity"]
    OM["A-OPT<br/>OpenMDAO bounded studies"]
    REP["D-REPORT<br/>Evidence reports"]
    DATA["A-DVC<br/>Private artifact management"]
    PF -->|"approved export"| IDX
    CAT -->|"allowlisted summaries"| IDX
    IDX -->|"untrusted referenced context"| AI
    AI -->|"human-reviewed proposal"| GATE
    CAT -->|"independent contract"| GATE
    GATE -->|"admitted request"| GEO
    GEO -->|"diagnostic samples"| CC
    CC -->|"measurement report"| REP
    GEO -->|"frozen input surface"| SM
    SM -->|"checked mesh and groups"| CAE
    CAE -->|"verified response"| OT
    CAE -->|"verified response"| OM
    OT -->|"scoped study"| REP
    OM -->|"reviewed parameter proposal"| GATE
    CAE -->|"numerical evidence"| REP
    DATA -.->|"versioned artifacts"| GEO
    DATA -.->|"versioned artifacts"| REP
```

The documentary path does not modify `qwen-picogk-qualified` or inject arbitrary
text into its canonical numeric request. Optional MLX inference runs offline
with explicit local model/adapter directories, records their identities, and
produces only a draft. Model output is never executed or used as inspection
evidence. The 30-case retrieval suite does not measure generated-answer quality.

FTS5 stores source IDs, titles, excerpts, rights, scope and the snapshot digest.
The index is a disposable derivative. Corpus changes require a rebuild. Its
claim metadata is documentary input, not a new engineering authority.

DVC transfers content objects. Existing SHA-256 manifests establish input
identity independently of DVC's internal object hashes. The private DVC metadata
and remote paths remain private; public receipts retain sanitized asset IDs.

## Logical architecture

```mermaid
flowchart TD
    START["Freeze carrier revision and input hashes"]
    INPUT{"Evidence sufficient for declared scope?"}
    BLOCK["Record engineering blocker"]
    RUN["Run bounded diagnostic or analysis"]
    CHECK{"Complete outputs and independent checks pass?"}
    FAIL["Preserve failed attempt"]
    RESULT["Record scoped result"]
    READY{"Convergence and physical inputs established?"}
    OPT["Reviewed carrier optimization study"]
    REVIEW["Engineering review"]
    START --> INPUT
    INPUT -->|"No"| BLOCK
    INPUT -->|"Yes"| RUN
    RUN --> CHECK
    CHECK -->|"No"| FAIL
    CHECK -->|"Yes"| RESULT
    RESULT --> READY
    READY -->|"No"| BLOCK
    READY -->|"Yes, future reviewed baseline"| OPT
    OPT --> REVIEW
```

The registered carrier baseline deliberately cannot enable optimization.
Changes to its evidence require a new reviewed baseline and acceptance policy,
not editing a caller-supplied boolean. Current physical-interface and convergence
blockers are read back in each admission replay. Historical surface certificates
are not replaced by CloudCompare samples or SALOME's volume checks.

Each run writes into a new directory. Missing output, nonfinite values, hash
mismatch, invalid units, timeout and tool failure prevent acceptance. Failed
logs remain private. A completed command can still yield `blocked_engineering`.

The Markdown Mermaid blocks above are the diagram source of truth. SVG exports
are generated for rendering checks, never maintained as competing manual views.
