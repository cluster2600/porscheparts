# Delivery, verification and architecture governance

## Ordered increments

| Increment | Deliverable | Acceptance | Current boundary |
|---|---|---|---|
| I1 | English architecture, ADR and Mermaid viewpoints | Render diagrams; verify links and stable IDs | This change |
| I2 | Local Qwen dataset, training runner and adapter evaluation | Immutable model revision; disjoint splits; actual before/after receipt | This change; see training report |
| I3 | Reconnect existing Kali workers and inventory resources | Host identity, CPU/RAM/disk, tool versions and bounded witness run | Live access still required |
| I4 | Synthetic duct through PicoGK and CPU analysis | Voxel study, three mesh levels, conservation and analytical benchmarks | No physical Porsche dimensions inferred |
| I5 | Portable USD assembly package | Strict USD, unit/axis checks, relocated dependencies | No rental before completion |
| I6 | Omniverse review | Approved ceiling/deadline, collected hashes and confirmed teardown | No rental in I1/I2 |
| I7 | Additional measured engine parts | Per-part evidence and professional review as applicable | Physical qualification remains separate |

I3-I7 reuse the existing station, CPU, catalogue and USD workflows. They are
not reported as deployed by the documentation/AI increment. Preserve current
user work by implementing on a clean branch from current upstream main.

## Requirements and traceability

| Requirement | Element | Decision | Verification |
|---|---|---|---|
| R-EN: English authored output | all views, A-AI | ADR 0012 | English docs/prompts; existing translation report tracks legacy work |
| R-PROVENANCE: never invent fit or material evidence | B-DESIGN, B-QUALIFY | ADR 0012 + catalogue policy | Catalogue checks; model evidence-gate holdouts |
| R-LOCAL: prepare before renting | T-MAC, T-K1, T-K2 | ADR 0012 | Host receipts; solver checks; no rental code in AI runner |
| R-GPU-LAST: GPU only for final review | T-VAST, A-RTX | ADR 0012 | I5 gate, approved budget and existing deadline guard |
| R-CAD: new geometry uses PicoGK | A-CAD | ADR 0004 + ADR 0012 | Existing station witness; later duct resolution study |
| R-CAE: reproducible CPU analysis | A-CAE | ADR 0012 | Executed Poiseuille, traction and conduction, then mesh convergence |
| R-USD: portable composition | A-USD | ADR 0012 | Relocated strict and semantic USD validation |
| R-AI: measured local adaptation | A-AI | ADR 0012 | Dataset checks, actual QLoRA logs, base/adapter evaluation |
| R-CHANGE: evidence remains immutable | all data contracts | translation policy | Preserve pinned inputs, review diff, run `make check` |

Requirement and element IDs above are stable review anchors. Each future PR
names affected IDs, updates the relevant view/ADR, and links actual receipts.
The project owner approves scope and cost; the engineering reviewer approves
physical acceptance. The implementing agent cannot fill either role by
producing a diagram or a model response.

## Tailored TOGAF ADM

| ADM concern | Project artifact |
|---|---|
| Preliminary and Architecture Vision | Objectives, authority and conventions in the architecture overview |
| Business Architecture | Design, numerical verification, review and physical qualification capabilities |
| Information Systems Architecture | Workflow contract, data lineage, Qwen and solver roles |
| Technology Architecture | Mac/Kali/Vast allocation and pinned runtime references |
| Opportunities, Solutions and Migration Planning | I1-I7 and the baseline-gap table |
| Implementation Governance | Requirements table, PR checks and explicit acceptance evidence |
| Architecture Change Management | ADR updates when a runtime, material, host or claim changes |
| Requirements Management | R-* table maintained throughout every increment |

No enterprise repository service, new scheduler or modeling server is needed.
Markdown, Mermaid, existing JSON records and Git reviews are the initial tools.

## Verification and failure handling

Run the dedicated AI tests without MLX or network access. The runtime training
path is opt-in and uses a separate Python environment. Validate JSON types,
unique case IDs, exact split membership, absence of duplicated prompts, source
references and expected-output consistency before training.

For live training, preflight Apple Silicon/Metal and disk reserve, record model
and dataset hashes, use a new output directory, retain failure logs and never
mark an incomplete run successful. Freeze package versions in a lock file.
Run no external telemetry and publish no adapter or dataset to a model hub.

Render every Mermaid block in the three architecture documents and training
README with a pinned Mermaid CLI. Check local Markdown links. Run targeted
tests and `make check`; record unrelated baseline failures separately rather
than silently repairing or skipping them.

Future I3-I6 negative tests: unreachable host, changed key, timeout, interrupted
calculation, missing output, hash mismatch, changed input, broken USD reference,
missing approval, failed collection and failed teardown verification. Any such
failure blocks promotion; numerical success never grants manufacturing release.

## Language migration

The current upstream already has English top-level documentation and a
[translation policy](../TRANSLATION.md). Extend that policy to all newly authored
comments, training examples and generated reports. Continue legacy translation
in separate reviewed batches, preserving technical meaning and stable names.
Pinned evidence, archive files and external quotations stay original; supply
English explanation alongside them. Do not claim the entire historical tree
has been translated by this increment.
