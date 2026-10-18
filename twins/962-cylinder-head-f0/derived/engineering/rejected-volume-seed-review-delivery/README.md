# Rejected volume seed: numerical review download

**The saved tetrahedral mesh is rejected.** The distinct
`962-bionic-bore-95-rejected-volume-seed-review.zip` is uploaded to the
[existing draft study release](https://github.com/cluster2600/porscheparts/releases/tag/untagged-3dc4679a17c16edf0fb4),
which requires authenticated draft access. It is **51,283,212 bytes**, SHA-256
`b0c32a5a045c8e63142ff2aebeee8ba4bcb0bd47f651a409a0836432bf974391`.
The deflated ZIP contains 32 members: 31 payloads and their complete
byte-count/SHA-256 manifest. Compression preserves every uncompressed member.
The [separate publication receipt](publication-receipt.json) verifies all three
new assets' uploaded states, exact sizes and SHA-256 digests. The existing draft
now contains **24 assets**; all previous 21 IDs, names, sizes, digests and states
remain unchanged, as do the release tag, URL and draft state. This delivery
does not change the mesh's rejection or authorise functional use.

The [metadata](REJECTED_VOLUME_SEED_REVIEW_ARCHIVE.json) and
[checksum](REJECTED_VOLUME_SEED_REVIEW_SHA256SUMS.txt) are byte-identical safe
copies of the local packaging records. Their `uploaded=false` value records
the creation checkpoint and remains unchanged. The later
[actual publication receipt](publication-receipt.json) separately attests
successful uploads, server sizes/digests/states and preservation of the earlier
assets. Transfer success and the current asset count come from that server
verification, not from the packaging records. This mutable README is outside
the checksum manifest.

## Inspecting the file in Gmsh

Extract and open `volume/head-volume.msh` in Gmsh for numerical inspection.
The exact saved file is **210,476,070 bytes**, SHA-256
`7bfb96b55af3fadd81ea1409f633882f6a0249f961ef4f2a7f549a0fd2da2e67`.
Its mesh coordinates are unitless in MSH and must be interpreted using the
project's **millimetre convention**, with the unchanged source frame. Opening
the file applies no unit conversion; do not relabel those numbers as metres.
No viewer import, new render, repair or additional native solve is claimed
by packaging.

The actual mesh has **3,096,408 tetrahedra** and **902,148 nodes**, including
only **three interior nodes**. Minimum SICN is
`-1.2793193015693403e-14`, failing the unchanged **SICN ≥ 0.1** requirement.
Exact source import, boundary/orientation checks and independent saved-file
readback do not waive that quality failure or establish adequate interior
thermal resolution. The file contains no computed temperature, stress,
deposition or other physical solution fields. It is not an accepted thermal,
structural or LPBF discretisation.

## Source, evidence and scope

The archive includes the new
[sealed rejected-seed capsule](../analysis-quality-volume-seed/README.md),
English instructions, the source licence and the per-member manifest.
The underlying admitted numerical surface is
`7f0d96988684f7d36dab8f65c5b63b1919c2c2121768cf9caec466867a5c2b43`.
Its exact BIN and standard PLY are available in the
[prior surface review delivery](../analysis-quality-review-delivery/README.md)
and are not duplicated in this download.

This saved seed diagnostic is separate from the earlier
[300-second stopped volume trial](../analysis-quality-volume/README.md),
which saved no MSH. Both records retain their own outcomes. The current mesh
does not retroactively supply that earlier trial's missing final results.

The packaging-time baseline is
`75e3be21359755c20d1af1eda1b80bc3d85b9815`; the scoped file manifest identifies
the new local evidence without inventing a later repository commit. The source
is a generated bionic study, not a measured Porsche component. Historical
fidelity, full interface/channel/BCC semantics, head thermal/strength results,
material/process qualification, calibrated LPBF and manufacturing authorisation
remain open. Inspection follows the included proprietary licence.
