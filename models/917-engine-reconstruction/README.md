# Reconstruction of the 917 engine with PicoGK

Rework requested on 10 October 2026: final objective **functional engine**.
This new step uses the scan of the case with cylinders. The earlier
[archived work](../../docs/ARCHIVE.md) remains a method reference; its
hypothetical geometries and its results do not qualify this engine.
The exact variant, the displacement and the target speed remain to be determined.

The [longitudinal covers and lowered ducts](compact-packaging/README.md)
apply the video references to the 4V banks: six-opening plates, rounded roofs
and native branching ribs. Two wall thicknesses are compared at the same
candidate interfaces; physical qualification remains open.

The [detailed mechanical reconstruction](mechanical-detail/README.md) replaces
the accessory boxes with bodies carrying ducts, fins and mountings; it
adds a removable housing and branched supports in PicoGK, as well as
the forced-induction paths through the heat exchangers. The checks remain
numerical under assumptions, without manufacturing qualification.

The [gear timing drive of 12 October](cam-drive/README.md) continues the
4V twin-turbo engine: four trains with a positive 1/2 ratio, involute teeth and
branched PicoGK hubs. The supports, torque connections and materials remain
to be qualified; the dossier also keeps the first rejected meshing trial.

The [bionic cylinder head and its parametric valvetrain](head-bionic/README.md)
continue this design: gas/oil ducts, seats and guides, BCC
lattice, Bézier branches and roller cams. Bounded searches choose
the valve layout, the lift laws and the material volume.
The published preview shows only these new parametric geometries;
the scans and private meshes of the engine remain excluded from Git.

The [modern four-valve twin-turbo assembly](assembly/README.md) takes up
our air + oil cylinder heads and our bionic turbos: 119 geometric definitions
and 1,129 design occurrences. The missing shapes are parametric,
with branched ribs and manifolds. The interfaces and functional qualification
remain open; no manufacturing is authorised.

The [FIA reconciliation of 11 October](fia/README.md) uses the dimensions already
present in Git, re-read on the original homologation form no. 250. It corrects the
piston pin axis–crown distance to 43 mm and applies the reference
crankpin diameter of 52 mm. This correction rejects the provisional axial layout
of the cylinder; the FIA masses are also used for a load
comparison. The scanned specimen remains to be linked to the documented variant.

The [suite under assumptions](hypothesis/README.md), authorised the same day,
adds four PicoGK families and 48 instances, a controlled kinematics and
18 load scenarios with candidate materials. The check detects an
interference of the solid piston with the connecting rod small end, then verifies
the clearance of the same probes after building a hollow piston with bosses. The checks
remain partial; the assumptions and rejected versions are traceable.

## First executable step

[reconstruct.py](source/reconstruct.py) verifies the canonical SHA-256 of the scan,
transports its triangles without change of scale and calls
[the C# program](source/Program.cs), with PicoGK 2.3.0 and .NET 9.
PicoGK builds a **digital shell of the observed surfaces**, exported as
STL and VDB. The thickness of this shell is used to represent the scanned surface:
it does not define the thickness of a real case. No hole is interpreted
as an oil passage and no internal engine volume is invented.

The two default resolutions are 3 and 2 **scan units**. The STL
transport uses PicoGK's MM numerical convention without establishing the physical unit.
The shell thickness changes with resolution: the comparison is not
a convergence study at constant geometry.

An independent audit with trimesh verifies finite numbers, watertightness,
orientation, positive volume and the number of components. It measures the
source→shell and shell→source distances on 2,000 points in each direction,
with seed 917. The sampled maximum is not a Hausdorff bound.
It does not yet have a metrological acceptance tolerance.

The raw scan and all its derivatives remain outside Git in `work/`. Each run
requires a new directory; on failure, the artefacts are kept and the
status allows no manufacturing. Only the code and text results
without geometry may accompany a GitHub review.

```bash
PYTHON=/chemin/vers/python-avec-numpy-scipy-trimesh-rtree
DOTNET=/chemin/vers/dotnet-9

"$PYTHON" models/917-engine-reconstruction/source/reconstruct.py \
  --source /chemin/vers/917-engine-case-with-cylinders.obj \
  --output work/917-picogk/nouvelle-execution \
  --dotnet "$DOTNET"

"$PYTHON" tests/test_917_picogk_reconstruction.py -v
```

The files `report.json`, `status.json`, `build.log`, the PicoGK receipts and the
per-resolution audits make it possible to verify the run. The VDBs are the
geometric fields; the C# is the editable source. This step does not
produce a mechanical definition STEP.

## Local run of 10 October 2026

The [text record](execution-20261010.json) links the canonical scan, the sources,
the executable and the exports by SHA-256. PicoGK was run on the ARM64 Mac
with .NET 9.0.317. The two selected grids pass the geometric audit:

| Grid, scan units | STL triangles | Closed surface components | p95 distance source→shell | p95 distance shell→source |
|---|---:|---:|---:|---:|
| 3 | 1,162,808 | 167 | 3.426 | 3.472 |
| 2 | 2,605,872 | 118 | 2.157 | 2.270 |

The distances include the deliberate thickness of the digital shell and are
not a part reconstruction accuracy. The number of components
is not a mechanical bill of materials. The 1.5-unit trial is kept and
rejected: STL not watertight and four zero-area triangles. No automatic
repair was used to make it accepted. All physical qualification,
manufacturing and start-up gates remain closed.

The five targeted tests pass, the C# compilation finishes without warning or
error and the Markdown links are valid. `make check` ran 3,619 tests
(153 skipped) then stopped: two exact floating-point comparisons
in the old 993 impeller/stator dossiers and a missing `networkx` dependency
in the QA environment. After local installation of this dependency,
the two tests concerned pass; the two floating-point comparison failures
reproduce on unchanged files of `origin/main`. They are not
fixed in this 917 rework. The global check is therefore not green.

## Interfaces and load paths to establish before any functional part

| Assembly | Required measurements and interfaces | Load path or function to demonstrate |
|---|---|---|
| Case halves | joint faces, bolts and studs, datums, bearing housings and alignment, cylinder registers, oil circuits, output and engine mounts | bearing and cylinder loads into the case, fasteners, transmission and mounts |
| Cylinders and cylinder heads | bore, base register, cylinder head seat, studs and preload, seats/guides, chamber and ducts, thicknesses and fins | gas pressure and expansion into cylinder head, studs and case; heat rejection |
| Crankshaft and reciprocating assembly | main journals/crankpins and radii, axes, clearances, oil, central take-off, connecting rod centres, pins/pistons/rings, masses and balancing | pressure → piston → pin → connecting rod → crankpin → crankshaft and bearings |
| Valvetrain and accessories | cam profiles, supports and bearings, drive and timing, springs, clearances and contacts, pump and fan mountings | valve actuation and transient loads; oil and air flow |

These interfaces are not validated by the projected circles of the scan. The
specimen must be identified, the datums fixed, at least three independent
dimensions measured and the uncertainty documented. The internals require measurements
on a dismantled engine, authorised drawings and/or suitable tomography.
Missing data remain unknown; the model does not supply its own
inspection evidence.

## Materials and manufacturing: candidates, not qualified choices

| Family | Route to study | Qualification needed |
|---|---|---|
| Case and cylinder heads | aluminium; compare conventional manufacturing and LPBF, including AlSi10Mg, AlF357 and Aheadd CP1 depending on temperatures and machine | hot properties, conductivity, expansion, thermal fatigue, porosity, machined condition and sealing |
| Cylinders | body and friction surface to be defined together | wear, tribology, treatment or liner, bore distortion and heat transfer |
| Crankshaft, connecting rods, pistons and pins | conventional routes as priority, to compare with qualified alternatives | fatigue, defects, treatments, finish, balancing and individual inspection; no STL of the scan defines them |
| Valves, springs, bearings, rings, seals and fasteners | specialised components to specify or buy | supplier reference, allowable temperature/speed/load and interface compatibility |

[EOS](https://www.eos.info/metal-solutions/metal-materials/aluminium) documents
AlSi10Mg and AlF357 for additive manufacturing;
[Constellium](https://www.constellium.com/products/aluminium-powders/)
documents Aheadd CP1 for LPBF. These sources establish material leads,
not allowable values for this engine. The earlier dossiers
[F19](../../twins/reference-917-engine/manufacturing-routing-f19.json) and
[F49](../../twins/reference-917-engine/material-lpbf-qualification-f49.json)
remain studies to be reassessed, with no transfer of qualification.

For each candidate part: grade and batch, machine, parameters, orientation,
supports, powder removal, any heat treatment/HIP, machining
allowances, roughness, tolerances, CT/NDT inspection and test specimens of the final process.
Any titanium route must also document fatigue and galvanic isolation.
A functional engine does not require all its components to be printed.
Part decisions and their evidence will be carried by `catalog/parts/`.

## Next work and pass criteria

1. **Metrology**: identity and variant of the specimen, exact licence, unit,
   uncertainty, measured datums and interfaces. Criterion: interface contract
   verified independently on the same specimen.
2. **CAD per part**: case, cylinder, cylinder head then reciprocating assembly in PicoGK,
   with sourced dimensions/tolerances, assembly and internal circuits. Criterion:
   comparison with the scan and measurements, complete bill of materials and interfaces.
3. **Calculations**: kinematics/contact, lubrication, flow/thermal, stresses
   and fatigue under the loads of the chosen engine. Criterion: convergence,
   balance and physical correlation; archived numerical trials are not enough.
4. **Process**: test specimens and representative prototype, finishing and inspection
   on the selected machine. Criterion: allowable properties and inspection
   satisfying the plan approved by the engineering lead.
5. **Tests**: assembly, sealing, lubrication, external drive then
   progressive instrumented test bench. Criterion: documented professional review and
   validation of the plan before manufacturing or start-up of loaded parts.

No functional metal printing, start-up or power is validated
by this first reconstruction. The next data needed is a
metrology contract for the exact case/cylinders, before freezing their CAD.
