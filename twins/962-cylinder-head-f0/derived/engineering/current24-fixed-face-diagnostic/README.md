# Current24: exact fixed-face diagnostic

All **24** fixed triangles have a real single-apex SICN ceiling strictly above **0.1**. Neither the sharp test nor the earlier looser bound identifies an obstruction. The head still has **24 poor tetrahedra**: this diagnostic changes no coordinates or connectivity and proves no compatible repair.

The [complete report](fixed-face-report.json) retains all24 ordered cell/node associations, fixed-face coordinate words, exact reduced fractions and classifications. The [independent review](review/independent-result-review.json), [full arithmetic bindings](review/independent-result-bindings.json) and [root acceptance](review/root-acceptance.json) preserve their separate scopes. All seven original files are copied byte-for-byte; [manifest.json](manifest.json) records their original identities.

## What was calculated

The current saved context contains16 movable seeds,499 incident tetrahedra,475 initially good cells and33 shared cells, with271 coordinate rows. Each poor cell has three fixed source-boundary-tag vertices. Such a triangle need not be an exterior facet: explicit exterior and source-BIN membership remain unknown.

For the pinned ideal-reference inverse-Frobenius SICN metric, a fixed face with triangle quality q2 has an optimal real-apex ceiling `3*q2/(2+q2)`. A strict ceiling below0.1 is equivalent to `q2^2 < 4/841`. Equality is recorded separately. The [method](source/METHOD.md) gives the derivation. Exact rational arithmetic preserves the saved binary64 coordinates without rounding or tolerance changes.

| Complete classification | Count |
|---|---:|
| Strict sharp obstruction | 0 |
| Equality | 0 |
| Not obstructed by this necessary test | 24 |
| Earlier loose-bound obstruction | 0 |
| Distinct fixed triangles | 24 |

An independent implementation reconstructed every exact rational and flag using Gram invariants. Six synthetic fixtures passed before one saved diagnostic invocation. That invocation returned0 in0.07734seconds; all30 protected metadata identities and direct controls were unchanged. The output identity is `319b8184e10191088681bf085974f25a0a46115cbfa9e68dd439454fbccf1a77`. The separate private closure identity is `5e119fbafd27ead88584134a95bcc88f37083a79556504e540c442879956389c` (24,828bytes). Resource observations are sampled, with no hard quota or complete runtime/ABI closure claim.

## What remains open

A movable seed can belong to several poor cells and initially good neighbors. It must satisfy its complete incident star while preserving signed volumes, existing quality and coupled compatibility. A favorable individual face ceiling supplies no binary64 apex, joint feasibility or embedding proof. The whole-head minimum remains0.039074265058645995 and the0.1 gate remains failed. The86 previously accepted improvements are unchanged; see the [native partial application](../current24-partial-application/README.md).

The [editable diagnostic source](source/audit_current24_fixed_faces.py) and [held input contract](source/held-preparation.json) are review evidence. Their original work paths and external authorization guard remain intact. This capsule is not a standalone runnable solver package and grants no execution authority. The report includes the fixed-face coordinate words needed to independently reconstruct the finite face arithmetic; no raw mesh, scan, proprietary drawing, solver field or third-party runtime is redistributed.

Head strength, hot-material qualification, LPBF calibration, accepted Omniverse fields, PhysicsNeMo labels and manufacturing release remain open. No remeshing or surface change is inferred from this result.
