# Held generation of the specific apex1435493 cavity

This is source preparation only. No mesher, scientific import, prepared function,
test or geometry operation was executed here. The held contract grants no
execution authority, reserves no output, and has no actual-child identity.

The sole prospective input is the frozen local shell `a6f15db6…`: 16 source
coordinate rows and 28 oriented triangles, with local tags 1–16 and face tags
1–28. The excluded old apex is 1435493. Its original complete star contained
28 cells. The exact-pair certificate `160dff41…` obstructs movement of that one
apex under the old fixed connectivity; it does not prove remeshing infeasible.
The saved shell and exact face screen establish closure and necessary face
quality only. Global completeness is inherited from the frozen census, not
recomputed from a head MSH by this caller.

The old source has nine boundary and seven interior shell nodes. All 16 would
be fixed nodes on the boundary of this separately declared cavity-generation
study. That new local policy neither changes their original classifications nor
authorizes a head repair. Local-to-global rows are retained; generated interior
tags have no claimed correspondence to old head nodes.

The construction reuses the now-tested seven-mm cube generation path:
`addDiscreteEntity(2,1)`, exact nodes and TRI3 rows, one surface loop and volume,
then exactly one `generate(3)`. Every `mesh_head.py` option is unchanged:
Algorithm3D 1, MeshOnlyEmpty 1, renumbering and both optimizers off, linear
elements, two requested threads, binary MSH 4.1. There is no Netgen,
`createGeometry`, optimizer, solve, fallback or automatic retry.

The cube-specific bounds and volume inspector are not reused for this irregular
cavity. The caller loads the bound generic `mesh_head.py` module without calling
its worker or reading its head inputs, and uses its unchanged `volume_arrays`,
`tetra_volumes`, `tetra_boundary`, `canonical_oriented` and `array_sha`. It
extracts only a326's unchanged `internal_face_orientation` definition, avoiding
that module's head-specific top level. The unchanged 97b7 canonical,
distribution, snapshot, exact comparison and quality-gate definitions are
extracted into the same helper namespace; `arrsha` aliases generic `array_sha`.
The helper AST identities and caller differences are recorded in
`source-reuse.json` and `source.diff`.

Before any mesh call, stdlib/Fraction checks require the exact mapping, binary64
coordinate words/bytes, original nine/seven classification split, all oriented
faces, paired edges, nondegenerate triangles and exact old enclosed volume.
That exact volume is 1450956179458166404046894365859946143854307 /
522673715590561479879743397015195972796416 mm³. Generated and native volume
sums each use the existing relative numerical bookkeeping bound of 1e-6;
passing that bound does not assert exact equality of computed floating sums.

The complete generated audit requires finite distinct nodes, positive unique
tags, no orphan nodes or duplicate cells, linear TET4 only, all three native
metric arrays with exactly one row per cell, positive signed/native volumes and
Jacobians, exact oriented tetrahedral exterior, and opposite internal faces.
All 16 boundary coordinate bytes (including signed zero), tagged oriented TRI3
faces and native entity classifications remain exact. Every new node must be
classified on a volume; counts and coordinates are dynamic. All coordinates,
cells, three native metrics and signed volumes are exported in `arrays.json`.
The saved MSH is reopened and every array, classification and metric is
compared byte-for-byte with the generated state. The unchanged SICN gate is
minimum 0.1 over every generated cell. A procedural success with poor SICN
preserves the MSH and arrays and returns rejection.

These audits do not perform global self-intersection, tetrahedron overlap or
point-in-cavity containment tests for this irregular shell. Positive cells,
matching boundaries and volume bookkeeping are not substitutes for those
checks. Even a completed local SICN pass would be a generation observation;
stitching, full-head conformity/intersection/quality audits and any engineering
or physical admission remain separate and unauthorized.

The controller is the tested fixed-shell cube controller with three descriptive
label changes only. Its ownership, SIGTERM, timer, sample limits, kill/wait,
handler restoration and final refusal logic are unchanged: 30 seconds, sampled
1 GiB RSS, sampled 16 MiB output, two requested threads. These are not hard OS
CPU or address-space limits. Full arrays are retained without sampling; the
output limit may stop a larger generation. Operation declarations in the
controller are distinct from worker attempt counters.

Six new stdlib/AST shell guards and 14 selected mocked-controller methods are
prepared and unrun. Root must review these sources, run those guards, freshly
verify the selected three native identities and exact NumPy origin/module
bytes, resources and sole-worker state, then separately freeze a reviewed
actual child and fresh output. Runtime metadata is a selected identity scope,
not complete package, import, build, OS or ABI closure. The root independent local-map check `e56fd3fa…` is available for exact-child
binding; its author did not issue a duplicate independent peer for his own map.
