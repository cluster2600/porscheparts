# Original-scan intersection inspection — 28 October 2026

The detector reports **180 intersecting triangle pairs involving 196 original
faces**, including two coplanar pairs. It tested 2,466,032 of the 2,466,040
triangles. The eight exactly zero-area triangles were excluded from this detector
and retained as separately indexed defects. They were not removed from the scan.

These results describe the complete raw scan, including attached hardware.
Intersections are review candidates, not a semantic decision about casting defects,
contacts between separate components or acceptable geometry. No face was deleted,
no gap was closed and no manufacturing release was granted.

## Method and input fidelity

The [inspection script](../../../scripts/check_935_scan_intersections.py) uses
[libigl's documented predicate API](https://libigl.github.io/libigl-python-bindings/api/igl_predicates/#find_self_intersections)
with `first_only=False`. The existing DfAM sidecar's 0.0001 mm welding grid is
**not** applied. The OBJ is read directly in Float64; there is no STL conversion,
vertex welding, coordinate rounding or scale assumption.

A separate Trimesh 4.7.4 read of the verified original produced the canonical
coordinate and connectivity hashes. The libigl reader must match both before
inspection. The run matched exactly:

- Float64 vertex array: `9c62ec1ff0cb72a26908878cd8607699745d0c7da20a5f9705a0003c04c695e2`;
- Int64 triangle array: `84177b945a073ff4f30c75983131584c2b7ed7101f9570b38d95894e8d013303`.

Source identity is checked before and after execution. Output must be a new
directory. Pair indices are mapped back to the original faces after excluding
zero-area triangles from the computational input. This exclusion is explicit:
a detector result on the remaining faces cannot certify the entire source.

Six controls run before the full intersection inspection: separated triangles, crossing triangles,
coplanar overlap, ordinary shared-edge adjacency, original-index mapping after a
degenerate face, and rejection of an invalid face index. All passed. These test
engine operation and indexing, not physical scan accuracy.

## Reproduction and collected files

Use an isolated Linux x86_64 CPython 3.12 environment and the
[hash-pinned wheel requirements](../../../scripts/935-intersection-requirements.txt):

```sh
python -m pip install --require-hashes --only-binary=:all: -r scripts/935-intersection-requirements.txt
python scripts/check_935_scan_intersections.py --self-test
python scripts/check_935_scan_intersections.py "$SOURCE_OBJ" "$NEW_OUTPUT"
```

Kali1 completed loading and inspection in approximately 6.34 seconds, under a
300-second timeout and a 6 GiB virtual-memory limit, with one OpenBLAS/OMP thread.
That limit is not a measured peak-memory figure. Versions: libigl 2.6.3, NumPy
2.2.6, SciPy 1.15.3. The [execution receipt](intersection-execution.json) records
these settings, code hashes and the four collected payload hashes.

Private outputs remain outside Git:

- `intersecting-source-face-pairs.npy`;
- `coplanar-pair-flags.npy`;
- `excluded-zero-area-source-faces.npy`;
- `inspection.json`, with a separate SHA-256 manifest.

All four payload hashes were verified after retrieval. No coordinates or face
arrays are published. The synthetic controls run in the dedicated GitHub workflow;
the full-scan result comes from Kali1, not CI. Previous execution receipts retain
their earlier `not_evaluated` status as historical snapshots.

## Effect on reconstruction

The scan cannot be accepted as a valid manufacturing surface merely by filling
its 928 open contours. The indexed intersections and zero-area triangles also
need review against source surfaces and component identity. Any repair must be a
separate candidate with a recorded mask, deviation analysis and independent
acceptance; this inspection does not select or authorise a repair. Scale, hidden
geometry, material, loads and process qualification remain unresolved. Vast cost
for this inspection was USD 0.
