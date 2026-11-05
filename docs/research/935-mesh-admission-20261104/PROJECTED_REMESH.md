# Projected 935 surface trials — 2026-11-04

Two further full-surface candidates were executed after the
[ineffective planar-flip trial](PLANAR_FLIP.md). **Both are rejected for volume
meshing.** Their improved triangle quality does not override intersections,
changed protected geometry or deviation failures. The
[aggregate receipt](projected-trials.json) preserves all results and gates.

## Fixed inputs, parameters and admission gates

Both trials start from the same immutable coarse reconstructed assembly:
1,048,504 vertices, 2,099,584 triangles, 8,489 triangles below normalized shape
quality 0.01. Its inferred closures and unresolved physical/anatomical identities
remain limitations. The original scan is used for distance assessment only.
Study and scan-array hashes were checked before execution and independently
rechecked unchanged after the runs. No new source geometry was acquired.

The local PyMeshLab 2025.7.post1
[isotropic remeshing filter](https://pymeshlab.readthedocs.io/en/latest/filter_list.html#meshing-isotropic-explicit-remeshing)
uses three iterations, 0.5 mm target edges, 30-degree feature angle, 0.01 mm
per-operation surface-distance setting, smoothing and reprojection enabled.
Pure-value lengths are used rather than percentages. The masked run changes
only face selection/protection; it restarts from the original parent, not the
rejected first candidate.

Predeclared study gates require:

- no degenerate faces or self-intersections in independent native CGAL checks;
- manifold vertices and closed manifold edges, preserved Euler characteristic
  and edge-connected component count in an independent Open3D reader;
- bidirectional 100,000-point area-weighted sampled parent deviations at most
  0.01 mm, plus every candidate vertex within 0.01 mm of the parent;
- relative volume change at most 0.0001 and at least 50% fewer triangles below
  shape quality 0.01;
- for the masked trial, every protected triangle's coordinates, connectivity
  and winding preserved exactly.

These are numerical study limits, not measured specimen tolerances or physical
release criteria. Sampling is not a Hausdorff bound. Passing the vertex-distance
check cannot replace the triangle-surface check.

## Results

| Quantity | Unmasked | Masked |
|---|---:|---:|
| Vertices | 961,817 | 966,210 |
| Triangles | 1,926,210 | 1,934,996 |
| Triangles below quality 0.01 | 406 | 1,360 |
| Reduction from 8,489 | 95.22% | 83.98% |
| Triangles below quality 0.1 | 5,072 | 14,380 |
| Native self-intersection pairs | **3** | 0 |
| Degenerate faces | 0 | 0 |
| Euler characteristic / components | -1288 / 1 | -1288 / 1 |
| Manifold vertices and closed manifold edges | Pass | Pass |
| Parent → candidate sampled maximum | **0.03555 mm** | **0.02822 mm** |
| Candidate → parent sampled maximum | **0.02297 mm** | **0.02121 mm** |
| Maximum over all candidate vertices → parent | 6.330e-9 mm | 6.330e-9 mm |
| Final volume-study admission | **Rejected** | **Rejected** |

All candidate vertices are extremely close to the parent surface, yet the
interpolated faces depart beyond the predeclared surface limit. Neither the
reprojection flag nor the per-operation distance setting establishes a global
surface-deviation bound. Signed volume is preserved within its declared limit;
that does not rescue local geometry errors. The shape-quality minimum remains
3.304e-6 in both candidates. No tetrahedral mesh or solver run was launched.

Scan → candidate p95 is 0.10252 / 0.10267 mm; reverse p95 is
1.55339 / 1.56650 mm, respectively. These use the **coarse reconstructed assembly**,
not the fine reference envelope. Reverse distances retain the effects of
inferred/unobserved surfaces; they do not prove an identical physical replica.

## Diagnostic localization and exact mask test

The full unmasked candidate's three intersection pairs involve four triangles.
An index-bearing CGAL companion was checked with an isolated leading triangle
and a known crossing pair: it correctly returns the shifted pair indices 1/2.
Every parent and candidate triangle centroid was then measured against the
opposite surface: 6,577 parent and 8,409 candidate centroids exceed 0.01 mm.
Mapping those failures and seven probes on each intersecting face yields 13,521
parent seed faces. Nearest-face associations are spatial support, not anatomy.

Expanding those seeds by two shared-edge rings protects 111,463 faces (5.31%).
Before the full masked run, a warped-grid control preserves its two protected
faces exactly. A separate oriented-key control accepts cyclic vertex ordering
and rejects reversed winding and a coordinate change. The mask could still
permit the target quality improvement: only 670 original bad triangles are
protected, giving a theoretical maximum reduction of 92.11%, not an achieved
result.

On the full head study, **275 protected triangles are not preserved exactly**.
An independent nearest-coordinate/connectivity check with 1e-10 mm tolerance
confirms that this is not merely serialization roundoff:

- 16 protected original vertices have no candidate vertex within that tolerance;
  the largest nearest-candidate-vertex separation is 0.20516 mm;
- 259 protected faces retain close coordinates for their original vertices but
  do not retain the same oriented connectivity.

Nearest-vertex separation is not a tracked displacement history. The result
shows that this filter invocation's selection flag is insufficient for exact
protected-region preservation on this case, despite the small control passing.
The original exact-preservation gate remains unchanged and failed.

## Controls, provenance and replay

CGAL 6.2.1 read-only inspection, Open3D 0.20.0 and libigl 2.6.3 assess outputs
independently of the remesher. Open3D controls accept a closed tetrahedron and
reject two closed tetrahedra pinched at a vertex despite manifold edges. The
unmasked driver also rejects an existing output or a corrupt prior inspector
before writing a trial. A masked-driver serialization exception was caught in
its control before full remeshing; its failed source/log were retained privately,
and the separately named v2 driver was used. Successful process exit does not
mean candidate acceptance.

Private bundles (with manifests, raw outputs and source snapshots):

- `~/Developer/PorschePartsArtifacts/935-isotropic-20261104/`
- `~/Developer/PorschePartsArtifacts/935-masked-isotropic-20261104/` — failed preflight
- `~/Developer/PorschePartsArtifacts/935-masked-isotropic-20261104-v2/`

The [isotropic driver](source/trial_isotropic.py),
[corrected masked driver](source/trial_masked_isotropic_v2.py),
[vertex-topology inspector](source/inspect_vertex_topology.py),
[intersection index inspector](source/inspect_intersection_indices.cpp),
[localization driver](source/localize_remesh_defects.py) and
[protected-face assessor](source/audit_protected_faces.py) retain actual APIs.
Use the preceding planar trial's manifest-bound native inspector and original
input bindings, the repair-trial Python environment, and a fresh output directory.
Each remesh invocation had a 900-second process-group bound, native/topology
checks a 300-second bound, and localization a 600-second outer bound. No timeout
occurred. Geometry, coordinates and mask arrays remain private; this report
publishes aggregates and hashes only. No cloud inference or paid rental was used.

## Next admissible action

Stop using `selectedonly` as proof of exact protection on this case. Prepare a
separate CGAL constrained-patch witness with explicit constrained edges/vertices
and independent protected-face comparison before another full-surface attempt.
The [installed-version family documentation](https://doc.cgal.org/6.2/PMP_Remeshing/group__PMP__local__remeshing__grp.html)
documents these constraints and warns about constrained edges longer than twice
the target length. Audit that length precondition before execution; do not
silently split protected edges or reduce the target into a nonterminating regime.
The witness and any later geometry must still pass the existing surface-distance,
topology, quality and intersection gates. None supplies missing specimen geometry,
material laws or a qualified metal build process.
