# Editable scan-derived CAD fragments — 4 November 2026

Three existing private, scan-derived CAD exports and their original receipts
have been collected in one [private archive](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-editable-fragments-20261104.tar.gz),
SHA-256 `f203a348b405b9e72b45914d7ebdb9a66fa6d751cfc8cae380ef6e62d7456b63`.
This is an index and preservation checkpoint: it does not add geometry or
reclassify a fragment as a complete part.

| Archive directory | Native editable file and STEP | Evidence status |
|---|---|---|
| `hub/` | `observed-hub-surfaces.FCStd`, `.step` | Two analytic open surface candidates; not a complete rotor hub. |
| `support/` | `observed-support-candidates.FCStd`, `.step` | Open support surface candidates; not a complete support. |
| `drive/` | `observed-drive-shaft.FCStd`, `.step` | Partial periodic shaft open loft. This acquired shaft patch is not established as the rotor output coupling. |

Each directory contains its original `receipt.json`. The six CAD files were
checked against their recorded native hashes before packaging. All nine files
and the checksum manifest were extracted to a fresh private directory and the
manifest passed; the release digest matches the archive hash. The native
receipts record FreeCAD 1.0.2 reread checks and an **assumed** one millimetre
per source unit, not a calibration. The files have no permission for
manufacture and no established 935 engine fit. The fragments retain their
original frames and must not be assembled together until their transforms and
functional mating datums are independently established.

The original construction programs are
[`build_hub_cad.py`](../../../twins/935-horizontal-cooling-system-f0/source/build_hub_cad.py)
for the hub and support, and
[`build_drive_cad.py`](../../../twins/935-horizontal-cooling-system-f0/source/build_drive_cad.py).
The [original-bound assembly review](ORIGINAL_BOUND_ASSEMBLY_20261028.md)
explains the unresolved rotor/drive separation and engine-envelope interference.

## Shaft-to-support frame mapping

The shaft profile and support surface reports identify the same original drive
scan. The [frame-composition program](../../../twins/935-horizontal-cooling-system-f0/source/fragment-frames-20261104/compose_drive_frames.py)
checks those reports' hashes, their common source hash, the shaft transform and
its inverse, rigid handedness and the support candidate-frame identity. It
composes shaft candidate → original drive source → support normalized frame.
Both CAD receipts use the same unverified scale assumption of one millimetre
per source unit. This numeric frame mapping is not a physical mating datum or
an assertion that the shaft belongs to a particular bearing or rotor coupling.

The [private transform receipt](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/shaft-to-support-transform.json)
has SHA-256 `11039619a1e206090b28ee919faaf4d2f96107d47a63809a9f77a39811cf0d04`.
Its output was reproduced byte-for-byte; synthetic translation composition and
reflection-rejection controls passed. Placement of the rotor remains
independent: it comes from a different scan, and the registration between the
two physical parts is not verified. A future scene must label these fragments
as open surfaces and retain that distinction.

## Open fragments placed together

The [composition program](../../../twins/935-horizontal-cooling-system-f0/source/fragment-frames-20261104/compose_step_fragments.py)
imports the hash-pinned shaft and support STEP fragments and applies the
same-scan transform to the shaft in FreeCAD 1.1.4 on the Mac. It checks input
validity, preserved surface area and a transformed vertex, then rereads the
exported STEP and FCStd. The result contains 1,056 shaft faces and two support
faces, and no solids. This is an open-surface pose study, not an assembled
bearing or torque path.

The [private editable and STEP package](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-posed-drive-fragments-20261104.tar.gz)
has SHA-256 `4b362dfd71380f553087986819beb9bc80dd64a04813fa9de2f7f2ca89cc843f`;
its files passed checksum verification after extraction. The [three-view review](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/posed-drive-fragments-review.png)
has SHA-256 `478d3d6caa62e607e25e7321d8596555c4d2fbc8bbf10526549a1ea74067436f`.
The displayed patches are spatially separated in this scan-derived frame; no
mating or contact is inferred. Dimensions, scale, assembly fit and suitability
for manufacture remain unverified. The rotor from the separate scan is not
registered by this result.

## Review against the same drive scan

The [private three-view overlay and receipt](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-drive-fragments-scan-overlay-20261104.tar.gz)
have archive SHA-256 `45f74de14f6e57595153c607b9a75e203c1d1750b52b8302aa44626423e9d679`;
its extracted files and release digest were verified. The plot places the two
fragments on separate areas of the normalized drive scan. It is a review of
coordinate transport using the **same scan** that informed the fits, not an
independent dimensional or mating validation.

The [render and distance screen](../../../twins/935-horizontal-cooling-system-f0/source/fragment-frames-20261104/render_drive_context.py)
compares tessellated CAD triangle centres to the nearest scan vertex. For 2,112
shaft samples the median upper bound is 0.1832 source unit and p95 is 0.4681;
for 94 support samples they are 0.1662 and 0.3479. Nearest-vertex distance is
an upper bound on point-to-triangle-scan distance. These numbers depend on the
tessellation and do not certify physical scale, complete scan coverage, or a
functional contact. The support crop is not asserted to be a material edge.

## PicoGK inspection overlay

The [binary-input preparer](../../../twins/935-horizontal-cooling-system-f0/source/fragment-frames-20261104/prepare_picogk_inputs.py)
converts the normalized drive scan and the two placed open-fragment
visualization meshes to binary STL, checks every float32 triangle after
readback, and pins all inputs. A first PicoGK import rejected the original
ASCII FreeCAD STL; the separate binary conversion is retained as the successful
path. The input conversion was reproduced with identical hashes.

The [PicoGK program](../../../twins/935-horizontal-cooling-system-f0/source/fragment-frames-20261104/picogk-drive-overlay/Program.cs)
imports and appends the three meshes without voxelization. It emitted 2,486,862
triangles: 2,484,656 for the scan, 2,112 for the shaft and 94 for the support.
An independent binary STL readback compared all concatenated triangle vertices
to the respective inputs exactly at float32 precision. This is an inspection
mesh, not a solid reconstruction, Boolean union, watertight assembly, physical
connection or functional twin. The [private mesh archive](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-picogk-drive-overlay-20261104.tar.gz)
has SHA-256 `fb31d926964e5b8670144b507b72600af5b3e574e3f859792c2888d6a36ec592`;
all archive files passed checksum verification after extraction. Scale,
physical registration, mating and manufacturing remain unverified.

## Open drive fragments in the provisional 935 USD scene

The [placement program](../../../twins/935-horizontal-cooling-system-f0/source/fragment-frames-20261104/assembly-placement/place_fragments.py)
uses the existing 935 assembly case's drive transform. Before placing either
fragment it checks all 2,484,656 original drive triangles against the retained
placed drive; the largest coordinate discrepancy is 0.00004951 source unit.
The shaft and support STL transformations independently retain their triangle
counts and match transformed coordinates within 0.00000763 source unit.
These are numeric checks on an assumed assembly pose, not evidence of fit.

The [USD composer](../../../twins/935-horizontal-cooling-system-f0/source/fragment-frames-20261104/assembly-placement/compose_usd.py)
adds the two open fragment meshes as separately classified inspection prims to
a layer over the existing four-component scene. It checks the base stage's
metre/Z-up metadata and explicitly sets these values on the new root layer;
the initial attempt without root metadata was rejected. Every added point was
reread exactly. The source-to-metre factor 0.001 is conditional on the
unverified one-millimetre/source-unit assumption.

The [private layer package](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-usd-drive-fragments-layer-20261104.tar.gz)
has SHA-256 `906970da881461ace16a37fa810a8d62d45de44e34e003d7136c48fb876ae2af`.
Its contents passed extraction and checksum readback. It requires the separately
retained base `assembly-inspection.usdc`, SHA-256
`22fa354baa2d69d22e21b4677625023259cd529e22708b25aeba0affe87f10ce`,
from `exports-002/` in the [original-bound assembly archive](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-original-bound-assembly-20261028.tar.zst).
Place that base next to the USDA layer. The [private overview](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/assembly-fragments-review.png)
has SHA-256 `3523382b130b53314f74877b0307302f9d2a91978b98fb0b7e0bfc1e871d9254`.
The engine and shroud remain placeholders; rotor/drive mating, scale and
physical operation are not established.

## PicoGK flange witnesses in the same scene

The [witness layer composer](../../../twins/935-horizontal-cooling-system-f0/source/fragment-frames-20261104/assembly-placement/add_flange_witnesses.py)
adds the eight existing PicoGK lower-flange location witnesses to the prior
fragment scene. The witness receipt pins the same placed drive scan used by
the original 935 assembly. The witnesses contain 221,304 triangles and remain
explicitly classified as location aids, not mounting material or verified
through-holes. All witness coordinates and triangle indices were reread from
the USD; a fresh rerun reproduced the layer byte-for-byte.

The [private two-layer package](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-usd-drive-fragments-witnesses-20261104.tar.gz)
has SHA-256 `acbec1767e379122cc0d997e76044158b2f22e9d37307dc0a77967a7556fc769`.
Its files passed extraction and checksum readback and its release digest
matches. It requires the same separately retained original-bound USDC base
specified above; place that file beside both USDA layers before opening the
witness layer. The added geometry does not resolve the engine mount, hub
connection, physical scale or internal transmission.

## Provisional rotor revolution with the added fragments

The [animation composer](../../../twins/935-horizontal-cooling-system-f0/source/fragment-frames-20261104/assembly-placement/animate_scene.py)
layers a single Z rotation on the original rotor candidate while retaining the
two open drive fragments and eight flange witnesses. The existing, pinned
240-phase rigid surface sweep is used only for the same original rotor, drive
and provisional shroud. It does not assess collision with the added witness
meshes or open CAD fragments. Frames 0–240 contain 241 samples at 1.5°
intervals; 60 frames per second is an arbitrary preview rate, not a measured
operating speed. The shaft, support and witnesses are fixed inspection geometry;
no transmission ratio or physical joint is modelled.

All 241 rotor transforms matched an independent point-rotation calculation to
within `1.25e-16` stage metre; a separate readback checked that all ten added
inspection prims remain stationary at five sampled times. The stage metre uses
the same unverified source-unit conversion. The [private animation-layer package](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-usd-drive-fragments-animation-20261104.tar.gz)
has SHA-256 `7340f6d385d63c74b40a7771dab1144d79767cdb9079cf01a7c1c902003df45d`.
Its files passed extraction and checksum readback. Restore the separately
retained original-bound USDC base beside its three layers, as described above.
The result is a kinematic visualization, not validated physical operation.

## Rigid surface sweep against added geometry

The [FCL screen](../../../twins/935-horizontal-cooling-system-f0/source/fragment-frames-20261104/assembly-placement/sweep_added_surfaces.py)
checks the retained original-bound rotor at 240 phases against the placed open
shaft, open support and eight combined flange-location witnesses. It uses the
same assumed Z axis and pose as the prior sweep, with a conservative bound on
between-phase rotor displacement. Synthetic separated, crossing and moving
triangle fixtures passed. An independent second run reproduced all 720 phase
results.

| Fixed geometry | Sampled surface crossings | Minimum sampled surface distance | Continuous rigid-surface lower bound |
|---|---:|---:|---:|
| Open shaft fragment | 0 | 189.559 | 187.677 |
| Open support fragments | 0 | 15.944 | 14.063 |
| Flange-location witnesses | 0 | 146.000 | 144.118 |

Distances are uncalibrated source units. Bounds concern only the listed triangle
surfaces in the assumed pose. The flange witnesses are artificial inspection
markers, not material surfaces. This screen does not test enclosed solids,
thermal growth, deflection, rotor mounting, actual bearings or 935 fit. It does
not establish a functional clearance or a manufactured part.

The [private detailed report](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/sweep-added-surfaces-replay-20261104.json)
has SHA-256 `d08d47693a3e6f26e660e6113bea1f661fe7885b40ec4c0f71302293e20c7709`.

## Relation between the observed shaft and support-axis candidates

The [axis-relation screen](../../../twins/935-horizontal-cooling-system-f0/source/fragment-frames-20261104/axis_relation.py)
compares the candidate shaft axis with the fitted support-bore arc axis in the
common scan-derived frame. Their acute angle is 1.956°. The shortest distance
between the infinitely extended fitted axes is 62.978 source units; restricting
the calculation to the shaft profile's three fitted axial sections and the
support model's fitted axial span gives 243.710 source units. These are axis
centreline distances, not surface clearances or physical dimensions. The
source units and both fitted axes remain unverified as functional datums.

This supports keeping the observed fragments as separate evidence objects; it
does not rule out an unobserved shaft extension, bearing or other linkage.
Parallel, endpoint-limited and crossing-segment analytic controls passed. The
[private receipt](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/axis-relation-20261104.json)
has SHA-256 `0160109c6aef9484e37ae410c21987d95d660f4c1afc8c10a16bf64c4ac25905`.

## Cross-band opening-pattern consistency

The [band-consistency screen](../../../twins/935-horizontal-cooling-system-f0/source/fragment-frames-20261104/flange_band_consistency.py)
uses the eight previously paired lower-flange openings. It fits one 2D proper
rigid transform between their independently fitted centres in the two axial
bands, then repeats the fit while withholding one pair at a time. The
centre-set mean translation is 0.1921 source unit, with fitted in-plane rotation
0.00448°. The in-sample RMS and maximum residual are 0.0790 and 0.1496 source
unit; leave-one-out RMS and maximum are 0.0967 and 0.1838. Raw paired-centre
shifts range from 0.1218 to 0.2620 source unit.

The bands come from the same scan, the opening pairing follows visual seeds,
and each sidewall fit uses many correlated triangles. These results screen fit
consistency only: they do not establish a machined pattern, through-holes, an
axial taper, independent measurement uncertainty or manufacturing tolerance.
Rigid-transform, leave-one-out and rank-deficient synthetic controls passed.
The [private report](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/flange-band-consistency-20261104.json)
has SHA-256 `059558161ffe9a1460249b33c453915c759c32edf7ee1f824e91ea5d36621df7`.

## Independent placed-CAD vertex review

The [independent FreeCAD reviewer](../../../twins/935-horizontal-cooling-system-f0/source/fragment-frames-20261104/review_placed_vertices.py)
compares all 1,584 ordered shaft BRep vertices with the original STEP vertices
transformed by the pinned same-scan matrix; the largest coordinate error is
`7.461e-14` source unit. All eight ordered support vertices are unchanged.
It checks the two named objects remain open, rejects incorrect input hashes
without writing a report, and ran on FreeCAD 1.1.4. This strengthens the
coordinate-transport evidence only: vertices alone do not independently
certify curved face interiors, assembly fit or physical scale.
The [private receipt](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/independent-vertex-review-20261104.json)
has SHA-256 `b812fa5f80e8a0b336e82579f6e0b12f5a1504cba8f42d45295f5d4c97e2ca2e`.
