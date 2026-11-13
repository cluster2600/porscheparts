# Complete native geometry inspection of the conditioned 935 study

The actual OpenFOAM 13 `checkMesh -case head` completed on a receipt-bound Vast
instance. It rejected five geometric checks, despite returning exit code zero.
The input geometry was not changed and no field solver was launched. This closes
the earlier incomplete native inspection; it does not admit the mesh to CFD.

This is the separately conditioned hypothetical **bare-head numerical mesh**,
not the [supported single-volume printing assembly](../935-single-volume-20261107/README.md).
Its 12,981,388 tetrahedra and 4,181,299 points retain the earlier conditioning
lineage and 0.0070661043 mm numerical correspondence bound to the frozen
hypothetical printing surface. That bound is not specimen metrology. The
original scan, acquired-surface reconstruction and supported printing files
remain unchanged. No result here qualifies their physical scale or interfaces.

## Native result and independent checks

The fresh analytic control passed first. The actual head check then completed
in 793.032 seconds, within its 1,200-second limit and 48 GiB address-space cap.
It read 30,072,005 faces, including 21,853,547 internal faces. Its terminal `End`
marker, complete statistics, log hash and unchanged input hashes were recovered
and independently verified. A successful process status alone is insufficient.

Native topology checks passed, including one cell region and a closed, singly
connected boundary patch. A separate local audit also traversed every internal
owner/neighbour edge: all 12,981,388 cells belong to one connected region, every
cell has four faces and every cell index is in range. Connected, disconnected
and isolated-cell controls passed before that audit.

| Native geometric finding | Actual result |
| --- | --- |
| High aspect ratio | 39,913 cells; maximum 1.0505536196303592e102 |
| Zero or negative computed volume | 4,070 cells; minimum -1.562181735243843e-15 |
| Non-orthogonality errors | 1,009 faces; maximum 90.000000000224475 degrees |
| Severe non-orthogonality above 70 degrees | 3,953,359 faces |
| Incorrect face pyramids | 6,851 faces |
| High skewness | 63,762 faces; maximum 1112.9646044215631 |
| Overall native verdict | `Failed 5 mesh checks.` |

Face-area magnitudes and coupled-point location checks passed. Native volumes
above use the case's numeric coordinates; do not interpret them as calibrated
SI volumes. Earlier exact positive tetrahedral determinants do not establish
usable finite-volume operators: this native rejection is retained alongside
them, without relaxing thresholds or claiming that the signs identify a newly
measured physical defect.

The same geometric findings were already observed by the separate
[extended geometry diagnostic](../935-native-geometry-admission-20261105/README.md)
and its [exact-origin experiment](../935-exact-origin-20261105/README.md).
This increment completes the historical default topology check; it does not
discover a new geometric defect or supersede the later conditioning candidates.
The [centroid native readback](../935-centroid-native-readback-20261105/README.md)
retains a different mesh with 997 nonpositive native shape indicators, while the
[complete condition census](../935-condition-directed-20261105/README.md)
already attributes severe cells to boundary constraints. Further work must
start from those current candidates and source constraints, rather than repeat
this old native case or a blind parameter sweep. Every replacement still needs
an independently checked surface contract, quality, native geometry and
convergence gates before head CFD/CHT. No duplicate or geometry-only check was
run after this complete rejection.

## Execution and resource closeout

The pinned image was
`ghcr.io/cluster2600/3dprinting993-mesh-cfd@sha256:a1db60cbf61bbcca52c171e50cab01ed0b6ec860b227e7c5fc50f7b809659b4f`.
The actual OpenFOAM 13 setup file hash was checked before execution. The offer
provided 16 effective CPUs and 256,498 MB allocated RAM; larger host-level RAM
and CPU affinity values were not treated as dedicated allocation.

Two earlier launch attempts produced no instance. The installed approved
wrapper re-searched only 50 bundles when resolving a selected offer, so an
offer visible moments earlier could disappear from that bounded lookup.
[The two-line fix](source/mesh-offer-lookup.diff) raises only the selected-offer
lookup limit to 1,000. Its default listing, safety filters, authentication and
secret access remain unchanged. Original and installed hashes and independent
query/rollback controls are recorded in `results.json`. The repaired real
launch succeeded; no Keychain or raw OpenBao fallback was used.

The task rented only instance 59565622. A separate local guard was armed before
creation. An amendment retained a 40-minute paid-runtime deadline measured
from the successful creation intent, rather than consuming the window on
failed offer preparation. Its $1.50 attempt cap and the original $5 reserve
remained. The 474,522,459-byte upload was hash-verified before extraction.
Provider endpoint metadata and a dedicated first-use SSH host-key pin were
used; that pin is not independent host attestation. Private endpoints and keys
are excluded from this public increment.

After the worker and native child were confirmed terminal, the collector
omitted only 19 hash-matching input copies and recovered 14 generated files.
Every recovered byte was independently checked. Tampered-archive and unsafe
archive-member controls were rejected. The task instance was then destroyed;
both controller and independent guard confirmed absence, and the guard exited.
The conservative charge estimate is **$0.3362**, including a **$0.28** network
allowance, rather than a provider invoice. The cumulative conservative
allocation is **$15.6789** under the unchanged $35 total / $30 compute / $5
transfer-and-closeout budget. No foreign resource was destroyed.

## Replay and acceptance boundary

Use Python 3.11 or newer (local verification used 3.13; the system `python3`
was too old for `hashlib.file_digest`). Keep the actual private input manifest,
case files and archive hashes bound to `results.json`. The worker is a one-shot
script placed alongside that manifest and the fresh case directories. It
checks the image setup hash, control and unchanged original inputs, and kills
and reaps its own child on timeout or termination. Do not restart a timed-out
observer without reconciling the same worker handle.

`collect_native_check.py --help` requires the exact owned instance ID and
original manifest/archive hashes. It refuses live task workers and includes
changed input files rather than silently discarding them.
`verify_native_collection.py --help` independently verifies the recovered
archive, regular member paths, exact file set and hashes, original omitted
inputs, native completion and admission. Run `inspect_cell_regions.py --help`
against a job bound to the unchanged native files and the frozen earlier
reader; it reuses only that reader's numeric-list parser. Sources, execution
receipts, failures and private native outputs are preserved in the named
private capsule. Git contains source and scalar evidence only.

This increment follows the [scan workflow](../../architecture/scan-repair-workflow.md)
and [local-compute decision](../../decisions/0012-local-compute-gpu-last.md).
Requirement `R935-NATIVE-GEOMETRY-1` binds the previous import to a complete
native geometric verdict; `results.json` links inputs, commands and checks.
Qwen/CADAM assistance does not replace PicoGK/STEP, Gmsh, OpenFOAM, CalculiX or
Adamantine. This run neither changes their authority nor completes mechanical,
thermal, fatigue or additive-process qualification.

Physical scale, specimen interfaces, hidden passages, alloy, process recipe,
powder removal, support acceptance, machining, inspection and professional
engine validation remain open. The existing hypothesis 3MF and neutral
contours are digital study deliveries; no machine-specific metal job is
released. Supplier drafts remain unsent and the original functional objective
remains active.
