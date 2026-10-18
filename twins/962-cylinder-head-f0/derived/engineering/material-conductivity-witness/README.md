# Measured-conductivity bar software witnesses

Two separate MOOSE steady-conduction cases, **Z and XY**, completed without retry.
Each passes **109/109 frozen final-field checks**. This is a synthetic material-law
software witness, with no head temperature, strength or process qualification.

The assumed insulated bar is **1 × 2 × 10 mm**, with 16 HEX8/Q1 cells, 68 temperature
nodes and 60 free temperature DOFs. Its end temperatures are 23 and 250 °C. Only
one axial scalar column is used per case; no tensor or head build orientation is
inferred. The solver uses NEWTON, SMP and PETSc preonly/LU, one rank/thread.

## Data and model

Willkomm et al., *Design and manufacturing of a cylinder head by laser powder
bed fusion*, IOP Conference Series: Materials Science and Engineering 1097 (2021)
012021, [DOI 10.1088/1757-899X/1097/1/012021](https://doi.org/10.1088/1757-899X/1097/1/012021),
Table 2, printed page 6, reports the separate LPBF AlSi10Mg conductivity columns.
The source article is CC BY 3.0. Its recorded treatment is heating to 240 °C over
one hour, holding six hours, oven-cooling to 100 °C and then air-cooling. Coupon
machine, scan recipe, layer thickness and plate preheat are not bound to Table 2.
The component's later manufacturing description is not transferred to the coupons.
This recipe is separate from CP1/HT1 and is not a selected head material.

At 23/150/200/250 °C, the measured means used here are Z
162.9/163.6/165.4/160.5 and XY 154.6/154.4/154.9/152.2 W/(m·K).
The inputs divide by 1,000 for W/(mm·K). **Piecewise-linear interpolation is a
numerical assumption**, not a published continuous law. Measurement scatter is
not a design allowable. This steady problem requires neither density nor heat
capacity. The prior literature capsule retains source and visual provenance;
no paper PDF or page image is redistributed here.

## Actual final results

| Retained quantity | Z | XY |
| --- | ---: | ---: |
| Passing checks | 109/109 | 109/109 |
| Native wall time (s) | 0.820003 | 0.716061 |
| Maximum nodal error / 227 K | 1.0103444429e-5 | 5.2670148702e-6 |
| Maximum nodal error (K) | 0.0022934819 | 0.0011956124 |
| Cold / hot outward power (W) | +7.4191596605 / −7.3884965598 | +7.0067556135 / −6.9884613438 |
| Exact continuum cold / hot power (W) | +7.42105 / −7.42105 | +7.0063 / −7.0063 |
| Worst raw end-power error vs continuum | 0.4386635346% | 0.2546087976% |
| Raw end-power imbalance / exact power | 0.4131908659% | 0.2611117100% |
| Weak consistent cell-power max relative deviation | 7.30080546e-15 | 2.78892770e-15 |

All final nodes and all reconstructed Q1 Gauss temperatures are within 23–250 °C.
The maximum native k-average discrepancy is 5.5511151231e-17 W/(mm·K) in each case.
The independent Decimal Kirchhoff reference integrates the declared k(T), then
inverts its monotone primitive at every actual node coordinate. The complete
[Z](assessments/Z.json) and [XY](assessments/XY.json) assessments retain every
comparison, cell record, tolerance and consumed-export hash.

The **1%** nodal/continuum-power/raw-imbalance criteria were frozen before native
execution and remain unchanged. Raw boundary powers use the finite-mesh Q1 end
gradients; independent direct Q1 integration agrees within 1e-9 W. Those boundary
values need not equal the almost constant weak consistent cell heat rates on
this one mesh. They are reported separately. The console tables precede FINAL
export and show zeros: the hash-bound, single-row FINAL CSVs are authoritative
for the assessed powers. The deprecation warning in both logs is preserved.

## Evidence and provenance

This capsule is a **selected public subset**, not the complete native launch or
readback bundle. The retained private capture has **77 files / 307,461 bytes**,
with equal remote-before, local and remote-after size/hash maps. The complete
relative-name inventory is included; private command vectors and user/host
runtime locations are omitted only through explicit field projections.
[original-records.json](original-records.json) identifies exact copies,
original hashes, every projection's preserved/omitted fields and added role fields.
All 29 frozen source pins, eight runtime hashes, both case input/artifact maps,
six final CSVs, two native logs and the complete numerical assessments remain
available as bytes or explicit original hash records. The captured code, test and
review copies are unchanged; initial held labels and the preserved failed launcher
mock test are historical, followed by the separately recorded corrected mock tests
and actual authorization. The private range/launch addendum superseded the original
protocol's blanket pre-run range-refusal proposal without changing the data,
geometry, reference or tolerances.

The original stopped execution summary keeps `material_witness_passed=false`
because the launcher performs no independent assessment. The later complete
assessments and actual peer review record the scoped software passes separately.
The two native receipts record return code 0, process reaping and unchanged inputs
and runtime. Per-case configured controls were 30 s timeout plus 5 s kill grace,
40 s controller wait, systemd RuntimeMax45 s, 2 GiB/no swap, CPUQuota200%, TasksMax128,
one rank/thread, read-only rootfs and network/PID isolation. No observed RSS or CPU
sample series was recorded; configured limits are not measured usage or peak claims.

Run the copied standard-library integrity check from this directory:

```sh
python3 -B verify.py
```

This checks only sealed bytes and complete capsule closure. It does not rerun a
solver or reconstruct the omitted private native invocation. The full production
assessor's receipt/contract orchestration requires the retained original bundle;
its exact source and numerical final-field evidence are included for inspection.

## Limits

Outside-knot function behavior and **all intermediate nonlinear/material
 evaluations remain unobserved**; final range checks do not establish universal
fatal range refusal or permit extrapolation. This is one 16-cell mesh, with no
mesh-convergence study, formal separate AD-derivative proof, tensor orientation,
head boundary conditions, elastic/strength law, material/process qualification,
LPBF calibration, physical correlation or manufacturing authorization.
