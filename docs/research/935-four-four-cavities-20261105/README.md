# 935 four-to-four conditioning without surface motion

A single verified four-to-four topology pass removes 6,754 cells from the
ultra-low mean-ratio bin below 0.0001: an 18.3343% reduction, with no regression
in any of the five reported bins. All points, boundary faces and total cell
count remain exact. It replaces 506 members of the previously identified severe
conditioning subset. Every one of the 27,016 new cells has an interval-certified
mean-ratio floor and a derived edge-Jacobian Frobenius-condition bound of 12,000.

The candidate is suitable for **further source-preserving conditioning work**,
not engine fields. The global minimum remains unchanged, 2,624 previously severe
cells persist, and native readback/operator checks have not been repeated for
the changed connectivity. Faithful editable CAD, physical scale/interfaces,
operating data and metal-process/physical qualification remain separate open
requirements of the full head goal. No printing master or specimen geometry is
redesigned by this numerical topology operation.

## Source and admission before execution

The input is the exact positive source volume
`233f7bd83072772fa0b92d0287f20cec3cf44c4988546be42addf5579630299e`,
with its frozen whole-volume, boundary and native-winding evidence. The
[two-to-three trial](../935-residual-cavities-20261105/README.md) uses this same
parent, not a predecessor of the new candidate. Its 0.01-bin gain does not touch
the worst cells and worsens moderate bins; it is not the starting mesh here.
The two trials' gains must not be added as though they were consecutive passes.

The selected operation removes an internal edge with exactly four incident
tetrahedra. Their remaining vertices must form a closed four-cycle. A strictly
convex six-vertex cavity admits two finite opposite-ring diagonals; each gives
a known four-cell alternative. The constructor takes the first admissible
diagonal in canonical order. It does not search over coordinates, origins,
quality thresholds or mesher settings.

Every new cell must have mean ratio at least 0.01. Every accepted cavity must
remove at least one cell below 0.0001, preserve the oriented boundary, and
increase none of the counts below 0.0001, 0.001, 0.01, 0.05 or 0.1. Its new edge
must be absent from the entire source. Packed old-cell domains must be disjoint,
and created edges unique. These are diagnostic numerical gates, not engineering
material allowables or a complete operator-admission specification.

## Independent reference and actual operator controls

The six-point reference is a rectangle bipyramid, with poles `(0,0,1)` and
`(0,0,-1)` and ring `(e,-1,0)`, `(e,1,0)`, `(-1,1,0)`, `(-1,-1,0)`.
The final reference uses exact dyadic `e = 2^-24`. These are synthetic,
dimensionless coordinates, not a Porsche calibration. Its four old cells
surround the pole edge; its literal alternative surrounds the diagonal between
the first and third ring vertices. All eight oriented hull triangles remain
identical and strictly support all other vertices. The exact total volume is
`16777217/12582912`; every reference cell has exactly one quarter of it.

Preliminary fixture 001, with `e = 2^-20`, is retained as an admission failure:
its old minimum is 0.000115349, above the unchanged target 0.0001. Fixture 002
is justified before execution by the analytic bound
`Q_old^3 <= 27*e^2/16`. Its old minimum is approximately 1.8166363e-5 and its new
minimum 0.66666668. Every quality bin improves. Both tiny reference capsules are
frozen/rehashed; their manifests are included in [results.json](results.json).

The actual constructor must reproduce the frozen literal cell sets, not merely
invent a different passing toy. It passes that comparison and the source-derived
contract before the head call. Reversed cells, duplicate cells, nonconvex source,
and occupied new edges are refused. A separate verifier exercises full source
edge-incidence counts and the same published geometric contract. Shared pinned
predicate/contract code is explicit; no claim of independent implementations of
every predicate is made. Complete global inspection uses the distinct frozen
whole-volume inspector.

## Complete current-source cavity coverage

All 12,981,388 source cells are inspected with interval/exact signs. Every
existing quality-bin count is reproduced, including 143 exact sign fallbacks.
The 36,838 critical cells touch 206,343 unique edges. Of these, 65,968 have
valence four and 32,036 form closed four-cycles. Strict supporting-plane checks
admit 8,618 cavities. There are 3,323 exact support fallbacks and 2,981 known
coplanar support rejections. A coplanar rejection here is a restriction of this
strict-cavity contract, not proof of a physically invalid or nonconvex surface.

Of the two finite alternatives per admitted cavity, 12,268 satisfy all quality
and chain checks; all proposed new edges are globally absent. Canonical choice
selects one alternative for each of 7,208 cavities. Disjoint packing rejects
454 cell conflicts, with no duplicate new edge, leaving 6,754 proposals.
The constructor exports indices and predictions only, not an admitted mesh.

The separate verifier scans all source edges to confirm that every removed star
has exactly four cells and every new edge has zero source incidence. It checks
all expected new cell sets, strict old hull supporting planes, positive signs,
oriented boundary chains, quality values and every local nonregression rule.
Only then is a candidate exported and reloaded for complete array comparison.
All old cells outside those cavities are also compared directly with their
candidate rows in the subsequent conditioning audit.

## Complete volume and quality outcome

The frozen inspector certifies 12,981,259 cell signs by outward intervals and
129 by exact fractions. All 21,853,547 internal face pairs cancel, the complete
8,218,458-face source boundary and orientation match, and every node is used.
The calculation candidate has the same 4,181,299 nodes and 12,981,388 cells.
Local strict-convexity/partition proofs preserve the replaced domains. The
inherited global tetrahedron-intersection status is not upgraded into an
exhaustive new pairwise-intersection certificate.

| Diagnostic threshold | Source cells below | Candidate cells below | Change |
|---|---:|---:|---:|
| 0.0001 | 36,838 | 30,084 | -6,754 |
| 0.001 | 56,409 | 49,655 | -6,754 |
| 0.01 | 254,353 | 247,599 | -6,754 |
| 0.05 | 2,014,409 | 2,007,674 | -6,735 |
| 0.1 | 4,427,483 | 4,420,773 | -6,710 |

The minimum remains `1.291009351665788e-11`; minimum volume remains
`2.5543337315637495e-20` in inherited hypothetical mm cubed. Physical scale is
not calibrated by this work. The absolute diagnostic quality gate still fails.
The accepted input for further conditioning is candidate
`62717026bdfc3dc9c1a6cde682b32db12900cad8460f158a7319c41d001e2462`.
This designation grants no native solver, engine or manufacturing admission.

## New-cell condition certificate and retained severe cells

For a positive tetrahedron, write `S` for the sum of its six squared edge lengths
and `D` for its edge-Jacobian determinant. Then `q^3 = 432*D^2/S^3`.
`inspect_condition_coverage.py` compares this expression with the **exact cube
of binary64 0.01**, using outward interval operations throughout. Exact Fraction
fallbacks are implemented for ambiguous cases. All 27,016 new cells pass
intervals; none needs fallback. Thin, inverted and coplanar controls are refused.

For the three-by-three edge Jacobian `A`, its singular values give
`||adj(A)||_F <= ||A||_F^2/sqrt(3)`, and `||A||_F^2 <= S`. Substituting the
mean-ratio identity yields `kappa_F(A) <= 12/q^(3/2)`. Since binary64 0.01 is
at least exact 1/100, every certified new cell has **kappa_F <= 12,000**. This
dimensionless edge-matrix bound is not a PDE matrix-condition, native geometry
evaluation-error, field-convergence or physical-accuracy bound.

The audit maps the old 3,130 minSICN-disagreement cells and their exact rational
condition values into the candidate by source cell identity. It confirms all
retained coordinate bits and ordered cell tuples unchanged. Of that old subset,
506 are replaced, including 39 with kappa_F at least 1e15 and six at least 1e16.
The remaining 2,624 keep their prior exact conditioning: 186 are at least 1e15,
40 at least 1e16, and 54 have kappa_F times binary64 epsilon at least one.
All five prior spectral-lower-bound amplification cases persist. The retained
maximum is approximately 4.65754e16. The candidate's native minSICN is **not**
recomputed or inferred from these source-tuple facts. Remaining extreme cells,
source-relative constraints and operator-specific admission precede a field run.

## Execution, reproducibility and boundaries

The phase ledger is written before execution. In the existing isolated Mac
Python 3.12.11/NumPy 2.5.4 runtime, the unchanged bounded runner enforces 600
seconds per stage, 40 GiB sampled RSS and a 4 GiB disk reserve; it terminates and
reaps only its owned child group on a limit. Actual proposal, local proof,
whole-volume inspection and condition audit complete in about 16.2, 24.3,
55.6 and 3.05 seconds. All workers are terminal before private freezing.

Run `propose_four_four.py --control-only` with the repository, frozen source
mesh/report, frozen reference and a fresh output directory, then its head
proposal profile. Give `verify_four_four.py` the source/proposal/report/reference
and run its control profile before local verification. Run the frozen complete
volume inspector against the exact original calculation surface, source report
and frozen helper. Finally run `inspect_condition_coverage.py` with those
outputs and the frozen native-conditioning parent. Exact argument/PID/execution
receipts and source snapshots are private; no existing output is overwritten.

The source-derived contract, actual operator, verifier and conditioning auditor
are published with hashes and aggregate receipts. The frozen reference archive
and acquired head data are required for exact receipt replay; the reference
geometry itself is fully specified above. Raw arrays, subset maps and candidate
remain outside Git. The original scan and printing master are freshly rehashed
unchanged. No supplier message, scan transfer, cloud creation or paid compute
occurs here. Prior reservation ceilings remain $10.80 within the unchanged
$35/$30/$5 budget; they are not a provider invoice.

Further work must target the retained severe subset and re-establish native
readback/admission for any changed connectivity. The full specimen/geometry,
interfaces, operating conditions, material/process, finished inspection and
engine-validation requirements remain open; this dossier does not redefine
completion around a mesh metric or a passed repository check.
