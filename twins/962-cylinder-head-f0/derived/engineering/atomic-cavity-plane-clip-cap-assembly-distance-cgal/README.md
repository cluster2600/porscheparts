# Assembled candidate: polygon-distance evidence

The assembled candidate passes the scoped polygon-distance gate against the **original analysis mesh**. The completed saved-result assessment gives the two-way enclosure **[0.03283858206618785, 0.03288858206618786] mm**: its upper bound is below the unchanged **0.0625 mm analysis budget**, with a stored gap of 0.00005000000000000837 mm below the 0.0001 mm requirement. Root and independent stopped-result reviews checked the saved evidence. [Assessment](assessment/report.json), [result peer](reviews/assessment-result-peer.json).

This is a numerical comparison between polygonal research surfaces. It establishes no factory/OEM dimensional accuracy, CAD deviation certificate, inner floating-point roundoff certificate, accepted volume mesh, PDE/strength result, material qualification or LPBF/manufacturing authorization. The separate stronger Mesh_2 criterion still has **414 failures**. Head surface and physical admission remain open.

The unchanged assembled input is BIN SHA256 `9d62eac6e2cd7b6a9ecb4a7ea5b632685820369b5c4ede379acc34238f50d7b4` (871,731 vertices; 1,743,878 faces). The unchanged reference is the original analysis BIN `894ece6e63d99684fd7c8710caf73132cd73731ac8bc667548c21c85962d4c95` (902,145 vertices; 1,804,706 faces). Exact oriented-coordinate cancellation retains 1,729,476 common faces; the remaining original 75,230 and assembled 14,402 faces are evaluated against the **complete opposite targets**. The assembled changed set is the exact disjoint union of all 8,976 cap faces and 5,426 noncap faces. A mask exclusion in one reverse component defers that face to the other component; it does not assign zero distance.

The three completed directed enclosures are combined by their maximum. The original-to-assembled direction uses the valid preserved CUB forward result; the reverse direction uses the maximum of two CGAL results:

| Direction | Selected source faces | Complete target faces | Enclosure (mm) |
|---|---:|---:|---|
| Original changed → assembled, CUB | 75,230 | 1,743,878 | [0.03193591661872411, 0.031970337358431314] |
| Assembled cap → original, CGAL | 8,976 | 1,804,706 | [0.006338983259280657, 0.0063889832592806586] |
| Assembled noncap → original, CGAL | 5,426 | 1,804,706 | [0.03283858206618785, 0.03288858206618786] |

Both reverse CGAL jobs completed RC0, in 198.5869691669941 s and 6.353123832959682 s respectively, including setup/cleanup. Each has an eight-file stopped closure, all 133 input pins unchanged before/after/current, complete selected-ID association, unchanged point/oriented-face snapshots and owned stopped cleanup verified by root and independent peers. The saved mixed assessment completed RC0 in 3.761039791861549 s, with all 280 bound inputs unchanged and no new native query. The exact child review is an external launch guard, avoiding a self-referential child hash. The [cap report](head/cap/report.json), [noncap report](head/noncap/report.json), [source-split proof](input/source-split-proof.json) and assessment retain their separate scopes.

The earlier unsplit reverse CUB query and later cap-only CUB split query both stopped with `RuntimeError: Exceeded maximum number of faces or vertices`. Neither supplied a reverse distance interval. The split controller stopped after its first failure and never launched its noncap query. Both failures remain preserved and uncredited in `cub-unsplit/` and `cub-split/`; the valid old forward interval remains individually usable despite its original overall completion flag being false. No numerical threshold, geometry or CUB failure record was changed.

The CGAL 5.6 wrapper performs a const sequential complete-facet directed query on the exact source triangle union, retaining all target faces (`match_faces(false)` for both meshes). Under the documented absolute-error convention, epsilon = 0.000025 mm = GAP/4 gives an outward scalar ± epsilon enclosure whose actual stored width must be ≤ 0.0001 mm. The upper-budget test remains separate. Outward endpoint arithmetic does not certify CGAL's internal floating-point arithmetic. Primary version/API provenance, installed-header metadata and source hashes are included; upstream headers are not redistributed.

Source `26297ed1…` compiled once to a 278,584-byte AArch64 ELF `6a173c3a…`, RC0 in 25.129856541054323 s. Selected controller `c51fc335…` uses an absolute deadline starting before container creation, synchronous completion/deadline checks and owned cleanup. Compilation and each head job used two CPUs, 4 GiB RAM, no swap/network and a read-only container root; compilation alone had 1 GiB tmpfs. Nine controller mocks passed separately. Compiled binaries remain private.

Two separately reviewed four-job fixture groups completed the six analytic and two negative checks below. Each group has a seventeen-file stopped closure, with all 89/108 input pins unchanged. Root's seven saved-assessor guard tests passed separately. The exact imported `assess_split_distance.py` helper is included with `assess_mixed_distance.py`, tests, METHOD and source reviews because it contains imported validation logic. These source copies are evidence for review, not a standalone execution package.

| Literal case | RC | Exact reference (mm) | Observed enclosure (mm) | Budget flag |
|---|---:|---:|---|---|
| open-to-closed | 0 | 0.03125 | [0.031224999999999996, 0.031275000000000004] | true |
| coincident-zero | 0 | 0 | [0, 0.00005000000000000001] | true |
| component-union-max | 0 | 0.04686737060546875 | [0.046842370605468746, 0.046892370605468754] | true |
| asymmetric-forward | 0 | 0.00000762939453125 | [0, 0.00005000000000000001] | true |
| asymmetric-reverse | 0 | 0.03124237060546875 | [0.031217370605468746, 0.031267370605468754] | true |
| continuous-interior-max | 0 | 1 | [0.9999749999999998, 1.0000250000000002] | false |
| malformed | 2 | — | null, input refusal | false |
| empty | 2 | — | null, input refusal | false |

Coincident zero and the positive sub-epsilon asymmetric-forward case both show the observed 0.000025 mm scalar error floor; their conservative intervals contain the exact values. The interior maximum is 1 mm despite zero distance at every source vertex, and its budget flag is false. Completed evaluation and budget acceptance are distinct. Historical fixture receipts retain their point-in-time pending statements about later phases.

Geometry is unchanged. Reuse the existing [35.5 MB research-model ZIP](https://github.com/cluster2600/porscheparts/releases/download/untagged-3dc4679a17c16edf0fb4/962-bore95-plane0-assembled-unadmitted-review.zip), SHA256 `8ba6fc5dca47f3a51bc6298f481aaa334ac1096608552a96159a1d4688f6a4d5`, from the recorded draft/prerelease. Its recorded upload/download limitations remain in the included download receipt. No new geometry asset, upload or remote download is created by this capsule; the archive's existing research/unadmitted label remains appropriate for the open physical gates.

`original-records.json` distinguishes exact copies from explicit selected-field projections. Every selected original hash and included payload hash is recorded. Host command lines, absolute host paths, container ownership IDs and raw observer output are omitted; container-side compile arguments remain visible. Three approved CUB runtime path keys become explicit hash roles, without changing their digest values. All retained mount/control/map entries and field omissions are identified in the private preparation ledger. Public projections are not execution contracts. The public seal covers these selected files and does not claim to reproduce every private native input, omitted artifact or receipt byte. No BIN, NPZ, raw-ID binary, upstream header, executable or raw scan is distributed here.

Run `python3 verify.py` from this directory to check the capsule's hashes, byte counts and complete file closure. This is a standard-library byte check and performs no geometry, native query or scientific assessment. It does not grant engineering or manufacturing approval.
