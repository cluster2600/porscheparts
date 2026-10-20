# Held complete degree4–8 seed-edge removal source

This is an unrun source proposal for one finite route: remove each of the 55
saved complete degree4–8 central-seed edges in turn, keep every coordinate word,
and screen every abstract link-polygon triangulation. No candidate is selected
or applied. The earlier 19 empty segments exclude only those segments. The
accepted 204-row flip refusal excludes only its finite 2↔3 family. Neither result
proves global infeasibility or a necessity to change topology.

`propose_saved_edge_removal.py` is an editable pure function module, with no
entry point, file IO, dynamic import, geometry writer or launch authority. A
future reviewed caller must perform exact input pin checks before and after
calling it. No source/helper/fixture, real context, determinant, quality,
triangulation or certificate evaluation was executed during this preparation.
Only source text/AST and saved non-geometric identity metadata were inspected.

## Exact finite scope and link construction

The unchanged intake checks the accepted 271-node/499-cell/24-poor/16-seed
context, including all good and shared cells, the complete source classification
rows, and the prior 66-node/1,983-cell/86-improvement history. The source embeds
the 55 saved edge IDs/degrees copied from the frozen reason-accounting metadata:
21 degree4, 17 degree5, 6 degree6, 7 degree7 and 4 degree8. It independently
derives all poor-cell edges containing a complete-star seed from connectivity
and requires exact agreement with these identities. Outside-degree rows remain
in the output; the earlier degree3 route is not silently reclassified.

For an edge {u,v}, every incident owner must contain both endpoints. Its two
other vertices define an undirected link edge. The link must have n distinct
edges, n vertices, degree2 at every vertex and one connected closed traversal.
The canonical traversal starts at the smallest tag and follows its smaller
neighbor. This chooses a combinatorial cycle, not a projected geometric order.
No partial owner subset or guessed outside owner is used. Owner completeness
comes only from the accepted complete star of a seed contained in the edge.

For each valid cycle, root-edge Catalan recursion enumerates every triangulation
of the abstract n-gon once. The exact counts are 2, 5, 14, 42 and 132 for n4–8.
The conditional family bound is 1,033. An invalid link retains a complete
refusal row and produces no invented disk. Each disk has n−2 triangles; coning
it to u and v produces 2(n−2) tetrahedra using existing words only. Every
triangulation is retained, including all failed geometric/quality alternatives.
No random grid, ratios, point displacement, optimizer or subset search exists.

## Local embedding certificate and its proof obligations

The local certificate is deliberately restricted to strictly convex cavities.
It is not derived from positive SICN or volume equality alone.

1. A simple link cycle C validates the old abstract complex [u,v]*C as a finite,
   compact, orientable connected triangulated 3-ball. Its boundary is the
   combinatorial sphere u*C ∪ v*C, with exactly 2n distinct triangular faces.
   Every old tetrahedron must have its original strictly positive determinant,
   and every internal face must occur exactly twice with opposite orientations.
   Original orientations are never repaired. The actual old boundary must equal
   that complete cone-cycle sphere, with no extra or omitted faces.
2. For each outward boundary face (a,b,c), every other one of the n+2 cavity
   vertices x must satisfy det(b−a,c−a,x−a)<0 exactly. Every face is nondegenerate
   because it belongs to a positive old tetrahedron. The hull is full dimensional.
   Each of the 2n triangles is a distinct exposed triangular hull facet: no
   other vertex lies in its plane. Every vertex is consequently extreme. A
   convex 3-polytope with V=n+2 vertices has at most 2V−4=2n facets, by Euler's
   relation and the fact that each facet has at least three edges. These 2n
   facets therefore exhaust the hull boundary. The distinct labeled facets and
   their cycle-sphere incidence give a bijective boundary map, including edges
   and vertices. Failed or zero supports leave the strict-convex certificate
   unresolved; they do not prove overlap or general infeasibility.
3. A disk produced by the complete Catalan recursion is a triangulated 2-ball.
   Its suspension by the distinct vertices u,v is a triangulated 3-ball. The
   source requires membership in this exact finite family, 2(n−2) cells,
   opposite orientations at every internal face, and exact equality of the
   entire oriented boundary chain to the old boundary. Candidate cells may
   be ordered to positive orientation, but every final determinant must be
   strictly positive. Thus the map is nondegenerate and preserves a consistent
   orientation of the abstract ball. Its vertices lie in the same convex hull.
4. These verified assumptions allow the simplicial global-inversion theorem to
   conclude that both the old ball and the replacement ball map bijectively
   onto this same convex cavity. This addresses lower-dimensional improper
   contacts as well as positive-volume overlap; an informal volume-only or
   almost-everywhere multiplicity argument would not suffice. The precise
   primary result is Theorem1, with the finite compact orientable connected
   manifold-mesh assumptions in Section2, in [Y. Lipman, *Bijective Mappings of
   Meshes with Boundary and the Degree in Mesh Processing*, SIAM J. Imaging
   Sciences 7 (2014), DOI10.1137/130939754](https://arxiv.org/pdf/1310.0955),
   arXiv1310.0955v2, pp2–3 and proof pp9–10.

The source therefore does not assume that the old star is embedded merely
because its cells are positive. No nonconvex extension, general intersection
engine or pairwise whole-head SAT computation is added. A future nonconvex
route would need a separately reviewed rigorous certificate.

## Unchanged exact gates and complete conflict evidence

The donor `exact_quality` kernel is byte/AST unchanged. Every replacement cell
must satisfy D>0 and Q²≥1/100 exactly in rational arithmetic on the original
binary64 words. Q is the same ideal-reference inverse-Frobenius SICN metric;
the equivalent identity is Q²=36D²/(S T), where S is the sum of the six squared
edge lengths and T is the sum of the four squared face-cross norms. No tolerance
or quality relaxation is introduced. Old cells need positive orientation; they
include the known poor cells and are not required to pass the replacement gate.
Exact old/new signed-volume equality remains a separate checked invariant.
The old six-face assumption is replaced by the full 2n-face boundary test.

Every candidate records all final ordered cells, determinant/quality rational
witnesses, complete boundary and volume, all reasons, within-proposal duplicate
four-sets, duplicates of unchanged observed cells, and newly introduced edges
and faces with observed complement owner sets. A new feature containing a
complete-star seed has complete saved owner coverage; otherwise outside owner
absence remains unavailable. Every observed introduced-feature owner causes a
local refusal. Every removal must be disjoint from the protected 1,983 cells.
All 271 words, classification rows, 499 ordered connectivities and history sets
are snapshotted before and after, with exact canonical-byte equality required.

The conflict report is a lossless finite relation, not a truncated pair sample:
same-case candidate cliques, cross-case products for shared removed tags, and
cliques indexed by equal proposed unordered four-sets. Case→candidate memberships
and every shared tag/duplicate four-set are retained. The union is expanded
internally only to count distinct conflicting candidate pairs (at most choose
1,033 over2); unordered pair normalization prevents double counting. The
serialized relations allow every pair and each reason to be reconstructed,
including duplicate outputs whose removals are disjoint. No independent set,
sequence, combined subset or application is chosen.

## Held analytic fixtures, capacity and authority

The separate source has one direct TestCase with 16 unrun methods. A regular
square-equator octahedron supplies independent expected volume4/3, D2 and
Q²36/49 for both 4→4 fillings. Other fixtures challenge Catalan cardinalities,
duplicate/disconnected links, reversed and degenerate old cells, a nonplanar
positive-cell star without strict convex support, skinny convex quality failure,
incomplete/repeated disks, boundary/volume preservation, protected history,
existing observed duplicates/features, unavailable owners, disjoint-removal
duplicate conflicts, factored pair-union accounting and signed-zero word
preservation. The association-only conflict fixtures assert no cavity geometry.
Boundary equality implies volume equality for a valid consistent filling; the
incomplete-disk case deliberately fails both and does not pretend these are
independent mathematical events.

No fixture, API/runtime probe or real screen is authorized or executed here.
Future execution requires its own source peer, synthetic review/admission,
exact caller, runtime closure and owned one-shot controller. Existing bounds
remain 60s polled stop threshold, T8, 2GiB sampled aggregate RSS, 32MiB complete
outputs/logs and one thread, with no retry. These are future control ceilings,
not a proof of runtime, memory or serialization completion. A complete result
must retain every row; any exception, timeout or size refusal is INCOMPLETE,
never an empty family. No new serializer/control framework is proposed.

Even a passing local candidate keeps complete application eligibility null,
whole-head embedding/nonoverlap false, and geometry/native/physical/material/
LPBF/manufacturing authority false. Global cell/feature owners and duplicates,
complete independent oriented TET-boundary incidence, source-region/interface/
physical labels, exterior/BIN correspondence and the global manifold/embedding
proof remain open. The 235MB MSH and BIN are opaque descriptors only. No raw
body is read, hashed or statted. No existing coordinate-only application
authority authorizes topology edits.
