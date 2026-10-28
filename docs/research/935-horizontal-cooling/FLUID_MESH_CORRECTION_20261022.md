# 935 fluid-mesh correction — 2026-10-22

## Position in the README software chain

This continues the [Foundation 13 rotor pilot](FOUNDATION13_ROTOR_PILOT_20261022.md)
at **geometry inspection → CFD case preparation and meshing**. The retained
PicoGK master is unchanged. The 993 programme remains separate. No new paid
instance was rented; native meshing uses Kali1 and independent readback uses
the Mac. PhysicsNeMo must wait for accepted reference simulations.

The new volume meshes preserve a closed fluid cavity, positive tetrahedra and
named boundary markers. **None passes the complete unchanged OpenFOAM quality
check. No new fan-flow calculation is admitted or executed in this stage.**

## Repair the CFD boundary before volume meshing

The original snapped mesh contains warped polygons. Triangulating them around
their area-weighted face centres exposes 19 exact intersection pairs in the
actual CFD boundary. Turning off feature attraction reduces this to three,
but does not remove them. A proposed tangential face-centre repair refuses
its 0.1 mm movement limit; that limit is not enlarged.

A fresh snapping attempt disables feature attraction and tightens the snapping
`maxConcave` setting from 80° to 20°. The final `meshQualityDict` is unchanged.
The resulting boundary has **114,551 vertices and 229,098 triangles**, including
212,096 rotor triangles. CGAL 6.2.1 exact predicates find zero intersection
pairs across all faces. Independent solid-angle winding tests distinguish the
solid rotor hole from the connected fluid cavity. The closed fluid volume is
`0.05140958285727807 m³` under the existing conditional scale.

These changes concern an analysis mesh. They do not establish scan scale,
machining tolerances, or historical housing geometry. A complete deviation
bound from this snapped CFD wall to the retained analysis surface remains open.

## Complete volume and native-conversion checks

Upstream TetGen 1.5.1 uses `-Y` to preserve every boundary triangle. Every
tetrahedron is checked with exact integer orientation; the exact rational sum
equals the closed boundary's volume. All boundary coordinates, triangles and
patch markers match, with one connected fluid region and no nonmanifold faces.
The audit binds the actual input bundle and mesher input hashes, not only their
receipt filenames. Raw inputs, output arrays and rejected attempts stay private.

The frozen Foundation 13 runtime imports the mesh using `tetgenToFoam`, restores
`inlet`, `outlet`, `duct` and `rotor`, then runs:

```sh
checkMesh -allGeometry -allTopology -meshQuality
```

Every candidate eliminates the earlier concave cells. The other checks remain
blocking. Native exit code zero alone does not mean that mesh quality passed.

| Candidate | Fluid cells | Faces >70° non-orthogonality | Cells with determinant <0.001 | Faces with weight <0.05 | Failed native checks |
|---|---:|---:|---:|---:|---:|
| Preserved boundary, `q1.4` | 884,608 | 929 | 3,261 | 63 | 4 |
| Preserved boundary, `q1.2/10O5` | 1,590,792 | 892 | 2,842 | 39 | 4 |
| Bounded CGAL skin, `q1.2/10O5` | 1,085,891 | 3,920 | 3,346 | 536 | 5 |
| Local centroid subdivision | 894,040 | 5,355 | 597 | 1,056 | 4 |

The weight column is the extended check's 0.05 threshold. The separate local
dictionary retains its original 0.02 threshold. Neither threshold is changed.
Volume-ratio failures are also retained in the machine-readable checkpoint.

Independent VTK 9.6.2 and ASCII readback verifies **every coordinate, tetrahedron
and boundary marker** after native conversion for both preserved-boundary meshes,
including the 1.59-million-cell alternative. This verifies import fidelity,
not finite-volume suitability.

## Test the suspected causes

Two VTK decimation attempts reduce the rotor to 84,838 triangles. Both fail the
independent complete bidirectional surface-distance check, despite passing the
topology check. Neither enters volume meshing. A local decimation error parameter
does not establish a complete surface-distance bound.

A separate CGAL 6.2.1 simplifier uses a 0.020 mm construction envelope and a
triangle-quality floor of 0.05. The unchanged independent CGAL 5.5.1 checker
accepts all 212,096 source and 127,256 candidate triangles in both directions
within **0.0225 mm**, with a separate 0.0025 mm numerical reserve. This bound
applies to the existing CFD skin, not directly to the scan or PicoGK master.
The SI/mm round-trip shift is below `3e-17 m`. The generator's process limits
were attached after launch; its receipt does not claim otherwise.

This geometrically bounded simplification still worsens CFD mesh quality.
The source rotor's minimum triangle quality was already 0.276; the simplified
surface's minimum is 0.0501. The evidence contradicts the initial suspicion
that poor surface triangle shape explained the volume failures. The candidate
is rejected for CFD.

The independent native-mesh diagnostic reproduces exactly 929 severe faces and
3,261 failed cell determinants. Of those cells, **3,144 have only two internal
faces**. Foundation 13's determinant calculation sums internal/coupled face-area
outer products: two directions cannot span three dimensions, even in a positive
tetrahedron. See the [actual Foundation 13 implementation](https://github.com/OpenFOAM/OpenFOAM-13/blob/master/src/meshCheck/primitiveMeshCheck/primitiveMeshCheck.C).
The frozen runtime's source copy and hash are retained privately.

Splitting those 3,144 tetrahedra at their centroids preserves every boundary
triangle and the exact total volume. A unit-tetrahedron control independently
checks exact partition into four positive children. The complete volume audit
passes again. However, native non-orthogonality and interpolation weights become
substantially worse. This alternative is also rejected; fixing one metric does
not qualify the mesh.

## Reproduction, preservation and next work

The [dated sources](../../../twins/935-horizontal-cooling-system-f0/source/fluid-mesh-study-20261022/README.md)
reuse existing orientation, connectivity and reconstruction helpers. The
[checkpoint](fluid-mesh-correction-20261022.json) pins sources, numerical results,
native logs and the private archive. Tests cover ASCII/unit boundaries, solid
versus fluid classification, exact volume, marker rejection and input tampering.
The 935-focused suite passes **150 tests, with four optional skips**. Full Linux
`make check` and delivery status are recorded separately after publication.

Private geometry, all failed variants, native cases, independent verification
and controller logs are saved on Kali1, the Mac and the existing private GitHub
release. The archive is read and checked member by member on both machines;
its uploaded server digest must match before delivery is called preserved.

The next mesh change must improve the full unchanged quality check: investigate
boundary-layer/volume meshing or constrained local optimization rather than
repeating the rejected decimation, TetGen flags or centroid subdivision. Then
address the previous pilot's outlet reversal, domain dependence and possible
compressibility before running three-grid fan curves.

Physical scan scale, shaft registration, the 17 interfaces, hidden transmission,
actual 935 engine mounting, material/process data, structural spatial convergence,
fatigue and the bench test remain unresolved. The registered 917 engine scan is
comparative context, not a 935 engine. No manufacturing or fitment release follows
from this numerical checkpoint.
