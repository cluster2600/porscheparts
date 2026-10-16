# Source-only review: immutable original-patch envelope

Verdict: mathematically conservative and supported by the pinned CGAL 5.6 API. This is a proposal only: no source change, compilation, envelope construction/query, geometry run or resource escalation was performed. The prior 4 GiB OOM remains unchanged. Its empty log does not locate the failing allocation or phase.

## Bound and scope

Let S be the complete immutable original surface, P the union of exactly its already-declared 4,704 patch triangles, and epsilon = 0.0625 mm. Since P is a subset of S, distance(x,S) <= distance(x,P). Therefore requiring every complete surviving modified triangle to lie inside the epsilon envelope of P is sufficient for the same candidate-to-full-original distance bound. It is stricter and may reject placements the full envelope would admit; it cannot legitimately admit a farther placement by shrinking the reference set.

Unchanged exterior faces must remain exactly equal to original oriented faces. Every modified surviving fan triangle must still receive the whole-triangle envelope query, not just its vertices or edges. The present placement checks both endpoints are free, all retained fan triangles, normal change, finite positive triangle quality, and strict local bad-face improvement. Keep all those rules and the zero-length-edge refusal unchanged. Keep the original patch/fixed masks unchanged and prove the complete final exterior/fixed arrays again.

This is one directed local containment condition. It does not prove original-to-candidate coverage after face removal, global intersections, topology, channels or solver quality. Later independent two-direction CUB must still compare against the complete original surface and use complete opposite targets, with the unchanged 0.0625 mm upper bound and 1e-4 mm interval gaps. Any exact shared-facet reduction must be recomputed for the new candidate.

## Pinned API and storage

Header: work/962-engineering/cgal-envelope-runtime-002/package-metadata/Polyhedral_envelope.h
SHA-256: a76fc09d3ce383059444fc3f3a9838cc3a7de80bac80af2a4a026d385d7441c5.

The subset constructor is explicitly documented at lines 432-464 and implemented at 465-543:
`Polyhedral_envelope(face_range, tmesh, epsilon)`.
Use a sized `std::vector<Face>` of original descriptors in original face order with the immutable full `original` mesh. The implementation actually uses face_range.size(); a generic unsized iterator pair is insufficient. Lines 485-510 build a local vertex-index map and copy only points referenced by selected faces. No separate closed patch Surface_mesh is required; the envelope represents a set of triangles, and this constructor accepts a subset on an existing FaceListGraph. Original descriptors and point property map must be valid while construction runs. It internally copies its reference data; keep that envelope immutable for the whole pass.

The full constructor (365-406) currently copies all 902,145 vertices and 1,804,706 faces. The subset is expected to reference 3,858 vertices and 4,704 faces; freeze exact descriptor/triangle identities as well as counts and reject any silently skipped degeneracy. Lines 631-641 build the prism AABB tree; 1949-1956 size prism/box arrays per selected face with epsilon/sqrt(3) conservative thickness. The subset needs no halo, boxes, transformed points, welding or candidate-derived reference.

Current helper: twins/962-cylinder-head-f0/source/analysis-cgal/finest_endpoint_002.cpp
SHA-256: 55da19ca708d48429afd69115345cf0983df99f1fd5c26ab62f8286fed1cc604.
Its original/candidate copies (110), original patch selection/fixed masks (114-123), whole-fan containment (53-60) and full-original constructor (133-134) are the relevant sites. Both full Surface_mesh graphs and the global SMS edge queue remain allocated. Reducing the envelope's reference set may reduce its own storage, but does not establish total peak memory, a successful 4 GiB run, or the cause of the previous OOM. Do not substitute a compact patch graph for the candidate: SMS requires the complete valid triangular candidate and unchanged exterior topology.

## Smallest next separately reviewed proposal

Preserve source002/binary/receipts. Prepare a newly named version whose only algorithmic change is selecting the exact existing original in_patch face range for this constructor. Freeze the original source, ordered patch-face IDs/hash, referenced-coordinate IDs/hash, same image/compiler/options, and new source/test/binary provenance. Add flushed stage/count checkpoints before/after original import, candidate copy, envelope construction and SMS entry, so any future stop has attributable progress; these diagnostics must not alter acceptance.

Compile only after separate root authorization under the existing bounded compile scope. Before any head launch, use separately authorized tiny known-reference fixtures to verify the same three endpoint outcomes and a direct subset-envelope rejection near an omitted reference triangle, while complete patch-triangle containment remains correctly accepted. A later distinct head child would retain 2 CPUs, 4 GiB/no swap, 300 s external cap, no network, one pass and no retry; no head run is authorized by this note. All independent final admission/physics flags remain false until their own gates are executed and passed.
