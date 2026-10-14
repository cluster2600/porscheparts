# Cylinder head: observed architecture and calculated envelope

The first frame, then the rounded block, did not reproduce the visible
architecture of a 962 C cylinder head. This variant uses the
[examined photographs](ORIGINAL_ARCHITECTURE.md), ShapeKernel and PicoGK:
chamfered body, two open spring pockets, ports joined in pairs,
oval bosses and a conformal coolant envelope. The variant adds external BCC ribs with LatticeLibrary and
[exchanges the geometric fields in VDB](BIONIC_FIELDS.md). The images show the actual
calculated meshes; all dimensions remain assumptions.

## Exterior

![Architectural envelope calculated with ShapeKernel](derived/bionic-views/exterior.png)

## Envelope cutaway

![Actual cut of the mesh, coolant in blue and dry reservations in orange](derived/bionic-views/cutaway.png)

The virtual cut at X = 0.25 mm keeps the half facing away from the camera and
closes its cut faces. The orange volumes are reservations, not assembled
valves or spark plugs. Blue represents the coolant, with no temperature or
pressure result.

## Coolant inside the transparent body

![Conformal water jacket inside the transparent envelope](derived/bionic-views/coolant.png)

## Sources and limits

The [base generator](source/architecture/Head962ArchitectureStudy.cs) builds
the shapes in local frames, modulates their sections and subtracts the
reservations. Four inclined guides and two spark plug wells are represented.
The [rib runner](source/bionic/HeadBionicRunner.cs) adds complete cells
joined to the flanks, with no optimization under load.
The two wells are our modern adaptation; the chamber photo
examined shows a single central opening. Assembled seats, springs and spark plugs
are not represented by the orange volumes.

The jacket follows the chamber and gas reservations through offsets and Booleans.
The nominal coolant/dry-volume separation is 4.5 mm and the nominal outer skin
5 mm, before discretization and intersection: **these are not
qualified thicknesses**. Purging, depowdering,
supports, flow, fatigue and retention of guides/seats still need examination. The
[interface contract](interface-contract.json) remains unknown.

The [report of the ribbed variant](derived/bionic-report.json) keeps the
digests of sources, libraries, meshes, probes and images. A
closed mesh proves neither strength nor physical tightness.
Coolant circulation and thermal improvement are not validated.

The [views without ribs](derived/architecture-views/exterior.png) and their
[report](derived/architecture-report.json), the
[intermediate generic block](STOCK_ENVELOPE.md) and the
[refinement of the initial routing](REFINEMENT.md) remain available with their
original evidence. None of these models is a part that can be fitted to a 964/993.

## Sources and reproduction

The build and VDB readback of the variant follow
[BIONIC_FIELDS.md](BIONIC_FIELDS.md). The commands below reproduce
the base architecture without ribs.

The [build project](source/architecture/Engine.csproj) uses the
verified PicoGK runtime and the ShapeKernel sources identified in the
[references](source/architecture/references.json). It builds separately from the
previous generators. See the [dossier](ORIGINAL_ARCHITECTURE.md) for
the Qwen assistance, the libraries used and the missing inputs.

```sh
dotnet build twins/962-cylinder-head-f0/source/architecture/Engine.csproj \
  -p:PicoGKBinaryRoot=/path/to/the/verified-F0-runtime \
  -p:ShapeKernelRoot=/path/to/LEAP71_ShapeKernel \
  -o work/962-head/architecture-bin
```

Run this runner with the three specifications
[solid](source/architecture/solid.json), [coolant](source/architecture/coolant.json)
and [dry-passages](source/architecture/dry-passages.json)
**under the shared lock** of
[run_part.py](../../parts/picogk-catalog/tools/run_part.py), with the dylibs
of the verified runtime next to the binary. The retained local outputs are
`work/962-head/architecture-native-004/`. The inspection and views can be replayed:

```sh
python twins/962-cylinder-head-f0/source/architecture/inspect_and_render.py \
  work/962-head/architecture-native-004 \
  work/962-head/architecture-bin /path/to/LEAP71_ShapeKernel \
  work/962-head/architecture-inspected-new
```

The [inspection/render script](source/architecture/inspect_and_render.py) checks
the three volumes and reuses the closed virtual cut. The cut uses
[VTK ClipClosedSurface](https://vtk.org/doc/nightly/html/classvtkClipClosedSurface.html).
The STL files and binaries stay local; the sources and renders are
shareable. No manufacturing or engine performance is authorized.
