# 0013 — The three phase 2 pilots advance on documentary evidence

Date: 2026-10-15

Status: proposed for issues #3 and #4. It records a selection made on
2026-08-28 and a constraint stated by the project owner on 2026-09-14. One
choice, pilot 2 below, is left open for the owner.

## Context

Issue #3 asks for three non-critical pilots: a simple measurable part, an
organic shape that needs a scan or photogrammetry, and a missing part rebuilt
from its surroundings or its symmetry. Braking, steering, suspension, restraint,
fuel and highly loaded engine parts are excluded. The issue is done with three
concept records, their sources and a measurement owner.

The three pilots were chosen on 2026-08-28 (commit `774242da`, PR #8). They are
named in [ROADMAP.md](../../ROADMAP.md) ("Physical prototypes — suspended"), in
[MEASUREMENT_CAMPAIGN.md](../MEASUREMENT_CAMPAIGN.md) and in the records'
descriptions, but no decision recorded why they were chosen. Their measurement
plans, `parts/<id>/evidence/measurement-plan.md`, are frozen by the
`evidence/**` rule of [AGENTS.md](../../AGENTS.md) and name
"Responsable : contributeur", a role nobody holds.
[PROJECT_CHARTER.md](../PROJECT_CHARTER.md) already says the maintainer has no
part and no instrument.

On 2026-09-14 the project owner went further: no part will be bought and none
measured, by the owner either ("I won't buy 30,000 parts"). Everything starts
from existing scans, workshop manuals, the PET parts catalogue and published data
sheets. A dimension none of them gives is recorded as unsourced or candidate; it
is not estimated, and nobody is sent to measure it.

## Decision

### 1. The pilots

| Category | Record | Safety class | Why this part |
|---|---|---|---|
| Simple, measurable | `993-INT-SWITCH-BLANK-0001` | `non_critical` | a flat face and clips, seven dimensions D01–D07; its master `source/switch_blank.py` already builds only from a measurement record; the only pilot with published figures, two level-C forum posts; a fit-test kit exists ([decision 0009](0009-first-fit-test-print-switch-blank.md)) |
| Organic, scan | `993-INT-DOOR-PULL-0001` | `functional` | an ergonomic grip that a caliper cannot describe; the plan scales and registers a photoset on two caliper interface dimensions, then checks three more |
| Missing or symmetric | `993-INT-SEAT-RAIL-COVER-0001` | `non_critical` | left and right versions exist (9xxteile shows distinct numbers); a missing side is rebuilt by mirroring about the vehicle's longitudinal plane, once the symmetry is measured |

### 2. The exclusion rule

The rule is [SAFETY.md](../../SAFETY.md): its presumed-critical domains, and the
failure mode overriding the domain. None of the three pilots belongs to a
presumed-critical domain.

`scripts/select_candidates.py` applies the presumed-critical list automatically,
but to a factory listing, not to the catalogue records. The pilots were chosen
by hand, about half an hour before that tool was committed (`834b1c5f`). Run on
the record names today, its `classify()` returns `unclassified` for the switch
blank and `candidate` for the other two: none is excluded.

The run also shows a defect. The tool matches plain substrings, so any text that
contains "trim" is excluded as a wheel "rim": `classify("Trim strip")` returns
`excluded`. The error is on the safe side, but it hides trim candidates. It is
not changed here: SAFETY.md requires the list to stay identical to the titanium
screenings, so a fix is a separate change.

The seat rail cover sits on the seat rail, which belongs to seat retention. A
design that uses a seat mounting fastener, or alters the rail or the adjuster
travel, leaves the record's `non_critical` class.

### 3. Pilot 2 is `functional`: the choice is open

The door pull takes a repeated hand load and the record classes it `functional`:
its failure in the hand can injure. Issue #3 asks for non-critical pilots, and
ROADMAP.md says "three non-critical parts". For pilot 2 that is not accurate.

| | Keep the door pull | Swap it for a `non_critical` organic part |
|---|---|---|
| For | the organic category needs an organic part, and the catalogue has no `non_critical` organic record today (the `non_critical` records are the switch blank, the seat rail cover, the F1 trim ring and two PET identity sets); no pilot can leave `concept` under the constraint above, and the class binds at publication, where it requires documented functional testing | meets issue #3 as written; no pilot whose eventual print could injure |
| Against | the pilot set is not "three non-critical parts" | needs a new record, chosen from the PET listing with `select_candidates.py` and sourced; no candidate is named here because none is sourced |

**Proposal**, for the owner to accept or reject: keep the door pull for method
development only. Publish no print file for it, of any kind, before the owner
decides. Swap it before any physical capture if the owner wants three literally
non-critical pilots. This decision does not make that choice.

### 4. Evidence owner

- **Documentary evidence**: the maintainer, by desk review of existing sources.
- **Physical capture**: unassigned. It awaits an external contributor.

This is written into each pilot's `validation.known_limits`, since the pinned
plans cannot be edited and the part schema has no owner field.

### 5. Consequence of the owner's constraint

The pilots advance on documentary evidence only: sources registered, declared
values transcribed as documented specifications, contradictions listed, a part
number entered only when a PET plate and position give it. The physical capture
in the plans (D01–D07 of the switch blank, the door pull photoset, the seat rail
symmetry check) stays backlog for an external contributor. Every pilot stays at
`concept`. [PROJECT_CHARTER.md](../PROJECT_CHARTER.md) records the constraint.

### 6. Porsche part numbers

No repository source gives a PET number with a plate and a position for any of
the three pilots, so `porsche_part_numbers` stays empty and each record says so.

- Switch blank: `993 613 523 00` is a candidate, from a retailer listing of an
  OEM Schalterblende (`SRC-PARTWORKS-993-SWITCH-BLANK-OEM`, level B) in a switch
  panel and center console context. It is not entered. The PicoGK batch
  variant `PGK993-10` (`parts/picogk-993-batch-01/params/pgk993-10-console-switch-blank.json`
  and that batch's README) already lists it without that qualifier; this
  decision does not confirm it.
- Door pull: `993 555 851 00` and `993 555 852 00`
  (`SRC-PORSCHEFANATICS-993-DOOR-OPENER-PET`, PET illustration 807-10,
  position 18) identify the interior door opener, a different part with its own
  record, `993-INT-DOOR-OPENER-LEVER-F0-0001`. They are not copied.
- Seat rail cover: 9xxteile shows distinct left and right numbers; no repository
  source transcribes them.

### 7. Desk test of the capture protocol on pilot 1 (issue #4)

[CAPTURE_PROTOCOL.md](../CAPTURE_PROTOCOL.md) was applied to the switch blank,
documentary intake only. The two Rennlist sources were added to the record and
transcribed as two documented specifications, one per source as the validator
requires:
[`MEAS-DECLARED-993-INT-SWITCH-BLANK-0001-RL-750484`](../../catalog/measurements/MEAS-DECLARED-993-INT-SWITCH-BLANK-0001-RL-750484.json)
and
[`MEAS-DECLARED-993-INT-SWITCH-BLANK-0001-RL-1202129`](../../catalog/measurements/MEAS-DECLARED-993-INT-SWITCH-BLANK-0001-RL-1202129.json).
All values are declared, level C, with no instrument, tolerance or repeat, and
both pages are blocked to automated re-reading.

| Quantity | Declared | Source | What the repository's geometry uses |
|---|---|---|---|
| Console switch opening | 17.0 × 27.9 mm (0.67 × 1.10 in) | `SRC-RENNLIST-993-CONSOLE-SWITCH-HOLE-DIMENSIONS` | not used by the record's own geometry |
| Switch blank | 16.2 × 27.4 mm (0.637 × 1.077 in) | same | body of the PicoGK batch variant `PGK993-10` ([params](../../parts/picogk-993-batch-01/params/pgk993-10-console-switch-blank.json)) |
| Faceplate opening of a switch housing | about 17 × 28 mm | `SRC-RENNLIST-993-DASHBOARD-LIGHTING-DIMENSIONS` | not used |
| Passage under the covering | about 19 × 31 mm | same | the "declared opening" of the concept F0 ([concept-f0.json](../../parts/993-int-switch-blank-0001/evidence/concept-f0.json)), of the record's PicoGK model and of the fit-test kit ([kit.json](../../parts/993-int-switch-blank-0001/print/kit.json)) |

What the comparison shows, by arithmetic on declared values only:

- **The kit brackets the wrong figure, if the faceplate is the opening.** The
  source of the 19 × 31 mm figure gives it for the passage under the covering;
  the faceplate opening of thread 1202129, about 17 × 28 mm, and the console
  switch opening of thread 750484, 17.0 × 27.9 mm, agree within rounding. The kit inserts, 18.6 × 30.6, 19.0 × 31.0 and
  19.4 × 31.4 mm, exceed a 17.0 × 27.9 mm opening by 1.6 to 2.4 mm in width and
  2.7 to 3.5 mm in height: none would enter it. The kit's ±0.4 mm bracket cannot
  separate two hypotheses 2 to 3 mm apart.
- **Two geometries of one record use different bases.** The record's F0, its
  PicoGK model and the kit use 19 × 31 mm; the batch variant `PGK993-10` uses
  16.2 × 27.4 and 17.0 × 27.9 mm.
- **The console figures are consistent with each other.** Read against the
  interface contract of `TWIN-993-CABIN-DASH-SWITCH-0001`, the opening maps to
  H01/H02 and the blank to D08/D09: nominal clearances of 0.8 and 0.5 mm. With
  no stated uncertainty there is no worst-case margin, so this is not a fit
  check, and the mapping is the repository's reading, not the source's.
- **The location is not established.** The record says dashboard; one source
  concerns the center console, the other a window switch measured to estimate a
  lamp opening above the ignition lock.

Geometry and print files are not changed. Decision 0009 already says that a kit
in which no size fits is a result worth recording; a kit that brackets both
figures would be a separate decision.

The measured-input gate stays closed. A documented specification has no
readings, so `switch_blank.py` and the twin's `check_fit.py`, which build only
from readings, refuse these records; `switch_blank.py` and `check_fit.py` now also
refuse any record whose `record_kind` is not `physical_measurement`.
`tests/test_switch_blank_measurement_gate.py` proves both, including on a
declared record with injected readings.

## Consequences

- Issue #3: three pilots, their reasons, sources and evidence owner are
  recorded; pilot 2's class is an open owner choice.
- Issue #4: one protocol, [CAPTURE_PROTOCOL.md](../CAPTURE_PROTOCOL.md), with
  per-method targets and thresholds proposed before any acquisition. Its
  documentary intake was desk-tested on pilot 1; its physical sections have never
  been exercised, and cannot be until a contributor comes forward.
- Unchanged: every status (`concept`), every geometry and print file, and the
  pinned plans.
