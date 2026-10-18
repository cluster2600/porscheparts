# Intermediate step: generic solid envelope

The first render showed a frame around the ports. **The outer
envelope was missing.** The new variant adds a real continuous
volume, then subtracts the coolant and gas volumes using PicoGK.
The views below use the new calculated and inspected solid.

## Exterior

![Continuous envelope of the study cylinder head](derived/enclosed-views/exterior.png)

## Envelope cutaway

![Virtual cut of the body, coolant in blue and dry volumes in orange](derived/enclosed-views/cutaway.png)

The virtual cut at X = 0.25 mm keeps the half facing away from the camera and
closes its cut faces. The orange volumes are reservations, not assembled
valves or spark plugs. Blue represents the coolant, with no temperature or
pressure result.

## Coolant inside the transparent body

![Coolant circuit inside the transparent envelope](derived/enclosed-views/coolant.png)

## Added body, still to be developed

The [new generator](../../parts/picogk-catalog/engine/Head962EnclosedStudy.cs)
reuses the F0 passages and adds a rounded body **160 × 160 × 90 mm**,
corner radius **8 mm**, at a 0.5 mm voxel. These are demonstration
assumptions, not Porsche measurements. The four guide reservations
and the two spark plug wells remain open. The seven additional probes
confirm material on the flanks, the roof and in the regions where the
frame alone left a void.

The metal volume is about **2,086.73 cm³**, against 352.98 cm³ for
the refined frame. It is a **solid starting body**, to be lightened based on
loads and thermal behavior; it is not a validated bionic
optimization. Valvetrain, seats, studs, joints and lubrication
are not completed by this envelope. The
[interface contract](interface-contract.json) remains unknown and unqualified.

The [report](derived/enclosed-report.json) keeps sources, binaries,
mesh, probes and image digests. The mesh is closed, consistently
oriented and made of one surface component. This
qualifies neither thickness, strength nor physical tightness.
The coolant/metal classifications near the surfaces remain unresolved.

The [earlier routing refinement](REFINEMENT.md) is kept separately,
with its images and provenance. It is no longer presented as a cylinder head
with an envelope.

## Sources and reproduction

The [build project](source/enclosed/Engine.csproj) uses the
verified F0 binary libraries; the old local path of the PicoGK
checkout is no longer available. No kernel change is needed.

```sh
dotnet build twins/962-cylinder-head-f0/source/enclosed/Engine.csproj \
  -p:PicoGKBinaryRoot=/path/to/the/verified-F0-runtime \
  -o work/962-head/enclosed-bin
```

Run this runner with [enclosed-solid.json](source/enclosed-solid.json)
**under the shared lock** of
[run_part.py](../../parts/picogk-catalog/tools/run_part.py), with the dylibs
of the verified runtime next to the binary. The retained local outputs are
`work/962-head/enclosed-native/`. The inspection and views can be replayed:

```sh
python twins/962-cylinder-head-f0/source/enclosed/render_enclosed.py \
  work/962-head/enclosed-native \
  work/962-head/refinement-0p5-final/inspected \
  work/962-head/enclosed-bin work/962-head/enclosed-inspected-new
```

The [inspection/render script](source/enclosed/render_enclosed.py) checks
that the solid and the virtual cut are closed. The cut uses
[VTK ClipClosedSurface](https://vtk.org/doc/nightly/html/classvtkClipClosedSurface.html).
The STL files and binaries stay local; the sources and renders are
shareable. No manufacturing or engine performance is authorized.
