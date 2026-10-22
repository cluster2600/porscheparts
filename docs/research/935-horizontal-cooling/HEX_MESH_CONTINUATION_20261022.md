# 935 hex-mesh continuation and user-requested pause — 22 October 2026

## Result in the software chain

This continues the [bounded local relocation](LOCAL_RELOCATION_20261022.md)
at **PicoGK geometry → independent geometry checks → fluid meshing**. The
PicoGK design master and certified analysis surface remain unchanged. The
latest real snapping run is **paused by the user**, with all owned meshing
processes stopped and the private case preserved. No complete snapped mesh,
boundary-layer result or new accepted flow calculation is produced.

The [checkpoint](hex-mesh-continuation-20261022.json) binds executed source
bytes, native runtime receipts, diagnostic measurements and private archives.
The [source snapshots](../../../twins/935-horizontal-cooling-system-f0/source/hex-mesh-study-20261022/README.md)
are preserved without rewriting their original execution paths or hashes.

## Saved hexahedral mesh and parallel control

The fresh case uses the certified SI-converted rotor from the preceding study.
Conversion still assumes 0.001 metres per uncalibrated source unit. The square
study duct is not a historical 935 housing. Surface refinement levels are
(5, 6), with a distance band at level 2. The initial recipe requests three
surface layers; their execution is not established.

The configured six-million-cell refinement limits are not a hard operating
system ceiling: intermediate refinement reaches about 6.8 million cells.
After inside-cell selection, the saved mesh has **4,666,166 cells and 6,483,943
points**. The actual resource guards are separately recorded. The serial
run reaches snapping but stops at its 1,200-second wall-time limit.

Local MPI 4.1.6 is checked with `self,vader` transports and `ob1` communication
inside the existing rootless, network-isolated Foundation 13 runtime. A fresh
analytic cube then passes four-rank decomposition, full parallel quality,
reconstruction and full serial quality. Independent readback checks all 756
faces, 343 points and 216 cells, boundary planes and closed oriented topology.
Its exact serialized volume differs from the analytic unit volume by
`5.09e-17`. This validates that control, not the real rotor mesh.

Fresh real-case preparation reuses the saved castellation and decomposes it
with four-way Scotch. Every source cell is assigned exactly once. All eight
per-rank point/cell refinement fields match the exact native addressing;
`level0Edge` is retained. The native decomposer supplies those fields, so the
documented fallback does not run. The source checkpoint remains unchanged.

Snapping creation requires minimum interpolation weight 0.05 and retains the
70-degree nonorthogonality criterion, including its relaxed block. The frozen
final quality dictionary and command remain unchanged:

```sh
checkMesh -case /workspace -allGeometry -allTopology -meshQuality
```

## Interrupted attempts and pause semantics

The first four-rank snapping attempt stops at its actual 1,200-second deadline
during morph iteration 6 of ten. A fresh attempt uses a 3,600-second deadline,
with the same mesh, isolation and quality requirements. Its workers retain a
3 GiB address-space limit each. Both stages disable recastellation and layers.

At **19:36:28 UTC**, the user requests a pause and publication on main. The
owned child process group receives SIGTERM. The unchanged runner returns
exit `-15` after **1,607.02 seconds** and writes its terminal receipt. Its
`stop_reason` remains null because its timeout branch did not run; the separate
pause-request receipt records the actual user-requested cause. Neither that
receipt nor the executed runner is rewritten to manufacture a different cause.
Independent process inspection confirms the driver, namespace and all four
workers are absent.

The second attempt also stops during morph iteration 6. Its last on-disk mesh
is the **pre-snap castellated checkpoint**. Displacement iterations recorded in
the log are not a completed snapped checkpoint and cannot be resumed as though
iteration 7 were saved. Intermediate error counts are not final quality results.
The goal remains paused; no automatic restart is authorised by this record.

## Complete wall view and precise export controls

Fresh native exports of the saved pre-snap mesh complete in 198.73 seconds.
Every copied constant/system input matches the parent's recorded hashes. The
private figure shows all **1,652,214 rotor-wall polygons**, with a blade-tip
camera crop and no display decimation. All **1,676,697 boundary vertices** are
queried against the retained analysis reference. A parallel-triangle witness
checks the distance operation.

Under the inherited scale assumption, the maximum, 95th-percentile and median
sampled gaps are respectively **0.384235, 0.292016 and 0.112323 mm**. These are
one-way vertex samples from display-precision coordinates. They do not prove
a complete bidirectional surface bound, calibrated dimensions or performance.
The image contains no pressure, airflow or stress field and remains private.

An independent cube export control distinguishes data formats. The OBJ contains
218 boundary vertices and 432 triangles, preserves the exact native boundary
coordinate set, has closed oriented topology and differs from analytic volume
by `4.45e-17`. The four VTK patch files use Float32 coordinates and six-decimal
ASCII values; maximum cube vertex error is `4.9172e-7` unit lengths. The VTK
OpenFOAM reader returns Float32 points even when 64-bit input is requested;
its complete cube-coordinate comparison measures `1.7207e-8` unit lengths.

These VTK versions are suitable for the declared inspection view. Precise
native ASCII/OBJ data must support coordinate admission; the view cannot supply
its own exact geometric evidence. The real snapped wall has no export or
complete geometric certificate because snapping is unfinished.

## Preservation and publication

Raw scans, geometry, native mesh arrays, fields and scan-derived images remain
private. Public Git contains the English report, checksummed source snapshots
and reduced metadata. The private release retains the serial checkpoint,
qualified controls, terminal attempts, complete wall exports and images.
Archive members are checked on Kali1 and the Mac, and uploaded asset sizes and
SHA-256 digests are checked against GitHub.

The pause archive preserves all 69 files of the interrupted case: five new
payloads and 64 byte-identical references to the preceding verified parallel
archive. Its manifest names every file, hash, size and parent member. This
retains the complete saved case without duplicating its large unchanged mesh.
The pause request and terminal execution receipt are new payloads. Older
archives and evidence remain unchanged. No new paid instance is created.

The publication checks source identities, pause/timeout separation, precision
limitations and admission boundaries. The focused 935 suite passes 213 tests
with four optional skips. Repository validation does not turn this
interrupted study into a fan performance or manufacturing result.

## Work remaining when the user resumes

Inspect or revise the stopped snapping case before requesting a new run. A
new flow calculation requires complete independent wall bounds, outer patch
and plane checks, volume/topology, precise native readback and the unchanged
full native quality command. Boundary layers and three-grid CFD convergence
remain pending. Physical scale, seventeen installation/drive interfaces,
hidden drivetrain, historical engine/shroud fitment, structural convergence,
fatigue and bench correlation remain open. PhysicsNeMo has no accepted fan
reference dataset, and the complete system is not fabrication-ready.
