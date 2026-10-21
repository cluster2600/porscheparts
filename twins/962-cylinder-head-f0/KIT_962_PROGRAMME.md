<a id="programme-produit--kit-moteur-inspiré-du-962-objectif-1-000-ch"></a>

# Product program: 962-inspired engine kit, 1,000 metric-horsepower target

**Priority of October 16, 2026: reconstruct the water-cooled 3.0 L 962 C head
as faithfully as possible, then develop a range up to 4.0 L.** The
[family dossier](REPLICA_FAMILY.md) and its [register](replica-family.json)
carry this decision. The following text preserves the earlier modern
conversion program: its two spark plugs, SP95 and 1,000 PS are not
automatically characteristics of the replica or the entire range.

<a id="programme-antérieur-de-conversion-moderne"></a>

## Earlier modern conversion program

**Owner's stated objective: develop and then sell a kit that converts a
classic 911, 964 or 993 engine into a modern 962-inspired engine.**
It retains the four-valve, twin-ignition, water-cooled, bionic-geometry and
additive-manufacturing target. The 1,000 metric horsepower is a development
target, with no engine result to date.

The [product register](kit-program.json) retains this objective, unknowns,
variants and required evidence. “962 kit” is a working name; the proposed
product is a modern conversion, not an original Porsche 962 engine.

<a id="première-version-et-décisions-ouvertes"></a>

## First version and open decisions

The proposed first industrial deliverable is **a bench demonstrator engine
built on one identified variant**, then installed and tested in one vehicle
configuration. The commercial kit would follow qualification, with assembly
by an engine builder and a traceability dossier.

Owner-confirmed target: **1,000 metric horsepower (PS) at the crankshaft**,
with qualification **on the bench then on the track**. The owner later
specified **Mezger 4 L twin-turbo on SP95**; the [updated sizing study](MEZGER_4L_SP95_EN.md)
retains the assumptions and associated requirements. The exact donor variant,
fuel batch and endurance cycle remain to be defined. No calculation converts
crankshaft power into wheel power using an arbitrary loss percentage.

The 993 Turbo M64/60 was proposed as the first **reference candidate** because
the [existing engine program](../m64-engine-system/program.json) already covers
that variant. Its physical availability and 1,000 metric-horsepower capability
are not established. This proposal does not select the donor for the owner
or prove Carrera compatibility. The stated Mezger target is insufficient to
identify a variant or its interfaces.

| Envisaged commercial base | Treatment in the program |
|---|---|
| 993 Turbo M64/60 | Initial candidate; case, cylinders, studs, oil and drivetrain to measure/qualify |
| 993 Carrera M64 | Separate variant; naturally aspirated-to-turbo conversion and interfaces to establish |
| 964 Carrera M64 | Separate variant, compared with the pilot donor after metrology |
| 964 Turbo | Distinguish exact engine and displacement; do not treat every 964 as an M64 |
| Earlier classic 911s | Later phase by engine type; no universal kit claimed |

**Central gate: can the donor case be retained durably at the selected power
and duty cycle?** If another case is needed, the kit, cost and actual retained
portion of the engine must be reconsidered. Turbo-case robustness does not
transfer to a Carrera by assumption.

<a id="périmètre-du-kit-à-développer"></a>

## Kit scope to develop

| Subassembly | Proposed manufacturing route | Qualification dependency |
|---|---|---|
| Six heads, 24 valves, 12 spark plugs | LPBF bodies; machined seats, guides, threads and planes; dedicated valve components | M64 metrology, chambers/ports, seat retention, sealing and fatigue |
| Camshaft carrier and DOHC drive | Donor-compatible architecture to define; machined gears/chains, shafts and contacts | Kinematics, lubrication, clearances, piston/valve clearance and lifetime |
| Cylinders and head connection | Reuse or replacement according to CHT; full water cooling to compare with a mixed solution | Combustion decks, registers, preload, distortion and seals |
| Bottom end | Inspected then analyzed case; conventional pistons/rods/crankshaft or qualified specialized components | Cylinder pressure, bearings, fatigue, detonation, speeds and torque |
| Water and oil | Complex galleries/manifolds as AM candidates; qualified pumps, radiators, seals and fittings | Flow, pressure loss, degassing, boiling, oil return and thermal load |
| Forced induction and charge air | Purchased and characterized turbos; manifolds/plenums as AM candidates; dedicated exchangers and wastegates | Flow/pressure maps, backpressure, temperatures and transient response |
| Fuel supply and control | Qualified injectors/pumps/sensors/ECU, twin-ignition calibration | Fuel and pressure, knock, mixture, protections and degraded modes |
| Vehicle installation | Variant-specific mounts and lines; verified clutch, gearbox and drivetrain | Torque, in-car cooling, braking/tires and intended use |
| Commercial delivery | BOM, manual, approved torques/clearances, serial numbers, final inspection, maintenance and spares | Manufacturing repeatability, workshop installation, total cost and usage rules |

3D printing serves internal passages and shapes that are otherwise impossible
or expensive to produce. It does not become a requirement for every part.
A printed case, head or connecting rod is accepted only after comparing the
process with alternatives and qualifying its function. The kit may therefore
combine printed, forged, machined and purchased parts.

The CP1/CuCrZr options in the [material dossier](README.md#matière--conductivité-et-tenue-à-chaud)
remain open. No benefit, mass, price or lifetime is promised.
The existing M64 twin's K16 turbos are an original reference, not a
1,000 metric-horsepower turbo selection.

The owner also proposes a GemaTEG-inspired enclosure with waterblocks, fans
and Peltier devices. The [thermal-module study](THERMAL_MODULE.md) adds a
candidate secondary branch; main heat exchangers remain necessary.
The balance includes TEC electricity and hot-side heat rejection.

<a id="ce-que-signifie-la-cible-de-puissance"></a>

## What the power target means

Four-stroke scoping calculations with a **hypothetical 3.6 L displacement**:

| Calculation point | Power | Associated torque | Associated BMEP |
|---|---:|---:|---:|
| 1,000 PS at 6,000 rpm | 735.499 kW | 1,170.6 N·m | 40.86 bar |
| 1,000 PS at 7,000 rpm | 735.499 kW | 1,003.4 N·m | 35.02 bar |

Relations: `P = 2πNT/60` and `BMEP = 4πT/Vd`. BMEP is brake mean effective
pressure, **not peak combustion pressure**. These historical points selected
neither speed, displacement, boost, efficiency nor fuel. The linked 4 L/SP95
budget replaces their 3.6 L assumption for active sizing; the historical data
remain readable. They do not calculate head heat flux or validate the case
or gearbox. Complete values are in [kit-program.json](kit-program.json),
checked by a dimensional test.

The engine must be defined by a torque/power curve, fuel, inlet conditions
and a duty cycle. A bench peak demonstrates neither continuous power nor
commercial service life. Correction standard, instrumentation, repetitions,
endurance duration and maintenance interval must be set **before** the
qualification test.

<a id="précédents-consultés-et-signal-commercial"></a>

## Consulted precedents and commercial signal

[Swindon Powertrain](https://swindonpowertrain.com/products/24-valve-porsche-911-m64-cylinder-head-kit/)
offers a 24-valve kit for 964/993 M64 engines that, according to the
manufacturer, retains original valvetrain and lubrication interfaces.
Its [data sheet](https://swindonpowertrain.com/wp-content/uploads/2025/10/M64-24V-Cylinder-Head-Kit-Product-Sheet-0923.pdf)
lists a complete head and valvetrain kit, with air-cooled cylinders.
This is a conversion precedent, without proving our water-cooled architecture,
twin ignition or 1,000 metric horsepower.

The [webshop consulted on October 12, 2026](https://webshop.swindonpowertrain.com/index.php?product_id=361&route=product%2Fproduct)
lists £31,447.50 excluding tax for the base kit, made to order.
This is a displayed competitor price, not our quote, production cost or
sales evidence. The complete product and accessories have a different scope.

The [2024 MAHLE Motorsport guide](https://www.us.mahle.com/media/usa/motorsports/2024-mahle-motorsport-porsche-application-guide-2.pdf),
printed page 5, distinguishes 993 Turbo applications from 964 Turbo/converted
993 Carrera applications, and installations with/without register machining.
This is a concrete reason to qualify variants separately; kit dimensions do
not replace donor-case measurement and are not power limits.

**Customer hypothesis to test:** 964/993 owners and preparation workshops
seeking a documented conversion with controlled power, maintenance and
installation cost. A competing offer does not demonstrate willingness to
pay for our product.

The first proposed commercial research is five owner interviews and five
engine-builder/installer interviews: actual need, use, available fuel,
acceptable total installed price, maintenance and purchase conditions.
No interview or purchase commitment is performed or claimed here.
No revenue is projected from an assumed customer count.

A selling price will be proposed only after a costed BOM, manufacturing,
machining and inspection quotes, material yield and scrap, assembly,
calibration, installation, warranty/service and small-series assessment.
Suppliers, prices, volumes and margin remain unknown.

<a id="parcours-de-qualification-et-critères-de-réussite"></a>

## Qualification path and success criteria

1. **G0 — product target.** Crankshaft power and bench/track priority confirmed;
   set fuel, duty cycle and exact donor. Define delivered scope, installation
   and target total cost with the first users.
2. **G1 — interfaces and bottom end.** Donor metrology/CT; compatibility map;
   case, stud and load-path review. Assess cylinder and valvetrain-drive
   retention/replacement.
3. **G2 — one head and coupons.** M64 reconstruction, four valves and two spark
   plugs laid out on measured interfaces; CHT and stress, LPBF coupons, CT,
   cleaning, material and approved hydraulic proof testing.
4. **G3 — instrumented six-cylinder engine.** Complete assembly, calibration and
   staged loading approved by the engine builder; monitor cylinder pressure,
   temperatures, oil/water, knock and distortion. A repeatable measurement at
   the target does not close the endurance program.
5. **G4 — vehicle and endurance.** Validate installation, thermal management,
   drivetrain, braking and customer cycle; set operating limits, maintenance
   and regulatory requirements specific to the country and use.
6. **G5 — saleable small series.** Professional review and approved plan,
   repeatable process, successful tests, published compatibility, workshop
   installation, traceability, cost, warranty and support. Sales and technical
   claims follow evidence, not the twin's render.

Gates G1–G5 remain open. The [G1 acquisition dossier](DONOR_METROLOGY.md)
provides the donor-interface measurement sheet; [material qualification](MATERIAL_QUALIFICATION.md)
defines the data to obtain for each LPBF recipe.
The [F0 coolant boundary diagnostic](COOLANT_BOUNDARIES.md) extracts the
two sections and keeps the coolant/metal probing gaps before any CFD.
The [cylinder head gallery](GALLERY.md) shows the exterior, a cutaway and the
conformal water jacket. The [architectural dossier](ORIGINAL_ARCHITECTURE.md) links
the 962 C photographs to the ShapeKernel shapes and documents the accepted/rejected
Qwen responses. The [generic block](STOCK_ENVELOPE.md) and the
[routing refinement](REFINEMENT.md) are kept.
The [F0 head contract](interface-contract.json) and its digests are preserved.
The [existing M64 program](../m64-engine-system/program.json) supplies per-zone
references without transferring its fidelity levels or interfaces to this kit.
PicoGK/CHT/mechanical analysis/assembly follow the [existing architecture](../../docs/architecture/README.md);
no new simulator, scheduler, purchase, supplier contact or preorder is launched.
