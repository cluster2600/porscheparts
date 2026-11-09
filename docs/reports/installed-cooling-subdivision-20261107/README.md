# Installed cooling: exact surface subdivision

For [issue #452](https://github.com/cluster2600/porscheparts/issues/452), a
bounded longest-edge subdivision now preserves every retained source triangle
while reducing all surface edges below 5 mm. **This is a surface check, not an
admitted volume mesh. No flow solver ran in this experiment.** The installed
cooling geometry remains an uncalibrated layout, not a measured assembly.

This follows the [baseline and local-refinement rejection](../installed-cooling-mesh-diagnostic-20261107/README.md).
The [result](result.json) records inputs, numerical checks and private artifact
hashes. Original source coordinates, historical evidence and rejected trials
remain unchanged. No raw geometry is included here.

## Why change the subdivision order

The original indexed source has 45,906 vertices and 91,812 triangles. Its
longest edge is about 0.413 m, despite the requested 0.005 m meshing size.
There are 201 triangles with the descriptive quality measure
`4 sqrt(3) area / sum(edge_length_squared)` below 0.01; this measure is not a
new engineering acceptance threshold. A first fixed-boundary Gmsh trial failed
to finish within its 180-second bound.

CGAL 6.2.1's `split_long_edges` convenience overload does not compile with the
exact construction kernel in this installation: the uniform sizing field
returns `optional<FT>`, while the remesher expects `optional<double>`. A small
local sizing adapter resolved compilation without changing installed headers.
However, the algorithm defers new triangle diagonals until another pass. The
observed counts were 236,458, 681,458, 1,891,160 and 3,246,156 triangles across
four passes, exceeding the preset size guard. That failed implementation and
its logs remain private and hash-bound in the result.

The [replacement](split-longest.cpp) uses installed CGAL Euler operations and a
single queue ordered by exact squared edge length. It immediately queues each
new diagonal and half-edge, discards stale queue entries, and splits only at
exact midpoints. It carries the original triangle ID through every split.
There is no smoothing, collapse, edge flip, tolerance welding or projection.
The source and output coordinates are never used to invent physical dimensions.

The original one-million-vertex/two-million-face limit remains; the replacement
checks it before each split. The run had a 180-second deadline and a 4 GiB
sampled-RSS ceiling. It completed in 1.538 seconds with 208,969 vertices,
417,938 triangles and 105,627,648 bytes peak sampled RSS. These bounds apply to
this native subdivision run; independent read-only checks ran separately.

## Independent checks

The [Python reader](verify_exact.py) uses standard-library rational arithmetic
on the separately exported exact coordinates. It rereads every source and
output triangle and checks:

- Original vertices are exactly unchanged.
- Each child is coplanar with and contained in its named source triangle, with
  positive relative orientation.
- Summed oriented child area vectors equal each original area vector exactly.
- Every indexed output edge occurs once in each direction.
- Exported binary64 coordinates and exact rational coordinates lie inside the
  recorded certified coordinate intervals.

These checks pass for all 417,938 triangles and all 91,812 source triangles.
A separate outward-rounded interval calculation bounds every edge strictly
below 5 mm. Its largest squared upper bound is
`2.499990330653739e-5 m²`, below the inward-rounded squared limit
`2.4999999999999998e-5 m²`.

The rounded coordinates also pass the existing complete CGAL triangle-soup
intersection audit with zero pairs. Independent indexed topology finds one
connected component, 626,907 edges, opposite paired edge uses and circular
vertex links everywhere. There are no duplicate coordinate vertices or
zero-area triangles. The signed volume is approximately
0.03196966878395933 m³. Numerical rounding bounds are not physical tolerances.

A unit cube and a slender 3 × 0.01 × 0.2 synthetic box pass the rational checks;
the replacement produces 192 and 2,056 triangles respectively. The unchanged
reader rejects controls with an invalid parent ID, moved vertex or reversed
face. The earlier adapter's cube result, retained in `cube-verification.json`,
has 240 triangles and is not the replacement's 192-triangle result.

Skinny triangles remain: 8,065 subdivided triangles have the descriptive quality
measure below 0.01. Longest-edge subdivision establishes a length bound and
source preservation; it does not establish acceptable tetrahedral quality.

## Bounded tetrahedral trial

Gmsh 4.15.2 received the checked subdivided surface with source patch labels
inherited through the parent IDs. Its 5 mm minimum/maximum size, two-thread
setting, `MeshOnlyEmpty=1` and other options were unchanged from the prior
trial. The worker refused to start without the independent exact check.

The new trial reached its 180-second deadline (180.514 seconds observed) and
was terminated, returning -15. Peak sampled RSS was 1,766,162,432 bytes, below
the unchanged 4 GiB bound. No `.msh` output was produced. The log reported
16,719 added Steiner points and points on surface 1 during boundary recovery;
without an exported mesh, boundary preservation could not be verified. No
native volume-quality check or flow solver ran. The failed attempt and complete
log remain private with hashes in the result. Its settings were not tuned or
its deadline extended.

## Reproduction and remaining gate

Compile the source with CGAL 6.2.1, GMP and MPFR using C++20 and `-O1`.
The CLI takes `INPUT.bin OUTPUT_PREFIX MAX_EDGE`. Its private binary input is
`M64TRI1\0`, two little-endian uint64 counts, binary64 XYZ vertices, then uint64
triangle indices. Outputs are the same indexed binary format, uint64 parent
IDs, exact rational coordinates and binary64 interval endpoints. Existing
output paths cause refusal. Run the independent reader with
`python3 verify_exact.py INPUT.bin OUTPUT_PREFIX`.

The required next gate remains a volume mesh preserving boundary semantics and
passing the unchanged standard and extended native quality checks. Neither
surface subdivision nor software controls qualify flow convergence, mesh
independence, installed heat rejection or manufacturing.
