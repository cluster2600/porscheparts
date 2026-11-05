# Open LPBF preparation with PySLM

This version is kept as the **initial witness refused on the carrier**.
Run `run-001` was interrupted after 526 layers out of 1,034: a support
region was omitted and native errors of vertex correspondence,
normalisation and parameter transfer were identified. The
files and their digests are kept; they do not constitute an admitted complete
preparation. The correction is developed in the separate version
`source/process-coverage-20261016/`, with per-region checks and
additional witnesses. The
[resumption dossier](../../../../docs/reports/993_CARRIER_WORKFLOW_20261016.md)
keeps the decisions of each version.

This pilot produces the sections of **all 60 µm layers**, the compensated
contours, the hatches and the toothed support surfaces of the supplied carrier.
The input is a closed STL whose SHA-256 is mandatory. Only exactly
identical vertices are reindexed; no face or coordinate is corrected.
The native Trimesh sections must be closed before their conversion to
PySLM polygons and paths. The implicit `fill_gaps()` filling of
`Part.getTrimeshSlice` is thus avoided; an open section interrupts the computation.
The pose is kept: rotation `[0, 0, 45]`, support gap of 10 mm and
plate of 500 × 500 × 20 mm. The plate occupies `z = -20…0 mm`.

## Engine and installation

[PySLM](https://github.com/drlukeparry/pyslm) is kept at revision
`8fa03f1eb98b1fbc8e617eb3119d669f356a2f0b` of 1 February 2026, under LGPL-2.1.
The digests are in `upstream.json`, and the author's licence in
`LICENSE.pyslm`. The runtime executed is Python 3.11 on macOS arm64. The
dependencies actually installed are kept in
`requirements-macos-arm64-python311.lock.txt`.

Durable installation from the repository root:

```sh
python3.11 parts/993-eng-carrier-0001/source/process-20261016/setup_pyslm.py \
  work/part-workflow/runtimes/pyslm
```

`runtime.json` gives the path of the interpreter to supply to the workflow. The
script refuses an existing directory, verifies the patch and the installed code,
checks the versions, then actually slices a box of 200 mm² section.

```sh
python3.11 -m venv /path/to/pyslm-env
/path/to/pyslm-env/bin/python -m pip install -r requirements-macos-arm64-python311.lock.txt
git clone https://github.com/drlukeparry/pyslm /path/to/pyslm-source
git -C /path/to/pyslm-source checkout 8fa03f1eb98b1fbc8e617eb3119d669f356a2f0b
git -C /path/to/pyslm-source apply /absolute/path/to/pyslm-support-projection.patch
/path/to/pyslm-env/bin/python -m pip install --no-deps /path/to/pyslm-source
```

NumPy is limited to **1.26.4**: the array-to-scalar conversions of the
tooth generator fail with NumPy 2.4. A separate patch reuses
`geometry.extrudeFace` to keep vertex correspondences during
support projection. Without this patch, the carrier caused a size
error: 1,523 heights for 1,519 vertices merged in XY.

## Execution

From the repository root, with a new output directory:

```sh
/path/to/pyslm-env/bin/python parts/993-eng-carrier-0001/source/process-20261016/build_pyslm.py \
  /absolute/path/to/carrier.stl work/new-carrier-build --sha256 INPUT_SHA256
/path/to/pyslm-env/bin/python parts/993-eng-carrier-0001/source/process-20261016/render_pyslm.py \
  work/new-carrier-build
/path/to/pyslm-env/bin/python -m unittest discover -s tests -p test_carrier_process_20261016.py -v
```

To chain the remeshing directly without copying its digest, replace
`--sha256 INPUT_SHA256` with `--identity-receipt /path/to/meshing.json`.
These options are mutually exclusive. The exact field
`candidate_STL_sha256` must match the input STL; the receipt is frozen
in `source/meshing.json` and rechecked at the end.

The render can write to a new directory with `--output DOSSIER` to
keep the previous views. Its captions are in French; the computed
layer is supplied as PNG and as vector SVG for the printed dossier.

The generator uses the 5 mm grid, the 1.5 mm tooth interval and
the 1 mm wall of the author's example. Region selection keeps the
author's other settings, recorded in the report; spline
simplification is disabled. The hatches use the PySLM default values:
0.08 mm pitch, 45° angle, one external and one internal contour. These values
are the explicit parameters of this numerical study.

## Files delivered

- `part-build.stl`, `plate.stl`, `support-*.stl` and `build.glb`: geometry
  actually generated, in the same reference frame.
- `support-*.npz`: original surfaces with the order and
  type identifiers needed for their re-inspection.
- `layers/layer-*.npz`: height, closed raw contours, compensated contours,
  hatch segments and support segments; numerical arrays without pickle.
- `layers.csv`: part area, segment counts and lengths per layer.
- `report.json`: input, versions, parameters, digests, volume integrated
  over the layers and build envelope. The launcher code and the versions are
  frozen in `source/` before the computation; their digests are rechecked
  before the final receipt.
- `build-supports.png`, `support-teeth.png`, `layer-contours-hatches.png`: views
  of the generated geometry and of an actually computed layer; `figures.json`
  keeps their digests and the coordinates of the detail view.

The PySLM supports are **wall and grid surfaces**. The engine does not
provide their fusion into a solid; their mass therefore remains `null`. The teeth
nominally penetrate 0.2 mm into the part; the lower teeth may
descend into the plate zone.
The author's algorithm may omit a peripheral skin when it cannot
pair its contours; the warning remains in the log. No
volumetric thickness or tool accessibility is deduced from an open shell.

The support sections use `trimesh.intersections.mesh_plane`, the
same intersection as the PySLM slicer, directly on the generated
surfaces. This keeps the segments without the quadratic sort of the author's
slicer. Triangles far from the layer are excluded by their Z bounds,
with the native Trimesh tolerance; `local_faces` and `cached_dots` feed the
same native intersection. Bit-for-bit equality is checked on a toothed witness,
including planes passing exactly through a vertex or an edge.
Zero-length segments and exactly identical duplicates are counted and
removed; no rounding grid modifies their coordinates. Machine order,
power, speed and machine-specific strategies remain to be
assigned. The commercial `libSLM` translators are not installed.

`support-stage.json` allows resumption with `--reuse-supports DOSSIER`: the
parameters, the pose and each support file are verified before copying.
The new results keep the digest of the generator that produced these
supports. This resumption keeps the results of a long preparation without
passing off an interrupted attempt as a complete execution.

An interrupted witness keeps `partial.json` and its computed layers; it
has no complete `report.json` receipt. Rendering with `--layer INDEX` shows it
explicitly as `PARTIAL WITNESS`.
