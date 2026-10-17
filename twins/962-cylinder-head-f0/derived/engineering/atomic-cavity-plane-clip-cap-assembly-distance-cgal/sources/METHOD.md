# Held directed CGAL query preparation

No compilation, fixture query or head query has run for this source. The CLI is
`directed-distance source.bin complete-target.bin sorted-source-face-ids.u64 fresh-output-directory`.
Only report.json and stderr are written. The controller must pin every input,
source, installed runtime/image and source-selection proof before/after, and
enforce reviewed process/resource/cleanup limits. Native failure is retained;
there is no retry or fallback algorithm.

The codec is the existing little-endian 962SURF1 binary64-point/uint64-face pattern.
Its existing2,000,000 input vertex/face guard remains a format/resource guard;
it is not an adaptive query face quota. Every input triangle is validated.
Selected source triangles get three fresh graph vertices each, copying every
original binary64 coordinate and oriented corner. This is exactly the same
triangle union, without a claim that an arbitrary selected subset has manifold
vertex fans. The full selected original-face ID list is reported in order;
constructed source vertex3*i+k is the copied corner k of selected face i.
The target uses EVERY input point and face with shared original indices. No
target filtering, coordinate normalization, welding, perturbation or repair.
Both meshes may be open if their constructed triangle graphs are valid.

The reviewed installed CGAL5.6 scalar API is called with const meshes,
Sequential_tag, match_faces(false) in BOTH named-parameter packs and absolute
epsilon=0.000025mm. Under its documented |scalar-h|<=epsilon guarantee, the
interval is scalar±epsilon with one outward nextafter per endpoint, lower
clamped0. Explicit finite/order/gap<=0.0001mm checks are required. No claim of
an internal floating-point roundoff certificate is added. Exact serialized
vertex-index/coordinate-bit and oriented face-index/corner snapshots are
memcmp-compared before/after, including after a caught query exception.

RC0 means a completed software interval. polygon_budget_passed separately
reports upper<=0.0625mm; fixture distance1mm must complete RC0 with that flag
false. No single directed result is a whole-surface bidirectional acceptance.
The retained forward CUB result and both disjoint reverse source pieces need a
separate combined saved-result assessment; the old CUB-specific assessor is
not silently reused for this report schema.

prepare_literals.py is prepared, unrun source. Root may materialize its six
known-result queries and two malformed/empty refusals in a fresh directory.
The square/four-wall fixture has a true continuous interior maximum1 despite
all source vertices having distance0. Native fixture checks must verify the
exact known distance lies within the stored closed interval, the actual gap,
complete target counts, selected-ID/corner association, both snapshot flags,
return codes and separate budget result. A reviewed controller/actual binary
child is still required before any native execution. No head output, geometry
modification, fields, solver or physical qualification follows.
