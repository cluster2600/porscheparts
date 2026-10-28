# Native005 coupon: current END181 equilibrium

The fixed offline diagnostic completed once at raw exit **0**. It records **66,590 scalar comparisons with no exceedance**, while **12 of 36 aggregate force/moment checks still fail**. Three failures belong to the 12 native constrained/all-row criteria. Diagnostic completeness is accepted; equilibrium remains failed.

| Recorded scalar comparison | Count | Exceedances |
|---|---:|---:|
| Temperature | 650 | 0 |
| Displacement | 606 | 0 |
| Strain | 49,152 | 0 |
| Stress | 12,288 | 0 |
| Force reconstruction/residual | 3,894 | 0 |

| Failed native constrained criterion | Observed value | Unchanged absolute limit |
|---|---:|---:|
| Fx (N) | -2.29850465416348e-6 | 1e-7 |
| My (N m) | -9.236246114596725e-7 | 1e-7 |
| Mz (N m) | 1.0408839443698525e-6 | 1e-7 |

All six native all-row criteria pass. Free-row sums approximately cancel the constrained-row failures; this does not pass either failed partition. Each failed native constrained resultant reduces to a single component at the declared support positions, so downstream nodal summation cannot explain those three failures. The complete [1,024,623-byte report](originals/native005-END181-equilibrium-execution-001/diagnostic.json) retains all 1,275 native/assembled force-component comparisons, 36 aggregate criteria, failure values, coordinate/connectivity associations, birth references, maxima and CSV positions.

The [independent saved-result review](originals/native005-END181-equilibrium-result-peer-001/review.json) rebuilds all 1,275 differences, 18 maxima/witnesses and 36 resultants using exact rational/integer binary64 rounding. Root independently recomputed the component differences and resultants and accepted the [limited diagnostic scope](originals/native005-END181-equilibrium-root-result-review-001/review.json). Neither review independently reexecutes the full tensor comparison from raw QP data. All 12 aggregate failures remain preserved.

The [fixed source and manifest](originals/native005-END181-equilibrium-prep-001/input-manifest.json) bind six current inputs totaling 4,794,503 bytes. Existing assessor kernels, old/born reference handling and all seven POLICY limits are unchanged. Native CSV displacements, reactions and QP fields drive the calculation; Exodus supplies geometry, connectivity, blocks and time, with its averaged nodal fields kept separate. All 2,048 QP associations are validated by the calculation, but the report saves counts/maxima/exceedances rather than a full per-QP table. The frozen METHOD overstates QP retention; the [source peer](originals/native005-END181-equilibrium-source-peer-001/review.json) supplies the explicit correction. A [separate diff-proof clarification](originals/native005-END181-equilibrium-prep-001/DIFF-PROOF-CLARIFICATION.json) preserves and corrects the original index's proof-method implication.

The [root capture](originals/native005-END181-equilibrium-root-execution-001/result.json) records one selected Python 3.12.11 `-B -I` call, child exit 0, 0.622 seconds, deliberate wait/reap, complete 607-byte [stdout](originals/native005-END181-equilibrium-root-execution-001/stdout.log), empty [stderr](originals/native005-END181-equilibrium-root-execution-001/stderr.log), exact planned counts and stable named identities before/after. The parent-tool timer has a separate scope. The [operative census](originals/native005-END181-equilibrium-root-execution-001/census.json) closes 52 paths / 17,470,620 bytes, below 32 MiB; later saved-result/root reviews are separate. No hard quota, true peak, full ABI or benchmark claim follows.

This is a rate-independent synthetic coupon calculation with hypothetical E=71 GPa, nu=0.33 and alpha=1e-5. It does not select a production material. Expected support labels are not live BC measurements; F1 force unscaling, the frozen strict collector, whole-trajectory energy/release/hold, numerical convergence and process calibration remain open. The observer's dt/scaling instrument lineage is ancillary, not an invented nominal expectation or an argument to this field kernel.

Next, audit rounded per-QP force contributions to distinguish assembly product/accumulation error from upstream stress/solution effects, preserving every original force/moment limit. Improved solver convergence requires a separately controlled native trial. The **24 poor head cells and 12 aggregate mechanical failures remain unresolved**; head strength, calibrated LPBF, a physically correlated twin and PhysicsNeMo are incomplete.

[FILES.json](FILES.json) binds 27 byte-exact first-party originals. Raw six scientific input files, full native console, raw OS reports and installed runtime/library bodies are excluded; nested descriptors are not followed. Archived source is for review and AST checks, not execution during publication. Frozen HELD labels retain their freeze-time meaning. See the [averaging reconstruction](../native005-exodus-averaging/README.md), [material study](../material-prescribed-strain-sensitivity/README.md) and [engineering programme](../../../ENGINEERING_PROGRAM.md).
