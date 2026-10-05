# Measurements needed to turn the purchased scan into engineering evidence

This checklist applies independently to the scanned 935-labelled specimen and the target 993 Turbo assembly. It does not presume they fit each other. Proposed measurements and workflows below are engineering recommendations, not quoted Porsche procedures or tolerances.

## 1. Resolve identity before scale

Record:

- Vehicle/engine application, year, exact engine type, factory/customer-racing or replica status
- Every cast, stamped or machined identifier, with close-up and full-part photographs
- Number of blades, angular spacing, blade handedness, hub/cup/opening pattern and material appearance
- Actual rotor, housing, hub, pulley, shaft/bearing, rear cone and alternator included in the assembly
- History of repairs, coatings, machining, blade trimming, hub replacement and balancing cuts
- Vendor's original filename, acquisition date, scanning process, units, calibration and licence

Ask exactly what “back not lined up with center” means. Request the original separate front/back passes and registration references if they exist. Do not infer a failure mode from that phrase alone.

## 2. Minimum scale/alignment packet

| ID | Required measurement | Datum / method | Why it is needed | Current state |
|---|---|---|---|---|
| M01 | Clean machined bore/register diameter at multiple depths and angles | Bore gauge/CMM; local cylinder fit | Functional rotation axis A and small-scale check | Missing |
| M02 | Swept tip diameter around verified A | CMM/rotary metrology; record all tips | Large-scale radial check and real envelope | Missing |
| M03 | Face-to-face axial distance between two identified machined planes | Height gauge/CMM; exact surfaces photographed | Independent axial scale/distortion check | Missing |
| M04 | Mounting/abutment plane location and flatness | Independent plane fit | Datum B; prevents hiding warped registration | Missing |
| M05 | Keyway/indexed hole position | CMM/optical metrology | Datum C and front/back angular alignment | Missing |
| M06 | Front/back overlapping machined feature coordinates | Both original scan passes and calibrated points | Rigid registration and residual assessment | Missing |
| M07 | Representative blade thickness near root, midspan and tip | Suitable micrometer/CMM/CT; avoid damaging edges | Detect doubled/misaligned scan surfaces | Missing |
| M08 | Raw-file transform and fitting residuals | Record after future scan analysis | Reproducible registration provenance | Missing |

At least two independent physical lengths are necessary for a defensible initial scale check; three well-separated radial/axial checks are preferable. Instrument resolution is not the same as measurement uncertainty. Select the method and uncertainty against the eventual functional tolerance rather than assuming a universal target.

Do not compute M02 from the axis-aligned bounding box of an unaligned mesh. Establish A and evaluate the swept radial envelope. Do not treat a nominal 0.5 mm file label as ±0.5 mm accuracy.

## 3. Rotor aerodynamic and structural geometry

Acquire sections at explicitly documented radii, with enough stations to resolve nonlinear twist, root transition and tip shape. The number of stations should be chosen from measured curvature and fit convergence, not an arbitrary fixed count.

For every blade, retain:

- Leading/trailing-edge positions in A/B/C
- Chord and signed stagger in the declared cylindrical section
- Camber and normal thickness distributions; edge radius and trailing-edge finish
- Axial sweep, tangential skew and the chosen stacking line
- Root fillet and minimum thickness with location
- Tip shape and actual radial/axial envelope
- Surface condition, roughness, damage and missing/inferred scan regions

Measure all blades before averaging. Preserve a mean/idealized model as a derivative and report maximum and statistical deviations from individual blades. A blade-to-blade difference can be measurement error, damage or intentional geometry; do not automatically erase it.

## 4. The target 993 interface stack

| ID | Measurement / evidence | Record details | Consequence if absent |
|---|---|---|---|
| I01 | Rotor bore, steps and registers | Diameters, lengths, GD&T/fit if specified, surface finish | Shaft/hub fit unknown |
| I02 | Mounting face to blade axial envelope | Leading/trailing extrema relative to B | Axial interference unknown |
| I03 | Bolt/key/spline/retaining arrangement | Pattern, threads, engagement, torque/preload source | Load path and retention unverified |
| I04 | Bearing part and seats | Exact IDs, fit, clearance, load/speed/temperature ratings | Support behavior and limits unknown |
| I05 | Housing inner profile | Multiple axial/angular stations, mount condition | Tip gap cannot be established |
| I06 | Housing-to-shaft axis relationship | Eccentricity, tilt, mounting distortion | Cold nominal clearance misleading |
| I07 | Actual fan pulley geometry | Effective pitch diameter, groove, belt path, offset | Speed and bearing loads uncertain |
| I08 | Actual crank pulley geometry | Matching belt effective diameter and offset | Nominal ratio may be wrong |
| I09 | Fan and alternator speed measurements | Separate tachometry across range and load | Dual-speed architecture may be conflated |
| I10 | Selected alternator exact revision | Manufacturer drawing or calibrated physical interfaces | 175 A/240 A/997 dimensions cannot be mixed |
| I11 | Rear cone, auxiliary impeller and supports | Geometry, spacing, assembly relationship | Blockage/cooling/load omitted |
| I12 | Shroud, seals and branches | Complete installed configuration | Flow delivery to heads/cylinders unknown |

Use a stack-up drawing that identifies each contact, fit, fastener, gap and tolerance source. Determine the smallest operating clearance from the combined cold geometry, tolerances, temperature fields, rotational deformation, runout, shaft/bearing motion and mount distortion. Keep correlated terms together and avoid counting the same error twice.

## 5. Bench aerodynamic packet

An appropriately equipped test facility should define safe containment and the speed range before rotating experimental hardware. An unvalidated printed rotor is not a suitable first baseline.

Use an identified, intact reference assembly to obtain:

- Measured fan rpm, flow, pressure rise and shaft torque across a throttled curve at several speeds
- Pressure type and exact inlet/outlet stations; raw transducer values and zero/calibration records
- Ambient and inlet temperature, absolute pressure, humidity and density convention
- Rig geometry and installation category, leakage checks and any flow straighteners
- Alternator electrical load and mechanical losses kept separate from rotor aerodynamic power
- Upstream distortion/swirl and downstream velocity/pressure distribution where practical
- Repeat measurements and uncertainty budgets, especially near instability
- Raw data, acquisition frequency/duration, corrections and the complete processing formulae

Do not compare a free-air flow number with an installed engine flow number as if both measured the same duty. If a supplier supplies only “CFM,” ask at what pressure, rpm, density and assembly configuration.

## 6. Hot-system packet

The desired outcome is adequate cooling of every critical location, not maximum total airflow alone.

Record engine load/rpm/boost, vehicle speed, ambient state, inlet temperature, oil-cooler state, intercooler configuration, alternator load and cabin-heating/auxiliary-air paths. Measure representative cylinder/head temperatures and branch flow/pressure, with sensor locations and uncertainty. Define acceptable temperatures from a defensible engine specification or responsible engine engineer, not from this research.

Test normal and demanding use cases, including heat soak and transients when relevant. State which cases were actually tested, which were simulated, and which remain uncovered.

## 7. Mechanical and manufacturing packet

- Measured final mass, center of mass and inertia or a verified mass model
- Exact material, process and condition; do not identify magnesium/aluminium alloy by visual appearance alone
- Temperature-dependent elastic/static/fatigue properties and statistical basis matching build direction and final surface
- Root/edge quality, defect population, residual stress and approved inspection plan
- Centrifugal plus aerodynamic plus thermal plus joint/belt/gear load cases
- Prestressed modes and speed-order separation with realistic support stiffness
- Mission cycles and fatigue assessment including starts/stops and transient overspeed
- Engineer-selected balance acceptance and correction planes; record residual unbalance after final machining/coating/assembly
- Qualified guarded spin test, post-test inspection and defined acceptance criteria

No process-independent “safe” LPBF blade thickness, balance grade, overspeed multiplier or maximum rpm has been established. These remain release decisions requiring qualified analysis and testing.

## 8. Questions to send only after authorization

For the scan seller:

1. What exact vehicle/engine/year and factory part or casting number does the scanned fan come from? Is it original, reproduction, repaired or modified?
2. What are the exported units, actual measured outer diameter and at least one machined bore/register diameter plus an axial face distance?
3. Does the 0.5 mm label mean point spacing, meshing target, voxel size or something else? What is the calibrated accuracy?
4. What does the unaligned-back filename describe? Can the original separate passes and registration references be supplied?
5. What licence governs the purchased scan, private derived CAD, public renders and public redistribution of a derived mesh or parameter extraction?

For the target assembly/alternator supplier:

1. Can you provide a revision-controlled interface drawing for the exact selected unit and intended 993 Turbo installation?
2. What fan, hub, pulley, bearings, cone and auxiliary impeller are required, and what speed/load/temperature limits apply?
3. Are published dimensions nominal envelopes, inspection dimensions or toleranced interfaces?
4. Is there a measured cooling/performance map or assembly test, with rpm, pressure, power and conditions?

These are prepared research questions, not messages that have been sent.
