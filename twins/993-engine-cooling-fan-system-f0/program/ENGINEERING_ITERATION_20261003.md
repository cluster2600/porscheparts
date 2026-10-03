# Engineering iteration: executable plan and acceptance criteria

This iteration continues the engineering work after PR119. Its deliverable is
a traceable **hypothetical manufacturing candidate**, with explicit failed or
blocked gates. It cannot establish Porsche fit, a qualified metal build or an
approved operating limit without physical evidence. No paid instance, physical
manufacturing or order is authorized.

## Inputs and scope

The [104-parameter contract](research/corpus/geometry/parameter-contract.json)
remains the input dictionary. Unknown scan scale and target interfaces stay
unknown. The purchased scan and its derivatives remain private. No commercial
diameter is used to calibrate it. The 935/993 identity claim is unresolved.

Use the existing original PicoGK reference and Organic E as separate design
hypotheses. E has eleven blades, a nominal 245 mm diameter, 36° root/26° tip
pitch and −3.5 mm camber. These inputs are not physical measurements. Preserve
all earlier geometry, meshes, loads, failed solves and result receipts.

Parameter admission is explicit: geometry/fit parameters require metrology;
drive and fluid operating conditions require measured load cases; material
properties require matching process, condition, orientation and temperature;
LPBF inputs require a controlled recipe and calibration. Parametric values can
be used in sensitivities if identified as assumptions, without advancing any
physical validation gate. The calculation receipts cite the contract IDs used.

## Ordered runs and stop conditions

| Stage | First executable action | Required numerical evidence | Physical evidence still required |
|---|---|---|---|
| Geometry | Audit existing original E surface and independent analysis reductions; test the archived conforming fluid mesh in installed OpenFOAM | Single positive oriented closed solid, zero degenerate faces and zero reported surface intersections; bidirectional sampled errors, retained openings and minimum tip gap; tetrahedral Jacobians positive | Scan units, at least two calibrated dimensions, specimen identity, functional datums and target interface stack |
| CFD | Convert and check the archived 355,404-tetrahedron fluid mesh before any solver; repair recoverable mesh issues in a new directory | Standard **and extended** `checkMesh` pass; if not, no flow solve on that mesh | Housing/alternator/drive geometry and bench pressure–flow–torque map |
| CFD convergence | A new bounded pilot may change mesh or solver formulation; never rerun the rejected 8-million-cell cases unchanged | Two consecutive 100-iteration windows: mass imbalance and mean flow/torque drift <0.1%; peak-to-peak flow/torque <0.2%; last-window initial U residual ≤1e−4, p ≤1e−3, k/omega ≤1e−4; record pressure definition/stations and torque sign | Benchmark uncertainty and installed resistance/branch distribution |
| CFD comparison | Match reference and candidate boundary conditions, signed speed and numerical formulation | At least three accepted meshes; flow, pressure rise and shaft power change ≤5% between finest two, with refinement/GCI assessment where valid; wall/y+ and turbulence sensitivity before quantitative ranking | Correlated physical test points; no apparent gain is released from unconverged cases |
| Structural | Reuse independently audited original decks and run new centrifugal-prestress/modal and manufacture sensitivities | Native solver completion, finite fields, all requested eigenvalues; mesh convergence of deformation and stress (≤5% finest-two change as an iteration target); never discard a peak because it is inconvenient | Interfaces, contact/preload, temperature, aerodynamic pressure, mission history and process-specific statistical strength/fatigue |
| Material | Compare AlSi10Mg routes/states, AlF357 and CP1 from primary data | Separate coupon data from allowables; no invented E(T), yield(T), fatigue curve or density; linear scaling is labeled analytical, not another FE solve | Matched-machine/recipe coupons, surface/orientation/hot properties and defect basis |
| LPBF | Compare rigid orientations and retained support proxies; add elastic eigenstrain/support-release sensitivities only with explicit assumed strain | Closed geometry; build envelope with allowances; layer/island/support diagnostics; full-field distortion/residual stress and support release; zero-strain control and linear scaling check | Supplier support/scan paths, temperature-dependent elastic-plastic card, calibrated eigenstrain or thermal process model, plate/release sequence and recoater criterion |
| OpenUSD | Link geometry, conditions and actual receipts using meters, +Z and explicit unvalidated metadata | Resolved assets, units/axes/material and result links; available USD validators | GPU/RTX runtime for that workflow and correlated physical state for a validated digital twin |

The 5% mesh target is a proposed numerical screening criterion, not an approved
hardware acceptance tolerance. Yield margins against published coupon values
are comparisons only. Fatigue life, safe speed and manufacturing authorization
remain null/false until their inputs and engineering review exist.

## Process scenarios and resources

The inherited [ZRapid card](../zrapid-print-process.json) identifies
iSLM420DN / AlSi10Mg, DOI `10.1016/j.mtcomm.2026.115712`: 500 W, 1300 mm/s,
0.10 mm hatch, 0.04 mm layer, 0.08 mm spot and 303.15 K plate. One active laser,
absorptivity, supports, orientation and recoating timing are project assumptions.
This is a research recipe, **not a confirmed supplier production process**.
EOS and CP1 coupon properties are never substituted into its material card.

Kali2: one heavy job at a time, at most four CPUs and 6 GiB; existing native
CalculiX 2.23, container CalculiX 2.17 and pinned OpenFOAM Foundation 13 are
available. Local diagnostics use existing Python packages and bounded thread
counts. Check load before each heavy job because Qwen work shares the machines.
No security changes, image pulls, persistent service changes or new rentals.

## Data that actually blocks completion

1. **Scale and interfaces:** export unit, calibrated outside/bore dimensions
   with uncertainty, exact specimen and target part reference; shaft, seats,
   mounting faces, retention, clearances and drive direction/ratio. Without
   these, geometry deviations cannot be expressed against the real part and
   contact/support/clearance models cannot be accepted.
2. **Operating and aerodynamic evidence:** actual impeller speeds, inlet state,
   temperature, pressure–flow–torque map and installation resistance. Without
   these, exploratory CFD cannot validate engine cooling or aerodynamic loads.
3. **Material/process:** exact machine/recipe/lot/treatment/orientation, hot
   constitutive and fatigue data, supports and distortion calibration. Without
   these, an assumed-strain model quantifies sensitivity, not build prediction.
4. **Qualification:** approved balance, NDT and guarded spin/test plan plus
   professional review. This blocks metal manufacture and hardware release.

Proceed with independent numerical work while those inputs remain open. Report
every stage separately; successful code tests or USD export do not clear a
geometry, physics, manufacturing or hardware gate.

## Additional geometry hypothesis before its run

The strict 0.1 mm regularization did not clear the extended fluid-mesh gate.
The next original design revision, **Organic E-R1**, intentionally changes the
analysis surface. It is not accepted as a repair of E under that earlier bound.
Before generating it, set five isotropic remeshing iterations, 1.5 mm target
edge and 0.1 mm local-operation bound; require maximum bidirectional sampled
deviation ≤0.25 mm (5% numerical sampling allowance), volume difference <0.2%,
unchanged Euler characteristic, closed oriented one-component topology and
zero independently reported intersections. This is an assumed design envelope,
not a measured part tolerance. Report its actual tip clearance to the same
assumed 124 mm radius duct. Apply the same unmodified standard and extended
OpenFOAM gates, followed by the same convergence criteria if those pass.
Never transfer E's structure/modal results to E-R1 as its validation.
