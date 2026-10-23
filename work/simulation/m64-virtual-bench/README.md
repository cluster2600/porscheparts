# M64/60 Virtual Test Bench — 0D quasi-steady digital-twin consumer

Deterministic 0D model of the 3.6 L twin-turbo flat-six on a virtual dyno:
electricity, petrol, and air go in; torque/power, charge-air, cooling-air,
oil and electrical panels come out, compared against the public
408 PS / 540 Nm case. Status `exploratory_reference`: hypothesis-grade,
not a measurement, not a release.

Run: `python3 source/run_bench.py` (stdlib + numpy, byte-identical reruns).
Test: `python3 -m unittest discover -s tests`.
Missing inputs and exact acquisition asks: [`inputs-gap.md`](inputs-gap.md).
Generated results: [`results/`](results/) (`report.md` documents solver,
boundary conditions and convergence per repository simulation rules).

## Validation record (executed checks and honest deviations)

Executed 2026-09-29 on this worktree (`wave2/bench-20260929`):

- `python3 source/run_bench.py` — end-to-end run OK, wall time < 0.1 s,
  rerun byte-identical against committed `results/` (diff clean).
- `python3 -m unittest discover -s tests -v` — **8/8 OK** in 0.017 s
  (anchor exactness, heat-split closure, energy ordering, sweep grid
  completeness, part-load monotonicity, bounded deviations, inputs-gap
  register present, byte-identical determinism).
- Deviations at execution date (see `results/deviation_table.csv`):
  model peak power +1.06 % vs public 300 kW; model peak torque +2.93 %
  vs public 540 Nm (location is a prediction, not a calibrated row);
  boost plateau −19.95 % vs the 1.0 bar brochure setpoint (M64-ACQ-BENCH-08);
  both calibration anchors (300 kW @ 5750 rpm, 540 Nm @ 4050 rpm) and the
  1010 l/s fan flow are exact by construction, NOT blind verification.
- NON vérifiés / not verified by any of the above: torque-curve shape
  between anchors, transient behaviour, part-load BSFC (weakly-bounded,
  no pumping-loss model, M64-ACQ-BENCH-10), thermal split and effective
  fin flow (open contradiction in `results/report.md`), oil pressure,
  turbo shaft speeds, wheel-side power, and every ASSUMPTION-tagged input
  in `inputs-gap.md`.

**Evidence-coverage limit:** the bench remains a 0D model that is
untested and unvalidated against a physical test bench; the smoke tests
check internal consistency and determinism only, not physical accuracy.
Missing inputs stay listed in `inputs-gap.md` and are never invented.

Panels: `air_path` (VE + PR hypothesis, REPO 0.8 bar plateau), `charge_air`
(compressor/intercooler audit), `fuel` (energy balance, two-anchor BSFC
calibration), `cooling_air` (fan FACT_public anchor, heat split), `oil`
(flow demand vs assumed pump), `electrical` (starter/ignorption/injection
parasitics), `driveline` (crank→wheel), `dyno` (WOT + part-load sweeps,
deviation table), `thermal` (compatibility shim).
