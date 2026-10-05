# Unconverged pressure and next common objective

**Update:** the single trial prepared here was authorized and executed.
The [D1C result](D1C_EXECUTION.en.md) passes original numerical criteria but retains
backflow and physical limits. No additional batch was launched.

The cadence correction withdraws fine R0 admission and fine means presented
as twenty iterations. The [39 native tables](results/cfd/measurement-cadence-audit.json)
remain identical to their original hashes; historical helpers wrote only two
measurements per phase. Corrected code retains checkpoints at 150 and
measurements every iteration. The summarizer now rejects an incomplete or
misaligned window. Both common cases retain numerical admission.
This correction changes neither FEM results, contraction/unclamping cases
nor USD exports.

## Diagnosis of already computed data

The [reproducible report](results/cfd/pressure-followup-diagnostic.json) uses
native logs, fields 600/750/900 and the same fine V2 mesh.
[Input hashes](results/cfd/pressure-diagnostic-input-manifest.json) are
cross-checked against the verified private archive. No new solver is launched.

Over the last hundred V2 iterations at 900, the maximum initial pressure
residual is 1.5667×10⁻⁴; its mean is 9.9766×10⁻⁵ and relative standard deviation
16.2 %. Relaxation 0.15 did not remove the exceedance. Maximum final linear
residuals are approximately 1.11×10⁻⁶; the solver can stop at relative criterion
0.01 before reaching its absolute tolerance 10⁻⁸. Matched R0 reaches
6.0216×10⁻⁵ for maximum initial residual, but its flow/torque window remains
insufficient. The residual's temporal structure is that of steady iterations;
no physical frequency or rotational instability is established. The
[OpenFOAM normalization code](https://raw.githubusercontent.com/OpenFOAM/OpenFOAM-13/master/src/OpenFOAM/matrices/lduMatrix/lduMatrix/lduMatrixSolver.C)
justifies distinguishing a normalized algebraic residual from physical
pressure variation.

From 600 to 750, then 750 to 900, volume-weighted pressure change is respectively
0.283 and 0.566 Pa RMS. Local maxima reach approximately 209 and 187 Pa, near
the trailing edge and blade tip: radius 127–137 mm, z ≈ −16 mm, distance to
the nearest rotor-face centroid 0.5–2.5 mm. These distances are geometric
proxies; these cells are not identified as maximum algebraic-residual cells.
Both mesh checks pass; maximum non-orthogonality remains 71.09° and minimum
determinant 0.00515. Gross outlet backflow reaches approximately 10.8 % of net
flow, and variations are only 31–34 mm from the outlet, approximately 0.12 D.

These observations make local sensitivity of numerical coupling, wake and
outlet condition plausible. They do not yet distinguish conditioning,
boundary effect and unsteady flow. Priority is a short discrimination,
not an extension intended to cross a threshold.

## Objective fixed before the next calculations

The [prepared, unexecuted protocol](parameters/matched-cooling-objective-protocol.json)
retains R0 and only one V2 variant: root pitch 42° versus 36°, unchanged twist
−8°. V2 reduces nominal loading; the current common result exchanges −26.98 %
power for −7.14 % flow and −21.39 % total pressure. It demonstrates no better
installed cooling and selects no optimal pitch. No new geometry sweep is
planned before a comparison at a common hydraulic objective.

The hypothetical comparative objective is net Q = 1.00 m³/s, mean static
pressure rise at ports = 600 Pa, screening ceiling P = 3300 W. These are analyst
assumptions, not Porsche, measured thermal or normative requirements.
Resistance scenarios are static Δp = K Q² with K = 200 / 600 / 1000 Pa/(m³/s)².
They are explicitly bounded and hypothetical.

The common bench prescribes inlet Q with
[flowRateInletVelocity](https://cpp.openfoam.org/v13/classFoam_1_1flowRateInletVelocityFvPatchVectorField.html),
the same declared uniform profile for R0 and V2;
[fixedFluxPressure](https://cpp.openfoam.org/v13/classFoam_1_1fixedFluxPressureFvPatchScalarField.html)
adapts pressure gradient to prescribed flux. The outlet imposes zero gauge
static pressure and permits backflow. Planned samples are Q = 0.85 / 1.00 /
1.10 m³/s. Earlier imposed-inlet-total-pressure points are not added to this
new curve with a different profile. Mean static pressure, flux-weighted total
pressure, torque, P, backflow, Mach and energy balance remain separate
quantities. Resistance intersections are interpolated only between admitted
points; no extrapolation or qualified efficiency is announced.

## Batches proposed for coordination, none launched

| Batch | Calculations and stop | Resources per sequential case | Estimate / overall ceiling |
| --- | --- | --- | --- |
| D1 | Two 60-iteration branches from the same V2/900: pressure relTol 0.01 / 0, absolute tolerance 10⁻⁸ and physics unchanged; telemetry every iteration | 4 CPU, 5 GiB, external ceiling 300 s and solver 270 s | 4–6 min / 10 min |
| D2a | After diagnosis and a new window: R0 and V2 at Q = 1.00 on their common grids; at most two 150 phases per case | 4 CPU, 5 GiB, 300 s per phase | 8–12 min / 20 min |
| D2b | After D2a admission and a new window: four Q = 0.85 / 1.10 points for R0 and V2 | 4 CPU, 5 GiB, at most two 150 phases per case | 16–24 min / 40 min |

This table retains batches proposed before D1. The
[local analysis after D1](D1_NEXT_DIAGNOSTIC.en.md) now ranks coupling, outlet and
conditioning, proposing one `consistent yes` branch against the already
computed control. Outlet-length sensitivity remains a possible follow-up
with its own CAD and mesh gates. Every original threshold remains required,
with twenty consecutive measurements. None of these batches is launched
in the background. Kali2 windows must be coordinated with independent FEM work.
The [exact D1 configurations and prospective-window policy](D1_PREPARATION.en.md)
were prepared separately before launch. The
[current D1 result](D1_EXECUTION.en.md) retains the unadmitted control and strict
branch interrupted within budget. D2 batches are not launched.

Reproduce the lightweight diagnosis from private native inputs:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python source/diagnose_pressure_followup.py PRIVATE_NATIVE_INPUTS work/pressure-diagnostic.json --source-directory source
python source/audit_measurement_cadence.py . PRIVATE_NATIVE_TABLES work/measurement-cadence-audit.json
python source/compare_matched_flow.py . work/matched-grid-comparison.json
python source/verify_study.py
```
