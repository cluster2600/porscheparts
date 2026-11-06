# 935 acquired-frontier pairing and strip study — 6 November 2026

The filtered surface study adds **1,064 local strips / 2,128 inferred triangles**
to the [previous acquired-gap candidate](../935-acquisition-gap-trials-20261106/README.md).
It preserves every parent coordinate, face and provenance field. Full saved
OBJ/NPZ readback, exact-predicate intersection inspection, edge winding/incidence,
duplicate/degenerate checks and every used vertex fan pass. It is still an open
surface: **97,153 boundary edges and 1,489 walks**. No complete faithful head,
functional CAD solid, printable job or manufacturing qualification is delivered.

The [scalar receipt](results.json) binds all seven executed source versions,
six reused helpers, native results and the immutable private capsule. No scan,
source-index list, local correspondence, private geometry or solver dump enters
Git. Physical classifications remain unaccepted. The owner permits scan transfer
to Vast, but this increment uses the Mac and a separate Kali1 check without paid
compute or any external AI/CAD transfer.

## Admission and independent inspection

The previous dossier leaves 612 acquired-only walks, containing 91,318 edges,
that were never admitted to the planar cap constructor. Their nonplanarity and
size do not authorize planar filling. This increment tests whether two nearby,
oppositely directed edges on the **same** acquired walk can bound a narrow local
strip. It never establishes that the gap is accidental scan damage or that a
physical passage should be closed.

The pre-execution census fixes a 0.5 nominal-mm midpoint search radius and
crossed-endpoint distance, tangent dot product at most -0.8, acquired owner-normal
dot product at least 0.8, and signed patch/owner-normal dot product at least 0.8.
All four points and the two owning acquired triangles are traceable to the raw
source. Shared indices or coordinates, different walks, opposite source layers,
reversed patch normals, degeneracy and ambiguous nearest partners are refused.
Reciprocal unique minimum crossed-width selection uses a fixed squared-score
ambiguity tolerance of 1e-12. These thresholds are study assumptions, not measured
manufacturing tolerances. Owner-declared source units remain independently
uncalibrated.

The spatial-index census examines 268,117 same-walk midpoint pairs, finds 1,810
eligible pairs and selects 1,315 reciprocal unique pairs on 379 walks. An
independent blocked exhaustive search reproduces the full pair set, all ordered
eligibility stages, diagonal flags and selection. It imports neither the census
nor its spatial index. Ten literal positive/negative controls pass. The first
checker run stopped on a faulty negative fixture: its unit-length reversed edge
correctly failed width before reaching the intended tangent test. Both source
versions and the failed run are retained; version 2 shortens that fixture.
Production thresholds and source geometry were unchanged.

## Construction, refusals and complete candidate checks

Each pair proposes both original-point quad diagonals. A proposal must reverse
the source frontier, respect the complete parent edge incidence/winding and
acquired-only origin, and pass native local intersection and complete corner-fan
checks. Extra old perimeter edges may close only on that same acquired walk.
The minimum-area passing diagonal is selected, followed by a deterministic
width/area/pair order under a cumulative edge-use budget. No point is moved or
welded, and no parent face is deleted.

| Stage | Result |
|---|---:|
| Selected pairs / diagonal proposals | 1,315 / 2,630 |
| Pairs with a locally passing diagonal | 1,120 |
| Refused by cumulative edge budget | 19 |
| Initial composite strips / added facets | 1,101 / 2,202 |
| Whole-composite intersections | 41, involving 37 strips |
| Entire conflicting strips removed | 37 |
| Filtered strips / added facets | 1,064 / 2,128 |
| Final intersections / zero-area / duplicate / edge conflicts | 0 / 0 / 0 / 0 |
| Final nonmanifold used vertices / unused vertices | 0 / 18 |

All local refusals, both diagonals and the initial failed composite remain in the
private capsule. Whole offending strips are removed without threshold relaxation,
alternate diagonal reselection or rejection of acquired faces. Global checks and
export readback are then rerun on the exact filtered bytes.

The final mesh has 1,248,924 stored vertices and 2,404,493 triangles. Its SHA-256 is
`a46ac1cceb571bfccfc48269117e6cf6b332ae06c180e6a78449ecc8ddfd7e51`;
the OBJ SHA-256 is
`5e487ce2cee69d83a89bc75034ee332b7eb7f6dcc20b8a8c32edd39e137739d3`.
New facets carry kind 4, their own pair and parent-walk channels, a disjoint legacy
label range starting at 30,000,000, and no acquired-face attribution. All previous
quarantine, contact, omission and cap channels remain exact.

## Distances and remaining topology

Every new triangle is probed on the predeclared degree-16 barycentric grid:
**325,584 samples**, maximum **0.2438122 nominal mm** to the raw source, under the
unchanged 0.25 bound. All 219,476 previous source probes and 46,184 omission probes
are recomputed and do not increase pointwise. A separate 100,000-point random
candidate-to-source sample has maximum 0.1910923 nominal mm. These finite samples
are neither Hausdorff bounds nor evidence of the missing surface's physical shape.
The preceding raw-source-to-candidate maximum includes excluded provisional
components and remains a material limitation; the favorable reverse sample does
not replace that direction or establish complete coverage.

The strips close 2,477 old acquired edges and introduce 1,687 unclosed cross-edges,
for a **net reduction of 790** from 97,943 to 97,153 boundary edges. Walk count rises
from 850 to 1,489 because partial strips subdivide openings. This is not 1,064
whole holes closed. All inherited open edges retain their direction, owner and
origin. Origin counts are 94,609 acquired / 100 quarantine / 726 declared cut /
six contact bridge / 25 bounded omission / 1,687 new strip. The fresh private
walk census includes parent links and deliberately unaccepted physical labels.
Ten surface components remain, including five single-facet components; the
largest has 2,397,182 facets. Anatomy and component selection are still unresolved.

## Native execution and software-chain status

| Phase | Concrete input / runtime and command | Output / check / state |
|---|---|---|
| Pair census | Previous filtered NPZ, full boundary ancestry and raw arrays; isolated Python/NumPy/SciPy; `census_frontier_pairs.py --job … --output …` | Complete 612-walk denominator; executed |
| Independent census | Frozen pair NPZ and same original inputs; `verify_frontier_pairs_v2.py --job … --census … --output …` | Exhaustive pair/eligibility/selection replay and controls; executed |
| Strip construction | Independently admitted census; pinned libigl plus frozen fan helper; `build_frontier_strips.py --job … --output …` | Both diagonal outcomes, preserved parent and initial candidate; executed |
| Whole candidate | Existing pinned `inspect_intersections.py` followed by `inspect_frontier_strips.py --job … --mesh … --intersection-proof … --output …` | All-face intersections, exact export/provenance, full topology, distances and component denominator; executed |
| Filtering and recheck | Failed composite plus exact inspection hash; `filter_frontier_strips.py --mesh … --inspection … --expected-mesh-sha256 … --expected-inspection-sha256 … --output …` | Whole-patch removal, then repeat both whole-candidate checks; executed |
| Independent Linux byte replay | Hash-checked parent and filtered NPZ streams; `verify_streamed_source.py` on Kali1, Python 3.14.7 / NumPy 2.3.5 | Exact entire parent prefix/provenance, complete edge winding/incidence, duplicates and degeneracy; executed, no Linux intersection/fan replay claimed |
| Downstream head CAD, physics and fabrication | Prescribed Qwen/CADAM/PicoGK/STEP/Gmsh/OpenFOAM/CalculiX/Adamantine chain | Complete source interpretation and closed admissible domains remain prerequisites; not performed by this surface increment |

Mac uses the existing isolated Python 3.12.13 / NumPy 2.5.4 / SciPy 1.18.1 runtime
and pinned libigl 2.6.3 addon; no runtime installation or upgrade. Eight bounded
execution groups retain seven completed groups and the one deliberate checker
stop. Every owned child is reaped. Each group has a pre-execution ledger, 600 s
shared deadline, sampled 4 GiB RSS ceiling and 4 GiB local free-disk floor.

Kali1 is reached through the live Thunderbolt IPv6 peer and the existing trusted
host identity, with strict checking and no agent forwarding. It has only about
1.65 GB persistent free space, so no job files or runtime are installed there.
The read-only check consumes 104,770,179 bytes over SSH into RAM, with two CPUs,
a 4 GiB address-space limit and a remote 110 s deadline. It completes in about
seven seconds at 1,328,664 KiB maximum RSS and writes zero persistent payload
files. It independently reproduces 97,153 open edges and 18 unused vertices.
The stream consists of one bounded JSON header, hash-checked checker source,
parent NPZ and candidate NPZ, in that order. The private ledger retains lengths,
hashes and byte identities; the checker refuses trailing bytes or changed inputs.

The approved CADAM/Qwen launcher's bytes still match its installation receipt.
Actual startup fails because `chat_template.jinja` is missing at the dedicated
Qwen model target on `qwentraining`; the dedicated model endpoint is unreachable.
No Qwen inference or cloud fallback is claimed. This does not change the
[documented CADAM role](../../architecture/cadam-local-qwen.md) or grant its
synthetic coupon authority over the source scan. This increment produces no
PicoGK solid or qualified replacement CFD/FEM/AM solve. The older hypothetical
Gmsh domain's 996 failing minSICN cells remain unresolved, not superseded.

The private capsule contains **71 payload files / 405,322,114 bytes**, under
manifest `9625e46a0b47864e2813094fd53f19cb25ef607b9d42a6a407efd39f6bd2caf4`.
All payloads are frozen and rehashed. Public tests exercise adversarial fixtures
and bind source/receipt hashes; they cannot replay private geometry in CI.

## Next work and release limits

Re-audit the 1,489 current walks before further construction. Of these, 991 mix
acquired and strip edges, 462 are acquired-only, and two are strip-only; older
mixed, cut and omission frontiers remain. A source-only cap policy must not be
silently applied to inferred strip borders. Keep the rejected 37 strips and
their intersecting face witnesses available for physical/anatomical review.
Any new band growth or cap study needs its own source-support, orientation,
topology and distance admission before geometry changes or parameter sweeps.

The engineering requirements remain the
[scan-reconstruction workflow](../../architecture/scan-repair-workflow.md) and
[engineering workflow](../../architecture/engineering-workflow.md). A faithful
complete editable head, measured interfaces and units, internal passages, loads,
material and machine/powder/process/support/toolpath data, converged/correlated
physics, physical build/metrology and professional engineering review are still
open. Falcontech/Farsoon and BLT remain qualification candidates, not selected
qualified processes. G0–G5 and manufacturing authorization remain false. The
full goal stays active. No new Vast resource, supplier message, merge or release
is performed; the original $35 total / $30 compute / $5 reserve limit remains.
