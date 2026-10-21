# Bore95 original and normal-bearing USD review download

[Download the 35,081,708-byte review ZIP](https://github.com/cluster2600/porscheparts/releases/download/untagged-3dc4679a17c16edf0fb4/962-head-bore95-normal-usd-review-en.zip)
from the existing **draft/prerelease**. GitHub access to a draft requires the
appropriate signed-in account. SHA-256:
`a372b88b285fdd3be0463d58e235440307f0f40d66cd84d8792379208d6178d1`.

The matching [checksum](962-head-bore95-normal-usd-review-en-SHA256SUMS.txt)
and [member manifest](962-head-bore95-normal-usd-review-en-manifest.json) are
also release assets. The [publication receipt](publication-receipt.json)
verifies GitHub's sizes, SHA-256 digests and uploaded states for all three;
all 30 earlier assets and the release tag, name, URL and draft flags remain
unchanged. The release now contains 33 assets.

The archive's 30 members contain the original USDC, one normal-bearing `.usd`
alias, the complete [sealed evidence capsule](../usd-face-normals-bore95/README.md),
project helpers, three byte-copy tests, licence and English guidance. The alias
has binary USDC content and is byte-identical to its normal-bearing source;
the installed profile API requires the supported `.usd` suffix. Both complete
model files and all other source-backed members pass independent full-byte
comparison. Every member's size, CRC32 and SHA-256 is checked in the
[root](package-root-review.json) and [peer](package-peer-review.json) reviews.
The manifest covers every other member and deliberately excludes itself.

Read the [actual validation results](../../../USD_NORMALS_ENGINEERING.md)
before interpreting the models. The normal-only derivative retains the
original 902,145 vertices, 1,804,706 faces and 744 deficient analysis triangles.
The separate rejected endpoint003 geometry with 266 deficient triangles is
absent from this archive and remains in its earlier download. Use the retained
millimetre frame. No units, topology, material or physics schemas were changed.

The eight minimum checks and generic/Geometry/Physics CPU reports pass; the
substantive formal profile retains six failed features and its ignored-policy
ledger. These are software asset checks. Head strength, thermal performance,
material qualification, calibrated LPBF, computed twin fields, PhysicsNeMo and
manufacturing authorization remain open.

[ARCHIVE_REVIEW.json](ARCHIVE_REVIEW.json) preserves its packaging-time
`uploaded=false` flag. The later publication receipt records the actual upload
without changing that historical record. No raw runtime, upstream API source,
private transport capture or duplicate normal-bearing USDC is bundled.
