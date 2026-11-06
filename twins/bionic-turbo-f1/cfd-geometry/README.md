# Idealised compressor fluid domain

This generator builds a **sealed numerical domain candidate**, distinct
from the real 39-part assembly. It uses the final F0/F1 housing and the three
F0 rotating obstacles identified by their SHA-256. It produces no CFD
result and does not declare the domain ready for a solver.

The source geometry is fixed to the F0/F1 comparison at 0.50 mm; the domain has been
revoxelised at **0.25 mm** since attempt 005. The housing parameters
must match this study exactly. F1 accepts the volute law
`radius_linear` or `area_affine`, the profile `conical` or `wheel_shroud`, with a
radial profile clearance fixed at **1.5 mm**. The housing regularisation is finite,
between **0.5 and 1 mm**, without exceeding a quarter of the thickness; the study's
parameter files use **0.5 mm**. These four study fields are
absent for F0 and mandatory together for F1. A different configuration is rejected,
as are unknown, missing or duplicated parameters.

## Construction and boundaries

1. Import `housing.stl` and `flow-domain.stl`, after comparing their
   digests and triangle counts with the housing report.
2. Dilate the nominal domain by **1 mm**, to form a mask wide
   enough to reach the internal surfaces of the regularised housing.
3. Add the outlet extension: cylinder of radius **14 mm**, Y axis,
   transverse centre `(49, 0)` in X/Z, from **Y = 40 to Y = 81 mm** before smoothing.
   The final cut at Y = 80 mm happens only after regularisation.
4. Subtract an ideal rear closure of radius **35.5 mm**, below
   **Z = −3.75 mm**. The inlet remains extended beyond the future Z = 44 mm plane.
5. Subtract, **after adding the outlet**, the imported final housing, then
   the union of the compressor wheel, the shaft and the F0 nut.
6. Regularise the fluid volume with `Smoothen(0.125 mm)` then apply the
   inlet plane Z = 44 and outlet plane Y = 80. This last cut is limited
   to a cylinder of radius 16 mm surrounding the outlet extension; it does not
   cross the volute.

The dilated nominal mask is not an authorised definition of an internal wall.
The independent inspection must show that the fluid boundary follows the final
housing or the obstacles, except at the explicitly created idealised surfaces:
rear closure, inlet and outlet extension. If the mask bounds the fluid
anywhere else, the domain must be rejected. The exact input STLs and the dilated
mask are exported to allow this comparison.

The final 0.125 mm regularisation can move the fluid boundary; its
volume before and after treatment is recorded. The final cutting planes
are defined exactly in the implicit fields; their position in the
exported triangles remains to be verified. Reimporting the STLs into the kernel at
0.25 mm can also move their surfaces. The current proximity check
rejects physical face centroids more than **0.65 mm** from the
source housing or rotor. It does not bound the distance of all points of the
triangles; this limitation must be lifted before a ranking. A nominal
distance is not a clearance measurement.

The volume fields from `PicoGK.CalculateProperties` are kernel
diagnostics. They are not equivalent to the signed net volume of the STL, which includes the
oriented envelopes of the obstacles: for reference 003, these values are
respectively **261,762.52 mm³** and **231,942.59 mm³**. The independent inspection
must keep this distinction and use the signed net volume to describe
the exported fluid domain.

The first domain was rejected for a rear pocket of 61.12 mm³, small
islands near R34 and Z−8, and eight degenerate facets at the rear junction. The
closure radius therefore goes from 34 to 35.5 mm to enclose the lip of the mask.
The sources of this attempt are kept in
`work/bionic-f1-20261011/fluid-001-source`. No triangle is repaired or
removed. A global clipping of the outlet around Y42 is not added: this
region overlaps the volute, which must remain whole.

Attempt 003 passes the first surface-closure checks, but 482 reference faces remain outside the
admissible boundaries near the Z = 44 mm inlet edge. Smoothing an already
cut volume rounds this edge; a second cut does not restore the removed surface.
Attempt 004 therefore moves the inlet cut after smoothing and extends the outlet
to Y = 81 mm before its final cut at Y = 80 mm. Its previous sources are
kept in `work/bionic-f1-20261011/fluid-003-source`. The topology
and 0.65 mm proximity criteria remain identical for inspection 004.

This inspection keeps eight triangles outside the proximity criterion,
identical on the reference and the volute variant. Each connects two vertices
of the Z44 cap to a Z43.8 wall vertex. Their centroid distance is
0.665–0.671 mm; the wall vertex is 0.254–0.268 mm from the source housing.
Preparation 005 treats them explicitly as a **numerical inlet
junction**: two vertices on Z44, the third within Z43.5..44 and R21..22.5,
radii of all vertices ≤22.5 mm, edges ≤1.5 mm and centroid distance
to the housing ≤0.75 mm. Walls outside this junction remain subject to 0.65 mm.
The report counts the faces, their area and their maximum deviation. No triangle
is moved or removed. This admission serves only the pilot; the
sensitivity to inlet junctions remains to be qualified before a ranking.

The [later independent diagnostic](../evidence/fluid-004-topology-diagnostic.json)
**revokes the admission of domain 004 for CFD**: its revoxelisation
at 0.5 mm merges the wheel and the nut, although they are separated by at least 0.499 mm
according to their extreme Z planes. The rotor union creates five handles; the fluid
boundary has 29. A closed, oriented surface was therefore not enough.
The new check requires an outer envelope of Euler characteristic 2 and two distinct inner
obstacles of Euler characteristic 0 each, corresponding to the bores of the wheel
and the nut. This expectation comes from the separate sources, not from the result to be accepted.

Attempt 005 reduces the fluid voxel to 0.25 mm and the regularisation to 0.125 mm,
keeping the source STLs and the closures. It recovers the three separate rotor
solids, but eight exactly degenerate facets and four small
zero-volume shells cause the fluid to be rejected. Attempt 006 applies the same
grid offset `(0.173; 0.119; 0.071)` mm as the housing generator:
imports, fields, bounds and probes are transformed together, then the exports
return to the initial frame. Both 006 domains pass the strict
triangle checks and the check of the three expected shells; no triangle is
removed. The previous domains and
their receipts remain kept as rejected attempts. The rear passage of the
004 STL measures about 0.634 mm at the minimum of the 720 radii examined; this sampled
minimum demonstrates neither the global minimum nor its hydrodynamic resolution.

Boundary preparation 008 is then rejected by the
[independent rear-seal check](../evidence/rotor-label-diagnostic-008.json):
near the shaft, comparing only the distances to the rotor and to the housing
assigned fixed faces to the rotor. Preparation 009 also compares the
distance to the fixed cylindrical closure, without immobilising the neighbouring shaft.
It reserves the inlet/outlet labels for triangles coplanar to within 10⁻⁶ mm;
nearly coplanar edge facets remain walls. This threshold
matches the port check of the CFD preparer. The triangles and their
coordinates are kept in full.

## Execution

```sh
dotnet build twins/bionic-turbo-f1/cfd-geometry/CfdGeometry.csproj -c Release
dotnet twins/bionic-turbo-f1/cfd-geometry/bin/Release/net9.0/CfdGeometry.dll --self-test
dotnet twins/bionic-turbo-f1/cfd-geometry/bin/Release/net9.0/CfdGeometry.dll \
  HOUSING_RUN F0_ASSEMBLY_RUN NEW_OUTPUT_DIR
```

`HOUSING_RUN` contains the two STLs and `report.json`; `F0_ASSEMBLY_RUN` contains
`compressor-wheel.stl`, `shaft.stl`, `compressor-nut.stl` and its `report.json`.
The obstacle digests must also match the three F0 digests
pinned in the generator. The output directory must be new. An error
after its creation keeps the files already produced and writes `FAILED.json`.

The native execution must be wrapped by the machine lock
`parts/picogk-catalog/tools/run_part.py`, like the F0 assembly; no other
native PicoGK process may run at the same time. Compilation and
`--self-test` do not run native geometry.

The main exports are `fluid.stl`, `rotor-union.stl`, `housing-final.stl`,
`nominal-mask.stl`, `rear-seal.stl` and `outlet-extension.stl`. The other STL
copies and the two input reports keep the sources needed for the audit.
`report.json` records the digests, parameters, volumes, limits and native
probes. The probe `(15, 0, 40)` must be in the fluid; it does not by itself prove
that all fluid regions are connected.

The rotor union must keep the hypothetical clearances between its three parts:
three distinct solid envelopes are expected here. The fluid inspection must
correctly interpret the oriented surfaces of the obstacles and identify the
fluid components; it must neither remove triangles nor artificially connect the
obstacles to make a test pass.

What remains to be verified: the meshes, their topology, the proximity to the source
surfaces, the absence of spurious boundaries and the exhaustive classification of faces
into inlet, outlet, rotor and fixed wall. These checks precede any volume-mesh
preparation or declaration of a CFD result.
