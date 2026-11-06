# 935 — rotor closed under assumptions, and first solvers

[Dossier](README.md) · [Plan](RECONSTRUCTION_PLAN.md) ·
[Reference status](STATUS_20261012.md) · [Bench](BENCH_PROTOCOL.md)

## Result and status of the five stages

This continuation produces a **whole-rotor candidate**, masses and inertias
for ten material cards, an MRF/SST CFD pilot, a mechanical mesh of the whole
rotor and a geometric USD. It does not close the five stages of the system:
the complete mechanism, the mounting interfaces and the comparison with the
bench remain to be established. The target remains the 935; no 993
adaptation is part of this batch.

| Stage | Work delivered | Closure |
|---|---|---|
| 1. Metrology and reconstruction | Blade source acquired, cyclic registration of the contours, periodic repetition and explicitly hypothetical closures. | Scale to be confirmed by two dimensions per scan; independent comparison of the surfaces and an exact variant still needed. |
| 2. Parts and assembly | Rotor closed as one solid, STEP read back and FCStd with components and union. | Shafts, angle drive, bearings, engine mounting and guides do not yet form a functional assembly. |
| 3. Calculations | Masses/inertias, 80 kinetic scenarios, CFD pilot and 3D centrifugal calculation. | CFD/structural convergence, aerodynamic loads, thermal, modes, fatigue and transmission are not validated. |
| 4. Manufacturing | Regenerable source, candidate surfaces and the list of operations/checks below. | Provisional dossier; interfaces, tolerances, qualified processes and mechanical review are missing. |
| 5. Twin and bench | USD geometry, SI units, ten mass/inertia variants and prescribed rotation. | Rotor only; no dynamic simulation of the mechanism and no bench measurement used. |

The reference contracts are not fulfilled with these assumptions: the
17 interfaces remain unverified and the manufacturing and physical validation
authorisations remain at `false`.

## Reconstruction and rejected variants

The old observed ranges are the inputs. Their digest and the acquisition
transforms are kept. The scale of **1 mm per source unit** is a working
assumption, not a calibration; the precisions stated in the OBJ names do not
define their units.

A first closure used the median of several contours. It produced a valid
solid, but multi-view inspection revealed irregular spikes. **This variant is
rejected**, with its geometries, images and receipts kept. Volume convergence
is not enough to accept a shape.

The next candidate uses a better-covered blade. The contours are registered
by cyclic permutation before lofting; nine identical sectors are a
periodicity assumption. The sections missing at the roots/tips extend a
constant profile; the tip is trimmed circularly. The dish, its thickness, its
closure and the boss are provisional definitions. The blends do not
constitute qualified fillets. The other acquired blades remain available for
an independent comparison; they are not replaced in the original scans.

The FCStd contains the imported BRep components and an editable union.
The regenerable parameters and profiles are in the JSON case, the JSON
sections and the Python program; this FCStd is not a complete native history
of all the sections. The STEP is read back and checked for volume and
solidity.

## Requalified environment

Kali2 was unreachable at the known address. No certificate or secret was
changed. The work uses the Mac and local Linux containers, without a new Vast
rental.

| Tool | Runtime executed |
|---|---|
| .NET | SDK 9.0.318, installed in the batch's private folder |
| PicoGK C# | 2.3.0, official tag `PicoGK-v2.3.0`, commit `14c5384bcac57ede245021bb78e70d1445b40e3f` |
| PicoGK native | Core 26.2.0, build of 5 June 2026, macOS ARM64 |
| FreeCAD | 1.1.4, macOS ARM64; STEP/FCStd read back |
| Science/CAD | Linux AMD64: NumPy 2.5.2, SciPy 1.18.1, build123d 0.11.1, Gmsh 4.12.1 |
| CFD | OpenCFD OpenFOAM v2406, Linux ARM64 |
| Structure | CalculiX 2.21; emulated AMD64 and native ARM64 runs kept separate in the logs |
| USD | usd-core 25.11; ten variants and inertia tensors read back |

The versions/digests actually used are kept with the results. The old locks,
receipts and recipes are not modified. The PicoGK code and binaries come from
the [official LEAP 71 repository](https://github.com/leap71/PicoGK/tree/PicoGK-v2.3.0).
The authoring uses the standard USD Physics schemas; a readable export is not
a validation of an Omniverse simulation or of real operation.

## Conditional results for the periodic candidate

The closed BRep represents about **426.24 cm³** at the assumed scale.
After local correction of the two voxel artefacts, the fine surface is closed,
with one component and a consistent orientation. The volume change between
0.4 and 0.2 mm is **0.0149 %** and that of the principal inertias
**0.0133 %**. These checks concern the discretisation of the candidate, not
its historical fidelity or its manufacturing tolerances.

| Card | Assumed CAD mass | Polar inertia in the candidate frame |
|---|---:|---:|
| AlSi10Mg | 1.138 kg | 0.009408 kg·m² |
| WE43 | 0.780 kg | 0.006448 kg·m² |
| Ti‑6Al‑4V | 1.876 kg | 0.015504 kg·m² |

At 6,000 rpm, on the **same 1.5 mm hexahedral mesh**, the serial
calculations give the values below. Fixed clamping and an isotropic material
are assumed; aerodynamic pressure and temperature are not applied. The peak
is not an allowable stress and convergence under refinement is not
established.

| Card | Von Mises peak | Maximum displacement |
|---|---:|---:|
| AlSi10Mg | 122.6 MPa | 0.138 mm |
| WE43 | 84.0 MPa | 0.150 mm |
| Ti‑6Al‑4V | 202.1 MPa | 0.145 mm |

The first CFD point completes 400 iterations with a volumetric balance error
of about **0.0634 %**. The pressure remains unstable: this point is
**refused for the flow–pressure curve**, and no efficiency of the 935
installation is stated. The medium/fine meshes are prepared; their
convergence is not demonstrated by the coarse pilot.

## Reproducible commands and interfaces

The coordinator keeps three arguments: case, stage, new private folder.
The new stages are separate from the reconstruction of the observed surfaces:

```sh
python twins/935-horizontal-cooling-system-f0/source/run_reconstruction.py \
  /private/candidate-case.json candidate /private/new-components

python twins/935-horizontal-cooling-system-f0/source/finalize_candidate_cad.py \
  /private/components.step COMPONENTS_SHA256 /private/candidate-case.json /private/new-cad

dotnet build twins/935-horizontal-cooling-system-f0/source/picogk-candidate-rotor/CandidateRotor.csproj \
  -c Release -p:PicoGKAssembly=/private/runtime/PicoGK.dll

dotnet /private/CandidateRotor.dll /private/candidate.stl STL_SHA256 \
  0.4 /private/new-voxels 4,3,2

python twins/935-horizontal-cooling-system-f0/source/run_reconstruction.py \
  /private/cfd-case.json cfd-candidate /private/new-cfd

# Dans le runtime OpenCFD v2406, après chargement de son environnement :
bash twins/935-horizontal-cooling-system-f0/source/run_candidate_cfd.sh /private/new-cfd/artifacts/coarse

python twins/935-horizontal-cooling-system-f0/source/run_reconstruction.py \
  /private/fea-case.json fea-candidate /private/new-fea

# L'exécution série copie le deck vérifié vers un nouveau dossier de travail.
bash twins/935-horizontal-cooling-system-f0/source/run_candidate_fea.sh \
  /private/new-fea/artifacts/rotor.inp DECK_SHA256 /private/new-solve

python twins/935-horizontal-cooling-system-f0/source/run_reconstruction.py \
  /private/twin-case.json twin-candidate /private/new-twin
```

The two French comments in this block read: "In the OpenCFD v2406 runtime,
after loading its environment:" and "The serial run copies the verified deck
to a new working folder."

In a Git checkout, derived outputs must be in the ignored `work/`. The
`/private/` examples designate a private folder outside the repository.
An existing folder is refused. Each case references the digests of its
inputs; the coordinator saves failures without promoting the results.
The candidate's source STLs are in mm; the CFD STLs and the USD are in metres.
The CalculiX mesh uses N–mm–tonne–s, with stresses in MPa.

## Limits of the calculations and checks

Density turns the geometric volume and inertias into mass and mechanical
inertia. The ten previous cards remain comparators. WE43 keeps substitute
properties that are not qualified for the part. The braking scenarios use the
speeds, stopping times and imbalance assumed in the existing campaign; they
do not give an allowable speed.

The CFD pilot places the rotor in a hypothetical square duct:
**6,000 rpm, imposed flow of 0.6 m³/s**. This flow is a numerical bench
condition, not the predicted flow of the engine installation. The stations
use the area average of `rho*(p + |U|²/2)`; torque is calculated from the
fluid moment in the candidate frame. Acceptance also requires stability of
these quantities and the three meshes. The first attempts were kept: SI
conversion, fluid point position, concavity diagnostics and the quality
dictionary header were corrected. The `checkMesh -meshQuality` check applies
the explicit thresholds; the complete geometric diagnostics of the first mesh
remain kept separately. The wall layers, y+, the real housing and the engine
losses are not qualified by this pilot.

The tetrahedral attempts on the BRep failed on facet intersections. The
mechanical pilot therefore uses hexahedral cells whose centres lie in the
PicoGK signed field, with Gmsh checks of Jacobians, connectivity, bore and
volume. No fragment is silently deleted. Coarse grids that are disconnected
or that fill the bore are refused. The case run clamps a nominal bore; it
applies only centrifugal loading, with an isotropic material and an assumed
Poisson's ratio of 0.33. It is neither a real shaft/hub contact nor a fatigue
calculation.

The parallel ARM outputs that failed the force balance are rejected. The
replays and logs of each architecture are kept; the launcher now uses a
serial calculation in a new folder. A zero return code does not amount to
acceptance of the stresses or the speed.

Voxelisation at 0.2 mm also produced two small isolated polyhedra of twelve
triangles. They are identified as numerical artefacts of a single-solid input
BRep, never as fragments of the scan. An explicit local exclusion keeps the
coordinates/bytes of all other faces; the raw outputs and the rejected format
conversion remain kept. The closure and connectivity of the result are
re-checked after correction.

The USD checks masses, units, centres and inertia tensors after reading back.
The rotation is **kinematically prescribed**; it does not prove that the gears
transmit torque, that the bearings hold or that interferences have been
resolved.

## Manufacturing — dossier still provisional

| Item | Definition/check required before functional manufacturing |
|---|---|
| Rotor | Calibrate the scan, qualify roots/fillets/thicknesses, bore and retention; check deformations, prestressed modes, overspeed and fatigue; define balancing. |
| Hub/shaft | Fits, splines/key, clamping, axial retention, concentricity and transmission of the braking torque measured. |
| Angle drive | Gear teeth, ratio, centre distances, supports, backlash, lubrication, seals and heat dissipation defined; an outer envelope does not determine them. |
| Bracket/housing | Engine mounting drawings, load paths, stiffness, hot/cold clearances and maintenance access confirmed. |
| Air guides | Surfaces, leaks and connection to the engine established before concluding on installed cooling. |

For AlSi10Mg, WE43 or Ti‑6Al‑4V, the supplier must freeze process,
orientation, powder, treatments, finish machining and coupons. The dossier
must cover dimensional inspection, defects/porosity, fatigue, non-destructive
testing and balancing. For titanium, add galvanic isolation at the interfaces
and traceability of the treatments. Machining allowances and tolerances
remain to be defined with the chosen interfaces and process; the scan
precisions do not replace them.

The [bench protocol](BENCH_PROTOCOL.md) must then be run on a reviewed
mechanical assembly, with measurement points reserved for correlation.
An identified donor/recipient, reference dimensions and an accessible
workshop or bench are needed to close the installation replica and the
physical validation. Neither the closed volume, nor the software tests, nor
the USD replace this evidence.

The results, cases, sources of each attempt and derivatives stay in the
[private repository](https://github.com/cluster2600/porscheparts-935-private).
The public Git contains only programs, tests and documentation.
