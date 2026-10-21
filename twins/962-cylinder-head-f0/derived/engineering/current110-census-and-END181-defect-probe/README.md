# Current110 head census and END181 defect probe

This checkpoint advances two software investigations in the assumed 962 C head family through 4.0 L. Missing OEM interfaces and production operating data remain open.

## Actual head

The [saved census](head/native/readback-report.json) freshly matches the combined mesh: 1,097,268 nodes and 3,622,025 TET4 cells. The unchanged whole-head SICN 0.1 gate still fails: 110 positive-poor cells remain, minimum 0.039074265058645995. This read-only run changes no geometry.

All 110 poor cells touch 82 movable interior nodes. Their complete recorded neighbourhood contains 2,482 cells: 110 poor and 2,372 initially good, including 58 shared by multiple movable nodes. No poor row is unseedable. The [independent review](head/reviews/result/review.json) checks selected associations and six typed hashes. Global arrays and absence of omitted outside cells remain reviewed-source/native-execution evidence.

The [coupling graph](head/coupling/coupling-graph.json) has 73 components: 64 singletons and nine pairs. The largest has two movable nodes, six coordinates and 77 cells. One fixed context node is shared between two components. The [root review](head/coupling/root-review.json) reconstructs the graph from saved rows. These are local cell-quality dependencies with other coordinates fixed; no repair feasibility or global embedding is proven. The frozen pending-census label predates the later census acceptance.

## Synthetic coupon

The [derived END181 probe](coupon/results/diagnostic.json) constructs the consistent Q1 tangent and performs one 1,269-free-DOF solve on the same synthetic 2 by 1 by 1 metre coupon. Original temperature, birth references, supports and saved native fields stay fixed. Maximum requested correction is 1.0040208483470068e-15 m.

Derived force and moment resultants meet the original 1e-7 N and 1e-7 Nm limits; largest magnitudes are 5.872191621847378e-10 N and 4.4943992971724356e-10 Nm. All 23 force-comparison exceedances remain: 18 regional and five global nodal. Native and original assembled resultants still fail. No corrected state, original trajectory, convergence, numerical cause or roundoff floor is accepted.

The [saved-arithmetic review](coupon/reviews/result/review.json) checks all 1,275 component rows, 1,269 defect associations, 27 resultant rows and complete 2,048 tensor associations. Missing prior full tensor rows, unsaved regional comparisons and unreplayed matrix/solve operations are explicit limits. The [authorship companion](coupon/sources/AUTHORSHIP-CLARIFICATION-001.json) corrects three attribution statements while preserving the five original frozen files.

The earlier [LINEAR refusal](../cp1-oneway-cooling-release-linear-refusal/README.md) and [balance diagnostics](../cp1-cooling-release-balance-diagnostics/README.md) remain immutable. This probe does not replace their rejected native result.

## Scope and next work

The [selection manifest](selection-manifest.json) accounts for all complete selected first-party bodies. Fixed private path prefixes become role URIs. Numeric values/types, binary64 words, process IDs, arrays, ordering, failures and historical authority flags are preserved. Original digests still refer to original bodies. Projected sources are readable records, not directly runnable reproduction packages.

Raw head MSH/BIN, native coupon CSV/CDF families, runtime packages/binaries, third-party source bodies and transitive ancestors are excluded; recorded identities remain. No new raw mesh download is implied.

Next are coordinate-quality repair candidates preserving every affected good/shared cell, matched hot properties and head strength, then calibrated LPBF, Omniverse mapped fields and PhysicsNeMo datasets/evaluation. Fitment, strength, material/process qualification and manufacturing release remain open.

Run python3 verify.py to check sealed payload bytes and exact file closure. The verifier performs no scientific calculation.
