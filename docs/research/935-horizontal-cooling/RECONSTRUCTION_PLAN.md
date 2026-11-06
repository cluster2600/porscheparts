# Reconstruction and improvement of the 935 horizontal system

[Two distinct programmes](../../FAN_DEVELOPMENT_PROGRAMMES.md) ·
[Dossier and bill of materials](README.md) · [Sources](sources.json)

## Chosen implementation order and current state

The [25 October continuation](ROOT_MESH_RESUME_20261025.md) closes five inferred
root passages in the native PicoGK recipe, preserving protected original
triangles, and corrects Foundation 13 reconstruction with a moved analytic
control. The real fluid mesh still fails the full native concavity check.
Calibration, installed interfaces, accepted fan CFD and fabrication remain
open; the earlier pause record is retained as history.

The [21 October resumption through the README chain](README_CHAIN_20261021.md)
keeps the corrected rotor and isolates the sensitivity of the calculation to the
bore fixing band. The analytical studies R0/V2/S1 remain identified
separately; their results are not transferred to the scanned rotor.

The [native 935 chain and the local Qwen trial](NATIVE_935_PIPELINE.md) constitute
the active continuation: nine individually reconstructed blades, rotor and
shroud created in PicoGK, six-cylinder engine envelopes and an interference
check. The editable sources are C# with private JSON parameters.
The historical assembly and manufacture remain to be qualified.

The [13 October tip correction](TIP_CORRECTION_20261013.md) keeps
the acquired arcs of blade 03, replaces its terminal extrapolation and
compares the deviations as well as three centrifugal calculations. The repair
hypotheses remain distinct from the measured surfaces.

The [12 October continuation](CONTINUATION_20261012.md) adds a closed-rotor
candidate under hypotheses, the CFD/structure pilot interfaces and
a geometric USD. It remains separate from the calibrated historical reference
and does not close manufacture or bench validation of the assembly.

The [refinement and comparison with the scan](CONVERGENCE_20261012.md) specify
the geometric deviations between blades and the sensitivity of the stresses to the
mesh; these results guide the corrections before manufacture.

Qualified Linux/Python/.NET environment → surfaces from the scans with
SciPy/PicoGK → native PicoGK assembly and interface qualification → OpenFOAM →
Gmsh/CalculiX → SciPy optimisation then OpenMDAO coordination → PhysicsNeMo
model on accepted calculations → USD/Omniverse assembly and results.
The historical reference precedes the improved variant. The first work package covers
numerical validation and the [bench protocol](BENCH_PROTOCOL.md);
manufacture and physical validation come afterwards.

On 6 October 2026, the owner set the target of the first assembly:
**an exact replica of the horizontal system and its mounting on a 935**.
The layout, interfaces, transmission and air guides of this
reference are reconstructed before any improvement. A second step
will adapt the horizontal system to a **993 engine**, with its own installation
contract; it remains distinct from the vertical 993 programme.
The vehicle families are known, but the exact variants and their
mounting dimensions remain to be qualified. This decision validates no
interface or dimension that is still unknown.

The [5 to 7 October implementation record](IMPLEMENTATION.md) contains the
executable commands, versions, checks and limits. The coordinator accepts
a case, a step and a new private directory. The campaign reconstructed nine
observed blade ranges, produced three PicoGK resolutions, an editable native
CAD and the deviation/section maps. The continuation adds two open analytical
hub surfaces, checked on reserved sectors of the scan
and exported to FreeCAD/STEP. The detailed data and results are saved
in the [private GitHub archives](https://github.com/cluster2600/porscheparts-935-private).
The mechanism now has a shaft portion with 22 observed periodic
lobes, with an editable open loft, a gap map and bidirectional deviations
to the STEP. The mating splines and the internal gears remain unknown.
The support also has a local inspection plane and a portion of
bore wall reconstructed on its single acquired arc; their frames remain
inspection candidates, without the status of a measured mounting reference.
It has not yet closed the geometry
of the rotor, the metrology of the interfaces or the mechanism; the physical steps
that depend on them remain open. No old proxy enters the reference
calculations and no new Vast rental is used.

The expected result is an editable source geometry of all the specific
parts, a bill of materials of the standard components, an assembly with
documented interfaces, calculations characterising the system and a twin
confronted with measurements for the 935 replica, then for the 993 adaptation and the
improved versions. The supplied specimen serves as the starting
reference; an exact reproduction and a redesign of an unobservable zone
have distinct statuses. The work packages below characterise the reference and
the improved variants with the same evidence requirements.

## Work package 1 — Frames, segmentation and interfaces

The [12 October assembly continuation](INSPECTION_ASSEMBLY.md) reuses
PicoGK and the available geometries without a Vast rental. It delivers a reversible
inspection scene with a 917 engine context identified as comparative;
the interfaces of the historical 935 mounting remain to be established.

Take the two OBJs present as reversible private copies. Segment the
mechanical parts and the acquisitions without eliminating unknown fragments.
Classify holes, missing surfaces and intersections before repair. Identify
the back regions of the rotor and the hub/shaft stack of the Fan Drive.

Establish an engine frame and part frames: vertical output axis,
input axis, mounting faces and angular reference. The private PCA poses
serve only for inspection. Measure orthogonality, centre distances and
transformations before asserting a common assembly.

For each interface in the bill of materials: source side and receiving side,
axis/face/holes, nominal dimension, tolerance, fastening method, transmitted load and
independent evidence. In priority: rotor/hub/vertical shaft; shaft/bearings;
support/engine; pulley/input shaft; housing/rotor; guide/engine.
Unacquired surfaces remain absent from the functional contract.

Obtain the export unit and at least two calibration dimensions per scan, with
tool/uncertainty. The rotor and the drive are not scaled by
a visual fit. Scans of the housing/guide and a view of the mounted
assembly complete the work package when they are accessible. The catalogue or a
disassembled inspection must resolve the hidden interfaces and internal parts.

**Deliverables:** component register, assembly matrix, interface
contract, coverage map and acquisition list. **Gate:**
traceable assembly without scale contradiction or invented coordinates.

## Work package 2 — C# PicoGK reconstruction and usable CAD

Reuse the existing C# PicoGK chain after a witness of the exact runtime.
Reconstruct separately the rotor, hub, support/housing, shafts, pulleys and
guides with parameters taken from the observed regions. Keep section
distributions and functional surfaces. The voxel resolution is subject to
a study over three steps; the choices must resolve walls and clearances.

The gears are not obtained by copying the outer envelope.
Qualify type, tooth count, ratio, module/geometry, width, angle,
axis position, clearances and process before defining them. With these data,
produce the geometric source and drawings suited to the process. Standard bearings,
seals and belts are specified by reference and interface;
their complete manufacture is not assumed to be necessary.

Measure the bidirectional deviations between reconstruction and scan on the observed
regions, then sections, thicknesses, clearances and continuity. Interpolated
or redrawn zones have their own status and a justification.
The error budget depends on the metrology; no universal accuracy
is promised on the basis of the file name.

**Deliverables:** C#, parameters, PicoGK geometry, meshes and interface drawings.
Complete with a surface/BRep reconstruction in a CAD tool for a
usable STEP; the voxel envelope does not replace machining tolerances
or the qualification of a gear tooth form. **Gate:** fidelity, integrity and
completeness of the interfaces compatible with the calculation concerned.

## Work package 3 — Kinematics and transmission

Establish dimensions, blade count, volume and section distributions.
With documented density and material: mass, centre of gravity and inertia
tensor. For each rotor speed, calculate tip speed, Mach,
Reynolds and blade-passing frequency; leave unknown physical inputs
explicit and produce separate scenarios if necessary.

Establish the direction of rotation and the overall ratio from the pitch diameters of the
pulleys and the real gear ratio, with an explicit input/output convention.
Ratios taken from old M64 sections and speeds from commercial kits
do not constitute the data of this transmission.

Calculate rotor and shaft speeds, reflected inertias, aerodynamic torque,
accelerations/decelerations and belt forces. Establish losses and the power
balance from the engine to the fan. The torque demanded includes the inertia
variation and the losses, beyond the steady state alone.

After internal identification: radial/axial tooth loads,
shaft bending/torsion, contacts, strength of the housing, screws and bearings. The
[ISO 10300-1 framework](https://www.iso.org/standard/79401.html) covers the load
capacity of bevel gears; the full text and the applicable parts
remain to be consulted for the chosen gear. Public data sheets are not
evidence of conformity.

Define fits, preload/clearance, speed, bearing life, lubrication,
sealing and heat dissipation of the angle drive. The
[ISO 281](https://www.iso.org/standard/38102.html) and
[SKF](https://evolution.skf.com/new-skf-engineering-software-for-the-evaluation-of-bearing-arrangements/)
methods are calculation references, not references for 935 parts. The edition and
the limits of application must be frozen when the calculation is launched.

**Deliverables:** kinematic diagram, torque/speed curves, loads and
loss budget. **Gate:** identified inputs and results checked
by independent calculations and corresponding measurements.

## Work package 4 — Flow, distribution and cooling

Mesh the assembly of rotor and fixed parts with its real housing geometry,
clearances and obstacles. An isolated pilot is useful to check the method; it
is not a prediction of the installed system.

Under OpenFOAM, check surfaces and volume mesh before the solver,
rotating/fixed domains, interfaces, turbulence, boundary layers and `y+`.
First produce an accepted pilot point, then flow/pressure/torque and
power curves over the relevant speeds and back-pressures. Compare three
meshes, convergence windows, conservation and energy balance;
resolve in time the interactions that require it.

An MRF model can serve for the mean characteristics; a transient rotating
interface is necessary for the retained unsteady
interactions. Qualify compressibility and the flow model from the velocities
and dimensionless numbers, with a frozen OpenFOAM family/version.

Include the resistance of the guides and engine passages to obtain the installed
point and the distribution by zone/cylinder. The thermal calculation depends on the
engine loads, the exchange surfaces and the defined air/water variant.
Keep separate the exchanges with oil, intercooler or water cooling
if they are not part of the documented air network. A horizontal orientation
does not, on its own, demonstrate a better distribution.

**Deliverables:** curves, native fields, distribution, losses, temperatures and
uncertainties according to the available data. **Gate:** fidelity of the network,
convergence and agreement with measurements; no old 993 field is attached to
the 935 geometry.

## Work package 5 — Strength, vibration and manufacture

On the qualified assembly, combine centrifugal, pressure, temperature,
drive, contacts and fasteners. Check blade roots, hub,
shafts, housing/support and maintenance of clearances. Spatial convergence and the distinction
between numerical singularities and physical stresses are necessary.

Perform prestressed modes in rotation and a Campbell diagram with bearing stiffnesses,
gyroscopic effects according to the solver's capabilities, engine orders, blade
passing and gear-mesh frequency. Add transients, fatigue and a usage
spectrum when material, process, surface and fatigue data are
qualified. Plan balancing with
[ISO 21940-11](https://www.iso.org/standard/54074.html) if rigid behaviour
applies; do not impose a balancing grade arbitrarily.

Define for each part its process: machining, gear cutting/treatment,
forming/composite or additive manufacturing where justified. Document
material, orientation, treatments, machining allowances, inspection and standard
components. The aluminium/magnesium/composite choice remains specific to the specimen
and to the qualified design.

**Deliverables:** mechanical fields, dynamics, fatigue criteria and
manufacturing/inspection dossier. **Gate:** technical review and the corresponding
test plan; rotating tests remain under human responsibility.

## Optimisation after characterisation of the reference

Define controlled variants on the sections, twist, camber,
blade roots and tips, then the hub, the support and the air
passages. Evaluate current materials and processes with properties at temperature,
surface finish and inspection capability. Gear teeth, bearings and lubrication
may be redesigned when the loss budget and the loads justify it.

Measure the mass of the rotor and of the assembly, inertia, actually distributed flow,
pressure, power at the transmission input and relevant temperatures.
Compare at the same rotor speed, air and network, then at a common power budget
if the variants demand different torques. Quantify the uncertainty
of the deviations. No numerical gain target is invented before these data.

Keep the defined installation interfaces or explicitly document
their evolution. Recalculate structure, hot/rotating clearances, modes and fatigue
for each retained candidate. A lightened shape or a modern material is not enough
to qualify the overall gain. The result of this work package is a traceable
comparison and a variant that is a candidate for testing, with its known trade-offs.

## Work package 6 — Validation and digital twin

Define tests distinguishing transmission, fan on the bench and installed
system. Measure input/output speed, torque/power, temperature of the
angle drive, flow/pressures, thermal distribution and vibration. Document
calibration, uncertainties and independent validation points. Any
overspeed/balancing bench requires an appropriate enclosure and protocol.

Compose all confirmed parts in OpenUSD with units, frames,
assembly and kinematic joints. Associate each result with its geometric
hash, conditions, solver version, materials and validation status.
Keep native formats and the cell/point association for the Omniverse review.

Include transmission losses and the thermal/airflow network in the system
model. A reduced model may interpolate the accepted calculations within their
domain of validity and be confronted with the sensors. An animation of the wheel
alone does not close this work package.

**Final deliverables:** sources and CAD, bill of materials, drawings, calculation dossier,
test plan/report and twin package. Physical validation remains
open if the corresponding measurements are not available.

## First geometric delivery

The next usable work package will be the segmented rotor + support/drive
assembly, its frames and the interface contract, followed by the first
scan-based PicoGK generator. The hidden parts and the guides will have explicitly
missing inputs. No plausible solid will replace them in an
assembly declared complete.

The raw data, derivatives and parameters taken from geometry under unknown rights
remain private. Generic code and permitted reports may be
versioned. Implementation changes will be verified by the
targeted checks and `make check`, with existing qualified resources and
pilots before any costly campaign.
