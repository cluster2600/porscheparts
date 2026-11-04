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
