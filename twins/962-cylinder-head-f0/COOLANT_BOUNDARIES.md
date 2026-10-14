# F0: coolant sections and interface diagnostic

**The check uses the PicoGK STL files actually generated, with their
digests kept. It does not modify the cylinder head.** The circuit remains an
unmeasured study, with no qualified hydraulic performance or manufacturing.

The [script](source/audit_coolant_boundaries.py) extracts the two sections at
the X = −80 and +80 mm planes of the F0 envelope. These planes belong to the
hypothetical model; they are not donor fittings. The cuts are
triangulated after checking for a single closed loop, with no vertex of degree
other than two. The [report](derived/boundary-audit.json) links sources,
meshes, outputs and runtime. The cut surfaces `inlet.vtp` and
`outlet.vtp` stay local and can be opened in ParaView.

## Results on the retained F0

| Geometric section | Area | Perimeter | Hydraulic diameter `4A/P` |
|---|---:|---:|---:|
| Inlet, X = −80 mm | 52.5045 mm² | 26.2833 mm | 7.9906 mm |
| Outlet, X = +80 mm | 52.4872 mm² | 26.2195 mm | 8.0074 mm |

These values describe the mesh sections, not machined dimensions
or a tolerance. The hydraulic diameter is not a drill diameter.
The small inlet/outlet difference does not establish a pressure loss.
The coolant volume does not exceed the F0 envelope in Y or Z; it extends
through the two X terminations. This envelope check is not an
exhaustive wall-tightness check.

## Coolant/metal probing: anomaly retained

From the centers of the coolant triangles, move a probe along the
outward normal of the face. Classify independently its signed distance
to the two surfaces, coolant and metal. Four offsets are examined; a zero
sign is classified as outside. Probes may land in another branch
of the same circuit: these cases do not become material validations.

| Offset | Metal only | Coolant only | In both | In neither |
|---|---:|---:|---:|---:|
| 0.25 mm | 130,048 | 0 | 0 | 28 |
| 0.50 mm | 130,062 | 6 | 0 | 8 |
| 0.75 mm | 130,062 | 10 | 0 | 4 |
| 1.50 mm | 130,040 | 36 | 0 | 0 |

Each row covers **130,076 probes**. The **1,480 face centers**
within the 1.5 mm guard near the X terminations are excluded: the wall around
the fittings is therefore not inspected by this probing. The centers, normals
and probe positions are those of the mesh, with no photographic registration.

![Projection of the unassigned probes](derived/boundary-probes.png)

The magenta points are the probes inside neither of the two triangulated
volumes, projected on XY. Their number falls as the offset grows, but this
is not convergence: the mesh and its 0.75 mm voxel are unchanged.
Changing the probe distance does not refine the geometry.

**Coolant/metal conformity remains not validated.** At small offsets,
gaps are observed near junctions. At 1.5 mm, the 36 probes outside the metal
are in the coolant. These classifications prove neither a physical leak nor a closed
wall, and do not give a minimum thickness. The separate surfaces are
not accepted as a shared CHT mesh interface.

## Next hydraulic step

Locate the affected cells/interfaces, then compare a voxel refinement
on the same geometry, with new evidence linked to each output.
Then build a fluid/solid partition with a shared interface, with
identified inlet, outlet and walls. Do not move the surfaces artificially
to pass the check, nor hide the unassigned points.

CFD still requires flow rate or pump curve, coolant composition,
inlet temperature/pressure, roughness and junction behavior.
CHT adds heat flux/chamber, material laws and external conditions.
Pressures, flow rate and heat load remain unknown in the
[F0 contract](interface-contract.json). No pressure loss, boiling,
powder removal, wall strength or thermal improvement is calculated.

## Reproduction and negative controls

With the NumPy/trimesh/VTK/Matplotlib runtime already used for F0:

```sh
python twins/962-cylinder-head-f0/source/audit_coolant_boundaries.py \
  work/962-head/delivery work/962-head/boundary-audit-new
python -m unittest discover -s tests -p 'test_962*.py' -v
```

The output directory must be new and the STL files must match the
original digests. A modified F0 source is also refused. Independent
controls check a cube cut (analytic area and perimeter),
an open or disconnected section, an analytic wall with a piece removed, a probe
returning into the coolant, an overlap and non-finite inputs. The
diagnostic remains unqualified even when its tool's tests pass.

The cutting method relies on the
[VTK 9.7 documentation of ContourTriangulator](https://vtk.org/doc/nightly/release/9.7/html/classvtkContourTriangulator.html).
Its cut triangles do not make a quality CFD mesh.
