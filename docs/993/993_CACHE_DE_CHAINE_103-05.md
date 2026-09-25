# Chain case, plate 103-05 — a good additive candidate, in aluminum

The third part examined after the tip and the turbo oil circuit. The verdict
follows the same pattern, and that is what makes it interesting: the process
question and the material question do not get answered together.

## What the plate establishes

| position | references | designation |
|---|---|---|
| 1, 5 | `993 105 093 05`, `964 105 094 04` | `chain case` |
| 11, 15, 19 | `993 105 022 01`, `964 105 107 01`, `964 105 108 01` | `lid` |
| 9, 10 | `964 105 079 00`, `964 105 080 00` | `chain adjuster` |
| 21, 27, 28 | `993 107 088 00`, `993 107 087 51`, `993 107 088 52` | `bridge`, **also described as `oil gallery`** |
| 23 | `964 105 110 01` | `bearing` |
| 24 | `993 106 253 06` | `heat protection plate` |

The detail that matters is the double designation of positions 27 and 28:
**bridge and oil gallery at once**. A case, its lids, a bearing, a tensioner and
add-on oil galleries on a single plate describe a subassembly that additive
manufacturing consolidates naturally.

And the heat protection plate at position 24 tells the rest of the context:
this part has hot neighbors.

## Why it is a real additive candidate

Consolidation and internal passages, two of the three families in
`TITANIUM.md`. The oil galleries of a timing case are exactly the kind of volume
a foundry cores badly and machining reaches through cross-drillings that are
plugged afterwards. In additive, they are drawn directly.

The screening gives it a raw score of **+4**.

## Why titanium is refused there

Two reasons, after examination — and not the ones you would expect.

**Galling and the galvanic couple are not enough to refuse.** The case is
removed at service and bolts onto aluminum, that is true. But steel inserts in
the stud bosses deal with the first, and a coating plus a sealing compound deal
with the second. These are known mitigations. The grid itself says "**untreated**
sliding contact" and "**uncontrolled** galvanic couple", and `SAFETY.md` lists
their prevention among the minimum requirements for metal: they are work to be
done, not reasons to abandon.

**Differential expansion, on the other hand, has no mitigation.** The case bolts
onto the aluminum crankcase, over an extended joint face. Titanium expands
roughly half as much. At oil temperature, a long assembly between two materials
this far apart works its gasket and its fasteners. I have no joint-face design
to propose that absorbs this, and as long as I do not, the condition blocks.

**And above all, titanium does not improve on the original material.** An
aluminum casting bolted onto an aluminum crankcase: titanium loses there on
expansion, on the galvanic couple and on price, while bringing nothing in
temperature or corrosion. It is the simplest reason, and it is the one the
screening could not formulate before this part.

## The two corrections this part triggered

**First correction, in the wrong direction.** The screening treated only two of
the five counter-indications as refusals. I made all five disqualifying — and in
doing so deleted the words "untreated" and "uncontrolled" that the grid
contains. Eligible parts dropped from 5 to 1, for a bad reason.

**Second correction, the right one.** A counter-indication is a **condition to
be lifted**. It blocks as long as no mitigation is declared; a declared
mitigation turns it into a requirement carried to the route, which the supplier
will have to hold. And the question the grid nonetheless asks explicitly was
missing — "problematic corrosion **with the original material**": **does
titanium beat the incumbent?** Without it, the screening scored words instead of
comparing metals, and ranked first a lukewarm aluminum intake manifold.

## Verdict

`prohibited_pending_engineering`, and not only for data reasons: the case
carries the timing drive and pressurized oil, its failure can cost the engine,
and the plate itself flags a hot neighborhood.

If this subassembly is one day remanufactured in additive — and it deserves to
be — it will be **in aluminum**, which follows the expansion of the crankcase and
removes the galvanic couple. Not in titanium.

This is the third time in a row that the examination separates the two
questions. It is starting to look like a rule, and it is now written in
[`SAFETY.md`](../../SAFETY.md): process and material are two independent
judgments, delivered separately.

## What this screening does not say

It covers the 33 records in `catalog/parts`, not the car. The 993 factory
catalogue counts **6,259 distinct references**; the records cover a fraction of
a percent of them. "A single eligible part" is therefore a sentence about the
state of the repository, never about the automobile. The wide sweep is the PET
triage, which keeps 70 designations of which only three have been examined to
date.
