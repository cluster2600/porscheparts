# Current110: complete 73-component coordinate diagnostic

This research checkpoint retains every one of the 73 single-call SLSQP diagnostics for the assumed water-cooled 962 C head family through 4.0 L. The original head mesh is unchanged. Unknown OEM interfaces, operating loads, hot material properties and manufacturing qualification remain open.

## Result

All 73 optimizers reported success, but the unchanged exact signed SICN 0.1 gate passes only 62 groups. The 11 rejected groups are 2, 7, 8, 9, 10, 21, 28, 30, 31, 39 and 45. Their complete proposals remain available, including 43 positive-poor cells: 23 were initially poor and 20 were initially acceptable. No returned cell has nonpositive or undefined quality. Solver convergence does not override the exact gate.

The [complete result review](evidence/work/962-engineering/head-star-current110-component-sicn-result-peer-001/review.json) independently reconstructs all 4,964 before/final Fraction rows from saved binary64 coordinates and ordered connectivity. Fixed coordinate words, oriented component boundaries and each component's own exact volume match. Process/runtime observations are root-attributed; independent arithmetic does not establish global embedding or physical validity.

The [root acceptance](evidence/work/962-engineering/head-star-current110-component-sicn-root-execution-001/result-peer-acceptance.json) accepts this finite diagnostic accounting. All 73 calls closed without stops or signals; failed candidates were retained and no call was repeated. Ordinary/sample limits were 30 seconds, 1 GiB RSS, 16 MiB output and two requested threads per case, with separate outer supervision.

The 62 passing groups cover 66 movable nodes and 1,983 cells, including 86 originally poor cells. The rejected 11 cover 16 movable nodes, 499 cells and 24 originally poor cells. Combining only passing free rows has no saved-set shared-cell coupling conflict; one cross-group context node stays fixed. A separate native application and full save/reopen census are still required.

The current head therefore retains 110 poor cells and minimum native SICN 0.039074265058645995. That minimum lies in rejected component 30. A future partial application cannot by itself clear the whole-head quality gate. The separate 414 stronger surface-quality failures and geometric embedding remain unclosed. The aggregate quality of returned local proposals is not a newly evaluated whole-head mesh.

## Complete inspectable evidence

The [selection manifest](selection-manifest.json) contains all 843 selected originals: 827 checkpoint files, 14 direct input dependencies and the original selection plan/note. Every one of the 73 exact contracts, eight-file outputs and root closures is included, alongside source preparation, guards, runtime admission, launch, source/batch/result reviews and acceptance. No case, rejected row, duplicate source copy or empty controller log is omitted.

Start with the [component manifest](evidence/work/962-engineering/head-star-current110-component-sicn-prep-001/component-manifest.json), [worker](evidence/work/962-engineering/head-star-current110-component-sicn-prep-001/propose_component.py), [batch closure](evidence/work/962-engineering/head-star-current110-component-sicn-root-execution-001/batch-once-closed.json) and [result bindings](evidence/work/962-engineering/head-star-current110-component-sicn-result-peer-001/bindings.json). These enumerate exact cases, full saved points/quality rows, statuses and original identities.

Fifteen fixed literal path rules make private local paths readable. The earlier fourteen-rule selection-plan refusal is historical; one additional exact registered Python configuration-path rule closes its 152 listed residuals. Numeric values/types, binary64 words, SHA strings, process IDs, arrays, ordering and historical flags are preserved. Projected source is an inspectable record, not a directly runnable host-independent simulation package. Original digests still identify original bodies.

Raw head MSH/BIN, installed Python/NumPy/SciPy/Gmsh packages, runtime binaries and third-party source bodies are excluded. Their recorded identity metadata remains; no new raw mesh download or physical measurement is implied. Complete selected coordinate/quality JSON bodies are included.

## Next stages

The programme remains: English baseline; documented material/process state and head thermal/structural analysis; calibrated LPBF; Omniverse with accepted fields and units; PhysicsNeMo reference datasets, independent evaluation and twin integration. This local-quality study establishes none of those physical qualifications and applies no head edit.

Run python3 verify.py to check sealed bytes and complete file closure. It performs no scientific calculation.
