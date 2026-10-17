# One cap-aware quotient plus planar triangulation: held design

The smallest complete deterministic proposal is **one simultaneous quotient of
the 476 frozen all-minimum groups, followed by one constrained planar cap
triangulation**, with every final guard evaluated on the combined result. It is
a source-only design, not a selected keeper map, accepted target policy or
repair outcome. Mixed-only contraction plus CDT is a useful partial control,
but cannot be presumed to remove the 2,396 cap-only poor faces.

## Measured reference and the permitted bounded query

Repair-reference report `ebf9dd54…` and its independent review `071fb7f8…`
establish a single abstract cap annulus: 3,508 vertices/3,508 triangles, Euler0,
two oriented boundary cycles of lengths1,482 and2,026; all cap vertices lie on
those cycles, all exact winding signs are negative-Z. Exactly38 cap faces belong
to the fixed exterior; 3,470 lie in the9,872 incident union. The masks were
measured equal (865,429 fixed); their approval remains a separate policy.
The full d2af reference is one closed manifold component/Euler-208 with complete
zero global intersections, independently reviewed; 3,112 poor faces still reject it.

The mixed-only saved query `ceb6769c…` gives716 edges/no ties, 296 pairs plus210
triples, all1,222 vertices on cycle0. The all-minimum report instead gives476
components/3,006 vertices:444 groups solely cycle0 and32 solely cycle1, no fixed
conflicts and no off-cap vertices. These are observations, not keeper choices.
Most large groups lie on cycle1; excluding that loop from simplification is not
a demonstrated complete fix. There is no new diameter, band or grid criterion.

The separately saved selected-row query `83e5be3d…` read only1,486 cached d2af
point rows using stdlib struct/Fraction; its complete source-file SHA was checked
before/after. Each329/410 group is one contiguous cycle1 run. The two410-member
runs are exactly collinear/strictly monotone at x=+/-58.249370650108546. The two329
runs are not exactly collinear: y spans68.2539282323315..68.25393004466838 and its
negative reflection over an82mm x span. Adding the two adjacent outside vertices
breaks exact collinearity for all four runs. Therefore whole-run contraction has
no proved exact-zero domain change; its large vertex displacement alone is also
no rejection proof. This query did not contract, triangulate or evaluate feasibility.

## One explicit deterministic map; no keeper-product search

Use d2af as immutable local reference/current, identity local origins. Freeze
all476 group/edge identities from the existing exact-Fraction result. For each
group independently, enumerate only its existing member coordinates (2..410,
finite data-derived membership). Evaluate its quotient on the complete incident
**non-cap** side star while other groups remain unchanged. Reject a proposed
keeper if a surviving side triangle is degenerate/reverses its old normal, or a
fixed member/coordinate would change. Rank eligible choices by maximum minimum
surviving side-star quality, using the retained quality expression; exact native
score ties choose the lowest local source ID. Require a nonempty score domain.
All members are exact z0 here; no point projection or constructed keeper occurs.

Freeze that one map and report non-cap faces shared by multiple groups. This
independent selection is a deterministic proposal even when groups are coupled;
it is not a proof of their simultaneous compatibility. Apply all groups once,
drop repeated-index quotient triangles, and reject any invalid final combined
state. Do not backtrack through a Cartesian product, add arbitrary search caps,
or claim that failure disproves all other maps. The old early global-quality
check must be deferred until after cap triangulation, with its predicate unchanged.

## Cap triangulation with exact domain and exterior preservation

Map each original cap cycle through the chosen map, remove only consecutive
duplicate IDs, and retain its original cycle association. Require two disjoint,
simple, nonzero-area nested planar polygons with no repeated surviving vertices;
assign outer/inner by exact containment, not cycle number or an OEM label.
Require consistent oriented boundary correspondence. Exact2D predicates can
establish this geometric annulus independently of any unknown physical hole map.

The proposed CGAL constrained planar triangulation inserts **only retained old
cap-boundary coordinates**, both mapped cycle segments, and every edge of the38
unchanged exterior cap triangles. Reject coincident distinct source IDs,
intersecting invalid constraints, inserted intersection/Steiner points or any
coordinate without a unique retained local source ID. Preserve coordinates by
copying the original3D binary64 row, not by converting generated rational points.
Select finite triangles by exact containment in the mapped outer-minus-inner
domain. Internal frozen-triangle constraints must not toggle domain parity as if
they were hole loops. Emit each cap triangle with negative-Z winding and require
all38 original exterior cap triangles to survive exactly by cyclic oriented key;
never replace them with a subdivided equivalent. Any inability to preserve them
is rejection of this proposal, not permission to expand the frozen region.

Prove the new cap equals the **explicit mapped annulus** by exact containment,
no positive-area triangle overlap, complete oriented boundary equality and exact
area coverage; check its manifold links/components/Euler0/two loops. This is not
a claim that the mapped domain equals the original d2af cap domain. Compare the
old/new exact boundary polygons and signed areas, record any domain change and
apply the unchanged full independent distance gates. No physical/OEM feature
map is needed to conduct this explicit assumed bionic-datum study.

## Existing source reuse and immutable final guards

`quality_patch.cpp:33-107` supplies the unchanged binary64/uint64 codec and q
expression. `atomic_cavity_002.cpp:16-36,124-150` supplies groups, origin bits,
cyclic face keys, simultaneous quotient/preimages and side-face normal checks.
Its fixed135/132/744/4704/900845 and old fixture/global-Euler branches must become
a distinct exact case binding; existing sources remain untouched. For this
variant the approved fixed exterior is retained exactly, the current9,872 union
is the local reference, and measured global Euler-208 is fresh evidence.

Retain zero global faces below2/29 and nonworsening minimum only **after both
operations**; full valid oriented closed mesh/vertex links, one component/Euler-208,
no duplicate/degenerate faces, exact exterior/fixed bits and oriented union boundary,
and every final affected-neighbor1e8/one-degree scalar predicate. Retain allz>=0,
all cap faces exactz0/negative-Z, cap annulus/void continuity and unchanged38faces.
Use full changed-triangle immutable-reference envelope checks; a single forward
Polyhedral_envelope is not a two-sided certificate. Separate full continuous
original894<->final distance must have both upper bounds<=0.0625mm, plus complete
global intersections, local-region/features/opening checks, before any HXT/SICN0.1
or PDE. No global or physics gate is granted by this design.

Retriangulated cap faces have no one-to-one old face preimage: record them as new
cap-domain triangles tied to frozen polygon/constraint/point-ID hashes. Keep
original face IDs for unchanged38 cap faces and quotient side-face preimages;
do not invent per-face original IDs or apply an arbitrary old-cap normal match.
All retained vertex origins remain local d2af coordinate IDs; compose older clip
provenance separately, respecting UINT64_MAX constructed-coordinate markers.

## Smallest source/API and fixture preparation still needed

No direct CDT/2D polygon implementation was retained in the inspected metadata;
this is not evidence that the cached CGAL5.6 image lacks it. The retained pinned
clip.h only includes triangulate_faces.h/triangulate_hole.h and invokes face
triangulation. It does not establish a two-loop CDT API or domain-marking policy.
Do not fill each loop independently with triangulate_hole: that would lose the
annulus hole. First capture/read exact cached CDT/polygon APIs and freeze the
small domain/exterior constraint adapter before compiling; no speculative API
call or source adapter is frozen here.

Use one closed annular-prism fixture with a coupled boundary pair/triple and a
poor cap fan, preserving one exterior cap triangle exactly; independently verify
complete output coordinates/origins, negative-Z cap, two exact mapped loops,
area/void coverage, links/Euler, fixed exterior and zero poor faces. A second
literal should prove long straight-run simplification is allowed by geometry
rather than banned by displacement. Reuse focused normal/quality/neighbor
refusals; add exact failures for merged loops, lost/subdivided fixed cap face,
unexpected point, and invalid/coupled-map outcome. Include a no-eligible-side-star
case. Tests and a bounded native fixture must precede any separately authorized
single head proposal. If fixed boundary edges themselves prevent quality with
old coordinates, preserve failure or propose a new explicit operation; no hidden
Steiner insertion, coordinate relaxation, mask expansion or retry is allowed.

Only the selected point-row query and saved-JSON summaries were calculated here.
No C++ adapter, keeper/map, mesh output, native/Docker/API/network/Git or large
NumPy array operation was produced or executed. All previous records stay frozen.
