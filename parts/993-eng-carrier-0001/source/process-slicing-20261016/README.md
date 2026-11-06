# Ordered slicing and toolpath checks

This branch keeps the native Trimesh/PySLM intersection cases and hatches. It
prepares the Z bounds of each triangle, then computes the independent layers
in **four processes**, with at most eight pending results. File publication
and the support section remain ordered in the parent process. The pose is
fixed before the bounds are prepared; the workers modify neither the vertices
nor the hatch parameters.

## Checks run

The eight layer planes 0, 166, 167, 299, 518, 701, 900 and 1033 were fixed
before the benchmark of the real carrier. The contour coordinates, their
order, the hatch vectors and the areas are **exactly equal** to the initial
sequential path. The
[four-process benchmark](parallel-benchmark.json) measures 32.282 s against
11.808 s, start-up included; the maximum observed per worker is 178 MB and the
pool is closed after computation. This result on eight layers is not
presented as a complete preparation time.

The [pre-selection alone](serial-filter-benchmark.json) also keeps the eight
results, but gives no time saving on this witness. This result is kept: the
observed speed-up comes from working on the layers simultaneously.

The [ten native tests](native-tests.json) cover holes, planes at boundaries,
refusal of an open section, process order, process shutdown, nested rings and
duplicated segments. The counter-example of a segment whose two ends are in
the material but which crosses a hole is explicitly refused.

## Vector audit

`audit_scanpaths.py` rebuilds the section domain with ring parity, which keeps
holes and islands, whatever their orientation. It checks the **entire
segments** of hatches and contours with
[Shapely covers](https://shapely.readthedocs.io/en/stable/reference/shapely.covers.html).
No buffer moves the boundary and no outside segment is admitted.
Zero lengths and exact duplicates are refused. The relative tolerance of
1e−10 applies only to comparing the rebuilt area with the CSV, not to
toolpath coverage. The `symmetric_difference_all` API, marked incorrect and
deprecated by its publisher, is not used.

The [first toolpath witness](part-scanpath-witness.json) passes on five
recorded layers of the initial refused run. It constitutes neither a complete
audit of the 1,034 layers nor an admission of its supports. The complete
report must carry `complete_build_audited: true` to cover a new run.

## Entry point for the new preparation

```sh
CHEMIN_DU_PYTHON_AM parts/993-eng-carrier-0001/source/process-slicing-20261016/build_parallel.py \
  work/PASSAGE/surface/carrier-remeshed.stl work/NOUVELLE_PREPARATION \
  --identity-receipt work/PASSAGE/surface/meshing.json --workers 4

CHEMIN_DU_PYTHON_AM parts/993-eng-carrier-0001/source/process-slicing-20261016/audit_scanpaths.py \
  work/NOUVELLE_PREPARATION work/NOUVEL_AUDIT_TRAJECTOIRES
```

In these commands, `CHEMIN_DU_PYTHON_AM` is the path to the AM Python
interpreter, `PASSAGE` is the run, `NOUVELLE_PREPARATION` the new preparation
and `NOUVEL_AUDIT_TRAJECTOIRES` the new toolpath audit.

The region and skin generator of `process-skins-20261016` remains subject to
its own envelope, contact and collision checks. This entry point does not
exempt it from their admission. The initial run and its sources remain
unchanged.
