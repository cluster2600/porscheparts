# Large-contour acquired-source audit — November 6, 2026

The complete **124 source-scope large walks / 69,101 boundary edges** now have
independently checked observed/inferred ancestry, component membership, directed
cycle identities and local source-normal diagnostics. They account for about
72% of the remaining open boundary. **None qualifies as a planar cap** under
the unchanged signed-source criteria: 123 fail planarity, all 124 fail positive
acquired-binormal direction/cone checks, and none has a uniquely measured thin
principal-frame diagnostic. These are results about this proposed planar method,
not proof that the source normals are wrong or that reconstruction is impossible.

No contour is filled, no coordinate/facet changes and no large reconstruction
domain is admitted. The fully checked open parent remains exactly
`b4705dbb46a67f467bcb43cdc5bb922a77b2b01274fea1935bd805db15a3f559`, with
2,405,744 triangles, 95,868 boundary edges / 1,448 walks, ten anatomically
unaccepted components and 18 unused vertices. It remains **not print-ready**.

The [scalar receipt](results.json) binds two executed sources, frozen helpers,
all four registry birth-census/proof families, controls and private reports.
All 17 payload files / 3,084,318 bytes are frozen and rehashed under manifest
`95b12e30e8fcfb8caadee1965423614f6c0dcf9f08fd71790f45d321ac7456b7`.
Per-walk dimensions/frame vectors, owner/corner indices, ancestry arrays and
private geometry remain outside Git.

## Requirement and complete scope

The [previous full frontier inventory](../935-post-interwalk-continuation-20261106/README.md)
identified large source-scope contours as the dominant unresolved population.
This audit follows that evidence and the
[scan-repair workflow](../../architecture/scan-repair-workflow.md) before any
new parameter sweep, contour filling or downstream head simulation.

All 1,448 boundary walks are freshly re-enumerated from the actual full mesh.
Their exact directed edges, owning facets and surface-fan cycles match the
saved accepted boundary. The selected population is every walk above 128 edges
with actual acquired edges and origins confined to {1, 6, 7, 8, 9}. No convenient
subset or largest-component anatomical selection replaces the denominator.
Six other large walks remain outside this origin scope; the complete inventory
still records them separately. The longest selected walk has 5,039 edges.

| Actual selected boundary origin | Edges | Evidence treatment |
|---|---:|---|
| 1 — acquired source | 68,588 | Original owning facet and directed raw corner IDs; actual raw normal |
| 6 — earlier frontier bridge | 479 | Exact inferred quad facet and its two acquired supports |
| 7 — earlier untried-pair bridge | 22 | Exact inferred quad facet and its two acquired supports |
| 8 — earlier opposed wall | 10 | Exact inferred quad facet and its two acquired supports |
| 9 — registered continuation | 2 | Immutable global ID and exact birth census/proof/class/round |
| **Total** | **69,101** | **All checked** |

Inferred owner normals never become acquired measurements. Their normal slots
remain zero; their separately retained raw references establish provenance,
not measured missing surfaces. Original scan bytes and the accepted parent
surface are untouched.

## Independent provenance and geometry replay

The [producer](source/audit_large_frontier.py) recovers actual raw identities
with the frozen vector helper. For every inferred owner it rejoins the exact
four observed support points, oriented triangle and directed endpoints. Kind 9
uses all 23 immutable registry entries, not a mutable edge row: canonical pair
keys, selected-edge order, geometry class, birth round and census/proof hashes
are checked against all four birth families. Ordered supports are not silently
replaced by the registry's canonical key order.

The [independent checker](source/verify_large_frontier.py) imports no producer.
It independently recovers raw facet/corner identity, cyclic oriented inferred
quad triangles and the actual cross-edge. Reversed facets, internal diagonals,
moved source points and unsupported class policies are refused. Every scoped
edge signature, acquired normal, support reference and complete cyclic source
identity matches the saved result. Directed cycle hashes use a canonical
rotation, without changing winding.

Primal-vertex and face-dual connectivity independently agree on every original
component and V/E/F/B/Euler/genus certificate. Every selected walk belongs to
one component; component membership does not identify the physical head or
attached hardware. No components are merged or removed.

Principal-coordinate spans, fitted-plane residuals and acquired edge-binormal
minimum/p10 are diagnostics. The producer uses SVD; the checker separately
accumulates covariance outer products, solves its symmetric eigenproblem and
recomputes signed directions one acquired edge at a time. Plane/frame
uniqueness and projected-area orientation strength are explicit. Numerical
comparison guards are arithmetic checks, not physical tolerances or changed
admission bounds. Principal frames are not manufacturing datums.

## Result and consequence for reconstruction

The original compact planar limits remain fixed: 3–128 edges, at most 3 nominal
mm diagonal, fitted-plane residual at most 0.25 nominal mm, at least two distinct
acquired owners, strictly positive acquired-binormal minimum and p10 at least
0.8. All selected walks exceed the old size scope. For diagnostic comparison
only, removing the **size reason labels** still leaves:

| Independent diagnostic | Large walks |
|---|---:|
| Plane residual above the existing 0.25 nominal-mm bound | 123 / 124 |
| Nonpositive acquired-binormal direction against the fitted plane | 124 / 124 |
| Acquired-binormal p10 below 0.8 | 124 / 124 |
| Otherwise compatible planar signed-source diagnostic | 0 / 124 |
| Unique principal second span at most 0.5 nominal mm | 0 / 124 |

No old size guard is removed from an admission or constructor. No exact
projection/contact audit or native large-contour trial is claimed. In
particular, raising the edge-count/diameter limit would not cure these
nonplanarity/direction failures. The result rules out that shortcut while
preserving the actual source surfaces.

The next proposed investigation is **local chain-to-chain reconstruction with
unequal boundary sampling** on these large walks. A one-edge-to-two-edge strip
can have matching endpoints and a narrow material gap when no whole atomic
edge pair meets the original sampling correspondence. This is a new input
class, not a retry of a refused four-corner pair or a relaxed distance bound.
Before scan construction it still needs an independently verified source census,
unequal-sampling and annular-through-opening controls, complete incident masks,
exact target perimeter, signed realised triangles, local/global native predicates,
manifoldness, unchanged-source exports, topology and source-support checks.
Neither a local pairing nor a hidden passage is invented by this audit.

## Runtime, controls and evidence limits

Both bounded local execution groups complete and their owned children are
reaped. The producer takes 5.74 observed seconds (peak sampled child RSS
1,465,136 KiB); the independent replay takes 10.35 seconds (1,508,736 KiB).
Each retains the 600-second shared deadline, sampled 4-GiB child RSS ceiling
and 4-GiB disk floor. The pinned isolated Python/NumPy/SciPy runtime and
SIGTERM-safe controller are unchanged; there is no installation or paid compute.

Eight new plus 130 preceding focused tests pass, including a 134-edge,
30 × 0.2 nominal-mm synthetic rim with unequal side sampling, independent
SVD/covariance agreement, void-side and annular-inner-rim/global reversal
refusals, rank-one ambiguity, birth hash/round/class forgeries and exact
oriented cross-edge ancestry. The final run treats RuntimeWarning as an error.
Five frozen scalar raw-identity controls also pass during actual replay.
These source diagnostics grant no native or physical reconstruction admission.

The last read-only Kali1 source/provenance/edge witness still matches the exact
unchanged mesh hash. It is reused only for that geometric witness. No new Kali
diagnostic replay, Linux native intersection/fan replay or remote payload
installation is claimed in this increment. Public CI checks synthetic and
repository contracts without the private scan.

Owner-declared millimetres remain the working units; independent physical
calibration is absent. Outward source winding/material-side interpretation,
component anatomy, functional interfaces and unobserved passages remain
unaccepted. The full goal remains faithful editable head CAD,
admissible/correlated physics and qualified functional-metal fabrication through
the prescribed Qwen/CADAM/PicoGK/STEP/Gmsh/OpenFOAM/CalculiX/Adamantine chain.
The earlier hypothetical Gmsh domain still has 996 failing minSICN cells.
No complete solid, accepted head physics, machine-specific fabrication file,
physical build/inspection or professional engine release is established.
G0–G5 and manufacturing authorisation remain false.

No new Vast resource/spend, external AI scan transfer, supplier outreach,
merge, physical print or release occurs. Original private-scan-on-Vast
permission and the $35 total / $30 compute / $5 reserve remain in force;
current balance is not asserted. The approved wrapper's missing OpenBao
bootstrap identity remains a prerequisite for future paid work, without another
secret source. Independent local reconstruction work continues; the full goal
stays active.
