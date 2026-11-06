# Complete 935 conditioning census and bounded surface-sliver correction

This increment first classifies **every** cell of the preceding calculation
mesh. The previously retained native-disagreement subset is not a complete
conditioning census: the full audit finds 29,814 cells with edge-Jacobian
Frobenius condition number at least 1e12, including 27,190 outside that subset.
All 27,016 cells introduced by the preceding four-to-four pass remain below
the severe threshold, consistent with their separate certificate.

The source attribution then determines the admissible operation. Of the 29,814
severe cells, 26,837 have exactly two actual source-boundary faces; 29,811 have
no interior vertex. More arbitrary interior relocation or mesher-parameter
sweeps would miss this boundary constraint. The new operation removes tiny
surface sliver tetrahedra, replacing each pair of exterior triangles by the
opposite pair of faces. It changes the represented calculation surface and
material volume. **It does not preserve the exact old surface.** No acquired
scan coordinate or original printing master is changed.

After complete independent checks, the severe count falls from **29,814 to
15,945**, a **46.5184% reduction**. The count above 1e16 falls from 85 to 29.
The maximum and absolute quality failure remain; this candidate is accepted
only for further calculation-domain conditioning, not head field calculations.

The full faithful-CAD, functional-engine and metal-process goal remains open.
Physical units, interfaces, hidden passages, operating data, material/process,
finished inspection and engineering qualification are not supplied by this
numerical calculation-surface study.

## Inputs and upstream verdict

The accepted numerical parent is the [four-to-four candidate](../935-four-four-cavities-20261105/README.md),
SHA-256 `62717026bdfc3dc9c1a6cde682b32db12900cad8460f158a7319c41d001e2462`.
Its 12,981,388 positive tetrahedra and complete oriented boundary have already
been independently checked. Its absolute quality gate still fails. New source
versions and outputs are separate; no frozen source, recipe or evidence is
edited.

The surface has 4,106,319 vertices and 8,218,458 triangles, SHA-256
`5b04e72b5f7b48f340a39c14009292c52c1bf1ac422ad64cd3250c17ddf51db4`.
Its construction tags are retained: tag zero is the inherited envelope skin,
**not established acquired-scan identity**; positive tags are assumed cut caps,
**not measured engine interfaces**. Incident cap tags alone do not establish
exact coplanarity. A literal node-ID triangle join attributes all severe-cell
faces and vertices; absent faces receive no inferred construction label.

The inherited source-to-surface correspondence bound is 0.009643215373731693
nominal mm. It is a complete digital geometry correspondence, not metrology,
physical tolerance or proof of hidden specimen geometry. The new fixed local
limit is `512 * 2^-52 * maximum_bbox_extent`, about 2.54842e-11 nominal mm,
chosen before candidate inspection. The composed bound must remain below the
existing 0.01 nominal-mm study limit. The bound is not swept or relaxed.

## Complete condition census

For each ordered cell edge matrix `A`, the audit encloses
`kappa_F^2 = ||A||_F^2 * ||adj(A)||_F^2 / det(A)^2` using outward intervals.
Ambiguous threshold comparisons and signs use an exact Fraction oracle for
the stored binary64 coordinates. Every severe cell also gets a stored exact
reciprocal condition value. The controls compare 960 classifications against
independent exact arithmetic over 120 dyadic and near-threshold fixtures;
inverted and singular inputs are refused and power-of-two scaling is checked.

| Condition number at least | Complete parent count |
|---|---:|
| 1e3 | 306,517 |
| 1e6 | 30,125 |
| 1e9 | 29,814 |
| 1e12 | 29,814 |
| 1e15 | 402 |
| 2^52 | 124 |
| 1e16 | 85 |
| 3 * 2^52 | 9 |

The exact reciprocal ordering gives an approximate maximum of 4.65754e16.
These are cell edge-matrix conditions. They are not PDE matrix conditions,
native geometry evaluation errors, discretization-error bounds or engine
accuracy. Native minSICN is neither recomputed nor inferred here.

## Source-derived peel contract

A candidate tetrahedron must have exactly two actual boundary faces, both
inherited skin. None of its four vertices may touch any cap. The old boundary
diagonal must not be any noncollapsed image of the 702,636 original marked
feature edges. The exact upstream collapse map and vertex-index inverse map
that feature contract into the current surface; no inferred crease detector
replaces it.

Complete source edge scans must show that the old diagonal belongs only to
this tetrahedron and the new diagonal occurs nowhere on the old boundary.
The new diagonal's complete tetrahedral link must be one connected simple
cycle. Removing the cell opens that cycle into a fan. Packed patches share
no vertices, so their unchanged outer cycles remain disjoint.

Each old/new two-triangle pair must project to the same strictly convex
quadrilateral with four strictly consistent projected orientations. The
dominant component of the first old triangle normal selects the dropped axis.
Subtract its affine plane from both graph interpolants: three vertex residuals
are zero and the fourth has absolute value `abs(det(A) / projected_area)`.
Both interpolants stay within that residual range. Their continuous
bidirectional vertical correspondence has this bound everywhere and fixes the
outer cycle. Disjoint local maps glue to the identity on the unchanged surface;
the added global bound is their maximum, not their sum.

Every old/new normal pair must have positive alignment and cosine at least
`1 - 2^-40`. New triangle minimum shape quality may not fall below the old
minimum, or below the fixed forcing-face floor. There is no coordinate
movement, interpolation of missing passages, smoothing, physical redesign or
shape optimization.

## Actual controls, proposal and independent verification

The five-point synthetic reference uses `A=(0,0,0)`, `B=(1,1,e)`, `C=(1,0,0)`,
`D=(0,1,0)`, `E=(0.5,0.5,-1)`, with exact dyadic `e=2^-44`. Its three positive
cells are `ABCD`, `EACD`, `EBDC`. Removing `ABCD` flips the top diagonal from
`AB` to `CD`; exact volume loss is `e/6`, and graph deviation is `e`. These are
explicit dimensionless control coordinates, not measured Porsche dimensions.
The actual incidence scanner and geometric predicates exercise this fixture;
open/duplicate links, inverted/flat/nonconvex patches and excess displacement
are refused.

The first head **audit**, before geometry export, fails closed on mixed
signed/unsigned NumPy edge-key addition promoting large indices to binary64.
Its source, terminal failure and empty output remain retained. Version two
explicitly casts both endpoints to uint64 and adds a key larger than 2^53 to
the control. It does not alter any geometric gate or overwrite the failed run.

Version two admits 15,933 exact local geometries after global incidence checks.
It excludes 10,693 for worsening triangle quality and 211 for cap constraints;
2,977 are outside the two-boundary-face operation. Vertex-disjoint packing
excludes 2,064 conflicts, leaving **13,869** proposals. Protected marked curves,
normal, correspondence and complete-edge-link rules are not weakened to
increase that number.

The separate verifier re-evaluates all 13,869 local proofs using Fraction
coordinates, independently of the proposal's integer-lattice predicates. It
reconstructs mapped marked edges and cap vertices, streams complete source
edge incidence again, checks all simple cycle links and disjoint vertices, and
checks every old surface triangle by literal vertex IDs. Only then does it
export and reload the new surface and volume, comparing every coordinate bit
and retained ordered tetrahedron tuple. All construction caps remain exact.

The largest added complete local correspondence bound is
1.273484037921788e-13 nominal mm. Upward-rounded composition with the inherited
bound is 0.009643215373859045 nominal mm. Exact summed material loss is about
1.909753036295427e-12 nominal mm cubed. This small number is an exact stored-
coordinate result; it does not grant physical dimensional accuracy.

## Complete independent checks and reproducibility

The independent native validator checks all surface edges, vertex links,
connected components, triangle intersections, material-shell orientation and
actual 3MF coordinate/index roundtrip. The frozen interval/Fraction volume
inspector checks every remaining cell, every paired internal face, all node
usage and the complete new oriented boundary. A fresh condition census must
agree with a separate exact prediction from the removed source-cell condition
values and unchanged retained coordinate/cell tuples. All these checks pass. The native surface has zero open, nonmanifold or
inconsistently oriented edges, manifold vertices, zero intersection pairs and
one positive material shell. Its actual 3MF roundtrip preserves every coordinate
and index. All 12,967,519 remaining tetrahedra are positive: 12,967,467 by
interval and 52 by Fraction. Every node is used; all 21,825,809 internal face
pairs cancel, and the complete new boundary matches with orientation.

| Diagnostic | Parent | Candidate |
|---|---:|---:|
| Mean ratio below 0.0001 | 30,084 | 16,215 |
| Mean ratio below 0.001 | 49,655 | 35,786 |
| Mean ratio below 0.01 | 247,599 | 233,730 |
| Mean ratio below 0.05 | 2,007,674 | 1,993,805 |
| Mean ratio below 0.1 | 4,420,773 | 4,406,904 |
| Condition number at least 1e12 | 29,814 | 15,945 |
| Condition number at least 1e15 | 402 | 121 |
| Condition number at least 2^52 | 124 | 49 |
| Condition number at least 1e16 | 85 | 29 |

The fresh complete condition census agrees exactly with the independent
source-cell deletion prediction at all eight thresholds. Maximum condition
remains approximately 4.65754e16 and minimum mean ratio remains
1.291009351665788e-11. The absolute gate still fails. No tetrahedron-pair
intersection certificate is added to the inherited source status; complete
surface intersection checking is a different check.

Candidate volume SHA-256 is
`a4b19f3303e55e4a13830829664e26596247d26cd41632704d4584706773538a`;
calculation surface is
`16553493632d689fbb78f18403d7a3734a7ed4a111f67cf89f93864cfbec57e9`.
Aggregate terminal receipts and current verdicts are recorded in
[results.json](results.json).

The phase ledgers are written before each stage. Existing isolated Mac Python
3.12.11/NumPy 2.5.4 and the pinned native-validation runtime are reused without
dependency changes. The existing bounded runner enforces 600 seconds per stage,
40 GiB sampled child RSS and a 4 GiB free-disk floor; exact owned children are
reaped. For the native validation stage, the sampled child is its timeout
supervisor, not the Python descendant: its reported RSS is not a whole-job
memory measurement. The wall-time and disk checks still apply; no claim of
complete native-stage RSS enforcement is made.
Run the complete parent census and surface attribution first. Run
`audit_surface_peels_v2.py --control-only` before its read-only head admission;
run `verify_surface_peels.py --control-only` before the head verification/export.
Then run the frozen native surface validator, frozen complete volume inspector,
and `audit_peeled_conditions.py` in that order, each with fresh output paths.
The private ledgers retain the exact command lines and source-at-execution
snapshots. Private acquired data and frozen parent capsules are required for
exact head replay; the toy geometry is fully specified above.

No raw mesh, scan, private contact or solver field bytes are committed. The
original scan and original printing master are independently rehashed unchanged.
The new 3MF is a **calculation-surface study export**, not a machine-specific
metal build, replacement printing master or functional-head release.

All workers are terminal before the private capsule is frozen read-only and
rehash-verified: 76 payload files, 655,920,120 bytes, manifest
`5daee08ce4a12bbe1c389d7eecd7125c63392b3c961954e7d5bb1d18078c02ea`.
The payload count excludes the manifest itself. Repository checks do not
qualify the geometry for engine use or the material/process for manufacture.

No new cloud machine, paid computation, supplier message or scan transfer is
used in this increment. The user's scan-to-Vast authorization remains available
for a prepared task that benefits from it. Prior reservation ceilings remain
$10.80 within the original $35 total / $30 compute / $5 closeout plan; ceilings
are not a provider invoice. Further source-constraint conditioning and renewed
native readback/operator admission precede any head field calculation.
