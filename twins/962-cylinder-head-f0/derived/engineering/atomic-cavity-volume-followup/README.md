# Atomic volume follow-up: timeout and poor-cell diagnosis

One default post-export optimizer was stopped at its 20-minute deadline without exporting a mesh. A separate completed read-only query classified every positive raw-mesh cell below the unchanged SICN 0.1 threshold. **The head volume remains rejected; no thermal, structural or LPBF result is established.**

## Optimizer: authoritative stop, stale checkpoint

The [controller projection](optimizer/controller.json) records return code −9, `native_deadline`, 1200.096300000092 seconds, all 2,338 RSS/output samples and maximum observed RSS 2,657,042,432 bytes. The separate [exact worker checkpoint](optimizer/worker-checkpoint.json) still says `running` at `calling_default_postexport_optimizer`: one attempted call, no return, no cache refresh and no saved MSH. It is the last written checkpoint, not an active-process or successful-result claim. The [root terminal review](optimizer/root-result.json) confirms stopped ownership, no MSH, all 208 launch pins, all 26 direct wrapper pins and six executed source snapshots unchanged.

This distinct call used the existing raw mesh, default `optimize('', force=True)`, a 1,200-second external deadline, an 8 GiB sampled-RSS stop and two software threads. These are monitored controls, not hard OS memory/CPU quotas or a peak-RSS guarantee. No mesh generation or automatic retry was requested. The selected [log lines](optimizer/native-log-selected.json) preserve the original Gamma histogram and intermediate optimizer messages; Gamma is not SICN, and those messages establish neither final quality nor stagnation. No partial in-memory result is admitted.

## Read-only diagnosis of the unchanged saved raw MSH

The [exact diagnostic report](diagnosis/report.json), [execution receipt](diagnosis/execution.json) and [root result review](diagnosis/root-result.json) bind the original saved MSH SHA-256 `5092c22174f7dd085058cf414478a9600e5022653e609a6bf385df09e12c3fa7`. Actual counts remain 3,058,267 tetrahedra, 979,076 nodes and 77,349 referenced interior nodes. All 283,853 cells with **0 < SICN < 0.1** are partitioned by their number of source-boundary nodes:

| Source-boundary nodes in cell | Positive poor cells |
|---:|---:|
| 0 | 1,227 |
| 1 | 309 |
| 2 | 26,598 |
| 3 | 10,299 |
| 4 | 245,420 |
| Total | 283,853 |

The minimum SICN remains 1.234770950435885e−10; no nonpositive cell is observed. Here “source boundary” means the exact admitted surface tags 1–901,727, distinct from the 900,845-vertex surface-repair fixed mask and from any physical support, OEM or feature classification. With connectivity and all boundary coordinates unchanged, moving interior nodes cannot alter the 245,420 cells containing four boundary nodes. This is a limitation of that operation, not an impossibility certificate for other meshing methods.

The report retains at most five deterministic representatives, one minimum `(SICN, tetrahedron_tag)` per bin. The root review's exact rational-coordinate volume calculations concern **those five cells only**, not the entire mesh. Full tetrahedral face incidence/internal orientation is retained from the earlier native worker and was not independently repeated in this query. `fixed_boundary_only_nonpositive_cells=true` is vacuously true for an empty nonpositive list; it does not classify positive cells below 0.1.

The query completed with return code 0 in 14.816477665910497 controller seconds (13.856454707914963 readback seconds), 29 recorded RSS samples and maximum observed RSS 1,740,800,000 bytes. Controls were 120 seconds, 4 GiB sampled RSS and two software threads. The audited runner waits its owned child in `finally`, and the outer execution closed successfully; no independent OS PID-absence probe is claimed. No generate, optimize, mesh-write or solve call was made by this diagnostic.

## Sources, tests and preserved evidence

The [optimizer wrapper](sources/mesh_atomic_postexport_002.py) is the actual SHA-256 `28746e14a041db464c3a41b732f1fc3e9ad9fd6ce96e886f728e5409d6ea0e36`. Its [three source guard tests](sources/test_atomic_postexport_source.py) and [actual root log](optimizer/source-tests.log) are distinct from the [seven actual-function classification tests](sources/test_classification.py), [independent scalar reference](sources/poorcell_reference.py), [root test log](diagnosis/root-tests.log) and [earlier source-only peer review](diagnosis/source-peer.json). The diagnostic reader is preserved [byte-for-byte](sources/reader.py). Test records are explicitly projected to omit the selected interpreter location; actual outcomes and hashes remain unchanged.

The unchanged `61542a…` core and `e0e63b…` runner are referenced in [source-bindings.json](source-bindings.json) at the existing [raw-volume capsule](../atomic-cavity-volume-raw/README.md), along with the four shared helpers. The earlier rejected raw mesh/review download is documented [separately](../atomic-cavity-volume-raw-review-delivery/README.md). These source snapshots permit source review; this small capsule does not contain the large MSH/BIN or a portable native replay bundle.

[original-records.json](original-records.json) identifies every exact copy and explicit projection by its original/public digest and field scope. The optimizer command and duplicated embedded worker report are omitted; the separate complete checkpoint is retained. The diagnostic contract retains all 195 relative pins and replaces three absolute runtime binding keys with generic roles; private interpreter and obsolete tool-session prose are omitted. The launch projection retains all 208 binding values with the same runtime-role substitution. No executable/runtime binary, private authorization command or personal path is included. Original files and earlier capsules remain unchanged.

Only the copied standard-library integrity checker is needed to verify this sealed payload:

```sh
python3 -B verify.py
```

It checks bytes and file closure, not geometry or native computations. Code is covered by [LICENSE.project](LICENSE.project). Mesh admission, convergence, engine loads, material qualification, strength, thermal performance, process calibration, OEM fitment and manufacturing release remain unestablished by these records.
