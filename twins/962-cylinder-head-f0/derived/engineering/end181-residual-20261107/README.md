# Saved END181 residual and correction diagnostic

Issue [#446](https://github.com/cluster2600/porscheparts/issues/446) requires
inspection of the captured residual/correction vectors before another numerical
experiment. This offline diagnostic reads the retained two- and three-update
captures; it does not rerun the solver or change a limit. The original
[three-update trial](../rich3-coupon-and-head499-held/README.md) remains rejected:
**12 of 36 equilibrium aggregates still fail.**

## What the saved bytes establish

| END181 quantity | Two updates | Three updates |
|---|---:|---:|
| Reassembled F1 L2 norm | 1.84984e-7 | 1.80267e-7 |
| Largest free-row absolute residual | 3.15213e-8 | 4.69772e-8 |
| Sum of free x residuals | 2.29859670e-6 | 2.25325983e-6 |
| Constrained x nodal force | -2.29850465e-6 | -2.25298967e-6 |

All 1,269 free-row F1 values equal the corresponding saved nodal-force values
exactly in both captures. The six constrained F1 rows are zero while their
nodal reactions are nonzero: the boundary-condition residual is not a support
reaction. Individually small residuals can accumulate into the failed global
force and moment checks. No tolerance is widened or divided by node count.

All 1,275 X1 displacement words match the current CSV, and `X0 - Y1 == X1`
holds in binary64 for every component. Each complete X/F/Y stream has 364
objects, bound to the complete native monitor trace; END181 uses ordinals 360
and 361. The retained parser checks framing and EOF. Node coordinates are
compared to the current CSV, including its 25 identical duplicate rows.

The three-update native log reports a last **linear** residual norm of
9.882764403438e-8 and `CONVERGED_ITS`. Its separately reassembled **nonlinear**
F1 norm is 1.802667365503e-7. These describe different residual evaluations.
An extra linear update did not clear the equilibrium failure.

The already-recorded END182 hold at 300 K has much smaller native resultants:
all six force/moment components in each of the free and constrained groups
have magnitude below 7e-10 in both captures. These sums use exact rational
arithmetic on the decoded binary64 CSV values. This checks twelve native
aggregates per capture, **not** the full 36-aggregate mechanical assessment or
the complete history. END182 does not retroactively admit END181.

## Reproduction and scope

Run the [diagnostic](../../../source/physics_witness/inspect_end181_vectors.py)
against the private `work/962-engineering` directory, with a fresh output path:

```sh
python3 -B twins/962-cylinder-head-f0/source/physics_witness/inspect_end181_vectors.py \
  /private/path/work/962-engineering /private/path/new-diagnostic.json
```

The [summary](summary.json) binds both native receipts, selected artifact hashes,
parser, script, Python version, complete private report and derived results.
Every consumed scientific artifact must match its native receipt. Raw vectors,
CSV files and the full native console remain private. The earlier six-file
three-update scientific intake was also checked against its published pins.
Synthetic tests check the force/moment projection and exact cancellation sum.

The next justified investigation is the nonlinear reassembly/stopping behavior
at support release, including the arithmetic of the residual evaluation.
This evidence does not establish a root cause or prove that another nonlinear
iteration would satisfy the complete trajectory. No further solver experiment
has run, and independent review remains outstanding.

Affected phase IDs are `lpbf_build` and `lpbf_release`, diagnostic only. The
[mandatory workflow](../../../WORKFLOW.md),
[instructions](../../../AGENTS.md) and
[nineteen-phase contract](../../../workflow-contract.json) apply. All nineteen
engineering phases remain unpromoted by this work; see the existing
[phase ledger](../../phase-ledger-20261106/README.md) for their distinct historical
states and concrete blockers. Head geometry, material/process calibration,
strength, physical correlation and manufacturing acceptance remain blocked.
