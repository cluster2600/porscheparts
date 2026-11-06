# 3D scan inventory — intake 2026-09-28 (Wave-1)

Register: `catalog/scans/` (new register, see its README). The raw files
(100–202 MB) stay outside Git, recorded by absolute path + SHA-256 + size
+ mtime, recomputed on host `kali2` on 2026-09-28 with `sha256sum`.
The prior geometric triage is in
[obj-scan-intake-2026-09-27.md](obj-scan-intake-2026-09-27.md); this page
records the digest and positions each scan as potential evidence.

None of these scans is a certified measurement: they are raw
`SINGLE_SOURCE` inputs. A dimension exists only after promotion through the
`containers/obj-metrology-f15` pipeline (identity, scale, segmentation), then an
`M64-ACQ-*` acquisition with declared uncertainty. The OBJ files carry no
unit; mm is an assumed convention throughout.

## Complete inventory (5 files, 4 unique payloads)

| Record | Payload | Bytes | mtime | Declared | Track | Registration state |
|---|---|---|---|---|---|---|
| `SCAN-FAN-DRIVE-0P21MM` | `6c0b12d4…` | 105,090,339 | 2026-09-27 | 0.21 mm (filename) | engine / cooling | **new record**, no upstream source — provenance and licence **unknown** |
| `SCAN-917-ENGINE-CASE-W-CYL-0P5MM` | `428c4143…` | 107,128,223 | 2026-08-31 | 0.5 mm (vendor page + name) | engine / case-cylinders | already source `SRC-LOCAL-917-ENGINE-CASE-CYLINDERS-SCAN` and in the 917 pipeline; record = digest of the **two identical paths** |
| `SCAN-935-XTREME-CYLINDER-HEAD` | `4623d5d3…` | 104,598,077 | 2026-08-31 | unknown | engine / cylinder head-valves | already source `SRC-WOLFE-CLASSICS-935-BILLET-CYLINDER-HEAD-SCAN`, in the `reference-935-cylinder-head` pipeline |
| `SCAN-964-WIDEBODY-UNDERSIDE` | `f3979091…` | 210,972,101 | 2026-09-25 | unknown | body | **new record**, provenance and licence **unknown** |
| (2nd path of the 917 payload) | `428c4143…` | 107,128,223 | 2026-08-31 | same | — | `Library/Mobile Documents/com~apple~CloudDocs/Downloads/917+engine+case+w+cyl+0.5mm.obj` — **byte-identical** to the 917 raw scan: copied, not scanned twice |

Intake assumption corrected: the iCloud file `917+engine+case+w+cyl+0.5mm.obj`
is **not** a distinct high-resolution variant; its SHA-256 is that of the 917
scan already referenced by the 917 work packages (F11 `EXPECTED_SHA256`,
F15, F17). It is recorded as `other_paths` of the 917 record, with no duplicate
source record. (Note: the real path under iCloud is
`…/com~apple~CloudDocs/Downloads/917+engine+case+w+cyl+0.5mm.obj`.)

## What each scan proves — and does not prove

| Scan | Can prove (after F15 promotion) | Does not prove |
|---|---|---|
| Fan Drive 0.21 mm | Raw geometry of the fan drive: pulley and tooth positions/diameters, axial height, layout → feeds `M64-ACQ-0005` (fan geometry, zone M64-Z-CL) and calibrates the F2 airflow study (`work/simulation/993-fan-baseline`) | Tooth count (already unresolved at the 0.21 mm pitch, angular coverage 0.03–0.24), a conclusive stage ratio (idler pulley + elastic belt in the field: observed ratio 1.7–2.0 vs 1:1.6 `FACT_public`, not conclusive), scale, airflow |
| 917 case + cylinders | Flat-12 case/cylinder reference for geometry review and comparative metrology; already consumed by the 917 twin (F11/F15/F17) | 917 variant identity, real accuracy of the declared 0.5 mm, 993/M64 compatibility, functional interfaces |
| 935 cylinder head | Ground truth of an air-cooled billet cylinder head: interfaces, register, chamber, studs; feeds the `reference-935-cylinder-head` twin (already F1_interface_proxy, parametric F1 valves) | 993 compatibility, material, mass, accuracy; derived STLs = `fit-check-only` |
| 964 underside | Overall shape of the widebody underside, possible mounting-environment reference on the body-shell side (body track, to compare with `SRC-CARGEOMETRY-993-BODY`) | Dimensions: 176 unsorted bodies, unverified scale, unresolved provenance; nothing for the engine |

## Engine subsystems gaining measured ground truth

- **Cooling (fan)**: Fan Drive 0.21 mm — first dedicated scan of the M64
  cooling circuit; potentially unblocks `M64-ACQ-0005`
  (blocked today: wheel geometry not published, only the airflow of 1,010 l/s
  at ≈6,100 rpm is public).
- **Cylinders / cylinder heads**: 935 cylinder head (in the pipeline, F1) and
  917 case+cylinders (external case reference); the 935 is the direct candidate
  for the cylinder-head/M64 chain, the 917 remains a morphological reference.
- **Body** (outside the engine): 964 underside, unsorted.

## Next metrology steps (existing pipeline `containers/obj-metrology-f15`)

1. **Fan Drive** — run the F15 pipeline on the raw file mounted read-only
   (`--source …/Fan+Drive+0.21mm.obj`, contract to create on the model of
   `twins/reference-917-engine/scan-segmentation-f15.json`): digest,
   bounds, components. Then a plane section re-oriented perpendicular to
   each axis (locally fitted plane), crest/valley thresholding for the tooth
   count, and separation of idler pulley / belt before any ratio. Expected
   output: promotion of `M64-ACQ-0005` to F2 status with declared uncertainty.
   Non-technical prerequisite: resolve the scan's provenance and licence.
2. **935 cylinder head** — already passed F15; next documented step:
   interface metrology on a calibrated section and a visual re-check of the
   unit (the "probably mm" envelope remains unconfirmed).
3. **917 case** — rerun F15 only if a new semantic segmentation contract
   requires it; F11 integrity is already sealed on `428c4143…`.
4. **964 underside** — sort by component before any acquisition record;
   file it in the body track, do not bring it into the engine contracts.
5. For every record whose `rights.license = unknown` (Fan Drive, 964): publish,
   redistribute or resell nothing until the scan's origin is documented.
   Honestly marked unknown, not invented.

## Integrity and traceability

- `sha256sum` (coreutils, host kali2) on the 5 paths, 2026-09-28;
  sizes and mtime via `stat`. The two 917 duplicates verified equal byte for
  byte by common digest.
- The 935 and 917 digests match the `EXPECTED_SHA256` of the twins'
  `prepare_scan.py` — no drift since entering the pipeline.
- Validation: `python3 scripts/validate_scans.py` (new, covered by
  `make check`) — 4 valid records.
