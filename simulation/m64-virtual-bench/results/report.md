# M64/60 Virtual Test Bench — 0D Quasi-Steady Report

Dataset `M64-VIRTUAL-BENCH-0002`, status `exploratory_reference`.
Hypothesis-grade simulation: nothing here is a measured, fitted,
tested, released, or manufacturing-ready part or engine. Inputs and
provenance tags: see every module docstring and
[`inputs-gap.md`](inputs-gap.md).

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
- **Grid:** WOT 1000–6800 rpm at 250 rpm plus both anchor speeds
  and the limiter (26 points); part-load overlay at
  throttle fractions [0.25, 0.5, 0.75] on a coarser rpm grid
  (59 rows incl. WOT). All fixed.

## Dyno result vs public case (408 PS / 540 Nm / 1.0 bar / 1010 l/s)

| label | rpm | thr | public | model | unit | rel. err. % | note |
|---|---|---|---|---|---|---|---|
| peak_power | 6250 | 1.00 | 300.0 | 303.2 | kW | +1.06 | model peak may sit off the calibrated rpm if the BSFC/VE shape tilts the curve |
| power_at_public_peak_rpm | 5750 | 1.00 | 300.0 | 300.0 | kW | +0.00 | calibrated anchor (model is exact by construction) |
| peak_torque | 4750 | 1.00 | 540.0 | 555.8 | Nm | +2.93 | model peak torque location is a prediction |
| torque_at_public_torque_rpm | 4050 | 1.00 | 540.0 | 540.0 | Nm | +0.00 | calibrated anchor (two-point calibration solve uses this anchor; exact by construction) |
| boost_plateau_vs_brochure | 5750 | 1.00 | 1.0 | 0.8 | bar_gauge | -19.95 | model keeps the 0.8 bar REPO-envelope plateau; brochure 1.0 bar setpoint is FACT_public (M64-ACQ-BENCH-08) |
| cooling_air_flow_at_6100 | 6100 | 1.00 | 1010.0 | 1010.0 | l/s | +0.00 | exact by construction of the fan anchor; effective fin flow 0.71 kg/s assumes a 60 % effective fraction (ASSUMPTION, M64-ACQ-BENCH-06) |

Model peak power 303.2 kW @ 6250 rpm;
model peak torque 556 Nm @ 4750 rpm.
WOT fuel consumption at peak: 0.0281 kg/s (137 l/h at 740 kg/m3 assumed);
min BSFC on WOT grid 288 g/kWh;
min BSFC on part-load grid 289 g/kWh at
4500 rpm / thr 0.25.

## Panel verdicts

- **Air / charge air:** AIR/CHARGE-AIR: charge flow closes the public 0.8 bar plateau with the VE shape inside the REPO 0.85-1.0 envelope near peak; per-turbo flow 0.169 kg/s sits within +-3% of the 0.156 kg/s REPO variants anchor at mid-high rpm; compressor duty 29 kW total at 388 K discharge with eta_ad=0.65 ASSUMPTION; implied intercooler effectiveness 0.76; PR curve is an unverified map hypothesis (M64-ACQ-0003).
- **Fuel:** FUEL: energy balance at AFR 12 reproduces 300 kW at 5750 rpm and 540 Nm at 4050 rpm exactly (both anchors enter the two-point calibration); model peak 556 Nm at 4750 rpm and curve shape between anchors are blind predictions; BSFC min 288 g/kWh (WOT grid) is plausible for a turbocharged SI; part-load min 289 g/kWh at 4500 rpm / thr 0.25 is a weakly-bounded estimate (no pumping-loss model); fuel card missing (M64-ACQ-BENCH-05/-10).
- **Cooling / oil:** COOLING/OIL: oil flow demand 14 L/min (film-floor-dominated) vs assumed pump 233 L/min — no sourced pump curve (M64-ACQ-BENCH-02); fan-air 1.20 kg/s (1035 l/s) implies effective-fin dT 511 K at the assumed 372 kW air share — the fan is the thermal bottleneck until the split and hA are measured (M64-ACQ-BENCH-04).
- **Driveline:** DRIVELINE: crank 303 kW at peak maps to 290 kW wheel-side under ASSUMPTION parasitics (accessory 4.0 kW + oil pump 0.1 kW + 13.0 kW total loss, eta_dl 0.96); gearbox data missing (M64-ACQ-BENCH-09).

## Known contradictions (flagged, not corrected)

- At peak power the cooling-air share (372 kW)
  over the model effective fin flow (0.72 kg/s)
  implies a free-stream dT of 511 K, far above
  the 35 K fin-stack anchor: the published 1010 l/s fan figure and
  a 30 % cooling-air split cannot both describe effective fin flow
  (M64-ACQ-BENCH-04/-06).
- Brochure boost setpoint is 1.0 bar gauge (FACT_public) but the
  model plateau is the 0.8 bar effective reading from the repo dyno
  envelope: 1.0 vs 0.8 bar kept as deviation
  M64-ACQ-BENCH-08, uncorrected.
- Public brochure gives 408 PS / 540 Nm but the repo survey carries no
  rpm positions; 5750 / 4050 rpm are ASSUMPTIONs taken as anchors
  (M64-ACQ-BENCH-01b).
- Starter draw (4.5 kW) exceeds every other running electrical load
  by an order of magnitude; battery/alternator sizing is out of scope.
- Part-load rows use a throttled-density law with unchanged VE and
  unchanged WOT efficiency calibration: the resulting BSFC is a
  weakly-bounded estimate, not a fuel-consumption prediction
  (M64-ACQ-BENCH-10).

## Not proven by this bench

Torque-curve shape between anchors, transient behaviour, drive-cycle
fuel figures, turbo shaft speeds, oil pressure, metal temperatures,
fan static pressure, wheel-side power validity (driveline constants
are ASSUMPTIONs), part release of any kind, dimensional correctness,
fitment, safety, or manufacturing readiness of any part.
