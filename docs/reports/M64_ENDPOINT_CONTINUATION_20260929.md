# M64 — endpoint reconstruction and local mesh sizing, 29 September 2026

## Retained engineering state

Continuation of the [local reconstruction trials](M64_LOCAL_RECONSTRUCTION_20260928.md).
The retained volume result is **32 tetrahedra below minSICN 0.1 / 1,341,461**.
The reference CAD has not been replaced. This remains a 935 scan-derived
research body, not a metrologically qualified M64 head. All geometric lengths
below are provisional scan units, not certified millimetres or a printer
specification. No physical, material or manufacturing gate is closed.

**Earlier experiment, 1 October:** local conforming surface subdivision reduces
the maximum sampled shape error from **0.0948743 to 0.0723482 scan unit**, with
zero incompatible surface triangles. It still fails the 0.040-unit screen;
the CAD master and retained volume are unchanged. Details and rejected controls
are recorded below.

**Earlier result, 2 October:** native-curve-aware refinement and one local
error-driven pass produce **933,562 surface triangles**, zero incompatible
triangles and a maximum sampled deviation of **0.0665857 scan unit**. The
0.040-unit shape screen still fails. A second local pass is rejected because
one child fails the orientation guard relative to its parent; it is not promoted.

**Earlier continuation, 2 October:** the fixed-diagonal defect is corrected and
three further passes finish without orientation or quality rejections. The
best sampled maximum is now **0.0642802 scan unit**, with **938,982 surface
triangles**. It still fails 0.040; the retained volume and physical gates remain
unchanged. The frozen-code full `make check` now passes on Kali2, including
the previously blocked pinned Docker test. See the final section below.

**Earlier result, 2 October:** all-exceedance selection and guarded polygon
triangulation lower the sampled maximum to **0.04959299 scan unit**, about 23%
below 0.0642802. The lower patch passes both sampled directions; the upper
patch retains **56 native samples above 0.040**. A subsequent pass is rejected
for one orientation failure. This remains a surface experiment, not the
physical 0.040 mm goal or a manufacturing release. The retained volume still
has 32 rejected tetrahedra.

**Latest result, 2 October:** native-feature-constrained projection removes
the remaining orientation rejection. Both reconstructed patches now pass
the **sampled 0.040 scan-unit screen**, with a maximum of
**0.03984823204**, 992,724 triangles and zero necessary surface rejections.
This is not a continuous error bound, the physical 0.040 mm requirement, or
volume/printing qualification. The retained volume is still unchanged. See
the final native-feature section for the measured result and remaining gates.

**Later recovery, 1 October:** both authorised Linux hosts are reachable again.
The previously uncollected size-0.1 run completed but has **5 incompatible
triangles / 976,144**; the curvature-64 run ended at its 1,800-second alarm.
Neither result replaces the retained geometry. See the recovery record below.

![Two lateral openings and four recesses of the retained boundary](../media/m64-openings-20260929/openings.png)

The requested close-up is rendered from the exact retained mesh, without
smoothing, decimation, invented internal channels or generative imaging.
Left and centre: opposite lateral openings. Right: four visible recesses,
with separate valves absent. These openings are not the 32 rejected volume
elements. The displayed facets and irregularities have not been cosmetically
removed. Geometric views alone do not establish their functional qualification.
The [source licence and provenance](../../catalog/sources/src-wolfe-classics-935-billet-cylinder-head-scan.json)
remain attached; the image is research documentation, not a released product.

## Fix the construction contract before adding compute

The previous filling helper supplied exterior edges in map order. A new
regression test demonstrates that consecutive edges did not form the continuous
oriented wire required by the [OCCT filling API](https://occt3d.com/dev/doc/refman/html/class_b_rep_offset_a_p_i___make_filling.html).
The test failed before the correction and passes afterwards.

The corrected shared helper traverses exact topological vertices, requires
degree two and one closed loop, or rejects the input. It uses no coordinate
welding, relaxed tolerance or deleted edge. The boundary is copied together
so its shared vertices survive; original constraints remain untouched. The
real lower and upper patches have respectively 18 and 13 ordered edges.
A disconnected two-loop witness is now rejected.

This is a real software-contract fix, **not the cause of the head's entire
reconstruction failure**: four repeats still fail with the same native results.
An additional initialization uses the original plane (142 below, 1412 above).
Only a plane is admitted, ensuring orthogonal local coordinates as required by
the same API; this is an initial surface, not permission to flatten the part.

| Trial | Maximum reported G0 error | Decision |
|---|---:|---|
| Lower, ordered boundary only | 0.1981524648 | Invalid patch; reject |
| Lower, ordered boundary + 33 interior constraints | 0.0710922485 | Invalid patch; reject |
| Upper, ordered boundary only / interior constraints | No completed patch | Both rejected |
| Lower, native plane initialization, boundary only | 0.1552171844 | Invalid patch; reject |
| Lower, native plane initialization + 33 interior constraints | 0.0206819153 | Invalid patch; reject |
| Upper, native plane initialization, both settings | Native `Standard_Failure` | Both rejected |

The lower error reduction does not meet the unchanged **1e-7 boundary
construction guard**. It is not a 0.020 or 0.040 engineering result. No patch
above reaches sewing, volume meshing or thermal testing. All eight execution
receipts finish without a timeout and preserve their input file hashes.

## Meshing experiments

The previous finer-curvature run ended at its 540-second alarm. A fresh Linux
run keeps the same geometric recipe (curvature 64, junction size 0.020,
compound factor 1, reclassification 1) with an explicit 1,800-second wall limit.
This is a new calculation, not a checkpoint resume. An initial packaging
attempt failed at import because a helper dependency was missing; it produced
no mesh. The retry includes the tracked Python dependency tree.

Two other runs use the documented [Gmsh restricted sizing field](https://gmsh.info/doc/texinfo/#Gmsh-mesh-size-fields)
on the eight original compound faces and their boundaries: size 0.2 or 0.1,
curvature 12, factor 1. This differs from refining only within a narrow distance
of six internal curves. Geometry, minSICN thresholds and admissibility checks
are unchanged. A two-square numerical witness checks that the selected square
is refined while a separate control is not, and checks actual triangle edge
lengths; API option assignment alone is not counted as a test.

The size-0.2 Linux run completes in **490.37 s**: **587,912 triangles**, zero
incompatible triangles, minimum q2 **0.07085403530**, no duplicate triangles
and no edges without incidence two. This is not a complete manifold or
intersection check. The unchanged bidirectional shape audit rejects it:

| Patch | Mesh to native, sampled maximum | Native to mesh, sampled maximum |
|---|---:|---:|
| Lower | 0.06544985810 (319,421 samples) | 0.08310593681 (1,781 samples) |
| Upper | 0.06037308328 (25,787 samples) | 0.09487428993 (1,987 samples) |

The largest observed error exceeds the exploratory **0.040 scan-unit** screen.
This is neither a certified Hausdorff bound nor physical millimetres. No
volume is generated from this rejected approximation.

Initially on 1 October the two remaining Linux outcomes (size 0.1 and curvature
64) could not be collected: the known SSH host returned `No route to host`.
They were recorded as **uncollected**, without assuming completion or continued
execution. The later recovery below supersedes that collection status.

## Reproduction

Use the existing isolated OCP 7.9.3.1 / Gmsh 4.15.2 environment and private
inputs; the compound jobs use the existing authorized Linux host.

```sh
python twins/m64-cylinder-head/source/wholebody/trial_constrained_patch.py \
  --body /private/original.brep --patch lower --grid 5 --initial-plane \
  --output /private/fresh-plane-trial
python twins/m64-cylinder-head/source/wholebody/trial_compound_junction_mesh.py \
  --body /private/original.brep --classify 1 --factor 1 --patch-size .2 \
  --curvature 12 --wall-seconds 1800 --output /private/fresh-patch-mesh
python twins/m64-cylinder-head/source/wholebody/trial_project_compound_surface.py \
  --body /private/original.brep --mesh /private/fresh-patch-mesh/surface-private.msh \
  --receipt /private/fresh-patch-mesh/report.json --split-interior-edges \
  --output /private/fresh-refinement
python twins/m64-cylinder-head/source/wholebody/audit_compound_shape.py \
  --body /private/original.brep --mesh /private/fresh-refinement/surface-private.msh \
  --receipt /private/fresh-refinement/report.json --wall-seconds 1200 \
  --output /private/fresh-refinement-shape.json
python -m unittest discover -s tests -p test_m64_constrained_patch.py -v
make check
```

Original/rejected private geometry and historical receipts are not overwritten.
Producer snapshots preserve revisions used before subsequent code changes.
No new paid instance is rented, no catalogue release is edited, and no site is
deployed by this continuation.

The six focused numerical tests pass without skips in the qualified runtime.
The initial repository check passes its **3,206-test main suite (161 optional
skips)** but stops at the report-index check because this new report was added
during execution. After regenerating the index, the final 29 September
`make check` completes with exit **0** in **232.87 s**.

## 1 October: correct the approximation without moving the master

The Mac runs a fresh bounded size-0.1 experiment. It is not a recovered Linux
result. One initial local attempt is explicitly stopped after 143.07 s (exit
-15) because a source helper was edited during execution. It is not accepted
as evidence. The replacement uses a separate frozen copy of the producer.

The [local projection trial](../../twins/m64-cylinder-head/source/wholebody/trial_project_compound_surface.py)
loads the completed size-0.2 surface and its hash-bound face correspondence.
For each of the two compounds, it selects only nodes unused by every other
surface. Those interior nodes are projected to the closest point of the
original **trimmed** CAD patch. Shared boundaries and every other node stay
exactly fixed. No native surface, mesh connectivity, element count, threshold
or original file is modified. Each displacement must remain at most 0.1
provisional scan unit; this is a bounded experimental guard, not an approved
design tolerance. No smoothing, welding or triangle deletion is used.

The first complete projection takes **53.82 s**:

| Patch | Projected interior nodes | Maximum displacement in scan units |
|---|---:|---:|
| Lower | 51,761 | 0.000124994187 |
| Upper | 3,968 | 0.000355636954 |

All **587,912 triangles** remain, with zero below the necessary q2 limit and
the same minimum **0.07085403530**. No triangle has a nonpositive old/new normal
dot product. Protected node coordinates, native in-memory geometry, source
hashes and binary mesh readback pass their exact checks. These are necessary
checks only: vertex links, self-intersections and physical face roles remain
unqualified. No full-volume or physics run is authorised by this result.

The separate bidirectional audit **rejects** this projection-only surface:

| Patch | Mesh to native, sampled maximum | Native to mesh, sampled maximum |
|---|---:|---:|
| Lower | 0.06544737408 | 0.08308649403 |
| Upper | 0.06037322241 | 0.09490790456 |

The native-side maxima occur on source faces **141** and **1411**. Moving
existing nodes leaves the excessive error essentially intact. This supports
the diagnosis of facets bridging the local shape between nodes, rather than
material drift or a physically measured displacement. The original and
projection-only audits complete in 157.05 and 143.44 s respectively, with
unchanged bound inputs. Their native sample sets and mesh connectivity match;
the mesh-side sample coordinates change with projection. Neither passes the
unchanged 0.040-unit screen.

A second bounded option splits **interior** patch edges once and projects
their new midpoints onto the same trimmed native patches. Exterior edges
remain unsplit and fixed. Conforming 1/2/3-edge subdivision patterns avoid
T-junctions without moving neighbouring surfaces or dropping a region. This
is surface-discretisation repair, **not a new editable B-Rep**. The full
exported surface remains capped at two million triangles.

It completes in **61.50 s** and produces **927,696 triangles**, still zero
below the necessary q2 limit and minimum **0.07085403530**. Lower/upper patches
grow to **420,725 / 33,224 triangles**, adding **157,495 / 12,397 nodes**.
There are no flipped normal-dot checks, duplicate triangles or edges without
incidence two; binary readback is exact and bound inputs remain unchanged.
The denser bidirectional shape audit completes in **127.27 s**:

| Refined patch | Mesh to native, sampled maximum | Native to mesh, sampled maximum |
|---|---:|---:|
| Lower | 0.04556742862 (1,264,391 samples) | 0.06168744117 (1,781 samples) |
| Upper | 0.05012542051 (100,169 samples) | 0.07234822226 (1,987 samples) |

The largest recorded deviation decreases from **0.0948743 to 0.0723482 scan
unit**, about **23.7%**. Native sample locations are unchanged; mesh-side
sampling is denser, so its sets are not identical. The exploratory
0.040-unit screen still **fails**. The original retained volume remains
**32 rejected tetrahedra**, and no volume is generated from this candidate.

The new worst native-side witnesses lie on faces **142** and **1411**. The
upper witness's nearest triangle includes an **unsplit compound-exterior
edge**, length 0.1961929 scan unit (patch edge incidence one); its other two
edges have incidence two. All three edges of the lower witness triangle
have incidence two. This identifies a boundary-resolution limitation for
the next experiment; it does not prove that one edge is the unique cause.
Further work must cover the shared curve and its neighbouring surface
conformingly, not repeatedly refine the interior while silently moving a
fixed interface. Native CAD, functional-face roles, vertex-link topology,
self-intersections and physical tests remain separate gates.

```mermaid
flowchart LR
    A["Size 0.2 compound: 0.0948743"] --> B["Project existing nodes: 0.0949079; reject"]
    B --> C["Split interior edges: 0.0723482; reject"]
    C --> D["Next: shared-curve and neighbour resolution"]
    D --> E["Shape + topology + volume gates before physics"]
```

These labels are sampled scan-unit deviations, not millimetres or certification.

The fresh Mac size-0.1 run is stopped after **989.32 s**, exit **-15**, when
available disk space drops to approximately **120 MiB**. It has no completed
mesh or quality result. No unrelated files or processes are removed. The
first 1 October `make check` exits **2** after **283.69 s** with actual
`OSError: [Errno 28] No space left on device` failures in temporary-file
creation. This environmental failure is not hidden by the passing targeted
tests; repository-wide success still needs a completed retry.

The shape auditor now retains the actual worst sampled point and its closest
counterpart in the **private** receipt, including the native source-face
index in the native-to-mesh direction. This supports locating a defect instead
of only quoting one maximum. It retains the original sampling density and
0.040-unit screen. It also binds its helper hashes and writes an explicitly
incomplete progress receipt. A first 300-second local audit reaches its child
alarm (exit -14); a frozen retry uses a 1,200-second bound. The native target
is loaded once into the closest-point solver for each batch; the distances
are still native closest-point calculations, not an AI surrogate.

Eight focused tests pass in the actual OCP/Gmsh/VTK runtime. They include a
trimmed-plane projection witness with fixed boundary, unchanged input,
oversized-shift rejection, and a triangle-interior closest-point witness.
Subdivision witnesses cover all four split patterns, positive orientation,
area conservation, exact exterior edges and non-manifold-edge rejection.

The final 1 October retry passes the **3,208-test main suite (163 optional
skips)** and the subsequent Python checks, then stops because the Docker daemon
socket is unavailable at the pinned F37 LPBF audit target. Thus the **whole
`make check` is not green**, despite the passing main suite and eight separate
CAD-runtime checks. Strict documentation validation reports **zero broken links
across 573 Markdown files**; diff whitespace checks pass. No new Vast spending,
automatic Docker restart, main-branch merge, catalogue release or site deployment
is performed. All local numerical workers from this continuation have ended
or been explicitly stopped; Linux outcomes were still unknown at that checkpoint.

## 1 October: Linux result recovery after network restoration

Both authorised x86_64 hosts now answer authenticated SSH. Kali1 is reached
through Wi-Fi, checked against its existing trusted host key; host-key checking
is not disabled and no trusted key is replaced. Each host reports 12 logical
CPUs and about 15 GiB RAM, not a large-memory GPU workstation. Kali1 has about
379 GiB free disk and Kali2 about 302 GiB at collection time.

The nine existing result, baseline and log files are copied into fresh private
storage. All nine local SHA-256 values match their remote originals. These are
recovered 29 September calculations, **not new 1 October simulation runs**.

| Recovered trial | Execution | Result and decision |
|---|---|---|
| Patch size 0.1, curvature 12 | Exit 0; 1,760.64 s | 976,144 triangles; 5 incompatible; minimum q2 0.035495665. Reject. |
| Curvature 64, junction 0.020 | Exit -14; 1,800.19 s | Child SIGALRM; incomplete receipt; no final mesh. Reject. |

The second launcher receipt says `timed_out: false`: its outer timeout did not
fire, but the child reached its own alarm. This is not a completed calculation.
The first receipt binds the unchanged original CAD and copied surface hash;
it reports no duplicates and no edges without incidence two. Vertex-link and
self-intersection checks remain absent. No shape-screen pass or new volume
result is inferred. The retained volume remains **32 rejected tetrahedra**.

Recovered report hashes are
`b4b626537e3ca0f04c4a3cc12be3b6e2036f21d7141f030f2d7df1061ee9c136`
(size 0.1) and
`1879938033a74fcc33a8b6e2bce0df8317517e1ea0945fbe8719ec9b3c8f8957`
(incomplete curvature 64). The size-0.1 surface hash is
`77c2f3641ea63a7bb740877f33883a72fe6bd96c349e35d6a39586eaa8e1f91c`.
Raw geometry and coordinate-bearing receipts stay private. The next geometric
experiment still needs conforming shared-curve and neighbouring-face correction;
repeating the global size-0.1 recipe is not justified by this rejected result.
No new calculation, rental, manufacturing release or master replacement is
claimed by this recovery.

## 2 October: shared native curves, neighbour control and local error refinement

The [projection tool](../../twins/m64-cylinder-head/source/wholebody/trial_project_compound_surface.py)
now supports `--split-interior-edges --split-shared-boundaries`. One midpoint
per selected shared mesh edge is used on **both** incident surface triangles.
The midpoint is projected to the common native **edge**, identified by OCCT
topological identity, not independently to either face. Existing edge endpoints
must already lie within 1e-6 scan unit of that common curve; measured maximum
here is **9.27e-14**. Original nodes are retained at this boundary stage.

Four frozen-source experiments run on the existing Kali1 CPU, with the pinned
OCP 7.9.3.1 / Gmsh 4.15.2 runtime. No GPU surrogate or rental is involved.
Each projection run has a 600-second child alarm, and each separate shape
audit a 1,200-second alarm. The original native body remains hash-identical.

| Experiment | Surface triangles | Incompatible triangles | Minimum q2 | Outcome |
|---|---:|---:|---:|---|
| Split every shared boundary | 933,118 | 4 | 0.05084775103 | Reject: quality and shape |
| Retain exact straight shared curves | 932,176 | 0 | 0.07085403530 | Necessary surface screen passes; shape fails |
| Refine around measured worst samples | 933,562 | 0 | 0.07085403530 | Necessary surface screen passes; shape still fails |
| Repeat at newly measured worst samples | 935,576 | 0 | 0.07085403530 | Reject: one nonpositive normal-dot check; no further shape audit |

The first run splits **2,711 shared edges** and finishes in **83.28 s** including
the supervisor. Four degraded triangles occur on neighbour faces 136, 273 and
276. Their common native curves are single exact `GeomAbs_Line` edges: extra
chord subdivision brings no curvature benefit. The revised rule retains those
straight boundaries after the same endpoint check; it does not relax any quality
threshold or move a native feature. The second run splits **2,240 curved edges**,
retains **471 straight edges** and finishes in **44.82 s**.

![Actual local triangles before and after retaining an exact straight boundary](../media/m64-boundary-20261002/comparison.png)

This is a local planar projection of the same actual neighbouring face in the
two experimental meshes, not a new whole-head product rendering. The displayed
minimum is **local**, not the whole-surface minimum in the table. The original
[scan provenance and non-commercial research licence](../../catalog/sources/src-wolfe-classics-935-billet-cylinder-head-scan.json)
apply. The [renderer](../../twins/m64-cylinder-head/source/wholebody/render_boundary_refinement.py)
checks input hashes; no smoothing or generative geometry is used. Image SHA-256:
`353a9678f16ed43bd89064c01847f94c2019e2d6121d8b1d08b29b99056c0027`.

**The boundary experiment does not solve shape fidelity.** Both completed shape
audits give lower-patch mesh/native maxima **0.04556742862 / 0.06168744117** and
upper-patch maxima **0.05012542051 / 0.07235533342**. These are essentially the
previous result (0.07234822226 maximum), not an improvement to advertise.
The two audits finish in **298.95 s** and **202.25 s**, with unchanged inputs.

Consequently, the third experiment uses `--local-shape-witnesses` with the
completed, hash-bound parent audit. It selects triangles with a vertex within
**0.4 scan unit** (two original 0.2 edge sizes) of either directional worst
sample, then splits only edges interior to that local selection. Local-selection
and compound-exterior polygons stay fixed; both incident triangles use each
new midpoint. It selects **275 lower / 226 upper triangles**, adds **384 / 309
nodes**, and finishes in **27.26 s**. This is adaptive surface approximation,
not native CAD reconstruction. Its complete shape audit finishes in **162.11 s**:

| After one local pass | Mesh to native, sampled maximum | Native to mesh, sampled maximum |
|---|---:|---:|
| Lower | 0.04549009729 | 0.05906187524 |
| Upper | 0.04847518443 | 0.06658567954 |

The maximum decreases about **8.0%** from the curved-boundary parent, while the
necessary quality screen remains unchanged. It still fails the exploratory
0.040-unit screen. This motivates a bounded follow-up on the newly measured
worst samples, not an extrapolated success or a physical millimetre claim.

The follow-up allows at most three further passes, but **stops after its first
attempt**, in 27.17 s: one child has a nonpositive normal dot product relative
to its parent, in the upper patch. Quality q2 alone does not detect this failure. The rejection
is retained and neither its shape audit nor the two unused passes are launched.
The best shape-audited candidate therefore remains the first local pass above.
The next correction must control projection across the native crease/patch
charts and preserve orientation, instead of blindly adding more subdivisions.

The first three completed mesh exports preserve edge incidence two, have no duplicate
triangles or nonpositive old/new normal dot products, and read back exactly.
These checks still do **not** establish vertex-link manifoldness, absence of
geometric intersections, functional facewise boundary conditions or a volume.
The modified 2D boundary is not a regenerated native 1D curve-element mesh.
**No candidate is passed to volume meshing or physical solvers.** The retained
volume still has **32 rejected tetrahedra / 1,341,461**.

Ten focused tests pass on Mac and Kali1, including a curved cylinder/cap edge
shared by two surfaces, an exact straight-edge control, unchanged old vertices,
two-sided edge incidence, missing-native-edge and non-manifold rejection, and
the local witness selector. The first full `make check` passes 3,209 main tests;
the final retry passes **3,210 main tests (165 optional skips)** and subsequent
Python checks, but the pinned F37 Docker target cannot connect to the Mac daemon.
Thus whole-suite success and merge readiness are **not** claimed.
The final receipt-binding guard is exercised afterwards in the focused Mac
runtime: an audit bound to the wrong parent receipt is rejected before output
creation. Frozen job sources and historical receipts are not overwritten.

Private report hashes: all boundaries
`1c10c15c723671e30db68cc8a266c0d89534e193c2ebee5fbfd025567b3f127c`;
curved boundaries
`50a4a2e3efab515a32c33183975ec4b55988f93e5448495e4345449095cbd15f`;
local witness refinement
`c4515f7ac1e3f3d2aad1856e67901911256ab8eff2f22059929af53989d84d88`.
The rejected second-local-pass report hash is
`99d5e0fa70a10cf718b2585a4d34e4fc51bd3b7ecf7b5eebf417904d9ea05853`.
Detailed geometry, coordinates and receipts stay private; the public report
records measured outcomes without a manufacturing or physical 0.040 mm claim.

## Orientation-preserving diagonal correction, 2 October

The rejected second local pass was reproduced from its hash-bound parent.
The failing parent has two split edges. The old splitter always chose the
same quadrilateral diagonal, even after the new edge midpoints were projected
onto the native surface. That fixed diagonal produces a child with a negative
normal dot product; **the other diagonal preserves orientation using exactly
the same five vertices**. This is a triangulation defect, not evidence that the
native CAD needs to be flattened or its feature removed.

The shared `split_edges` helper now tries the alternative only when the
default fails and all alternative children have positive parent-normal dot
products. Both interior and shared-boundary callers supply the projected
coordinates. No vertex moves, quality thresholds, CAD tolerance changes,
triangle deletion or post-hoc reversal are introduced by this choice. If both
diagonals fail, the original failure remains visible to the rejection gate.

The regression covers cyclic indexing, reversed parent winding, conserved
five-edge polygon boundary, signed polygon area and the case where neither
diagonal is acceptable. All **11 focused tests pass on Mac and Kali1**.

![Real exported local triangles before and after the diagonal correction](../media/m64-orientation-20261002/comparison.png)

Both panels show triangles read back from the rejected and corrected exports,
projected onto the same parent plane. The five vertices match within 1e-10
scan unit. Red means negative parent-normal dot product in this local view;
this is not an independent global intersection test. The image neither changes
the head silhouette nor depicts a complete, qualified product. The research
[source licence and provenance](../../catalog/sources/src-wolfe-classics-935-billet-cylinder-head-scan.json)
still apply. Image SHA-256:
`01b6280db6983bc101af6749d85bec1a3ade5591a22d73996fb288ebab31f26c`.

The corrected second pass finishes in **27.12 s**, with **935,576 triangles**,
zero incompatible triangles and zero nonpositive normal dot products. The
necessary surface checks pass, including exact export readback, fixed protected
nodes, two-sided edge incidence and no duplicate triangles. Its completed
shape audit takes **138.85 s** and measures a maximum **0.06558267613 scan unit**.
This is still above the unchanged exploratory 0.040-unit threshold.

Two further bounded passes also complete; all three retain min q2
**0.07085403530**, zero incompatible triangles, zero nonpositive normal dot
products, exact readback, unchanged inputs and all necessary surface checks.

| Local pass | Surface triangles | Lower mesh/native maximum | Lower native/mesh maximum | Upper mesh/native maximum | Upper native/mesh maximum |
|---|---:|---:|---:|---:|---:|
| 2, corrected | 935,576 | 0.04496372435 | 0.05637440169 | 0.04723165871 | 0.06558267613 |
| 3 | 937,484 | 0.04483763451 | 0.05537201348 | 0.04348361352 | 0.06505214650 |
| 4 | 938,982 | 0.04425521458 | 0.05421935354 | 0.04214043246 | 0.06428019459 |

Passes 3 and 4 take **36.60 / 41.27 s** to build and **161.18 / 166.89 s**
to audit shape. The chain reaches its three-pass bound normally. No worker
remains running. The maximum is about **3.46% below the first local pass**;
all four directional maxima still fail 0.040. The native sample set is fixed,
but its worst sample changes on each pass (upper indices 797, 781, 1262).
The next experiment should capture and refine multiple above-threshold error
regions together, rather than assume that one worst-point neighbourhood closes
the shape gate. No unsampled-extrema or Hausdorff bound is established.

**Verification runtime:** the first Kali2 full-suite attempt exposes incomplete
user-site OCP imports and group-writable temporary source metadata. A second
attempt isolates system Python but still fails metadata guards; its restrictive
umask also invalidates a fixture that deliberately needs a public directory.
These failures are retained. Only the job's temporary checkout permissions and
process environment are corrected: sources are not group/world writable,
`umask 022`, `PYTHONNOUSERSITE=1`. No installed packages or account permissions
are changed, and no rejection check is weakened.

The resulting **`make check` exits 0**, with **3,218 main tests, 158 optional
skips**, and all subsequent Makefile checks. Native OCP coverage is supplied by
the separate 11-test qualified Mac/Kali1 runs, not claimed for skipped tests.
The F37 Docker target uses the exact project-pinned image digest and passes
15 tests (also passed in a separate run). These are software/fixture tests,
**not a printing simulation of this new candidate**. Final documentation links
and report-index checks are rerun after the report and picture are added.
Full-suite log SHA-256:
`9cc2276dc28c75a12858eee149d55744633c801b2ac32a94b4ef4537406c808a`.

No geometry is promoted to the master, and the retained volume still has
**32 rejected tetrahedra / 1,341,461**. Vertex-link manifoldness, global geometric
intersections, native 1D mesh consistency, functional boundary conditions,
accepted volumetric meshes and the subsequent physical/manufacturing campaign
are not established by this correction. No cloud rental, CFD/FEA execution,
GPU inference, thermal result or physical 0.040 mm claim is made.

The source bundle is frozen before these executions:
`63265d070f0fbd945453f4beac06067b9419d85994dea93bddf81a8b1d1bf502`.
Corrected second-pass mesh SHA-256:
`a1ed658a240723e3827df9980486ddee357af0053dfb2e832556361d95c5b0bd`;
receipt SHA-256:
`76d9db6c38ec7cc1c8312df57a4a10b6425652c870225e178f5070c57731af2c`.
Fourth-pass mesh SHA-256:
`05f4fc09970dfc02651787bc0488bcb37fc8aebf960f8c11ffa51439baa021e0`;
receipt:
`dc81056c9cc04917b27ad154b61f4fbc4542a1817a5c3b49195a42fa7b16a771`;
shape audit:
`555355ed13606d7ca6f114fb4c8c4697cd0fa574d620341fa57876d1ddc77a1a`.
The recovered result archive matches the remote SHA-256:
`094183479a1250ca57b03349b5359547ea7b7a3e2d00fce551730be4c649e2cb`.
Raw meshes, geometric witnesses and numerical job receipts remain private.

## All-exceedance refinement and concave split boundaries, 2 October

The shape audit now retains every **sampled** point above 0.040, in each
direction, rather than only its maximum. Each collection is capped at 20,000
points and exceeding that cap fails, without truncating the data. Existing
callers of the distance helpers retain their previous behaviour unless they
request this collection. A fresh baseline audit reproduces the previous
maximum **0.06428019459238127** exactly and records:

| Patch | Mesh-to-native samples above 0.040 | Native-to-mesh samples above 0.040 |
|---|---:|---:|
| Lower | 19 | 123 |
| Upper | 3 | 132 |

These are **277 sample records**, not 277 distinct physical defects. Unmeasured
points remain unbounded. `--all-shape-exceedances` requires a completed,
body/mesh/receipt-bound audit with finite, threshold-labelled collections.
An empty collection paired with a maximum above 0.040 is rejected. The existing
0.4-radius vertex-neighbourhood rule is retained. SciPy's installed `cKDTree`
replaces the dense triangle-by-witness distance array, avoiding its memory
growth when many witnesses are used. A patch with no recorded exceedance is
not subdivided. The unchanged two-million-triangle cap still applies.

### Rejected control and root cause

The first all-exceedance pass selects **7,528 lower / 4,877 upper triangles**
and adds **10,782 / 7,172 nodes**. It finishes in **36.03 s** with 974,890
triangles, but fails: **15 nonpositive child-normal dots and two triangles
below the quality threshold**, minimum q2 **0.06832676524**. It is retained
as a rejected control; no shape audit or subsequent pass is run from it.

Reproduction locates all 15 orientation failures in triangles with **three**
split edges. Their projected midpoints form a concave six-vertex boundary;
the standard central-triangle split folds despite adequate unsigned q2. The
two quality failures have two split edges. Trying alternative vertex fans on
the same polygons resolves all 17 local cases without moving any point.

The shared splitter therefore retains the standard subdivision whenever it
passes. Otherwise, for a five- or six-vertex boundary, it selects the best
admissible vertex fan by minimum q2. Every child must have a positive
parent-normal dot product. The sum of projected positive fan angles must be
less than 2π, excluding a fan that wraps around its apex. The boundary sequence,
all midpoint indices and child count are preserved. If no alternative passes,
the full-mesh rejection gates remain decisive; this is not triangle deletion,
coordinate smoothing or tolerance relaxation.

Twelve focused tests pass in the qualified Mac and Kali1 runtimes, including a concave
six-vertex witness, rotated/reversed parent indexing, signed polygon area,
boundary incidence, multi-region selection, invalid collections and exact
threshold handling. This local triangulation check does not establish global
intersection freedom, functional face labels or physical validity.

### Completed outcomes and remaining obstruction

The corrected all-exceedance pass completes in **31.89 s**, with the same
**974,890 triangles**, zero quality rejections, zero nonpositive normal dots,
minimum q2 **0.07085403530**, unchanged protected nodes and inputs, exact
readback, two-sided edge incidence and no duplicates. Its shape audit takes
**173.67 s**:

| Patch | Mesh-to-native maximum | Native-to-mesh maximum | Remaining above-threshold sample records |
|---|---:|---:|---:|
| Lower | 0.03782211596 | 0.03984823204 | 0 / 0 |
| Upper | 0.03303451901 | 0.04959299060 | 0 / 56 |

The next pass correctly skips lower-patch subdivision and selects 6,061 upper
triangles, adding 8,917 nodes. It completes in **37.24 s**, with **992,724
triangles**, no quality rejections (minimum q2 0.06913127978), but **one
nonpositive normal dot product**. It is rejected. Its shape audit and the
unused third follow-up are not launched.

Reproduction isolates a six-vertex upper-patch boundary which crosses itself
when projected onto its parent plane. The existing fan alternatives cannot
repair that boundary without changing a projected vertex. A separate,
array-only diagnostic tests intersections along averaged adjacent-triangle
normals, retaining the original CAD and the 0.1 displacement bound. All 8,917
rays intersect, but the result worsens to **28 orientation failures and four
quality failures** (minimum q2 0.03963196440). Seven nonempty subsets of the
three problematic new vertices are then tested with this ray alternative;
all still have one or two orientation failures. **Neither ray method is
added to the production helper or exported as an accepted mesh.**

The next reconstruction must constrain projection/connectivity at the actual
native feature, rather than keep subdividing a crossed local boundary. The
best complete shape-audited candidate remains the corrected pass 5. Its lower
patch result is not a continuous error bound, a whole-head dimensional
certificate or evidence that the upper patch or retained volume passes.

![Actual concave-boundary triangles before and after corrected triangulation](../media/m64-exceedance-20261002/comparison.png)

The picture reads back four actual triangles from each export, on the same
six vertices, matched within 1e-10 scan unit. It is a local projection, not a
new head design. The same [non-commercial research provenance](../../catalog/sources/src-wolfe-classics-935-billet-cylinder-head-scan.json)
applies. Image SHA-256:
`39a8d0ad27a568af2be0456e69a74eb6d22750d3031579da9521a6c77c20c239`.

The final frozen-source **`make check` exits 0 on Kali2**: 3,219 main tests,
159 optional skips, and all subsequent checks including the pinned F37 Docker
target. Twelve native tests run separately on Mac and Kali1. Documentation
links and report-index checks pass after this report and image are added.
No numerical process remains active, and no rental is used. The original CAD,
retained volume, physical qualification and manufacturing authority stay
unchanged; no CFD, thermal, mechanical or candidate printing simulation is
claimed.

Provenance:

- First all-exceedance source bundle: `7b46c39fd98bed4d4ed166b4ee00ee7e35fdf018d4aa49ae54c73346fca452db`.
- Corrected fan source bundle: `2daf2376499b8866a593acc7f0fe1e4e032cd0d5884fcfc7a24c2d4641b8c8ef`.
- Accepted necessary-surface screen, pass 5 mesh: `a73bf6d6ceb9c2be8ecb8e46e744d10531c62e67a08116ce26534f73e8883013`.
- Pass 5 receipt: `610afacb8307c22401fae92bcf7235a84db9993f7639f01b25a8a66dcf0e53c1`; shape audit: `23bab39cfa2fa67ae96346962d72cae7ea839e7d6950b6aad5fc1edfd9e56e9b`.
- Rejected pass 6 receipt: `8f650d6bd5e1a45513017ee9f997225eea5458400a7f2582fcad78542bdbf321`.
- Recovered fan-result archive: `a388d142a5d7c434a6d8f804afd7871feb411a6704df7135d4ea2b509a9174f8`.
- Full-suite log: `cae6dd9f77d3a64bdbf80167c1265821db4d1ffc6e694bca1afc9cffad10118e`.

## Native-feature projection reaches the sampled screen, 2 October

### Diagnosis and bounded correction

Native distance queries show that the rejected upper parent has two vertices
on face 1411 and one on face 1647. Those faces share exactly one topological
edge. Unrestricted nearest-point projection sends the two crossing-edge
midpoints to different faces, producing the crossed local boundary. The
nearest-face result cannot be repaired by triangulating its fixed vertices.

The existing refinement helper now attempts a bounded native-feature correction
only after child orientation or q2 fails. For each affected new point it binds
both edge endpoints to trimmed native faces, within 1e-6 scan unit:

- Shared endpoint face supports restrict projection to those faces.
- Otherwise, projection is restricted to the unique native edge common to
  their supporting faces. A missing or ambiguous shared edge is rejected.
- Only newly inserted points can change. The same new index is used by both
  incident triangles; original points and the exterior boundary stay fixed.
- Adjacent triangles are rechecked after each correction. At most eight rounds
  and 256 new points per patch are allowed; the original 0.1 displacement
  bound, q2 threshold and orientation checks are unchanged. Unresolved defects
  are not accepted when the bounded correction stops.

The private reproduction needs two rounds, considering five new points:
three common-edge projections and two shared-face projections. The first
round resolves the initial parent but exposes one neighbour; the second
resolves it. The original CAD is not edited. A synthetic box-corner regression
checks common-edge versus nearest-face projection, same-face behavior,
unchanged inputs, bad indices and bounds, off-surface endpoints, and nearby
but topologically disconnected faces. No scan coordinates are added to tests.

### Completed full-surface result

The frozen-code job on Kali1 resumes the bound, screened pass-5 candidate.
Pass 6 completes in **35.15 s**, selects 6,061 upper triangles and adds 8,917
nodes. The lower patch is not subdivided. All necessary surface checks pass:

| Check | Result |
|---|---:|
| Surface triangles | 992,724 |
| q2 below 0.06896551724 | 0 |
| Minimum q2 | 0.06913127978 |
| Nonpositive child/parent normal products | 0 |
| Edges without exactly two incident triangles | 0 / 1,489,086 |
| Duplicate triangles | 0 |
| Protected nodes, native CAD and input hashes unchanged | yes |
| Exact binary export/readback | yes |

The separate two-direction sampling audit completes in **193.85 s**:

| Patch | Mesh-to-native maximum | Native-to-mesh maximum | Samples above 0.040 |
|---|---:|---:|---:|
| Lower | 0.03782211596 | 0.03984823204 | 0 / 0 |
| Upper | 0.03303451901 | 0.03954089482 | 0 / 0 |

The maximum over these four measurements is **0.03984823203951887**.
The bounded driver stops on this sampled-screen pass; its three unused
follow-ups are not launched. This is the existing vertex/centroid/edge-midpoint
versus 17×17 trimmed-face/65-per-edge sampling, **not a continuous Hausdorff
bound or an audit of every native face**.

![Actual rejected and corrected triangles at the native junction](../media/m64-native-feature-20261002/comparison.png)

The image reads back four real triangles from each exported mesh, matches
their node tags, verifies unchanged original vertices, and uses the same
parent-plane projection and axis scales. Red marks the previous reversed
child; none is reversed in the corrected view. It is a local mesh diagnostic,
not a rendering of a finished head. The existing
[research-scan provenance](../../catalog/sources/src-wolfe-classics-935-billet-cylinder-head-scan.json)
still applies.

Thirteen native tests pass on Mac and Kali1. Full **`make check` exits 0 on
Kali2**: 3,220 main tests, 160 optional skips, and subsequent checks including
the 15 pinned F37 Docker tests. Native skips in the broad suite are not claimed
as executed coverage. Source and recovered-log hashes match the remote copies.
All numerical jobs finish; no rental, merge or deployment occurs.

### Still required before volume or physical acceptance

Vertex-link manifoldness, global geometric intersections, consistency of the
updated native 1D curve mesh and functional face labels remain unchecked.
The next stage must bind those audits to this exact export before a bounded
volume experiment. No new tetrahedral volume, CFD/CHT, material, thermal,
strength or printing result is produced here. The retained 32 rejected
tetrahedra and the M64 interface/physical-scale gates remain unresolved.

Provenance:

- Frozen source bundle: `816de272173e661a594b3c001ac4671a9fe0583d809b1483a7de5b07d35afc75`.
- Feature-projection helper: `a49383183f7fdf7e4bc03ca8d94d83c849c242a00018368c811b04679d97cb24`.
- Corrected pass-6 mesh: `7e59631d8e009107e57af7d284d6501522ed353b6d4b188492b718722ac80076`.
- Pass-6 receipt: `776442bcc2aab180b2f319370e167b1cf1457d03bd0d97a32ccab5f0e3d6e704`.
- Completed shape audit: `7d2851c46c80ff5ed8e45c7cdbc3e61a129f9b51d697f4ba42d53019569a8182`.
- Recovered result archive: `ea59cb1acec095ba3ffceffd85113b8444c7d468af4873b622b40068f5e77338`.
- Actual mesh image: `2ff9bedd667686f509d44b34353d4a1c98f5daa08519bf103285c40571d6a92a`.
- Full-suite log: `daa51e9c8163265c8fcc48bfc746fdec3cb5108c9446acadd9d50503215ce6b9`.
