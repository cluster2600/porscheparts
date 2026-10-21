# Assembled surface: exact model and provenance download

The current research ZIP is **35,517,230 bytes**, SHA-256
`8ba6fc5dca47f3a51bc6298f481aaa334ac1096608552a96159a1d4688f6a4d5`:
**151 files / 149,167,189 uncompressed bytes**. It contains the actual assembled
BIN, lossless PLY, all seven provenance maps, assembly manifest, format sources
and complete sealed [assembly evidence](../atomic-cavity-plane-clip-cap-assembly/README.md).

Uploaded to the existing **draft/prerelease**:

- [Model ZIP](https://github.com/cluster2600/porscheparts/releases/download/untagged-3dc4679a17c16edf0fb4/962-bore95-plane0-assembled-unadmitted-review.zip)
- [Complete member manifest](https://github.com/cluster2600/porscheparts/releases/download/untagged-3dc4679a17c16edf0fb4/ASSEMBLED_PLANE0_REVIEW_MEMBERS.json)
- [SHA256SUMS](https://github.com/cluster2600/porscheparts/releases/download/untagged-3dc4679a17c16edf0fb4/ASSEMBLED_PLANE0_REVIEW_SHA256SUMS.txt)

Open `geometry/head-plane0-assembled-exact.ply` with **one unit = one millimetre**.
PLY has no standardized physical units. Every coordinate byte and all 1,743,878
ordered oriented faces match BIN `9d62eac6…`; [independent format review](format-peer-review.json)
checks the complete 871,731-row surface. The archive README documents the
962SURF1 codec and all seven little-endian uint64 maps. Their ancestry uses
d2af clipped-head local IDs and refined-cap IDs; UINT64_MAX is never an index.
The assumed z=0 finishing plane is not an OEM datum.

Necessary q, topology, complete self-intersection and scoped neighbor/opening/
local-boundary checks pass. **Two-way distance is incomplete:** the forward
upper bound is 0.03197034 mm; reverse CUB hits a native subdivision-capacity
limit and supplies no interval. The unchanged assessor refuses the pair.
The separate stronger Mesh_2 criterion still has 414 failures. No head surface,
volume/PDE, strength, material, LPBF, computed-field twin or surrogate is qualified.

[Independent archive review](archive-peer-review.json) streams all 151 members
byte-for-byte against their sources and verifies SHA-256, CRC, metadata and
complete closure. [Server metadata](publication-receipt.json) matches all three
new asset sizes, digests and uploaded states; both small sidecars downloaded
byte-for-byte. All 42 preceding asset identities remain unchanged (45 total).
A complete second remote ZIP download was not performed.

The original [package ledger](package-review-at-build.json) retains its earlier
`uploaded=false` state; the separate publication receipt records the later upload.
This small sealed companion omits the large geometry and archive. Run
`python3 -B verify.py` to check its bytes and closure; that does not repeat geometry
or qualify a part. The [engineering programme](../../../ENGINEERING_PROGRAM.md)
keeps the remaining work and earlier rejections explicit. No merge or manufacturing
release follows from this draft inspection delivery.
