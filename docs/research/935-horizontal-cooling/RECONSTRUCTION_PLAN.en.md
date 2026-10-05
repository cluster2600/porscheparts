# Reconstruction and improvement of the horizontal 935 system

[Two distinct programmes](../../FAN_DEVELOPMENT_PROGRAMMES.en.md) ·
[Dossier and bill of materials](README.en.md) · [Sources](sources.json)

Expected outcome: editable source geometry for every specific part, standard
component bill of materials, assembly with documented interfaces, calculations
characterizing the system and a twin compared to measurements, for a modernized,
lighter version delivering more useful engine air. The supplied specimen is the
initial reference. Exact reproduction and redesign of an unobservable region
have separate statuses. The batches below characterize reference and improved
variants under identical evidence requirements.

## Batch 1 — Frames, segmentation and interfaces

Use reversible private copies of the two available OBJ files. Segment mechanical
parts and acquisitions without eliminating unknown fragments. Classify holes,
missing surfaces and intersections before repair. Identify rotor back regions
and the Fan Drive hub/shaft stack.

Establish engine/part coordinates: vertical output axis, input axis, mounting
faces and angular reference. Private PCA poses are for inspection only. Measure
orthogonality, spacing and transformations before claiming a shared assembly.

For every bill-of-materials interface, record source/receiver sides, axis/face/
holes, nominal dimensions, tolerance, fastening, transmitted load and independent
evidence. Prioritize rotor/hub/vertical shaft, shaft/bearings, support/engine,
pulley/input shaft, housing/rotor and guide/engine. Unacquired surfaces remain
absent from the functional contract.

Obtain export unit and at least two calibration dimensions per scan with tool/
uncertainty. Do not scale rotor/drive by visual adjustment. Housing/guide scans
and an installed assembly view complete the batch when accessible. Catalogue
or disassembled inspection must resolve hidden interfaces/internal parts.

**Deliverables:** component registry, assembly matrix, interface contract,
coverage map and acquisition list. **Gate:** traceable assembly without scale
contradiction or invented coordinates.

## Batch 2 — C# PicoGK reconstruction and usable CAD

Reuse existing C# PicoGK after a control of the exact runtime. Reconstruct rotor,
hub, support/housing, shafts, pulleys and guides separately using observed
regions' parameters. Retain section distributions and functional surfaces.
Study three voxel spacings; selections must resolve walls and clearances.

Gears cannot be recovered by copying external envelopes. Qualify type, tooth
count, ratio, module/geometry, width, angle, axis positions, clearances and
process before defining them. Then create geometric source and process-suitable
drawings. Standard bearings, seals and belts use references/interfaces; complete
manufacture is not assumed necessary.

Measure bidirectional reconstruction/scan differences on observed regions,
sections, thicknesses, clearances and continuity. Interpolated/redesigned regions
have explicit status and justification. Error budget depends on metrology;
filenames promise no universal precision.

**Deliverables:** C#, parameters, PicoGK geometry, meshes and interface drawings.
Add surface/BRep CAD reconstruction for usable STEP: a voxel envelope replaces
neither machining tolerance nor gear qualification. **Gate:** fidelity, integrity
and interface completeness suitable for the intended calculation.

## Batch 3 — Kinematics and transmission

Establish dimensions, blade count, volume and section distributions. Documented
density/material give mass, centre of gravity and inertia tensor. At each rotor
speed calculate peripheral speed, Mach, Reynolds and blade passing frequency;
leave unknown physical inputs explicit and use separate scenarios if necessary.

Establish rotation direction and overall ratio from pulley pitch diameters and
actual gear ratio with an explicit output/input convention. Ratios from older
M64 sections and commercial kit speeds are not this transmission's data.

Calculate rotor/shaft speeds, referred inertia, aerodynamic torque, acceleration/
deceleration and belt loads. Establish losses and engine-to-fan power balance.
Requested torque includes changing inertia and losses beyond steady operation.

After internal identification, calculate radial/axial tooth loads, shaft bending/
torsion, contacts, housing, fasteners and bearings. [ISO 10300-1](https://www.iso.org/standard/79401.html)
concerns bevel gear load capacity; complete text and applicable parts remain
to review for the selected gear. Public sheets do not prove compliance.

Define fits, preload/clearance, bearing speed/life, lubrication, sealing and
drive heat dissipation. [ISO 281](https://www.iso.org/standard/38102.html) and
[SKF](https://evolution.skf.com/new-skf-engineering-software-for-the-evaluation-of-bearing-arrangements/)
are calculation references, not 935 part references. Freeze editions/application
limits before calculation.

**Deliverables:** kinematic diagram, torque/speed curves, loads and loss budget.
**Gate:** identified inputs and results checked by independent calculations and
corresponding measurements.

## Batch 4 — Flow, distribution and cooling

Mesh rotor/fixed assembly with actual housing, gaps and obstacles. An isolated
pilot checks method; it does not predict installed performance.

Under OpenFOAM, check surfaces and volume mesh before solver, rotating/fixed
domains, interfaces, turbulence, boundary layers and `y+`. First obtain an
accepted pilot point, then flow/pressure/torque/power curves across relevant
speeds/backpressures. Compare three meshes, convergence windows, conservation
and energy balance; resolve time-dependent interactions where required.

MRF may describe mean characteristics; selected unsteady interactions require
a transient rotating interface. Qualify compressibility/flow model from speeds
and dimensionless numbers with frozen OpenFOAM family/version.

Include guide/engine passage resistance for installed operating point and
distribution per zone/cylinder. Thermal calculation needs engine loads,
exchange surfaces and defined air/water variant. Keep oil, intercooler and water
exchange separate if outside documented air network. Horizontal orientation
alone does not establish better distribution.

**Deliverables:** curves, native fields, distribution, losses, temperatures and
uncertainties as inputs permit. **Gate:** network fidelity, convergence and
measurement agreement; no old 993 field is assigned to 935 geometry.

## Batch 5 — Strength, vibration and manufacturing

On qualified assembly, combine centrifugal, pressure, temperature, drive,
contact and fastening loads. Check blade roots, hub, shafts, housing/support
and maintained clearances. Spatial convergence and distinction between
numerical singularities and physical stresses are necessary.

Calculate rotation-prestressed modes and Campbell with bearing stiffness,
gyroscopic effects as solver permits, engine orders, blade passing and gear
meshing frequencies. Add transients, fatigue and service spectrum when material,
process, surface and fatigue data are qualified. Plan balancing under
[ISO 21940-11](https://www.iso.org/standard/54074.html) if rigid behaviour applies;
do not impose an arbitrary balance class.

Specify each part's process: machining, teeth/treatment, forming/composite or
justified additive manufacture. Document material, orientation, treatments,
stocks, inspection and standard components. Aluminium/magnesium/composite
selection remains specific to specimen and qualified design.

**Deliverables:** mechanical fields, dynamics, fatigue criteria and manufacture/
inspection dossier. **Gate:** technical review and corresponding test plan;
rotation testing remains human responsibility.

## Optimization after reference characterization

Define controlled section, twist, camber, root/tip variants, then hub, support
and airflow passages. Evaluate current materials/processes using temperature
properties, surface condition and inspection capability. Teeth, bearings and
lubrication can be redesigned where losses/loads justify it.

Measure rotor/assembly mass, inertia, distributed flow, pressure, transmission
input power and relevant temperatures. Compare at identical rotor speed, air
and network, then common power if torques differ. Quantify difference uncertainty.
Invent no gain target before these data.

Retain established installation interfaces or explicitly document their change.
Recalculate structure, hot/rotating gaps, modes and fatigue per selected candidate.
Lightening or modern material alone does not qualify system gains. This batch
produces traceable comparison and a test candidate with known tradeoffs.

## Batch 6 — Validation and digital twin

Separate transmission, bench fan and installed system tests. Measure input/output
speed, torque/power, drive temperature, flow/pressure, thermal distribution and
vibration. Document calibration, uncertainties and independent validation points.
Any overspeed/balance bench needs suitable enclosure/protocol.

Compose confirmed parts in OpenUSD with units, coordinates, assembly and
kinematic connections. Link every result to geometry hash, conditions, solver
version, material and validation state. Retain native formats and cell/point
association for Omniverse review.

Include transmission losses and thermal/airflow networks in the system model.
A reduced model can interpolate accepted calculations within their valid domain
and compare to sensors. A wheel animation alone does not close the batch.

**Final deliverables:** sources/CAD, bill of materials, drawings, calculation
dossier, test plan/report and twin package. Physical validation remains open
without corresponding measurements.

## First geometry delivery

The next usable batch is segmented rotor + support/drive assembly, coordinates
and interface contract, then the first scan-based PicoGK generator. Hidden parts
and guides retain explicitly missing inputs; plausible solids cannot replace
them in an assembly claimed complete.

Raw data, derivatives and parameters from geometry of unknown rights remain
private. Generic code/permitted reports can be versioned. Implementation changes
require targeted checks and `make check`, existing qualified resources and pilots
before any costly campaign.
