# 935 reference surface in the airflow domain — 2026-10-22

## Result in the software chain

This returns from the [agglomeration study](FLUID_AGGLOMERATION_20261022.md) to
**geometry fidelity → CFD preparation** in the root README. Every one of the
analysis reference's **436,712 vertices and 873,444 triangles** now appears
unchanged in the final fluid boundary, with orientation reversed for the solid
hole. The PicoGK design master is unchanged; this repairs its analysis-to-fluid
link, not its agreement with the historical fan or the raw scan.

The complete new volume contains **809,217 points and 3,685,053 positive
tetrahedra**. Its exact rational volume equals the closed input domain. Every
boundary triangle, coordinate and patch marker survives native conversion and
independent readback. **Six unchanged native mesh-quality checks still fail;
no new rotor flow solve is run or admitted.** This is a faithful geometric
baseline, not an accepted CFD mesh or a fabricable system.

## Why replace the old wall

The old snapped wall is compared with the exact hash-bound SI analysis OBJ used
by the original CFD preparation. Double-precision nearest-triangle queries test
every vertex and face centroid in both directions, after an analytic triangle
control. The observed maximum is 2.039 mm from wall to reference and 3.639 mm
in reverse. The 95th percentiles are 0.236 mm and 0.474 mm respectively.
These are samples, not a complete continuous-distance certificate. Values use
the unverified assumption of 0.001 metres per source unit.

The new construction copies the entire reference triangle set instead of
resnapping it. A separate OBJ parser independently verifies all coordinates and
triangles in the bundle, serialized OBJ and TetGen SMESH. The complete rotor
surface sets are therefore identical: their geometric distance is exactly zero
at this link. This is not a zero-error claim against the raw scan, PicoGK master
or physical hardware. The previous bounded analysis-to-master certificate
remains a separate dependency.

All 17,002 outer inlet/outlet/duct triangles and their markers are retained.
The square duct is a conditional study domain, not the historical 935 housing.
The combined 890,446-triangle boundary is closed, consistently oriented and has
zero self-intersection pairs under the existing CGAL 6.2.1 checker. Solid-angle
winding distinguishes the rotor hole from the connected fluid cavity. Nested
analytic boxes independently check orientation and the exact volume subtraction
8 − 1 = 7; an open-rotor control is refused.

## An unexpected mesher edit is rejected and repaired

The existing bounded TetGen 1.5.1 runner uses `-pYq1.4MzCf`. Its first output
adds one rotor-edge Steiner point and replaces two reference triangles by four.
The unchanged complete boundary audit refuses it. The
[upstream description of boundary preservation](https://wias-berlin.de/software/tetgen/1.5/doc/manual/manual005.html)
does not replace that audit. The actual pinned source's repeated `Y` handling
does not establish a stronger alternative; no undocumented switch retry is used.

Exact integer predicates find the added point is not precisely collinear with
the original edge, although an ordinary floating projection reports zero
distance. It is not accepted as an exact surface subdivision.

The repair removes its 12 incident tetrahedra, restores the two original wall
facets, and cones the resulting closed 14-face cavity to a strictly interior
point. The existing normalized linear-programming kernel proposes that point;
exact orientation checks accept all 14 children. Only the added Steiner point
is moved. Every original input coordinate, physical wall triangle and marker
is retained. The unit-tetrahedron control sums to exactly 1/6; translated small
controls, inverted surfaces, open cavities and zero-volume cavities are tested.

The unchanged complete volume auditor then verifies all 3,685,053 cells, one
connected fluid region, no nonmanifold faces or repeated-node tetrahedra, the
complete boundary-marker bijection and exact equality to the input PLC volume:
`0.051409334075927696 m³` under the assumed scale. There are no negative or zero
exact determinants. The mesher's original rejected output is preserved.

## Native readback and quality refusal

The frozen, rootless, network-isolated Foundation 13 runtime converts the mesh,
restores `inlet`, `outlet`, `duct` and `rotor`, then runs the original
`checkMesh -allGeometry -allTopology -meshQuality`. Its quality dictionary is
byte-identical. Complete independent ASCII and VTK readback checks every native
point, tetrahedron and physical boundary marker against the audited arrays.
VTK connectivity is checked independently; exact point identity uses ASCII
doubles, not the reader's display precision.

| Native observation | Result |
|---|---:|
| failed extended quality checks | 6 |
| faces above 70° nonorthogonality | 186,047 |
| cells with determinant below 0.001 | 103,604 |
| interpolation weights below 0.05 | 13,571 |
| neighbour-volume ratios below 0.01 | 1,761 |
| maximum skewness | 15.4450 |
| minimum positive cell volume | 6.203e-18 m³ |

The local dictionary separately reports 756 face-decomposition quality failures,
1,411 skewness failures and 2,965 weights below its unchanged 0.02 threshold.
These observations concern a different wall/mesh from the earlier 419-defect
case and are not cumulative improvements to that case. Positivity, exact volume
and a successful import do not establish finite-volume suitability.

The reference surface itself has **189 triangles below quality 0.05**, minimum
quality `5.407e-5`, and a minimum edge length of `1.526e-8 m`. This matches the
previously protected poor input facets in the
[quadratic-rotor checkpoint](quadratic-rotor-20261022.json); the simplifier's
floor applied to new faces, not to those protected originals. No global quality
floor is inferred from its configuration.

## Reproduction and next action

The [executed sources](../../../twins/935-horizontal-cooling-system-f0/source/reference-fluid-wall-study-20261022/README.md)
reuse existing winding, exact-orientation, kernel, topology and native-import
helpers. The [checkpoint](reference-fluid-wall-20261022.json) binds inputs,
source hashes, full audits, native refusal and private preservation. Failed
imports, the rejected mesh and all corrected attempts remain private. Five
targeted numerical tests pass; the complete focused 935 suite passes 185 tests
with four optional skips. Full Linux checks and publication evidence are recorded
separately after the scientific checkpoint.

Next repair or remesh the protected poor surface patches with a complete
bidirectional bound to this retained reference. Recheck topology and intersections
before constructing a graded fluid mesh with appropriate near-wall resolution.
Boundary-layer/finite-volume construction and any internal optimization must
pass the unchanged full native quality gate. A lower defect count alone is not
acceptance; repeating the same unconstrained tetrahedralization is not the next
action. Physical scale, all 17 interfaces, hidden transmission, historical engine
mounting, actual shroud, structural spatial convergence, fatigue, accepted fan
curves and bench validation remain open. PhysicsNeMo still has no accepted fan
reference dataset.

All new work uses Mac and Kali1. No new paid instance is created, and no geometry
or scan is committed to public Git.
