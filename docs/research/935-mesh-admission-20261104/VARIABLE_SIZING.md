# Constrained variable-size full-surface trial — 2026-11-04

This executes the spatial-sizing step after the
[explicit-constraint witness](CONSTRAINTS.md).
**The full candidate is rejected:** exact protection and topology pass, but
native intersection and sampled surface-deviation gates fail. No volume mesher,
CFD, thermal, mechanical or manufacturing job is launched from it.
The [aggregate receipt](variable-sizing.json) preserves runtime and assessment.

## Sizing rule and protected geometry

A fine uniform target had failed native locked-edge admission. The new
[CGAL sizing field](source/constrained_variable_sizing.cpp) assigns 0.7 mm to
locked vertices and approaches 0.2 mm over one millimetre of shortest edge-path
distance on the original mesh:

`target(v) = 0.7 - 0.5 * min(1, graph_distance_to_locked_vertices_mm)`

Distances are computed from all constrained vertices by a bounded Dijkstra
propagation. The field is then carried by vertex properties; edge subdivision
registers a new size by averaging its two endpoint sizes. It is not a calibrated
curvature/error law or a guaranteed geometric tolerance. The bounds have a
1e-12 numeric comparison tolerance, not a physical uncertainty claim.

The implementation follows the installed `PMPSizingField` interface and the
endpoint-minimum split/collapse thresholds used by CGAL's sizing fields:
long edges above 4/3 of the minimum endpoint target, short edges below 4/5.
Locked edges and vertices, the excluded protected-face range, three iterations,
projection and nonrelaxation of constraints remain explicit. Native
preconditions are enabled. Compiler, installed-header, binary and source hashes
are retained; the [CGAL reference](https://doc.cgal.org/6.2/PMP_Remeshing/group__PMP__local__remeshing__grp.html)
describes the underlying API, not approval of this custom field.

Inputs remain the same hash-bound coarse reconstructed assembly with inferred
closures and unresolved physical interfaces. The protected mask is the frozen
111,463-face diagnostic mask, not an anatomical classification. Source input
and mask hashes were rechecked unchanged after execution.

## Qualification before the full run

The warped 17 × 17 grid witness refines from 512 to 2,932 triangles. It changes
unprotected geometry, preserves both protected oriented triangles exactly,
reaches the fine target and keeps final sizes within the declared bounds.
Independent native inspection finds no intersections or degenerate faces.

Negative controls confirm refusal of existing outputs and invalid mask IDs,
preservation of an existing mesh, and rejection of an oversized locked-edge
case before mesh output. The full original assembly's field preflight reproduces
492,169 locked edges and 342,090 locked vertices with **zero oversized locked
edges**. This resolves the uniform 0.5 mm precondition conflict for this field;
it does not establish that a generated surface will be admissible.

The full invocation had a 900-second wall bound and a sampled 12 GiB RSS guard.
Its Mac resource check required at least 18 GiB in the free/inactive/speculative
page estimate; that estimate is not a guarantee of available memory. Process
groups are terminated on resource/time failure. No limit was reached.

## Actual full-surface execution and independent results

Native remeshing completed in 158.31 seconds with a peak of 2,385,215,488 bytes
RSS (2.22 GiB). The independent assessment took 133.35 seconds and reached
4,606,050,304 bytes sampled peak RSS. Neither exceeded its bound.

| Quantity | Frozen coarse parent | New candidate |
|---|---:|---:|
| Vertices | 1,048,504 | 2,844,918 |
| Triangles | 2,099,584 | 5,692,412 |
| Shape quality below 0.01 | 8,489 | 2,008 |
| Shape quality below 0.1 | 85,069 | 18,560 |
| Median shape quality | 0.81229 | 0.95744 |
| Minimum shape quality | 3.304e-6 | 3.304e-6 |
| Independent intersection pairs | 0 | **35** |
| Degenerate faces | 0 | 0 |
| Euler characteristic / components | -1288 / 1 | -1288 / 1 |

Bad triangles below 0.01 decrease by about 76.35%. The full candidate remains
closed, vertex/edge manifold and orientable. All **111,463 protected oriented
triangles are exact**. These successes do not override the failed gates.

| Distance assessment | p95 | Sampled maximum |
|---|---:|---:|
| Parent → candidate, 100,000 samples | 0.01048 mm | **0.08285 mm** |
| Candidate → parent, 100,000 samples | 0.01002 mm | **0.09070 mm** |
| Scan → candidate, 100,000 samples | 0.10274 mm | 5.05645 mm |
| Candidate → scan, 100,000 samples | 1.54543 mm | 10.80588 mm |

Every candidate vertex was also measured against the parent: the maximum over
all 2,844,918 vertices is 4.203e-12 mm. This strong vertex-projection result
still cannot bound the intervening triangle surfaces. Sampled distances are not
Hausdorff bounds. Scan statistics concern the coarse inferred assembly, not the
fine envelope or an accepted bare head. The signed-volume change passes its
0.0001 relative limit, but local geometry remains inadmissible.

## Engineering decision and next work

Exact constraints are now verified on this full case, resolving the previous
selected-only preservation failure. Global fidelity and intersections remain
unresolved. Do not promote the result to volume meshing, engineering acceptance,
print readiness or engine release. The original parent and prior rejected
candidates remain unchanged.

This closes this bounded trial, not the head objective. Return to the acquired
observations and the existing source-supported CAD/interface work to establish
reconstructable regions and admissible domains. The inferred monolithic
assembly, attached hardware and missing/unclassified surfaces remain upstream
limitations. Further field tuning requires a specific geometry diagnosis and
newly justified input admission; median triangle quality alone is insufficient.
Material/process data, loads and professional/physical qualification remain
separate requirements of the original functional-metal objective.

## Replay and evidence

The private bundle is
`~/Developer/PorschePartsArtifacts/935-variable-sizing-20261104/`.
It retains native source/binary, exact argv, resource receipts, controls, output
OFF/NPZ, independent topology/distance reports, source snapshots and a manifest.
Only aggregates, hashes and code are public. No raw scan, coordinate/mask arrays
or full mesh is published. No external inference, supplier message, fabrication
order or rental was created.

Compile the [native field](source/constrained_variable_sizing.cpp) with the
same CGAL/GMP/MPFR flags as the preceding witness. Use the retained repair-trial
Python environment and [controller](source/run_variable_sizing.py), passing the
qualified constraints bundle and its committed reference JSON to fresh output
paths. Run the [independent assessor](source/assess_variable_sizing.py) only after
native completion, with pinned parent/scan hashes, the actual mask, the qualified
read-only inspector and Open3D interpreter. Each inspector/topology child is
bounded to 300 seconds and 8 GiB RSS; the assessment controller uses 1,800 seconds
and 12 GiB. The frozen argv provides concrete installed paths; CLI definitions
are retained in the source. Compilation, a successful process exit and a produced
OFF are distinct from the independent acceptance decision recorded above.
