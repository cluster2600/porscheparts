# Turbo oil circuit, plate 202-16 — examined, and ruled out

The titanium triage of the factory catalogue brought up `oil pipe`, 21
references, as a serious additive candidate. This document examines it. The
conclusion is **no** — twice, for two independent reasons, and it is the second
one that is instructive.

## What the plate establishes

Plate `202-16 Turbocharger` of the 993 Turbo identifies the oil circuit of the
two K16s. Eleven fluid or retention parts, not counting the fasteners, gaskets
and o-rings on the same plate:

| position | references | designation |
|---|---|---|
| 18 | `993 107 125 53`, `993 107 126 53` | `oil pipe`, left/right pair |
| 20 | `993 107 339 53` | `oil pipe` |
| 21 | `993 107 338 53` | `oil pipe` |
| 19 | `993 107 311 53`, `993 107 312 52`, `993 107 312 54` | `vent line` |
| 9 | `993 107 127 51`, `993 107 128 51` | `oil collection container` |
| 22 | `993 107 005 52`, `993 107 005 53` | `bracket` |

The catalogue **identifies, it does not dimension**: no dimension, no material,
no interface. And it does not establish **which pair is the feed and which pair
is the return**. This point corrects, in passing, a claim in the repository: the
record `993-ENG-TURBO-OIL-RETURN-LINE-IN625-F0-0001` announces itself as a
"return" without anything establishing it. The limit is now written into the
record.

## Why it is a very good additive candidate

Eleven parts doing a single job: bring oil to two bearings, bring it back, vent,
and hold the whole thing. That is the very definition of consolidation, the
third family in `TITANIUM.md`. Add internal passages, a constrained routing
around scorching parts, and a series that will never justify tooling. On paper,
it is better than the tip.

## First reason for refusal: the failure mode is fire

`SAFETY.md` defines `safety_critical` as a failure that "could cause loss of
control, **fire** or injury".

A turbo oil line that lets go sprays or drips oil onto a turbine housing. Engine
oil autoignites at around 350 to 400 °C; the hot housing of a K16 is well above
that. This is not a theoretical risk, it is the best-known engine-compartment
fire scenario on these cars.

The feed/return distinction changes the intensity, not the nature. A feed is at
engine oil pressure and **sprays**. A return is a gravity drain, with almost no
pressure, and **drips**. Both end up in the same place.

No refinement of the drawing removes this failure mode. The part stays
`prohibited_pending_engineering`, and would even with a perfect geometry.

## Second reason, and the more interesting one: titanium is the wrong metal

Even setting fire aside, the repository's grid rules titanium out here, and on a
criterion that is easy to forget.

`TITANIUM.md` lists among the cases where titanium **is not** relevant:
"untreated sliding contact or **repeated threading exposed to galling**".

An oil line is taken apart at service. Its fittings — banjos, swivel nuts — are
tightened and loosened several times in the life of the part. Titanium galls,
against itself as against steel, without surface treatment. That is exactly the
exclusion case.

So if this part is one day remanufactured in additive, **it is in nickel or in
steel**, not in titanium. The best additive candidate of the triage is not a
titanium candidate. The two questions are not the same, and that is the lesson
to keep from this examination.

## What would unblock the part

To take it out of `prohibited_pending_engineering`, it would take, in this
order:

1. the feed/return attribution of each reference, and the real pressure of each
   branch;
2. the measurement of a specimen: length, diameters, flanges, interfaces, and
   the relative engine/turbo movements the line must absorb;
3. a qualified hot material card, with resistance to thermal cycling and to oil;
4. a pressure and leak test, then a vibration endurance test at temperature;
5. a signed engineering review, in the sense of `SAFETY.md`, explicitly covering
   the fire risk.

That is a program, not a print. It has no place in a first metal run.

## Consequence for the current selection

The exhaust tip remains the first titanium part. It gains less on consolidation
than the oil circuit — but it sets nothing on fire, and its interfaces do not
come apart at every oil change.
