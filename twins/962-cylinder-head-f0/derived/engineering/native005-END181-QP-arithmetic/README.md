# END181: quadrature arithmetic does not clear equilibrium failures

The fixed offline audit completed once with raw return code **0**, explicit child reap and no timeout. It saved **2,048 quadrature operand records, 900 regional merge records and 1,275 force-component comparisons** in the [complete report](originals/native005-END181-QP-arithmetic-execution-001/report.json). All original **12 failures in 36 aggregate checks** remain unchanged. This is a synthetic coupon diagnostic, not head-strength or LPBF qualification.

Two stress channels remain separate: stress calculated from the captured displacement/temperature and birth references, and stored native quadrature stress. Native CSV nodal forces remain a third provenance. Each channel compares three arithmetic variants:

| Variant | Calculation |
|---|---|
| A | Original binary64 products, regional accumulation and regional merge. |
| B | Exact rational sum of the same already-rounded contribution words. |
| C | Exact rational products and sums of the same captured stress, gradient and weight words. |

All 1,275 computed-A force words reproduce the earlier diagnostic exactly. Both A channels match the frozen accumulation function. B and C remove specified arithmetic rounding only; they do not supply exact geometry, constitutive physics or native solver arithmetic. Exact force and moment sums retain the original binary64 `1e-7` limit through comparison. Signed-zero input words remain visible; rational zero has no sign.

**Every channel/variant still fails six of its 18 derived checks: 36 failures in 108 checks.** These derived checks are separate from the preserved original 36 criteria. At the three constrained support witnesses, the largest tested A−C force correction is about `3.40e-11 N`, compared with native residual magnitudes of approximately `9.24e-7` to `2.30e-6 N`. The tested product/accumulation corrections do not clear those failures. This comparison does not establish the native solver's cause.

The [independent saved-result review](originals/native005-END181-QP-arithmetic-result-peer-001/review.json) reproduces all 294,912 rounded products, 98,304 weighted contributions, merges, component rows, 80 witness records, resultants and derived checks using separate integer ties-even and rational arithmetic. It executes no target kernel or raw-input reconstruction. The [root disposition](originals/native005-END181-QP-arithmetic-root-result-review-001/review.json) accepts complete arithmetic reporting only. The reviewer's prior method-design and source-review contributions are disclosed.

The [source method](originals/native005-END181-QP-arithmetic-prep-001/METHOD.md), [independent source review](originals/native005-END181-QP-arithmetic-source-peer-001/review.json), [execution receipt](originals/native005-END181-QP-arithmetic-execution-001/execution-receipt.json) and [root result](originals/native005-END181-QP-arithmetic-root-execution-001/result.json) preserve the operation and its limits. Source-only labels in frozen preparation records describe their freeze time. Archived source was not executed for publication.

The direct child completed in the recorded parent interval of `1.817782667 s`, within its 20-second bound. Complete stdout and stderr, raw status, exact source/input/runtime identities before and after, and the [inclusive census](originals/native005-END181-QP-arithmetic-root-execution-001/census.json) are retained. That census covers **21 paths / 10,118,460 bytes**, including itself; later reviews and this publication are separate. No live RSS, full ABI or transitive runtime claim follows.

The [next controlled native experiment](originals/native005-END181-QP-arithmetic-next-experiment-001/NEXT_EXPERIMENT.md) changes only the Richardson update count from two to three in a fresh copy of the captured deck. Keep the count-based stopping rule, LU preconditioner, unit scale, physical inputs, observer and all original SI limits. Count completion remains distinct from residual accuracy. Preserve the previous result and assess the new complete fields independently before drawing a convergence conclusion. The frozen proposal's large numeric ratio summaries lost integer precision through JavaScript serialization; the additive [exact-ratio clarification](originals/native005-END181-QP-arithmetic-next-experiment-clarification-001/RATIO-CLARIFICATION.json) supplies decimal integer strings and source-row associations. Root verified all eight maxima against the full report. Approximate summary values are not exact-ratio evidence.

[FILES.json](FILES.json) binds the byte-exact first-party originals. Raw CSV inputs, installed runtime bodies and native console are excluded; nested descriptors are not followed. The **24 poor head cells**, missing measured interfaces and operating loads, material/process calibration and all downstream qualification remain open. Follow the [engineering programme](../../../ENGINEERING_PROGRAM.md).
