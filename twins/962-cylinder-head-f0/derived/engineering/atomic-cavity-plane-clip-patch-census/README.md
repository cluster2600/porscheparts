# Clipped surface: poor-face and incident-patch census

The completed read-only census describes the rejected clipped surface
`d2af68ee8ab242e992b15b6e2a93ac7e487972277af7f31a8496a7036ec32240`.
Its 3,112 poor triangles remain rejected. This result identifies their local
indexed structure; it approves no repair region, target edges, keeper vertices
or geometric operation.

| Observation | Completed result |
| --- | ---: |
| Poor-face edge-connected groups | 758 |
| Shared-vertex contact records between poor groups | 760 |
| Poor-face seed vertices | 3,580 |
| Complete seed-incident face union | 9,872 faces in one edge-connected component |
| Incident-region vertices / edges / faces | 5,938 / 15,814 / 9,872 |
| Incident-region Euler characteristic | −4 |
| Oriented abstract boundary cycles | 6, containing 2,012 boundary edges |
| Incident cap / mixed / off-plane faces | 3,470 / 4,914 / 1,488 |

Each poor-face group is individually recorded as an abstract disk. The 760
contacts are shared-vertex records; a vertex may belong to more than two groups,
so this count is not a pairwise-contact count. The complete incident union is
a local oriented manifold with boundary, with clean local edge, orientation and
vertex-link checks. It is **not an abstract disk**. All 15,814 selected edges
have two oppositely oriented incidences in the complete saved surface, and the
complete surface stars of its 5,938 selected vertices have clean cycle checks.
These observations do not qualify unselected global geometry. The six abstract
boundary cycles do not establish six physical holes, geometric cap openings,
or any correspondence with cooling passages.

The [full report](readback-report.json.gz) retains every component's face IDs,
boundary cycles, full boundary incidence, plane classes, links and coordinate
hashes. Its uncompressed JSON is 5,005,369 bytes with SHA-256
`8750db7d8553fbb37e6df30b93fc743dadfcb6860fa03ca3f7bf4cc514f5ec4c`.
The deterministic gzip is 376,043 bytes with SHA-256
`e8979a91c90cb438eca8c83596bffa4fdf4a2803947523622ccfec682685015d`.
The [format receipt](report-format.json) records full decompressed-byte equality
and gzip CRC verification, an empty filename and zero modification time, and no geometry
change. The uncompressed report is not duplicated here.

The [execution receipt](execution-receipt.json) records return code 0, no stop
reason and 3.292 seconds of controller wall time. The configured controls were
a 120-second wall deadline, a sampled 4 GiB worker-RSS stop and two library
threads. Seven RSS observations reached 221,954,048 bytes. This is an observed
maximum, not a certified peak or a hard OS memory/CPU quota. No separate
OS PID-absence check is claimed. The [log](native.log) records the completed
census status.

The [source peer review](reviews/source-peer.json) covers the frozen preparation
and six tiny stdlib kernel tests. The [actual result peer review](reviews/result-peer.json)
independently reconstructs the selected saved rows and all component records;
it does not repeat a complete head scan. The [root result review](reviews/root-result.json)
records a separate stdlib scan of all 1,739,126 saved faces, independently
reproducing the exact incident union, selected complete edge incidences and
vertex stars, poor-group contacts, exterior and coordinate hashes, Euler
characteristic, boundary cycles and plane classes. Its scope remains the
selected incidence and abstract combinatorics.

The [reader](source/reader.py), [kernels](source/patch_kernels.py), unchanged
[controller](source/run_readback.py), [kernel tests](source/test_patch_kernels.py),
[test result](details/kernel-tests.json), [source provenance](details/source-provenance.json)
and [preparation checks](details/preparation-checks.json) are exact selected
source records. [METHOD.md](METHOD.md) preserves the earlier held preparation
wording. Its unrun/absent-output statements describe that historical stage;
the completed receipt and result reviews above describe the subsequent run.

The [native contract projection](native-contract-projection.json) retains all
24 input pins and every original field value except the private absolute
`native_python` path. The historical `native_launch_authorized: false` field
is preserved alongside the actual `readback_launch_authorized: true` field.
This selected evidence set includes no surface binary, runtime executable,
upstream headers or original uncompressed report. A census rerun requires the
original pinned inputs, directory layout and selected runtime.

The 865,429-vertex legacy fixed mask is descriptive and **not an approved repair
constraint**. No old 135-edge or 228-disk proposal is inherited. Any later
repair needs its own reviewed constraints and new checks of global topology,
intersections, cap features/openings and both continuous distance upper bounds
against the original surface at the unchanged 0.0625 mm budget. Strict zero
faces below 2/29 remains necessary before a volume trial with SICN ≥ 0.1.
Surface admission, volume admission, head physics, material qualification,
LPBF qualification and manufacturing authorization remain open.

After the complete payload is sealed, `python3 -B verify.py` checks its recorded
hashes, sizes and file closure. The reused verifier does not decompress the
report, rerun the census or establish geometry/physics acceptance.
