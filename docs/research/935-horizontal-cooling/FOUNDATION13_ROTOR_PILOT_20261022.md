# 935 Foundation 13 rotor pilot — 2026-10-22

## Scope and software-chain position

This continues the root README workflow after the
[interior-star study](INTERIOR_STAR_CONTINUATION_20261022.md): the retained
PicoGK design master and independently checked analysis surface enter native
OpenFOAM case preparation. No geometry is regenerated for an unchanged design.
Qwen, Warp, PhysicsNeMo and rendering are not prerequisites for this calculation.
The 993 programme remains separate.

This is a conditional rotor/duct study, not the historical 935 engine assembly.
Physical scale, shaft registration, the 17 mechanical interfaces and the hidden
transmission remain unverified. The existing structural calculation has not yet
received CFD pressure loads; strength, fatigue and manufacturing remain open.

## Use the installed solver family

The existing `prepare_candidate_cfd.py` remains frozen for **OpenCFD v2406**.
Kali1's verified image actually contains **OpenFOAM Foundation 13**, build
`13-18870c24d21c`. Its `simpleFoam` file is a compatibility shell launcher;
the executed solver is `foamRun -solver incompressibleFluid`.

- Image index: `a1db60cbf61bbcca52c171e50cab01ed0b6ec860b227e7c5fc50f7b809659b4f`.
- Native `foamRun`: `96aeb56a4fb12fae411076235ca7469f988fc09c0a2eeb288f18cfce3522aead`.
- The existing rootless runtime retains a read-only root, one writable case,
  an isolated network namespace, UID 1000, dropped capabilities and no Docker daemon.
- Runs use an 8 GiB address-space limit; the rotor probe has a 1,800 s wall limit.

The new adapter reuses the existing duct generator, retaining its parent recipe
receipts, then writes Foundation's `physicalProperties`, `momentumTransport`
and `MRFnoSlip` rotor boundary. The axis and signed speed are explicit. The
native `topoSet` compatibility utility creates the cylindrical cell zone;
its deprecation warning is retained.

Primary references: [Foundation 13 momentum transport](https://doc.cfd.direct/openfoam/user-guide-v13/turbulence)
and the actual image's `mixerVessel2DMRF` tutorial, `surfaceFieldValue` sources
and `surfaceCheck` sources. The private runtime snapshot records the files and
their hashes. Foundation uses `patch inlet` and `operation average; weightField phi`
for flux weighting; OpenCFD's `regionType` and `weightedAverage` syntax is not assumed.

## Analytical rotating-wall and torque control

Before the rotor calculation, three annular 2D meshes exercise the actual MRF
wall boundary and force function. The stationary outer wall has radius
0.1 m; the inner wall has radius 0.05 m and rotates at 60 rpm. Depth is 0.01 m,
kinematic viscosity 0.001 m²/s and density **3 kg/m³**, deliberately non-unity
to check force normalization. This laminar control does not validate SST.

The independent solution is `u_theta = A*r + B/r`, where
`B = Omega*Ri²*Ro²/(Ro²-Ri²)` and `A = -B/Ro²`.
The fluid moment on the rotor is
`Mz = -4*pi*rho*nu*Omega*L*Ri²*Ro²/(Ro²-Ri²)`.

| Cells | Relative velocity L2 | Torque relative error |
|---:|---:|---:|
| 256 | 3.86% | 0.675% |
| 1,024 | 0.890% | 0.287% |
| 4,096 | 0.211% | 0.0953% |

The initial 1,000-iteration run is **rejected**: fine-grid torque still changes
by `5.58e-5` over the final five samples, above the predeclared `1e-5` limit.
A fresh 2,000-iteration run passes the **unchanged** contract. The final fine-grid
range is `3.51e-9`; fine/medium torque differs by 0.192%. Every cell centre and
velocity is compared, not a selected line. The public reassessment requires
all mesh logs and original input hashes. Both trials and their sources are retained.

Foundation's non-porous `forces.dat` has **13 numeric columns**, including time,
two force vectors and two moment vectors. Torque uses the pressure and viscous
z moments; the v2406 `moment.dat` parser is not reused.

## Exact SI transport and conflicting surface diagnostics

The retained analysis boundary has 436,712 vertices and 873,444 triangles:

- PicoGK design master STL: `f32bbabab3e5f7d9ca7c5283d18703cfe7cedbd3eb2c72a57a1c222c0a9df1e5`.
- Analysis STL: `1fcf180cf1f8425a56d23114a487d72a2f2e15003fc644fc2f282078ab6422d5`.
- Indexed bundle: `bc0698eeb329853020c82f3dcef013d547f19f6e4bbc234f3f64cc0cc1f43aec`.

Assuming **0.001 m/source unit**, the adapter writes a 17-digit indexed OBJ.
It reads every coordinate and triangle back exactly against the float64-scaled
array. This avoids an additional float32 rounding when scaling a binary STL to SI.
It does not establish the physical scale of the original scan.

The actual SI OBJ hash is
`5eb9ee8a73b140198013fe511916c150316acc8e31174a2ca1fea4bac4db3e44`.
Native `surfaceCheck` confirms the counts, closure, one connected region and no
illegal triangles, but reports **74 approximate self-intersection hits** and
four nearby-point pairs. The first meshing attempt is stopped for investigation.

A separate **CGAL 6.2.1 exact-predicate** audit of this actual SI OBJ finds
**zero intersecting face pairs** across all faces. The checker accepts a closed
cube, rejects crossing cubes with 15 pairs, and rejects an open cube. This
resolves the approximate hit discrepancy without altering the surface or
silencing the OpenFOAM diagnostic. The retained CGAL 5.5.1 envelope proof of the
original analysis surface is unchanged; the new SI audit does not replace it.

## First fluid mesh and exploratory calculation

The stated hypotheses are a square duct of width 0.36 m and length 0.4 m,
flow in negative z, an assumed 6,000 rpm and an **imposed 0.5 m³/s**. Air density
is 1.204 kg/m³ and kinematic viscosity 1.5e-5 m²/s. Inlet turbulence intensity
is 3%, with length scale 0.007 m. The cylindrical MRF zone has radius 0.16 m
and z limits −0.06 to 0.07 m. These are not measured engine or housing values.

The coarse block has 24×24×32 cells before surface refinement at levels 2/3.
There are no prism layers in this initial meshing probe. Snapping produces:

- 237,338 fluid cells, one connected fluid region, 49,547 rotor wall faces;
- positive minimum volume `4.00e-10 m³`, maximum non-orthogonality 62.78°,
  maximum skewness 3.68 and no failures against the unchanged local quality dictionary;
- **13,692 concave cells in `checkMesh -allGeometry -allTopology -meshQuality`**:
  the extended check fails and the original execution stops before the solver.

A separate exploratory case retains this failed log, mesh lineage and all input
hashes. Standard topology/local-quality checks pass, and 221,764 cells enter
`rotorZone`. MRF/SST is allowed to run as a diagnostic. The assessment retains
`extended_geometry_mesh_check_pass = false`, which prevents single-mesh admission
even if the residuals, balances and force histories become stationary. There is
no retrospective relaxation of the extended check.

An independent VTK 9.6.2/Python readout of every inlet/outlet face at iteration
200 confirms native flux-weighted pressure/kinetic-energy averages within
`4.88e-8` relative error. It also finds **0.263 m³/s entering the nominal outlet**,
while 0.763 m³/s leaves it: the net 0.5 m³/s balance conceals substantial reversal.
This requires a boundary/domain study, not an efficiency claim. The complete
200 field has a maximum cell speed of 146.14 m/s; using an assumed sound speed
of 343 m/s gives **Mach 0.426**, requiring compressibility assessment before
accepting this incompressible approximation. The displayed meridional slice uses
cell-to-point interpolation for presentation only.

The 500-iteration solve completes with unchanged prepared inputs. Its final
100-iteration window gives the following **unaccepted diagnostic values**:

| Quantity | Window mean | Peak-to-peak / mean | Change from previous window |
|---|---:|---:|---:|
| Total-pressure rise | 553.83 Pa | 12.68% | 6.34% |
| Resisting z torque | 2.738 N·m | 3.15% | 1.46% |
| Shaft power | 1,720 W | 3.15% | 1.46% |

Both pressure and torque fail the unchanged 1% stationarity criteria. Maximum
final-window mass imbalance is `1.42e-8` relative, below 0.1%; conservation alone
does not admit the result. Native SST postprocessing gives rotor yPlus
9.48–582.74, mean 99.40, and duct yPlus 44.97–1,889.12, mean 1,034.80.
Near-wall resolution is not qualified. No fan efficiency, installed-engine
airflow, accepted reference dataset or aerodynamic design improvement is claimed.

The [JSON checkpoint](foundation13-rotor-pilot-20261022.json) records result and
private delivery digests, including rejected attempts. No new Vast rental is used.

## Reproduction and next acceptance gates

From the repository root, use the existing numerical Python environment:

```bash
export PYTHONPATH=twins/935-horizontal-cooling-system-f0/source
python twins/935-horizontal-cooling-system-f0/source/foundation13-study-20261022/prepare_couette.py NEW_PRIVATE_CONTROL_DIRECTORY
```

Inside the pinned, sourced Foundation 13 runtime, each fresh control runs
`blockMesh`, `checkMesh -allGeometry -allTopology`,
`foamRun -solver incompressibleFluid`, then `postProcess -func writeCellCentres -latestTime`.
Assess the three completed cases without overwriting an earlier assessment:

```bash
python twins/935-horizontal-cooling-system-f0/source/foundation13-study-20261022/analyze_couette.py PRIVATE_CONTROL_DIRECTORY NEW_PRIVATE_ASSESSMENT_DIRECTORY
python twins/935-horizontal-cooling-system-f0/source/prepare_foundation13_rotor.py PRIVATE_CASE_JSON NEW_PRIVATE_ROTOR_DIRECTORY
python twins/935-horizontal-cooling-system-f0/source/assess_foundation13_rotor.py PRIVATE_COMPLETED_CASE NEW_PRIVATE_ASSESSMENT_DIRECTORY
```

The rotor JSON preserves the existing duct recipe's configuration keys and
requires the indexed bundle/hash, STL/hash, unverified scale/axis flags and the
explicit 0.001 m/source-unit hypothesis. All scan derivatives, fields, detailed
receipts and failed attempts stay private. Git receives sources, tests and a
non-geometric checkpoint only.

Next: resolve fluid-cell concavity, study the outlet/domain and compressibility,
and qualify wall error/yPlus before three accepted spatial meshes. The radial
discharge/engine passages require the housing definition; this axial square duct
does not supply it. Require mass imbalance below 0.1%, final pressure
and torque stationarity below 1%, and fine/medium differences below 3%. The
imposed flow remains an input, not a measured or predicted installed-engine flow.
Only accepted cases may supply optimization or PhysicsNeMo reference data.
