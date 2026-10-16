# 0014 — The exhaust tip stays the titanium candidate, behind a conditional go that is closed today

Date: 2026-10-15

## Status

**Proposed, not reviewed.** Drafted for issue #5. The go/no-go rule below is a
project decision rule pending professional review. Two points are owner
decisions and are not taken here: accepting a `functional` part as the first
titanium part, and how the deciding temperature will be sourced. Model output
grants no engineering approval.

## Context

Issue #5 asks for a first Ti-6Al-4V part that is non-critical, where titanium
brings a measurable benefit, with a mandatory comparison of LPBF, CNC, sheet
metal, casting and polymer or aluminium, a decision matrix, load and
environment requirements and a documented go/no-go.

[Decision 0007](0007-premier-titane-embout-echappement.md) retained the oval
exhaust tip `993-EXH-OVAL-TIP-TI-F1-0001` and left four gaps:

- its screen compares **parts**, not processes; the tip's own engineering
  screen lists two process comparisons as required and never made (fabricated
  stainless, LPBF IN625);
- its rule says Ti-6Al-4V at 350 °C or less, IN625 at a confirmed 427 °C, and
  nothing in between;
- its next step is an infrared measurement on a car, which the project owner
  does not take;
- it calls the failure "benign", while the record is `functional`.

[Decision 0008](0008-le-magnesium-moderne-bat-le-titane.md) adds the test any
titanium choice must pass: beat the **original material done properly**, not
a nobler material.

## Decision

1. **The tip remains the only titanium candidate.** The written grid leaves one
   eligible part out of 43
   ([screen](../../twins/993-exhaust-tip-ti-f0/evidence/selection/titanium-candidate-screen.json)).
   There is no non-critical alternative to switch to.
2. **The five-route matrix** below, machine-readable in
   [`exhaust-tip-route-matrix.json`](../../catalog/manufacturing/exhaust-tip-route-matrix.json)
   and checked by
   [`test_993_exhaust_tip_route_matrix.py`](../../tests/test_993_exhaust_tip_route_matrix.py),
   replaces the missing process comparison.
3. **Go/no-go is conditional, and today it is no-go.** The rule is in the
   section of that name. Its single input is blocked.
4. **The baseline is stainless, and it is also the fallback.** If titanium is
   ruled out, LPBF IN625 is not the automatic answer 0007 gave: on this
   geometry it is heavier than stainless.
5. **A manufacturing request is drafted, not sent:**
   [`993-exh-oval-tip-ti-f1-0001-manufacturing-request.md`](../993/993-exh-oval-tip-ti-f1-0001-manufacturing-request.md),
   with proposed acceptance criteria and an empty review table.

## The first titanium part is `functional`, not `non_critical`

The issue asks for a non-critical part. The tip is not one, and this decision
says so instead of relabelling it.

- The record's class is `functional`
  ([record](../../catalog/parts/993-exh-oval-tip-ti-f1-0001.json)):
  "loaded part whose failure can immobilize or damage the vehicle"
  ([SAFETY.md](../../SAFETY.md), section 1). 0007's "benign failure" is a
  judgement, not a class.
- Under SAFETY.md a `functional` part is published only after **documented
  functional testing**, on top of the eleven stages of the
  [AM pipeline](../AM_VALIDATION_PIPELINE.md) and the eight release conditions
  of [TITANIUM.md](../TITANIUM.md). A non-critical part would only need
  dimensional and fit validation.
- Failure mode decides the class, not the domain. A tip that cracks or comes
  off near the rear bumper cover carries 850 K gas (synthetic) next to it. The
  fire question is not assessed; if a reviewer judges it credible, the class
  rises to `safety_critical`. This is an open item.
- Accepting a `functional` part as the first titanium part is the explicit
  trade-off [decision 0005](0005-alsi10mg-nest-pas-un-choix.md) asked for. It
  is the owner's decision. "No titanium part for now" is an equally valid
  outcome of this issue.

## Route matrix

Masses are the CAD volume, 48,149.34 mm³, times a sourced density. The
stainless baseline assumes the **same** 0.8 mm double wall and ties, at
7.7 to 8.0 g/cm³ (ferritic to austenitic heat-resistant grades); a real
fabricated tip would differ. Temperature margins are the service ceiling minus
the two synthetic figures of the F0 screen: 427 °C on the outer surface, and
850 K (577 °C) for the gas that wets the inner duct.
Basis: **S** sourced, **E** repository evidence, **A** arithmetic, **As**
assumption, **J** judgement, **O** open. Every cell, with its source or file,
is in the JSON.

| route | mass (g) | vs stainless | margin at 427 °C / 577 °C | one body | 0.8 mm walls, 2.7 mm channel | supply | inspection | cost class |
|---|---:|---:|---|---|---|---|---|---|
| LPBF Ti-6Al-4V | 212.34 E | −42.7 to −44.9 % A/As | **−27 / −177** S | yes E | p01 0.600, min 0.460 mm vs 0.3–0.4 min; channel not proven E/O | commodity E | high J | high J |
| LPBF Ti-6242 | 218.60 A | −41.0 to −43.2 % A/As | +123 / −27 S | yes E | no published minimum O | none E | very high J | very high J |
| LPBF IN625 (F0) | 406.38 E | **+5.5 to +9.6 %** A/As | not quantified O/J | yes E | p01 0.636, min 0.245 mm; no published minimum E/O | published route E | high J | high J |
| CNC from billet, Ti or stainless | 213.30 Ti A/As | as the alloy | Ti: −27 / −177 S/As | no E/J | not producible J | commodity shops J | low J | high in Ti J |
| stainless sheet, formed or welded | 370.75–385.19 A/As | baseline | **+293 / +143** S/A/As | no J | feasible, simplified J | commodity S | low to medium J | low to medium J |
| Ti-6Al-4V investment casting | 213.30 A/As | −42.5 to −44.6 % A/As | −27 / −177 S/As | yes, with a core J | unsupported J/O | specialised foundry J | high J | very high J |
| aluminium (AlSi10Mg; Aheadd HT1 ceiling) | 128.56 A | — | −167 / −317 S | yes J | 0.4 mm published minimum E | commodity J | — | — |
| polymer (PEEK HP3) | 63.32 A | — | −247 / −397; melts at 372 °C S/J | yes J | — | specialised J | — | — |

**The ceilings are not of one kind**, so the margin column compares unlike
limits. The titanium rows use a creep-limited ceiling for prolonged service.
The stainless 720 °C comes from a guidance maximum service temperature in air,
an oxidation-environment value rather than a creep limit, and assumes grade
1.4301 or 1.4541. The Aheadd HT1 260 °C is a supplier stability statement, not
a service rating. The PEEK 180 °C is the UL 746B continuous-use rating for
mechanical duty with impact, chosen over the 240 °C without-impact and 260 °C
electrical ratings because the tip vibrates (judgement); the exclusion holds
on any of the three. Each temperature cell of the JSON carries its
`ceiling_type`. A margin ranks a route only within the meaning of its own
ceiling.

Sources of the limits:
[`SRC-TI64-CREEP-SERVICE-CEILING`](../../catalog/sources/src-ti64-creep-service-ceiling.json)
(Ti-6Al-4V 350–400 °C, Ti-6242 about 550 °C),
[`SRC-EURO-INOX-STAINLESS-HIGH-TEMPERATURES-2012`](../../catalog/sources/src-euro-inox-stainless-high-temperatures-2012.json)
(stainless 870 °C intermittent in air for 1.4301 and 1.4541, less up to
150 °C in water vapour, so 720 °C is used; densities 7.7 for the ferritic and
7.8 to 8.0 for the austenitic heat-resistant grades),
[`SRC-CONSTELLIUM-AHEADD-HT1-FACT-SHEET`](../../catalog/sources/src-constellium-aheadd-ht1-fact-sheet.json)
(stability to about 260 °C) and
[`SRC-EOS-PEEK-HP3-MATERIAL-DATA`](../../catalog/sources/src-eos-peek-hp3-material-data.json)
(UL 746B continuous use 180 °C mechanical with impact, 240 °C mechanical
without impact, 260 °C electrical; melting point 372 °C). Aluminium and
polymer are ruled out by temperature by a margin no measurement is likely to
close.

**The original material is not identified.** The repository's declared data
for the 993 tailpipe records the material as "to be determined"
([`993-declared-part-data.json`](../../catalog/reference/993-declared-part-data.json)).
The aftermarket oval tip is declared stainless (FVD, level C), Porsche
describes optional Turbo tips as chromed stainless steel with no alloy
([`SRC-PORSCHE-993-TURBO-DUAL-EXHAUST-1-98`](../../catalog/sources/src-porsche-993-turbo-dual-exhaust-1-98.json),
level B), and the PET judgement presumes stainless. The baseline is stainless
by presumption.

### What the matrix says

- **Titanium's measurable benefit is mass**, and only mass: 158 to 173 g
  per tip against equal-geometry stainless, 194 g against IN625.
- **Corrosion is not established as a benefit.** The screen inputs judge the
  incumbent's corrosion not problematic, and titanium adds a titanium/stainless
  couple at the mounting.
- **Consolidation and the unmachinable channel belong to LPBF, not to
  titanium.** IN625 has them too.
- **The inner duct matters more than the surface.** Against the gas
  temperature, Ti-6Al-4V is 177 °C short and even Ti-6242 is 27 °C short.
- **0007's fallback is the wrong way round.** IN625 is heavier than an
  equal-geometry stainless tip. Without titanium, the original material done
  properly is lighter and commodity; IN625 only buys the one-piece double
  wall.

## Load and environment requirements

What the repository knows comes from one F0 screen
([`engineering-screen-ti64.json`](../../parts/993-exh-oval-tip-ti-f1-0001/evidence/engineering-screen-ti64.json)).
None of it is measured.

| quantity | value | status |
|---|---|---|
| engine case | 3.8 L, 6,500 rpm, volumetric efficiency 0.95, two outlets | synthetic regression input |
| exhaust gas temperature | 850 K (577 °C) | synthetic |
| tip surface temperature | 700 K (427 °C) | synthetic, uniform, never measured |
| gauge pressure | 30 kPa | synthetic |
| thin-wall hoop stress | 1.24 MPa | estimate from the synthetic pressure |
| axial pressure force | 77.6 N | estimate |
| free thermal expansion | 0.42 mm | estimate |
| fully constrained thermal stress | 385 MPa | warning that demands a sliding interface, not a predicted stress |
| first mode | 44.8 Hz | equivalent-strip estimate, not a correlated shell mode |
| inlet velocity, pressure loss | 107 m/s, 845 Pa | steady ideal-gas screen |
| clamp torque at the tailpipe ball clamp | 25 Nm, 30 Nm maximum | OCR transcription, unverified; applicability to this variant not established ([torques](../../catalog/specifications/porschefanatics-993-torques.json)) |

Open, each one blocking a functional claim:

| requirement | status |
|---|---|
| vibration spectrum at the mounting (engine, road, exhaust pulses) | **open** — none recorded |
| thermal cycling: number of cycles, ramp, cold start to hot running | **open** |
| inner-duct metal temperature | **open** — the screen assumes one uniform temperature |
| oxidation of Ti-6Al-4V in the delivered condition | **open** — listed as missing by the process card |
| condensate at cold start | **open** — no source in the repository |
| road salt and moisture, and the titanium/stainless couple | **open** — the record says "to be addressed" |
| fatigue | **open** — no load case, cycle count or S-N data; see `titanium.fatigue_assumptions` in the record |
| inlet interface, insertion depth, clamp, clearance to the bumper cover | **open** — F0 assumptions |
| temperature of the adjacent bumper cover | **open** — listed as a release blocker |

## Go/no-go rule

Input: **T_max**, the highest metal temperature anywhere on the part in
service, inner duct included, taken from a published source or third-party data
with recorded provenance. A synthetic or screening value is not an input. If
only an outer-surface value is sourced, the inner duct is taken at the gas
temperature unless an inner-wall value is sourced too.

| T_max | decision for Ti-6Al-4V | consequence |
|---|---|---|
| not sourced, or synthetic | **no-go** | current state; the request stays a draft |
| ≤ 350 °C | **conditional go** | a reviewed supplier feasibility request may proceed if every condition below holds; not a manufacturing authorization |
| 350 to 400 °C | **no-go** | inside the source's own 350–400 °C uncertainty band; reopened only with creep and oxidation data for the delivered condition of the actual route, and professional review |
| 400 to 550 °C | **no-go** | above the Ti-6Al-4V ceiling; Ti-6242 fits but has no supply route; fall back to stainless, or IN625 if the one-piece double wall is kept |
| > 550 °C | **no-go** | no titanium route |

The 350 °C threshold is the lower end of the source's band, not the 400 °C
0007 used to compute its −27 °C margin. Choosing the lower end is the
conservative reading of a published guidance value that is not a guarantee.
This closes 0007's undefined 350–427 °C band in the no-go direction.

**For the professional reviewer: the whole threshold rests on one supplier
page.** [`SRC-TI64-CREEP-SERVICE-CEILING`](../../catalog/sources/src-ti64-creep-service-ceiling.json)
is a grade-selection guide published on the blog of an alloy supplier, Huaxiao
Alloy, recorded at evidence level B. Its record lists one cross-check under
`verified_against`, the article
[doi:10.1002/adem.202301122](https://advanced.onlinelibrary.wiley.com/doi/10.1002/adem.202301122),
without saying which statement that article confirms. The 350–400 °C band and
the 550 °C Ti-6242 figure are to be checked against that article or a primary
creep source before the rule is relied on.

Other conditions for a conditional go: the owner's written acceptance of the
`functional` class; the manufacturing request and its acceptance criteria
reviewed by a named human; a galvanic isolation scheme; an inlet interface and
clamp defined from sourced data; a drawing with tolerances, without which the
request's dimensional acceptance criteria cannot be quoted.

**The input is blocked.** The owner does not measure parts, so 0007's infrared
measurement is not a next step this project takes. The only path is a sourced
value: a published measurement of a 993 tip or outlet temperature, or
third-party data with provenance, recorded as a source before it is used.
Until then the decision is no-go.

## Consequences

- Issue #5 has its matrix, its requirements and its rule. The rule is
  conditional and closed today; nothing is ordered.
- The tip record gains a `titanium.fatigue_assumptions` field that says what is
  assumed and what is unknown; the part schema accepts it as optional.
- ASTM F2924, F3001, F3302 and F3049 get source records, cited by designation
  only.
- 0007 gets a "See also" line. Its text and its evidence are not changed.

## Accepted limitations

- The stainless baseline mass rests on an equal-geometry assumption; no
  sourced mass of the oval original exists.
- The IN625 temperature margin is not quantified.
- The temperature margins compare ceilings of different kinds (creep,
  oxidation guidance, stability statement, continuous-use rating); see the
  note under the route matrix.
- The go/no-go threshold rests on a supplier-published source; see the note
  for the professional reviewer in the go/no-go rule.
- `titanium.fatigue_assumptions` is optional in the schema and the validator
  for now, because six other titanium records do not carry it yet
  (`993-ENG-CHAIN-CASE-LID-TI-F0-0001`, `993-ENG-CONNECTING-ROD-TI64-F0-0001`,
  `993-ENG-EXHAUST-VALVE-F1-0001`, `993-ENG-INTAKE-VALVE-F1-0001`,
  `993-ENG-INTAKE-VALVE-TI64-HOLLOW-F0-0001`,
  `993-ENG-INTERCOOLER-BRACKET-TI-F0-0001`). AGENTS.md asks for fatigue
  assumptions on every titanium part; the field should become required once
  those six records are filled.
- The thin-wall feasibility of fabrication, casting and machining is judgement,
  not a supplier statement.
- The generated quote requests in `twins/993-exhaust-tip-ti-f0/evidence/` keep
  boilerplate from the trim ring; they are frozen and are superseded by the
  drafted request once it is reviewed.
