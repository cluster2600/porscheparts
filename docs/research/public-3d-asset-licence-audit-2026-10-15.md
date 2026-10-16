# Public 3D asset licence audit, 2026-10-15

This pass answers issue #1 ("audit the public 3D models and scans of the Porsche
993") on the two points the owner left open on 2026-08-29:

- (a) licences must be verified on the **original** publication, not on a
  secondary index;
- (b) scale anomalies must be handled, notably the speaker frames.

No file was downloaded, bought or imported. No record gains `measured`,
`fitted` or a `verified_against` entry from this pass.

## What was audited

The 62 source records whose `content_types` include `scan`, `cad` or `mesh` and
whose `source_type` is not `manufacturer`: 41 community, 18 marketplace,
2 dataset and 1 official record. The 41 `manufacturer` records that also carry
those content types describe scanning or reverse-engineering services and
finished products; none publishes a reusable 3D file (for example
`SRC-SHAPEWAYS-993-SUN-VISOR-GOPRO-CLIP` is an article about a printed part,
with no CAD or STL file), so they are out of scope.

| kind | records | with a file (free, paid or behind a login) |
|---|---:|---:|
| scan (laser, photogrammetry, videogrammetry, point cloud) | 13 | 7 (two more are scan stores with no 993 item) |
| CAD (STEP or print mesh designed as a part) | 30 | 30, including the Renn 3D Parts archive and its nine part records |
| CAD lead (forum thread, no public file) | 17 | 0 |
| artistic mesh (modelled for appearance) | 1 | 1 |
| CAD dataset (generic cars, not a 993) | 1 | 1 |
| game model | **0** | — |

**No game-model record exists.** The word `game` in the URL of
`SRC-CULTS-964-993-CONSOLE-REPAIR-STL` is a Cults marketplace category; the
asset is a repair print mesh.

## Method

1. Each site's `robots.txt` was checked before any of its pages was requested,
   with the page-reading tool and, where it was refused, a plain HTTP client
   (curl with its default `User-Agent`).
   A page was read only when `robots.txt` was readable and did not exclude
   Claude agents. No `User-Agent` was changed and nothing was bulk-fetched.
2. The licence was taken from the original publication only. A licence shown by
   Renn 3D Parts or 3D GO is a secondary declaration.
3. `rights.redistribution` follows from a licence read on the original page:
   CC-BY gives `attribution_required`, CC-BY-NC gives `noncommercial_only`,
   CC0 or public domain gives `allowed`, a standard, private-use or
   all-rights-reserved licence gives `prohibited`, and anything else gives
   `unknown`. One exception: where a twin record read the original page and
   recorded a more restrictive value, that value is kept (`prohibited` rather
   than `unknown`).
4. `rights.license` wording shows the verification state. A licence verified on
   the original page uses the bare identifier, as in the existing
   `SRC-SKETCHFAB-993-GT2-RAW-SCAN` record (`CC-BY-4.0`). A licence known only
   from the Renn 3D Parts archive is written
   `archive-reported-<licence>-primary-page-not-verified`. A licence copied
   from a twin record that read the original page is written
   `twin-recorded-<licence>-not-reread`.

### Access observed on 2026-10-15

| site | `robots.txt` | original pages |
|---|---|---|
| thingiverse.com | HTTP 403, Cloudflare bot challenge, to the page-reading tool and to a plain HTTP client | not requested: permission for automated agents could not be established |
| printables.com | readable; allows all agents except `/world/` | HTTP 403 with a JavaScript challenge ("Enable JavaScript and cookies to continue") |
| cults3d.com | HTTP 403, Cloudflare bot challenge | not requested |
| 3dgo.app | HTTP 403, Cloudflare bot challenge | not requested |
| sketchfab.com | readable; no rule on `/3d-models/` | read |
| renn3dparts.com | readable; allows all except account pages and `/api/` | speaker-frame page re-read |
| web.archive.org | — | the index (CDX) answered, but the page-reading tool refuses `web.archive.org`, so no capture was read |

## Results

### Licences verified on the original page

Only one licence was verified in this pass:

- `SRC-SKETCHFAB-RWB-993`: the Sketchfab page shows "CC Attribution", linked to
  `creativecommons.org/licenses/by/4.0/`, author GORDEYKOMARK, published
  20 March 2024, free download, 125.3k triangles. The record now says
  `CC-BY-4.0`, `attribution_required`. The page claims "All proportions are
  respected" but gives no unit, scale or dimension, so `dimensional_accuracy`
  moved from `declared` to `visual_only`.

Four other records carry a licence recorded in an earlier pass as read on the
original page, not re-read now: `SRC-SKETCHFAB-993-GT2-RAW-SCAN`
(`CC-BY-4.0`, 2026-08-28), `SRC-DRIVAERNET-PLUSPLUS` (CC-BY-NC-4.0 data and MIT
code, 2026-08-28), `SRC-CULTS-993-WHEEL-CENTER-CAP` (`Cults-Private-Use`,
2026-08-29) and `SRC-CGTRADER-993-DASHBOARD-SCALE-MODEL` (CGTrader editorial
licence, 2026-08-30).

### Licences that are still only declarations

None of the eleven Thingiverse and Printables originals could be read
(Thingiverse things 6901857, 4349486, 3143518, 2152823, 2006970, 5787387,
3180872, 3752304 and 4427893; Printables models 1507503 and 1369571), and the
Cults page behind `SRC-CULTS-964-993-CONSOLE-REPAIR-STL` was not requested. As
a result:

- the nine `SRC-RENN3D-*` records now carry
  `archive-reported-<licence>-primary-page-not-verified` and redistribution
  `unknown`. Before this pass the two public-domain records said `allowed`, five
  CC-BY or CC-BY-SA records said `attribution_required` and the CC-BY-NC and
  CC-BY-NC-SA records said `noncommercial_only`, all on the archive's word;
- the Thingiverse and Printables records whose original page is the record URL
  now record access `access_blocked`, `not_accessed`, 2026-10-15.
  `SRC-THINGIVERSE-993-REAR-SPEAKER-SHIM` was `not_checked` with no access date
  and now has these values too.

The Internet Archive index lists captures of some originals. They were **not
read**, so they are leads only: thing 4349486 (2023-09-28), thing 2152823
(2024-05-27 and 2024-12-09), thing 2006970 (2017-04-24), thing 3752304
(2022-01-09) and Printables 1369571 (2025-09-12). Things 3143518, 3180872 and
4427893 have captures of their ZIP download redirect only, not of the page.
Things 6901857 and 5787387 and Printables 1507503 have no capture. Even once
read, an archived capture shows the licence at its capture date, not the
current licence on the original page.

### Duplicate and twin records

The records were cross-referenced in `notes` ("same asset as …"), and none was
deleted.

| records | same | rights after this pass |
|---|---|---|
| `SRC-RENN3D-CENTER-CONSOLE-CUP-HOLDER`, `SRC-3DGO-993-964-CUP-HOLDER` | Printables 1507503 | both `unknown` (the Renn 3D record said `allowed`); the two secondary declarations also differ, CC0 (3D GO) against a public-domain mark (Renn 3D), which are not the same instrument |
| `SRC-RENN3D-GAUGE-RING-PHONE-MOUNT`, `SRC-THINGIVERSE-993-PHONE-MOUNT` | thing 3143518 | both `unknown`; same licence string |
| `SRC-RENN3D-POLLEN-FILTER-COVER-TABS`, `SRC-THINGIVERSE-993-POLLEN-TABS` | thing 2152823 | both `unknown`; same licence string; evidence level C vs D still disagrees |
| `SRC-RENN3D-CONSOLE-SWITCH-TAB-REPAIR`, `SRC-PRINTABLES-964-993-CONSOLE-SWITCH-TAB` | Printables 1369571 | both `unknown`; same licence string |
| `SRC-CULTS-993-WHEEL-CENTER-CAP`, `SRC-CULTS-993-WHEEL-CENTER-CAP-CAD` | same Cults URL | `Cults-Private-Use` (read 2026-08-29) and `twin-recorded-Cults-Private-Use-not-reread`, both `prohibited`: the only licence ever recorded for the page, and the more restrictive value; the CAD record's own 2026-08-30 read said the licence was not verified |
| `SRC-WOLFE-993-TURBO-EXTERIOR-SCAN`, `SRC-WOLFE-CLASSICS-993-TURBO-SCAN` | same Wolfe URL | both `unknown`; licence wording differs (terms not displayed, 2026-08-29, against terms not published); evidence level D vs C still disagrees |
| `SRC-RENNLIST-993-DIY-3D-BITS`, `SRC-RENNLIST-993-3D-PRINTED-DIY-BITS` | same thread | both `unknown` |
| `SRC-RENNLIST-993-SEAT-RAIL-BUSHING-CAD`, `SRC-RENNLIST-993-SEAT-RAIL-BUSHING-STL` | same thread and ZIP | both `unknown` |
| `SRC-RENNLIST-993-WINDSHIELD-CAD-TEMPLATES`, `SRC-RENNLIST-993-WINDSHIELD-TEMPLATES` | same thread | both `unknown`; `declared` vs `measured` still disagrees |
| `SRC-PFF-993-SUNROOF-REPRODUCTION`, `SRC-PFF-993-SUNROOF-REVERSE-ENGINEERING` | same thread | `prohibited` vs `unknown`, cross-referenced, not re-read; both block redistribution |

Possible duplicate, not established: the first file of
`SRC-CULTS-964-993-CONSOLE-REPAIR-STL` has 63.679 × 5.5 mm extents, which match
the 67.000 × 63.678 × 5.500 mm envelope of `SRC-RENN3D-CONSOLE-SWITCH-TAB-REPAIR`,
but the two records name different authors.

### Scale anomalies

- **Speaker frames**, `SRC-RENN3D-HIFI-SPEAKER-ADAPTER-FRAMES`. The Renn 3D
  page re-read on 2026-10-15 still declares 2152.040 × 1437.940 × 253.976 mm
  and gives no unit in the owner notes. The original thing 6901857 could not be
  read, so the licence is not confirmed, so no mesh was downloaded and the
  bounding box was not recomputed. Divided by 10 the envelope would be
  215.2 × 143.8 × 25.4 mm, the right order of magnitude for a frame around a
  4×6 in speaker, but that is an untested hypothesis. **Scale unresolved;
  excluded from use until checked.** Row 5 of
  [phase-1-recherche-allemande.md](phase-1-recherche-allemande.md) stays
  `Blocked`.
- **Door scan**, `SRC-CULTS-993-DOOR-SCAN`. The declared 2266.18 mm length is
  more than half the 4,245 mm overall length and almost the 2,272 mm wheelbase
  in `SRC-ASTRA-993-TYPE-APPROVAL-DIMENSIONS`, although a door sits between the
  wheel arches. `dimensional_accuracy` moved from `declared` to `unknown`. The
  real door length is not sourced here.
- Already flagged and unchanged: `SRC-CGTRADER-993-DASHBOARD-SCALE-MODEL` is
  drawn for a 1/8 scale model, and the two Wolfe engine scans bought by the
  owner (917 case, 935 head) are OBJ files with no declared unit.

### Independent dimensional verification

Independent dimensional verification is out of scope. The owner does not buy
or measure parts, so no declared dimension in this table has been checked
against a part. A declared value is challenged only when it contradicts an
official dimension already in the catalogue, as for the door scan.

## Blocked records

- **HTTP 403 (Rennlist):** sixteen records, from
  `SRC-RENNLIST-993-3D-PRINTED-DIY-BITS` to
  `SRC-RENNLIST-993-WINDSHIELD-TEMPLATES` in the table. They were not
  re-attempted. `SRC-RENNLIST-993-RS-HOT-AIR-BYPASS-TUBE-CAD-LEAD` was read in
  an earlier pass.
- **HTTP 403 (Cults detail pages, 2026-08-30):**
  `SRC-CULTS-993-DOOR-POCKET-REINFORCEMENT`, `SRC-CULTS-993-SEAT-HINGE-COVER-CAD`.
- **Bot challenge on 2026-10-15:** Thingiverse (four Thingiverse records and
  the originals of seven Renn 3D records), Printables (two originals), Cults
  and 3D GO.
- **Login required:** `SRC-GRABCAD-964-993-TWEETER-GRILL-BRACKET`,
  `SRC-CARPOKES-993-CLIMATE-KNOB-INSERT`.
- **Paid:** `SRC-WOLFE-993-TURBO-EXTERIOR-SCAN`,
  `SRC-WOLFE-CLASSICS-993-TURBO-SCAN`, `SRC-SKETCHFAB-993-BARN-FIND-SCAN`,
  `SRC-CULTS-993-DOOR-SCAN`, `SRC-CULTS-993-WHEEL-CENTER-CAP`,
  `SRC-CULTS-993-WHEEL-CENTER-CAP-CAD`, `SRC-CULTS-993-SEAT-HINGE-COVER-CAD`,
  `SRC-THANGS-993-LOWER-CONSOLE-TABS`, `SRC-THANGS-993-UPPER-CONSOLE-TABS`,
  `SRC-CGTRADER-993-DASHBOARD-SCALE-MODEL`, and the two scan stores without a
  993 item (`SRC-BREMAR-3D-SCAN-STORE`, `SRC-CAR-CLOUDS-POINT-CLOUDS`).
- **Digest-pinned, not edited:** `SRC-PELICAN-993-FAN-SHROUD-DELETE-CAD-LEAD`
  and `SRC-WOLFE-CLASSICS-935-BILLET-CYLINDER-HEAD-SCAN`. The 935 record says
  `allowed` on the owner's statement of an open licence, while the 917 scan
  bought from the same vendor, `SRC-LOCAL-917-ENGINE-CASE-CYLINDERS-SCAN`,
  says `unknown` on the same kind of statement. That disagreement stays
  visible.

## Inventory

"Earlier pass only" means the access fields come from an August 2026 pass and
were not re-checked today.

| record | kind | original page read? | licence as found | redistribution | scale status | remaining blocker |
|---|---|---|---|---|---|---|
| [`SRC-3DGO-993-964-CUP-HOLDER`](../../catalog/sources/src-3dgo-993-964-cup-holder.json) | CAD (print mesh), aggregator index | no: model 1507503; Printables page answered HTTP 403 with a JavaScript challenge on 2026-10-15 | `aggregator-reported-cc0-primary-page-not-verified` | `unknown` | archive bbox 224.803 x 92.300 x 69.051 mm, unverified | licence on Printables 1507503 |
| [`SRC-BREMAR-3D-SCAN-STORE`](../../catalog/sources/src-bremar-3d-scan-store.json) | scan store (no 993 item) | earlier pass only (2026-08-28); not re-read | `vendor-terms-not-published-on-product-page` | `unknown` | not applicable | no 993 asset; paid |
| [`SRC-CAR-CLOUDS-POINT-CLOUDS`](../../catalog/sources/src-car-clouds-point-clouds.json) | scan store, point clouds (no 993) | earlier pass only (2026-08-28); not re-read | `commercial-licence-agreement-not-read` | `unknown` | not applicable | no 993 asset; paid |
| [`SRC-CARPOKES-993-CLIMATE-KNOB-INSERT`](../../catalog/sources/src-carpokes-993-climate-knob-insert.json) | CAD (forum attachment) | blocked: login required | `forum-download-license-not-confirmed` | `unknown` | unknown | login; licence of attachment |
| [`SRC-CGTRADER-993-DASHBOARD-SCALE-MODEL`](../../catalog/sources/src-cgtrader-993-dashboard-scale-model.json) | CAD for a 1/8 scale model (false positive) | blocked: paid asset; page not re-read, nothing bought | `CGTrader-editorial-license-purchase-required` | `prohibited` | 1/8 scale model, not 993 geometry | paid; not usable as 993 geometry |
| [`SRC-CULTS-964-993-CONSOLE-REPAIR-STL`](../../catalog/sources/src-cults-964-993-console-repair-stl.json) | CAD (print mesh) | no: Cults robots.txt behind a Cloudflare challenge on 2026-10-15, page not requested | `platform-license-field-empty` | `unknown` | file bboxes declared (27 x 63.679 x 5.5 mm and 33.238 x 61.999 x 5.580 mm), unverified | licence field empty; Cults unreadable; possible re-upload of the Renn 3D switch tab |
| [`SRC-CULTS-993-DOOR-POCKET-REINFORCEMENT`](../../catalog/sources/src-cults-993-door-pocket-reinforcement.json) | CAD (print mesh) | blocked: HTTP 403 on 2026-08-30; not re-attempted | `platform-license-field-unverified` | `prohibited` | declared 75.184 x 12.7 x 73.660 mm, unverified | licence field not read; record says prohibited on an unverified field |
| [`SRC-CULTS-993-DOOR-SCAN`](../../catalog/sources/src-cults-993-door-scan.json) | scan (commercial) | blocked: paid asset; page not re-read, nothing bought; Cults unreadable | `commercial-marketplace-license-not-verified` | `unknown` | declared 2266.18 x 573.24 x 1033.44 mm, implausible against the 4,245 mm car (SRC-ASTRA-993-TYPE-APPROVAL-DIMENSIONS); unknown | paid; scale anomaly; modified G-body door |
| [`SRC-CULTS-993-SEAT-HINGE-COVER-CAD`](../../catalog/sources/src-cults-993-seat-hinge-cover-cad.json) | CAD (print mesh) | blocked: HTTP 403 on 2026-08-30; not re-attempted | `commercial-marketplace-license-not-verified` | `unknown` | unknown | paid; licence |
| [`SRC-CULTS-993-WHEEL-CENTER-CAP-CAD`](../../catalog/sources/src-cults-993-wheel-center-cap-cad.json) | CAD (STEP and STL), duplicate | blocked: paid asset; page not re-read, nothing bought | `twin-recorded-Cults-Private-Use-not-reread` | `prohibited` | no dimensions published | same as twin |
| [`SRC-CULTS-993-WHEEL-CENTER-CAP`](../../catalog/sources/src-cults-993-wheel-center-cap.json) | CAD (STEP and STL) | blocked: paid asset; page not re-read, nothing bought (Cults-Private-Use recorded 2026-08-29) | `Cults-Private-Use` | `prohibited` | no dimensions published | private-use licence; wheel part needs engineering review |
| [`SRC-DRIVAERNET-PLUSPLUS`](../../catalog/sources/src-drivaernet-plusplus.json) | CAD and CFD dataset (generic cars, no 993) | earlier pass only (2026-08-28); not re-read | `CC-BY-NC-4.0-data-and-MIT-code` | `noncommercial_only` | dataset geometry, not 993 | not 993; non-commercial data |
| [`SRC-GRABCAD-964-993-TWEETER-GRILL-BRACKET`](../../catalog/sources/src-grabcad-964-993-tweeter-grill-bracket.json) | CAD | blocked: login required | `grabcad-user-content-rights-not-verified` | `unknown` | unknown | login; licence |
| [`SRC-LMS-993-GT2-EVO-WHOLE-CAR-SCAN`](../../catalog/sources/src-lms-993-gt2-evo-whole-car-scan.json) | scan lead (video only) | earlier pass only (2026-08-30); not re-read | `video-and-scan-rights-not-verified` | `unknown` | no file published | no file; rights |
| [`SRC-LOCAL-917-ENGINE-CASE-CYLINDERS-SCAN`](../../catalog/sources/src-local-917-engine-case-cylinders-scan.json) | scan (917, bought by the owner, local copy) | direct download 2026-08-31 | `open-reuse-user-confirmed; exact-license-identifier-not-captured` | `unknown` | OBJ units undeclared; 0.5 mm vendor claim | not 993; exact licence identifier not captured |
| [`SRC-OTTO-MODELS-993-LASER-SCAN`](../../catalog/sources/src-otto-models-993-laser-scan.json) | scan lead (no file) | earlier pass only (2026-08-29); not re-read | `forum-content-rights-unclear` | `unknown` | no file published | no file |
| [`SRC-PELICAN-993-BUMPERETTE-DELETE-CAD`](../../catalog/sources/src-pelican-993-bumperette-delete-cad.json) | CAD lead (no file) | earlier pass only (2026-08-29); not re-read | `all-rights-reserved-forum-content` | `prohibited` | no file published | no file |
| [`SRC-PELICAN-993-FAN-SHROUD-DELETE-CAD-LEAD`](../../catalog/sources/src-pelican-993-fan-shroud-delete-cad-lead.json) | CAD request (no file) | earlier pass only (2026-08-29); not re-read | `forum-user-content-rights-unclear` | `unknown` | no file published | no file; record is digest-pinned and was not edited |
| [`SRC-PFF-993-ALARM-MODULE-MEASUREMENTS-TOOL`](../../catalog/sources/src-pff-993-alarm-module-measurements-tool.json) | CAD lead (STL offered privately) | earlier pass only (2026-08-30); not re-read | `forum-content-and-attachment-rights-not-verified` | `unknown` | no file published | no public file |
| [`SRC-PFF-993-CASSETTE-CONSOLE-3D-PRINT`](../../catalog/sources/src-pff-993-cassette-console-3d-print.json) | CAD lead (no file) | earlier pass only (2026-08-30); not re-read | `forum-content-rights-reserved` | `prohibited` | no file published | no file |
| [`SRC-PFF-993-SUNROOF-REPRODUCTION`](../../catalog/sources/src-pff-993-sunroof-reproduction.json) | CAD lead (no file) | earlier pass only (2026-08-29); not re-read | `all-rights-reserved-forum-content` | `prohibited` | no file published | no file; twin SRC-PFF-993-SUNROOF-REVERSE-ENGINEERING says unknown |
| [`SRC-PORSCHE-MUSEUM-917001-RECONSTRUCTION`](../../catalog/sources/src-porsche-museum-917001-reconstruction.json) | scan-to-CAD precedent (official, no file) | earlier pass only (2026-09-01); not re-read | `porsche-ag-copyright-reference-only` | `prohibited` | no file published | no file; Porsche AG copyright |
| [`SRC-PRINTABLES-964-993-CONSOLE-SWITCH-TAB`](../../catalog/sources/src-printables-964-993-console-switch-tab.json) | CAD (print mesh) | no: model 1369571; Printables page answered HTTP 403 with a JavaScript challenge on 2026-10-15 | `archive-reported-CC-BY-primary-page-not-verified` | `unknown` | unknown | licence on Printables 1369571 |
| [`SRC-RENN3D-CENTER-CONSOLE-CUP-HOLDER`](../../catalog/sources/src-renn3d-center-console-cup-holder.json) | CAD (print mesh), secondary archive | no: model 1507503; Printables page answered HTTP 403 with a JavaScript challenge on 2026-10-15 | `archive-reported-public-domain-primary-page-not-verified` | `unknown` | archive bbox 224.803 x 92.300 x 69.051 mm, unverified | licence on Printables 1507503 |
| [`SRC-RENN3D-CONSOLE-SWITCH-TAB-REPAIR`](../../catalog/sources/src-renn3d-console-switch-tab-repair.json) | CAD (print mesh), secondary archive | no: model 1369571; Printables page answered HTTP 403 with a JavaScript challenge on 2026-10-15 | `archive-reported-CC-BY-primary-page-not-verified` | `unknown` | archive bbox 67.000 x 63.678 x 5.500 mm, unverified | licence on Printables 1369571 |
| [`SRC-RENN3D-CUSTOM-SPLIT-GRILLE-BAR`](../../catalog/sources/src-renn3d-custom-split-grille-bar.json) | CAD (print mesh), secondary archive | no: thing 4349486; Thingiverse robots.txt behind a Cloudflare challenge on 2026-10-15, page not requested | `archive-reported-CC-BY-NC-SA-primary-page-not-verified` | `unknown` | archive bbox 355.934 x 140.000 x 18.805 mm, unverified | licence on thing 4349486 |
| [`SRC-RENN3D-GAUGE-RING-PHONE-MOUNT`](../../catalog/sources/src-renn3d-gauge-ring-phone-mount.json) | CAD (print mesh), secondary archive | no: thing 3143518; Thingiverse robots.txt behind a Cloudflare challenge on 2026-10-15, page not requested | `archive-reported-CC-BY-primary-page-not-verified` | `unknown` | archive bbox 136.013 x 91.999 x 35.520 mm, unverified | licence on thing 3143518 |
| [`SRC-RENN3D-HIFI-SPEAKER-ADAPTER-FRAMES`](../../catalog/sources/src-renn3d-hifi-speaker-adapter-frames.json) | CAD (print mesh), secondary archive | no: thing 6901857; Thingiverse robots.txt behind a Cloudflare challenge on 2026-10-15, page not requested; Renn 3D page re-read 2026-10-15 | `archive-reported-public-domain-primary-page-not-verified` | `unknown` | archive bbox 2152.040 x 1437.940 x 253.976 mm, implausible; scale unresolved, excluded from use | licence on thing 6901857; scale |
| [`SRC-RENN3D-POLLEN-FILTER-COVER-TABS`](../../catalog/sources/src-renn3d-pollen-filter-cover-tabs.json) | CAD (print mesh), secondary archive | no: thing 2152823; Thingiverse robots.txt behind a Cloudflare challenge on 2026-10-15, page not requested | `archive-reported-CC-BY-primary-page-not-verified` | `unknown` | archive bbox 30.700 x 18.000 x 10.800 mm, unverified | licence on thing 2152823 |
| [`SRC-RENN3D-REAR-MAIN-SEAL-TOOL`](../../catalog/sources/src-renn3d-rear-main-seal-tool.json) | CAD (print mesh, workshop tool), secondary archive | no: thing 2006970; Thingiverse robots.txt behind a Cloudflare challenge on 2026-10-15, page not requested | `archive-reported-CC-BY-SA-primary-page-not-verified` | `unknown` | archive bbox 225.299 x 208.077 x 45.000 mm, unverified | licence on thing 2006970 |
| [`SRC-RENN3D-REMOTE-CLUTCH-BLEEDER-BRACKET`](../../catalog/sources/src-renn3d-remote-clutch-bleeder-bracket.json) | CAD (print mesh), secondary archive | no: thing 5787387; Thingiverse robots.txt behind a Cloudflare challenge on 2026-10-15, page not requested | `archive-reported-CC-BY-NC-primary-page-not-verified` | `unknown` | archive bbox 50.000 x 49.081 x 28.442 mm, unverified | licence on thing 5787387; clutch-system safety review |
| [`SRC-RENN3D-SEAT-BACK-RELEASE-BUTTON`](../../catalog/sources/src-renn3d-seat-back-release-button.json) | CAD (print mesh), secondary archive | no: thing 3180872; Thingiverse robots.txt behind a Cloudflare challenge on 2026-10-15, page not requested | `archive-reported-CC-BY-primary-page-not-verified` | `unknown` | archive bbox 40.130 x 37.500 x 26.000 mm, unverified | licence on thing 3180872; seat safety review |
| [`SRC-RENN3DPARTS-993-OPEN-FILES`](../../catalog/sources/src-renn3dparts-993-open-files.json) | secondary archive of nine CAD print meshes | archive page: earlier pass only (2026-08-30); originals as in the nine part rows | `mixed-per-part-license-declared-by-archive` | `unknown` | see part rows | all nine original licences |
| [`SRC-RENNLIST-993-3D-PRINTED-DIY-BITS`](../../catalog/sources/src-rennlist-993-3d-printed-diy-bits.json) | index thread of CAD links (duplicate) | blocked: Rennlist HTTP 403 in earlier passes; not re-attempted | `forum-content-and-linked-files-rights-not-verified` | `unknown` | no file published | Rennlist 403; each linked original |
| [`SRC-RENNLIST-993-ALTERNATOR-INSULATOR-PHOTOGRAMMETRY`](../../catalog/sources/src-rennlist-993-alternator-insulator-photogrammetry.json) | scan lead (failed photogrammetry, no file) | blocked: Rennlist HTTP 403 in earlier passes; not re-attempted | `forum-content-rights-not-verified` | `unknown` | no file published | no file |
| [`SRC-RENNLIST-993-BUMPERETTE-DELETE-CAD`](../../catalog/sources/src-rennlist-993-bumperette-delete-cad.json) | CAD lead (Shapeways design, no file) | blocked: Rennlist HTTP 403 in earlier passes; not re-attempted | `forum-user-content-and-marketplace-rights-unclear` | `unknown` | unknown | no file; Shapeways terms |
| [`SRC-RENNLIST-993-DIY-3D-BITS`](../../catalog/sources/src-rennlist-993-diy-3d-bits.json) | index thread of CAD links (duplicate) | blocked: Rennlist HTTP 403 in earlier passes; not re-attempted | `mixed-community-links-reference-only` | `unknown` | no file published | Rennlist 403; each linked original |
| [`SRC-RENNLIST-993-DOOR-POCKET-DIMENSION-LEAD`](../../catalog/sources/src-rennlist-993-door-pocket-dimension-lead.json) | CAD lead (no file) | blocked: Rennlist HTTP 403 in earlier passes; not re-attempted | `forum-user-content-rights-unclear` | `unknown` | forum figures only | no file |
| [`SRC-RENNLIST-993-DOOR-POCKET-REINFORCEMENT`](../../catalog/sources/src-rennlist-993-door-pocket-reinforcement.json) | CAD lead (no file) | blocked: Rennlist HTTP 403 in earlier passes; not re-attempted | `forum-user-content-rights-unclear` | `unknown` | no file published | no file |
| [`SRC-RENNLIST-993-DOOR-SPEAKER-POD`](../../catalog/sources/src-rennlist-993-door-speaker-pod.json) | CAD lead (no file) | blocked: Rennlist HTTP 403 in earlier passes; not re-attempted | `forum-user-content-rights-unclear` | `unknown` | forum figures only | no file |
| [`SRC-RENNLIST-993-HVAC-BUTTONS-CAD`](../../catalog/sources/src-rennlist-993-hvac-buttons-cad.json) | CAD lead (Shapeways design, no file) | blocked: Rennlist HTTP 403 in earlier passes; not re-attempted | `forum-user-content-rights-unclear; Shapeways-terms-not-verified` | `unknown` | no file published | no file; Shapeways terms |
| [`SRC-RENNLIST-993-REAR-SPEAKER-FRAMES-STEP`](../../catalog/sources/src-rennlist-993-rear-speaker-frames-step.json) | CAD lead (private STEP) | blocked: Rennlist HTTP 403 in earlier passes; not re-attempted | `forum-user-content-and-private-step-file-rights-unclear` | `unknown` | no file published | no public file |
| [`SRC-RENNLIST-993-REAR-SPEAKER-MOUNTS`](../../catalog/sources/src-rennlist-993-rear-speaker-mounts.json) | CAD lead (no file) | blocked: Rennlist HTTP 403 in earlier passes; not re-attempted | `forum-user-content-rights-unclear` | `unknown` | no file published | no file |
| [`SRC-RENNLIST-993-RS-HOT-AIR-BYPASS-TUBE-CAD-LEAD`](../../catalog/sources/src-rennlist-993-rs-hot-air-bypass-tube-cad-lead.json) | CAD lead (no file) | earlier pass only (2026-08-30); not re-read | `forum-content-rights-not-verified` | `unknown` | no file published | no file |
| [`SRC-RENNLIST-993-SEAT-RAIL-BUSHING-CAD`](../../catalog/sources/src-rennlist-993-seat-rail-bushing-cad.json) | CAD (forum ZIP attachment), duplicate | blocked: Rennlist HTTP 403 in earlier passes; not re-attempted | `forum-content-rights-not-verified` | `unknown` | unknown | Rennlist 403; seat part needs engineering review |
| [`SRC-RENNLIST-993-SEAT-RAIL-BUSHING-STL`](../../catalog/sources/src-rennlist-993-seat-rail-bushing-stl.json) | CAD (forum ZIP attachment), duplicate | blocked: Rennlist HTTP 403 in earlier passes; not re-attempted | `author-upload-no-explicit-license-found` | `unknown` | unknown | Rennlist 403; seat part needs engineering review |
| [`SRC-RENNLIST-993-SPLIT-GRILL-CAD`](../../catalog/sources/src-rennlist-993-split-grill-cad.json) | CAD lead (no file) | blocked: Rennlist HTTP 403 in earlier passes; not re-attempted | `forum-user-content-rights-unclear` | `unknown` | forum figures only | no file |
| [`SRC-RENNLIST-993-SWITCH-REPAIR-CAD`](../../catalog/sources/src-rennlist-993-switch-repair-cad.json) | CAD lead (no file) | blocked: Rennlist HTTP 403 in earlier passes; not re-attempted | `forum-user-content-rights-unclear` | `unknown` | no file published | no file |
| [`SRC-RENNLIST-993-WINDSHIELD-CAD-TEMPLATES`](../../catalog/sources/src-rennlist-993-windshield-cad-templates.json) | CAD (templates linked to Printables), duplicate | blocked: Rennlist HTTP 403 in earlier passes; not re-attempted | `community-file-license-not-confirmed` | `unknown` | author comparison only | Rennlist 403; Printables original not identified |
| [`SRC-RENNLIST-993-WINDSHIELD-TEMPLATES`](../../catalog/sources/src-rennlist-993-windshield-templates.json) | CAD (templates linked to Printables), duplicate | blocked: Rennlist HTTP 403 in earlier passes; not re-attempted | `forum-user-content-rights-unclear` | `unknown` | author comparison only (record says measured) | Rennlist 403; Printables original not identified |
| [`SRC-SKETCHFAB-993-BARN-FIND-SCAN`](../../catalog/sources/src-sketchfab-993-barn-find-scan.json) | scan (commercial) | blocked: paid asset; page not re-read, nothing bought | `Sketchfab-Store-Royalty-Free-terms-require-purchase-verification` | `prohibited` | 2 mm vendor claim | paid; licence after purchase |
| [`SRC-SKETCHFAB-993-GT2-RAW-SCAN`](../../catalog/sources/src-sketchfab-993-gt2-raw-scan.json) | scan (unscaled videogrammetry) | yes, earlier pass (2026-08-28); not re-read | `CC-BY-4.0` | `attribution_required` | no scale bar; shape only | rights chain: derived from a third-party video |
| [`SRC-SKETCHFAB-RWB-993`](../../catalog/sources/src-sketchfab-rwb-993.json) | artistic mesh (modelled, modified RWB body) | yes, 2026-10-15 | `CC-BY-4.0` | `attribution_required` | no units or dimensions; visual only | none for licence; not usable as geometry |
| [`SRC-THANGS-993-LOWER-CONSOLE-TABS`](../../catalog/sources/src-thangs-993-lower-console-tabs.json) | CAD (print mesh, commercial) | blocked: paid asset; page not re-read, nothing bought | `commercial-digital-download-terms-not-verified` | `unknown` | declared 87 x 12 x 31 mm, unverified | paid; licence |
| [`SRC-THANGS-993-UPPER-CONSOLE-TABS`](../../catalog/sources/src-thangs-993-upper-console-tabs.json) | CAD (print mesh, commercial) | blocked: paid asset; page not re-read, nothing bought | `commercial-digital-download-terms-not-verified` | `unknown` | declared 68 x 6 x 29 mm, unverified | paid; licence |
| [`SRC-THINGIVERSE-993-PHONE-MOUNT`](../../catalog/sources/src-thingiverse-993-phone-mount.json) | CAD (print mesh) | no: thing 3143518; Thingiverse robots.txt behind a Cloudflare challenge on 2026-10-15, page not requested | `archive-reported-CC-BY-primary-page-not-verified` | `unknown` | unknown (archive bbox in twin) | licence on thing 3143518 |
| [`SRC-THINGIVERSE-993-POLLEN-TABS`](../../catalog/sources/src-thingiverse-993-pollen-tabs.json) | CAD (print mesh) | no: thing 2152823; Thingiverse robots.txt behind a Cloudflare challenge on 2026-10-15, page not requested | `archive-reported-CC-BY-primary-page-not-verified` | `unknown` | unknown (archive bbox in twin) | licence on thing 2152823 |
| [`SRC-THINGIVERSE-993-REAR-SPEAKER-SHIM`](../../catalog/sources/src-thingiverse-993-rear-speaker-shim.json) | CAD (print mesh) | no: thing 3752304; Thingiverse robots.txt behind a Cloudflare challenge on 2026-10-15, page not requested | `thingiverse-original-page-not-verified` | `unknown` | unknown | licence on thing 3752304 |
| [`SRC-THINGIVERSE-993-RS-MOMO-HORN-RING`](../../catalog/sources/src-thingiverse-993-rs-momo-horn-ring.json) | CAD (print mesh) | no: thing 4427893; Thingiverse robots.txt behind a Cloudflare challenge on 2026-10-15, page not requested | `thingiverse-original-page-not-verified` | `unknown` | index figures (52 mm bore, 59 mm OD), unverified | licence on thing 4427893; steering-wheel part needs engineering review |
| [`SRC-WOLFE-993-TURBO-EXTERIOR-SCAN`](../../catalog/sources/src-wolfe-993-turbo-exterior-scan.json) | scan (commercial), duplicate | blocked: paid asset; page not re-read, nothing bought | `commercial-purchase-terms-not-displayed` | `unknown` | 1.76 mm vendor claim | paid; terms not published |
| [`SRC-WOLFE-CLASSICS-935-BILLET-CYLINDER-HEAD-SCAN`](../../catalog/sources/src-wolfe-classics-935-billet-cylinder-head-scan.json) | scan (935, bought by the owner) | direct download 2026-08-31 | `open-reuse-user-confirmed; exact-license-identifier-not-captured` | `allowed` | OBJ units undeclared | not 993; exact licence identifier not captured; record is digest-pinned and was not edited |
| [`SRC-WOLFE-CLASSICS-993-TURBO-SCAN`](../../catalog/sources/src-wolfe-classics-993-turbo-scan.json) | scan (commercial), duplicate | blocked: paid asset; page not re-read, nothing bought | `commercial-download-terms-not-published` | `unknown` | 1.76 mm vendor claim | paid; terms not published |

## What remains open for issue #1

- Point (a) is not met. Only `SRC-SKETCHFAB-RWB-993` had its licence confirmed
  on the original page in this pass; 49 of the 62 records still say
  redistribution `unknown`. A human reading Thingiverse, Printables
  and Cults in a browser, or an owner decision on reading Internet Archive
  captures, is the next step. A dated capture is weaker evidence than the live
  page.
- Point (b) is handled as far as the evidence allows. Both anomalies are
  flagged and excluded from use. The speaker-frame unit cannot be settled
  until the licence allows downloading the file to compute its bounding box.
