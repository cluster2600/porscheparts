# STEP exchange route — m64-cooling-fan-0001 (honest status)

Status: `parametric_source_ready_step_conversion_unproven`
Date: 2026-09-29. Branch `wave2/fan-stp-20260929`.

## What the pipeline actually emits today (proven)

The two parametric programs in this directory (`M64Fan.cs`,
`M64CrankcaseInterface.cs`) run against the pinned PicoGK managed assembly
(`/app/PicoGK.dll`, native `picogk.26.2`) and export **STL only**. The
managed API verified against the pinned assembly's own documentation file
(`PicoGK.xml`, member list) exposes exactly these file-level sinks/sources:

- `Mesh.SaveToStlFile(System.String, PicoGK.Mesh.EStlUnit, ...)` — used by both programs;
- `Mesh.mshFromStlFile(...)` — STL re-import;
- `Voxels.SaveToCliFile`, `Voxels.SaveToVdbFile`, `OpenVdbFile.SaveToFile`,
  `SaveToSvgFile`, `SaveJpg/Png/Tga`.

There is **no** `SaveToBoffFile`, no STEP, and no B-Rep writer in this API
surface. Any claim that this pipeline produces STEP directly is false. The
generated meshes are voxel-surface triangulations, and prior audits elsewhere
in this repository (for example
`twins/m64-cylinder-head/source/picogk-local-junction/README.md` and
`twins/993-m64-60-piston-gallery-f0/evidence/picogk-f0/README.md`) found
zero-area and non-manifold edges in raw PicoGK STLs, so an exported STL is
not automatically a clean watertight mesh either.

## Supported conversion path to STEP (declared route, not yet executed for this part)

Repository policy (docs/TOOLCHAIN.md, docs/decisions/0002-scriptable-toolchain.md)
keeps STEP/FreeCAD as the dimensional-truth format and lists the order of
master formats: script → `.step` → manufacturing derivatives. For voxel
pipelines the only mesh→B-Rep route currently inventoried in this repository
is:

1. **STL (this pipeline, proven)** → mesh repair/cleanup if needed
   (pymeshlab, in the `3dprinting993-cadsim` / geometry-qa images);
2. **mesh → B-Rep STEP**: OpenCASCADE via FreeCAD or build123d/CadQuery
   (OCCT kernel, both in the repository's container images; FreeCAD is
   explicitly accepted for "STEP inspection and visual check", and
   `containers/examples/cad_to_fea.py` demonstrates a scripted STEP chain
   with no GUI);
3. Optionally **STEP → OpenUSD scene** with `usd-convert-cad 0.2.0`
   (STEP→USD direction only; `containers/simready-preflight/convert.py`).

Honest limits of this route:

- The OCCT mesh→B-Rep conversion of a 600k+ triangle voxel STL has **not been
  run on these parts**; no STEP file exists yet in `export/`, and none is
  claimed. Stitching a faceted surface into B-Rep faces yields a heavy,
  faceted STEP, not an analytic solid.
- A converted STEP inherits every assumption of the source: it can at most
  carry `dimensionally_reviewed` status per docs/WORKFLOW.md §4, never
  `prototype_fitted` without recorded fit evidence.
- The USD path never carries a manufacturing dimension on its own
  (docs/TOOLCHAIN.md).

## Bottom line

For `m64-cooling-fan-0001` the deliverable is a **parametric source** plus
**STL** outputs. A STEP exists only if someone runs and records step 2 above;
until then, "STEP" in this lane names a target format, not an output.
