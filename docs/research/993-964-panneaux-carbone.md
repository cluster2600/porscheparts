# Carbon body panels — 993 and 964 candidates

State: **documentary inventory**. No part is qualified, no geometry exists,
nothing is proposed for manufacturing.

## Why these parts, and not the body shell

`ROADMAP.md` places the composite monocoque out of scope and keeps body panels
as a legitimate objective. The line is not arbitrary: it runs between what
carries load and what clothes the car. `SRC-GUNTHER-WERKS-CARBON-993` draws it
word for word at the most advanced 993 restomod on the market — "beneath the
carbon fiber, only the structural components and door crash bars remain steel" —
for an announced saving of **91 kg** on the panels, with the steel body shell
kept, inspected and reinforced.

The candidates are therefore the **bolted-on** panels, those that come off
without touching the self-supporting structure. The factory catalogue names
them, and that is the first thing it serves to establish.

## What the factory catalogues give

| generation | catalogue | record |
|---|---|---|
| 993 | PET Kat 017, 674 pages, English | `SRC-PET-993-KAT17-PDF` |
| 964 | PET Kat 013, 794 pages, German | `SRC-PET-964-KAT013-PDF` |

Both are held locally by the project owner and their text is extractable: the
part numbers can be transcribed without OCR. This repository imports neither
illustrations nor excerpts from them; it keeps only the numbers, which are
identification facts.

**And what they do not give.** No dimension, no mass, no material, no
thickness. A parts catalogue establishes the identity of a part and its place in
an assembly. It is no basis for any design.

### Bolted-on panels — 993 (1994-1998)

| panel | number | variants transcribed |
|---|---|---|
| Left front fender | 993 503 031 00 | `02` Turbo, `04` Carrera RS |
| Right front fender | 993 503 032 00 | `06` from 96, `02`/`08` Turbo, `04` RS |
| Front lid | 993 511 010 01 | `31` Carrera RS |
| Engine lid | 993 512 010 00 | — |
| Rear spoiler | 993 512 317 00 | 993 512 511 00 Turbo; 993 512 119 00/01/02 RS M470/M471 |
| Left bare door | 993 531 005 00 | `01`/`02`/`03` depending on drive side and model year |
| Right bare door | 993 531 006 00 | same |
| Front bumper cover | 993 505 311 00 | `01` USA version |
| Rear bumper cover | 993 505 411 00 | `01` USA, `02`/`03` Turbo |

### Bolted-on panels — 964 (1989-1994)

| panel | number | variants transcribed |
|---|---|---|
| Left / right front fender | 964 503 031 02 / 964 503 032 02 | `04` Carrera RS; 965 503 031/032 `02` and `04` Turbo |
| Front lid | 964 511 010 00 | Carrera 2/4 |
| Engine lid | 964 512 010 01 | `02` Carrera RS; 965 512 010 01 Turbo |
| Rear spoiler | 964 512 017 00 | — |
| Left / right bare door | 964 531 005 00 / 964 531 006 00 | `03` right-hand drive, `10`/`11` Speedster |
| Front bumper cover | 964 505 113 00 | `01` Carrera 2/4, 965 505 113 01 Turbo |

**The roof is not listed, and that is deliberate.** `993 503 087 00`, *outer
roof panel*, is a **welded** panel. Replacing it is not a part swap, it is an
intervention on the structure — the one `ROADMAP.md` excludes, and which the 964
FEA study shows precisely changes the load-carrying mechanism as soon as a
closed ring is touched.

## What these panels weigh

Only one source in the repository publishes per-panel masses:
`SRC-FEDERLEICHTE-ELFER-993-WEIGHTS`, a tuner's comparison table, original mass
against mass lightened by material.

| panel | original | carbon | saving | saving per vehicle |
|---|---|---|---|---|
| Front fender | 7.2 kg | 2.2 kg | -5.0 kg | **-10.0 kg** (x2) |
| Front lid | 14.0 kg | 4.1 kg | **-9.9 kg** | -9.9 kg |
| Rear spoiler | 12.5 kg | 4.8 kg | -7.7 kg | -7.7 kg |
| Rear bumper | 5.05 kg | 3.1 kg | -1.95 kg | -1.95 kg |
| Light strip | 1.26 kg | 0.26 kg | -1.0 kg | -1.0 kg |
| Mirrors (pair) | 1.8 kg | 0.25 kg | -1.55 kg | -1.55 kg |

Sum of the rows above: **about 32 kg**. Gunther Werks announces 91 kg by also
replacing the doors, the roof and the rear fenders, which this table does not
cover: the two figures are consistent with each other.

**Status of these masses.** These are values **declared by a seller**, neither
measured by this repository, nor traced to a scale, nor given with a tolerance.
They serve to rank candidates, not to compute a saving. The 14.0 kg of the front
lid in particular deserve to be reweighed: it is the highest value in the table
and the one that drives the ranking.

The only commercial catalogue that publishes a mass on every product page,
`SRC-ROSEPASSION-993-PARTS`, is **closed to automated agents** by its
robots.txt. It will not be queried by any tool in this repository; see
`docs/decisions/0003-no-vendor-harvesting.md`.

## What is missing, and it is the same for all of them

None of these panels has, in this repository:

- any **geometry**. No CAD, no scan. `SRC-SCHONER-993-GT2-LIDAR` claims a LiDAR
  scan of a 993 but publishes no file, no scale and no license: it is a project
  claim, not data;
- any **measured mass**, nor sourced original material and thickness;
- any **interface**: fastening points, styling gaps, fitting tolerances.

A body panel is judged first on its gaps, and a gap is measured. Nothing above
can therefore pass the gates of `docs/QUALITY_GATES.md` as it stands.

## The candidate to tackle first

**The front fender.** It is the best compromise across the three criteria:

- **bolted on**, removable without touching the structure, and with no restraint
  or crash-absorption function — unlike the bumper covers;
- **10 kg per vehicle**, the largest saving in the table, tied with the front
  lid but spread over two smaller parts, therefore easier to measure and to
  mold;
- **symmetric**: the left validates the right, which halves the geometric
  qualification work.

The front lid comes next, with a caveat: its 14.0 kg must be confirmed before it
is made the lead argument.

## What this document does not authorize

It authorizes neither manufacturing, nor publication in the catalogue, nor any
announcement of a mass saving. It establishes a list of candidates identified by
their factory number and ranked by a declared order of magnitude. The next step
is not CAD: it is **a scale and a caliper on a real fender**, plus the original
material and thickness. Otherwise the announced saving remains a seller's.

## Objection, and it is fair: these panels already exist

Carbon lids, fenders, spoilers and bumpers are in the catalogues of several
tuners. Remaking what can be ordered teaches this repository nothing and gives
it no reason to exist. The useful question is therefore not "which part weighs
the most", but **which part nobody sells**.

### What nobody sells: the dashboard trim

Record: `catalog/parts/993-int-dashboard-trim-0001.json`.

Two things carry the same name in the factory catalogue, and confusing them
would take the project out of scope:

| what it is | number | nature |
|---|---|---|
| `Dashboard` | 993 502 027 02 /LL | **body-shell sheet metal**, body group |
| `Dashboard trim` | 993 552 055 00 /LL | add-on trim, on clip nuts |

Only the second is a candidate part. The first is structure.

**What the catalogue establishes, and what drives everything else.**
Illustration 809-00 is titled "Dashboard, **for cars with Airbag**, Passenger's
side". The Carrera RS one, by contrast, reads "Dashboard, Knee protection strip,
**for cars without Airbag**, Passenger's side", with its own variant
993 552 055 70 under M003. The option codes separate M561 driver airbag, M562
driver and passenger, **M564 without airbag**.

In other words: on an M562 car, the trim carries the **passenger airbag
deployment flap**, whose tear line is an occupant-restraint part — presumed
critical by `SAFETY.md`. On an M564 or an RS, this flap does not exist and the
part goes back to being trim.

The record is therefore opened as `prohibited_pending_engineering`, and the
first job is neither CAD nor a scan: **transcribe the option code of the donor
vehicle**. It is a label reading, and it decides whether the project exists.

**This is not a mass project.** The announced saving is 1.15 kg, against 9.9 kg
for a front lid. The reason to make this part is that it is not in any
catalogue, not that it saves weight.

**No geometry exists, and the repository has already checked.** The two leads
found in phase 1 are classified: `SRC-CGTRADER-993-DASHBOARD-SCALE-MODEL` is a
1/8 scale model, archived as a false positive; `SRC-FSH-993-DASHBOARD-TRIM-DIMENSIONS`
describes a Singer Style aftermarket trim, not the original part. A dashboard is
a freeform surface with multiple interfaces — vents, instrument hood, column,
glovebox, console junction, pillars, windshield base — that cannot be
transcribed with a caliper. Photogrammetry at the scale planned for
`993-INT-DOOR-PULL-0001` is the right method, on a part a hundred times larger.

Three difficulties are specific to it, and none concerns an exterior panel:

- the original is thirty years old, cracked and warped by heat; molding a
  deformed part gives a wrong part;
- it is the interior surface most exposed to the sun, so the resin ages there;
- lacquered carbon under a windshield **reflects light into the driver's field
  of view**, which grained leatherette does not. That is a requirement, not a
  finish.

### What becomes of the previous ranking

It remains true as a **mass** ranking, and it stops being a work order. The
front lid keeps its record, `993-BODY-FRONT-LID-0001`, opened as the first body
pilot and now tied to its factory reference 993 511 010 01. But between remaking
a lid that can be ordered and transcribing a dashboard that nobody offers, it is
the second that teaches something.
