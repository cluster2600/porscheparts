# Continuous distance audit for the local quality candidate

The [public distance capsule](../derived/engineering/analysis-quality-distance/README.md)
retains scalar reports, exact reduction metadata and source/runtime hashes.
Its [immutable payload receipt](../derived/engineering/analysis-quality-distance/receipt.json)
does not bind this working navigation note.

The original source and the one-pass quality candidate both contain 1,804,706
triangles. Exact coordinate comparison identifies 1,800,014 corresponding
shared triangles and 4,692 remaining triangles on each side. Equality uses
finite binary64 coordinates, cyclic orientation and signed-zero equivalence;
there is no geometric rounding, distance threshold or sampling in this split.
A second implementation checks every triangle under all three cyclic
permutations without importing the canonicaliser.

Write the surfaces as `A = S ∪ A_changed` and `B = S ∪ B_changed`, where `S`
is exactly identical geometry. Every point of `S` has distance zero to the
opposite full surface. Therefore
`h(A,B) = max(0,h(A_changed,B))` and
`h(B,A) = max(0,h(B_changed,A))`.
Only the source of each directed query is reduced. The opposite target keeps
all 1,804,706 triangles. Corresponding-row cancellation is conservative:
additional shared triangles may remain in a query without invalidating it.

`audit_quality_distance.py` calls CUB once for each directed query. The existing
`distance_bounds(fragment, full)` wrapper must not be used: it also evaluates
the unrelated reverse distance from the full target to the fragment.
The matching PyPI 1.0.0 source builds an AABB of `B`, evaluates and subdivides
only `A`, and defines the last argument as `normalize`, not symmetry. Source
version agreement is not a rebuild attestation of the installed binary.

Eight predeclared native fixture queries passed. An asymmetric containment
case returns `h(A,B)=0` and `h(B,A)=1` for both full and reduced sources. A
second case returns `0.125` in both directions because the nearest target is
the shared triangle; incorrectly discarding that target would give `0.25`.
Both fixtures contain open triangle fragments. The complete frozen references,
inputs and retained intervals are in
`work/962-engineering/quality-distance-fixtures-001/`.

The head queries require a separate reviewed child contract. Each directed
interval must be finite, nonnegative and closed to an absolute gap of
`1e-4 mm`; the maximum upper endpoint must be at most `0.25 mm`. The existing
source-dependent allocation rule is unchanged. A resource failure, open
interval or excessive upper bound remains a rejection, without an automatic
retry or relaxed threshold.

The existing macOS runtime refused `RLIMIT_AS` before a query. The authorised
replacement is a sampled 4 GiB worker-RSS stop and a 300 s process-group
deadline, with serial native CUB and thread environment set to two. These are
not a hard address-space limit or an operating-system CPU quota; sampling and
process scheduling have finite observation latency. The original refusal is
distinguished from the replacement controls in the private preparation note.

The separately reviewed head child ran only its two frozen directed queries.
Their retained intervals are `[0.07185669700547284, 0.07192052963427972] mm`
from original to candidate, and
`[0.07056987737974417, 0.07062596035893927] mm` in reverse. Both gaps are below
`1e-4 mm`, and the symmetric upper endpoint `0.07192052963427972 mm` is below
`0.25 mm`. Jobs completed in 3.135 and 3.415 seconds with no watchdog refusal;
maximum observed worker RSS was 1,062,223,872 bytes. Both workers were reaped
and all 92 frozen bindings remained unchanged. The frozen assessor's result is
`work/962-engineering/quality-distance-head-001/interval-assessment.json`.

This result concerns distance between these polygon surfaces only. It provides
no CAD rounding-error certificate, complete Porsche interface map, channel/BCC
feature review, tetrahedral quality, whole-head simulation or manufacturing
approval. Separate topology and feature receipts must be assessed on their own
scope; they are not silently granted by this distance check.
