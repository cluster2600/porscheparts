# Endpoint003: immutable patch-envelope compile and fixture evidence

Two new helpers compiled successfully, followed by one direct subset-envelope
witness and three complete synthetic endpoint-collapse cases. The unchanged
source-envelope budget is **0.0625 mm**. These records establish the declared
software reference behavior only; they contain no head execution or admission.

Version003 preserves version002's placement, quality, normal, topology, fixed
coordinate and exterior-face rules. Its algorithmic change constructs the
CGAL envelope from the exact immutable original patch-face range instead of
the complete original surface. The ordered original face and vertex IDs are
exported as evidence. Flushed scalar progress records identify completed
stages without printing geometry coordinates.

For a subset P of the complete immutable original surface S,
distance(x,S) ≤ distance(x,P). Requiring a complete modified triangle inside
P's envelope is therefore conservative for candidate-to-original containment.
It can reject more placements. This does not establish original-to-candidate
coverage, global intersections, semantic features or solver quality. Any later
head result still needs its own complete independent gates, including both
continuous-distance directions against the complete original and unchanged
0.0625 mm upper bound and 1e−4 mm interval gaps. The exact earlier
[source-only note](original-patch-source-review.md) retains its historical
preparation status; the later compile/fixture records are separate ledgers.

| Actual endpoint case | Accepted collapses | Vertices / faces | Faces below triangle screen 2/29 | Minimum triangle SICN | Native exit |
|---|---:|---:|---:|---:|---:|
| Common fixed neighbors, preserved source001 | 0 | 10 / 16 | 2 | 0.000022255998243252707 | 3 |
| Same input, new source003 | 1 | 9 / 14 | 0 | 0.8660254037844386 | 0 |
| All-fixed rotated control, source003 | 0 | 10 / 16 | 2 | 0.000022255998243252707 | 3 |

Return code 3 is the declared unchanged/stagnating control outcome, not an
acceptance of poor triangles. The inputs are a literal **152 mm cube**, volume
**3,511,808 mm³**, with two free top vertices at (0,0,76) and
(1/1024,1/1024,76) mm. The proper rotation makes the third case entirely fixed.
The saved-array assessments compare every coordinate, oriented triangle and
origin to the exact known reference. Fixed coordinates, exterior faces,
opposite edge incidence, referenced vertices and exact rational volume pass.
The analytical whole-cube surface distance is zero because the only change is
the exact planar subdivision. This is not a sampled or continuous head-distance
measurement, and passing this triangle screen is not tetrahedral SICN ≥0.1.

Both version003 fixtures export exactly **12 ordered original patch-face IDs**
and **10 original vertex IDs**. The pure ID helper independently reselects them
from the original two bad triangles using the unchanged one-ring incidence
rule; actual bytes equal the precompiled expected exports. The native logs
retain thirteen scalar progress events followed by the final report. The
preserved source001 log remains its original single report.

The separate two-triangle subset witness records six literal outcomes:
included point and complete triangle accepted; a small offset accepted;
an omitted point and complete omitted triangle accepted by the complete
reference but rejected by the subset; an outside point rejected by both.
All six passed. This witness confirms the declared API subset behavior; it is
not a proof for arbitrary geometry or a head result.

The two actual compile windows were 51.78838320891373 and
31.474957583937794 s under separate two-CPU/4 GiB/no-swap/300 s limits and a
1 GiB temporary filesystem. The four later fixture windows were
0.89300920907408, 0.8781064578797668, 0.8973660829942673 and
0.9335583341307938 s with exits **0 / 3 / 0 / 3**, under two CPUs,
512 MiB/no swap and 60 s per job. Network access was disabled and the root
filesystem read-only. All attach processes were reaped and exact owned
containers removed, without OOM. These windows include lifecycle overhead;
RSS and CPU usage were not sampled. There was no automatic retry.

`input-binding-projection.json` preserves all 100 compile and 112 fixture
input hashes without duplicating their common entries. Complete original
before/after maps equal their frozen contracts and were independently checked.
Between-job preservation is the frozen controller's retained boolean; there
are no separate retained per-job hash maps. `original-inventory.json` preserves
every original compile/fixture artifact hash, including omitted binaries and
private receipts. Each phase summary's own hash is listed separately from its
artifact map. Original pending numerical-acceptance flags remain unchanged;
the independent saved-array and root reviews provide the scoped outcomes.

Exact copies include the tiny BIN geometry, uint64 origin/reference IDs,
native logs/reports, new source/test snapshots, source-preservation record,
source diff and safe reviews. The `962SURF1` format uses an eight-byte magic,
little-endian uint64 vertex/face counts, binary64 xyz coordinates in millimetres
and uint64 triangle indices. Raw `.u64` files contain little-endian zero-based
original indices. These are original project fixtures, not scans or supplier CAD.

Contract, execution and phase projections use explicit allowlists. Commands,
private absolute paths, container identities/owner values, PIDs and host
metadata are omitted. Binaries and upstream headers are not redistributed.
The pinned CGAL package/image and upstream licence origins are retained in
`runtime-projection.json`; no commercial licence is claimed. Original project
material follows the included [LICENSE](LICENSE). The unchanged cleanup and
metadata helpers and shared C++ dependency are bound by hash; their exact
source copies are already in the earlier
[fixture capsule](../finest-endpoint-fixtures/README.md).

Run only standard-library integrity and saved-array arithmetic with an
existing Python; the verifier imports the two hash-checked pure helpers only:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 twins/962-cylinder-head-f0/derived/engineering/finest-endpoint-003-fixtures/verify.py
```

The sealed payload inventory is `receipt.json`. This capsule permanently
establishes no head surface, complete OEM feature map, tetrahedral mesh,
thermal or structural solution, material/LPBF behavior or manufacturing release.
