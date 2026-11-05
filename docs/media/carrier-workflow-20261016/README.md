# Overview of the chain

[Vector diagram](process.svg), [PNG image](process.png), [PDF](process.pdf).

The drawing describes the six steps and the three inputs of the
[process](../../manufacturing/PART_WORKFLOW.md). The numbers run left to right
on the first row, then right to left on the second.
It shows the actions and the expected files, without attributing a result
to a step that has not yet finished.

The mass shown, rounded to three decimals, comes from the
[export of the retained geometry](../../../parts/993-eng-carrier-0001/derived/workflow-20261016/export.json):
1.262212620786407 kg for the STEP
`de0e55a3150dacc5428bbc301d18d2e43477f038c3f4df295d9373af8e906b63`.
The ceiling is the one Maxime asked for: 1.30 kg.

The SVG file is self-contained, with no script, downloaded font or external image.
Its text stays selectable and scaling preserves strokes and
characters. It was inspected in full in the browser, at the width
of the window, after checking its six cards and their arrows.

The exports use the already installed software `rsvg-convert 2.63.2`:

```sh
rsvg-convert --width 1500 --keep-aspect-ratio --output process.png process.svg
rsvg-convert --format pdf --width 1500 --keep-aspect-ratio --output process.pdf process.svg
```

The [export receipt](exports.json) links the three files and the mass
source. The single page of the PDF was also rendered then inspected in full.
