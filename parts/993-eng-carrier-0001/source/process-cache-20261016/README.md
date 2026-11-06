# Part scan-path cache

This run computes the 1,034 layers of the part alone on the admitted STL, with the
historical pose: 45° Z rotation, 10 mm clearance, 0.06 mm layer and the same
contour/hatch parameters. `ParallelLayers` keeps four processes and
at most eight pending tasks. No support is generated or reused.

```sh
PY parts/993-eng-carrier-0001/source/process-cache-20261016/test_cache.py
PY parts/993-eng-carrier-0001/source/process-cache-20261016/part_cache.py \
  work/part-workflow/run-001/surface/carrier-remeshed.stl WORK_CACHE \
  --identity-receipt work/part-workflow/run-001/surface/meshing.json
PY parts/993-eng-carrier-0001/source/process-slicing-20261016/audit_scanpaths.py \
  WORK_CACHE WORK_AUDIT
```

`PY` designates the PySLM runtime recorded in `work/part-workflow/runtime.json`.
The builder freezes its sources, the relevant dependencies and the native
binaries before starting. The final status is `part_layers_completed`; it does not
mean that the complete LPBF preparation is finished.

The reader integrates without modifying the support builder:

```python
from part_cache import CachedLayers
layers = CachedLayers(cache_directory, source_stl, core.PARAMETERS)
report = build_pyslm_skins.build(..., layer_generator=layers)
```

The object is called like `layers(part, z)` and returns `(raw, contours, vectors,
area)` in the exact native order. It requires a complete cache, the digests of
each file, the same part parameters, the same relevant versions and sources,
as well as the exact pose and vertices/faces arrays. Each
read checks again the digest of the NPZ and the identity of the part. A
change to the supports does not invalidate this part cache, but the final
run will have to compute its new support vectors and publish its own
audit.
