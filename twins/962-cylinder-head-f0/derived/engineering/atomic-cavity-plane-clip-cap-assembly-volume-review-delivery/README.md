# Assembled plane0 HXT volume — rejected-mesh review download

The review archive is **complete and independently verified locally; upload is pending**. No new download URL or remote verification is claimed at this checkpoint. The archive contains the saved raw HXT mesh and its evidence; it is **rejected at the unchanged minimum SICN 0.1 gate**.

| Local archive identity | Value |
|---|---|
| Filename | `962-bore95-plane0-assembled-rejected-volume-review.zip` |
| Bytes | 56,195,323 |
| SHA256 | `1cbcd72458d52fb122eed52b455bb1a0293f7e97c64a0342f241d27c5d49faf4` |
| Members / uncompressed bytes | 84 / 206,302,779 |
| Format | Standard deflated ZIP; exact unconverted Gmsh4.1 binary MSH |

The [actual member map](ASSEMBLED_PLANE0_VOLUME_REVIEW_MEMBERS.json) and [checksum](ASSEMBLED_PLANE0_VOLUME_REVIEW_SHA256SUMS.txt) are byte-identical copies from the completed local build. Independent streamed readback compared every uncompressed member with its source bytes and checked SHA256, CRC32, size, complete 84-member closure, fixed ZIP metadata, the embedded 83-other-member manifest and both nested capsule seals. All 94 bound inputs remained unchanged across the peer review. The [completed byte-audit receipt](archive-byte-review.json) is identified by SHA256 `15bd43bdad41154a203c58002edeb55cbaaabb6b674b53c89dbd646ead27dbc7`; no native or geometry assessment was replayed.

The exact 205,789,862-byte MSH is SHA256 `4a17567e6394bcda8571b0ff07f74471338bc7f3be60b0153a20020f654c6b41`. Its saved observations are 950,032 nodes, 2,989,608 tetrahedra, 78,301 referenced interior nodes and zero orphans. Minimum SICN is 3.784626658982107e-9: 285,573 positive cells are below 0.1, with zero nonpositive cells. Of these, 247,088 have all four vertices on the admitted candidate boundary; 38,485 involve an interior vertex. This classification does not prove boundary coordinates must change or identify a successful repair.

The archive includes the complete [HXT rejection and independent saved-file capsule](../atomic-cavity-plane-clip-cap-assembly-volume/README.md) and [positive-poor-cell diagnosis capsule](../atomic-cavity-plane-clip-cap-assembly-volume-poorcell-diagnosis/README.md). It contains **the HXT case only; no Delaunay result**. Coordinates are millimetres in the unchanged assembled-study frame. Boundary tags are numerical associations, not OEM interface labels, material assignments or physical boundary conditions. Preserve coordinates/connectivity and avoid automatic optimization when inspecting this rejected result.

The existing [assembled BIN/PLY and seven-map review download](https://github.com/cluster2600/porscheparts/releases/download/untagged-3dc4679a17c16edf0fb4/962-bore95-plane0-assembled-unadmitted-review.zip), SHA256 `8ba6fc5dca47f3a51bc6298f481aaa334ac1096608552a96159a1d4688f6a4d5`, remains unchanged and is not duplicated here. The repository project licence and both selected evidence capsules are included; this is a review package with explicit dependency/provenance limits, not standalone reproduction.

The archived README/internal manifest remain historical held-preparation records. Actual local build identity is established by these sidecars and the completed audit. Their `uploaded=false` is the immutable packaging-time state; a later root publication receipt must separately establish any remote upload. The 414 stronger Mesh_2 failures remain separate. No accepted volume, head PDE, convergence, thermal resolution, OEM accuracy, material/strength, LPBF process or manufacturing qualification is established.
