# PET 107-xx / 202-xx per-line transcription - exhaust and charge air

Date: 2026-09-29. Lane: `wave2/pet107-20260929`. Owner: m64-researcher.

Closes the `pet_reference_gaps` entry of
`twins/m64-engine-system/bom/m64-bom-v1.json`: per-line transcription of the
993 Turbo PET groups covering exhaust and charge air, from **local sources
only**.

## Sources used (all local)

| Source | What it provides |
| --- | --- |
| `data/oem-listed.json` of `/home/lolman/repos/porschefanatics.com` (commit `f5dc1c2`) | Machine transcription of two independent PET catalogue tables: `pet-993-pdf-rsworkshop` (KAT 17) and `pet-classic-993` (Porsche Classic KAT 517 USA). Per line: part number, description, position, illustration, page, catalogue. **No quantity field, no dimensions.** Registered as `catalog/sources/src-porschefanatics-993-oem-listed-pet.json`. |
| `data/993-manual/torque-specs.json` (same repo) | p. 61 exhaust-system torques, already registered in `catalog/manual/993-workshop-manual-measurements.json`. |
| Existing fiches `src-porsche-austria-993-107-45-pet`, `src-porsche-pet-993-turbo-heat-exchanger-202-10`, `src-porschefanatics-993-turbo-pet`, `src-pet-993-kat17-pdf` | Official/audited context and cross-checks. |

A line is treated as **confirmed** when both independent catalogue tables
list the same number at the same position, or a single table plus a
registered official read. Single-table lines are marked as such. Quantity per
car is never taken from the transcription (the field does not exist there);
it is recorded from the engine architecture and flagged.

## Transcribed lines

| PET illustration | Pos | Part number | Description | Status | BOM line |
| --- | --- | --- | --- | --- | --- |
| 202-10 (exhaust, Turbo) | 1 | 993 211 039 55 (rev A) / -56 in KAT 517 | heat exchanger, left | confirmed (both tables) | M64B-IN-003 |
| 202-10 | 2 | 993 211 040 55 (rev A) / -56 in KAT 517 | heat exchanger, right | confirmed (both tables) | M64B-IN-003 |
| 202-10 | 3-12 | 993 111 195 00, 999 084 052 02, 999 085 001 02, 944 111 205 01, 999 084 627 02, 993 211 036 56, 993 211 313 52/53, 999 512 539 00/01, 900 025 007 02/03, 900 076 025 02/064 02 | sealing rings, nuts, heating tube, sleeves, clamps, washers | context only (both tables) | M64B-IN-003 interfaces |
| 202-15 (exhaust, cat section) | 14 | 993 113 213 57 | catalytic converter (one bank) | **single-source locally** (KAT 17 table only) | M64B-IN-004 |
| 202-15 | 15 | 993 113 214 57 / -58 in KAT 517 | catalytic converter (other bank) | confirmed at position; suffix pair unresolved | M64B-IN-004 |
| 202-15 | 20, 22 | 993 606 128 01, 993 606 127 01 | oxygen sensors | context | M64B-IN-004 |
| 107-45 (charge air cooler) | 1 | 993 110 330 53 | charge air cooler | confirmed (both tables) | M64B-IC-001 |
| 107-45 | 2 | 993 110 340 53, -54 | air guide | confirmed | M64B-IC-004 |
| 107-45 | 5 | 993 110 110 50, -52 | bracket | confirmed | M64B-IC-005 |
| 107-45 | 10 | 993 110 111 50 | sleeve | confirmed | (fastener-adjacent) |
| 107-45 | 12 | 993 606 114 00 | temperature sensor | confirmed (matches Austria KAT 17 read) | (sensor) |
| 107-45 | 19 | 993 110 633 56, 993 110 632 56 | pressure hose L/R | confirmed | M64B-IC-002 / -003 |
| 107-45 | 20, 21 | 999 512 648 02, 999 512 647 02 | hose clamps | confirmed | (fasteners) |
| 107-20 (turbocharging) | 1 | 993 110 062 50, -51 | intake manifold | confirmed (both tables) | charge-air context |
| 107-20 | 18, 21 | 993 110 631 54; 993 110 630 52, -53 | intake manifolds | confirmed (both tables) | charge-air context |
| 107-20 | 10 | 993 110 337 50, -51 | shut-off valve | confirmed | charge-air context |
| 107-20 | 6, 14 | 993 606 124 01; 993 606 103 00, -01 | MAF, pressure transmitter | confirmed | sensors |
| 107-20 | 31, 32 | 993 110 113 52, 993 110 114 51 | hoses | confirmed | context |

Fiches created: `catalog/parts/993-exh-heat-exchanger-pair-pet-0001.json`,
`catalog/parts/993-exh-cat-converter-pair-pet-0001.json`,
`catalog/parts/993-ca-charge-pipe-set-pet-0001.json`,
`catalog/parts/993-ca-turbo-intake-manifold-pet-0001.json`.
Source fiche: `catalog/sources/src-porschefanatics-993-oem-listed-pet.json`.

## Unresolvable locally (kept out of the catalogue)

- **Wastegate actuator Porsche number** (M64B-TR-003): no line matching
  wastegate/actuator exists in any local 993 `107-xx` or `202-xx` PET
  transcription; the only "actuator" in the whole 993 dataset is a central
  locking part (803-30). Stays null; BorgWarner reference remains
  single-source from the research lane.
- **Left/right assignment of the two catalytic converters** (202-15 pos 14/15):
  the transcription does not annotate sides; bank assignment stays assumed.
- **Supersession relations** between the suffix pairs (-55/-56, -57/-58,
  -50/-52, -53/-54): both suffixes are recorded as listed; which supersedes
  which, and for which build date, is not in the local data.
- **Quantity per car from the PET itself**: `oem-listed.json` carries no
  quantity field; the Austria fiche gives quantities for 107-45 only.
- **All dimensions, wall thicknesses, flow cross-sections, pressure ratings,
  cell counts, pressure drop**: the PET tables carry none of these; every
  `dims` field in the BOM stays `missing` on these lines.
- **Intercooler effectiveness data** (M64B-IC-001): still absent locally.

## Method note

`data/oem-listed.json` lines have `depth: "listed"` (machine-transcribed, not
read in context). Where both independent catalogue tables agree, and where a
registered official read exists (Austria KAT 17 for 107-45; Porsche Classic
read for 202-10), the identity is treated as confirmed at the nomenclature
level — consistent with the standing caveat in
`docs/PORSCHEFANATICS_993_TURBO_AUDIT.md` that PET lines establish identity,
not geometry, fitment or safety.
