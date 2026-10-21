# Smallest scalar-to-enclosure route — held proposal

**Yes, under CGAL5.6's documented absolute-error software guarantee**
`|s−h|<=epsilon`, report `[max(0,s−epsilon), s+epsilon]`. This follows without
calling s a lower bound. In exact arithmetic its width is at most2epsilon;
epsilon<=0.00005mm therefore preserves the unchanged0.0001mm gap requirement.
The [official5.6 declaration](https://doc.cgal.org/5.6/Polygon_mesh_processing/group__PMP__distance__grp.html)
and [version-pinned implementation](https://github.com/CGAL/cgal/blob/de4fa0d7d57b5a997012f2804161386ff4bc0d0f/Polygon_mesh_processing/include/CGAL/Polygon_mesh_processing/distance.h)
are the authority, rather than a newly assumed one-sided scalar error.

For one future frozen implementation, epsilon=gap/4=0.000025mm is a simple
**proposed stricter API parameter**, leaving margin for outward binary64 endpoint
rounding. It changes neither geometry nor the0.0001mm admission gap/0.0625mm
budget. Root may instead choose epsilon<=gap/2 with explicit endpoint/gap
refusal. In every case: form conservative endpoints, require finite ordered
values, verify actual stored upper−lower<=0.0001mm, and accept the polygon budget
only if upper<=0.0625mm. Never clamp a too-wide interval or use s alone to pass.
No parameter or query is authorized here.

## Source-checked stopping behavior

Private pinned distance-v5.6.h b007e6df… lines2508–2540 takes const meshes,
requires nonempty triangle meshes and passes distance-threshold−1. Thus the
boolean threshold early exits are disabled in this estimation call (internal
traversal014234cd… lines590–603 only enables them for a positive threshold).
With match_faces(false) on **both** named-parameter sets, preprocessing inserts
all source faces and **all complete target faces** (distance.h1411–1416); it
cannot replace the1.8million-face target by a patch.

The global criterion is approximate_sqrt(upper)−approximate_sqrt(lower)<=epsilon
(line1553). Per-face pruning uses the same epsilon/local width or an upper bound
below the known maximum. Equal nearest target faces at all three corners allow
an exact triangle-distance stopping case in the algorithm. There is no separate
user/default per-face relative tolerance, sampling quota or max_factor. An
optional closed-mesh enclosure shortcut is only a TODO, not a prerequisite.
The source's epsilon² initial accumulator means near-zero distances can yield
s=epsilon; this is why `[s,s+epsilon]` is invalid generally.

The return still passes through approximate_sqrt/to_double. The documentation
provides an algorithmic absolute-error guarantee, **not a separately returned
certified pair or a directed-rounding certificate**. Exact kernel arithmetic
cannot itself certify that final conversion. Outward endpoint rounding protects
the wrapper's additions/subtractions, not an unproved error inside CGAL. An
actual valid software enclosure may be reported at that explicitly limited
level; a stronger roundoff/CAD certificate remains false. Installed-header
identity, compilation and literal witnesses are still prerequisites.

## Exact minimal fixture proposal

Use the complete closed unit cube [0,1]³,12 outward triangles, as target. Let
T(z) have ordered points(1/4,1/4,z),(3/4,1/4,z),(1/4,3/4,z). All source points are
at least1/4 from vertical sides; for0<=z<=1/8 the nearest target face is bottom.

- T(0): true directed distance0; enclosure must include0 despite the error floor.
- T(1/32): true distance1/32 everywhere, with an open source and closed target.
- T(1/32) union T(3/64): true supremum3/64; validates source-union maximum.
- T(1/8): true distance1/8; its valid enclosure must reject the0.0625mm budget.

The reverse cube→T direction is different (top points are at least1−z away),
so the fixtures must check directed semantics explicitly. Also refuse empty,
nonfinite or degenerate inputs before CGAL; retain deadline/memory-stop outcomes
and complete input immutability. These are planned analytic fixtures, not
observed results. The actual8976-cap source selection must stay byte-exact and
full original target intact. A cap interval alone does not complete reverse:
the5426 noncap part and exact union proof are still required. New CGAL reports
cannot be passed through the frozen58a-specific combined assessor unchanged.
