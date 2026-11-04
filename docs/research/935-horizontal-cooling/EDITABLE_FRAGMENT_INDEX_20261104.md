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
