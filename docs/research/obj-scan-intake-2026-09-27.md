# OBJ scan import (Mac) — intake 2026-09-27

Inventory, provenance and integrity of the automotive scan meshes imported
under `/home/lolman/imports/mac-obj`, triaged by
`work/obj-intake-20260927/triage_obj.py` (host `python3`, trimesh 5.1.0,
pymeshlab 2025.7.post1). Machine-readable report:
`work/obj-intake-20260927/reports/obj-intake.json`.

The source trees are treated as read-only raw evidence. Nothing here is a
measurement certificate: scans stay `SINGLE_SOURCE` raw inputs until a twin
pipeline (contracts `M64-ACQ-*`) derives dimensions with stated uncertainty.
OBJ files carry no unit metadata; mm is assumed (scanner convention) and flagged.

## Mesh inventory (unique payloads)

| id | sha256 (prefix) | bytes | triangles | bbox (assumed mm) | state |
|---|---|---|---|---|---|
| 935-xtreme-cylinder-head | `4623d5d3b73fe3d0` | 104,598,077 | 2,466,040 | 197.9 × 198.8 × 227.1 | 3 identical copies, including the repository working copy (`work/mesh-repair-935-head/.../935-xtreme-cylinder-head-working-copy.obj`) → **already in the pipeline** |
| 917-engine-case-with-cylinders | `428c4143d073f833` | 107,128,223 | 2,465,879 | 1,002.2 × 768.3 × 739.8 | 2 identical copies (iCloud + raw-scans) → **already in the 917 pipeline** (`EXPECTED_SHA256` of the 917 `prepare_scan.py` = this hash) |
| 964-widebody-underside | `f397909141e5af25` | 210,972,101 | 4,684,929 | 2,074.7 × 4,283.5 × 894.4 | new, 176 bodies — body scan, not yet sorted by component |
| **Fan Drive 0.21 mm** | `6c0b12d4dd782fd4` | 105,090,339 | 2,484,656 | 325.2 × 398.6 × 450.1 | **new engine asset** → feeds the `M64-ACQ-0005` gap (fan geometry) |

Duplicates: the `Downloads/` files are byte-identical to the corresponding
`raw-scans/` copies (935: `Downloads/935+Xtreme+Cyl+head.obj` =
`raw-scans/wolfe-classics-935-cylinder-head/original/…` = repository working
copy; 917: iCloud file = `raw-scans/917-engine/original/…`); the complete
duplication groups are in the JSON. None of these scans has a
`catalog/sources/` record yet — to be created with the acquisition that uses
them, not before.

Mesh state (trimesh): the 4 payloads are not watertight; non-manifold edges
(>2 shared faces) 1.21–2.32 M per scan, 7 k–27 k boundary edges, multiple
bodies (1 for Fan Drive, 3–4 for 917/935, 176 for the 964) — expected raw
scanner output, no repair applied here.

## Fan Drive (direct interest for the M64 twin)

- A single body, 1,256,836 vertices / 2,484,656 triangles, unknown orientation
  (no scan frame attached). Not watertight: 1.24 M non-manifold edges,
  7,013 boundary edges. Usable geometry will come from slice sections, not
  from a direct remesh.
- Two clear clusters at z ≈ 205 (probably two pulleys/toothed wheels of the
  fan belt drive):
  - lower component: 206.6 × 251.4 × 212.9, XY centroid (26.3; −92.1), r max 146.9;
  - upper component: 265.9 × 243.0 × 237.2, XY centroid (−80.2; 51.7), r max 192.7.
- Radius ratio ≈ 1.31 for the first batch of sections — consistent with a
  reduction stage, **not yet** confirmed as the 1:1.6 ratio (`FACT_public`);
  the elastic belt and the idler pulley distort the sections. To be redone in a
  plane perpendicular to each axis.

### Per-component extraction (2nd pass, `fan_drive_features.py`)

Segmentation by z/y clustering + radial section profiles
(`work/obj-intake-20260927/fan-drive-extract.json`). Assumed mm units.

- Lower toothed disc (XY axis ≈ (−11.6; −187.1)): total axial height
  67.9; tooth-tip OD ≈ 127.6; minimal hole at the tooth plane
  ⌀ ≈ 5.3 but angular coverage of the void only 0.34 at z<0 →
  probably partly obstructed or a scan artefact, **pilot not
  confirmed**. The void edges per slice (void r≈21–29, rmax
  43–62 above the tooth plane) suggest a conical hub rather than a clean
  cylindrical bore.
- Upper pulley (center derived per slice, ≈ (−84; 55)): axial height
  202.2; OD varies by slice ⌀219–256 (conical flanks / multiple
  flanges); hole ⌀ ≈ 17.3 at z∈[346,354] (1st percentile, lower bound).
- **Tooth count: NOT resolved.** The angular coverage of the tooth bands is
  low (0.03–0.24 over 720 sectors): at the 0.21 mm scan pitch,
  teeth of ~1–3 mm are undersampled and the dominant harmonics
  (6–16 depending on the band) are inconsistent between slices. A reliable
  count will require a plane section re-oriented perpendicular to
  each axis (locally fitted plane), then crest/valley thresholding — or a
  physical part.
- Stage ratio: toothed ⌀ ≈ 127.6 vs pulley ⌀ 219–256 → ≈ 1.7–2.0, of the same
  order as 1:1.6 (`FACT_public`) but **not conclusive** (idler pulley and
  elastic belt included in the scan).

Next step: segment the bodies separately, re-orient each axis,
redo the tooth count on a calibrated section, then a source record and
`F2` promotion of the `m64_cooling_fan` component.

## Integrity

- Host: `kali2`, trimesh 5.1.0, pymeshlab 2025.7.post1, python 3.14
  (JSON report).
- Full sha256 in the JSON; no byte modified in the source trees.
- Nothing is yet registered in `catalog/sources/` (deliberate: the source
  record will be born with the acquisition that uses the scan).
