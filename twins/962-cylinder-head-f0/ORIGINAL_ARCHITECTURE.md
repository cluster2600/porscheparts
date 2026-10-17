# From the original to the modern study cylinder head

## What the sources show

The photographs from [Performance Developments, 962 C restoration, part 3](https://performancedevelopments.com/porsche-962c-race-engine-part-3/)
show individual cylinder heads, a four-valve chamber face,
two open spring housings per head and a lateral oval port shared
by a pair. The chamber view examined shows a central spark plug
opening. The builder states that they separated the jackets from the heads: these
photos therefore also document **their modification**, without establishing an exact
factory variant. [Part 2](https://performancedevelopments.com/porsche-962c-race-engine-part-2/)
shows the disassembled assemblies and the separate camshaft carriers.

Views examined: [chamber](https://performancedevelopments.com/wp-content/uploads/2017/04/123_2399.jpg),
[top](https://performancedevelopments.com/wp-content/uploads/2017/04/124_2408.jpg),
[ports](https://performancedevelopments.com/wp-content/uploads/2017/04/124_2409.jpg),
[disassembled assemblies](https://performancedevelopments.com/wp-content/uploads/2017/04/IMG_4108.jpg).
The pixels were inspected locally. They stay out of Git; no reuse license
was found. The [references and digests](source/architecture/references.json)
keep their provenance. A photo without scale establishes no dimension.

The manufacturer's dossier [40 Years Group C, pages 18–20](https://newsroom.porsche.com/dam/jcr:a6f33b52-c47d-47b4-98c1-7e963661f587/40%2520Years%2520Group%2520C.pdf)
describes aluminum, electron-beam-welded cylinder head/cylinder
assemblies, double-overhead-camshaft valvetrain and two independent coolant circuits
with one pump per side. It does not provide the mounting coordinates
or internal channels our CAD needs. The FIA archives
of the [initial dossier](README.md) concern the regulations and do not replace
metrology. Do not mix the initial air-cooled 962 IMSA with this
four-valve, water-cooled 962 C direction.

## Translation into the model

The [generator](source/architecture/Head962ArchitectureStudy.cs) takes up
the observed organization: two spring pockets, chamfered body and
ports shared in pairs. It adds four inclined guide reservations,
two ignition wells and a water jacket following the chamber and ports.
The twin ignition and the dimensions are **our proposal**.
This model is not a dimensioned reconstruction of the photographed cylinder head.

The conformal shape comes from native offsets, intersections and subtractions.
This construction allows paths close to the hot walls; it
does not demonstrate better flow or heat transfer. The layout of the
two terminals represents a supply/return study, to be checked against the
complete network of each bank. The model does not complete bearings, studs,
oil, inserted seats or valve actuation.

## PicoGK and its libraries

| Tool | Actual use or missing input |
| --- | --- |
| PicoGK 2.3.0 / native 26.2 | Booleans, offsets, body smoothing, connecting beams, voxelization at 0.5 mm and STL export executed. |
| [ShapeKernel](https://github.com/leap71/LEAP71_ShapeKernel) | `LocalFrame`, `BaseBox`, `BaseCylinder`, `LineModulation` and `SurfaceModulation` executed for the variable body and the oval lofts. Sources installed at the declared revision `554bce4…`, digests recorded. Apache-2.0 license. |
| [LatticeLibrary](https://github.com/leap71/LEAP71_LatticeLibrary) | `CuboidCell`, `BodyCentreLattice` and `ConstantBeamThickness` executed for open external ribs. Cells and diameter are assumptions, with no optimization under load. No lattice is placed in the coolant. |
| [Fasteners](https://github.com/joshmelnykcroft/PicoGK-Fasteners) | Installed. Threads and holes await the measured donor interfaces. |
| [HelixHeatX](https://github.com/leap71/LEAP71_HelixHeatX) | Installed; concerns the heat exchanger of the [thermal module](THERMAL_MODULE.md), not evidence of cylinder head cooling. |
| Native OpenVDB exchange | Three domains, one scalar distance field and one vector gradient field saved then read back by name; checks of domains and active values in both directions. |
| [SimulationExample](https://github.com/leap71/PicoGK_SimulationExample) | Available to prepare a simulation input. The present exchange uses `OpenVdbFile` directly, with no invented physical conditions and no CFD/CHT solver. |

Using every function without an identified need would add shapes
without physical justification. The shape library serves the cylinder head here;
the others stay tied to their problem and to the data they need.

The [ribbed variant](BIONIC_FIELDS.md) actually uses ShapeKernel,
LatticeLibrary and the VDB fields on the volumes of this cylinder head. It adds
material to the flanks: this is not a promise of weight reduction or thermal
gain. The [views of the variant](GALLERY.md) and its report remain at
unqualified-study status.

## Qwen contribution actually executed

The local Qwen is `Qwen2.5-Coder-1.5B-Instruct`, a 4-bit MLX conversion at a
frozen revision. The old base weights were missing: they were restored
from the expected public revision and their SHA-256 was verified. The
specialized PicoGK checkpoint **r3, step 240** was intact. No GPU
rental or change of the default model took place.

The [responses and receipts](derived/qwen-assistance/review.json) keep three
runs: full method with r3, full method with the base model,
then elliptical radius expression with the base model. The two
methods were invalid and are rejected without execution. Only the elliptical
expression was retained after an analytic check; the integration code was
corrected and built separately. This narrow assistance establishes no
mechanical or thermal expertise of the model.

## Step toward the 1,000 hp engine kit

The [gallery](GALLERY.md) presents the actual meshes. The
[report](derived/architecture-report.json) describes their independent check.
The material remains to be selected and qualified following the
[existing protocol](MATERIAL_QUALIFICATION.md): conductivity alone does not
choose a cylinder head alloy. Measurements of the
[donor interfaces](DONOR_METROLOGY.md), valvetrain, load cycle,
fuel, CFD/CHT and mechanical validation remain necessary for the
dyno/track kit. No 964/993 compatibility or power output is validated.
