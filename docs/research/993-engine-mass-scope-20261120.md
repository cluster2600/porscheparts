# 993 engine-mass scope: the sheet heading, and what it leaves open

Issue #434. Follows the [2026-11-07 addendum](993-engine-mass-scope-20261107.md).
Nothing here changes a counted mass: `make twin` still reads 32.5 % for the
manual-transmission Carrera.

## The p. 15 sheet says "dry, ready for fitting"

The workshop manual's technical-data sheet (group 0, "Overall Vehicle -
General", 911 Carrera (993), PDF p. 15) prints the two engine weights under the
heading **"Engine weight (dry, ready for fitting)"**: 232 (511) kg (lbs) for the
manual transmission and 224 (494) for the Tiptronic. The structured
transcription in `MEAS-MANUAL-993-ALL` keeps the values and row labels but not
the heading, which is why earlier notes read the scope as unstated.
`docs/993/993_MANUAL_DATA_MAP.md` had recorded the heading.

The sheet was read on the rendered page image in two copies:

| Copy | Identity | Page |
|---|---|---|
| Local scan behind the register, provenance undocumented | 1,481 pages, SHA-256 `dd3f55c5…1ad92` | PDF p. 15 |
| Volume I (General, Engine) in the public community archive that also holds the spec booklet | 351 pages, image-only, SHA-256 `3f691ded…37f4ca` | PDF p. 15 |

Both give the same heading and values. Full hashes and the URL are in the
[page-checked record](../../catalog/manual/page-checked/993-workshop-manual-group0-engine-weight.json),
which `scripts/twin_coverage.py` now reads to state the scope. Neither copy is a
purchased or licensed one, so this does not settle the issue's "authorised copy"
condition: that is the owner's call.

Settled scope: **dry, ready for fitting, without gearbox** (the gearbox
exclusion comes from the spec booklet, printed pp. 18 and 22-23). Open: what
"ready for fitting" includes. The sheet lists no parts. The Tiptronic figure
being 8 kg lower fits a figure that includes the manual gearbox's flywheel and
clutch, but that is an inference.

A second Porsche document uses the same convention for the previous engine. The
after-sales training "Air Cooled Engine Repair"
(`SRC-PORSCHE-AIR-COOLED-ENGINE-REPAIR-TRAINING-PUBSTACK`, printed p. 27) gives
"Engine weight (dry)" 238 kg for the 964 Carrera 2 RoW and 230 kg for the USA
(M64.01/02). Its 993 chapter gives no engine weight. It is cited only as an
example of Porsche labelling these weights dry.

## What this does to the 45.1 kg gap

The weighing (`SRC-PELICAN-TIMMINS-993-ENGINE-WEIGHTS`, 186.9 kg) is a 1995
Carrera engine with a light flywheel, headers and mufflers, no air
conditioning, and an unknown fluid state. Against a dry figure, fluids cannot
account for the gap: if the weighed engine held oil, the like-for-like gap is
larger than 45.1 kg, not smaller. The remaining candidates are configuration
differences (flywheel and clutch, exhaust and catalytic converters, air
conditioning, other ancillaries). No registered source gives their masses or
says which of them "ready for fitting" includes, so none is allocated. Closing
the gap needs either a Porsche list of what "ready for fitting" contains or an
itemised weighing contributed under ADR 0019.

## The Turbo, and the engine carrier

The engine carrier is the Turbo part, 993 115 021 53 (ADR 0021), so the Carrera
figure does not give its load. The Porsche UK brochure "the 911 Turbo", dated
2/95, WVK 142 020 (`SRC-PORSCHE-993-TURBO-BROCHURE-UK-1995-PUBSTACK`, Technical
Specifications, PDF p. 22) gives:

| Quantity | Value |
|---|---:|
| Kerb weight | 1,500 kg |
| Maximum weight | 1,840 kg |
| Maximum front axle load | 760 kg |
| Maximum rear axle load | 1,150 kg |
| Clutch | 240 mm, double-mass flywheel |

It gives no engine weight, and does not state the weighing standard behind the
kerb weight. With the manual (no Turbo volume) and the training document (no
M64/60 table), no Porsche document reached so far gives the M64/60 engine mass.
The carrier's load basis is unchanged: it still lacks the Turbo engine mass,
the share of it the carrier carries rather than the gearbox mounts, and the
centre of gravity. The axle-load figures above are Porsche limits a future
load case can cite; they are not the carrier's load.

## Documents read and not used

In the Turbo brochure, whose text layer is unreadable, only the Technical
Specifications spread and the last four pages were read at full resolution; the
rest was seen as thumbnails (marketing pages and photographs), so an engine
weight in its running text is not excluded. The training document was searched
through its text layer: "weight" occurs only in the 964 table above and in
component weights. The local 993 parts catalogue (PET) lists no engine weights.
No document was added to the repository; only facts, page references and hashes.
