# Observer004 native measurement: refused stopped capture

The instrumented native run exits **0**, but the caller exits **1** and the outer
owner exits **2**. The capture is **refused**. The owner records
`resource_or_group_observation_failed` with `PermissionError: [Errno 1] Operation
not permitted`. That original catch records neither the attempted operation nor
its traceback, so the exact operation and cause remain unknown. Subsequent
successful absence queries do not erase the failure.

The owner sends SIGTERM to its adapter group. The caller records that request
at 50.599017333006486 seconds, preserves stopped outputs, then refuses its
post-receipt closure gate. Its null local stop reason does not override the
request, error and nonzero exit. Inspect the [full owner closure](execution/closed-result.json),
[adapter traceback](execution/adapter.stderr.log),
[native caller receipt](native/native-execution.json),
[complete combined native stdout/stderr](native/native.log),
[independent saved-result review](result-peer/review.json) and
[separate root decision](root/result-peer-acceptance.json).
The root decision accepts refusal accounting only.

The [editable caller](source/run_native_capture.py),
[owner](source/run_root_once.py), [source method](source/METHOD.md),
[held actual](control/actual-contract.json),
[exact-child source review](control-peer/review.json),
[separate source decision](root/root-source-review.json),
[staging record](execution/staging-receipt.json),
[fresh preflight](execution/fresh-preflight.json) and
[one-run authorization](execution/authorization.json) preserve the protocol.
The [first metadata-preflight refusal](root/fresh-preflight-attempt-001-refusal.json)
is retained separately. Historical held/unrun labels describe the source
preparation checkpoint; later stopped receipts record this invocation. Fixed
workspace paths in copied sources are provenance, not replay instructions.

Saved before/after metadata match for all eight descriptor groups, including
197 inputs, 19 runtime files and 13 aliases, 89 host records and 22 provider
paths. The expected corrected plugin path is present in the native log. Owned
adapter/native groups are saved as waited on and absent. These are scoped saved
associations; no runtime body is republished or freshly revalidated here, and
full loader/ABI equivalence remains unproved.

Controls remain native 100 seconds, outer 115 seconds, TERM grace 10 seconds,
one thread, sampled RSS 2 GiB, inclusive output 512 MiB and positive per-file
growth 32 MiB. The full final census has 1,128 files totaling **433,263,540 bytes**;
positive growth is **11,599,196 bytes**, without offsetting shrinkage. The peer
reconstructs 87 outer RSS sample sums and 370 native samples, with maxima
250,003,456 and 219,398,144 bytes. Samples do not establish hard peaks. A saved
zero-RSS row with unknown process state remains uninterpreted. These limits
being met does not clear the observation error.

Saved caller/root elapsed values are 50.767864000052214 and 52.20251241698861
seconds; native text reports 47.20 seconds. Separately, root attributes a 71.951
second whole-owner observation and a conservative 73-second UTC bound at
one-second resolution, within the 115-second outer limit. Those scopes remain
distinct; tool wait time and native solver text are not complete-lifetime proof.
See the [complete saved accounting](result-peer/accounting.json).

The END181 map and three PETSc streams have saved presence/size evidence only.
Their bodies, all CSV/CDF/grid/mesh fields, runtime/plugin/object binaries and
third-party bodies are excluded. No vector/map decode, callback association,
global DOF validation, force/reaction result, measurement completeness or
physical qualification is accepted. All twelve original mechanical aggregate
failures and all 24 poor head cells remain. No solver, material, load, tolerance,
geometry or acceptance gate is relaxed; no retry or manufacturing is authorized.
The separate diagnostics source proposal is excluded.

[FILES.json](FILES.json) lists the complete capsule except itself. The 30 original
source/control/receipt/review files and four additive publication audit files
are byte-exact first-party UTF-8 copies, including historical workspace paths. New reader/index bytes provide navigation
only. The [preceding clean host check](../cp1-END181-observer-lifetime-host-check/README.md),
[original RICH2 refusal](../cp1-oneway-cooling-release-richardson2-refusal/README.md)
and [END181 equilibrium diagnostic](../cp1-richardson2-END181-equilibrium/README.md)
retain their separate scopes. The [publication review](publication-peer/review.json)
covers the initial snapshot; the [root publication decision](publication-root/reviewed-snapshot-acceptance.json)
records the final navigation and audit additions.
