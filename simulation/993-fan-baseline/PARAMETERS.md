# 993-FAN-BASELINE — Parameter Register (fan-zone actuator-disc deck)

Status legend:
- **FACT_public** — published in a cited source.
- **HYPOTHESIS_F0** — F0 synthetic design hypothesis, known to fail integration.
- **ASSUMPTION** — engineering assumption introduced to make the deck runnable; not evidence.
- **DERIVED** — computed from other rows.
- **UNKNOWN** — must be acquired (see ACQ-0005).

Every numeric input to the deck is generated from `parameters.json` by
`make_case.py`; nothing is hard-coded in the case directories.

## Physical / operating inputs

| ID | Symbol | Value | Unit | Tag | Source / note |
|---|---|---:|---|---|---|
| P-01 | Q_pub | 1010 | l/s | FACT_public | Published aggregate cooling flow @ 6100 rpm engine. `docs/research/m64-public-engine-data-2026-09-27.md` line 29 (Supplément OBD 1996). |
| P-02 | n_eng_A | 6100 | rpm | FACT_public | Engine speed paired with P-01. Same source. |
| P-03 | Q_pub_var | 1210 | l/s | FACT_public (variante à confirmer) | Second published value @ 5750 rpm. Same source, line 30; brochure variant, provenance weaker. |
| P-04 | n_eng_B | 5750 | rpm | FACT_public (variante à confirmer) | Paired with P-03. |
| P-05 | ratio_drive | 1.6 | – | FACT_public | Fan drive ratio ≈ 1:1.6 (crank→fan, over. fan faster). Same source, line 28. ASSUMPTION: ratio applied as fan speed = 1.6 × engine speed (direction of a step-up is assumed from the 1:1.6 notation). |
| P-06 | n_fan | 9760 / 9200 | rpm | DERIVED | n_fan = ratio_drive × n_eng (case A: 1.6×6100; case B: 1.6×5750). |
| P-07 | omega_fan | 1022.1 / 963.4 | rad/s | DERIVED | 2π n_fan/60. Used for tangential velocity only. |
| P-08 | rho_air | 1.204 | kg/m³ | ASSUMPTION | Dry air at 20 °C, 101 325 Pa. Real bay temperature 40–90 °C → −7 % to −20 % density; sensitivity deferred. |
| P-09 | mu_air | 1.82e-5 | Pa·s | ASSUMPTION | Air at 20 °C. |

## Geometry hypotheses (two cases)

| ID | Symbol | Case A (`caseA_published`) | Case B (`caseB_corrected`) | Unit | Tag | Source / note |
|---|---|---:|---:|---|---|---|
| G-01 | D_throat | 252 | 284 | mm | Case A: HYPOTHESIS_F0 / Case B: DERIVED | A = F0 housing throat as published. B = throat required for 2 mm radial clearance vs 280 mm impeller. `docs/993/993_ENGINE_COOLING_FAN_SYSTEM_F0.md` (origin/main): cold radial clearance −14 mm, "Throat required for 2 mm radial clearance = 284 mm". |
| G-02 | D_imp | 280 | 280 | mm | HYPOTHESIS_F0 | F0 impeller diameter hypothesis. Not measured. |
| G-03 | c_rad | −14.0 | +2.0 | mm | DERIVED | (D_throat − D_imp)/2. Case A is geometrically impossible (interference); documented, still run for comparison. |
| G-04 | hub_ratio | 0.357 | 0.357 | – | ASSUMPTION | Hub diameter = 100 mm (shaft + motor can envelope). No public hub data. |
| G-05 | D_hub | 100 | 100 | mm | ASSUMPTION | From G-04. |
| G-06 | t_disc | 20 | mm | ASSUMPTION | Actuator-disc axial thickness (numerical element only). |
| G-07 | L_up | 4·H | 4·H | mm | ASSUMPTION | Upstream development length, H = annulus hydraulic height. |
| G-08 | L_dn | 8·H | 8·H | mm | ASSUMPTION | Downstream length, for pressure recovery and outflow stability. |
| G-09 | n_blades | — | — | – | **UNKNOWN** | Blade count unknown → M64-ACQ-0005 (parallel lane deriving from fan-drive scan). Deliberately NOT modelled: the deck uses an actuator disc, no blade geometry, no invented count. |

## Actuator-disc surrogate model (labelled SURROGATE)

| ID | Symbol | Value | Unit | Tag | Source / note |
|---|---|---:|---|---|---|
| M-01 | model | fvOptions `momentumPenalty` (isotropic damping) + uniform `scalarCoded` pressure-gradient source over disc cells | – | ASSUMPTION | Simplest runnable surrogate in v2312 simpleFoam (no fanModel/actuatorDiscDisk library dependency). Momentum penalty represents blade blockage/tangential swirl proxy; pressure source represents the fan jump. |
| M-02 | Δp_fan | target 25.0 (caseA) / 20.0 (caseB), Pa | Pa | ASSUMPTION | Assumed fan static rise at duty point. No measured fan map exists (blocked by ACQ-0005). Result Δp is therefore an INPUT, not a prediction; the informative outputs are flow uniformity, blockage sensitivity, and deck operability. |
| M-03 | beta_disc | 60 (A) / 20 (B), 1/m | ASSUMPTION | Momentum-penalty magnitude, scaled ∝ 1/clearance area — stronger blockage in the interfering case A. Arbitrary but parameterised. |
| M-04 | BC | inlet: uniform axial velocity = Q_pub/A_ann(disc); outlet: zeroGradient p; walls: no-slip | – | ASSUMPTION | Displacement BCs from P-01/P-03. This makes flow rate prescribed, so the deck cannot validate the published flow; it tests the deck, not the fan. |

## Case A geometry failure note

Case A (throat 252 mm vs impeller 280 mm, clearance −14 mm) cannot exist as an
assembly: the impeller overlaps the housing throat. It is run only to show the
deck responds to area change (higher velocity, higher loss) and to keep the
documented F0 failure visible in the CFD lane. **Case B is the informative case.**

## Known deviations from reality (all cases)

1. Single annular duct ≈ radial-fan discharge plenum proxy; the real M64 fan
   feeds shrouded ducts to cylinders 1–3 / 4–6 with a central alternator/AC
   compressor blockage. No duct network exists yet.
2. Steady incompressible RANS (simpleFoam, k-ε). Mach ≈ 0.05 at disc, fine.
3. No rotation, no blade passage, no tip-clearance jet — blade count UNKNOWN (G-09).
4. Δp_fan is an assumption (M-02): absolute pressure/flow numbers are placeholders.
5. Isothermal 20 °C air (P-08): real bay hotter.
