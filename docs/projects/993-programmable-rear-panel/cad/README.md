# Full rear panel — PicoGK concept model

**October 10, 2026 — visual concept model with provisional dimensions, authorized
as such. Original concept geometry, with no transcription of a Porsche part. No
mounting, material, functional assembly or manufacturing process validated.**

![Assembled and exploded concept model](preview/preview.png)

Open the [GLB 3D model](preview/rear-panel-concept.glb) in a glTF viewer or
Blender. The four objects stay separate. The colors are for review; the lens is
opaque in this preview, with no simulation of its optical transmission.

## Content and parameters

| Object | Representation | Limit |
|---|---|---|
| `lens` | Curved red lens with rounded corners | Neither the OEM outline nor the regulatory texture or optics are reproduced |
| `housing` | Hollow black frame | No fastening point, insert or load path defined |
| `rear-cover` | Separate rear cover | Retention, seal and cable pass-through to be designed after measurements |
| `display-envelope` | Green volume reserved for the display | Curved for convenience; it is neither a PCB nor an available matrix |

The [editable JSON](concept.json) drives the [C# generator](Program.cs).
All the values below are **visual choices**, not 993 dimensions:

| Parameter | Provisional value | Meaning |
|---|---:|---|
| Width × height | 800 × 90 mm | Outer rectangle, corners rounded to a 10 mm radius |
| Body depth | 45 mm | Local offset along Y, excluding the clearance/rear cover and the curvature |
| Bow | 35 mm | Parabolic curve between center and ends, with no vertical curvature |
| Lens / wall / cover | 3.6 / 3.6 / 3.6 mm | Concept thicknesses; no manufacturing tolerance |
| Assembly clearance | 1.5 mm | Visual separation, not a seal definition |
| Display allowance | 776 × 66 × 4 mm | 12 mm margin; 8 mm gap behind the lens |
| Voxel | 1.2 mm | Computation resolution, **unrelated to the LED pitch** |

STL frame: X = width, Y = toward the visible face, Z = height, in mm.
The GLB converts these coordinates to meters with Y up. The bounding box of the
generated assembly measures about **800 × 84.83 × 90 mm** along X/Y/Z, so the
45 mm parameter does not designate the overall depth.
The curved deformation keeps thicknesses along Y, not along the surface normal;
a true constant-thickness shell remains to be built after metrology. No pixel
count, production budget or power consumption is derived from this volume. The
[E0 coupon](../electronics/coupon.md) remains a separate study.

## Regenerate

Run with **.NET SDK 9.0.317, PicoGK 2.3.0, macOS arm64**. The NuGet package
brings its native macOS library; the Windows build it provides has not been
tested. The package used does not provide the native Linux runtime: do not
transpose these commands to Linux without a suitable PicoGK runtime.

From the repository root, with `dotnet` available:

```sh
dotnet restore docs/projects/993-programmable-rear-panel/cad/RearPanel.csproj --locked-mode
dotnet build docs/projects/993-programmable-rear-panel/cad/RearPanel.csproj -c Release --no-restore
dotnet docs/projects/993-programmable-rear-panel/cad/bin/Release/net9.0/RearPanel.dll --self-test docs/projects/993-programmable-rear-panel/cad/concept.json
dotnet docs/projects/993-programmable-rear-panel/cad/bin/Release/net9.0/RearPanel.dll docs/projects/993-programmable-rear-panel/cad/concept.json work/rear-panel-native
```

The last command writes four STL files in mm and `geometry.json`, a completion
report with SHA-256 digests. It refuses to overwrite an existing directory. A
directory without a completion report indicates an incomplete run. The STL
files stay in `work/`, outside Git; the GLB and the review image are versioned
here.

The [exporter](export.py) checks the STL files actually produced by PicoGK
before creating the GLB and the image. It requires NumPy, trimesh, networkx and
matplotlib (run verified with trimesh 5.1.0 and networkx 3.4.2, Python 3.10.11).
Use a dedicated Python environment; this export makes no network call:

```sh
python3 docs/projects/993-programmable-rear-panel/cad/export.py work/rear-panel-native work/rear-panel-preview
python3 -m unittest discover -s tests -p 'test_993_rear_panel_picogk.py' -v
```

After a change, regenerate, then replace the three files in `preview/`
**together** with those from the new export. The test detects sources or
exports that no longer match the report. The C# and the JSON are the editable
parametric source; the STL files and the GLB are derived meshes, not STEP
surfaces nor a mechanical CAD feature tree.

## Verification and next steps

The [machine report](preview/checks.json) records four closed volumes,
consistently oriented, each in one piece. The frame does have an opening (Euler
characteristic 0); the other three volumes have Euler 2. 830,988 native
triangles; the export removes 108 degenerate or duplicate faces from the
display volume without changing its bounds. The reloaded GLB keeps four objects
and the dimensions after unit conversion. Two successive native generations
produced the same STL digests in this environment. The C# self-test checks
eight invalid configurations and interior, exterior and hollow points. The
assembled/exploded view was reviewed visually.

These checks do not search for self-intersections and prove neither physical
sealing, nor strength, nor manufacturability. The vehicle interfaces, original
optical functions and electronic resolution remain unknown in the native
report. **No fictitious fastening is added.**

To turn this concept into functional CAD: acquire the measurements and datums of
the exact reference, replace the envelope with the transcribed outline, define
the bearing surfaces and fastenings with their load path, then choose the
optical/PCB stack-up from the coupon results. See the
[measurement sheet](../measurements.csv), the [scan plan](../mechanical-optical.md)
and the [validation](../validation.md).

## Provenance

Sources consulted on **October 10, 2026**: [PicoGK, official LEAP 71 project](https://github.com/leap71/PicoGK)
and [PicoGK 2.3.0 NuGet package](https://www.nuget.org/packages/PicoGK/2.3.0).
C# API `Library`, `IImplicit`, `Voxels` and `Mesh` checked in the XML
documentation of the installed package. The NuGet lock keeps the versions and
digests. PicoGK is licensed under Apache-2.0; no dependency binary is copied
into the repository. No scan, third-party model, manual or Porsche logo used.
The geometry and its original sources follow the [repository license](../../../../LICENSE).
