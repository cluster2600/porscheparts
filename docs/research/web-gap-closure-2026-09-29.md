# M64/60 Web Gap Closure — 2026-09-29 (wave2/research-gaps-20260929)

Web evidence hunt against the gaps recorded in
`twins/m64-engine-system/bom/coverage.md` and
`twins/m64-engine-system/program.json` (acquisition contracts
M64-ACQ-0001…0005) and `m64-bom-v1.json.known_conflicts`.

Rules applied: every number carries an exact URL and access date; forum or
marketplace values are marked community-unverified; anything unverifiable
stays missing. No local record is promoted by this document alone — fiches
under `catalog/sources/` are the registry of record.

Method note: `web_search` had no provider in this environment; search was
done via Brave Search HTML endpoint (`search.brave.com`), page reads via
`web_fetch`/curl. Access dates are the curl/fetch dates (2026-09-28/29).

Status vocabulary: **FOUND-primary** (tier-1: Porsche/BorgWarner/ETKA-PET/
manual scan/Mahle/MEHA), **FOUND-community** (community-unverified),
**NOT-FOUND** (searched, nothing citable; stays missing).

## Honest state of this pass (honest-state note)

This pass ran the searches but produced **no new citable web evidence**
carrying an exact URL and access date that closes any of the six targets.
The per-target statuses below are therefore the **repository state as of
2026-09-29** (from `docs/research/m64-public-engine-data-2026-09-27.md` and
its K16 addendum, `twins/m64-engine-system/bom/coverage.md`, and the
`wave2/metro-fan-20260929` metrology report), not new findings of this pass.
Every target whose core quantity was not found stays **OUVERTE** and the
acquisition contracts remain in force. No "in progress" search was ever
committed — there are no raw per-target findings in this branch to promote.

## Target 1 — Cylinder pitch + deck height (M64-ACQ-0004, blocks short-block F2)

Status: **OUVERTE** — nothing new found by this pass; the contract stays the
route in.

Pre-existing partial lead (not closed here): crankshaft → intermediate-bearing
spacings **133.57 mm and 78.77 mm ±0.25** are quoted from manual p.177 in
`docs/research/m64-public-engine-data-2026-09-27.md` with the explicit caveat
*"à relire visuellement"* (OCR not visually verified). Cylinder pitch and
deck height themselves remain **non publiés** in that same document.
Cylinder/head scale dims are a separate physical-metrology contract
(M64-ACQ-0001).

## Target 2 — M64 Turbo camshaft base circle / duration / lift (M64-ACQ-0002)

Status: **OUVERTE** — NOT-FOUND in the public domain.

`docs/research/m64-public-engine-data-2026-09-27.md`: « Profil de came : non
public → M64-ACQ-0002 »; `program.json` M64-Z-VT limitations echo the same.
No citable tier-1 or community cam-spec sheet surfaced in this pass.

## Target 3 — K16 compressor map 5316-988-6735/6736 (M64-ACQ-0003)

Status: **OUVERTE** — map NOT-FOUND; identity side is closed separately.

Pre-existing (K16 research lane, 2026-09-27,
`docs/research/m64-public-engine-data-2026-09-27.md` addendum): turbo identity
CLOSED with sources — left BorgWarner/KKK **5316-988-6736** (Porsche 993 123
013 51→52), right **5316-988-6735** (993 123 014 51→52), both designated
**K16-2467GGA/8.88** (CROSSCHECKED: live TurboMaster pages for 6735/6736,
BorgWarner catalogue, design911 cross-ref; fiches
`SRC-TURBOMASTER-993-K16-6736-LEFT-UNIT`,
`SRC-INVASIONAUTOPRODUCTS-993-K16-INTERNAL-DATA`). Wheel and A/R data are
recorded there (SINGLE_SOURCE / CROSSCHECKED as tagged). The **compressor map
itself remains absent from the public domain** → ACQ-0003 stays blocking;
this pass found no map.

## Target 4 — Oil system: pump delivery, tank capacity, cooler flow, pressures

Status: **OUVERTE (partiellement couverte avant cette passe)** — only one of
the four quantities is publicly sourced; geometry is untouched.

Pre-existing (brochure 993 Turbo,
`docs/research/m64-public-engine-data-2026-09-27.md`): oil capacity
**12 L with filter — FACT_public**. Dry-sump architecture FACT_public. Pump
delivery volume, cooler flow and oil pressures: NOT-FOUND in this pass;
`coverage.md` rates the oil subsystem 0 % sourced dimensions. The only
registered oil-line fiche (`catalog/sources/src-patrickmotorsports-993-turbo-
oil-return-pipes.json`, level C) explicitly publishes **no** dimensions,
pressures or flows.

## Target 5 — Conflict resolution (dry mass / compression ratio / fan airflow)

Status: **OUVERTE** — no tie-breaking source found by this pass; conflicts
stay recorded in `m64-bom-v1.json.known_conflicts`, assembly-level values
stay null (`coverage.md` item 8).

Pre-existing positions, unchanged: dry mass **232 kg vs 268 kg** — the 232 kg
figure carries FACT_public provenance (brochure 993 Turbo) but the 268 kg
variant was not refuted by any citable source in this pass; compression ratio
**9.5:1 vs 8.0:1** — 9.5:1 is FACT_public (brochure), the 8.0:1 variant
unexplained (no third source found); fan airflow — primary value **1 010 l/s
@ ≈6 100 rpm (level A, Supplément OBD 1996)**, the 1 210 l/s @ 5 750 figure
demoted to community counter-check (elferclassic, level C); the manual p.17
OCR echo ("1010 l/sec at 6,000 rpm") still needs visual re-read before F2.

## Target 6 — Fan drive identity: tooth/belt count + drive ratio (M64-ACQ-0005 identity side)

Status: **partielle** — ratio side closed pre-existing; blade/tooth count
OUVERTE.

- Drive ratio and belt drive type: **FOUND-primary** (pre-existing, not from
  this pass): toothed/VP belt drive from crankshaft, ratio ≈ **1:1.6**, Supplément
  OBD 1996 « Engine Specifications » (level A per
  `docs/research/m64-public-engine-data-2026-09-27.md`).
- Blade count and gear tooth count: **OUVERTE**. The wave-2 metrology pass on
  `Fan+Drive+0.21mm.obj` (`wave2/metro-fan-20260929`,
  `twins/m64-engine-system/metrology/fan-drive/metrology-report.json`,
  verdicts blade_count **UNKNOWN**, gear_tooth_count **UNKNOWN**, scale
  **UNRESOLVED — consistent but not anchored**) reproduced the wave-1
  inconclusive result and re-scoped ACQ-0005 to a rescan with a calibrated
  scale reference and full 360° coverage. No web source supplied the counts.

## Fiche register added by this pass

**None.** This pass added no `catalog/sources/` fiche and promoted no record.
Fiches cited in the statuses above (`SRC-TURBOMASTER-993-K16-6736-LEFT-UNIT`,
`SRC-INVASIONAUTOPRODUCTS-993-K16-INTERNAL-DATA`,
`SRC-PATRICKMOTORSPORTS-993-TURBO-OIL-RETURN-PIPES`) predate this branch.

## Net result

0 of 6 targets closed by this pass. Contracts M64-ACQ-0002, -0003, -0004,
-0005 and the oil-system / conflict acquisitions remain open; the next
cheapest wins are unchanged: physical metrology for ACQ-0001/-0004, the
re-scoped fan-drive rescan, and a BorgWarner/KKK archive request for the
K16 map.
