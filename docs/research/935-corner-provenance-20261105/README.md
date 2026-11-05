# Trace acute sectors and regularize the numerical head surface

The 170 limiting sectors come from the inherited reconstructed envelope,
not the later hardware cuts. A new bounded numerical contraction pass reduces
forcing faces from 633 to 60, exceeding the fixed 50% reduction target. Complete
independent correspondence, cap-plane membership and native surface checks
pass. This is a separate calculation surface: exact feature-graph preservation
is deliberately replaced by an explicit geometric correspondence bound. The
printing master and its supports/contours remain unchanged.

## Provenance before changing the construction

The [previous exact-feature trial](../935-feature-preserving-retessellation-20261105/README.md)
fails its quality target and identifies 170 acute fixed planar sectors. This
audit follows those face and vertex indices through the conditioned surface,
local clipping provenance and original fine-envelope arrays. It independently
checks inherited parent-face connectivity and attempts exact indexed
correspondence to the acquired source arrays.

| Origin | All 633 forcing faces | 170 fixed-sector faces |
|---|---:|---:|
| Inherited parent-envelope triangle | 597 | 170 |
| New partial cut fragment | 5 | 0 |
| Assumed cap | 31 | 0 |
| Retriangulated during first conditioning | 0 | 0 |
| Vertex coordinates changed during first conditioning | 64 | 0 |

None of the 1,301 selected parent-envelope vertices matches an acquired vertex
exactly, and no selected inherited face establishes exact indexed acquired
triangle ancestry. This means **unestablished correspondence**, not proof of an
unobserved surface, scan artifact or removable physical feature. It does not
classify any ridge as functional or nonfunctional. Adjusting the provisional
cut planes would not remove the inherited 170-sector constraint.

The original OBJ remains unchanged at SHA-256
`4623d5d3b73fe3d03ca988a47543a8dd1be7834d3040e6f7efd1e1e95c766486`.
The source-unit-equals-millimetre scale, inferred closures, provisional hardware
separation and missing measured interfaces remain explicit hypotheses.

## New numerical contract, fixed before execution

The upstream verdict admits diagnostic regularization only. Unlike the rejected
exact-feature contract, this pass permits a very short geometrically detected
edge to contract, including an edge in a marked curve. The image of every
marked curve must remain on the candidate skeleton and receive the same
complete displacement bound as the surface. This does not promise exact curve
graph topology, sharp-edge normals or physical feature preservation.

The plan fixes one deterministic pass over initial directed edges, with current
topology checked before each operation. It fixes a 0.0029 mm maximum displacement
of every original vertex, a 0.01 mm cumulative bound relative to the hypothetical
printing baseline, unchanged cap-plane memberships, no local normal reversal,
no increase in faces below shape 0.01, relative volume change below 0.0001, and
at least 50% fewer triangles forcing incident tetrahedra below mean ratio 0.01.
These are numerical study limits, not manufacturing tolerances or allowables.

An optimistic upstream check first finds 1,403 directed candidates that could
affect 630 forcing faces. Only after that admissibility check does the pass
execute. Each accepted contraction meets the current edge-link test, the
original-coordinate displacement constraint for its complete merged vertex
group, cap-plane membership, orientation and local quality tests. Retired
endpoints are not substituted into new candidate edges; no parameter sweep or
second pass follows.

## Actual surface result and independent proof

| Check | Result |
|---|---:|
| Contractions / removed triangles | 426 / 852 |
| Remaining vertices / triangles | 4,106,319 / 8,218,458 |
| Forcing faces before → after | 633 → 60 |
| Reduction / required reduction | 90.5213% / 50% |
| Faces below shape 0.01 before → after | 3,469 → 2,866 |
| Minimum triangle shape before → after | 6.61064 × 10⁻⁷ → 4.09386 × 10⁻⁶ |
| Maximum displacement from conditioned input | 0.0025771112 mm |
| Complete cumulative correspondence bound | 0.0096432154 mm |
| Relative volume change | 3.18 × 10⁻¹¹ |
| Original marked edges mapped to points | 262 of 702,636 |
| Original marked vertex coordinates changed | 371 |

Every surviving vertex retains an existing input coordinate. The independent
verifier reconstructs the global vertex image and all surviving face images.
Every nondegenerate source-face image is exactly a candidate face; every
degenerate image lies on its skeleton. Thus the continuous barycentric map is
onto the complete candidate surface and supplies a bidirectional correspondence
bound for all triangles, including removed faces. Every old marked segment
maps to an actual candidate edge or point, proving the analogous curve-image
bound. The old feature graph may contract; its exact preservation is not claimed.

Cap memberships are checked from original face tags, independent of the
producer's group bookkeeping. A point originally on a cap can map only to an
original point on all the same cap planes. The planes stay fixed; their rims
may contract within the stated distance bound. No measured interface is inferred.
Pyramid-contraction, forged-bound, altered-face and cap-violation controls pass.
The correspondence calculation uses stored double coordinates and numerical
norms, not physical metrology or a new interval certificate.

Full native checks accept one positive manifold shell and zero open,
nonmanifold, winding, degenerate or intersection findings. Both closed,
connected, oriented vertex-manifold surfaces have Euler characteristic -2,910
and genus 1,456; their surface topological type is unchanged. This high-genus
hypothetical envelope does not establish the identity or reality of physical
passages. The checker 3MF
round-trips all coordinates and indices exactly. It remains a numerical checker
artifact, without regenerated supports, machine parameters or printing release.
Sixty exact boundary faces still force at least fifteen tetrahedra below the
diagnostic mean-ratio bin; passing the surface target does not admit head physics.

## Complete-scan deviation and comparable volume diagnostic

The same 100,000 raw-scan forward samples are reproduced from the frozen helper,
seed, source hash and face IDs. The paired scan-to-model distance change from
the printing baseline is at most 0.000845956 mm in that sample. Forward P95 and
P99 remain 0.097860 and 28.184238 mm. The reverse sample has P95 1.534288 and
P99 4.359549 mm; its points are resampled and are not paired physical points.
Removed protrusions and inherited closures stay in their complete denominators.
These sample statistics do not bound global distance to the acquired scan or
establish dimensional identity.

A new local volume trial uses exactly the frozen unoptimized Gmsh wrapper,
algorithm 10, eight threads and 2 mm interior size, after fresh surface
admission and the analytic cube control. The head limit is 900 seconds,
sampled RSS limit 40 GiB, with disk checks, exact child-group termination and
reaping. Its actual export, complete interval/exact cell inspection and quality
comparison are in [results.json](results.json). The export completes in
140.823 seconds with 4,181,299 nodes and 13,250,576 material tetrahedra.
The independent whole-volume inspection proves 13,249,784 cell signs positive
by outward intervals and 792 by exact fractions of stored coordinates. The
native export's one floating nonpositive-cell finding is retained; the robust
sign inspection resolves that numerical cancellation without changing a cell.
Every source vertex and the complete 8,218,458-face boundary stay exact; all
22,391,923 internal face pairs have opposite orientation. It does not claim an
exhaustive tetrahedron-pair intersection search.

The boundary improvement does not resolve volume quality. At the same
unoptimized meshing settings, cells below mean ratio 0.01 decrease only from
527,342 to 526,110 (about 0.234%); the minimum remains 2.91459 × 10⁻¹².
The 0.1 bin actually increases from 4,692,681 to 4,693,357. All bins are retained,
and the digital volume-quality gate still fails. The next work must address
interior slivers, numerical conditioning and case-specific solver admission,
with the raw checkpoint preserved, rather than infer physics acceptance from
the 90.5% surface result. Quality bins remain diagnostics; no changed geometry
is covered by older envelope simulations.

## Phase ledger and reproduction

| Phase | Inputs / source | Output / acceptance |
|---|---|---|
| Provenance | Frozen clipping map, parent arrays, raw scan arrays, sector indices; `audit_corner_provenance.py` | 170 inherited sectors; indexed acquired identity unestablished |
| Initial admission | Exact input geometry, old preservation receipt, new provenance audit | Numerical regularization only |
| Regularization | `regularize_short_edges.py`, one fixed pass | Local quality target passed |
| Independent map | `verify_regularization.py`, complete source map and old marked curves | Full surface/curve image bound and cap memberships passed |
| Native geometry | Frozen `validate_build_final.py` | Complete surface checks passed |
| Scan distances | `check_regularized_scan_distance.py`, frozen forward samples and rigid frame | Complete denominators retained; sampled fidelity only |
| Volume diagnostic | `run_regularized_volume.py`, frozen wrapper and analytic cube fixture | Terminal and independent results in aggregate receipt |
| Head CFD/FEA and AM | Case-specific solver admission, loads/materials, calibrated process | Still separate unfulfilled requirements |

The private capsule retains exact commands, sources, maps, meshes, controls,
logs and manifests. Only sources and aggregate reports are committed. Each
source provides `--help`; replay into a new private directory using the pinned
inputs, never into frozen evidence. No paid compute or supplier message is
created by this increment. The full engineering goal remains active.
