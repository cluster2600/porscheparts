# Targeted mesh diagnosis and bounded recovery

The E-R1 primal mesh's four failed checks are localized from actual OpenFOAM
sets and VTK exports. No flow solver has run. Coordinates describe the assumed
parametric model in millimeters, not measured Porsche datums.

The installed checker is Foundation 13 build
`18870c24d21c6b982e2cdec27b2f59738cca5f90`. Its
[determinant implementation](https://github.com/OpenFOAM/OpenFOAM-13/blob/18870c24d21c6b982e2cdec27b2f59738cca5f90/src/meshCheck/primitiveMeshCheck/primitiveMeshCheck.C#L454)
forms a tensor from **internal/coupled face-area vectors only**. Two internal
faces have insufficient rank in three dimensions, even when the tetrahedron
has a positive geometric Jacobian. This explains the need for independent
finite-volume QA. The
[converter](https://github.com/OpenFOAM/OpenFOAM-13/blob/18870c24d21c6b982e2cdec27b2f59738cca5f90/applications/utilities/mesh/conversion/gmshToFoam/gmshToFoam.C#L564)
preserves sequential type-4 cell order; the localization parser verifies all
native bad-cell labels against that original mesh.

Of 3,376 underdetermined cells, **1,735 have two boundary faces**, 1,339 have one
and 302 are interior. All 1,735 members of the native two-internal-face set are
also underdetermined. Patch contacts include 1,672 rotor, 649 inlet, 751 outlet
and 184 duct contacts; a cell can touch more than one patch. The defects are
therefore partly consequences of the artificial conduit/cap discretization,
in addition to the curved impeller boundary and thin tetrahedra. The earlier
centroid split improves the rank deficiency but worsens some interpolation/
volume transitions, so it is not repeated.

The sole highly skew face is near the blade-tip region at approximately
(-60.947, 106.076, -15.109) mm. The three low-volume-ratio face centers are
(29.851, -100.964, -14.812), (16.265, -76.791, 24.258) and
(29.591, -101.489, -14.978) mm. The 104 low-interpolation-weight faces include
both inlet/outlet cap transitions and impeller-near regions. Closedness and
zero source intersections do not remove these finite-volume conditioning
problems. Original native IDs and all locations are retained in the receipts.

## Hex route declared before its run

The next bounded step uses the installed Foundation 13 `blockMesh` and
`snappyHexMesh`, with a Cartesian background/caps and a hex-dominant cut/snap
mesh of E-R1. This changes the numerical formulation and addresses the poor
boundary-neighbor stencil; it does not repeat a rejected tetrahedral smoothing
or dual conversion. The source remains the independently checked E-R1 surface.

Before running: 26 × 26 × 36 background cells; rotor refinement level four;
1.5-million-cell refinement setting; 600-second meshing bound; at most four
CPUs / 6 GiB; no image pull or purchase. Quality limits are at least as strict
as the independent standard/extended gate: skew ≤3.5, determinant ≥0.002,
face weight ≥0.05 and volume ratio ≥0.01 during mesh generation. No wall
layers and no flow fields/solver are prepared in this mesh-only experiment.

The initial 600-second attempt timed out during normal snapping progress; this
is a runtime-limit outcome, not a completed quality rejection. The preserved
castellated mesh passes the standard check but fails the extended check on
123,694 concave cells; it is a staircase intermediate, not a finished mesh.
The native refinement setting can overshoot: peak refinement reached
2,655,136 cells, retained mesh 1,907,523 cells. It is a mesher setting, not an
enforced process-wide allocation limit. Memory stayed within the container bound.

The preserved intermediate is archived privately. Only snapping is resumed
with `castellatedMesh false`, unchanged quality limits, and a new 1,200-second
wall-time limit. Stop on solver error/OOM, on memory above 5.7 GiB across two
observations, or on no log/iteration progression for 180 seconds; the container
also enforces 6 GiB and four CPUs. No unrelated worker is suspended.

If it finishes, require both independent checks, a closed oriented retained
rotor surface with the original Euler characteristic, sampled bidirectional
mesh-to-E-R1 deviation ≤0.2 mm and volume difference <0.2%. The distance is a
numerical representation target, not hardware accuracy; it is fixed before
the attempt. A threshold failure remains a failure. An accepted mesh still
needs wall-resolution, refinement, solver convergence and physical correlation
before aerodynamic ranking. If the cell/time/memory limits prevent this route,
retain its artifacts and report the exact limit rather than purchasing capacity.

The existing Gmsh/OpenCASCADE runtime successfully constructed and exported a
1 mm analytic box as STEP (350 entities), a bounded capability smoke check;
it does not establish an impeller BRep. A BRep route remains possible, but the current
Organic E source is a voxel/implicit surface, not an editable analytic blade-
root BRep. Reconstructing an original loft/root/hub geometry would be a new
design hypothesis, with fresh geometric/mechanical comparisons. A qualified
target BRep additionally requires measured interfaces, intended root/fillet
profiles, clearance stack and metrology; scan rights/scale remain independent.

## Completed hex outcome and remaining technical blocker

Snapping resumed normally and finished in **1,053.092064 seconds**; native exit
zero, all mesher-internal quality limits passed without relaxation. The retained
mesh contains 1,907,523 cells, including 1,578,397 hexahedra. The independent
standard check passes; the extended check **fails one check on 82,294 concave
cells**. The initial four failures are resolved in this different formulation:
minimum determinant 0.030291, maximum skew 3.496437, minimum interpolation
weight 0.081102 and minimum neighbor-volume ratio 0.016213. Extended face
concavity/warpage warnings are also retained; they are not silently dismissed.

The independent native rotor export has 755,484 triangles, consistent winding,
one component and no zero-area triangles. Its representation is nevertheless
rejected: two edges meet four triangles, at (74.812, -96.695, 5.361) and
(-117.608, -33.324, -10.344) mm. Euler characteristic is -28 instead of -30;
the representation therefore does not retain the original topology. These are
near-tip numerical contacts, not evidence of a defect in the independently
closed source. Source-to-mesh sampled maximum deviation is **0.377836 mm**
(202/5,000 samples above 0.2 mm); mesh-to-source is **0.364376 mm** (4/5,000).
The small volume difference, 0.005323%, does not cancel local errors or topology
loss. Maximum-error sample/nearest-point coordinates and every nonmanifold edge
location are included in the [surface receipt](../results/engineering-iteration-20261003/mesh/hex-er1/surface-audit.json).

The [outcome and exact native logs](../results/engineering-iteration-20261003/mesh/hex-er1/outcome.json),
concave-cell IDs and native diagnostic surface are public original-model
receipts. The entire final case is preserved privately with a verified archive
hash. **No flow solver has run.** This is a completed quality/geometry rejection,
unlike the earlier timeout. Existing resources are released; no extra capacity
or NVIDIA worker interruption was required.

A defensible next numerical experiment would first resolve the two near-tip
contacts and the located geometric-error regions with targeted refinement,
then address concave-cell construction using a conformal convex-cell topology.
Simply extending snapping again, reusing the rejected boundary as a new source,
removing diagnostic triangles or lowering thresholds would not solve these
failures. Finer cut-cell meshing alone is not yet demonstrated to meet the
strict concavity gate, so it cannot be promised as a validated recovery.
An analytic loft/root/hub BRep with explicit curvature and refinement controls
is the alternative to the current implicit/voxel boundary. Its kernel is
available, but an actual impeller BRep has not been constructed or verified.
Qualified reconstruction still needs measured attachment/bearing datums,
root/fillet profiles and clearances; a new hypothetical BRep must keep its own
identity and fresh simulation evidence. There is no demonstrated aerodynamic
benefit, physical fit, printing route qualification or safe operating speed.
