# Actual preserved-taper finite-element fields: source-only image proposal

Both new linear cases are actually closed and independently reviewed by ROOT.
The exact coarse-FEA ROOT closure is
`15c76fbdfc9563bc296b4a567c1218bee99d6fe7a6889171c2514ec75d2ff287`. No arrays, field projection,
plotting import or render has run here. No old C1/H2 stress result is transferred.

Reuse the retained figure24 field renderer: two cases, true deformation times
one, a common orthographic camera, millimetre axes and field scales. Preserve
its original boundary-element stress projection and complete global IP/node
maxima checks. Boundary colours show the maximum of four integration-point
values in the adjacent element; they are not nodal stress extrapolation. Display
every actual boundary facet and every global IP tie. Each displacement facet is
coloured by its maximum corner displacement, while global checks include all
nodes, including midsides. Keep these distinctions in the English legend.

The actual rigid peak lies at negative X; the spring peak lies at positive X.
The existing 50 mm-wide XY inset is therefore mirrored for the rigid case.
Both insets retain real coordinates, the same width and colour scale. This is
a display crop only; no field computation, peak search or acceptance criterion
uses it. The two full views retain common axes and camera.

`image-proposal.json` contains the exact measured values, all peak records and
input paths. The renderer will use all 89,536 C3D10 elements/four-IP fields and
166,403 actual nodes, with the common actual mesh and protected evidence.
The original 219-file plotting runtime will be pinned before and after, including
a recapture of NumPy/Matplotlib/PIL after saving all three formats. Fixed metadata
and SVG salt will support reproducibility. Proposed bounds reuse the retained
120-second owned group, 95-second inner alarm and CPU90/91, one thread/no workers.

The raw BREP's post-Build law refusal remains. These are assumed-load linear
diagnostics, not strength, convergence, physical or manufacturing qualification.
No CAD, mesh, solver, energy or peak computation is repeated for this figure.
ROOT review and separate render GO are required after the minimal source and
actual coarse-FEA ROOT bindings are frozen. The durable result capsule is owned
by the separate capsule task; this directory does not duplicate its archives.

## Arming boundary

Preserve the pending plan/launch/command. After a separate ROOT GO, new armed
files may change only readiness, the actual GO path/hash and its added pin;
replace pending-plan path/hash in launch argv and inputs by the armed plan,
and replace pending-launch path/hash in the outer command. Require the entire
reverse of these declared substitutions to equal all three pending objects.
Do not change any scientific source, bounds, actual evidence, crop or output
path. Rehash all pins and verify fresh outputs before one owned draw.
