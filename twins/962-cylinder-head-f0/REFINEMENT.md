# F0 routing without envelope: PicoGK refinement at 0.5 mm

This historical step keeps the frame and the reserved volumes, with no
continuous envelope. The [corrected gallery](GALLERY.md) shows the added body.
These renders come from the **meshes actually calculated and inspected**.
The reference geometry remains that of the unmeasured F0: four
valve/guide reservations and two spark plug wells, with no functional valvetrain or
mountings. Gray is a presentation shade; blue represents
the coolant volume, orange the volumes reserved for passages and spark plugs.
The colors do not represent a calculated temperature.

## Frame around the ports, before the envelope was added

![Exterior view of the F0 geometry at 0.5 mm](derived/views/exterior.png)

## Cutaway and internal passages

![Virtual cut: metal in gray, coolant in blue, dry volumes in orange](derived/views/cutaway.png)

## Coolant circuit and transparent body

![Geometric coolant circuit under the transparent body](derived/views/coolant.png)

## What actually changed

The [pipeline](source/refine_and_render.py) keeps the previous parameters,
generator and PicoGK binaries. Only the voxel goes from
0.75 to **0.5 mm** in three verified input copies. The native
runs are sequential under the shared lock. The new STL files and
inputs stay in `work/962-head/refinement-0p5/`; their inspection and the
published images are kept in `work/962-head/refinement-0p5-final/`.
The [report](derived/refinement-report.json) distinguishes the original geometric
references from the actual inputs executed at 0.5 mm.

| Geometric result | F0 at 0.75 mm | Refinement at 0.5 mm |
|---|---:|---:|
| Solid triangles after removing zero-area faces | 761,902 | 1,729,312 |
| Mesh metal volume | 353.185 cm³ | 352.985 cm³ |
| Mesh coolant volume | 46.180 cm³ | 46.741 cm³ |
| Minimum coolant–dry-volume distance, sampled | 3.598 mm | 3.575 mm |
| Number of probes for this distance | 197,322 | 447,288 |

The three refined meshes are closed, consistently oriented and
each has one surface component. The six opening probes are
checked again. This demonstrates neither fit, tightness nor wall thickness.
The volume values are not part measurements and do not give
a qualified material mass.

## Coolant/metal comparison: defects still open

The [previous diagnostic](COOLANT_BOUNDARIES.md) is reused on the new
surfaces. The inlet/outlet sections reach about 53.178 mm², with
a hydraulic diameter of 7.974 mm. These values remain F0 sections,
with no engine flow rate or pressure loss.

| Normal probe offset | Unassigned, 0.75 mm | Unassigned, 0.5 mm |
|---|---:|---:|
| 0.25 mm | 28 / 130,076 | 60 / 294,924 |
| 0.50 mm | 8 / 130,076 | 8 / 294,924 |
| 0.75 mm | 4 / 130,076 | 0 / 294,924 |
| 1.50 mm | 0 / 130,076 | 0 / 294,924 |

The probes change with the triangles: the raw counts do not compare
the same spatial points. At 0.25 mm, the unassigned fractions remain
close (about 0.022% and 0.020%). The gaps near the interface
are therefore not resolved by this refinement. At 1.5 mm, 160 refined probes
land in the coolant, against 36 previously: none of these probes
becomes a material validation.

Two resolutions are not enough to qualify convergence, the OEM
geometry or a shared interface for CHT. The report keeps all
physical qualifications at `false`. The next numerical step is a
conformal fluid/solid partition and a comparison at fixed positions,
before CFD/CHT; the donor interfaces remain to be measured.

## Reproduction

```sh
python twins/962-cylinder-head-f0/source/refine_and_render.py \
  work/962-head/bin/Engine.dll work/962-head/refinement-new
python -m unittest discover -s tests -p 'test_962*.py' -v
```

The binary and libraries must have the digests of the
[retained provenance](derived/runtime-provenance.json). The output
directory must be new. The inspections and renders can be replayed on
the retained native exports without rerunning the PicoGK calculation. The
`dotnet --version` measured here is 9.0.317; the initial dossier mentions
9.0.318. The new report distinguishes this measurement from the reference
provenance, whose upstream commit remains independently unverified.
