# Next repair method: exact coupled threshold feasibility

METHOD ASSESSMENT ONLY. No source implementation, geometry proposal, coefficients, solver query, test, runtime access, mesh edit or execution authority is created. The accepted current head retains24 poor tetrahedra. The19 empty prescribed segments and55/1033 failed fixed-word edge alternatives exclude only those finite families.

## One selected route and its actual degrees of freedom

Prepare exact polynomial feasibility for the16 admitted interior seeds, with every other coordinate word and the current connectivity fixed. The complete saved incidence already partitions these seeds into11 quality-coupling blocks: six singles and five pairs. The previous SLSQP calculation already moved each pair jointly; gathering them into a48-variable numerical solve adds no freedom. The distinct next operation is a hard SICN0.1 existence query over each complete3- or6-variable block, without a local objective, selected movement ray, coordinate radius, grid, restart or changed threshold.

| Component | Seed tags | Variables | Cells | Poor | Good | Shared |
|---|---|---:|---:|---:|---:|---:|
| 2 | 1393392 | 3 | 32 | 2 | 30 | 0 |
| 7 | 1436404, 1613783 | 6 | 55 | 3 | 52 | 5 |
| 8 | 1436405, 1613757 | 6 | 53 | 3 | 50 | 7 |
| 9 | 1436406, 1613784 | 6 | 49 | 3 | 46 | 7 |
| 10 | 1436407, 1613756 | 6 | 53 | 3 | 50 | 7 |
| 21 | 1459657, 1534323 | 6 | 77 | 3 | 74 | 7 |
| 28 | 1476316 | 3 | 46 | 2 | 44 | 0 |
| 30 | 1485102 | 3 | 52 | 2 | 50 | 0 |
| 31 | 1487573 | 3 | 22 | 1 | 21 | 0 |
| 39 | 1520064 | 3 | 32 | 1 | 31 | 0 |
| 45 | 1549537 | 3 | 28 | 1 | 27 | 0 |

These are saved manifest associations, not a new geometric census. The future intake must reconstruct the current partition from all499 incident cells and prove exactly this disjoint cell union, all16 seeds/48 variables,24 poor/475 good/33 shared memberships and all271 coordinate-word rows. There are255 fixed context nodes (179 source-boundary tags and76 other interior tags). All871731 source-boundary nodes remain fixed through the accepted complete-boundary identity; no omitted whole-head word is invented. The prior66 changed nodes,1983 affected cells and86 improved original poor cells are protected and disjoint from the new moving seeds/affected cells. A mismatch refuses intake before a solver call.

## Exact constraints, with every cell association retained

For original ordered cell e=(p0,p1,p2,p3), use exact dyadics for fixed words and real coordinate variables for its admitted seeds. Define

- D_e = det(p1-p0,p2-p0,p3-p0), in the original native orientation;
- S_e = sum over all six edges of squared edge length;
- T_e = sum over all four faces of squared cross-product norm, equivalently the face Gram determinant sum;
- P_e = 3600 D_e^2 - S_e T_e.

For the equilateral-reference inverse-Frobenius metric, Q_e^2=36D_e^2/(S_e T_e). Consequently the unchanged signed gate is D_e>0, S_e>0, T_e>0 and P_e>=0. The positive denominator predicates precede cross multiplication; D_e^2 alone never admits inverted cells. Nondegeneracy implies S,T positive, but retaining the explicit predicates makes that safeguard inspectable. With one moving vertex D has degree<=1 and T<=2, hence P<=4. With two moving vertices D<=2 and T<=4, hence P<=6. Each cell must confirm its one/two-seed incidence; no cell with unsupported variable scope is silently dropped. Closed P=0 equality stays eligible mathematically; strict D=0 stays refused.

Use only +,-,* and rational coefficients. Clear denominators by a recorded strictly positive common multiple to emit integer polynomial predicates; retain that scale and any primitive-factor normalization. No division by a variable, square root, floating coefficient, epsilon, transcendental, mixed integer or floating-point sort enters the feasibility query. Keep identically zero and constant polynomials with their original truth dispositions. A zero/false strict determinant cannot disappear in simplification.

Every polynomial/DAG retains componentID, tetrahedron tag, native array index, original ordered connectivity, moving-tag/axis variable map, all fixed binary64 words and the exact coefficient serialization/hash. The independent checker must reconstruct each expression from the original row and verify any normalized representation. Factorized exact expression DAGs avoid gratuitous dense expansion; they do not omit coefficient semantics or cell rows. Model projection retains all48 coordinate values and their mapping back to the complete271-word context. Internal solver CAD projection/lemma traces are solver-attributed; no independently checked projection proof is promised.

## Deterministic finite candidate generation

Use the standalone QF_NRA/NLSAT route, one query per saved component in increasing componentID, with real variables ordered by seed tag then x/y/z and constraints in original native-row order. Propose fixed randomize=false, shuffle_vars=false, reorder=false, seed=0 and exact algebraic zero_accuracy=0; exact accepted parameter names and semantics must be checked in future synthetic runtime guards. No changed setting or second attempt follows a refusal. There is no movement box: the query asks the full fixed-connectivity polynomial feasibility problem for that block. No starting local optimum is substituted for it.

Z3's [primary description](https://z3prover.github.io/papers/z3internals.html#nlsat-mc-sat) describes a polynomial real-arithmetic decision procedure using CAD within model search; the [original authors' paper](https://www.microsoft.com/en-us/research/publication/solving-non-linear-arithmetic/) supplies its algorithmic basis. These describe an unbounded mathematical fragment, not a bounded completion promise. Generic nonlinear/mixed/theory combinations are outside this method.

The root reports a named /opt/homebrew/bin/z3 resolving to Cellar/z3/5.1.0/bin/z3, binary SHA b9a2c3a7dc833da652955116ad743cc733aa7938dbe64f528f71cb09066e2512/16244496B, and one metadata-only --version result 'Z3 version5.1.0 -64bit'. This is root-attributed metadata; this author did not open/stat/hash or execute that binary. Installed API/source/closure equivalence and parameter/output behavior remain unverified. No installation is proposed now. The [official5.1.0 NLSAT tactic source](https://raw.githubusercontent.com/Z3Prover/z3/z3-5.1.0/src/nlsat/tactic/nlsat_tactic.cpp), line138, rejects proof generation; the earlier4.15.3 observation was version-specific and is only historical. Thus UNSAT is retained as a solver result, not a checked empty-feasibility certificate. An unsat core alone would not change this status.

For SAT, retain the complete exact model/values and evaluate each original predicate in that model. UNKNOWN, timeout, unsupported formula/model output, missing variable, exception, limit stop or absent complete result stays INCOMPLETE/UNRESOLVED. Never replace any of these by UNSAT or an empty list. A mathematically SAT result remains distinct from a representable accepted mesh candidate.

## One exact model to one binary64 proposal

Prefer the existing CLI in one persistent SAT session. Enable produce-models before the one check. After SAT, inspect model terms with get-value, including exact Boolean comparisons such as (< x rational), (= x rational) and their greater-than forms. The [SMT-LIB2.7 reference](https://smt-lib.org/papers/smt-lib-reference-v2.7-r2025-07-07.pdf), sections4.2.5–4.2.6/pp70–71, defines these queries over the same current model until the next check or leaving SAT mode. Do not assert, push/pop, re-check, change model options or restart during this phase. Log every exact request/response and the before/final full model. Unsupported or inconsistent behavior refuses materialization. This avoids requiring a new z3py/C-API setup; the official algebraic API remains background source evidence, not an available installed interface.

A rational model coordinate can use exact Fraction arithmetic. For an algebraic coordinate, use exact same-model comparisons to determine its sign and compare its magnitude against the maximum finite binary64 value. Refuse out-of-range materialization. For a finite magnitude, binary search the ordered nonnegative finite IEEE754 word codes to find the greatest representable dyadic value a<=|x|. This takes at most63 rank decisions; exact equality or one exact comparison to the adjacent-values' rational midpoint chooses the nearest word, with even-significand least-significant-bit selection on equality. Sign/range/equality checks are additional fixed Boolean queries; record them explicitly. Exact zero maps canonically to+0; a negative nonzero value that rounds to zero maps to-0. Fixed signed-zero words are never regenerated. Subnormal/normal and exponent boundaries follow the same ordered-word rule. This finite encoding calculation performs no quality-guided geometric search and uses no arbitrary precision sweep.

Save the adjacent exact dyadics, midpoint, comparison/tie disposition, selected word and original exact model term for each changed coordinate. Round the absolute coordinate once. The word vector may lie outside the real feasible set even when all model predicates are true. Recheck all499 original cells independently with exact Fraction Cartesian determinant/face-Gram arithmetic on the actual proposed binary64 words. Require D>0, denominator>0 and Q^2>=1/100, every fixed/context/boundary/protected word unchanged, original ordered incidence/classifications unchanged, complete shared/good/poor rows retained and exact before/final signed-volume equality for each own full component. Solver success, SAT or correct rounding cannot override one failed row. One failed rounded model is a failed candidate; it is neither a proof that no feasible binary64 vector exists nor authorization to try another model/sample.

## Independent acceptance and the geometry gap

Reuse the existing full saved intake and exact-quality kernels, but keep a separately authored Cartesian six-term determinant/face-Gram validator independent of the SMT emitter and solver. It reconstructs the11 blocks, all499 cell constraints and full48-to271 projection, validates binary64 words and checks the66/1983/86 protected history. It must validate complete oriented face cancellation, fixed exposed-face words and own exact volume for every block; preserving only a summed volume is insufficient. Any concatenation of component candidates gets a fresh all499 exact check. The independence of cell constraints does not prove geometric separation between moved components or the complement.

Fixed connectivity introduces no new feature owner or duplicate-cell topology. Complete seed stars already close affected-cell coverage. Application still lacks independently established full TET exterior incidence/opposite internal-face orientation, manifold vertex/edge links and an embedded global boundary/filling theorem applied to the actual current complex. Positive local determinants and fixed-boundary hashes alone do not close those gaps. Preserve region/entity/interface labels exactly; dim3/single volume(3,1) is not an OEM semantic-interface certificate. Missing labels require original CAD/interface evidence, not guessed names.

Known recovery sources remain the exact current head-volume.msh identity2b994eea.../235798094B and its source BIN, with a separately admitted read-only complete-incidence/classification capture. Existing reader.py:163–183 shows full node/TET/surface recovery and BIN face matching; classifications():91–116 and mesh_apply_sicn_proposal.py:101–126 recover entity records but currently preserve hashes. The reader explicitly does not provide an independent TET-boundary incidence audit. No such body is reopened or capture authorized here. A local/global injectivity theorem needs verified finite complex/manifold, consistent nondegenerate orientation and bijective embedded boundary premises. Until those are proved, geometry/application/global acceptance remains null/false even for a passing quality vector.

The871731 boundary coordinates and exterior connectivity remain unchanged, preserving the existing representation budget as inherited evidence. The414 stronger cap-shape failures are a separate criterion; they are not a theorem that SICN0.1 volume quality is impossible. Boundary retriangulation is not selected in this method. Conditional strength/material, calibrated LPBF, Omniverse and PhysicsNeMo remain downstream of an actually accepted head mesh.

## Finite synthetic guard plan and limits

Prepare eight named groups, source first and UNRUN: (1) exact current-intake/protected membership and omitted-good/shared/stale-word/type refusals; (2) independent regular/right tetra metric identities, reversed orientation and planar/coincident refusal; (3) one- and two-seed polynomial degree/denominator clearing plus zero/constant predicates and complete row associations; (4) exact rational/algebraic SAT and contradictory polynomial UNSAT toy cases, with version/parameter and original-predicate model checks; (5) same-model get-value Boolean semantics plus repeated full-value/model stability and malformed/UNKNOWN/timeout refusal; (6) rational/algebraic nearest-word fixtures spanning ties-even, negative zero, subnormal/normal and exponent boundaries; (7) a rounded-point failure despite a feasible real model and fixed/protected/orientation/volume failures; (8) complete11-case bookkeeping, incomplete unattempted cases, full-output cap/error retention and all null/false geometry/physical gates. These are groups, not a promised assertion count. No guard is authored or run by this assessment.

A future proposal may retain the existing whole60s stop threshold/T8 grace, sampled2GiB, inclusive32MiB and requested thread1/no-retry ceilings for one finite eleven-block diagnostic. It may stop with some blocks unattempted or UNKNOWN. Algebraic comparisons have finite word-rank decisions but unbounded exact arithmetic cost; no60s completion or hard peak guarantee follows. Keep all returned models, predicates, rounded failures, full transcript and incomplete terminals; no truncation, accepted empty result or automatic continuation. Exact source/guard/runtime/control review and a separate root decision are required before any real coefficient/model/word calculation. This packet creates none of those authorities.
