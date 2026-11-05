# 935 checkpoint optimization and native readback diagnosis

The imported-checkpoint optimizer now passes its independently inspected cube
control after correcting Gmsh region ownership. No optimized head volume is
admitted. An instrumented repeat identifies unresolved zero node labels in the
native head connectivity, before export normalization or exact-sign evaluation.
Actual terminal states, hashes and counts are in [results.json](results.json).
This is numerical admission work on a declared hypothetical envelope, not a
new printing master, an analytic CAD solid or an engine/process qualification.

## Upstream admission and fixed contract

The [preceding study](../935-corner-provenance-20261105/README.md) supplies a
preserved raw checkpoint with 4,181,299 nodes and 13,250,576 positive tetrahedra.
Its complete boundary and opposite internal face pairs pass independent checks.
Its quality gate fails: 526,110 cells are below mean ratio 0.01 and the minimum
is 2.914590667e-12. Boundary regularization was separately admitted under a
0.009643216 mm cumulative correspondence bound to the hypothetical printing
baseline. That bound does not establish physical scan accuracy or interfaces.

This trial permits interior optimization only, with exact source vertices and
complete oriented boundary required at readback. Before head execution, the
same import path must improve a distorted unit-cube witness whose only interior
node is at (0.000001, 0.000001, 0.000001). Its 12 tetrahedra initially have
minimum mean ratio 0.000094494173. The predeclared control gate is a complete
independent cell/boundary pass and minimum ratio at least
`max(0.01, 10 * before)`. The head diagnostic target is at least 50% fewer cells
below 0.01, no increase below 0.0001, and no worse minimum. These are screening
targets, not material allowables or proof of solver convergence.

Each accepted control permits one native optimizer API call on the head:
Gmsh 4.12.1, eight threads, fixed 2 mm size field, `force=True`, `niter=1`.
The API argument is recorded without claiming the kernel performs one internal
iteration. The worker has a kernel-level 900-second alarm; the controller also
monitors wall time, 40 GiB sampled RSS and 4 GiB free disk, terminates only its
own child process group, and reaps it. Controls have a 60-second kernel alarm.
The frozen raw input and printing/support/contour deliverables are never edited.

## Correcting checkpoint ownership before optimization

The first control returns 24 cells and total cell volume 2 rather than 1.
All original 12 cells remain as a prefix, with new cells appended. Independent
internal-face inspection rejects it, so the head is not run. The second
control checks node-tag uniqueness: no duplicate tags exist and no renumbering
is applied. It reproduces the failure, rejecting node-label aliasing as the
explanation for this control.

The tagged Gmsh 4.12.1 source has a cleanup path that skips fully discrete
regions in [deMeshGRegion](https://github.com/live-clones/gmsh/blob/gmsh_4_12_1/src/mesh/meshGRegion.cpp#L191).
The [Netgen integration](https://github.com/live-clones/gmsh/blob/gmsh_4_12_1/src/mesh/meshGRegionNetgen.cpp#L318)
invokes that cleanup before transferring the optimized mesh. This matches the
observed input-cell retention in the tested discrete-region import path;
the source tag is not an attestation of every installed binary or Gmsh version.
Private copies and hashes retain the inspected primary sources.

The new adapter restores the checkpoint on a GEO-owned `Volume` referencing
the same discrete boundary. It explicitly compares every node coordinate,
tetrahedral index and boundary index before and after conversion. All arrays
remain identical. This changes entity ownership; it does not remesh or create
analytic head surfaces. The restored size field is unchanged.

With that adapter, Netgen's cube control passes every independent cell and face
check, retaining 9 nodes, 12 cells and unit volume. Minimum mean ratio improves
to 0.761952505. This demonstrates the corrected software path on the witness,
not head quality.

## Head and alternative-method outcomes

The first admitted head call returns from native optimization, but the retained
exporter rejects an exactly zero determinant evaluated as fractions of stored
binary64 coordinates. It exits after 135.737 seconds with sampled peak RSS
24,523,392 KiB, without exporting an optimized candidate. The limit is not hit.
The native log's phrase `5871353 illegal tets` is kernel terminology, not an
independent reclassification of the fully positive frozen input. That run did
not save native output tags/arrays before export; it cannot on its own locate
the failure inside the kernel or rule out readback mapping errors.

A distinct control tests Gmsh's default optimizer on the same geometry-owned
checkpoint. Independent consistency passes, but minimum mean ratio remains
0.000094494173, failing the fixed quality gate. No head call follows. Its
actual-method receipt takes precedence over the legacy exporter's retained
`Netgen` request label. This rejects that fixed one-call configuration on this
witness; it does not rule out other algorithms or justified compositions.

The instrumented Netgen repeat changes no numerical setting. Its cube passes
again. The head returns 4,845,417 uniquely labelled nodes and 15,715,680 cells,
but 33,688 cells have all four node references equal to zero. No node labelled
zero exists. The 8,218,458 boundary faces have no unresolved references. A
separate retained-label inspector confirms all counts, with a valid cube and
an injected missing-label negative control. The native capture is preserved at
SHA-256 `8b38a7f8ba81bc0ca574e127d240e6e26b46fce530c76025180cc273d4135534`.

The audit stops at unresolved references, before evaluating head cell signs.
The repeat exits after 168.861 seconds, with sampled peak RSS 22,544,784 KiB.
The original exporter's unchecked sorted-label lookup could map a missing zero
label onto the first stored node and produce an apparent zero cell. The repeat
establishes invalid native readback connectivity, not a physical degeneracy;
the unsaved first native output cannot be retroactively inspected. No missing
coordinate is inferred, and no invalid cell is deleted to obtain acceptance.
The exact cause inside native optimization or its integration remains open.

The next method must validate node references before any coordinate indexing.
A native alternative with a justified interior-relocation witness can be tested
separately; this work does not authorize relaxing complete boundary, orientation
or shape checks. Repeating the same head call without new diagnostics is not
an admission strategy.

## Phase ledger and replay

| Phase | Concrete inputs / runtime | Output / acceptance |
|---|---|---|
| Upstream audit | Frozen surface, raw MSH/NPZ and independent interval report | Diagnostic optimization only; shape quality fails |
| Discrete import control | `run_optimization.py`, distorted cube, native Gmsh | Rejected duplicated cell set; no head call |
| Numbering diagnosis | `run_numbered_optimization.py`, same witness | Unique labels; same rejection; no head call |
| Region ownership | `run_geometric_optimization.py`, exact-array adapter | Cube passes; head export rejects zero cell |
| Default-method control | `run_default_optimization.py`, actual method receipt | Consistent cube but quality gate fails; no head call |
| Native readback audit | `run_audited_optimization.py`, tags/raw output before normalization | Unique labels but unresolved zero references; head signs not evaluated |
| Independent label audit | `inspect_native_tags.py`, saved raw head/cube and injected missing label | 33,688 invalid cells; boundary labels resolve; no coordinate invention |
| Independent volume admission | Frozen interval/face inspector and complete candidate | Required after successful export; no optimized head admitted |
| Head CFD/FEA and AM | Case-specific mesh admission, loads, material and calibrated process | Still pending; no field solve or manufacturing release |

Sources are retained under [source](source/optimize_volume.py). All five drivers
provide `--help` and take the same explicit inputs: a **new** private `--root`,
`--input-msh`, `--input-arrays`, `--input-inspection`, `--surface`,
`--surface-report`, `--cube-arrays`, `--cube-surface`, `--cube-report`,
`--repository`, `--python` and `--scientific-site`. Use Python 3.12.11,
NumPy 2.5.4 and the Netgen-enabled arm64 Gmsh 4.12.1 runtime. Set `PYTHONPATH`
to that scientific site before invoking the driver, as well as passing it as
an argument; the driver itself imports NumPy. The private launcher receipts
retain exact commands. An initial instrumented launcher missing this environment
fails at import before creating a trial; that receipt is preserved too.

The [independent inspector](../935-unoptimized-volume-20261105/source/inspect_interval_volume.py)
uses the frozen [cell/face helpers](../935-local-physics-20261105/source/inspect_tetrahedra.py).
It checks complete cell orientation, source coordinates, boundary equality and
internal face pairing; it does not exhaustively test every tetrahedron pair
for intersections. Source hashes, private capsule manifest, upstream reference
hashes, unchanged input hashes and terminal states accompany the aggregate
receipt. Replay into a fresh private directory; never write into frozen evidence.

The private capsule contains 178 indexed files (274,971,919 bytes, excluding its
manifest), rehashed and made read-only after every task process terminated.
Its manifest SHA-256 is
`9ee63840ce8db33e23f50d4bdcbd8f48e5979124126bee59bb7efd7e4d932c95`.
All three original checkpoint/surface inputs are rehashed unchanged after the
trials. Only source code and aggregate receipts are published here.

No paid compute, supplier message or external CAD/AI scan transfer is created by
this increment. Existing Vast budget commitments remain counted, and the owner
permits scan transfer to Vast if a prepared workload needs it. Missing physical
data and process calibration remain explicit. The full engineering goal is active.
