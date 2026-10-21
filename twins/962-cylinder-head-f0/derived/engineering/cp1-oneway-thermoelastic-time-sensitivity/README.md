# Matched-time sensitivity of the assumed thermoelastic coupon

The saved coarse and fine coupon results were compared once at **81 prescribed END pairs**: coarse step k against fine step 2k, with nominal decimal time k × 0.005 s. The fixed maps agree exactly: **425 nodes, 256 ordered HEX8 cells and 2,048 observed quadrature points**. The diagnostic scans **3,854,107 selected END scalar pairs**, then retains counts, maxima and witnesses by time, region and field. It also retains all **225 own-birth reference pairs**, including 25 shared nodes and five fields per node.

This is a sensitivity diagnostic for one synthetic case. It has **no cross-level pass threshold or convergence order**. It does not establish mechanical time/space convergence, material strength, a qualified LPBF process or head qualification.

## Observed differences

| Largest absolute difference across the stated regime | Before birth: 40 END pairs | From birth onward: 41 END pairs |
|---|---:|---:|
| Temperature | 6.78089122629899e-8 K | 0.0013517376056029207 K |
| Displacement component | 5.89403393598607e-13 m | 3.4257051200052926e-9 m |
| Stress component | 0.03953169851327387 Pa | 1653.4683410748275 Pa |
| Saved elastic-energy diagnostic | 1.7571311117676108e-13 J | 0.0006887902033433611 J |

These maxima combine the declared node or material regions for each row; the [complete report](result/report.json) preserves all per-region, per-time and component counts and witnesses. Energy remains attributed to the accepted single-case assessor; no energy or FEM reintegration was performed.

The largest postbirth temperature, displacement and stress differences occur at coarse END40 / fine END80. Energy reaches its largest difference at END80 / END160. The born material uses **its own BEGIN40 or BEGIN80 displacement, temperature and reference temperature**, including the shared nodes. Differences after birth therefore include the two thermal histories and their captured birth references. They are not a pure mechanical integration error.

BEGIN CSVs have no explicit timestamp column. Their filenames, phase, nominal birth-step association and neighboring accepted END times remain distinct. Both saved binary64 END timestamps are retained, including their previously accepted accumulation differences; they are not forced equal. No shared duplicate row is averaged, reset to zero or relabeled.

## Review and execution

The [comparison source](sources/compare_saved.py), [method](sources/METHOD.md), [six source guards](sources/selfcheck.py), [source reuse record](sources/source-reuse.json) and [complete source delta](sources/source.diff) are available. Eight parsing/identity helpers are reused exactly from both accepted single-case assessors. The guards ran once before this diagnostic.

The [source review](reviews/source/review.json), [exact-child review](reviews/exact-child/review.json), [root authorization](root/execution/authorization.json), [root closure](root/execution/closed.json), [root saved-report check](root/execution/own-review.json), [independent stopped-result review](reviews/result/review.json) and [root acceptance](root/execution/result-peer-acceptance.json) retain their separate scopes and disclosed author/reviewer lineage. Root and the stopped peer check saved associations and reductions; the complete raw-field scan remains attributed to the reviewed source and its one execution.

The saved query finished at RC0 in **14.3473399579525 s**, without a root stop or signal. Its owned process group was observed absent and the leader was reaped. All 354 bound inputs, static child/control records and selected interpreter body remained unchanged. Sampled leader RSS reached 69,550,080 bytes across 29 observations; this is not a true peak or a hard OS quota. No native solve, CDF decode or FEM replay was launched.

The [frozen intent](contracts/actual-contract.json) and held preparation retain their historical false/null observations and authority fields. They were not rewritten to describe a later execution.

## Input closure, rights and limits

The [original-record ledger](original-records.json) joins every original input identity to a new selected body or the already published [fine](../cp1-oneway-thermoelastic-transfer/original-records.json) and [coarse](../cp1-oneway-thermoelastic-level1/original-records.json) ledgers. Those two capsules retain the exact selected CSV bodies in their archives. They supply 171 original roles each: 164 selected CSVs and seven source/metadata records per case. No raw field archive, runtime or head mesh is duplicated here.

Complete-field JSON and whole-text path projections are declared in the ledger. All integer, float, bool and null values, numeric PID/PGID identities, binary64 words, list order and negative results remain unchanged. The report itself is published byte for byte: SHA256 **6e85559d63a085d74e68890a24042ebecc295f8061e70c657bc1f6fceb30ee77**, 4,276,104 bytes. The existing verifier checks capsule byte closure, not physics.

The unchanged seven single-case SI limits are provenance only, never cross-level tolerances. Original native receipt `passed=false` fields remain preserved in their parent capsules. The assumed CP1-like E/nu/alpha and thermal properties are not a matched measured material card. No cooldown, support release or residual-stress qualification is inferred. This single fixed geometry/load/build case must not be split across independent PhysicsNeMo training and evaluation cases.

The [project license](LICENSE.project) remains view-only. Publication grants no reuse, manufacture, fitment or release rights. The [current head census](../current127-full-stars/README.md) still reports 127 poor tetrahedra and minimum SICN 0.039074265058645995; the separate 414 historical surface-face failures remain open. All engineering, physical, material, process and manufacturing qualification flags remain false.
