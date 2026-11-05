# Print it: switch blank fit-test kit

<img src="plate.png" alt="The six fit-test blanks on the build plate, clips up" width="760">

*The six blanks as they sit on the build plate: visible face down, clips up.
Back row: set A. Front row, with a groove across the back: set B.*

This is the repository's first printable file, and it is deliberately a **fit
test**, not a finished part ([decision 0009](../../../docs/decisions/0009-first-fit-test-print-switch-blank.md)).
The real opening has never been measured, and the project measures nothing
([PROJECT_CHARTER.md](../../../docs/PROJECT_CHARTER.md)). Three level-C forum
figures exist and disagree by 2 to 3 mm
([decision 0013](../../../docs/decisions/0013-pilots-advance-on-documentary-evidence.md), section 7).
Since 2026-11-05 the kit brackets **both** hypotheses instead of one
([decision 0016](../../../docs/decisions/0016-organic-pilot-swap-and-switch-kit-bracket.md)):

| hypothesis | declared opening | sources (level C, declared) |
|---|---|---|
| **A** | 17.0 × 27.9 mm | console switch opening, Rennlist thread 750484 (0.67 × 1.10 in); faceplate opening about 17 × 28 mm, thread 1202129 |
| **B** | 19.0 × 31.0 mm | passage under the covering, about 19 × 31 mm, thread 1202129 |

| blank | marks on the back | insert (fits in the opening) | vs. its declared opening | face |
|---|---|---|---|---|
| A1 | 1 dimple | 16.6 × 27.5 mm | −0.4 mm | 20 × 30.9 × 2 mm |
| A2 | 2 dimples | 17.0 × 27.9 mm | 0.0 mm | 20 × 30.9 × 2 mm |
| A3 | 3 dimples | 17.4 × 28.3 mm | +0.4 mm | 20 × 30.9 × 2 mm |
| B1 | 1 dimple + groove | 18.6 × 30.6 mm | −0.4 mm | 22 × 34 × 2 mm |
| B2 | 2 dimples + groove | 19.0 × 31.0 mm | 0.0 mm | 22 × 34 × 2 mm |
| B3 | 3 dimples + groove | 19.4 × 31.4 mm | +0.4 mm | 22 × 34 × 2 mm |

Try set A first. An A blank that clicks in says the opening is near
17 × 28 mm; if every A blank is loose, try set B. Do not force a blank: an
over-tight blank can crack the trim. Everything except the declared openings is
a hypothesis: face overlap, face thickness, clip length (9 mm behind the face),
clip thickness and barb.

```mermaid
flowchart LR
    P["Print the plate<br/>six blanks"] --> T["Try A1, A2, A3,<br/>then B1, B2, B3"]
    T --> F{"one clicks in<br/>and sits flush?"}
    F -- yes --> R["Record which one,<br/>and how it sits"]
    F -- "all loose or<br/>all too tight" --> N["Record that too:<br/>the bracket was wrong"]
    R --> E["Evidence for the record<br/>→ next size of the part"]
    N --> E
    classDef ok fill:#e3f1e6,stroke:#2e7d32,color:#1a1a1a;
    classDef open fill:#fff4d6,stroke:#b7791f,color:#1a1a1a;
    class E ok
    class N open
```

## Files

| file | use |
|---|---|
| [`switch_blank_fit_plate.3mf`](switch_blank_fit_plate.3mf) | **open this** in PrusaSlicer (or any slicer that reads 3MF): the six blanks, placed; apply the settings below |
| [`switch_blank_fit_plate.stl`](switch_blank_fit_plate.stl) | the same plate as one STL, for other slicers |
| [`switch_blank_fit_A1.stl`](switch_blank_fit_A1.stl) … [`_B3.stl`](switch_blank_fit_B3.stl) | one blank each, to reprint only the size that fits |
| [`switch_blank_fit_plate_A.step`](switch_blank_fit_plate_A.step), [`_B.step`](switch_blank_fit_plate_B.step) | CAD, one row each, to modify |
| [`kit.json`](kit.json) | sizes and provenance, written by the generator |

Regenerate everything with `source/fit_test_kit.py` (build123d, cadsim image).

## Settings

The earlier three-blank plate sliced in PrusaSlicer 2.x on a generic 0.4 mm
nozzle in 59 min 45 s with 5.35 cm³ of filament. The six-blank plate has not
been sliced here; expect roughly twice that, as set A is slightly smaller.

| setting | value | why |
|---|---|---|
| material | **ASA or PETG**, black | PLA softens at the temperatures a closed car's dashboard reaches |
| nozzle | 0.4 mm | the clips are 1.2 mm = 3 perimeters |
| layer height | 0.15 mm (first 0.2 mm) | smooth barb ramps |
| perimeters | 3 | solid clips |
| top / bottom layers | 5 / 4 | |
| infill | 30 % | |
| temperatures | PETG 240–245 °C, bed 80 °C (ASA: 250–260 °C, bed 100 °C, enclosure) | |
| supports | **none** | the barbs overhang by 0.5 mm at about 40° |
| orientation | **as placed**: visible face on the plate | the face takes the bed's finish (textured sheet = matte) |

## After printing

1. Snap each blank in from the cabin side, clips first. Don't force it: an
   over-tight blank can crack the surrounding trim.
2. Note which blank clicks in and sits flush, and whether it rattles (the
   depth behind the panel is unknown too, so a loose-but-flush fit is useful to
   know).
3. That result is the missing evidence: it goes into
   [`catalog/measurements/`](../../../catalog/measurements/) and moves the
   record off `concept`. Until then the page says what it says: not validated.

> [!NOTE]
> This is a **non-critical** trim part (SAFETY.md: failure creates no immediate
> hazard). The exception in decision 0009 covers this part only. It does not
> extend to any functional, safety-critical or metal part in the catalogue.
