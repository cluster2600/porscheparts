# Visual surface repair of the 935 rotor

Private execution on 3 October 2026. The prepared rotor scan had 8657 boundary
edges in 58 contours. Abrupt automatic closure would create planar plates
through blades and hub. The repair below therefore produces a **closed visual
reference**, separate from the functional model and mechanical calculations.

## Visual references

Three public photographs/pages checked expected exterior topology: a horizontal
wheel with curved radial blades, central hub and overall flat fan volume.
They are neither downloaded nor included in the repository.

- [Design911 reproduction 935 wheel and funnel](https://www.design911.co.uk/p/fan-housing-with-fan-blades-porsche-935/)
- [AASE Sales 935/962 flat fan assembly](https://www.aasesales.com/products/noloc-j128-24000r-110746)
- [Jim Torres Racing reproduction assembly](https://jimtorresracing.com/for-sale/reproduction-flat-fan)

These sources document a silhouette and commercial components. They do not
calibrate a camera, supply specimen blade depth/thickness or establish variant
identity.

## Poisson closure rejected after visual review

The historical method produced `run-009`. The output is topologically closed,
but multiple-view review revealed artificial bridges among blades, hub and rear
face. It is **rejected as a visual reference**; its volume and mesh counts must
not be reused. It remains private solely as an attempt record.

The selected follow-up is the [PicoGK visual proxy](PICOGK_ROTOR_VISUAL_PROXY.en.md),
explicitly reconstructing observed disk, hub and ten blades without presenting
missing surfaces as measured.

## Historical method and private record

[photo_guided_surface_repair.py](../../../twins/935-horizontal-cooling-system-f0/source/photo_guided_surface_repair.py)
checks prepared OBJ SHA- 256, reduces the surface for calculation, estimates normals
and applies Screened Poisson reconstruction. It exports to a new private `work/`
directory and checks topology closure after welding STL vertices. Reconstruction
fragments below 0.1% of triangles are removed and recorded.

`run-009` retained two substantial components and removed 16 generated dust
triangles. These technical results do not compensate for visible rotor mismatch.
MeshLab detects no self-intersecting face, non-manifold edge face or non-manifold
vertex, but does not detect mechanically or visually invented topology.

Geometry, preview and execution receipt remain private under
`work/935-photo-guided-repair-20261003/run-009/`. Scans, coordinates and source
images remain outside Git.

## What repair leaves unresolved

The result supplies neither functional axis, hub/shaft, reliable local thickness,
rotor/housing clearance, support, drive nor datums. It is `solver_ready: false`
and cannot support mass, speed, stress, flow or a printing decision. Future
functional reconstruction will record repaired surfaces as assumptions and
replace them with independent measurements of seats, holes, thicknesses and
rear face.
