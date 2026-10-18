# Figure 26 — original C1 and the preserved terminal taper

These are actual native CAD sections in the same oblique plane through the
closed coarse peak 84037/IP1. The original baseline and original-C1 profiles
are reused unchanged from [figure 25](../C1-junction-section-20261017/README.md).
Only the preserved terminal-taper BREP was newly imported and sectioned.

The left panel shows original C1; the right shows the new raw taper. Both use
the same baseline reference, coordinates, scale and display crop. All native
section curves remain in the data: 30 for original C1 and 29 for the taper.
The taper's 2335 drawing points and 29 curves have different coordinate bytes
from the baseline despite equal counts. The orange ray belongs only to
original C1. No normal ray, local chord, minimum wall thickness or strength
result is inferred for the taper. The H2 peak is not substituted into this
coarse-peak plane.

The taper's one final native Build succeeded and a valid raw BREP was saved.
Its original post-Build law gate refused; that refusal remains unchanged. The
candidate is unqualified. Containment, surface screens, protected interfaces,
STEP exchange, meshing and FEA have separate scopes and are not granted by
this picture. The raw parent CAD and plotting runtime are not duplicated here.

[ROOT closed the new extraction and three same-Solid volume measurements](extraction/root-terminal-review-001.json).
The two nonadaptive overloads measured **285603.15679600753 mm³**; the adaptive
reference measured **285602.88227244973 mm³**. These remain separate numerical
operators. No Gmsh `getMass` or new T10-mesh result existed in that extraction.
[ROOT closed this English drawing](rendering/root-terminal-review-001.json),
inspected its PNG and checked SVG/XML and the one-page embedded-font PDF.
The PDF was not raster-viewed. The draw run recomputed no CAD, profiles, ray
or FEA. PNG, SVG and PDF above are byte-exact copies of its actual exports.

This capsule is an actual-evidence archive with the complete source data,
source files, historical plans/commands, supervision and ROOT receipts.
`archive.json` inventories every file except itself. The explicit figure-25
archive dependency supplies the closed original profile and its portable
closure evidence; it is not copied a second time. Installed absolute plotting
paths remain in historical records. The source files are archived unchanged;
a new portable rendering replay has not yet been executed for figure 26.
The standard-library check below reads stored evidence only and performs no
scientific imports or rendering:

```sh
python3 -I -B parts/993-eng-carrier-0001/source/progress-figures-20261016/C1-terminal-taper-profile-20261017/verify.py
```

Gallery publication and any portable replay are reviewed separately. Archived
GO receipts record their completed runs and do not authorize another run.
