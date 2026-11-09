# 935: refine the obstructing construction cap without moving its contour

The isolated cap surface now passes complete local topology, projected
intersection, correspondence and face-quality checks. Its 277 original contour
points and edges remain literal. Adding 8,125 interior mesh nodes removes its
one forcing triangle and all 35 face-quality warnings. This is a checked
**numerical surface proposal**, not an integrated cylinder-head volume, faithful
editable CAD, physical metrology, qualified printing job or functional part.

This increment continues the
[current volume and cap obstruction](../935-global-quality-continuation-20261107/README.md).
It does not change that volume, the original acquired scan or the supported
printing-study assembly. The complete objective and its six engineering gates
remain open. The [phase ledger](phase-ledger.json) covers those pending phases;
it does not claim their commands or inputs are prepared.

## Source admission and limits

The cap belongs to the earlier
[bare-head construction hypothesis](../935-bare-head-hypothesis-20261105/README.md),
not an observed hidden gallery or measured mating surface. The original driver
derives provisional clipping planes from source fits, with 0.75 nominal mm of
machining stock. CGAL clips using exact constructions, then exports binary64
coordinates. A subsequent rigid transformation also uses binary64 arithmetic.
The historical construction sources are
[run_clip.py](../935-bare-head-hypothesis-20261105/source/run_clip.py),
[clip_head.cpp](../935-bare-head-hypothesis-20261105/source/clip_head.cpp) and
[prepare_aligned.py](../935-bare-head-hypothesis-20261105/source/prepare_aligned.py).
They remain unchanged.

All points in the three immediate witness quadrilaterals have unique bitwise
ancestors in the original aligned hypothesis. Recomputing their source rigid
transform gives zero stored-coordinate difference in this execution. The
source fit is `back_face_candidate`; its physical datum remains unaccepted.
Their largest L1-normalised source-plane residual is bounded above by
1.847e-14 nominal mm. This algebraic residual is **not a Euclidean metrology
tolerance** and does not establish the cause of every noncoplanar point.

The [earlier exact same-surface test](../935-global-quality-continuation-20261107/README.md)
correctly refused all three quadrilaterals as noncoplanar. The present study
explicitly tests a different, bounded graph representation. No point is
silently projected or snapped, and literal old cap triangles are not promised
for a future integrated candidate. Such a candidate needs a new complete
boundary/domain contract; the old volume's immutable-cap rule is not relaxed
in place.

## Executed sequence

1. Rehash every consumed frozen input and bind the current witness, surface,
   source construction, exact metric helpers and runtime in private jobs.
2. Test the three local diagonals with exact rational projected-convexity,
   graph-deviation, normal and face/tetrahedron metrics. All satisfy the small
   graph bound, but all new face pairs fail the existing warning floor. The two
   two-tetrahedron alternatives also fail the mean-ratio floor. None is applied.
3. Extract the complete edge-connected cap containing the witness. Run one
   constrained, strict exact-incircle Lawson pass on the existing point set.
   Independently enumerate all 551 edges using permutation determinants, rather
   than the constructor's translated incircle formula.
4. Run one Gmsh 4.12.1 Frontal-Delaunay refinement with added interior points.
   Preserve each contour curve as its two endpoint nodes. Point mesh size is
   the minimum adjacent contour-edge length; algorithm 6, one thread and zero
   smoothing are fixed before execution. There is no tolerance/algorithm sweep.
5. Lift added points onto an affine graph defined by an existing cap triangle,
   rounded to binary64. Restore all original 3D point bits. Independently check
   the entire proposed surface against the original cap and current source.
6. Reopen the actual binary native MSH in a fresh process. Join all planar node
   coordinate bits and all cyclically oriented triangle indices to the lifted
   proposal. Do not accept a count-only or reordered-orientation match.

The Lawson certificate finds 277 boundary edges, zero constrained interior
edges, 28 nonconvex interior patches and 246 convex strictly legal diagonals.
There are no cocircular ties and no available strict Lawson flips. This covers
this point set and this criterion; it does **not** exclude other criteria or
meshes with added points. The subsequent refinement demonstrates that adding
points resolves this particular surface obstruction.

## Measured results

| Check | Original cap | Refined cap |
|---|---:|---:|
| Vertices | 277 | 8,402 |
| Triangles | 275 | 16,525 |
| Literal contour points / edges | 277 / 277 | 277 / 277 |
| Faces forcing any incident tet below q=0.01 | 1 | 0 |
| Faces below q_face=0.01 warning | 35 | 0 |
| Minimum exact q_face squared, shown as binary64 | 2.618505769423931e-7 | 1.598074406390039e-4 |
| Connected components / Euler characteristic | 1 / 1 | 1 / 1 |
| Complete projected intersection pairs | 0 | 0 |

Every projected old and new triangle has strictly positive exact area. The
refined mesh is a connected vertex-manifold disk, has consistently paired
interior edges and the identical oriented outer contour. Every mapped marked
edge on this cap is preserved. Complete libigl predicate checks cover both
projected triangulations, with shared-simplex negative and coplanar-overlap
positive controls. This establishes their common projected polygon for the
graph correspondence; it is not a complete-head intersection check.

Relative to one common affine graph, each old and new interpolant stays within
its vertex residual range. The range over their union bounds their vertical
separation everywhere on the common polygon. Exact rational arithmetic gives
an outward binary64 bound of **1.1275324656258362e-13 nominal mm**. Composing
this with the preceding complete hypothesis correspondence gives
**0.00964321537478613 nominal mm**, below the unchanged 0.01 limit. Neither
number measures deviation from the acquired scan or establishes physical scale.

The actual binary MSH readback joins all 8,402 node coordinates and 16,525
oriented triangles. The checked lifted-cap NPZ SHA-256 is
`662b86fbab7b30499c4fa4d50508a9a52ef995cf66eb9a6e3bbdb1d4a6db6036`.
The native MSH is planar input/provenance for this cap study; the NPZ carries
the lifted 3D surface. Neither is an engine manufacturing file.

## Reproduction and retained failures

Sources are in [source/](source/audit_bounded_cap.py):

- [Local source/diagonal diagnostic](source/audit_bounded_cap.py).
- [Constrained point-set triangulation](source/retessellate_cap.py) and its
  [independent fixed-point certificate](source/certify_cap_fixed_point.py).
- [Native refinement](source/refine_cap.py),
  [independent complete cap checker](source/check_refined_cap.py) and
  [native readback](source/check_cap_msh.py).

Each CLI takes `--job PRIVATE_JOB.json --output NEW_DIRECTORY`. Private jobs
bind actual input paths and hashes, commands, runtime binaries, Gmsh module and
library where applicable. All work uses existing isolated Mac runtimes and the
existing 600-second, 4 GiB bounded controller. The private capsule retains every
job, pre-execution ledger, log, source snapshot, exact selector, actual MSH and
derived cap arrays. [results.json](results.json) publishes aggregate checks and
hashes; proprietary geometry and selectors stay outside Git.

Four portable unit tests cover the graph formula, constrained Lawson example,
independent determinant signs and orientation-preserving native join. Additional
literal native/predicate controls run through the real Gmsh/libigl paths before
the head-cap cases. The controller's sampled child RSS values are observations,
not guaranteed process peaks.

The initial native square check stopped before head execution because NumPy
2.5 no longer accepts 2D `np.cross`. The final source uses the explicit 2x2
determinant. An actual ASCII MSH then failed the complete coordinate-bit join;
binary-double serialization passes. The final lifted-cap NPZ and every array
are byte-identical to the independently checked pre-serialization proposal, so
its geometric certificate applies unchanged. Both failed executions remain in
the capsule. Zero-context [v1](source/refine-cap-v1.diff) and
[v2](source/refine-cap-v2.diff) patches reconstruct those earlier sources from
the final refiner. Two preparation-only Python compatibility errors are also
recorded; neither started a numerical head job.

Local `make check` passed: 5,860 main tests, 421 skipped, including the four
new portable tests. The 77-payload-file private capsule (3,672,404 bytes) is
frozen; every payload was rehashed after permissions were made read-only. Its
manifest hash and final validation summary are in [results.json](results.json).

## Remaining work and resource accounting

The full current head still has 12,952,857 tetrahedra, 439 severe-condition
cells and 83 nonpositive native minSICN values from the preceding admission.
None of those counts is upgraded by this surface-only result. The new cap has
not been substituted into that volume or the printing-study assembly. No new
head field solve, full-head intersection check, volume partition/overlap proof,
physical calibration, functional CAD acceptance, process validation or physical
print has been completed here.

Next, bind the checked cap to a separately versioned complete boundary, verify
its joins and full intersections, then construct a conforming replacement
volume. Recheck every volume/native metric and source constraint before any
field solve. Other cap obstructions and all remaining cells need their own
admission. The newly added surface points do not imply that a conforming volume
with acceptable quality already exists.

New Vast expenditure is **$0**; no cloud resource, container or supplier message
was created. The existing $35 total cap, $30 compute ceiling and $5 closure
reserve remain unchanged. The earlier conservative $15.67884277510534 allocation
is not a provider invoice. Original scan, printing master and current full
volume hashes were rechecked unchanged. Physical/material/machine qualification
and professional review remain necessary before functional metal release.
