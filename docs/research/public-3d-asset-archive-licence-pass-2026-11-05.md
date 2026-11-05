# Public 3D asset licence pass from archive captures, 2026-11-05

Follows [the 2026-10-15 audit](public-3d-asset-licence-audit-2026-10-15.md) on
issue #1. On 2026-11-05 the owner decided that Internet Archive (Wayback
Machine) captures of the original model page count as provenance evidence.
This pass applies that decision to the records the earlier audit left
unverified.

No model file was downloaded or imported. No Thingiverse, Printables, Cults or
3D GO page was requested directly, and no Cloudflare challenge was met or
bypassed: only `web.archive.org` (CDX index and raw `id_` captures) was queried,
with a plain HTTP client and its default `User-Agent`.

## Schema change

`rights.archive_capture` is a new optional object in
[`source.schema.json`](../../catalog/schemas/source.schema.json), checked by
`scripts/validate_sources.py`. It holds `status` (`archive_verified`),
`capture_url`, `capture_timestamp`, `read_on`, `license_as_read` and `author`.
A licence read this way is written `archive-verified-<licence>`. The validator
refuses an `archive-verified-` licence without a capture, a capture without
such a licence, a capture URL that is not `web.archive.org/web/<14 digits>/…`,
and a timestamp that differs from the one in the URL.

`rights.redistribution` follows the 2026-10-15 rule: it moves only where the
licence text read on the capture grants redistribution (CC BY and CC BY-SA give
`attribution_required`).

## Captures examined

| original page | records | CDX result (HTTP 200 page captures) | licence on capture | outcome |
|---|---|---|---|---|
| Thingiverse thing 2006970 | `SRC-RENN3D-REAR-MAIN-SEAL-TOOL` | 2017-04-24 (`20170424143508`), server-rendered page, 101,191 bytes, SHA-256 `8a7927c7…ad1714f` | "Porsche 911 rear main seal tool by stagsimon is licensed under the Creative Commons - Attribution - Share Alike license", link to `creativecommons.org/licenses/by-sa/3.0/` | **archive-verified** `CC-BY-SA-3.0`, author stagsimon |
| Printables model 1369571 | `SRC-PRINTABLES-964-993-CONSOLE-SWITCH-TAB`, `SRC-RENN3D-CONSOLE-SWITCH-TAB-REPAIR` | 2025-09-12 (`20250912155210`), 181,151 bytes, SHA-256 `9149e09b…9c86925` | title "… by 9khil"; embedded page data gives licence id 1, which the same capture names "Creative Commons — Attribution" (no version) | **archive-verified** `CC-BY-unversioned`, author 9khil; remix of Thingiverse thing 4826642 "Porsche 964 Center" by Naischnotz (CC Attribution) |
| Thingiverse thing 2152823 | `SRC-RENN3D-POLLEN-FILTER-COVER-TABS`, `SRC-THINGIVERSE-993-POLLEN-TABS` | 2024-05-27, 2024-12-09 | none: the post-2020 Thingiverse page is a JavaScript shell; it names the author (LimeyBoy) in its title but carries no licence | not verified |
| Thingiverse thing 4349486 | `SRC-RENN3D-CUSTOM-SPLIT-GRILLE-BAR` | 2023-09-28, 2023-06-05, 2024-06-16 (`/files`) | none (same shell; title names LimeyBoy) | not verified |
| Thingiverse thing 3752304 | `SRC-THINGIVERSE-993-REAR-SPEAKER-SHIM` | 2022-01-09 | none: 2,467-byte shell, no title | not verified |
| Thingiverse things 3143518, 3180872, 4427893 | phone mount (2 records), seat-back button, RS Momo horn ring | only `/zip` redirects (HTTP 301) | — | not verified |
| Thingiverse things 6901857, 5787387 | speaker adapter frames, clutch bleeder bracket | no capture | — | not verified |
| `api.thingiverse.com/things/<id>` for the nine things | — | no capture | — | not verified |
| Printables model 1507503 | `SRC-RENN3D-CENTER-CONSOLE-CUP-HOLDER`, `SRC-3DGO-993-964-CUP-HOLDER` | no capture (CDX and availability API) | — | not verified |
| Cults console repair, door pocket reinforcement, door scan, seat hinge cover, wheel centre cap | five Cults records | no capture | — | not verified |
| GrabCAD tweeter bracket, Thangs designer pages, Sketchfab barn-find scan, Wolfe 993 Turbo scan, CGTrader dashboard | their records | no capture | — | not verified |

The forum leads (Rennlist, Pelican, PFF, Carpokes, PistonHeads) publish no
model page with a licence field, so an archive capture of the thread cannot
supply one; they were not queried.

## Result

- **3 records archive-verified**, from 2 original pages.
- **0 licence contradictions** with Renn 3D Parts: thing 2006970 is CC BY-SA
  as Renn declares, with the version (3.0) now fixed; Printables 1369571 is CC
  Attribution as Renn declares. No entry was added to
  `catalog/registers/contradictions.json`.
- One attribution gap: Renn 3D Parts credits only 9khil for the switch tab, but
  the Printables capture shows it remixes Naischnotz's Thingiverse thing
  4826642, so attribution must name both. The Cults record
  `SRC-CULTS-964-993-CONSOLE-REPAIR-STL` (URL slug `porsche-964-center`) may be
  a re-upload of that same Naischnotz original; this is not established and
  the record was not changed.
- 46 of the 49 previously unverified records stay unverified. Thingiverse pages
  archived after its 2020 redesign carry no licence in their HTML, so only
  pre-2020 captures can verify a Thingiverse licence.

## Capture hashes

| capture | bytes | SHA-256 |
|---|---:|---|
| `https://web.archive.org/web/20170424143508id_/http://www.thingiverse.com:80/thing:2006970` | 101,191 | `8a7927c7699f2a8893c229b231dada022582d22b0772da251c6503945ad1714f` |
| `https://web.archive.org/web/20250912155210id_/https://www.printables.com/model/1369571-porsche-964-993-center-console-switch-tab` | 181,151 | `9149e09be9dbad2d6a8b1166e83186e81cd5b5f7ff03dda9d11e2bc989c86925` |

The captured HTML itself is not committed.
