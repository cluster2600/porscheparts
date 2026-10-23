# Virtual bench — inputs gap register

Every input the 0D bench needed but could not source from this repository
(or from the public survey `docs/research/m64-public-engine-data-2026-09-27.md`)
is listed here as an exact acquisition ask. IDs prefixed `M64-ACQ-BENCH-*`
are new; `M64-ACQ-000x` already exist in the twin acquisition contracts.

Nothing below blocks the bench from running; everything below blocks the
bench from being called a calibration. Status of the whole model:
`exploratory_reference`.

| ID | Needed for | Status today | Exact acquisition ask |
|---|---|---|---|
| M64-ACQ-BENCH-01b | rpm positions of the public anchors (peak power, peak torque) | ASSUMPTION 5750 / 4050 rpm; values 408 PS / 540 Nm are FACT_public but published without rpm positions in repo | Scan the 1995 993 Turbo brochure / 993 Technical Specification Booklet "Engine Specifications" page and photograph the power/torque diagram axes (owner: documentation lane). Record as a source card with page reference. |
| M64-ACQ-0003 (existing) | compressor PR/efficiency vs flow and speed — replaces the PR-vs-rpm hypothesis curve | HYPOTHESIS ramp to the documented 1.79 plateau | BorgWarner/KKK K16-2467GGA compressor map (left unit 5316-988-6736, right 5316-988-6735): request from BorgWarner application engineering or a teardown report; any licensed map scan acceptable. |
| M64-ACQ-BENCH-02 | oil pump flow/pressure curve, relief-valve cracking, supply pressure vs rpm | ASSUMPTION linear 60→250 L/min, 2.0 bar, eta 0.45 | 993 Turbo dry-sump pump flow-versus-pressure-and-speed curve + pressure-relief setting from the Porsche 993 Turbo repair manual (M-Kat logbook section "Oil pump") or pump OEM (Mahle) data sheet; photograph the manual pages. |
| M64-ACQ-BENCH-04 | heat-rejection split (cooling air / oil / exhaust / other) and fin-stack hA | ASSUMPTION set 0.30/0.10/0.55/0.05; 35 K fin rise anchor | Engine-instrumented dyno heat balance: intake/exhaust gas temperatures + flows, oil in/out temperatures and flow, cooled-air temperature rise at 2-3 duty points. Second-hand: a published M64 or 964 Turbo heat-balance study (e.g. Porsche engineering Christophorus article) — record exact citation. |
| M64-ACQ-BENCH-05 | fuel card: LHV, density, WOT AFR schedule, measured BSFC map | ASSUMPTION LHV 44 MJ/kg, AFR 12 WOT, generic BSFC shape | Any 993 Turbo DME log (AFR vs rpm/load at WOT, e.g. PIWIS/Porscan dump) plus one measured engine BSFC map from a comparable 3.6 L turbo flat-six dyno session; fuel spec sheet for RON98 properties. |
| M64-ACQ-BENCH-06 | fan flow slope vs rpm and effective fin-flow fraction | FACT_public single point 1010 l/s @ 6100 rpm; linear affinity HYPOTHESIS; 60 % effective fraction ASSUMPTION | Pitot/bellmouth fan flow measurements at 3 rpm points on one car (or the CFD slope from `simulation/993-fan-baseline` extended with a parametric disc-pressure sweep), plus shroud flow-bypass estimate (smoke test or pressure traverse in the fan box). |
| M64-ACQ-BENCH-07 | electrical loads: starter rating, ignition power vs rpm, injection pump power, DME supply current | ASSUMPTION constants only | Wiring diagram (993 Turbo, factory electrical manual) with component ratings: starter part number + nameplate, fuel pump flow/pressure/power spec (tank unit), DME main-fuse rating; optional: clamp-meter current trace at cranking and 3000 rpm. |
| M64-ACQ-BENCH-08 | boost: 0.8 bar effective vs 1.0 bar brochure setpoint, and overboost strategy | Kept as an open deviation row; model runs the 0.8 bar REPO-envelope plateau | Verify on the paper brochure and one boost-log trace (2-channel logger, WOT run) whether 1.0 bar is momentary setpoint and 0.8 bar sustained; record boost-vs-rpm trace. |
| M64-ACQ-BENCH-09 | driveline parasitics: gearbox mechanical losses, accessory drive (fan belt tension/pulley sizes, generator load) | ASSUMPTION grids; 1.6:1 fan ratio is FACT_public | Gearbox oil-temperature/efficiency data from the 993 Turbo gearbox manual, or a drivetrain-loss chassis-dyno run (unfired engine drag power vs rpm); pulley diameter measurements from the fan drive (also feeds ACQ-0005). |
| M64-ACQ-BENCH-10 | part-load law: VE and AFR vs throttle/boost, pumping losses | ASSUMPTION: throttled-density with fixed VE, stoich part load, WOT efficiency reused | DME load-characterisation: logged airflow (LMM) vs throttle and rpm at part load from any 993 Turbo, or a manifold-vacuum-based VE estimate from one dyno session; otherwise downgrade part-load rows to "sensitivity only". |
| M64-ACQ-0005 (existing) | fan blade count / pulley diameters (geometry, not flow) | UNKNOWN; flow anchor only | Physical count and pulley OD on any 993 Turbo fan drive (photo + caliper), or complete the `Fan+Drive+0.21mm.obj` scan study in `work/obj-intake-20260927/`. |
| M64-ACQ-BENCH-11 | intercooler effectiveness / charge-temp rise (+20 K plateau constant) | Documented constant from the REPO dyno envelope; no measured IAT data | Logged intake-air-temperature vs underhood air temp on a 993 Turbo at cruise and WOT (IAT sensor reading is stock), or OEM intercooler effectiveness curve if a supplier doc surfaces. |

## Rules applied

- No ASSUMPTION value may be promoted to a catalogue/twin record
  (ADR-0004 promotion rule); this directory is a simulation lane output
  (`exploratory_reference`), not released data.
- The bench must re-run byte-identically after each input upgrade; the
  deviation table (`results/deviation_table.csv`) is the regression diff.
