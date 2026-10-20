# RICH2 END181: component checks pass, aggregate balance fails

The saved one-state calculation reproduces the RICH2 reaction imbalance using an independent Q1/Hooke/weak-form assembly. **All reported scalar checks meet their unchanged limits, while twelve aggregate force/moment checks fail.** The original full mechanical assessment remains refused. This is a synthetic software-coupon diagnostic, with no head strength or LPBF process qualification.

The [complete diagnostic](diagnostic.json) retains all 1,275 native-versus-assembled force components,425 coordinate-word associations,256 ordered HEX8 cells,225 own birth-reference rows, masks and complete resultants. The [independent saved-result review](review/independent-result-review.json), [full bindings](review/independent-result-bindings.json) and [root acceptance](review/root-acceptance.json) retain their separate scopes. All 4,060 independent checks pass for the available saved arrays; the twelve aggregate failures remain. [manifest.json](manifest.json) accounts for every included original and the disclosed source projection.

## What this distinguishes

Own RICH2 BEGIN80 supplies displacement/temperature references for all 225 born nodes, including 25 shared nodes. The selected own END181 geometry association is time 0.4525, index 101. All 2,048 QPs are covered; regional old2 and born3 forces combine before 1,269 free-component checks. The original six constrained degrees of freedom and all seven SI limits remain unchanged.

| Constrained resultant | Native field | Independently assembled field | Original absolute limit |
|---|---:|---:|---:|
| X force, N | -2.29850465416348e-6 | -2.299629159097094e-6 | 1e-7 |
| Y moment, N m | -9.236246114596725e-7 | -9.233190212398767e-7 | 1e-7 |
| Z moment, N m | 1.0408839443698525e-6 | 1.0406802175566554e-6 | 1e-7 |

The corresponding free-row resultants also fail, in both fields. The all-node sums pass through cancellation. Individual free components meet 1e-7 N; a per-component limit does not supply a budget for their sum. Native-versus-assembled agreement therefore does not establish physical equilibrium.

Reported scalar comparison counts are 650 temperature,606 displacement,12,288 stress,49,152 strain and3,894 force, with zero scalar exceedances. Full QP tensor/regional-force operand arrays and the omitted temperature/displacement arrays were not added by this binding-only diagnostic: these assembly/comparison results remain owner/source-attributed. Independent saved reconstruction covers the complete force-component arrays, masks, associations and resultant arithmetic that are actually retained. Single-state energy is not a release-energy or final-hold assessment.

## Execution and evidence limits

One saved-only invocation returned0 in0.83044seconds, with no stop, signal or error, and the owned group absent after wait/reap. All 317 protected input identities, direct controls, selected Python, launch and prepared-body identities were unchanged. Resource limits sampled direct-child RSS/output with 60 seconds, TERM 8 seconds,2GiB/32MiB and one thread. These are sampled controls, not hard quotas, continuous/descendant peak coverage or complete ABI/OS closure.

The separate private closure is `81b1fb0c819677a869ef674e70db3e044cd2c00a4fa4574629603905770c69bb` (274,169bytes). The diagnostic is `b3614f3d383583549a9e5eb12e47ca8135ed35d2eee611e324fc38f072516255` (762,717bytes). RC0 means this finite diagnostic completed, while its aggregate gates still fail.

The editable source and held contract in `source/` are review evidence. The public worker replaces exactly one private repository-root Path literal with a placeholder; the manifest records original and projected identities. Other included original bodies remain byte-exact. Original external authorization and runtime/input paths remain a separate private execution chain, so this is not a standalone runnable solver release. No raw CSV/CDF, runtime, third-party source or proprietary drawing is redistributed.

The result targets a separately measured physical residual as the next solver question. It does not justify arbitrary extra inner iterations or establish a callback cause, roundoff floor or feasible native correction. The unchanged full 183-step own-reference/storage/seven-SI assessment, release energy and final hold remain required. Head mesh admission, strength, hot-material laws, LPBF calibration, accepted Omniverse fields, PhysicsNeMo labels and manufacturing release remain open. See the [original RICH2 refusal](../cp1-oneway-cooling-release-richardson2-refusal/README.md).
