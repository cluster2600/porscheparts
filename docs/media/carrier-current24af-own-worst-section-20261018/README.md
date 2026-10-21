# Current 24af: native geometry at its own worst coarse peak

![Actual current24af native section and projected 3D chords](carrier-current24af-own-worst-section.png)

[PDF](carrier-current24af-own-worst-section.pdf) · [editable SVG](carrier-current24af-own-worst-section.svg) · [render record](render-receipt.json) · [ROOT review](evidence/root-terminal-review.json) · [file inventory](archive.json)

This is the **current coarse all20 snapshot** of the unchanged **24af0584**
geometry. The actual unfiltered worst integration-point stress is **1,904.28 MPa**
in reverse-torque combined loading with spring supports, at element **81426 / IP3**.
The displayed point is **(−87.4636936199211, 15.532077633276918,
17.247453314523334) mm**. Refined results are separate; this image does not
establish stress convergence or adequate strength.

The [raw native section](native-context/own-worst-section.brep) lies at the
actual point's **X = −87.4636936199211 mm**. All **28 curves / 708 samples**
are retained in the [complete coordinates and parameters](native-context/own-worst-section-data.json).
Both panels submit the complete section; the right panel only crops its display
to the actual peak-element bounds, with equal Y–Z axis scale.

Dashed segments are explicitly the Y–Z projections of two qualified reciprocal
3D normal-chord pairs at that point: **40↔36** gives **2.196040840 / 2.195968387 mm**,
and **42↔85** gives **1.705491771 / 1.704017387 mm**. Endpoint X coordinates differ;
these lengths are **not thicknesses of the section** or a global minimum. Native
face indices identify only this exact query body. All **four local NULL rows**
and the complete five-probe **eight qualified / 32 unresolved rows** remain in
the [render record](render-receipt.json) and [full native observation](native-context/five-probe-assessment.json).

The PNG, SVG and PDF are exact copies of annotation revision002. ROOT personally
viewed the PNG and actual PDF-page raster: the two-line right title fits and the
labels are legible. The [PDF QA](evidence/pdf-QA.json) retains the original
100dpi raster and PDF identity. The [001 title-overflow refusal](history/figure001-title-refusal-root.json)
and its original local PASS are preserved as history;002 changes only that title's newline.
No CAD extraction, solver, render or PDF authoring is performed for publication.

[Sources and inverses](source/render002-from001.json), [whole collector replay](source/collect_terminal.py),
[controls](controls/plan.json) and the [external input map](external-inputs.json)
retain the exact original work paths and **219 external runtime files**. They are
review snapshots, not a portable replay. A read-only recheck in the original
local environment imports the original collector and calls `collect()` without
its file-writing main block; the existing owner is never overwritten:

```python
import importlib.util
from pathlib import Path
path = Path("work/carrier-current24af-own-worst-section-figure-preparation-002/collect_terminal.py").resolve()
spec = importlib.util.spec_from_file_location("section002_readonly", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
result = module.collect()
print(result["status"], result["output_file_count"])
```

Run this from the repository root with the recorded local Python environment.
The [numerical checkpoint](../../reports/carrier-rib-20261018/README.md) keeps
current geometry, coarse/refined mechanics and print-preparation scopes separate.
