# Saved Netgen head-volume diagnosis

The completed read-only diagnosis finds **210 positive SICN < 0.1 cells**, all
with at least one interior node. Its complete boundary-participation counts are
**[0, 0, 15, 195, 0]** for zero through four original surface nodes per cell.
There are no observed nonpositive SICN cells. The unchanged **SICN >= 0.1**
gate still rejects this volume; no head field is accepted.

This extends the [completed Netgen trial](../atomic-cavity-plane-clip-cap-assembly-delaunay-netgen-postexport/README.md),
whose earlier publication deliberately left these new bins unknown. That
historical checkpoint remains unchanged. The inspected MSH identity is
**4b983f4ab0134d01573059aecb8f4ba512dabbdfe54fbce6abaa0a06af29fe1d**,
235,742,414 bytes. Its body is excluded here.

## What the saved-file reader observed

The exact [report](reports/readback-report.json) covers all **1,097,048 nodes**
and **3,620,809 tetrahedra**, with 225,317 referenced interior nodes and zero
orphans. Four complete tagged-array hashes, three complete native metric
arrays/distributions, signed volumes, explicit source-boundary coordinate bits
and explicit surface connectivity match the single completed Netgen
**16f6ecc5…['after']** proof. Minimum SICN is **0.039074265058645995**;
summed signed volume is **915453.1236217882 mm³**. Explicit surface-element
equality is not an independent tetrahedral-boundary incidence proof.

| Original source-boundary nodes per poor cell | Count | Deterministic representative |
| ---: | ---: | --- |
| 0 | 0 | None |
| 1 | 0 | None |
| 2 | 15 | tag 28848480; SICN 0.04678534994230571 |
| 3 | 195 | tag 29801902; SICN 0.039074265058645995 |
| 4 | 0 | None |

The two complete representative records are the minimum **(SICN, cell tag)**
in each nonempty class, not a statistical sample. Boundary participation means
exact admitted source tags **1..871731**, including constructed cap points;
it is distinct from any surface-repair fixed mask. Interior ancestry is not
transferred across optimizers. These bins neither identify an OEM/physical
feature nor establish repair feasibility, thermal resolution or a remedy.

Full tetrahedral exterior incidence, opposite internal orientation and entity
classifications remain **worker-only observations from the prior trial**, not
repeated by this reader. The report's `fixed_boundary_only_nonpositive_cells`
is vacuously true for its empty nonpositive list; it says nothing about the
210 positive poor cells. The [stopped-result peer](reviews/result-peer.json)
states its independent saved-record and representative-witness scope.

## Sources, controls and reproducibility limits

The executed [reader](sources/reader.py), SHA256 **65fe8215e9d96100bde76a1ec659d253102e5c3db2ec8ab12cca3f98e8629560**,
changes one literal baseline locator from the prior diagnosis; its three helper
ASTs are unchanged. The [runner](sources/run_readback.py) is byte-identical
**4fb37080…**. Five selected stdlib/AST guards passed; prior unchanged classifier
and runner guards were reused without a duplicate run. Source preparation and
source/child peer documents retain their historical pending/unrun fields;
the separately associated [root test projection](tests/root-five-guards-projection.json),
[actual child projection](contracts/actual-projection.json) and stopped records
describe the later completed execution. No historical contract is rewritten.

There was one read-only call and no generation, optimization, mesh export or
solve. Controller/outer elapsed times were **17.339048625 / 17.985258084 s**;
34 RSS observations reached **2,329,460,736 bytes**. The 120 s wall deadline,
sampled 8 GiB RSS and sampled 1 GiB output stop thresholds and two software
threads are recorded, with no hard OS CPU/RAM/disk quota or certified peak.
All **168 input and three runtime hashes** remained unchanged. Owned `wait()`
cleanup and terminal success are the lifecycle evidence; no worker PID was
retained for an individual absence probe, and known-workflow observations do
not prove comprehensive exclusion of all native processes.

[Original-records](original-records.json) gives exact-copy identities, explicit
projection omissions, the complete six-file stopped inventory and role-key
runtime bindings. Original digest values are preserved. Raw logs, argv, PID
values, private host locators and RSS series are omitted. This selected capsule
is not a standalone runnable workspace or the full private dependency closure;
the existing Netgen trial supplies linked ancestry. The unchanged stdlib
`python3 -B verify.py` verifies sealed bytes and closure only, without importing
scientific code or reproducing the diagnosis.

This is a numerical mesh diagnosis. It grants no accepted/converged head
volume, PDE/thermal/strength result, feature/OEM upgrade, fitment, material or
LPBF qualification, engineering release or manufacturing authorization. The
0.0625 mm source representation budget and 414 unmet stronger Mesh_2 shape
conditions remain separate surface evidence. Project-authored material retains
the [project licence](LICENSE.project); upstream/runtime bodies are excluded.
