# 935 — PicoGK libraries and calculations on the Mac

The chain now uses the LEAP71 libraries on the Mac to study
the rotor roots, probe thicknesses and exchange geometry and simulation
fields as VDB. **Five centrifugal calculations and one CFD point concern the
new rotor with nine individual blades.** Their checks still reveal
insufficient convergence; they do not validate a manufacturable assembly.

The [run receipt](mac-picogk-20261012.json) gives the digests, versions,
results and rejections. The scans, geometries, fields, cases and solver files
remain in the [private archive](https://github.com/cluster2600/porscheparts-935-private/releases/tag/mac-picogk-20261012).
The programme remains that of the historical 935, with its six-cylinder engine
and its interfaces still to be measured. No Vast machine is used.

## Qualified libraries

PicoGK 2.3/Core 26.2.0 and .NET 9.0.318 run natively on `osx-arm64`.
The following four repositories are frozen in the
[library lock](../../../twins/935-horizontal-cooling-system-f0/source/picogk-mac-study/libraries.lock.json).
Their sources are compiled with the already installed kernel, without modifying the
old programs or their evidence. Compilation: zero errors and 98
obsolete-API warnings in the upstream libraries.

| Library | Actual use | Verification |
|---|---|---|
| [ShapeKernel](https://github.com/leap71/LEAP71_ShapeKernel) | Frames, cylinders, tubes, annular root mask and fluid domain | Volume of an analytical tube: error 0.049 %; radii giving 9.6 mm for a 10 mm wall on a 0.6 mm grid |
| [LatticeLibrary](https://github.com/leap71/LEAP71_LatticeLibrary) | BCC lattice witness bounded to a tube | Positive volume below the envelope solid; no insertion into the historical replica |
| [QuasiCrystals](https://github.com/leap71/LEAP71_QuasiCrystals) | Sources compiled with the other libraries | Compilation only; no 935 geometry currently justifies its use |
| [SimulationExample](https://github.com/leap71/PicoGK_SimulationExample) | Official reader for the five-field VDB fluid protocol | Real read and check of the fields by name; geometry, density, viscosity and initial velocity |

ShapeKernel, LatticeLibrary and QuasiCrystals are under Apache-2.0. The file
`src/SimpleFluidSimulationInput.cs` carries SPDX CC0-1.0; no global licence
is assumed for the other files of the SimulationExample repository.
The new PicoGK.Geometry contract types require .NET 10/C# 14 and are
not needed for this .NET 9 chain. The HeatX/RoverWheel examples do not
define a 935. The generic screws of the third-party PicoGK-Fasteners project
do not replace measurement of the specimen's fasteners.

## Retained geometry and proposed blends

The [C# program](../../../twins/935-horizontal-cooling-system-f0/source/picogk-mac-study/Program.cs)
loads the native rotor from the previous campaign and revoxelises it at an assumed
0.6 mm. This pass constitutes a new numerical reference; it does not
guarantee equality with the original triangles or the scan.

Three morphological closings are examined: 0, 0.6 and 1.2 mm. The program
retains only their **additions** in the ring r = 25…95 mm, z = −30…40 mm.
The first acquired sections lie at a station of 98 source units
or more, measured on the radial axis of each blade. The guard does not rely on
a PCA. The program verifies an acquired provenance for each of the nine
blades, the absence of material removal, the absence of additions in the bore
and the absence of change outside the mask.

An independent check compares exactly the triangles at r ≥ 98 mm between
each variant and the revoxelised reference: they are identical. The three
meshes each have one component, are closed, consistently oriented
and have only faces of positive area. This does not constitute a
general proof of the absence of self-intersections.
These additions remain repair hypotheses for the missing roots; no
historical or machining fillet radius is declared measured. The historical
reference is not replaced by the 1.2 mm variant.

The visual inspection overlays the scan points on the rotor and shows the
variants as well as the discrete stresses. It preserves the asymmetry of the
blades. The hub, the back and the hypothetical blends remain visible as
such; overlaying the whole scan does not qualify the misaligned back.

## Thicknesses and VDB fields

The rays probe three genuinely acquired sections of each blade, with
a guard at the ends of the available interval, at 16 positions of the contour.
Of **432 probes**, 426 produce a length and six remain unresolved.
The normal lengths measured on this grid range from 0.6 to 18.49 mm, with
a median of 5.40 mm. The minimum reaches the voxel resolution: **it is not
a global minimum thickness nor a manufacturing dimension**. A normal ray
is not an exhaustive measurement of the distance between opposite faces.
All probes and all failures are kept in the VDB and its receipt.

Three types of VDB are produced with `PicoGK.OpenVdbFile`:

- inspection: rotor and sampled normal lengths;
- fluid input: solid/air domains, density, kinematic viscosity and initial axial
  velocity; the official reader accepts the five fields by name;
- mechanical result: rotor, maxima of the eight Gauss points of each C3D8
  at the element centres, and nodal displacements.

The fluid input domain is a trial cylinder of radius 180 mm, 240 mm
high, rasterised at an assumed 2 mm. It remains distinct from the square duct of the
OpenFOAM pilot. It does not yet export the rotating-wall condition.
The VDB export is a data protocol, not a CFD solver nor a complete SimReady
validation. The geometric coordinates remain in assumed mm;
density, viscosity and velocity explicitly carry their SI units. A
geometric conversion to metres is necessary before an SI calculation.
The mechanical results remain **pointwise and not interpolated**: a voxel
without a value is not a zero-stress zone.

## Mechanical calculation on the nine blades

PicoGK supplies the cell grids whose centre lies in the solid.
Gmsh 4.12.1 prepares the C3D8 in the existing local amd64 container; CalculiX
2.21 solves natively on Linux ARM64 in Docker on the Mac. The physical
solvers complement the PicoGK geometric kernel.

Common assumptions: 1 mm/source unit, 6,000 rpm, homogeneous material,
linear elasticity, Poisson's ratio 0.33 and bore fixed in
translation. The selection width of the bore nodes follows the grid
pitch. This discretisation of the support therefore changes with the mesh; its
effect is not separated from that of the cells. No air pressure, no temperature,
no shaft contacts and no real clamping preload are applied.

| Material, 1.5 mm grid | Conditional mass of the revoxelised CAD | Von Mises peak | Maximum displacement |
|---|---:|---:|---:|
| AlSi10Mg | 1.158 kg | 176.9 MPa | 0.816 mm |
| WE43 | 0.794 kg | 121.2 MPa | 0.887 mm |
| Ti‑6Al‑4V | 1.909 kg | 291.5 MPa | 0.855 mm |

The CAD masses use independent integration of the triangles and the
densities from the existing cards. The 1.5 mm FEA grid represents a volume
2.69 % larger than this geometry and therefore has a distinct mass in
its receipt. The cards qualify neither the printing process nor the fatigue
limits of the specimen. The peaks may include concentrations linked
to the supports and to the voxel steps. These three rows do not determine
a winning material or an admissible speed.

For aluminium, the grids 1.5 → 1.35 → 1.2 mm give respectively
**0.816 → 0.941 → 1.160 mm** maximum displacement and
**176.9 → 202.5 → 199.7 MPa** maximum stress. Between the two fine
grids, the 95th percentile of the per-element maxima outside r < 25 mm changes by
3.55 %, but the displacement still changes by **23.31 %**. The required mechanical
convergence is therefore not achieved.

The 3 and 2 mm grids are rejected for disconnected fragments:
17 and four cells outside the main component respectively.
None is removed to make a calculation pass. The 1.8 mm grid is
connected but fails the 6 % volume check. The three grids retained
for refinement are fully connected.

The [analyser](../../../twins/935-horizontal-cooling-system-f0/source/assess_mac_fea.py)
checks the digests, every node, the eight Gauss points of each
element and every bore reaction. Forces and moments close
with relative errors below 2 × 10⁻⁹ for the three materials
of the 1.5 mm grid, normalised by the sums of the centrifugal loads in
absolute value. An independent check recovers stress ratios
proportional to density and displacement ratios proportional
to density/Young's modulus, under the common assumptions.

The centre of mass of this reconstruction lies **2.53 assumed mm**
from the axis. At 6,000 rpm, the rigid model gives a conditional unbalance
force of about **1.16 kN in aluminium**. This result may come
from the reconstructed shapes, the closings or the registration; it does not measure the
unbalance of the real fan. Its origin must be resolved and a measured
balancing planned before sizing the supports or manufacturing.

## CFD point and next calculations

The new closed rotor is placed in the hypothetical square duct already
defined: 0.6 m³/s imposed, +6,000 rpm, air at 1.15 kg/m³ and kinematic
viscosity 1.55 × 10⁻⁵ m²/s. OpenCFD v2406 ARM64 runs MRF/k‑ω SST on the
Mac. The mesh passes `checkMesh` with `Mesh OK.` and 500 iterations complete.

Over the last 100 iterations, the maximum mass imbalance is
2.03 × 10⁻⁸ relative. The mean total pressure is 155.5 Pa and the mean resisting
torque 2.505 N·m, but their peak-to-peak variations reach
**6.04 % and 1.74 %**. The drift between 100-iteration windows reaches
3.74 % and 1.01 %. The 1 % stationarity threshold is exceeded: **point rejected**.
These values describe one calculation iteration; they are neither an accepted 935
curve nor PhysicsNeMo training data.

The next correction must address the definition of the hub surfaces and supports,
the mechanical representation of the blades and the conditions of the real
housing. Three-mesh CFD refinement remains to be done after acceptance
of the pilot; a transient calculation becomes relevant if the configuration does not
allow a representative steady state. The blade variants must not
be ranked by an unconverged flow rate. The gears, bearings,
retainers, seals and fasteners of the mechanism remain subject to the 17 documented
interfaces and to the missing measurements.

## Reproduction

Keep the old results and create a new directory under `work/`.
The case arguments are private; each case gives the paths and SHA-256 of the
rotor and of the sections, `purpose: hypothesis_screen`, `scale_verified: false`
and `scale_mm_per_source_unit: 1`. The fluid parameters appear in the archived
case. The `fea-fields` mode also requires the FEA analysis, the two CSVs, their
digests and their row counts; it refuses an unbalanced analysis.

With Git, fetch each of the four repositories into a new directory and
verify the revisions before compilation:

```sh
python3 - <<'PY'
import json, pathlib, subprocess
pins = json.loads(pathlib.Path('twins/935-horizontal-cooling-system-f0/source/picogk-mac-study/libraries.lock.json').read_text())
root = pathlib.Path('work/PRIVATE/upstream')
root.mkdir(parents=True, exist_ok=False)
for item in pins['libraries']:
    path = root / item['directory']
    subprocess.run(['git', 'init', str(path)], check=True)
    subprocess.run(['git', '-C', str(path), 'remote', 'add', 'origin', item['repository']], check=True)
    subprocess.run(['git', '-C', str(path), 'fetch', '--depth', '1', 'origin', item['commit']], check=True)
    subprocess.run(['git', '-C', str(path), 'checkout', '--detach', 'FETCH_HEAD'], check=True)
    assert subprocess.check_output(['git', '-C', str(path), 'rev-parse', 'HEAD'], text=True).strip() == item['commit']
PY
dotnet build twins/935-horizontal-cooling-system-f0/source/picogk-mac-study/MacStudy935.csproj \
  -c Release -p:PicoGKAssembly=/PRIVATE/PicoGK.dll -p:UpstreamRoot="$PWD/work/PRIVATE/upstream"
# Use the already qualified native osx-arm64 library.
DYLD_LIBRARY_PATH=/PRIVATE/PicoGK/native/osx-arm64 dotnet \
  twins/935-horizontal-cooling-system-f0/source/picogk-mac-study/bin/Release/net9.0/MacStudy935.dll \
  witness work/PRIVATE/new-witness
# Repeat the same command for the roots, thickness, simulation and fea-fields modes,
# with the private case before the new output directory.
python twins/935-horizontal-cooling-system-f0/source/assess_mac_fea.py \
  work/PRIVATE/prepared work/PRIVATE/solved work/PRIVATE/new-assessment
python -m unittest discover -s tests -p test_935_mac_picogk.py -v
make check
```

The existing scripts `prepare_candidate_fea.py`, `run_candidate_fea.sh`,
`prepare_candidate_cfd.py`, `run_candidate_cfd.sh` and `assess_candidate_cfd.py`
remain reused, unchanged. The private logs and receipts keep the exact
commands and inputs. The software and the trials on hypotheses are advancing;
historical compatibility, calibration, material/process qualification
and physical tests remain open.
