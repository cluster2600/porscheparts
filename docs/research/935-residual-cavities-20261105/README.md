# 935 residual cavity coverage and two-to-three trial

One fixed-coordinate topology pass removes 10,154 cells from the diagnostic
mean-ratio bin below 0.01, but leaves all 36,838 cells below 0.0001 unchanged.
Two broader bins deteriorate. Complete local-domain and whole-volume checks
pass; this candidate is retained as a calculation trial and **not promoted for
engine fields**. The original scan, boundary geometry and printing master stay
unchanged. The full faithful-CAD, functional-simulation and qualified-metal-build
goal remains open.

## Why another cavity type was investigated

The [preceding two local passes](../935-local-cavity-20261105/README.md) reduce
the 0.01 bin by 51.654%, preserving every coordinate and boundary face. The
[native frame experiment](../935-exact-origin-20261105/README.md) subsequently
establishes numerical frame sensitivity while both native reports fail ten
categories. Coordinate translation does not repair intrinsic conditioning.

This increment examines a different finite combinatorial operation: two
tetrahedra sharing an internal triangle can be replaced by three tetrahedra
around the edge connecting their opposite apices. It is admitted only inside a
strictly convex five-vertex cavity, with identical oriented boundary, a new edge
absent from the entire source mesh, and all three new cells at mean ratio at
least 0.01. Old cells must be disjoint between accepted cavities; duplicate new
edges are refused. No coordinate, surface, threshold or boundary type moves.
The 0.01 value is a diagnostic floor, not an approved engineering allowable.

## Explicit analytic control and refusal checks

The synthetic equatorial triangle has vertices `(0,0,0)`, `(1,0,0)`, `(0,1,0)`.
Its apices are `(1/4,1/4,2^-20)` and `(1/4,1/4,-1)`. These are independent toy
coordinates, never Porsche measurements or scan calibration. The old partition
has two tetrahedra; the literal new reference has three around the apex edge.
The exact total volume is `1048577/6291456`. Exact Fraction determinants give
the new volume fractions `1/4`, `1/2`, `1/4`.

The control improves minimum mean ratio from approximately 0.0001363 to 0.54545,
with exact positive partition and boundary-chain identity. Concave source,
reversed cell, duplicate cell, overlapping source-cell selection, duplicate new
edge, and globally present/absent edge cases are exercised. The separate
verifier uses a literal cell reference and a streaming whole-source edge query;
the constructor uses a sorted global edge index. Both actual control paths pass
before either full-head phase executes.

## Complete upstream audit on the current domain

The input is exactly the final conditioned source
`233f7bd83072772fa0b92d0287f20cec3cf44c4988546be42addf5579630299e`.
Its frozen whole-volume proof, native array mapping and complete integer winding
audit establish source/native cell order and stored-coordinate orientation.
Their manifests and each consumed native face/owner/neighbour file are rehashed
before using native adjacency. The constructor reproduces every existing quality
bin with interval/exact sign predicates, including 143 exact fallbacks.

All 8,218,458 boundary triangles are checked for the inherited fixed-face bound
`q_tet <= q_face^(2/3)`. Sixty lie below the incident-cell ceiling of 0.01 and
belong to sixty distinct current bad cells. Because a tetrahedron has at most
four boundary faces, a loose lower bound is fifteen unavoidable subthreshold
cells if these exact triangles remain fixed. This ceiling evaluation is a
binary64 analytic diagnostic, not an interval certificate or physical limit.

| Interior vertices in a current cell below 0.01 | Cells |
|---:|---:|
| 0 | 130,297 |
| 1 | 123,168 |
| 2 | 884 |
| 3 | 4 |
| 4 | 0 |

Thus arbitrary interior-node relocation at fixed connectivity cannot address
130,297 of the 254,353 bad cells. This does not exclude topology changes or
declare any finite-element operator valid.

## Proposal, separate verification and complete volume inspection

Of 659,091 internal faces incident to bad cells, 180,954 define strictly convex
cavities. Exactly 10,889 pass all new-cell quality and oriented-chain checks.
None has an already-existing proposed apex edge. Greedy disjoint packing refuses
735 cell conflicts and selects 10,154 replacements. The constructor exports
only indices and predictions; it does not export or admit a mesh.

`verify_two_three.py` independently reconstructs each expected three-cell vertex
set from the two old cells and their shared triangle. It derives all six outward
hull triangles from the old representation and checks both remaining vertices
against every supporting plane, with outward determinant intervals and Fraction
fallbacks. It verifies oriented-chain identity, positive cell signs, every new
quality value, disjoint old-cell IDs, distinct new edges and a separate streaming
membership check over all source edges. Only after this full contract passes
does it export the candidate. All coordinate bits and boundary rows are reloaded
and compared exactly.

The frozen independent whole-volume inspector then checks all 12,991,542 cells:
12,991,399 signs pass outward intervals and 143 require exact fractions. All
21,873,855 internal face pairs cancel, the complete 8,218,458-face source boundary
and orientation match, and every node is used. The local convex-domain proofs
preserve each replaced union. The inherited global tetrahedron-intersection
status is not strengthened into a new exhaustive pairwise-intersection claim.

| Diagnostic mean-ratio threshold | Before | After | Change |
|---|---:|---:|---:|
| 0.0001 | 36,838 | 36,838 | 0 |
| 0.001 | 56,409 | 56,409 | 0 |
| 0.01 | 254,353 | 244,199 | -10,154 |
| 0.05 | 2,014,409 | 2,026,397 | +11,988 |
| 0.1 | 4,427,483 | 4,437,713 | +10,230 |

The target-bin reduction is 3.9921%. Minimum mean ratio remains
`1.291009351665788e-11`, and minimum cell volume remains
`2.5543337315637495e-20` in hypothetical mm cubed. The candidate has 10,154 more
cells, the same 4,181,299 points and the exact same boundary. Its summed volume
is 1,094,352.3436893984 in hypothetical mm cubed; the approximate global volume
comparison is not substituted for the local exact domain contract.

These results do not establish an overall conditioning improvement. All newly
created cells meet 0.01, so the unchanged two lowest-bin counts also show that
none of those original critical cells was replaced. A smaller 0.01 bin cannot
be used to hide the unchanged worst cells or the larger moderate bins. The
authoritative parent for subsequent worst-cell work remains the preceding
source; the new candidate and its negative coverage result are retained.
No native solver readback or field check is inherited across the changed
connectivity. No cloud resource is created for this increment.

## Phase ledger and replay

| Phase | Runtime, concrete inputs and commands | Required output/check and state |
|---|---|---|
| R01 input admission | Frozen current source and whole-volume/native/winding manifests | Exact source/readback; absolute physics gate failed before execution |
| R02 analytic control | Existing Python 3.12.11/NumPy 2.5.4; constructor `--control-only` | Exact dyadic reference and refusal checks pass |
| R03 coverage | `propose_two_three.py`, every current cell/native boundary face/incident internal face | Full partitions and sixty fixed-face limitations before mesh export |
| R04 proposal | Same constructor, entire source edge index | Convexity, quality, oriented chains, absent edges and disjoint packing; indexed proposals only |
| R05 local verification | `verify_two_three.py --control-only`, then full source/proposal/report | Literal/negative controls; all 10,154 local contracts pass before candidate export |
| R06 complete volume | Frozen `inspect_interval_volume.py`, candidate and complete original calculation surface | Every cell sign, source boundary, face pairing and all bins checked; absolute gate fails |
| R07 closure/publication | Terminal process receipts, source/master hashes and private manifest | Private bytes frozen/rehashed; English sources/results; Linux repository validation tracked in PR |

The root contains the phase ledger created before execution, source snapshots,
full command/PID/execution receipts, controls, proposal, local proof, complete
volume report, bin comparison and source preservation hashes. The unchanged
bounded runner enforces 600 seconds per stage, 40 GiB sampled RSS and a 4 GiB
disk reserve, terminating and reaping only its child group if necessary.
Actual proposal/verification/whole-volume phases take about 46.5/25.3/54.6 seconds.
Their sampled peak RSS is about 6.14/1.26/3.19 GiB respectively.

To replay, give the constructor `--repository`, `--native-parent`,
`--winding-parent`, `--mesh`, `--mesh-report` and a fresh `--output`; run its
`--control-only` profile first. Give the verifier `--repository`, `--mesh`,
`--proposal`, `--proposal-report` and a fresh `--output`; run its control profile
first. Apply the frozen whole-volume inspector to its candidate with the exact
source surface, source report and frozen helper referenced by the parent study.
Existing output directories are refused. Never derive an input manifest from
the output it is intended to validate.

Sources and aggregate receipts are in [results.json](results.json). Raw arrays,
proposal indices and candidate remain private. The original $35/$30/$5 budget
is unchanged; prior reservation ceilings remain $10.80 and this local increment
adds $0 of paid compute. No supplier message or scan transfer occurs.

The next admissible experiment is a separately controlled larger edge cavity,
such as a convex four-to-four alternative, aimed explicitly at the ultra-low
subset and requiring no regression in any reported bin. It is not executed in
this increment. Source-relative geometry admission must precede any such trial;
the full specimen/scale/interfaces/material/operating/process/physical gates
remain unqualified.
