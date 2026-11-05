# Convex predicates and local hole normalisation

These two helpers are separate from the frozen sources of previous generations.
They modify no mesh, schedule or admission threshold.

`CompiledConvex(vertices)` in [exact_convex_halfplanes.py](exact_convex_halfplanes.py)
validates an oriented convex boundary in `Fraction` coordinates, then compiles
its half-planes into integer coefficients. `contains(point)` includes the closed
boundary; `contains_triangle(triangle)` checks the three vertices of a triangle of
strictly positive area. No point is rounded. When the positive triangulation
is already certified, three calls to `contains` avoid repeating that validation.

The [comparison receipt](compiled-convex-results.json) covers the **same
768 candidate pairs**, that is 102 triangles and 95 convexes from the existing witness.
All answers and the first convex identities are identical to
those of the generic rational predicate. Over three repetitions, the
three-point search drops from 50.67 to 2.61 ms median; compilation takes 15.99 ms,
a gain of 2.72 including compilation on this small witness. This is not a
measurement of total generator time. The helper has not been integrated into a job
already launched.

`normalize_holes(result, primitives, allowed)` in
[exact_intended_holes_v2.py](exact_intended_holes_v2.py) reuses the frozen
rational partitioner, verified by its SHA. It can examine a self-intersecting or
non-convex hole, but keeps a valid exterior. The proposed hull is certified
by its original vertices and all its closed half-planes. Every segment of the hole
therefore lies entirely within this hull, by linearity. The hole is removed only
if the **entire hull** is covered by the intended union and by `allowed`.
A hole without a certificate is kept; an invalid final result is refused.
The reconstruction reuses the coordinates of the exterior and of the retained holes,
then checks their exact equality. No new vertex, `buffer` or `make_valid`
is used. The receipt binds each primitive, `allowed`, the input and the result
by their WKB SHAs.

The [real source008 witness](hull-hole-evidence/source008-inputs.json), itself bound
by its SHA in the test, contains two holes, one of them self-intersecting. The
[compact replay](hull-hole-evidence/results.json) keeps the hull proofs,
the identity of the result and a rational counter-proof of the final check.
Both holes are removed with a certificate, the exterior stays identical and
the polygon becomes valid. `D ⊆ R` and `R ⊆ allowed` pass.

**Final containment of this R within the exact intended band remains
REFUSED.** The first refused triangle keeps a strictly positive uncovered area
of about `2,00646e-22 mm²` (2.00646e-22 mm²), with its rational value and the witness
cells kept. Normalisation alone succeeds; this support region is
not admitted. The final inclusions remain mandatory at the caller.

The raw replay evidence is kept under
`work/carrier-process-20261016/intended-holes-v2-002/`, with their SHAs in the
compact receipt. No support generator or native computation was rerun.

Targeted check from the repository root:

```sh
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  work/part-workflow/runtimes/pyslm-coverage-011/env/bin/python -B -m unittest \
  tests.test_carrier_exact_convex_halfplanes tests.test_carrier_intended_holes_v2 -v
```

The 15 tests pass: orientation and closed boundaries, non-dyadic fractions,
positive sliver without epsilon, invalid inputs, immutability, real
equivalence, genuine or partially covered holes kept, falsified hull
refused, coordinate preservation and source008 capture. Witnesses that
require Shapely are skipped when that optional runtime is missing.
