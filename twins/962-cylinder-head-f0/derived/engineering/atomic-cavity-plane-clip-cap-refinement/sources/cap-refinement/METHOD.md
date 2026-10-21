# Cap-only interior-point experiment — source preparation, unrun

This adapter tests whether installed CGAL 5.6 Mesh_2 can improve a mapped planar annulus by inserting only interior points. It is a new numerical representation hypothesis. It is not a full-head repair, an accepted surface, a volume mesh, or physical qualification. No native compilation/refinement or unit test has been executed in this preparation. The literal fixture writer performed standard-library data construction only; its fresh-output guard now preserves those inputs.

## Interface and original-coordinate meaning

`cap-refine cap.bin old-to-keeper.u64 fixed-face-ids.u64 fresh-output-directory`

The three inputs have no additional wrapper/header beyond the existing cap codec:

- `cap.bin`: `962SURF1`, little-endian counts, binary64 XYZ and uint64 oriented triangular faces. Input is a connected planar negative-Z annular cap at exact z=0; every input vertex belongs to one of its two boundary cycles.
- `old-to-keeper.u64`: raw little-endian uint64 pairs `(local original vertex ID, local keeper ID)`, sorted uniquely by source ID. Keeper identity rows are accepted and counted separately from contractions. Omitted IDs map to themselves. Bounds and the completed map's idempotence are mandatory. Every nonidentity contraction must remain on the same original cycle and avoid vertices of fixed cap triangles. This is a function, not an edge list; `a==b` is valid.
- `fixed-face-ids.u64`: sorted unique raw little-endian uint64 local original face IDs. The adapter preserves each selected triangle, its coordinate bits and winding exactly. Separate external local-to-head vertex/face provenance arrays are not inputs to this cap-only program.

The completed head map and cap subset are pending separate byte-verified delivery. Their counts and geometry are not inferred from telemetry or used by this preparation. Runtime selection must verify little-endian execution and bind all actual inputs before any native call.

## Exact domain, fixed cells and no-edge refinement

Existing project codec, triangle quality, oriented chain and complete vertex-link/edge/loop complex functions are reused as recorded in `source-reuse.json`. The codec's closed-surface predicate alone is removed for this open cap. No prior SMS/atomic main is included or called. The preserved prefix still includes unused project AABB/remesh declarations; no previous remeshing algorithm is instantiated or invoked by a preserved main.

The completed map must leave two simple, disjoint, properly nested cycles with the original outer negative/inner positive winding. Every boundary segment and every edge of every fixed triangle becomes a constraint in an EPECK CDT with the no-constructed-intersection tag. Exact fixed triangles must appear as individual CDT cells. The mutable domain is explicitly marked as annulus minus those cells before `init(true)`; internal fixed edges are not treated as parity toggles. The exact constraint endpoint-ID set and exact fixed-cell set are rechecked after refinement.

The installed `Delaunay_mesher_no_edge_refinement_2` uses `Delaunay_mesh_size_criteria_2(0.125, 0)`: the standard shape bound and disabled size bound. Each `try_one_step_refine_mesh()` call is counted separately as one insertion or no insertion. The adapter does not separately instrument why a request was discarded. Installed `Do_not_refine_edges` discards requests outside a marked face or encroaching constrained edges; queue exhaustion therefore does not prove all requested shapes were repaired. An independent recensus of active CDT faces reports criterion failures before and after. That criterion is evaluated on the exact-construction CDT with the installed double-valued quality evaluator; it is separate from the final rounded embedding's q>=2/29 gate.

No angular relaxation, boundary subdivision, coordinate grid, extra size cutoff, or automatic retry is introduced. A later root-authorized owned controller must impose bounded resources/time externally; this preparation creates no runner or execution authority.

## Rounded output and provenance

Retained points are copied from the original binary64 Point_3 values, including their exact stored bits. New exact XY coordinates are explicitly materialized with `CGAL::exact` before `to_double`; the resulting binary64 embedding is approximate, with no nearest-rounding claim, and z is set to zero. New coordinates must remain strictly inside the annulus, off every constrained segment, and distinct numerically and by full coordinate bits. They receive UINT64_MAX as the local original-vertex provenance sentinel. Every fixed cell retains its local original face ID; all other cap triangles receive UINT64_MAX.

After conversion, the adapter reconstructs the complete cap and checks finite coordinates, negative-Z nondegenerate winding, no duplicate/orphan points or duplicate faces, complete oriented edge and vertex-link topology, one component/Euler 0/two cycles, exact mapped boundary, all fixed triangles, exact mapped area and self-intersection absence. Every output face must pass both the existing scalar q>=2/29 comparison and the exact stored-coordinate equivalent `2523*det^2 >= (sum squared edge lengths)^2`. The mapped area is permitted to differ from the original area; both are reported. These cap-only gates do not establish the full assembled head's normals, neighborhood guards, local envelope, global intersections, scoped features, complete bidirectional distance or tetrahedral SICN>=0.1.

## Literal fixtures and result interpretation

The four exact synthetic cases are declared in `fixture-expectations.json`: ordinary annulus with a fixed cell and identity map row; a larger annulus intended to request refinement; invalid fixed association; and a map collapsing a loop to two unique vertices. The larger case deliberately has no reserved success or Steiner count: RC0/RC3, zero insertions and all refusal counters must be preserved truthfully. All positive results require full saved-array inspection rather than a guessed CDT diagonal or point count. `test_literal_contract.py` is prepared and unrun; it uses only the standard library.

RC0 exports `cap-candidate.bin`, `vertex-coordinate-origins.u64`, `face-source-ids.u64` and `report.json` only after cap guards pass. RC3 is a geometric refusal with a report and no candidate/provenance files. RC2 is invalid data or execution/I/O error and provides no acceptance; partial output after an I/O error must be quarantined, not accepted. Any zero/default counter before its reported stage is unobserved, not a credited pass. `CGAL_CDT_active_shape_criteria_satisfied` refers only to the separately recensused active CDT criterion, not manufacturing quality. All full-head/solver/manufacturing flags remain false.

## Primary-source and licence scope

The actual nine installed Mesh_2 header bytes were captured privately from the never-started immutable CGAL image, then the owned container was removed. Their exact hashes and the capture receipt hash are retained in `installed-headers.json`. Their GPL-3.0-or-later OR commercial licence notices govern the Mesh_2 implementation; this preparation does not redistribute those headers. Project helper blocks retain repository provenance. This source/API preparation does not attest an unexecuted compiled binary or a successful refinement.
