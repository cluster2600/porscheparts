<a id="culasse-4-l-sp95--géométrie-dimensionnée-pour-le-débit-deau"></a>

# 4 L SP95 head: geometry sized for water flow

This variant transfers the [Mezger 4 L/SP95 budget](MEZGER_4L_SP95_EN.md) into
new native PicoGK geometry. It retains four valve passages, two ignition
reservations, ShapeKernel lofts and external LatticeLibrary BCC ribs.
The previous models and their receipts remain intact.

![Chamber view: four valve passages and two proposed wells](derived/flow4l/views/chamber.png)

<a id="changements-effectivement-générés"></a>

## Changes actually generated

- Chamber envelope with semiaxes 49 × 49 × 13 mm and a 59 mm base radius,
  for the assumed 102 mm bore. This cavity does not establish the engine's
  clearance volume or compression ratio.
- Two water ports of **22 mm** nominal diameter, versus 10 mm in the previous
  variant. These are computational terminations with no installed fittings.
- A 12 mm central ignition well and a second 10 mm well at X=38 mm.
  These proposed envelopes are neither threads nor a spark-plug selection.
- A bifurcated supply around the second ignition reservation. The first
  attempt left a blind segment near its protected volume.
- Smoothing of the dry and water volumes **before** final subtraction from
  the metal. The metal wall in contact with water is not smoothed afterward.
- 36 external BCC cells, 12 × 14 × 14 mm, with 3.5 mm strut diameter.
  Their shape does not come from mechanical optimization under combustion loads.

The axes are local to the study. No cylinder pitch, bank axis, assembly plane
or donor stud coordinates are inferred from these dimensions.
The overall envelope of approximately 152 × 150 × 90 mm must in particular
be checked against the actual layout of adjacent heads.

The [design contract](source/flow4l/design.json) lists the required interfaces
and load path. The precise engine variant, fasteners, seats, valvetrain,
valve seats/guides, spark plugs and oil remain unknown.
The geometry is not a head that can be installed.

<a id="contrôles-sur-les-fichiers-réellement-produits"></a>

## Checks on the actual generated files

The [independent report](derived/flow4l/study-report.json) links sources,
binaries, STL files, VDB and images by digest. The [additional provenance](derived/flow4l/provenance.json)
retains the SDK and shared sources. The three domains are closed, oriented
and each has one surface component after recorded removal of degenerate faces.

| Geometric quantity | Result |
|---|---:|
| Metal volume | 952.07 cm³ |
| Water volume | 148.93 cm³ |
| Dry volumes, including extensions | 487.11 cm³ |
| Minimum sampled water/dry separation | 4.439 mm |
| Inlet / outlet section | 375.44 / 375.23 mm² |
| Inlet / outlet hydraulic diameter | 21.48 / 21.56 mm |
| Mean velocity at 48.62 L/min | 2.159 / 2.160 m/s |

The 48.62 L/min per head remains the scenario assuming 49.03 kW per head
and a 15 K water-temperature rise. It is not measured on an engine.
The section increased approximately fivefold; this does not determine
internal pressure loss or flow distribution among hot areas.

![Water volume inside the transparent envelope](derived/flow4l/views/coolant.png)

The probes at 0.25 mm give zero unassigned points, but still **two overlaps**
among 607,232 probes. The other probing distances are retained in the report.
This is still not a certified conformal CHT interface; closure and sampling
are insufficient to validate a wall or sealing.

The first rejected attempt is preserved in the
[component diagnostic](derived/flow4l/rejected/native-001-components.json).
Complete sources and outputs for each attempt remain in local
`work/962-flow4l/run-*` directories without overwriting.

<a id="échange-vdb-et-préparation-hydraulique"></a>

## VDB exchange and hydraulic preparation

PicoGK saved and read back the three domains, distance field and gradient
identically, using native comparison and verification of every active value
in both directions. The latter two fields are **geometric**, with no
calculated temperature, pressure or velocity.

A Cartesian derivative of the water is also exported using native
`Voxels.bIsInside` classification at cell centers. At 2 mm, two isolated cells
cause this derivative to be rejected. At 1 mm, the 149,980 cells are connected,
but the volume mesh then fails `checkMesh` on 708 cell determinants.
Direct Gmsh tetrahedralization of the surface is also rejected by the full
checks. No threshold is lowered.

The derived meshing surface remains closed: 61,504 triangles, maximum measured
vertex deviation of 0.238 mm and volume deviation of −0.150%.
This sampled check is not a global Hausdorff bound.
Surface snapping with `snappyHexMesh` in OpenFOAM **Foundation 13** produces
138,400 cells and one region, but the full check rejects 720 concave cells
and one excessively warped face. A new face-conforming representation then
uses native OpenFOAM face centers and bases: 1,612,960 positive-volume
tetrahedra, with a 0.0207% volume deviation from the parent. It is also
rejected: five checks fail, including 9,055 determinants and seven
excessively warped faces.

The [meshing report](derived/flow4l/meshing-report.json) retains case digests
and the main logs. The blocking check prevented solver launch on these
meshes. No threshold was lowered and no flow iteration is credited.
Pressure loss, flow distribution, thermal efficiency and engine power
remain to be established.

## Reproduction

The [C# generator](source/flow4l/HeadFlow4LStudy.cs),
[export program](source/flow4l/HeadFlowRunner.cs) and
[driver](source/flow4l/run_study.py) use the documented PicoGK installation.
The verified runtime uses SDK 9.0.319, .NET 9.0.21 and a 0.5 mm voxel.
ShapeKernel and LatticeLibrary are compared with their existing references.
The driver acquires the catalog's shared native lock.

```sh
python3 twins/962-cylinder-head-f0/source/flow4l/run_study.py \
  /path/to/PicoGK work/962-flow4l/new-run
python3 -m unittest discover -s tests -p 'test_962_flow4l.py' -v
```

Large STL/VDB outputs remain local derived files; their digests and renders
are versioned. No third-party scan or manual, model weights or vendor binary
is added to the repository.

A local review archive collects the three inspected STL files, geometric
VDB, this variant's sources, reports and renders:
`work/962-flow4l/delivery-001/mezger-4l-sp95-head-study.zip`.
The [delivery receipt](derived/flow4l/delivery-report.json) records its
95,532,176 bytes and digests of all 37 files, reread after compression.
This archive accompanies the complete repository for reproduction: shared
helpers and PicoGK dependencies remain those of the repository and verified
installation. It contains no solver pressure, velocity or temperature result
and no manufacturing dossier.

<a id="suite-de-la-chaîne-doutils"></a>

## Continuing the toolchain

The [repository workflow](../../docs/TOOLCHAIN.md) remains applicable.
The hydraulic stage must produce an accepted mesh, a converged solution
and a flow balance before a numerical result can be credited.
CHT then requires a conformal solid/water partition, heat fluxes and
material thermal properties as functions of temperature.

CalculiX cannot establish engine strength with invented studs, contacts and
preloads. Measured interfaces and the pressure cycle condition this analysis.
LPBF alloy selection, manufacturing simulation, coupons, inspection,
pressure tests and engine bench testing remain open; every qualification
flag remains false.
