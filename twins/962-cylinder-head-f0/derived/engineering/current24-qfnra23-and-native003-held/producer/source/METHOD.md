# Held coupled QF_NRA source preparation

This packet implements pure source functions for the method accepted by `head-star-current24-coupled-qfnra-method-root-001/method-review.json`. It has not been imported, executed or tested. No current-head coordinate, coefficient, root, model or candidate-word calculation was performed while preparing it. There is no process transport, executable entry point, actual contract, controller, launch or execution authority.

The scope is the existing complete 23-record saved intake: 271 coordinate rows, 499 original ordered TET4 rows, 24 poor and 475 initially good cells, including 33 shared cells, and all 16 admissible interior seeds. The manifest partitions these into the same 11 complete variable groups: six singletons and five pairs. All 255 other context coordinates are fixed, including 179 boundary-tag rows. The full head's 871,731 boundary nodes and prior 66 moved nodes, 1,983 cells and 86 improvements remain protected. This source neither regroups the variables nor claims that regrouping adds freedom.

## Exact intake and association

`admit_current(saved_bytes, edge_held_bytes)` consumes an explicit dictionary of exactly 23 saved byte strings and the accepted edge-intake held bytes. It opens no paths. The original map is fixed by canonical SHA256 `61a9482457279b33b43ae53aae18c5a7ebc6717e21a72ede8bab0e22e8cdc0e5`; every supplied byte string must match its original descriptor. Seven donor definitions are copied byte-for-byte and AST-for-AST: `coordinate_rows`, `need`, `typed_hash`, `current_faces`, `prepare_context`, `oriented_boundary` and `context_snapshot`.

The new intake additionally binds the rejected manifest IDs 2, 7, 8, 9, 10, 21, 28, 30, 31, 39 and 45; requires disjoint and complete 16-seed/499-cell unions; and refuses any incident cell containing a variable from a different block. Each cell keeps its native array index, tetrahedron tag and original ordered connectivity. A full before/after context snapshot includes signed-zero coordinate words and all classifications/protection records. No initial good or shared neighbor is dropped.

## Uniform integer normalization

For every stored finite binary64 coordinate, the exact rational value is dyadic. Let `k` be the largest denominator exponent among all 271 rows and let `K=2^k>0`. Define scaled variables and fixed coordinates by `y=K*x`. Every fixed scaled coordinate is an integer; native coordinates project back by `x=y/K`. This is a change of representation, with no movement radius, objective, additional geometric constraint or coordinate rounding.

For an ordered tetrahedron let `D=det(p1-p0,p2-p0,p3-p0)`, `S` be the sum of its six squared edge lengths and `T` the sum of its four squared face cross-product norms. The unchanged inverse-Frobenius quality satisfies `Q^2=36*D^2/(S*T)`. Therefore `Q>=0.1` is equivalent to `P=3600*D^2-S*T>=0` after imposing `D>0`, `S>0` and `T>0`. Under the common scaling, `D'=K^3 D`, `S'=K^2 S`, `T'=K^4 T` and `P'=K^6 P`. Positive `K` preserves every strict/non-strict predicate and the exact signed-volume equality. The DAG is built directly from integer constants, variables and `+,-,*`; it is not expanded into floating coefficients.

Each cell has one or two moving vertices. Choosing a fixed vertex as determinant origin preserves native orientation through the exact permutation parity and limits determinant degree to one or two. Every face has a fixed pivot. Hence the source checks a total-degree upper bound of four or six for `P`. Constant and zero nodes/predicates remain represented. All 499 cells receive the four explicit predicates; each group's complete oriented boundary must cancel internally and have only fixed vertices. An additional equality preserves that group's own baseline sum of signed determinants. The boundary/volume observations are procedural constraints, not a global embedding certificate.

## Literal solver plan and strict replies

The untested command plan is `/opt/homebrew/bin/z3 -in -smt2`, source tag `z3-5.1.0`. Root has observed only the version query, whose exact saved stdout is `Z3 version 5.1.0 - 64 bit\n`. Installed binary/source/runtime equivalence remains unproved. The source emits this fixed prologue:

```smt2
(set-option :print-success false)
(set-option :produce-models true)
(set-option :pp.decimal false)
(set-logic QF_NRA)
```

It follows declarations, acyclic `define-fun` integer DAGs and named assertions with this one planned command:

```smt2
(check-sat-using (using-params qfnra-nlsat :randomize false :shuffle_vars false :reorder false :seed 0 :zero_accuracy 0))
```

This is an exact literal proposal, not a successful CLI/API probe. Z3's tagged source registers `check-sat-using`, retains its check result/model, collects NLSAT and algebraic parameters, and documents algebraic `zero_accuracy=0` as exact computation. Any unsupported option, malformed response, error, EOF, timeout, resource stop or UNKNOWN is incomplete. UNSAT is solver-attributed only; tagged NLSAT rejects proof generation. No checked UNSAT certificate or global/topological impossibility is claimed.

`parse_sexpr` accepts one complete response with a 32 MiB byte ceiling. Duplicate/missing/extra/out-of-order model symbols, approximate numerals, unknown numeric syntax and mismatched Boolean query terms refuse. Exact integer/decimal/rational forms are retained as rationals. A supported `root-obj` form is retained as solver-owned polynomial/index syntax; this parser does not prove its isolation, interpret the root ordinal, call a root evaluator or use a decimal approximation. Unsupported exact printer syntax can therefore refuse safely. SAT alone permits a candidate projection.

After a SAT result, all comparison queries must use the same retained SAT model/session with no assertion, push/pop or additional check. SMT-LIB specifies evaluation of well-sorted closed terms, including Boolean comparisons, in the current model; model completion may extend it consistently. The projection hash is an association token, not proof that an external transport preserved that session. A later reviewed transport must retain complete requests/replies and bind the run, component, SMT text and projection. This packet supplies no such transport. Fixed protocol choices and rounding given a retained model are deterministic; no unique model, query-order-independent model or cross-version witness is promised.

## Exact binary64 proposal and independent gate

`nearest_binary64` accepts one exact component/node/axis association, positive power-of-two scale, model identity and an explicit pure Boolean callback. It asks exact scaled comparisons against rational thresholds. After zero/sign/finite-range checks, binary search over the ordered finite nonnegative binary64 words finds adjacent bracketing values in at most 63 rank decisions. Exact midpoint comparison and the least significant bit implement round-to-nearest, ties-to-even. Exact zero maps to canonical positive zero; a negative nonzero value rounding to zero retains the negative-zero word. Out-of-finite-range or unavailable/inconsistent replies refuse, retaining all partial events. These finite rank comparisons compute a representation; they do not search alternate geometry or models.

`word_proposal` requires all 48 mappings across all 11 groups, preserves the other 255 coordinate words and emits all 271 before/proposed rows. There is no selected subset, alternate ratio, nearby-word sweep or fallback. The pure handoff schema is `962-current24-qfnra-one-model-word-proposal/v1`:

- `input_records`, exact `context_before`, all 499 `original_cell_rows`, and 11 `components`;
- 271 `proposed_coordinate_rows` with `node_tag`, `coordinates_mm`, three `binary64_hex` strings and contiguous 48-hex-character little-endian `<3d` `words_le_hex`;
- 48 ordered `coordinate_mapping_records` with exactly `component_ID`, `node_tag`, `axis` (`x/y/z`), `symbol`, `word_u64`, 16-character `word_le_hex`, `model_ID` and full `events`;
- full `mapping_evidence` and positive homogeneous `normalization`, retained as source-attributed evidence, not validator proof;
- `complete_application_eligibility=null`; application, global embedding, physical and manufacturing flags false.

The independently authored validator's agreed API is `validate_proposal(proposal, saved_payloads, input_records)`. It must independently reconstruct the original intake and recheck every original cell with Fraction Cartesian determinant, six-edge/four-face quality, orientation, fixed words, own oriented boundary/volume and protection. A real SAT witness does not imply a feasible binary64 proposal. A failed rounded proposal is an explicit representability/candidate refusal, not an UNSAT result or permission to sweep nearby words. This preparation has produced no proposal and no word-validation result.

## Held synthetic checks and limits

The fixture source declares 14 direct unittest methods. It exercises duplicate/nonfinite JSON and held-map refusal; a dyadic right tetrahedron with analytically known `D,S,T,P`; one/two-variable degree bounds and reversed/planar orientation; constant DAG nodes and literal SMT text; rational/algebraic projection framing; malformed replies; Boolean query association; rational and algebraic fake-oracle rounding; subnormal/normal and exponent boundaries; ties-even and signed zero; a real interval whose rounded point fails; missing/non-Boolean/out-of-range callbacks; partial-mapping refusal; and exact donor/source reuse. All oracles are inert pure synthetic callbacks. The fixture's finite reads are the two new pure module files, original donor source and original held metadata; it reads no real coordinate payloads. None of the 14 methods has run.

Every complete DAG/SMT/proposal and reply is limited to 32 MiB, with refusal rather than truncation. No completion time is promised. Future guard/solver/validator executions require separately reviewed runtime, owner, actual and admission controls; proposed historical ceilings remain 60 seconds, eight threads observed, sampled 2 GiB RSS, 32 MiB inclusive output, thread-one environment and no retry. These are not an inclusive hard quota or a runtime authority. No transport/controller is authored here.

The 19 empty prescribed paths and 55/1,033 refused edge alternatives remain immutable and limited to those families. Full-head incidence/manifold/embedded-boundary/interface/region ownership evidence is still missing for application. Positive local cells, word validation or conserved volume cannot close that gap. The current 24 poor cells, original quality threshold, mechanical failures and all downstream strength/material, LPBF, twin and PhysicsNeMo gates remain unchanged.

Primary support (source review only): [SMT-LIB 2.7, model queries](https://smt-lib.org/papers/smt-lib-reference-v2.7-r2025-07-07.pdf), [Z3 5.1.0 shell CLI](https://github.com/Z3Prover/z3/blob/z3-5.1.0/src/shell/main.cpp), [tactic command/model retention](https://github.com/Z3Prover/z3/blob/z3-5.1.0/src/cmd_context/tactic_cmds.cpp), [QF_NRA tactic](https://github.com/Z3Prover/z3/blob/z3-5.1.0/src/nlsat/tactic/qfnra_nlsat_tactic.cpp), [NLSAT model/proof/parameter source](https://github.com/Z3Prover/z3/blob/z3-5.1.0/src/nlsat/tactic/nlsat_tactic.cpp), [NLSAT parameters](https://github.com/Z3Prover/z3/blob/z3-5.1.0/src/nlsat/nlsat_params.pyg), [exact algebraic parameter default](https://github.com/Z3Prover/z3/blob/z3-5.1.0/src/math/polynomial/algebraic_params.pyg), [Z3 NLSAT description](https://z3prover.github.io/papers/z3internals.html). No third-party source body is copied into this packet.
