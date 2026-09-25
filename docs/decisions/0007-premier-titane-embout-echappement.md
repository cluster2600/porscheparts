# 0007 — The first titanium part will be the exhaust tip, and a measurement decides the alloy

Date: 2026-09-11

## Decision

Retain `993-EXH-OVAL-TIP-TI-F1-0001` as the repository's first titanium part.
**Do not fix the alloy.** Ti-6Al-4V and Ti-6242 are both screened; what
separates them is a temperature of 427 °C that has never been measured.

## How the part was chosen

Not by elimination — that is the mistake [0005](0005-alsi10mg-nest-pas-un-choix.md)
corrected. The written grid of [`TITANIUM.md`](../TITANIUM.md) and the three
families where additive manufacturing wins were applied **to the catalogue's 32
records** by `scripts/screen_titanium_candidates.py`. The input judgements are
declared as such in `catalog/manufacturing/titanium-am-screen-inputs.json`:
contradicting a cell changes the rank, and that is intended.

| rank | part | score | verdict |
|---|---|---:|---|
| 1 | **oval tip, titanium variant** | **+6** | retained |
| 2 | three-runner intake manifold | +5 | aluminum remains the right material there |
| — | exhaust manifold | +7 | best score of the batch, **900 °C: a nickel case** |

Only five parts out of thirty-two are eligible. Twenty-seven fall on the safety
class, the absence of an additive family, temperature, the need to conduct heat
or the obligation to keep steel stiffness.

The tip wins because everything converges: consolidation of the duct, the shell
and the eight ribs into a single body, an annular cavity that no machining can
produce, small series, benign failure, and **a single interface to measure** —
the outlet diameter. The precedent exists at the highest level: APWorks prints
the exhaust outlet of the Bugatti Chiron Pur Sport in titanium.

## What the screening found that nobody would have guessed

My first temperature estimate was 300 °C. The part's F0 record declares a
surface at **700 K, i.e. 427 °C**. The repository's figure is the one that was
retained, not mine — and it overturns the answer.

| | Ti-6Al-4V | Ti-6242 |
|---|---|---|
| screening mass | **212.3 g** versus 406.4 g in IN625, i.e. **−47.7%** | 217.6 g |
| creep ceiling | 400 °C | 550 °C |
| margin at 427 °C | **−27 °C** | +123 °C |
| published layer thickness | 30 µm | none |
| published minimum wall | 0.3 to 0.4 mm | none |
| published heat treatment | 800 °C 2 h under argon | none |
| available at a service bureau | **yes, everywhere** | **no** |
| closed gates at step 04 | 6 | 10 |

The two routes exclude each other cleanly. Ti-6Al-4V is a real route, available,
documented, blocked by **a single figure**. Ti-6242 settles that figure and loses
everything else: no machine, no layer thickness, no supplier. Its first published
LPBF implementation dates from 2020; it is a research topic, not a catalogue
item.

## So what decides

An infrared thermometer on the exhaust outlet, after a drive.

The 427 °C comes from a synthetic case: gas at 850 K, 3.8 L engine at
6,500 rpm, two outlets, no measurement. A real tip, downstream of the muffler,
may well run a hundred degrees lower. If the measurement gives 350 °C or less,
Ti-6Al-4V passes and the part becomes orderable from any titanium shop. If it
confirms 427 °C, the part cannot be printed in titanium at a reasonable cost,
and the answer goes back to IN625 — twice as heavy, but purchasable.

No calculation in this repository will replace that measurement.

## Where the chain stands

| step | status |
|---|---|
| 01 — geometric authority | `completed_screening` |
| 02 — BREP and mesh | **`passed`** — watertight, single-component, 13,820 triangles |
| 03 — slicing and supports | `completed_screening` — 4,936 layers at 30 µm |
| 04 — material-machine-process map | `blocked_missing_input` |

## Accepted limitations

- The deciding temperature is not measured.
- Only the 120 × 85 mm outlet envelope is published; length, inlet interface and
  insertion depth are F0 assumptions.
- Depowdering of the 2.7 mm annular channel is checked only by the 1 mm voxel
  screening. That resolution is not conclusive: an endoscopy or a CT scan is
  needed.
- Two new islands and 1,044 layers with unsupported area call for supports,
  none of which is drawn.
- The titanium/stainless galvanic couple at the fastening remains to be
  addressed.

---

## Addendum of September 11, 2026 — the scope was wrong

The decision above says "the catalogue's 32 records". That is accurate, and it
is not enough: the 993 factory catalogue lists **6,259 distinct part numbers**.
The repository's records cover **0.51%** of them. Writing "applied to the
catalogue" suggested an exhaustiveness that did not exist.

Two triages were added to fix this.

**Zone triage** — `scripts/screen_pet_zones_for_titanium.py`, on the
repository's own data only: 239 illustrations, 499 labels, 23 zones retained
covering 1,538 part numbers. Runs anywhere, including in CI.

**Part-by-part triage** — `scripts/screen_pet_parts_for_titanium.py`, on the
transcription of designations kept **outside the repository**, like
`twin_structure.py`: 1,026 distinct designations, 70 retained, covering 439 part
numbers. Only the aggregate conclusions and a short list are published; the
catalogue lines stay with their holder.

### What the wider triage finds

| score | part nos. | designation | reading |
|---:|---:|---|---|
| +5 | 12 | `heat exchanger` | 993 heater heat exchanger — **exhaust temperature, a nickel case** |
| +5 | 5 | `hot-air manifold` | hot air, not gas; aluminum is enough |
| +4 | **21** | **`tail pipe`** | **the retained part, independently reconfirmed** |
| +4 | 4 | `turbocharger` | prohibited pending engineering |
| +2 | 21 | `oil pipe` | turbo oil lines, a genuine additive case, but an oil leak onto the exhaust |

**The conclusion does not change, but it is now defensible.** The tip comes out
in the top four of a triage covering the whole car, and no longer from a basket
of thirty-two hand-picked records. The two designations ahead of it fall on the
same barrier as the manifold: exhaust temperature is nickel territory, not
titanium.

### What these triages are not

A lexical triage retains words, not functions. A three-word designation states
neither material, nor mass, nor temperature. A retained entry is not a chosen
part: it is a part **to go and look at**, by opening the PET line, then running
it through `screen_titanium_candidates.py` with a declared judgement.

The group correction rule is worth noting. The first version excluded a
designation as soon as a single one of its plates touched a component presumed
critical; `oil pipe`, which appears once on a crankcase plate, thus disappeared
even though it is one of the best candidates of the batch. The group now
excludes only if it flags **all** of the designation's plates.

---

## Addendum of September 11, 2026 (2) — the grid was applied too softly

The chain case investigation showed that the screening treated only two of the
five contraindications of `TITANIUM.md` as refusals. The other three — simple
machinable shape, galling on re-used threads, galvanic couple — were only score
penalties. Yet "When it is not" (relevant) states refusals.

All five are now disqualifying, and the ranking changes in nature:

| | before | after |
|---|---:|---:|
| eligible parts out of 33 | 5 | **1** |

The exhaust tip is no longer the best of a batch. It is **the only titanium
candidate in the catalogue**. The intake manifold falls on the galvanic couple
with aluminum, the headlight hook and the door lever on the simple shape, the
hub cap on both.

This strengthens the decision rather than weakening it, but it must be said in
that direction: it is not that the tip won; it is that all the others were
already losing and the screening did not say so.
