# Next controlled convergence experiment

The smallest useful next native experiment is one additional Richardson correction: change only the value for `-ksp_max_it` from 2 to 3 in a fresh copy of the captured deck. Preserve the frozen deck, all physics/material/time/mesh settings, LU preconditioning, scale 1, unpreconditioned norm, `ksp_convergence_test=skip`, observers, native resource limits and every acceptance threshold. Do not change `nl_rel_tol` or `nl_abs_tol`: the captured LINEAR/ksponly route leaves those nonlinear tests inactive.

The saved QP audit contains 6 variants (computed/stored-QP stress × A/B/C). Each still fails 6 of 18 derived aggregate checks, totalling 36 of 108; the prior 12 failures among 36 original diagnostic aggregates remain unchanged. The native 12-check subset still has three failures. Its three constrained native witnesses exceed the original 1e-7 gate by 9.24–22.99×. Maximum absolute corrections over the two stress channels are:

| Native constrained criterion | Native value | max abs(A−B) | max abs(B−C) | max abs(A−C) |
|---|---:|---:|---:|---:|
| Fx (node0/x) | −2.298504654e−6 | 8.527e−14 | 1.481e−13 | 1.274e−13 |
| My (−node32/z) | −9.236246115e−7 | 2.296e−11 | 4.560e−12 | 2.221e−11 |
| Mz (node32/y) | 1.040883944e−6 | 2.797e−11 | 6.049e−12 | 3.402e−11 |

A−B removes only nodal/regional addition rounding; B−C additionally removes product/dot/weight rounding of the same frozen operand words. The largest witness A−C correction is 0.0341% of the gate, and the largest over all 1,275 components is 2.327327021e−10 (0.233% of the gate). These tested arithmetic transformations therefore do not remove the observed failures. This is not a bound on all native/constitutive/assembly arithmetic and does not establish a solver cause. The independent operand review/root decision remains separate.

The exact source change is one token on line 590 of the pinned 15,537-byte `thermoelastic-birth-observer-registration.i`:

```diff
-  petsc_options_value = 'richardson lu always 1 false unpreconditioned skip 2 binary:physical-X.petsc::append binary:physical-F.petsc::append binary:physical-Y.petsc::append'
+  petsc_options_value = 'richardson lu always 1 false unpreconditioned skip 3 binary:physical-X.petsc::append binary:physical-F.petsc::append binary:physical-Y.petsc::append'
```

The captured actual contract independently records exactly 2 Richardson updates and explicitly labels it count completion. Three is the minimal additional correction; the physical tolerance stays fixed. Update the fresh solver-profile/input hashes and ordinary exact staging/admission bindings; reuse the reviewed native route. This document creates no changed deck, operational paths, authority or run.

After one separately authorized bounded capture, reuse the existing END181 calculation with fresh same-run bindings. Compare all 1,275 component observations, original 36 aggregates/native 12-check subset, the constrained Fx/My/Mz and opposing free/all sums; retain all failures at 1e-7. Preserve the complete KSP true-residual sequence, actual three-update count, reason and final physical callback. Linear residuals and physical/CSV force criteria remain distinct; no F1 SI-force/unscaling inference is added. A reduction is evidence of iteration sensitivity, not a unique cause or complete convergence proof. If unchanged or worse, retain it and inspect that specific final update/residual evidence before any further authorized change; do not start a count/tolerance sweep.

Native all-row balance and cancellation between free and constrained sums do not close the failed constrained criteria. Material assumptions/calibration, full trajectory/mechanical assessment, strength, head-mesh qualification and manufacturing remain open. No scientific raw input, runtime body, solver or target program was accessed/executed for this proposal. The author also produced the arithmetic and prior END181 sources; the present work is saved-report interpretation rather than independent scientific acceptance. Exact descriptors and finite numeric summaries are in `proposal.json`.
