# Provisional bionic 993 Turbo carrier — CAD and structural study

**Current manufacturing direction: [flat titanium build](flat-review.md).**
The owner requires a flat metal build. The original XY plane remains horizontal;
only a 45-degree rotation within the bed plane is used. The earlier tilted
M 400-4 route is superseded. The proposed metal remains Ti-6Al-4V Grade 5.
Plasticity in the mechanical report means permanent deformation of metal.

**Previous extension: [V5 mechanical and additive-process study](comprehensive-review.md).**
It extends the frozen 1.185 kg geometry to three-axis loads, plasticity, loaded
vibration and staged printing simulations. V5 remains rejected under the study
assumptions. Its mechanical results remain applicable to the unchanged solid;
its tilted placement and machine-specific process card are historical.

**Latest correction: [weight and original-fastener review](lightweight-review.md).**
The 2.108 kg version is rejected; the new brief targets 1.0 kg with a 1.2 kg ceiling.
The lighter studies and their new calculations are kept separately below that link.

12 October 2026. **18 CalculiX jobs completed on original editable study solids.**
The user explicitly authorised assumed dimensions for a provisional study after
the initial engineering-input audit. This supersedes that audit's no-CAD/no-solve
status; its original private receipt remains unchanged. **Fitment, strength,
fatigue life and manufacturing release remain unverified.**

**Both plate versions are rejected as design candidates.** The 8 mm version has
excessive computed flexibility. The 20 mm version weighs 2.108 kg and thickens
the central joint, violating the user's weight and original-fastener requirements.
Its numerical results below are retained as a rejected comparison, not a proposed
replacement for `993 115 021 53`.

The corrected brief is **1.0 kg target, 1.2 kg absolute ceiling**, for the finished
carrier alone, and retention of the original fasteners, mating faces and joint
stack. PET lists four M10 × 20 central bolts; a 20 mm carrier pad alone consumes
their nominal under-head length before the bracket and nut are accommodated.
The earlier 8 mm pad is also only an assumption, not an OEM measurement. Available
grip, thread engagement, bolt grade and tool access remain unmeasured. A lighter
ribbed study may preserve the assumed interfaces but cannot establish OEM fitment.

## Editable geometry and attachment assumptions

[CAD source](cad.py), [8 mm inputs](study.json), [20 mm inputs](study-v2.json),
[solver/mesher](simulate.py), [numerical results](results.json),
[post-processing](analyse.py) and [actual-CAD rendering](render.py) are retained.
Both variants have a valid single BRep solid; STEP readback preserves its volume,
and STL checks find one closed, consistently oriented component.

The visual direction follows the approved 11 October illustration: four central
bores, two large central openings, branched arms and transverse end eyes. The
illustration is not dimensioned CAD. The private overview SHA-256 is
`4daa1390ffe2e07c803392ea69542166e1f8c4c735e66f881dd6223b6c6d094e`;
the central detail is
`5f9b830495f4888e03ceeecbfb41ae25ddd569a31b4d68b9f9e78968545ab09f`.
No geometry or numerical result from the distinct historical R9 study was reused.

| Design input | Provisional value — not an OEM measurement |
| --- | --- |
| Coordinates | X span; Y end-eye axis; Z normal to central pad; no measured vehicle transform |
| Four central bore centres | X = ±48 mm, Y = ±23 mm; axes Z; diameter 11 mm |
| Two end-eye centres | X = ±280 mm; axes Y; diameter 13.5 mm |
| End eyes | Outer diameter 32 mm, axial length 46 mm |
| Two central openings | Diameter 25 mm; X = ±20 mm |
| Two secondary holes | Diameter 4 mm; centres (-160, -26) and (-180, -23) mm |
| Overall study envelope | 592 × 72 × 32 mm |
| Plate depth | V1: 8 mm; V2: 20 mm |
| Blade-to-eye blend | 3 mm radius; window fillets and boundary curves are defined in the source |
| Calculated dense-material mass | V1: 1.002 kg; V2: 2.108 kg |

Readback checks verify six primary bore axes against these **design inputs**.
They do not replace independent inspection against measured interfaces. The
[PET-led requirements](../pet-redo/requirements.json) still contain unknown OEM
coordinates. PET establishes the assembly:

**Engine → bracket `993 115 103 52` → four M10 joints → carrier → two engine
mountings → body**, with the gearbox support affecting powertrain load sharing.
The supplier's mass/envelope and the illustration cannot establish a weight
saving, joint preload, clearances or compatibility. The historical 85 Nm value
for another M12 joint was not applied to the central M10 joints.

## Material, loads and solver model

Material is a **dense Ti-6Al-4V elastic reference**, not a selected or qualified
manufacturing condition: E = 107 GPa, Poisson ratio 0.31, density 4.42 g/cm³,
thermal expansion 9×10⁻⁶/K. These values follow the
[TIMET datasheet](https://www.timet.com/documents/datasheets/alpha-and-beta-alloys/timetal-6-4.pdf).
No yield allowable, plastic curve or fatigue curve has been assumed.

[Porsche specifies 540 Nm for the standard 993 Turbo](https://newsroom.porsche.com/en/press-kits/50-years-porsche-turbo/The-911-Turbo-generations.html).
Applying that entire torque to this carrier is an assumption. The 850 Nm and
2,000/4,000 N cases are sensitivity scenarios, not measured reactions or a
700 hp specification. Vehicle mass, centre of gravity and gearbox load sharing
are not inferred from these forces.

Gmsh 4.15.2 generates straight-sided quadratic C3D10 tetrahedra. Two initial
curved-mesh attempts were rejected before solving because of invalid elements
and a failed high-order optimisation. The accepted meshes have positive Jacobians;
V2 volume error is 0.059–0.116%. See the
[Gmsh manual](https://gmsh.info/doc/texinfo/) and
[CalculiX 2.21 manual](https://www.dhondt.de/ccx_2.21.pdf).

Loads are equivalent nodal tractions distributed over the four bore surfaces,
with exact six-component force/moment resultants and a virtual-work check.
They omit washers, bolt shanks, preload, contact, friction and joint separation.
Supports are either fully fixed end bores or distributed translational springs
normalised to **1,000 or 10,000 N/mm per eye per direction**. These spring values
are not measurements of Porsche mounts. All jobs use a bounded local container
with one CPU, 3 GiB RAM and a 590-second solver timeout; the actual solver is
CalculiX 2.21. V1 used the amd64 build; subsequent jobs used the native ARM build.

## Results

Values below are maximum displacement magnitude and maximum integration-point
von Mises stress. They are conditional elastic demands, not allowable margins.
V2 rows use the finest mesh unless stated otherwise.

| Variant and case | Displacement (mm) | Stress (MPa) |
| --- | ---: | ---: |
| V1, combined, fixed ends, initial mesh | 21.485 | 2,091.1 |
| V1, combined, fixed ends, finer check | 23.005 | 2,581.7 |
| V2, 2,000 N in -Z, fixed ends | 0.690 | 134.5 |
| V2, 4,000 N in -Z, fixed ends, derived by linear scaling | 1.380 | 269.0 |
| V2, 2,000 N in Y, fixed ends | 0.099 | 30.6 |
| V2, 2,000 N in X, fixed ends | 0.0054 | 8.3 |
| V2, 540 Nm about Y, fixed ends, derived by linear superposition | 0.339 | 139.7 |
| V2, 4,000 N in -Z + 850 Nm about Y, fixed ends | 1.689 | 450.2 |
| V2, same combined load, 10,000 N/mm supports | 6.304 | 636.6 |
| V2, same combined load, 1,000 N/mm supports | 8.762 | 661.6 |

The V1 elastic stress is outside a defensible design interpretation; its large
deflection and unresolved stress refinement reject it as the study candidate.
V2 is stiffer, but its 2.108 kg reference mass does not demonstrate a weight
advantage over the OEM part. No strength or fitment pass is issued.

For V2 fixed ends, 26,510 → 36,087 → 61,744 elements give displacement
1.6788 → 1.6851 → 1.6888 mm and peak stress 432.38 → 446.02 → 450.21 MPa.
The final changes are **0.22% and 0.94%**. This demonstrates numerical stability
for this mesh/load model, not a bound on unknown geometry or joint modelling.

On the coarse mesh, geometric nonlinearity changes the fixed-end response from
1.6788 mm / 432.38 MPa to 1.6727 mm / 440.86 MPa. For the 1,000 N/mm supports,
it changes 8.7436 mm / 667.62 MPa to 8.7281 mm / 672.12 MPa. Material behaviour
remains elastic; plastic set has not been predicted.

| Additional calculation | Result and interpretation |
| --- | --- |
| Free vibration, bare carrier, coarse mesh | First eight fixed-end modes: 263.49, 658.15, 685.53, 791.01, 1682.99, 1831.85, 2386.56, 2644.71 Hz. With 1,000 N/mm supports: 96.36, 105.41, 147.93, 154.74, 251.74, 268.08, 396.08, 664.34 Hz. No engine/gearbox inertia or damping: these are not assembled-powertrain resonance results. |
| Linear elastic buckling, fixed ends, coarse mesh | Factors 87.25, 97.48, 116.07, 133.60 on the specified combined load. These are ideal elastic bifurcations, not strength factors; yielding/contact and imperfections are not represented. |
| Central attachment demands | Maximum applied central-site force about 5.34 kN. Complete site forces and end reactions are in `results.json`; bolt strength, preload loss, bearing, slip and separation remain unassessed. |
| Cyclic demand: 2,000 N baseline to combined load | Equivalent alternating stress: 158.82 MPa fixed; 237.03 MPa with soft supports. No mean-stress correction or fatigue-life claim. |
| Cyclic demand: 2,000 N with fully reversed ±850 Nm | Equivalent alternating stress: 219.85 MPa fixed; 444.24 MPa with soft supports. This is an assumed cycle, not measured duty. |
| Free thermal warping, 50 K through 20 mm depth | 0.9321 mm with a 3-2-1 restraint removing only rigid motion. An independent compatible-strain solution agrees within 5.01×10⁻⁸ mm; stress is essentially zero, as expected. This deformation is reversible. |

The thermal case is **not a prediction of residual printing or welding
distortion**. Build orientation, support/fixture removal, process history,
plasticity, heat treatment, machining and calibration specimens are still needed.
Fatigue life likewise needs process-specific fatigue data, surface/notch effects,
mean stress, joints and a service spectrum; it is deliberately null.

## Reproduction and retained files

Local outputs are under `work/carrier-bionic-provisional-20261012/`:

- `v1/` and `v2/`: editable `carrier.step`, inspection STL, actual CAD views,
  frozen input JSON, geometry checks and hashes.
- `v*/mesh-*/`: Abaqus-format mesh, input decks, solver logs, `.dat`, `.frd`,
  displacement/stress arrays, JSON summaries and result plots.
- `benchmark-corrected/` and `benchmark-native/`: the independent unit-cube
  elastic test passed on both solver builds (1 MPa stress, 1 N reaction).
- `summary.json`, `results.csv`, `software.json` and `sha256.json`: collated
  results, runtime provenance and final file digests. Rejected attempts remain.

Use the installed CAD Python environment with build123d 0.11.1, Gmsh 4.15.2,
NumPy, trimesh and matplotlib. The container selected by `CARRIER_STUDY_CONTAINER` must provide CalculiX 2.21.
Create a **new** output directory for another attempt; inputs are not overwritten:

```sh
python cad.py study-v2.json /absolute/path/new-study
python simulate.py /absolute/path/new-study --mesh 8
python simulate.py /absolute/path/new-study/mesh-8 --case combined
python render.py /absolute/path/new-study
python render.py /absolute/path/new-study/mesh-8 --case combined-rigid-static
python verify.py /absolute/path/new-benchmark
```

`analyse.py` collates the retained V1/V2 campaign; `simulate.py --selfcheck` checks
load resultants and work. Five focused software tests cover result parsing,
load transfer, degenerate interfaces, stress invariants and eigenvalue extraction.
The existing four carrier tests also passed. The corrected native-Linux run
completed **3,258 Python tests with 159 explicit skips**. Subsequent `make check`
targets stopped at the existing LPBF voxel audit because Docker is unavailable
inside that validation container; the full aggregate is not green. The final
641-file Markdown check found zero broken links, and generated catalogue pages
match their records. Logs preserve both the initial environment failures and
the corrected run. Software checks are not physical tests.

The catalogue remains **concept**, with the old master retained. Before a
functional redesign or manufacture: independently measure the carrier/bracket
interfaces, establish actual reactions and mount stiffness, select and qualify
the material/process, model joints, agree acceptance limits, then perform
professional review and instrumented static/cyclic tests. No physical tests,
road installation, manufacturing release or Qwen weight update occurred here.
