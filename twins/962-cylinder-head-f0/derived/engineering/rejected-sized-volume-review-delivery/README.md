# Rejected sized-volume review download

**Uploaded and independently verified.** The existing
[draft/prerelease page](https://github.com/cluster2600/porscheparts/releases/tag/untagged-3dc4679a17c16edf0fb4)
now contains 27 verified assets. The [publication receipt](publication-receipt.json)
records matching local/server sizes and SHA-256 digests for all three new assets,
with all 24 preceding identities, sizes, digests and states unchanged. The draft
tag and URL are preserved. Packaging-time metadata keeps `uploaded=false` unchanged.
Authenticated draft access is required.

The new `962-bionic-bore-95-rejected-sized-volume-review.zip` contains the exact
**211,471,998-byte MSH**, its
[sealed sized-trial evidence](../analysis-quality-volume-sized/README.md), an
English inspection README, the repository licence and a per-member byte/hash
manifest. It duplicates no candidate BIN/PLY. The
[earlier surface download](../analysis-quality-review-delivery/README.md),
[earlier rejected raw seed](../rejected-volume-seed-review-delivery/README.md)
and no-MSH deadline trial remain separate and unchanged.

The sized raw mesh has **3,059,463 tetrahedra**, **979,452 nodes** and
**77,307 referenced interior nodes**, with zero unreferenced nodes. Its actual
minimum SICN is **−1.2793193015693403e−14**: **284,806 elements fall below 0.1**
and two have nonpositive SICN. The unchanged 0.1 criterion rejects this mesh.
Positive Jacobians/volumes and the exact 915,458.4757034747 mm³ sum do not
establish element quality or convergence. Exact worker tetra-boundary/internal
orientation and saved-array checks remain distinct from independent saved-file
readback, which does not repeat full tetra-face sorting.

The two nonpositive-SICN cells contain only original fixed-boundary nodes;
exact node coordinates and diagnostics are retained in the capsule. Interior-
only relocation with unchanged connectivity cannot alter those cells. The
next control is only a source proposal: one default Gmsh post-export optimizer
on the saved capped software cube, allowing audited internal connectivity
changes while preserving the exact surface. No run of that proposed optimizer
on either cube or head has occurred. Unfinished Relocate3D source is excluded.

Open the MSH in **Gmsh** for inspection. MSH carries no standard unit metadata;
this study interprets its coordinate numbers as **millimetres**. Account for
that scale in import/viewer settings without relabelling the raw numbers as
metres. This is a rejected numerical mesh, with **no computed temperature,
stress, displacement or LPBF fields**. It establishes no thermal resolution,
head strength, historical fitment, process calibration or manufacturing release.

The packaging-time baseline is
`8168ff8cb9e703b43c6079c1abfa93cf34fa838b`, with a complete current per-member
manifest. The original source is an assumed generated bionic study, not a
measured original Porsche head. Exact source/runtime/native/readback hashes
and safe projections are distinguished in the sealed capsule. Private native
commands, host paths, process identifiers, runtime binaries and raw access
records are excluded. No geometry regeneration or new native solve occurs.

[Archive metadata](REJECTED_SIZED_VOLUME_REVIEW_ARCHIVE.json) binds the complete
ZIP and its internal manifest; [SHA-256 checksums](REJECTED_SIZED_VOLUME_REVIEW_SHA256SUMS.txt)
provide the ZIP checksum. These files are byte-identical copies of the external
local packaging records. Their immutable `uploaded=false` records packaging
state only; it must not be edited into a later server attestation. This README
is mutable navigation outside the archive manifest and checksum file.
