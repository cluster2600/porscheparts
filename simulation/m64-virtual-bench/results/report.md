# M64/60 Virtual Test Bench — 0D Quasi-Steady Report

Dataset `M64-VIRTUAL-BENCH-0001`, status `exploratory_reference`.
Hypothesis-grade simulation: nothing here is a measured, fitted, or
released part. Inputs and provenance tags: see every module docstring
and [`inputs-gap.md`](inputs-gap.md).

## Solver, boundary conditions, convergence

- **Solver:** closed-form 0D quasi-steady evaluation (stdlib + numpy).
  No iterative solver; the only numeric solve is a linear 2x2 system
  for the two-point efficiency calibration (`numpy.linalg.solve`).
- **Convergence:** N/A by construction. Determinism contract:
  byte-identical outputs on rerun (asserted in `tests/`).
- **Boundary conditions:** ambient 101 325 Pa / 303.15 K (ASSUMPTION);
  manifold plateau 181.3 kPa abs / 323.15 K (REPO
  `simulation/993-turbo-dyno/dyno-reference.json` airflow envelope);
  heat split 30 % cooling air / 10 % oil / 55 % exhaust / 5 % other
  (ASSUMPTION set, M64-ACQ-BENCH-04).
- **Upstream CFD inputs consumed:** fan-zone OpenFOAM deck
  `simulation/993-fan-baseline` (caseB_corrected: 200 iterations,
  final outer residual 3.6e-3, mass-flow match <0.01 % against the
  prescribed 1.457 kg/s target — used as an order-of-magnitude check
  only, its pressure rise is an input not a prediction); variants
  anchor 0.156 kg/s per turbo from `simulation/993-turbo-variants`.
- **Grid:** WOT sweep 1000–6800 rpm at 250 rpm plus both anchor
  speeds and the limiter (26 points, fixed).

## Dyno result vs public case (408 PS / 540 Nm)

| label | rpm | public | model | unit | rel. err. % | note |
|---|---|---|---|---|---|---|
| peak_power | 6250 | 300.0 | 303.2 | kW | +1.06 | model peak may sit off the calibrated rpm if the BSFC/VE shape tilts the curve |
| power_at_public_peak_rpm | 5750 | 300.0 | 300.0 | kW | +0.00 | calibrated anchor (model is exact by construction) |
| peak_torque | 4750 | 540.0 | 555.8 | Nm | +2.93 | model peak torque location is a prediction |
| torque_at_public_torque_rpm | 4050 | 540.0 | 540.0 | Nm | +0.00 | blind prediction (not used in calibration) |

Model peak power 303.2 kW @ 6250 rpm;
model peak torque 556 Nm @ 4750 rpm.
WOT fuel consumption at peak: 0.0281 kg/s (137 l/h at 740 kg/m3 assumed);
min BSFC on grid 288 g/kWh.

## Panel verdicts

- **Air:** AIR: charge flow closes the public 0.8 bar plateau with the VE shape inside the REPO 0.85-1.0 envelope near peak; per-turbo flow 0.169 kg/s sits within +-3% of the 0.156 kg/s REPO variants anchor at mid-high rpm; PR curve is an unverified map hypothesis (M64-ACQ-0003).
- **Fuel:** FUEL: energy balance at AFR 12 reproduces 300 kW at 5750 rpm exactly (calibration) and 556 Nm at 4050 rpm as a blind prediction; BSFC min 288 g/kWh is plausible for a turbocharged SI; fuel card missing (M64-ACQ-BENCH-05).
- **Oil / thermal:** OIL/THERMAL: oil flow demand 3 L/min at peak vs NO sourced pump curve (M64-ACQ-BENCH-02); fan-air 1.20 kg/s implies cooling-air dT 307 K at the assumed 372 kW air share - the fan is the thermal bottleneck until the split and hA are measured (M64-ACQ-BENCH-04).

## Known contradictions (flagged, not corrected)

- At peak power the cooling-air share (372 kW)
  over the model fan flow (1.20 kg/s) implies a
  free-stream dT of 307 K, far above the 35 K fin-stack
  anchor: the published 1010 l/s fan figure and a 30 % cooling-air
  split cannot both describe effective fin flow (M64-ACQ-BENCH-04/-06).
- Public brochure gives 408 PS / 540 Nm but the repo survey carries no
  rpm positions; 5750 / 4050 rpm are ASSUMPTIONs taken as anchors
  (M64-ACQ-BENCH-01b).
- Starter draw (4.5 kW) exceeds every other electrical load by an
  order of magnitude; battery/alternator sizing is out of scope here.

## Not proven by this bench

Torque-curve shape between anchors, transient behaviour, drive-cycle
fuel figures, turbo shaft speeds, oil pressure, metal temperatures,
fan static pressure, part release of any kind.
