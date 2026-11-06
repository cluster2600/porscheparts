# Exact nonconvex cavity partitions: a 935 conditioning benchmark

This increment independently replaces the actual worst-conditioned source cell
inside one 37-cell cavity, without moving any existing coordinate or boundary
triangle. It is a numerical mesh benchmark on the inherited hypothetical
calculation domain. It does not reconstruct missing specimen geometry or qualify
a functional cylinder head. The [bulk trial](../935-centroid-extreme-batch-20261105/README.md)
uses the **same parent**; these two improvements must not be added together.

[Machine-readable results](results.json) include executed source hashes, terminal
receipts and private artifact hashes. Geometry remains outside Git. The frozen,
read-only private capsule `935-signed-partition-20261105-001` contains 95 payload
files (197,134,719 bytes); its manifest SHA-256 is
`4a9c29a825f7125e6b810d16e7fa2383993c4499086bcfc6d87500ce7521af04`.

## Upstream admission and domain proof

The [source-admitted parent](../935-residual-source-admission-20261105/README.md)
has SHA-256 `1bc2e8dddaf07c43ca36d35608f4fdb508f22e0694e922108a96466887f6182d`.
Its complete boundary, positive stored-coordinate tetrahedra and exact severe
condition values were checked before these trials. Absolute element quality and
physical admission remain failed. The source surface still includes inherited
envelope geometry and explicitly assumed closures.

Requiring a convex cavity, or comparing its volume with a convex hull, rejects
some valid nonconvex replacements. This increment instead checks the following
finite, exact certificate:

1. Every old and new tetrahedron has strictly positive orientation.
2. An exact separating plane certifies disjoint interiors for every pair within
   each partition. Touching boundaries are permitted.
3. The complete oriented triangular boundary chains are identical, after exact
   cancellation of interior faces. No original cavity vertex is discarded.
4. Independently summed exact volumes agree; all new mean ratios are at least
   the stored binary64 value `0.01`, and none of five fixed quality-bin counts
   regresses.

Here is the domain argument, rather than a sampled containment test. Away from
the finitely many triangle planes, the winding of a positive tetrahedron's
outward boundary is its interior indicator. Triangle contributions add and
reverse sign with orientation. Equal oriented chains therefore give equal sums
of indicators. Pairwise disjoint interiors make each sum the corresponding
union indicator. Both finite unions of closed, full-dimensional tetrahedra are
closures of their interiors, so the closed domains also agree. Exact volume
equality is an additional conservation check, not the domain proof by itself.

The oriented-triangle winding formulation is documented in section 4 of
[Jacobson, Kavan and Sorkine-Hornung (2013)](https://igl.ethz.ch/projects/winding-number/robust-inside-outside-segmentation-using-generalized-winding-numbers-siggraph-2013-compressed-jacobson-et-al.pdf).
The finite partition argument above is this project's derivation; no sampled
winding calculation is promoted to a certificate. Face normals and cross-edge
directions for polyhedron separation are described in section 4 of
[Eberly's separating-axis reference](https://www.geometrictools.com/Documentation/MethodOfSeparatingAxes.pdf).
Neither source establishes the identity or geometry of this specimen.

## Literal controls and bounded refused paths

Three independent synthetic references precede specimen trials:

| Reference | Exact volume | Replacement | Result |
|---|---:|---:|---|
| Concave four-cell notch | 1/2 | 4 to 4 | Each new volume 1/8; notch remains outside both domains |
| Concave six-cell notch | 7/6 | 6 to 8 | Four new volumes 1/8 and four 1/6 |
| Same six-cell domain, exact volume centroid | 7/6 | 6 to 12 | Centroid `(0, 27/56 + 2^-26, 0)`; 81 pair separations |

The four-cell control includes 66 independent barycentric sample checks,
translation/scale/sign controls and forged duplicates; sampling is diagnostic
only. The centroid control also rejects an apex outside the strict kernel, a
forced thin boundary face and unsupported deletion of old interior nodes.
Once-rounded centroid coordinates agree with an independent Fraction
calculation. The centroid control minimum mean ratio improves from approximately
`1.6367e-5` to `0.44165`.

The fixed worst-cell profile has 150 incident edges. The four-cell search admits
six disjoint alternatives elsewhere, but none removes the worst cell; they are
**not applied** here. Both incident six-cell stars were tested against all 28
finite alternatives: 21 overlap failures and seven nonpositive alternatives;
none was applied. These failed bounded paths remain in the capsule.

One initial control failed before opening the head because the native predicate
submodule was not explicitly imported. Its source and failure are retained;
`propose_centroid_cavities_v2.py` is a separate executed revision. All 14 worker
stages are terminal, including that expected failed control.

## Successful boundary-preserving centroid trial

Four complete source boundary-vertex stars and their one-ring expansions form
eight fixed profiles. Native source boundary intersection checks pass. Five
centroids fail strict interior admission; three proposals pass. The first
admissible profile in the predetermined order is selected, rather than choosing
the best observed quality. It replaces **37 cells with 44**, retaining all 24
old cavity vertices and all 44 cavity boundary faces, including 17 global faces.
The extra point is a numerical interior node, not a new physical feature.

The exact ideal centroid uses positive tetrahedron volume weights and is rounded
once to binary64. The fixed-face screen uses `q_face² = 12 |cross|² / S_face²`.
For a fixed face, maximizing tetrahedral mean ratio over the apex gives
`q_tet³ <= q_face²`; a face below `binary64(0.01)³` is therefore refused before
candidate tuning. No quality floor or boundary is relaxed.

The separate verifier recomputes the complete seed incidence in the original
volume, exact Fraction centroid, rounding, signs, volume, oriented chains and
five quality counts. It stores **1,612 independently generated Fraction
separating-plane witnesses**. Exact integer primitives and the source/domain
contracts are shared and explicitly disclosed; the verifier is not an entirely
independent implementation of every predicate.

| Whole-volume quantity | Parent | Benchmark candidate |
|---|---:|---:|
| Nodes | 4,181,299 | 4,181,300 |
| Tetrahedra | 12,967,519 | 12,967,526 |
| Cells with Frobenius condition at least `1e12` | 15,285 | 15,284 |
| Cells with condition at least `1e16` | 26 | 25 |
| Approximate maximum condition | `4.657541721488933e16` | `4.657541721481499e16` |

The actual worst source cell is removed, but the next one is nearly equal.
**There is no material global maximum improvement in this single-case trial.**
All 44 new cells have exact mean ratio at least binary64 `0.1`, implying
`kappa_F < 380` from `kappa_F² <= 144 / q³`.

Candidate SHA-256:
`fff534a14b9ddcfc37e8844c193852a7fdb2f28feae09e67b42be30621d42ad3`.
The whole-volume check covers every positive orientation, every used node,
8,218,458 exact boundary rows and 21,825,823 opposite internal face pairs.
A fresh complete condition census exactly matches mapped retained severe
values. The global minimum mean ratio remains approximately `1.2910e-11`, so
the absolute diagnostic quality gate still fails. The check does not establish
exhaustive full-volume intersection freedom.

## Replay and remaining gates

Executed Python sources are retained under [source](source/); do not edit their
hashed bytes in place. The actual Mac runtime is Python 3.12.11 with the existing
scientific environment. Scripts expose explicit input/output CLI arguments;
the private capsule retains exact commands, inputs, logs and running/terminal
receipts. Original OBJ, original printing-study master and unchanged calculation
3MF were rehashed after execution. No paid resource was used by this benchmark.

Qwen/CADAM remain auxiliary proposal tools and PicoGK/STEP remain geometry
authorities. Gmsh, OpenFOAM, CalculiX and Adamantine are not replaced by this mesh
certificate. Native volume readback, operator admission, converged correlated
physics, faithful editable CAD, specimen metrology, hidden passages, qualified
material/machine/process, physical inspection and engine validation remain open.
All physical release gates remain false; this is not a metal build file.
