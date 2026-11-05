# 935 acquired-source CAD atlas and complete record accounting

This increment expands the acquired-surface reference beyond the previous
18,682 original triangles. It accounts for all **2,466,040** original triangles:
**2,465,836** are admitted to native CAD construction and **204** are quarantined
without modifying their source records. The original scan remains authoritative.
This is a faceted surface reference, not a reconstructed functional head solid,
parametric head design, qualified fabrication file or engine release.

Checkpoint status: the exhaustive chart job is running and its completed charts
are being recovered. Whole-set FreeCAD validation has not yet completed. The
benchmarks below are actual terminal results; the full-run outcome will be
reported separately after final byte, coverage and saved-shape checks.

## Source admission before construction

The immutable decoded acquisition has 1,281,608 vertices. Its SHA-256 is
`dd94c37117a1f1277a4f2b7f0bf0023e0d1858991b943f766cf447db319a101a`;
the original OBJ contract remains
`4623d5d3b73fe3d03ca988a47543a8dd1be7834d3040e6f7efd1e1e95c766486`.
One OBJ unit is treated as one nominal millimetre by owner instruction. This is
not independently measured physical calibration.

[The complete source audit](source/audit_source_atlas.py) uses interval bounds
and exact Fraction fallback for triangle degeneracy. Literal right, thin and
collinear triangles, edge versus point contacts, inconsistent winding and
nonmanifold edge uses are controls. Eight exact degeneracies, 196 faces in the
retained original intersection index and 20 faces involving six coincident
distinct source vertex IDs give a union of 204 quarantined faces. Reason counts
overlap. These records remain in the unchanged acquisition; no welding,
smoothing, normal flipping, cap construction or defect deletion is performed.
The intersection index is inherited evidence, not a new exhaustive native
intersection certification.

The admitted acquisition has 3,748,827 source edges, 100,146 open edges and 26
edge-connected components. All 18,682 previously accepted reference triangles
remain admitted. These components are connectivity observations, not anatomical
head/accessory classifications. No unknown internal passage is invented.
The unchanged complete scan's earlier [boundary inventory](../935-faithful-replica-20261028/BOUNDARIES.md)
has 99,876 open edges. The 100,146 count applies to the admitted subset after
quarantine, before chart partitioning. It must not be reported as the complete
original scan's topology. Reconciliation fields named `original_*edges` refer
to original IDs restricted to this admitted subset.

## Exact chart construction and independent checks

A deterministic traversal of shared original edges partitions the admitted
faces into 83 charts of at most 30,000 triangles. Private original-ID provenance
records the partition. Chart boundaries are storage/construction seams, not new
physical openings or separate manufactured parts. At source point contacts, the
native representation uses separate edge-connected vertex fans at the same
original coordinates; global original vertex-contact topology is therefore not
claimed preserved in the native reference.

[The chart constructor](source/build_chart.py) reuses the frozen exact-source
builder, SHA-256
`fca5259ef3b3412a72e441fea39816e14fea4e375095e1c83def2e4117f6ae8e`.
It creates shared straight edges and planar triangular faces with original
coordinates and winding, without proximity sewing or geometry fitting.
[The separate verifier](source/verify_chart.py) reopens the actual STEP bytes
and compares them directly with the original acquisition, not the builder's
provenance map. Its frozen independent reader has SHA-256
`3a2ddf947a1083399890dc167ec631fec0bce4d5a7a564613a765fcd95158658`.

Checks require every selected original triangle exactly once, original winding,
straight source edges, exact edge adjacency, vertex fans, shell components,
valid native shapes and zero solids. Original vertex readback error must be
exactly zero. Every actual native support plane is inspected against its own
three stored vertices with a predeclared `1e-8` nominal-mm arithmetic guard.
That guard is not a physical manufacturing tolerance.

Both literal shared-square and point-contact STEP controls must pass. A square
with geometrically coincident but deliberately unsewn edges must be refused for
the expected edge-topology reason before any head chart is admitted. These
controls run on each host through the actual constructor and separate reader.

[The exhaustive controller](source/run_chart_job.py) uses four owned children
at most, separate construction and verification processes, a 2,700-second global
deadline, 615-second child limits, a sampled 4-GiB child RSS bound, 8-GiB Linux
address-space bound and 4-GiB disk floor. It stops scheduling after any failure,
reaps its own process groups and records partial results. Verified STEP bytes
are compressed and fully decompressed/rehashed before only the transient raw
copy is removed. No thresholds are swept after a refusal.

The portable [executed chart contract](chart-job.json) contains relative input
names, sizes and hashes only. Its SHA-256 is
`64ff8ec069bfd67d23bc9d516d609d6425a8a8b72e70b3187dd0fb3026c2e941`.
For replay, copy `chart-job.json` as `job.json` into a new private directory and
assemble its exact eight inputs. Copy
the four chart drivers from this directory's `source/`; copy the frozen
[builder](../935-source-shells-20261104/source/build_source_shells.py) as
`source_builder.py` and
[reader](../935-source-shells-20261104/source/verify_source_shells.py) as
`source_verifier.py`. The acquisition and audit-plan NPZ inputs are private and
must independently match the contract. Do not substitute another head's data.

Using an already qualified OCP runtime, the actual command forms are:

```sh
python -B PRIVATE_JOB/run_chart_job.py --job PRIVATE_JOB/job.json \
  --output NEW_PRIVATE_RESULTS --all-chunks --workers 4 --deadline-seconds 2700
python -B source/verify_source_set.py --prepared PRIVATE_JOB \
  --results RECOVERED_PRIVATE_RESULTS --output NEW_PRIVATE_RECONCILIATION
```

Replace the uppercase paths with new private locations; no rental is triggered
by these commands. Preserve rejected trials and their executed source hashes.

[Global reconciliation](source/verify_source_set.py) checks every recovered
manifest byte and all original IDs. It separately enumerates source edges and
requires that chart-edge sums equal original edges plus partition seams, and
chart-boundary sums equal original open edges plus twice the seams. The private
seam map preserves original edge identities. Counting chart boundaries as
acquisition holes would be incorrect.

## Editable native references

[Native document creation](source/create_source_document.py) imports verified
STEP into `Part::Feature` reference objects, saves, closes and reopens FreeCAD
documents, checking validity, topology, identity placement and evidence flags.
These are editable native reference objects with faceted BRep geometry, not a
parametric reconstruction of chambers, ports, fins and functional interfaces.
Imported reference faces cannot establish missing metrology or anatomy.

[A separate saved-document reader](source/export_saved_source_document.py)
exports the actual stored shapes without altering the documents. The same
independent original-source verifier must then inspect those exported bytes.
Successful creation/reopening or topology counts alone are insufficient.
[The bounded local set controller](source/run_native_chart_set.py) uses one
document per chart to limit native import memory, with four workers, 600-second
child limits, sampled 4-GiB RSS and a 7,200-second whole-set deadline. A document
set is not a globally sewn head or evidence that a monolithic import is feasible.

## Actual preparation benchmarks

Before renting, the first 30,000-face chart passes actual construction, separate
native STEP inspection, controls and lossless compression on both Mac and
Kali1. Elapsed time is 42.657 seconds on Mac and 54.235 seconds on Kali1. This
is a compatibility/resource witness, not a cloud speedup or GPU benchmark.
The Mac uses Python 3.12.11, NumPy 2.5.4, SciPy 1.18.1 and OCP 7.9.3.1; the
pinned Linux image uses Python 3.12.3, NumPy 2.5.2, SciPy 1.18.1 and OCP 7.9.3.1.
Its native OCP core SHA-256 is
`be0e408a1f401acf441ba4048742e0accdfbd51c35ffbe113cdd27e8c5a90448`.
Different STEP serialization hashes across runtimes do not imply geometric
agreement; the independent original-source comparisons establish that agreement.

Kali1 runs the real workload in an existing pinned image, with no network,
read-only root, dropped capabilities and bounded CPU/RAM/PIDs. All outputs are
recovered and hash-verified. A cleanup refusal caused by the read-only prepared
directory is retained; the corrected cleanup verifies task ownership, input
hash and owned-container absence before changing only owned temporary directory
modes and removing that directory. No scientific trial is replayed and no
foreign resource is removed.

The Linux image has no FreeCAD module or executable. A separate actual Mac
FreeCAD 1.1.4 trial, confined by the existing local-only network policy, creates,
saves, closes and reopens the first chart in 81.681 seconds, peaking at sampled
RSS 1,420,416 KiB. A new process reads its saved document and exports the stored
feature in 9.078 seconds. Separate OCP inspection of that actual saved feature
finds zero original-vertex error and maximum support-plane residual
`1.566194936575611e-11` nominal mm. This single-chart trial does not qualify
whole-head native import capacity or functional manufacture.

## Stack and release boundary

This extends the existing STEP/FreeCAD scan-reference branch in
[the engineering architecture](../../architecture/README.md) and
[scan workflow](../../architecture/scan-repair-workflow.md). PicoGK retains new
engine geometry authority; local Qwen/CADAM remain auxiliary proposal services.
Gmsh/OpenFOAM/CalculiX/Adamantine keep their prescribed roles. No external AI or
CAD service receives the scan. Owned Kali1 and the owner-authorized temporary
Vast host may process private acquired geometry; public Git retains source code,
hashes, aggregate receipts and limitations, not scan/STEP/native-document bytes.

The complete physical goal remains open: specimen identity and metrology,
accepted functional interfaces and component separation, missing surfaces and
hidden passages, faithful head-solid reconstruction, admissible meshes and
correlated engine loads/physics, material/process/support/toolpath qualification,
physical builds and inspection, professional review and engine validation.
Hypotheses stay explicit. Reference coverage never changes G0–G5 or authorizes
manufacture. The supplier draft remains unsent.
