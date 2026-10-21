# Bore95 numerical geometry review download

The new `962-bionic-bore-95-analysis-quality-mm-review.zip` is uploaded to the
[existing draft study release](https://github.com/cluster2600/porscheparts/releases/tag/untagged-3dc4679a17c16edf0fb4).
Draft access requires authentication. Its local size is **111,004,443 bytes**,
with SHA-256
`370701eca6999aed58b7508ea13bd7210f60701a2048b06c40e0cca4baa9d993`.
It has 100 ZIP members: 99 payloads and their complete byte/hash manifest.
The [separate server-verification receipt](publication-receipt.json) confirms
all three new assets' uploaded states, exact sizes and SHA-256 digests. The
draft now contains **21 assets**; every earlier asset's ID, name, size, digest
and state remains unchanged. The tag, URL and draft/prerelease state are also
unchanged. This is a draft review delivery, not a functional release.

The [archive metadata](ANALYSIS_QUALITY_REVIEW_ARCHIVE.json),
[checksum](ANALYSIS_QUALITY_REVIEW_SHA256SUMS.txt) and
[PLY readback receipt](PLY-independent-readback.json) are byte-identical copies
of the safe local packaging records. Their packaging-time `uploaded=false`
and pending-publication status are preserved as historical creation facts.
They attest local construction and checking. The later
[publication receipt](publication-receipt.json) separately attests server
verification and preservation of the eighteen earlier assets; it does not
rewrite those original packaging-time records.
This navigational README is outside any checksum manifest.

## Inspecting the actual new surface

Open `geometry/quality-candidate-exact.ply` from the archive in a viewer that
supports standard binary PLY. It contains 902,145 vertices as little-endian
`double x/y/z`, and 1,804,706 oriented faces as an unsigned 8-bit list count
`3` followed by three little-endian unsigned 32-bit indices.

**Coordinates are millimetres.** The PLY header states this explicitly, but
PLY carries no standardised unit/up-axis metadata. Blender or another viewer
can initially interpret those numbers as metres; configure import/viewing
scale so one stored unit represents **1 mm = 0.001 m**, retaining the source
Z-up frame. Do not relabel the raw coordinates as metres. No viewer import,
render or physical validation is claimed by the format export.

The PLY is **45,113,083 bytes**, SHA-256
`041429dff8dc9a88948735e2bfab79628cd8d2a4b4cdf340f9aa312e94315b32`.
The archive also retains the exact `962SURF1` BIN, SHA-256
`7f0d96988684f7d36dab8f65c5b63b1919c2c2121768cf9caec466867a5c2b43`.
`FORMAT.md` documents its binary64 points and unsigned 64-bit oriented indices.
Full independent readback checks all **21,651,480 coordinate bytes**, every
oriented face, counts and exact bounds. No coordinate rounding, welding,
rotation, scaling or geometry regeneration occurs.

## Evidence and remaining limits

The archive contains the sealed
[quality candidate](../analysis-quality-candidate/README.md),
[continuous-distance](../analysis-quality-distance/README.md) and
[stopped volume-trial](../analysis-quality-volume/README.md) records, plus
the source licence and separately labelled USD diagnostic projection.
The surface passes its scoped quality/topology/opening-patch screens and
the 0.25 mm continuous envelope: the symmetric upper bound is
0.07192052963427972 mm. These findings concern the generated bionic study;
“original source” is not a measured Porsche component.

The HXT volume trial stopped at its 300-second deadline without saving
`head-volume.msh`; no MSH is included. Final tetrahedral counts, minimum
SICN/Jacobian, actual boundary/internal orientation, saved-mesh readback and
interior thermal DOFs remain unknown/unrun. There is no accepted volume mesh
or head thermal, structural or LPBF result. Complete historical fidelity,
interface/channel/BCC mapping, material/process qualification and manufacturing
authorisation remain open. The USD diagnostics concern the earlier unchanged
source-exact export, not a conversion or conformance repair of this new surface.

The packaging-time published baseline is
`14735ae57cd773b9110f30d500620dc9ebca777b`; new evidence is identified by its
current file manifest without an invented later repository commit.
Download is for numerical geometry
inspection only, under the included proprietary licence.
