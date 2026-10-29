# Replica preparation and validation

## Required specimen and engine information

Prepare the following request for the seller and Xtreme. No request has been sent.
Measurements may be commissioned from the seller, manufacturer or a laboratory;
the owner need not personally possess the specimen.

1. Exact Xtreme reference, revision, family, approximate date, options, markings and bill of materials.
2. Donor configuration: engine type, bore/stroke, displacement, pistons/chamber, compression, turbos, intake, cooling, rpm, fuel and duty. Keep vehicle identifiers private.
3. Scan units, scanner, resolution, accuracy, registration, hidden surfaces and processing history; three independent same-specimen dimensions with uncertainties, not dimensions extracted from the same mesh.
4. Authorised drawings/CAD for ports, chamber, seats, guides, plugs, registers, studs, fasteners and galleries, including datums and tolerances.
5. Specimen alloy, batch certificate, heat treatment/HIP, service history, repairs, resurfacing and distortion.
6. Actual valves, guides, seats, springs, retainers and locks; cams/timing, moving masses, cold/hot clearances and preload.
7. Intake/exhaust flow curves against lift with depression, temperature, adapters, test bore, instrumentation and uncertainty. A peak-flow number is insufficient.
8. Power/torque curves and correction method, absolute intake pressure, exhaust backpressure, temperatures, mixture, ignition, crank-angle-resolved cylinder pressure, oil conditions and fan/air circuit.
9. Rights to reconstruct, manufacture and inspect the replica; separately establish redistribution rights.

## Work before paid compute

Freeze and hash the original scan. Classify surfaces as observed, measured, hidden,
reconstructed or unknown. Separate the head and its attached hardware without
silently cutting functional surfaces. Define an inspection plan for mating planes,
valve/plug axes, holes, registers, port sections, walls and oil galleries.

Prepare editable geometry and deviation checks. Do not smooth a seat or close a
gallery without evidence: a watertight envelope does not prove internal geometry.
Flow and thermomechanical cases must retain unknown fields, units, sources and
uncertainties. Agree tolerances, uncertainty budgets, correlation limits, cycles
and engine limits before computation. Generic thresholds are not substitutes.

Pin runtimes and scripts, preserve logs and restart information, and use independent
checks. The [execution report](EXECUTION.md) records which preparation steps actually ran.

## Gates before design optimisation

| Gate | Deliverable | Acceptance evidence |
|---|---|---|
| G0 — Identity | Specimen and donor dossier | Manufacturer/revision/configuration linked to evidence; critical unknowns resolved |
| G1 — Faithful CAD | Editable source, STEP, drawings, deviation map | Verified scale; complete interfaces and internal volumes; independent inspection to approved tolerances |
| G2 — Reference function | Flow, thermal and mechanical reference tests; correlated model | Representative conditions, conservation and convergence; correlation within the acceptance plan |
| G3 — Printing process | Machine/material/orientation/parameters/treatments/machining route | Representative coupons, defects and hot properties accepted by engineering review |
| G4 — Finished printed head | Metrology, CT/NDT, seats/guides/threads, cleaning and leakage | Actual finished-part results accepted; a coupon or print simulation alone is insufficient |
| G5 — Replica operation | Comparative flow, thermal cycling, instrumented engine bench and post-test inspection | Performance and target life demonstrated in the agreed envelope with a signed report |
| G6 — Design iterations | Variants against a frozen baseline | G0–G5 closed; traceable comparison and renewed validation of changes |

G2/G3 preparation may proceed alongside reconstruction. Physical tests need external
facilities. Solver convergence does not close G5; polymer printing does not qualify
metal; CT does not replace fatigue or representative cycling.

Preserve separate valves, guides, seats and springs. Do not fuse them into the print
to reproduce an assembled scan. Confirm the nominal definition and delivery condition.

## Vast execution package and budget

Select hardware from a benchmark, not GPU count. Before rental, require an input/hash
manifest and transfer rights; frozen geometry and inspection criteria; verified fluid
and solid domains, meshes and boundary conditions; process-specific material laws;
pinned solver options; a working small case; spatial/time convergence and conservation
checks; measured RAM/time; checkpoint/export verification and task-owned resource teardown.

The owner authorised **USD 35 total: USD 30 compute and USD 5 reserved for transfer
and teardown**. This is a budget instruction, not an implemented billing controller.
Count compute, storage and network charges; stop sooner if the reserve becomes
insufficient. No rental is needed for an unprepared or physically underdefined case.
No machine has been rented by this task; no fabrication or engine test is authorised
by this document.

## Completion accounting

The contract tracks twelve input packages. Admit a package only with specimen-specific
evidence and suitable independent checks. Keep catalogue ranges separate. Completion
requires 12/12 input packages and G0–G5, not an arbitrary percentage of “head finished”.
All twelve packages currently remain incomplete. Continue independent work while
leaving affected downstream gates blocked.
