# Plane0 clipped proposal: rejected raw-geometry download

The completed local ZIP is **28,705,026 bytes**, SHA-256
`8a152bcf3749e7436ceff00833b49162503e8111674da08c522fc3c80bedf4ca`.
It contains **129 members / 113,690,682 uncompressed bytes**. This is geometry
review only: **3,112 faces still fail the unchanged 2/29 surface threshold**
(2,396 cap, 716 mixed-plane). The assumed z=0 finishing datum is not OEM data.
No accepted volume mesh or engine/material/process qualification follows.

Publication status: **Uploaded to the existing draft/prerelease; GitHub digests, sizes and uploaded states match all three files. All 39 preceding asset records remain unchanged (42 total). No complete second binary download was performed**.
Independent complete archive review: **PASS: all 129 members were independently streamed and compared byte-for-byte with their sources; SHA-256, CRC, fixed metadata and closure match**.

Downloads in the existing draft release:

- [962-bore95-plane0-rejected-review.zip](https://github.com/cluster2600/porscheparts/releases/download/untagged-3dc4679a17c16edf0fb4/962-bore95-plane0-rejected-review.zip)
- [Complete member manifest](https://github.com/cluster2600/porscheparts/releases/download/untagged-3dc4679a17c16edf0fb4/962-bore95-plane0-rejected-review-members.json)
- [SHA256SUMS](https://github.com/cluster2600/porscheparts/releases/download/untagged-3dc4679a17c16edf0fb4/962-bore95-plane0-rejected-review-SHA256SUMS.txt)

Open `geometry/head-plane0-exact.ply` with **one unit = one millimetre**; PLY does
not standardize physical units. Its standard binary-little-endian layout retains
double xyz coordinates and uchar-count3/uint32 oriented triangles. The completed
independent format readback checks every one of the **869,355 coordinate rows**
and **1,739,126 ordered oriented faces** against the exact 962SURF1 BIN—no
transform, rescaling, remeshing or rounding. PLY is 43,473,608 bytes, SHA
`884eceaaac5added16caa97c8fbd1f166dd361862010159d9d39d2dff6d95a36`.
The BIN SHA is `d2af68ee8ab242e992b15b6e2a93ac7e487972277af7f31a8496a7036ec32240`.

The separate LE-u64 coordinate-ID file uses UINT64_MAX for 3,508 new plane
coordinates; all other IDs refer to pre-clip input1f9 local rows. It is not
original894, Porsche or construction-history identity. Its 865,847 retained
coordinate matches were checked byte-for-byte in the complete array census.

The ZIP includes the three complete public capsules **atomic-cavity-plane-clip**,
**atomic-cavity-plane-clip-readback** and **material-conductivity-witness**, with
editable sources and existing attribution. These are a selected review subset;
the separate conductivity bars are not computed fields on this head. This small
companion does not duplicate those capsules or the large geometry/archive files.

`package-review-at-build.json` records completed root packaging with `uploaded=false`.
That original ledger remains unchanged; the later `archive-peer-review.json` and
`publication-receipt.json` document independent checking and actual server
metadata separately. Source-reuse and source-peer records retain their earlier
preparation-time pending flags; the two later exact format reports record the
completed full-byte result. All original hashes and exact-copy associations are
listed in `original-records.json`.

Full clipped global topology/intersection/cap-hole/features/openings and two-sided
CUB checks remain incomplete. The **0.0625 mm** representation budget and volume
SICN **0.1** gate are unchanged. No clipped HXT or head PDE was run; there is no
fitment, strength, thermal performance, LPBF calibration or manufacturing approval.

`python3 -B verify.py` checks only this sealed companion’s byte hashes and
complete closure. It does
not reopen the ZIP, export geometry, rerun native calculations or qualify a part.
