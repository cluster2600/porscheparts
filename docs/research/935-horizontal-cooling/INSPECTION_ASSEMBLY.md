# PicoGK inspection assembly — 12 October 2026

This step actually assembles in PicoGK the **935 candidate rotor**, the
**complete scan of its drive/bracket**, the **available case/cylinder scan**
and a **provisional intake shroud**. The components remain distinct in the
GLB and OpenUSD exports. No dynamic calculation or physical installation is
validated by this scene.

The engine case with cylinders that was found is identified in its source
file as a **917**, not as a 935. It serves here as comparative context. The
« 935 Xtreme Cyl head » scan contains a cylinder head; it does not define the
complete engine or its mountings. The target remains the 935 replica, then
its 993 adaptation. This scene does not replace the 935 engine reference that
is still missing.

## What was built

- The [C# program](../../../twins/935-horizontal-cooling-system-f0/source/picogk-inspection-assembly/Program.cs)
  imports and places the three existing meshes with `PicoGK.Mesh`. It keeps
  the triangle order and uses reversible rigid transforms, with an explicit
  uniform scale. Open surfaces stay open.
- The shroud is generated with two `PicoGK.Lattice` sections, then a voxel
  subtraction to keep the intake open. The cylinder and the flared lip
  overlap at their junction to avoid the non-manifold faces that appeared in
  the first attempt. It does not represent the complete guide distributing
  air over the six cylinders of a 935 engine.
- The [check and export](../../../twins/935-horizontal-cooling-system-f0/source/export_inspection_assembly.py)
  independently reads back the positions of **every transformed triangle**,
  checks the digests and the closure of the shroud, then verifies the GLB and
  USD exports in metres. The USD scene remains geometric: no joint or physical
  mass is assigned to an unknown interface.
- The [shaded views](../../../twins/935-horizontal-cooling-system-f0/source/render_inspection_assembly.py)
  reuse the VTK runtime already used for the 917 and keep **all the
  triangles**, without simplification. The colours distinguish the
  components, without designating a qualified alloy.

## Placement and limits

The units of the scans are still not confirmed. The display factor is
**1 mm per assumed source unit**. The matrices and their inverses allow the
assembly to be redone after calibration.

The engine pose uses its PCA for inspection, without establishing a datum.
The drive uses the provisional frame of a local surface of the bracket.
Placing it above the engine's bounding box ensures visual separation; it
creates no mounting contact and no load path.

The first placement of the rotor intersected an observed protrusion of the
drive. The second re-centres the rotor on a **cylindrical centre estimated on
a partial arc**, below the 330° required to qualify an axis in the existing
coordinator. This centre therefore remains a pose assumption. The bearing
surface, the mating splines, the axial retention and the fit are not defined
by this visual alignment. The rejected attempts are kept.

The visual review also shows blade tips and blends that are still irregular
in the inherited periodic candidate. This assembly keeps that geometry so it
can be inspected; it does not close its reconstruction.

The rotor/shroud clearance is checked for all angular positions by a
conservative radial envelope of the triangles, including their edges.
The other checks use triangle envelopes and bounding-box separations. An
envelope that overlaps flags a check to investigate further; it does not by
itself prove a collision. Interiors missing from the scans, thermal expansion
and deformations remain excluded.

## Reproduction without renting a machine

Reuse a local official PicoGK/.NET 9 installation compatible with the system
and supply a private case containing: `classification`,
`scale_verified: false`, `engine_context_family`, `assumptions`, `voxel_mm`,
`imports` and `shroud`. Each import contains its `id`, its private path, its
SHA-256, its classification and `source_to_assembly_mm`, a 4×4 matrix applied
to **column vectors**. The C# transposes it for the PicoGK API.
The case actually run and its parameters stay in the private archive.

```sh
dotnet build twins/935-horizontal-cooling-system-f0/source/picogk-inspection-assembly/InspectionAssembly.csproj \
  -c Release -p:PicoGKAssembly=/PRIVATE/PicoGK.dll
# Rendre la bibliothèque native officielle accessible au chargeur du système.
dotnet twins/935-horizontal-cooling-system-f0/source/picogk-inspection-assembly/bin/Release/net9.0/InspectionAssembly.dll \
  work/PRIVATE/case.json CASE_SHA256 work/PRIVATE/new-native-output
python twins/935-horizontal-cooling-system-f0/source/export_inspection_assembly.py \
  work/PRIVATE/new-native-output work/PRIVATE/new-exports
python twins/935-horizontal-cooling-system-f0/source/render_inspection_assembly.py \
  work/PRIVATE/new-native-output work/PRIVATE/new-exports work/PRIVATE/new-views
python -m unittest discover -s tests -p test_935_inspection_assembly.py -v
```

The French comment in this block reads: "Make the official native library
accessible to the system loader."

NumPy/trimesh and `usd-core` are used for the exports; VTK is used for the
views. The program refuses to overwrite an output and requires the ignored
`work/` for geometry. The C# also checks the digests, the bounded dimensions
and the absence of reflection or anisotropic deformation.

## Next 935 assembly step

Replace the 917 context with the geometry of the identified 935/930 engine
case, then establish its mounting faces and holes, the angle drive output
axis, the hub/shaft stack-up and the definition of the air guide. The same
assembler will allow the poses and the shroud to be redone without modifying
the scans. Validation of loads, transmission and cooling waits for these
interfaces; the earlier calculations do not qualify this new assembly.

The detailed results and the rejected attempts are private. The
[execution receipt](inspection-assembly-20261012.json) keeps the publishable
checks, digests and limits. No Vast machine was rented.
