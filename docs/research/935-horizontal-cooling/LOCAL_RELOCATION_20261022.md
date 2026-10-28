# 935 bounded local relocation and adaptive fluid meshing — 2026-10-22

## Result in the software chain

This continues the [bounded surface repair](SURFACE_FACET_REPAIR_20261022.md)
at **PicoGK geometry → analysis-surface qualification → fluid meshing**. The
analysis surface now has **no triangle below quality 0.05**, down from 189,
then 46, then seven. Minimum quality is `0.050000877884919775` across all
873,288 triangles and 436,634 vertices. All face indices and vertex identities
are retained relative to the 46-poor-facet analysis baseline; the original
PicoGK design master is unchanged.

The complete original and retained-reference surface checks still pass in
both directions, at the unchanged **0.0225-source-unit bound** with its separate
**0.0025 numeric reserve**. Topology and self-intersection checks pass. These
checks qualify an analysis representation, not its historical identity,
physical scale, measured interfaces or manufacturing.

## Two local proposals and independent controls

The previously private proposal moves 45 vertices in two passes. SciPy SLSQP
maximizes the minimum incident-triangle quality in an averaged tangent plane,
within a 0.01-source-unit radius per move. Candidate points are quantized to
float32 before acceptance. An optimizer success flag alone is insufficient:
the actual point must improve local minimum quality, retain the quality floor
of incident faces, remain inside its numeric move bound and preserve local
normal orientation. The maximum total displacement in this proposal is
0.01999769 source units. Seven poor facets remain; its complete original and
reference certificates pass.

The first bundle exchange is refused because its face indices are int64 while
the existing handoff requires int32. A fresh bundle preserves every coordinate
and index value while normalizing the index dtype. Complete OFF/NPZ/STL
readback and a byte-identical STL replay pass. The rejected attempt remains
private; neither the geometry nor a reader's conditions are changed to hide it.

The second proposal uses one smaller pass, with a 0.005-source-unit radius.
It moves eight vertices and removes the last seven poor facets. Maximum
additional displacement is 0.00499954 source units. Complete serialization
readback passes before the unchanged native checker certifies both directions
against the original PicoGK surface and retained analysis reference. The
original check takes 188.62 seconds and the reference check 36.13 seconds.
No physical length tolerance is inferred from these numeric parameters.

The shared local functions are structurally identical to the first executed
private source; a source-hash/AST regression checks that extraction. Independent
controls cover a planar skinny triangle, an incident good face, a curved fan,
cancelled normals, invalid move radii, optimizer failure and nonfinite output.
A curved-patch move is not claimed to be a closest-surface projection. An
averaged tangent plane has no measured-interface or feature semantics; complete
independent certification remains mandatory for every real proposal.

## Adaptive volume experiment

The unchanged composition helper combines the certified rotor with the original
17,002 outer study-domain triangles. The resulting PLC has 445,137 vertices,
890,290 triangles and conditional volume `0.05140933407575627 m³`. Every SI
rotor coordinate/triangle is read back. Conversion still assumes 0.001 metres
per uncalibrated source unit; the square duct is not a historical 935 housing.

The new nodal size field is `clip(0.001 + 0.2*d, 0.001, 0.015)` in assumed SI,
where `d` is distance to the nearest input rotor vertex. This is a numerical
sizing definition, not an exact wall-distance certificate or measured flow
requirement. All rotor nodes receive 1 mm target sizes; TetGen linearly
interpolates the field from input nodes. Translation/unit-conversion and
invalid-input tests check this field.

The [TetGen 1.5 documentation](https://www.wias-berlin.de/software/tetgen/1.5/doc/manual/manual005.html)
describes metric refinement, radius-edge/dihedral targets and optimization.
The [MTR format](https://www.wias-berlin.de/software/tetgen/1.5/doc/manual/manual006.html)
defines one scalar target edge length per input node. The executed command is
`-pq1.4/10mO4/7S500000zCf`, with the frozen native 1.5.1 binary, 8 GiB address
space, 2 GiB per-file and 600-second limits. It requests radius-edge ratio 1.4,
minimum dihedral 10°, four optimization levels and at most 500,000 added points.
These requests are not reported as achieved mesh quality.

Boundary retriangulation is an explicit alternative to the previously refused
fixed-triangle volume. Its surface set must independently pass the original
geometric bounds; triangle IDs may differ. Complete solid-wall certification,
analytic outer-plane/marker checks, exact volume/connectivity audits and native
readback are required before admitting this representation. The original full
Foundation 13 quality command and dictionary remain unchanged. No previous
exact-boundary proof is reused for changed triangles, and the new mesh cannot
supply its own geometric reference.

The analytic unit-tetrahedron control retains all four marked planes, has 13
vertices and 14 positive tetrahedra, and differs from exact volume 1/6 by
`4.63e-18`. Its maximum boundary-plane error is zero. The native executable
explicitly opens the MTR file, and its inputs remain unchanged. This checks
metric input and geometric recovery, not finite-volume acceptance.

The real experiment completes in 47.30 seconds with 945,137 vertices,
3,995,994 tetrahedra and 1,199,698 boundary triangles. The 500,000-point budget
is exhausted: 154,704 additions are on input facets/segments, and 345,296 are
interior. Desired refinement is therefore not presumed complete. The native
consistency report alone is not an independent volume or wall certificate.

## Verification and remaining work

Native conversion at this stage is explicitly diagnostic. It copies the raw
output, restores four patch names and runs the unchanged full quality command
in the frozen, rootless, network-isolated Foundation 13 runtime. It runs no
flow equation and grants no geometry, volume, CFD or manufacturing admission.
The [checkpoint](local-relocation-20261022.json) records the observed quality
result and pending gates separately from surface qualification.

The adaptive tetrahedral case fails five unchanged native quality checks. It
has 4,363 faces above 70° nonorthogonality, 13,789 cells below determinant
0.001, fifteen highly skew faces, 1,696 weights below 0.05 and 38 neighbour-volume
ratios below 0.01. Native cell volumes are positive and its concavity check
passes; maximum skewness is 7.6573. These observations improve several counts
relative to the old fixed-wall tetrahedra but do not admit this mesh. Its
changed-wall geometric certificate and exact volume/native-readback audits
remain pending, and no flow equation is run.

The [executed sources](../../../twins/935-horizontal-cooling-system-f0/source/local-relocation-study-20261022/README.md)
reuse existing composition, serialization, exact predicates and native runtime.
Private images show the actual complete surface without display decimation;
they contain no flow or stress fields. Private scientific/delivery archives
retain the first refused dtype exchange, both proposals, native controls and
diagnostics. No new paid instance is created, and no private mesh is committed.
The focused 935 suite passes 209 tests with four optional skips, including
thirteen new numerical/source/scope tests. Strict documentation links also pass;
full Linux CI and publication evidence are recorded separately.

Before a new flow calculation, the selected graded mesh must pass all geometry,
marker, volume, connectivity, native-readback and unchanged full quality gates.
Then the original three-grid, mass-balance, pressure/torque stationarity and
convergence requirements apply. Physical scale, all seventeen mounting/drive
interfaces, hidden transmission, historical shroud/engine mounting, structural
spatial convergence, fatigue and bench tests remain open. PhysicsNeMo still has
no accepted fan reference dataset, and the complete system is not fabricable.
