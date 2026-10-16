# Endpoint-collapse fixtures: actual reference behavior

Three tiny synthetic cases verify the endpoint-collapse implementation and its
fixed-vertex behavior. Both CGAL 5.6 helper versions compiled successfully in
the same pinned ARM64 toolchain. No head geometry was processed by these
fixture invocations. The declared **0.0625 mm** source-envelope budget remains
unchanged; these are software reference checks, not an accepted head surface
or tetrahedral mesh.

The fixture is a **152 mm cube**, volume **3,511,808 mm³**, with a planar top-face
subdivision. Two close top vertices are at (0,0,76) and
(1/1024,1/1024,76) mm; their common neighbors are fixed. These literal values
activate the existing x=±76 fixed-plane rule. They are synthetic test inputs,
not measured head dimensions. A proper rotation produces the all-fixed control.

| Actual case | Edge-constraint rule | Collapses | Vertices / faces | Faces below declared triangle screen 2/29 | Minimum triangle SICN | Native return code |
|---|---|---:|---:|---:|---:|---:|
| Common fixed neighbors, source001 | fixed endpoint A **OR** B | 0 | 10 / 16 | 2 | 2.2255998243252707e−5 | 3 |
| Same input, source002 | fixed endpoint A **AND** B | 1 | 9 / 14 | 0 | 0.8660254037844386 | 0 |
| All-fixed rotated control, source002 | A **AND** B | 0 | 10 / 16 | 2 | 2.2255998243252707e−5 | 3 |

The only C++ change is the OR→AND constraint map in `source001-to002.diff`.
Source001 constrains every edge incident to a fixed vertex and stagnates in
the declared common-neighbor case. Source002 constrains edges joining two
fixed vertices; its separate placement guard still rejects a collapse whose
own endpoint is fixed. It removes the one declared free edge while preserving
every fixed coordinate and exterior oriented face. The all-fixed control
correctly stagnates. Return code 3 is the expected preserved/stagnating result
for those two controls, not a numerical acceptance of their poor triangles.

The separate full-array assessment compares every output coordinate and
oriented triangle against the exact known reference. It checks every source-
coordinate origin, opposite oriented edge incidence, no orphan vertices and
exact rational signed volume. All three represent the same complete cube
surface, so their analytical bidirectional surface distance is **zero**.
This follows from the exact planar subdivision/reference equality; no sampled
distance, continuous-distance library or head-distance result is credited.
Passing a triangle screen does not prove actual tetrahedral SICN ≥0.1.

`inputs/` contains all three exact tiny reference inputs. `data/` preserves the
actual BIN proposals, source-origin maps, native JSON reports and native logs;
only the improving case wrote `quality-candidate.bin`, identical to its proposal.
The `962SURF1` format is an eight-byte magic, little-endian uint64 vertex/face
counts, binary64 xyz coordinates, then uint64 triangle indices. Each `.u64`
map has one little-endian original zero-based coordinate index per output
vertex. The coordinate convention is millimetres. These are original project
fixtures, not scans or upstream CAD.

The first attempted fixture setup failed while querying an optional Docker
`Tmpfs` field. **No native fixture process started.** Its exact original
execution and root cleanup hashes are preserved in `initial-setup-projection.json`;
the created owned container was removed. A separately bound metadata companion
changes only that optional-field lookup. Its exact source and receipt retain
both core and companion attribution; compiled helpers, geometry, limits and
acceptance rules are unchanged. The first setup failure is not rewritten.

The later three fixture calls used verified Docker controls: two CPUs,
512 MiB memory, no swap, read-only rootfs, no network and a 60 s external limit
per case. Recorded controller windows were 7.932912457967177,
1.0658861249685287 and 1.1404641249682754 s respectively; these include container
lifecycle overhead. All attach processes were reaped and owned containers
removed, without OOM. The two compilation windows were 46.8456925409846 and
42.84572095796466 s under a separate 4 GiB/two-CPU/300 s compile scope. No peak
RSS or algorithmic performance claim is made.

Exact safe source/test snapshots mirror their original repository paths.
They preserve historical preparation comments. `quality_patch.cpp` supplies
the shared reader/writer/quality code; its original main was renamed and not
invoked by the endpoint executable. Compile/execution/contract projections
are explicitly labeled and omit private absolute paths, commands, container
identities and host metadata. Full original artifact hashes, deduplicated
38/41-input binding maps, four companion bindings, compiled-binary identities
and safe original record identities remain available. Binaries and upstream
headers are not redistributed. CGAL SMS/envelope licence and primary sources
are recorded in `runtime-projection.json`; no commercial licence is claimed.
Original project material follows the repository `LICENSE`.

The original phase summary's procedural `fixture_numerical_acceptance_established=false`
and native reports' pending-independent-check flags remain preserved. Separate
array/root/peer reviews establish only the declared fixture outcomes. They
establish no head execution, finest head representation, complete head feature
or semantic preservation, global head intersection audit, volume-mesh quality,
thermal/structural field, convergence, material behavior, LPBF or manufacture.

After sealing, verify the exact inventory and repeat only the small saved-array
arithmetic with an existing Python, without compilation, Docker or native calls:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 twins/962-cylinder-head-f0/derived/engineering/finest-endpoint-fixtures/verify.py
```

Root and independent retained-output reviews pass within this fixture scope.
The sealed inventory is in `receipt.json`. No new head trial or manufacturing
release is authorised by this document.
