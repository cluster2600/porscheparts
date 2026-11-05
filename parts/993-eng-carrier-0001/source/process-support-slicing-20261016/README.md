# Exact support sections in parallel

This module calls the rational hook `exact_support_section.py` without modifying it.
Four processes compute whole layers; the parent consumes the regions
in their original order, at the exact height of each layer. At most eight layers
are pending. The files, the hook and the dispatcher are verified
by SHA-256 before and after the computation. The process group is closed even
on rejection.

```python
with ParallelSupportSections(ordered_npz_paths, exact_layer_heights, workers=4) as cuts:
    core.support_section = cuts
    # Exécuter le CORE gelé, avec les mêmes surfaces et le même ordre de couches.
receipt = cuts.receipt()
```

(The comment in the block reads: run the frozen CORE, with the same surfaces and
the same layer order.)

The receipt must report all consumed layers and the closure of the group.
It replaces neither the admission of the support geometry nor the independent audit
of all their trajectories.

`benchmark.py` keeps the initial trial, interrupted on a non-zero rational section
that could not be encoded as a non-zero float64 segment. `benchmark_v2.py`
records each of the ten planes fixed in advance: rejections remain rejections,
and the arrays and their order must be identical on the encodable planes.
The old sheets used for this trial remain rejected.

```sh
AM_PYTHON -B -m unittest discover -s tests -p test_carrier_parallel_supports.py -v
AM_PYTHON -B parts/993-eng-carrier-0001/source/process-support-slicing-20261016/benchmark_v2.py \
  work/part-workflow/run-001/process work/carrier-process-20261016/support-benchmark-new
```

`AM_PYTHON` denotes the Python of the PySLM runtime installed by the project.
