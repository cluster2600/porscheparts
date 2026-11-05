# 0016 — Organic pilot replacement and a fit kit that brackets both openings

Date: 2026-11-05

Status: proposed for issues #3 and #4. It amends
[decision 0013](0013-pilots-advance-on-documentary-evidence.md), sections 3
and 7. The owner's constraint stands: no part is bought and nothing is
measured ([PROJECT_CHARTER.md](../PROJECT_CHARTER.md)).

## Context

The owner declined to close #3 and #4 and asked for a way to make them work.
Two points were open:

1. Pilot 2, the organic-shape pilot, is the door pull, classed `functional`.
   Decision 0013 found no `non_critical` organic part to swap in, because none
   was sourced.
2. The switch-blank fit kit bracketed 19 × 31 mm, while two sources give about
   17 × 28 mm for the opening, so no insert would enter it.

## Decision

### 1. Where the search looked

Every route stayed inside the owner's constraint: free downloads, licences read
on the original platform, nothing bought, nothing measured.

| Route | Result |
|---|---|
| The repository's 618 source records | no `non_critical` organic part with a scan or a recorded shape licence; the only licence-verified 993 scans are whole-car |
| Sketchfab public API, 2026-11-05 | `SRC-SKETCHFAB-993-GT2-RAW-SCAN` confirmed CC BY 4.0 and downloadable, but only with an account (HTTP 401 without one), unscaled, whole car; no 993 trim, knob or cover scan with a licence |
| Printables public API, 2026-11-05 (the platform's own licence field, which the 2026-10-15 audit could not read through the web page) | about 30 993, 964 and 944 part models, each with a licence; four retained below |

The four retained Printables models were downloaded through the platform's own
download link, hashed and inspected outside the repository. Nothing was
committed but their source records.

| Source | Part | Licence | Shape | Organic? |
|---|---|---|---|---|
| [`SRC-PRINTABLES-944-CLIMATE-KNOB-CC0`](../../catalog/sources/src-printables-944-climate-knob-cc0.json) | climate-control knob, reproduced by its author from his remaining original | CC0 | 19.97 × 10.00 × 12.50, stadium plan, filleted crown, pointer | partly: blends and crown, no grip surface |
| [`SRC-PRINTABLES-944-HVAC-KNOB-CC-BY-SA`](../../catalog/sources/src-printables-944-hvac-knob-cc-by-sa.json) | same knob, six months later | CC BY-SA | same envelope to 0.01, volume within 0.7 % | probably not independent of the CC0 model |
| [`SRC-PRINTABLES-993-OUTER-DOOR-LOCK-CAP`](../../catalog/sources/src-printables-993-outer-door-lock-cap.json) | outer door lock cap, SKU 993 537 613 00 (candidate) | CC BY-NC-SA | Ø 16 mm flat disc with a rounded edge, on a tongue | no |
| [`SRC-PRINTABLES-993-DOOR-PANEL-LINING-TRIM`](../../catalog/sources/src-printables-993-door-panel-lining-trim.json) | door panel lining trim, 993 555 697 00 (author's reference) | CC BY | 59.2 × 29.5 × 11.3, flat plate with holes | no |

### 2. Proposed replacement: the heater-control knob

**Proposal**, for the owner to accept or reject: replace the door pull as
pilot 2 by the heater-control knob, reference 944 653 205 00, listed by
`SRC-LT3D-993-HEATER-KNOB` (retailer, level B) for 944, 964, 968 and 993.

| Criterion | Heater-control knob |
|---|---|
| Non-critical | yes, by failure mode ([SAFETY.md](../SAFETY.md)): a knob pulled off its stub leaves the heater setting where it was; no load path, no presumed-critical domain. The control it turns sets cabin heat, not demisting by itself; that reading is the repository's and goes into the record |
| Shape data | two community models with licences read on the original platform: CC0 (reproduced from an original) and CC BY-SA; they are counted as **one** shape source (protocol section 8, rule 6) |
| Organic | **only in part.** Its crown, blends and pointer are surfaces a caliper does not define; it has no freeform grip. It exercises the organic pilot's method (register a shape on interface dimensions, check held-out ones) but it is not as organic as the door pull |
| 993 applicability | one level-B retailer listing. No PET plate and position: the number stays a candidate |
| Evidence level | D for the shape, B for the cross-reference |

Why it rather than the alternatives: the lock cap and the door trim are
prismatic, and the GT2 scan is unscaled, whole-car and behind an account. The
knob is the only `non_critical` candidate whose shape is published under a
verified open licence by someone who copied an original part.

What this does **not** do: it creates no catalogue record and no geometry. A
record needs the owner's choice first; once accepted, it is created with its
status card, preview and the two sources above, at `concept`. The door pull
keeps its record, its `functional` class and its role as method development,
as decision 0013 proposed.

**The owner chooses one of:** (a) swap the door pull for the knob; (b) keep
the door pull and add the knob as a fourth, non-critical pilot; (c) keep the
door pull alone and drop the literal "three non-critical" wording from issue
#3.

### 3. The switch-blank kit now brackets both sourced openings

Decision 0013, section 7, showed that the kit's three inserts (18.6 × 30.6 to
19.4 × 31.4 mm) were all larger than the 17.0 × 27.9 mm opening given by two
level-C sources. The kit now has two sets of three, generated by
`parts/993-int-switch-blank-0001/source/fit_test_kit.py`:

| Set | Declared opening | Inserts | Mark |
|---|---|---|---|
| A | 17.0 × 27.9 mm (threads 750484 and 1202129) | 16.6 × 27.5, 17.0 × 27.9, 17.4 × 28.3 mm | 1, 2, 3 dimples |
| B | 19.0 × 31.0 mm (thread 1202129) | 18.6 × 30.6, 19.0 × 31.0, 19.4 × 31.4 mm | dimples and a groove |

Together they cover the whole declared range, 17.0–19.0 mm wide and
27.9–31.0 mm high, each hypothesis at ±0.4 mm. The kit still measures nothing
by itself; a contributor's fit result would. The concept F0 and the PicoGK
model still use 19 × 31 mm: changing them waits for that result. The plate's
STEP is split into one file per set to stay under the 1 MiB file gate.

### 4. Scan against reference, run end to end (issue #4)

The scan acceptance section of [CAPTURE_PROTOCOL.md](../CAPTURE_PROTOCOL.md)
was run on `SCAN-935-XTREME-CYLINDER-HEAD`, an admitted, licence-recorded scan,
against the Xtreme catalogue ranges, with thresholds committed before the run
([trial](../research/capture-protocol-scan-trial-20261105/README.md)). One
check passed, two were not observable, and the port checks depend on which
face is the intake, which the scan does not settle. The protocol's proposals
now each state whether they were exercised; P5 gained three rule changes from
the run.

## Consequences

- Issue #3: a sourced `non_critical` candidate exists for the organic pilot,
  with its limits stated; the choice is the owner's. The switch-blank kit
  finding is fixed.
- Issue #4: the scan-vs-reference part of the protocol has been executed, with
  recorded pass, fail and not-observable outcomes. The physical capture
  sections (2 to 6) remain unexercised under the owner's constraint.
- Unchanged: every status (`concept`), the pinned measurement plans, the door
  pull record, and the measured-input gate of `switch_blank.py`.
