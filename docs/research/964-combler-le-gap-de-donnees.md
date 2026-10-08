# Closing the 964 twin's data gap: state of the leads as of 2026-09-04

Two blockers hold up the dossier. This document says what has been tried, what
is closed and what remains to be done — distinguishing what depends on us from
what depends on a third party.

## Blocker A: longitudinal registration of the datum network

### The diagnosis has changed

The search for point 17 on the scan failed, and the twin's README concludes
from it that "a published datum point must be located". That is true, but the
wording hides the real problem: **what is needed is not a hole, it is a
dimension**.

The best-located features of the scan are not the drilled holes — the scan does
not resolve them, a firmly established negative result — they are the **wheel
centers**, reproducible to +/- 7 mm and robust to the tire radius. What is
missing is therefore not a feature, it is **a single published longitudinal
dimension between a datum point and an axle line**. Volume IV was reread line
by line on 2026-09-04: it does not give one. It gives ride heights, not
stations.

### A dormant lead, already in the repository

`SRC-RENNLIST-993-BODY-DIMENSIONS-PDF` reports three attachments not obtained,
including a "Porsche 993 body measurement PDF" announced as a **table of points
in millimeters**. That is exactly the missing object, and it concerns the 993.

A cross-check made on 2026-09-04 makes this lead much better than it looked.
`SRC-RENNLIST-993-JACKING-POINT-DISCREPANCY` reports, for a 993, a front-to-rear
distance between jacking points of **1245 mm**. That is, to the millimeter,
**dimension R of the 964 manual**, published at 1245 +/- 2 mm between P17 and
P18. An independent, non-Porsche source therefore reproduces the transcription
from volume V, and above all **964 and 993 share the longitudinal spacing of
the jacking points**. A 993 point table would therefore be at least partly
transferable — and the repository is already 993-oriented.

It is the cheapest lead in the dossier and it has never been pushed.

### Frame bench data publishers

| publisher | status | remark |
|---|---|---|
| Celette | closed | 964-specific set 564.320, 42 points, documentation behind authentication |
| Car-O-Data | identified | never approached |
| **Autorobot** | **new, 2026-09-04** | see `SRC-AUTOROBOT-MEASURING-DATA-SERVICE` |
| Spanesi, Josam, Globaljig, Blackhawk, Chief | not tried | |

Autorobot is the best of the three known for a specific reason: its data
sheets contain **photographs of the measuring points**. The registration failed
because a published datum point could not be associated with a physical
feature of the scan; a photograph removes exactly that ambiguity. Autorobot
also describes its method — measured on undamaged vehicles clamped on a bench —
and distributes single sheets as PDF and in ADF format, so **a sheet is an
object that can be requested**. Access by subscription, no public database,
coverage of model years 1989-1994 not announced. Factory contact published.

**The realistic route, for all three publishers, is the same: a subscribing
shop, or a request for a single sheet on behalf of a documentation project. Not
a subscription.**

### FIA homologation

A new, free lead: the 964 Cup and the Carrera RS were homologated, the RS
N/GT as of March 2, 1992. The `historicdb.fia.com` database has a
`porsche-carrera-rs` entry. **It returns 403 to any automated read**: it must
be opened in a browser. A caveat to state up front: a homologation form gives
overall dimensions, a wheelbase, track widths and sometimes a dimensioned
drawing, but **rarely coordinates of body shell points**. Zero-cost lead,
uncertain yield.

### What was verified and acquired on 2026-09-04

- **Third, independent scale check.** Overall length of the scan in the
  vehicle frame: **4282.4 mm** against **4275 mm** in the 964 catalog, i.e.
  **+7.4 mm or +0.17%**. Same sign and same order as the +0.27% wheelbase
  discrepancy. It registers nothing in X — the extremities are bumper skins and
  not reference planes — but it confirms that the frame is sound.
- **A reference-frame bug fixed.** `wheel_fits.npy` was in scan coordinates and
  could not be combined with `verts_vehicle.npy`. See
  `source/wheels_vehicle.py`.
- **Correction of 2026-09-25: the visible relief does not describe the hidden
  tunnel.** `source/tunnel_probe.py` measures surface bands seen from below; it
  can conclude neither that there is no tunnel, nor that there is no
  longitudinal shaft, nor that a passage is free. See the twin README and
  `SRC-PORSCHE-964-993-ALL-WHEEL-DRIVE-HISTORY` for the C4 driveline.

### Still to do, not done here

- **A second scan, of a production body.** The current scan is a probably
  modified wide body, which hides the original rocker panels. Depends on a
  contributor.
- **The frame bench survey.** Depends on a third party. It is the most decisive
  item.

## Blocker B: torsional stiffness of a complete 964 body shell

### This blocker was bypassed, not opened

The good news is that it **no longer has to be opened for the essentials**. The
claim to test — "the leverage of a monocoque is architectural" — is relative,
so it can be measured without any external denominator. That is done: see
`docs/research/964-chassis-carbone-kevlar.md`. A German-language thread
consulted the same day also points out that the manufacturers themselves
publish only relative figures, for lack of a standardized protocol.

### What the 2026-09-04 search produced

Targeted German-language search on `Verwindungssteifigkeit` and
`Torsionssteifigkeit`, not covered by the 2026-09-03 campaign: **no factory
value**. The PFF thread "Karosseriesteifigkeit" gives none and explains why.

Only one figure emerged, and it is bad: **964 Carrera coupe about 11,563
N.m/deg**, 993 about 13,876. See `SRC-RENNLIST-911-TORSIONAL-RIGIDITY-LIST`.
The author himself presents them as values "that circulate online", with no
primary source, no protocol, and without saying whether they are body-in-white
or complete vehicle figures. **Not to be used as a reference.** Recorded only
so that the search is not repeated.

### Still to do, not done here

- Porsche 1988 press kit and SAE body-shell benchmarking literature.
- Restomod builders: search done on Tuthill, no published figure found.
- ~~**Extend the shell model** to the roof, the B-pillars, the wheel arches and
  the windshield frame.~~ **Done.** See `twins/964-chassis/fea/README.md`,
  sections "From the floor pan to the closed cell" and "What this ranking says,
  and what it does not say". From the bare
  floor pan to the closed cell, K x 3.7 for mass x 2.3. The useful result is
  not that factor but the ranking: the windshield frame, 1.1 kg, returns two
  orders of magnitude more per kilogram than the roof, 10.5 kg, because it
  closes the upper ring. Verified at three mesh densities. The extension also
  revealed, through a connectivity check, that a cross member of the model had
  been floating from the start: 5.7% dead mass, zero stiffness, and every
  published specific stiffness understated accordingly.

## Priorities

1. **The Rennlist 993 point table.** Free, already identified in the
   repository, and the 1245 mm cross-check makes it transferable to the 964.
2. **A request for a single sheet from Autorobot**, citing the photographs of
   measuring points. Free to ask.
3. **The FIA database**, to be opened in a browser.
4. ~~**Extend the shell model.**~~ Done, see above. What remains of comparable
   weight — bonded glazing, panel openings, doors — would refine the model
   without changing the ranking it produces, and therefore weighs less than the
   following items.
5. The frame bench survey and the production scan, which depend on third
   parties and remain the two decisive items.

There is therefore no longer, in this dossier, any lead that is both decisive
and entirely under our control. The first three priorities are requests to
make or a page to open in a browser; they need no computation.
