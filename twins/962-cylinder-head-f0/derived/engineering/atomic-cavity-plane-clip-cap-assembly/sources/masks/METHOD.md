# Held unequal-count exact coordinate source masks

This source-only preparation compares the complete original `894ece6e…`
(902,145 vertices / 1,804,706 faces) with the assembled `9d62eac6…`
(871,731 vertices / 1,743,878 faces). The original is
`analysis-envelope-025-003/exact-input.bin`. The representation budget remains
0.0625 mm for any future independent two-sided CUB check. No masks, distance
query, CUB controller, scientific array read or geometry export has run here.
The held contract has both authority fields false and runtime fields null.

`prepare_masks.py` copies `read`, `digest` and `coordinate_faces` exactly from
the existing audit sources, as recorded in `source-reuse.json`. The existing
coordinate function requires finite nondegenerate triangles, normalizes only
signed zero, then rotates each triangle cyclically to its lexicographically
smallest coordinate vertex. It preserves winding. Complete 72-byte binary64
coordinate keys are built in 65,536-face chunks; no quantization, grid, sample,
tolerance or vertex-origin correspondence is used. New UINT64_MAX origins are
never dereferenced. Reversal is deliberately not cancelled.

Each complete key array must have no duplicate oriented coordinate triangle.
Duplicate multiplicity causes a refusal before output, rather than silently
using set cancellation. With uniqueness established, `intersect1d` finds the
complete key intersection and both source indices. Each cancelled key occurs
exactly once in each full surface. Separate masks and complete complementary
source-ID arrays have each source's own length and are read back after saving.
Every unshared source face remains in its direction's query. Both proposed
query configs keep the complete opposite surface as target. The unchanged CUB
worker accepts those unequal source masks; its old equal-count partition helper
is not used. This preparation does not create a CUB execution controller.

If A = S union A_changed and B = S union B_changed, every triangle in S has
zero distance to the complete opposite surface. Consequently each directed
supremum is max(0, its own changed-source-to-complete-opposite-target supremum).
This is a conservative exact reduction, not a fragment-to-fragment comparison.
No distance bound is established until separately reviewed native queries and
interval assessment finish.

Four tiny tests are prepared and unrun: unequal counts plus duplicate refusal,
cyclic row/order equivalence, winding reversal, and signed-zero equivalence
without rounding a one-bit positive coordinate change. Input/source/interpreter
pins and NumPy version must be bound in a separately reviewed authorized child.
The script claims no hard OS memory/CPU quota or external watchdog. Root must
supply its normal bounded launch for the mask preparation. Existing or partial
output is preserved and prevents automatic retry.

Topology, intersections, neighbors, feature identity, volume quality, solver,
physical and manufacturing admission remain separate and false. Original
proofs and source files are immutable and have not been changed.
