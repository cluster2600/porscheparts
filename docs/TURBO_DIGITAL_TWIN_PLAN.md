# Data plan for the 993 Turbo digital twin

This document sets the scope before any computation on Vast.ai. It does not
declare that a part is accurate, fitted, tested, safe or releasable.

The specific collection of flow conditions, PET interfaces and supplier
envelopes is detailed in
[`TURBO_AIRFLOW_SIMULATION_DATA.md`](TURBO_AIRFLOW_SIMULATION_DATA.md). The
flow rates computed there are sensitivity bounds, not measurements.

## Collection status

| Data | Status | Level of use |
|---|---|---|
| Parallel twin-turbo architecture | Confirmed by Porsche | Context conditions |
| Engine displacement | 3,600 cm3 | Context conditions |
| Maximum boost of the base 993 Turbo | 0.8 bar | Public load case, not a design limit |
| Power/torque of the base version | 408 hp / 540 Nm | Public engine case, not a turbo map |
| K16 family and references 5316-988-6735/6 | Cross-checked manufacturer/distributors | Identification to be confirmed |
| K16 sub-assembly references | Supplier catalog | Bill-of-materials leads only |
| Envelope and mass of the complete K16 units | FVD: 280 x 190 x 210 mm; 5.76 kg left / 5.6 kg right | Mass and packaging check; supplier declaration |
| Right K16 wheel diameters | 54.96/48.97 mm turbine; 40.6/60.5 mm compressor | Parameterization bounds; supplier declaration, not aero profiles |
| A/R 8.00 | TurboMaster declaration on 5316-988-6735 | Not to be turned into a manufacturing dimension |
| Turbo-intercooler pressure hoses | FVD: 430 x 70 x 90 mm right / 430 x 70 x 115 mm left; 0.42 kg each | Envelope of supplier replacements; alternative EQ masses 0.52/0.44 kg |
| Intercooler air duct `993 110 340 54` | FVD: 600 x 280 x 50 mm; 0.9 kg | FVD in-house developed product; packaging reference, not OEM geometry |
| Reinforced intercooler bracket FVD11011050 | FVD: 255 x 80 x 23 mm; 0.2 kg | Aftermarket upgrade; strength and interfaces to be measured |
| Replacement intercooler `993 110 330 53` | AKS DASIS 177020T: core 260 x 270 x 60 mm; 7.06 kg | Replacement core, not the complete OEM envelope |
| Motorsport intercooler FVD110330 | FVD: 870 x 410 x 190 mm; 10.1 kg | Upgrade with installation modifications; packaging/thermal bound |
| Left heat shield `993 123 113 51` | FVD: 160 x 110 x 105 mm; 0.23 kg | Product envelope; thickness and fasteners unknown |
| 3D geometry and tolerances | Missing | Blocking |
| Flow/pressure/efficiency maps | Missing | Blocking for calibrated CFD |
| Materials and treatments | Missing per sub-assembly | Blocking for thermal/fatigue FEA |
| Clearances, rotor speed, balancing | Missing | Blocking for rotordynamics |

Porsche's public data confirm that the two turbochargers operate in parallel,
each feed one bank and include an integrated wastegate. They do not constitute
a definition drawing. See the sources recorded in `catalog/sources/` and the
target record `catalog/parts/993-turbocharger-k16-pair-0001.json`.

German-language research brought additional bounds: FVD publishes the
dimensions and masses of both K16 units, and Invasion Auto Products publishes
wheel references and a few diameters for the right K16. These data are now
traced in `catalog/reference/993-declared-part-data.json` and in the
corresponding source records. They allow an initial parameterization and a
consistency check; they replace neither a part, nor metrology, nor a
compressor map.

## Adjacent parts and new bounds

German-language research also produced bounds around the turbo. The hoses
`993 110 632 56` and `993 110 633 56` have an advertised envelope of 430 mm
long, 70 mm wide, with 90 mm high on the right and 115 mm on the left. The
duct `993 110 340 54` is advertised at 600 x 280 x 50 mm. These three FVD
listings state that they are products developed by FVD: they are useful for
packaging and for reconstructing an envelope, but do not give the OEM
cross-section, radii, wall thicknesses, end fittings or center distances.

For the intercooler, the German AKS DASIS 177020T listing associated with
`993 110 330 53` declares a 260 x 270 x 60 mm core and a mass of 7.06 kg.
These are the core dimensions, not those of the complete assembly. Another
bound is given by the Motorsport intercooler FVD110330: 870 x 410 x 190 mm and
10.1 kg, with advertised installation modifications. It must not be mixed
with the OEM.

The values are recorded in
`catalog/reference/993-declared-part-data.json`, with a distinct `source_id`
for each listing. Their status stays `declared`: none is a physical
measurement by the project. The Porsche Fanatics PET pages serve to confirm
the adjacent references and their positions, not their dimensions.

## What is still needed

### Identity and geometry

- legible photo of each nameplate and left/right identification;
- engine number, model year and exact configuration: Turbo, Turbo S, GT2 or
  tuned;
- metrology scan or CAD whose license allows use;
- common datum: rotor axis, flange planes, oil/air/exhaust interfaces;
- surfaces of the wheels, housings, volute, diffuser, wastegate and oil
  passages;
- radial/axial clearances, wall thicknesses, radii, roughness and tolerances.

A photograph, a PET exploded view or a seller listing does not allow these
surfaces to be deduced. Without a part or a licensed file, the CAD will remain
a parametric research volume, never a reproduction.

### Physics and operation

- engine operating points: speed, air flow, inlet/outlet pressure and
  temperature;
- exhaust gas pressure and temperature, back pressure and wastegate opening;
- oil pressure/temperature/flow and bearing cooling mode;
- maximum rotor speed and surge/choke limits;
- fatigue history, thermal cycles and wear state of a specimen.

## Vast.ai compute package

The `physicsml` container is already prepared for CAD, meshing, CalculiX,
OpenFOAM, JAX-FEM, PhysicsNeMo and DeepXDE. The first job must stay small and
reproducible:

1. validate a cold-side parametric geometry;
2. generate a mesh with a quality report;
3. run an OpenFOAM flow/pressure case;
4. run a thermal and structural case on the housing with CalculiX or
   JAX-FEM;
5. compare the outputs to reference data and keep the uncertainties;
6. only then train a Physics ML surrogate on solver-generated cases.

The language model can orchestrate the variants, check the files and
produce hypotheses. It replaces neither the solver, nor metrology, nor the
qualification of the additive process.

The first 0D normalizer for dyno data is in
`simulation/993-turbo-dyno/`. It converts the torque and power points,
computes BMEP and attaches an engine flow envelope to the published speeds.
Chassis points, tuner targets and reported engine curves stay separated by
dyno type; no whp to engine power conversion is applied.
`make turbo-dyno-check` must pass before using the package in a Vast.ai job.

The first case is now in
`simulation/993-k16-cold-side-baseline/`. It contains an editable OpenSCAD
geometry of a fixed diffuser and an OpenFOAM `blockMesh` + `simpleFoam`
harness. The mesh is a rectangular duct of equivalent cross-section: it serves
to validate the chain and compare variants, not to claim to reproduce the K16.
The commands are `make turbo-cold-side` then, in the cadsim container,
`blockMesh`, `checkMesh` and `simpleFoam`.

The next comparison set is in
`simulation/993-turbo-variants/`. Its single manifest generates three cases
with the same solver fields: `K16-OEM` control, `K16-24-HYBRID` sensitivity and
`K24-REFERENCE` high-flow sensitivity. The common flow rate is derived from an
estimated operating range; the diameters and lengths of the three diffusers
are research assumptions marked as such. Use `make turbo-variants`, then run
`blockMesh`, `checkMesh` and `simpleFoam` in each `cases/<variant>/` folder.
These cases validate neither tuner performance nor the geometry of a real
turbo.

## Recommended first demonstrator

The first demonstrator is a cold-side adapter or duct, non-rotating,
non-structural and amenable to an envelope check. The validation flow is:

1. CAD parameterization with ranges and uncertainties;
2. polymer fit-check prototype;
3. pressure-loss and temperature computation;
4. metal version only after choosing the material and the process;
5. metrology, pressure and temperature check on a suitable test rig.

The compressor/turbine wheels, the shaft, the bearings, the actuator and the
hot housing stay out of manufacturing until an engineering review and an
approved validation plan are available.

## Launch criterion

Vast.ai can be rented once the package contains at least:

- a geometry or a parameterization with explicit provenance;
- a boundary-conditions file and its units;
- a deterministic mesh and a reference case that runs locally;
- a matrix of unknowns and a stop rule in case of overrun;
- a manifest of sources, licenses, container versions and input hashes;
- an output folder separate from the repository, with checkpoint restart.

This threshold is met for a numerical study of a cold-side adapter. It is not
met for a validated twin of the complete turbocharger.
