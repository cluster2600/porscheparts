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

Panels: `air_path` (VE + PR hypothesis, REPO 0.8 bar plateau), `charge_air`
(compressor/intercooler audit), `fuel` (energy balance, two-anchor BSFC
calibration), `cooling_air` (fan FACT_public anchor, heat split), `oil`
(flow demand vs assumed pump), `electrical` (starter/ignorption/injection
parasitics), `driveline` (crank→wheel), `dyno` (WOT + part-load sweeps,
deviation table), `thermal` (compatibility shim).
