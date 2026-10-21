# T003: exact full-model definition set

**HELD / SOURCE ONLY / UNRUN.** This successor does not change T002 or its failed actual run. No Z3, transport, fixture, owner or runtime/API operation was executed during preparation. No head input, private owner receipt, scientific body, runtime/library body or PUB/Git file was accessed or changed.

## Small source correction

Only `one_model` and its two call expressions change. The function now receives the already declared `aliases` list, requires unique string names distinct from the target, and checks exactly one zero-argument target Real definition plus every exact declared zero-argument Bool alias. It rejects missing, duplicate, foreign, wrong-sort, nonzero-arity or malformed definitions; no extra model definition is ignored. Optional `(model ...)` framing remains supported. Definition order is immaterial.

The target body still goes directly to unchanged `protocol.model_value`. Bool alias bodies are retained as solver-owned model syntax; this is not a new independent Bool-body evaluator or proof of asserted formulas. Existing separate `get-value(alias)` Boolean-true checks, projection equality, retained-model continuity, same session, original predicates, exactly one check-sat and binary64 word criteria remain unchanged. The two original calls now pass their existing `aliases` list. All other transport source bytes remain exact.

`source.diff` is the complete narrow delta. The preparation reconstructed the whole predecessor byte-for-byte by reversing the function replacement and two call arguments. `run_fixed_toys` AST equals T002 after removing only those two added arguments; the other eight top-level function/class definitions remain text exact. The protocol file is unchanged. No new owner, controller, actual contract, launch, admission or selected-runtime arrangement is supplied.

## Offline fixture source — not run

`test_one_model.py` contains nine unittest methods: three positive schema cases and six rejection families with two variants each (15 concrete model inputs). Positives cover the exact captured rational model, existing optional model framing/reordered definitions, and two declared Bool aliases. Rejections cover extra, missing, duplicate, foreign-name, wrong-sort and nonzero-arity definitions on both target/alias sides. The two-alias case is synthetic parser schema coverage; it is not an executed algebraic solver case.

A future separately authorized fixture call would SHA-verify the complete T003 and frozen protocol bytes, compile those exact buffers into separate ordinary module namespaces, and call the actual T003 `one_model`. It uses no importlib/pyc route and no reimplemented acceptance predicate. Source compilation/execution appears only as future fixture code and was not invoked in preparation. Only parser functions are called by the fixture; no `Session`, `run_fixed_toys`, owner, subprocess or Z3 call occurs in that future fixture path. No current runtime is selected or probed here. Malformed externally supplied expected-alias metadata is statically refused by the new source, but is not a separately counted fixture family.

The embedded captured model is byte-for-byte the model response in `work/962-engineering/head-star-current24-qfnra-five-toy-root-execution-001/toys/toy_rational.jsonl`, SHA-256 `346902cb695ff2c083a7d3c4ff68755865134980294b64bc88cdff7ab73537d1`, 2,024 B. Its companion raw synthetic stdout is SHA-256 `3125823d7a9027b00348a149295cb7437c8cf104bba645c9b3f9f2aa95a73ed4`, 302 B. Those were the only actual-run captures read; the full private owner receipt was excluded.

## Limits and next gate

The author previously authored material/reference and native005 fake fixtures, and reviewed owner004/core13/readiness/concrete controls and the failed actual result. This is source authorship, not independent review. Independent source review and a separately admitted bounded offline fixture call remain required. A later full toy operation needs its own exact T003 owner/control integration and admission; existing owner004 still pins T002.

The rational model-shape failure is addressed at source level only. The preserved actual run remains failed/incomplete, four cases remain unattempted, and owner process-group TERM/KILL EPERM errors remain unresolved. This parser correction neither fixes nor requalifies cleanup. No physical, material, head-strength, mesh-repair, LPBF or manufacturing qualification follows. The 24 poor head cells and 12 aggregate mechanical failures remain open.
