# Reconstruction and improvement of the 935 horizontal system

[Two separate programs](../../FAN_DEVELOPMENT_PROGRAMMES.en.md) ·
[Dossier and bill of materials](README.en.md) · [Sources](sources.json)

## Selected implementation order and current state

Qualified Linux/Python/.NET environment → surfaces from the scans with
SciPy/PicoGK → assembly and BRep/FreeCAD interfaces → OpenFOAM →
Gmsh/CalculiX → SciPy optimization then OpenMDAO coordination → PhysicsNeMo
model on accepted calculations → USD/Omniverse assembly and results.
The historical reference comes before the improved variant. The first work package covers
numerical validation and the [bench protocol](BENCH_PROTOCOL.md);
manufacturing and physical validation come afterward.

On October 6, 2026, the owner set the target of the first assembly:
**an exact replica of the horizontal system and its mounting on a 935**.
The layout, interfaces, transmission and air guides of this
reference are reconstructed before any improvement. A second step
will adapt the horizontal system to a **993 engine**, with its own installation
contract; it stays separate from the vertical 993 program.
The vehicle families are known, but the exact variants and their
mounting dimensions remain to be qualified. This decision validates no
interface or dimension that is still unknown.

The [implementation record for October 5 to 7](IMPLEMENTATION.md) contains the
executable commands, versions, checks and limitations. The coordinator accepts
a case, a step and a new private folder. The campaign reconstructed nine
observed blade ranges, produced three PicoGK resolutions, an editable native CAD
model and the deviation/section maps. The continuation adds two open analytic
surfaces of the hub, checked on held-out sectors of the scan
and exported to FreeCAD/STEP. The detailed data and results are saved
in the [private GitHub archives](https://github.com/cluster2600/porscheparts-935-private).
The mechanism now has a shaft portion with 22 observed periodic
lobes, with an editable open loft, a gap map and bidirectional deviations
to the STEP. The mating splines and the internal gears remain unknown.
The support also has a local inspection plane and a portion of
bore wall reconstructed over its only acquired arc; their reference frames remain
inspection candidates, without the status of a measured mounting datum.
It has not yet closed the geometry
of the rotor, the metrology of the interfaces or the mechanism; the physical steps
that depend on them remain open. No former proxy enters the reference
calculations and no new Vast rental is used.

The expected result is an editable source geometry for all
specific parts, a bill of materials of the standard components, an assembly with
documented interfaces, calculations characterizing the system and a twin
tested against measurements for the 935 replica, then for the 993 adaptation and the
improved versions. The supplied specimen serves as the starting
reference; an exact reproduction and a redesign of a non-observable zone
have distinct statuses. The work packages below characterize the reference and
the improved variants with the same evidence requirements.

## Work package 1 — Reference frames, segmentation and interfaces

Take the two OBJ files present as reversible private copies. Segment the
mechanical parts and the acquisitions without discarding unknown fragments.
Classify holes, missing surfaces and intersections before repair. Identify
the back regions of the rotor and the hub/shaft stack of the Fan Drive.

Establish an engine reference frame and part reference frames: vertical output axis,
input axis, mounting faces and angular reference. The private PCA poses
are used only for inspection. Measure orthogonality, center distances and
transformations before asserting a common assembly.

For each interface in the bill of materials: source side and receiving side,
axis/face/holes, nominal dimension, tolerance, fastening method, transmitted load and
independent evidence. Priority: rotor/hub/vertical shaft; shaft/bearings;
support/engine; pulley/input shaft; housing/rotor; guide/engine.
Surfaces that were not acquired stay out of the functional contract.

Obtain the export unit and at least two calibration dimensions per scan, with
tool/uncertainty. The rotor and the drive are not scaled by
visual fitting. The housing/guide scans and a view of the mounted
assembly complete the work package when they are accessible. The catalogue or a
disassembled inspection must resolve the hidden interfaces and internal parts.

**Deliverables:** component register, assembly matrix, interface
contract, coverage map and acquisition list. **Gate:**
traceable assembly without scale contradiction or invented coordinates.

## Work package 2 — C# PicoGK reconstruction and usable CAD

Reuse the existing C# PicoGK chain after a witness of the exact runtime.
Reconstruct separately rotor, hub, support/housing, shafts, pulleys and
guides with parameters derived from the observed regions. Preserve section
distributions and functional surfaces. The voxel resolution is subject to
a study over three step sizes; the choices must resolve walls and clearances.

The gears are not obtained by copying the external envelope.
Qualify type, tooth count, ratio, module/geometry, face width, angle,
axis positions, clearances and process before defining them. With these data,
produce the geometric source and the drawings suited to the process. Standard bearings,
seals and belts are specified by part number and interface;
manufacturing them in full is not assumed to be necessary.

Measure the bidirectional deviations between reconstruction and scan on the observed
regions, then sections, thicknesses, clearances and continuity. Interpolated
or redrawn zones have their own status and a justification.
The error budget depends on the metrology; no universal accuracy
is promised on the basis of the file name.

**Deliverables:** C#, parameters, PicoGK geometry, meshes and interface drawings.
Complete with a surface/BRep reconstruction in a CAD tool for a
usable STEP; the voxel envelope does not replace machining tolerances
or the qualification of gear teeth. **Gate:** fidelity, integrity and
completeness of the interfaces compatible with the calculation concerned.

## Work package 3 — Kinematics and transmission

Establish dimensions, blade count, volume and section distributions.
With documented density and material: mass, center of gravity and inertia
tensor. For each rotor speed, calculate tip speed, Mach,
Reynolds and blade-passing frequency; leave the unknown physical inputs
explicit and produce separate scenarios if necessary.

Establish direction of rotation and overall ratio from pulley pitch
diameters and the actual gear ratio, with an explicit input/output convention.
Ratios taken from old M64 cutaways and the speeds of commercial kits
do not constitute data for this transmission.

Calculate rotor and shaft speeds, reflected inertias, aerodynamic torque,
accelerations/decelerations and belt loads. Establish losses and the power
balance from the engine to the fan. The required torque includes the inertia
variation and the losses, beyond the steady-state speed alone.

After internal identification: radial/axial gear tooth loads,
bending/torsion of the shafts, contacts, strength of the housing, bolts and bearings. The
[ISO 10300-1 framework](https://www.iso.org/standard/79401.html) covers the load
capacity of bevel gears; the full text and the applicable parts
remain to be consulted for the selected gear. Public data sheets are not
evidence of compliance.

Define fits, preload/clearance, speed, bearing service life, lubrication,
sealing and heat dissipation of the right-angle drive. The
[ISO 281](https://www.iso.org/standard/38102.html) and
[SKF](https://evolution.skf.com/new-skf-engineering-software-for-the-evaluation-of-bearing-arrangements/)
methods are calculation references, not 935 part references. The edition and
the limits of application must be frozen when the calculation is launched.

**Deliverables:** kinematic diagram, torque/speed curves, loads and
loss budget. **Gate:** identified inputs and results checked
by independent calculations and corresponding measurements.

## Work package 4 — Flow, distribution and cooling

Mesh the assembly of rotor and stationary parts with its true housing geometry,
clearances and obstacles. An isolated pilot is useful to check the method; it
is not a prediction of the installed system.

Under OpenFOAM, check surfaces and the volume mesh before the solver,
rotating/stationary domains, interfaces, turbulence, boundary layers and `y+`.
First run an accepted pilot point, then flow/pressure/torque and
power curves over the relevant speeds and back-pressures. Compare three
meshes, convergence windows, conservation and energy balance;
resolve in time the interactions that require it.

An MRF model can be used for mean characteristics; a transient rotating
interface is necessary for the selected unsteady
interactions. Qualify compressibility and the flow model from the velocities
and dimensionless numbers, with a frozen OpenFOAM family/version.

Include the resistance of the guides and engine passages to obtain the installed
point and the distribution per zone/cylinder. The thermal calculation depends on the
engine loads, the heat-exchange surfaces and the defined air/water variant.
Keep separate the exchanges with oil, intercooler or water cooling
if they are not part of the documented air network. A horizontal orientation
does not, on its own, demonstrate better distribution.

**Deliverables:** curves, native fields, distribution, losses, temperatures and
uncertainties according to the available data. **Gate:** fidelity of the network,
convergence and agreement with measurements; no former 993 field is attached to
the 935 geometry.

## Work package 5 — Strength, vibration and manufacturing

On the qualified assembly, combine centrifugal load, pressure, temperature,
drive, contacts and fasteners. Check blade roots, hub,
shafts, housing/support and retention of the clearances. Spatial convergence and the distinction
between numerical singularities and physical stresses are necessary.

Perform prestressed modes in rotation and a Campbell diagram with bearing stiffnesses,
gyroscopic effects according to the solver's capabilities, engine orders, blade
passing and gear mesh frequency. Add transients, fatigue and a usage
spectrum when material, process, surface and fatigue data are
qualified. Plan balancing with
[ISO 21940-11](https://www.iso.org/standard/54074.html) if rigid behavior
is applicable; do not arbitrarily impose a balance quality grade.

Define the process for each part: machining, gear cutting/treatment,
forming/composite or additive manufacturing when justified. Document
material, orientation, treatments, machining allowances, inspection and standard
components. The aluminum/magnesium/composite choice remains specific to the specimen
and to the qualified design.

**Deliverables:** mechanical fields, dynamics, fatigue criteria and
manufacturing/inspection dossier. **Gate:** technical review and corresponding
test plan; rotating tests remain under human responsibility.

## Optimization after characterization of the reference

Define controlled variants on the sections, twist, camber,
blade roots and tips, then the hub, the support and the air
passages. Evaluate current materials and processes with properties at temperature,
surface condition and inspectability. The gear teeth, bearings and lubrication
can be redesigned when the loss budget and the loads justify it.

Measure the mass of the rotor and of the assembly, inertia, actually distributed flow,
pressure, power at the transmission input and relevant temperatures.
Compare at the same rotor speed, air and network, then at a common power budget
if the variants require different torques. Quantify the uncertainty
of the differences. No numerical gain target is invented before these data.

Keep the defined installation interfaces or explicitly document
their evolution. Recalculate structure, hot/rotating clearances, modes and fatigue
for each selected candidate. A lighter shape or a modern material is not
enough to qualify the overall gain. The result of this work package is a traceable
comparison and a candidate variant for testing, with its known trade-offs.

## Work package 6 — Validation and digital twin

Define tests that distinguish transmission, fan on the bench and installed
system. Measure input/output speed, torque/power, temperature of the
right-angle drive, flow/pressures, thermal distribution and vibration. Document
calibration, uncertainties and independent validation points. Any
overspeed/balancing bench requires an appropriate enclosure and protocol.

Compose all confirmed parts in OpenUSD with units, reference frames,
assembly and kinematic joints. Associate each result with its geometric
hash, conditions, solver version, materials and validation status.
Keep native formats and the cell/point association for the Omniverse review.

Include transmission losses and the thermal/airflow network in the system
model. A reduced-order model can interpolate the accepted calculations within their
domain of validity and be tested against the sensors. An animation of the
impeller alone does not close this work package.

**Final deliverables:** sources and CAD, bill of materials, drawings, calculation dossier,
test plan/report and twin package. Physical validation remains
open if the corresponding measurements are not available.

## First geometric delivery

The next usable work package will be the segmented rotor + support/drive
assembly, its reference frames and the interface contract, followed by the first
scan-based PicoGK generator. The hidden parts and the guides will have explicitly
missing inputs. No plausible solid will replace them in an
assembly declared complete.

The raw data, derivatives and parameters derived from geometry under unknown rights
remain private. Generic code and permitted reports may be
versioned. Implementation changes will be verified by the
targeted checks and `make check`, with qualified existing resources and
pilots before any costly campaign.
