# 935 bounded surface repair and refused fluid dual — 2026-10-22

## Position in the software chain

This continues [reference-wall fidelity](REFERENCE_FLUID_WALL_20261022.md) at
**PicoGK geometry → analysis-surface checks → CFD meshing**. The design master
is unchanged. Local analysis remeshing reduces triangles below quality 0.05
from **189 to 46**, while preserving the complete independent bidirectional
surface bounds, closed topology, one component and Euler characteristic −10.
The new surface has 436,634 vertices and 873,288 triangles.

This is an accepted *analysis-surface repair*, not a historically calibrated
rotor, accepted CFD mesh or manufacturing release. A new faithful tetrahedral
fluid volume passes the complete geometric audits but fails seven native
finite-volume quality checks. A subsequent polyhedral alternative fails eleven
checks, including negative volumes, and is rejected. No new airflow solve runs.

## Repair, limits and rejected candidates

The original poor facets were explicitly protected by the previous simplifier;
its quality floor applied only to newly created faces. CGAL 6.2.1
`remove_almost_degenerate_faces` now operates locally, with a three-ring
neighbourhood, constrained exterior vertices/edges, and a quality-0.05 filter on
new triangles. Every untouched exterior vertex and face must remain unchanged.
The [CGAL repair documentation](https://doc.cgal.org/5.6.2/Polygon_mesh_processing/group__PMP__geometric__repair__grp.html)
describes the underlying class of operations; executed headers, build flags and
binary hashes identify the actual installed version.

All attempted policies remain private. Increasing the permitted collapse length
produces candidates with 171, 129, 70 and eight poor facets. The eight-facet
candidate fails the unchanged complete original-to-candidate envelope check and
is not admitted. A sample diagnostic at the refused face measures only sampled
distances; it does not overturn that refusal.

The [polyhedral envelope](https://doc.cgal.org/latest/Polygon_mesh_processing/structCGAL_1_1Polyhedral__envelope.html)
is a conservative geometric construction, not an exact Euclidean distance
oracle. Its face-prism half-thickness is epsilon divided by the square root of
three. A refused certificate therefore does not itself prove that Euclidean
distance exceeds epsilon. The reference surface passes the same full original
check again, ruling out a changed baseline/checker as the explanation.

The retained proposal uses a needle ratio of 35 and cap angle about 175.1°;
each classifier can trigger only below quality 0.05. For edge ratio R the
maximum possible triangle quality is `sqrt(3)*R/sqrt(R^4+R^2+1)`; for an angle
theta it is `sqrt(3)*sin(theta)/(2-cos(theta))`. Native analytic controls check
these inequalities and a tiny-edge repair on a unit tetrahedron. They are
sufficient poor-triangle classifiers, not exhaustive criteria or acceptance
bounds. Forty-six poor facets remain.

The retained candidate passes every original and retained-reference triangle
in both directions through the unchanged independent checker. The bound is
**0.0225 source units**, with the separate **0.0025 numeric reserve** retained.
All accepted vertices are a subset of the reference vertices; float32 exchange
moves none. Complete NPZ/STL readback, orientation, topology and intersection
checks pass. The minimum quality rises from `5.4071555e-5` to `0.0071048384`;
the minimum edge rises from `1.5258789e-5` to `0.0024337769` source units.
Neither length is a measured physical tolerance.

## Rebuilding the fluid volume

An exact coordinate/triangle bijection first rechecks the retained reference's
SI conversion. The repaired rotor is then combined with the unchanged 17,002
outer study-domain triangles and markers. The complete 890,290-triangle PLC is
closed and has zero reported self-intersection pairs. The conversion continues
to assume 0.001 metres per uncalibrated source unit. The square duct remains a
conditional calculation domain, not the historical 935 housing.

TetGen again introduces one boundary Steiner point despite the retained `Y`
switch. The complete boundary audit refuses that output. An exact predicate
finds this point noncollinear with its source edge, although a floating
projection reports zero distance. This diagnosis now explicitly uses Python
arbitrary-precision integer multiplication: a `2^80` cross-product control
exposes the overflow risk of int64 intermediates. Rechecking the preceding
study's actual cross product reproduces its result; its conclusion is unchanged.

The existing kernel-cone procedure replaces 18 incident tetrahedra with 20
positive children, moves only the added point into the cavity, and restores
all original wall facets and markers. The complete volume has **806,631 points
and 3,668,295 tetrahedra**, no negative or zero exact determinants, one fluid
region and exact rational volume equality to the PLC. Its conditional volume is
`0.05140933407575617 m³`. Independent ASCII and VTK readback then verifies every
native point, cell and physical boundary marker.

The original Foundation 13 quality dictionary and complete native command are
unchanged: `checkMesh -allGeometry -allTopology -meshQuality`.

| Native tetrahedral observation | Result |
|---|---:|
| failed extended quality checks | 7 |
| faces above 70° nonorthogonality | 193,816 |
| determinant below 0.001 | 108,863 cells |
| concave cells, face-plane test | 1 |
| maximum skewness | 13.9351 |
| interpolation weights below 0.05 | 13,879 faces |
| neighbour-volume ratios below 0.01 | 1,969 faces |

These counts do not improve on the preceding six-failure reference volume.
Surface quality, positive tetrahedra and finite-volume suitability are separate.

## Polyhedral control and real-geometry refusal

Native `polyDualMesh` with a 30° feature angle and `-concaveMultiCells` fails the
full quality gate on an analytic unit cube because of 60 concave cells. Combining
coplanar boundary faces is tested as a complete new procedure, without changing
the quality dictionary. The combined cube has 343 cells, passes the full native
quality command, and retains every boundary plane within `1e-12 m`. Independent
closed-surface/readback checks find a unit-volume error of `4.94e-17 m³`.
That numeric bound belongs only to this synthetic control.

OpenFOAM utilities can write a new `0/polyMesh` while retaining the original
`constant/polyMesh`. The cube reader selects the actual mesh instance and
compares its cell/face counts with the native log; tests cover this distinction.
The combined procedure's native check reads its final `constant` instance.

The same procedure on the real fluid mesh completes in 119.36 seconds, with
the original input and dictionary unchanged, but fails **eleven** full native
checks. It reports 1,004,196 cells, 11 negative-volume cells, a minimum volume
of `−2.019e-10 m³`, 362,203 concave cells and maximum skewness 24,493.9.
It is rejected before any downstream geometry admission or flow calculation.
Successful synthetic controls and command exit code zero are insufficient.

## Visual inspection, verification and preservation

Private images show all 873,288 actual repaired surface triangles, the remaining
poor-facet locations, and an enlarged before/after patch. They use no display
decimation and carry input/source/image hashes. Location markers are neither
flow nor stress fields. The private full-system image still includes a
provisional shroud and simplified six-cylinder packaging.

The [executed sources](../../../twins/935-horizontal-cooling-system-f0/source/surface-facet-repair-20261022/README.md)
and [checkpoint](surface-facet-repair-20261022.json) bind source versions,
receipts, controls, refusals, private archives and scope. Focused numerical tests,
documentation checks, full Linux CI and merge evidence remain distinct records.
The focused 935 suite passes 196 tests with four optional skips, including eleven
new tests for exact predicates, active-instance cube readback and scope guards.
No raw scan or derived private mesh is added to public Git. All work in this
phase runs on Mac/Kali1 without another paid instance.

Next construct a graded, near-wall-resolved fluid mesh from a bounded surface;
local remeshing of the remaining poor patches may be needed first. Do not repeat
the same unconstrained tetrahedralization or the refused global dual and infer
convergence from a lower individual defect count. All seventeen mechanical
interfaces, physical calibration, hidden transmission, historical mounting and
housing, structural spatial convergence, fatigue, accepted fan curves and bench
tests remain open. PhysicsNeMo has no accepted fan dataset yet.
