# 935 conservative surface: bounded local patch review

A follow-up to the [Vast diagnostics](935-printability-20261029.md) retained one
existing alternative triangulation in the open conservative surface. The new
candidate adds **29 triangles** across original contour 456, removing **31 open
edges** without moving a vertex or removing a parent face. This is a local study
repair, not acceptance that the physical opening should be closed.

The [earlier conservative surface](935-scan-repair-20261029.md), closed volume
studies and [editable reference CAD](935-scan-engineering-20261029.md) remain
unchanged. The new candidate has **94,871 boundary edges** and is not a closed
printable part. No functional or additive-process simulation was run, and no
additional paid instance was created for this follow-up.

## Selection and verification

The earlier CGAL trial rejected contour 456 because its triangulation
intersected geometry. An existing PyMeshLab alternative passed its original
filter and could be tested against the cleaned conservative parent. All 31
perimeter edges matched that parent's boundary with opposite orientation.
The 29 added faces use only existing source vertices; their total area is
approximately 0.988 mm². The owner-confirmed scale remains one OBJ unit per mm.

The whole candidate passed the independent intersection detector with zero
intersection pairs and zero degenerate triangles. Used vertices remain manifold,
no edge has more than two incident faces, and winding is consistent. An
unprocessed OBJ reload matches the NPZ coordinates and face indices exactly.
The patch mask remains separate from the parent geometry.

The three other rejected CGAL patches were retested against the updated parent.
Contours 807, 856 and 916 still produced respectively **1, 1 and 4 intersection
pairs**. None was retained. Removing more observed geometry to force their
acceptance was not part of this bounded experiment.

Native Linux execution on Kali1 reproduced all three candidate export hashes
from the Mac, every inspection field except elapsed time, and all rejected-patch
results. The detector's separated, crossing, coplanar, adjacent, degenerate-face
mapping and invalid-face controls passed. Its implementation is independent of
the PyMeshLab triangulation generator; this does not provide physical metrology.

## Reproduction and files

The [manifest](935-local-gap-review-20261029/manifest.json) binds the public
aggregate reports and the portable drivers actually executed on Kali1. The
[execution receipt](935-local-gap-review-20261029/execution.json) records runtime
versions, frozen-input verification and the unchanged acceptance gates.
The original Mac drivers, source geometry, masks and inspection image remain
private. The public reports contain no scan coordinates or face-index arrays.

Use Python 3.12 with the recorded NumPy, Trimesh and libigl versions, without
Python optimisation flags: the scientific replay scripts use assertions.
Retain this repository layout and the original private artifact directory layout.
Both output directories must be new:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python \
  docs/research/935-local-gap-review-20261029/reproduce_patch_456.py \
  /private/artifact-root /private/artifact-root/alternate-gap-456-20261029
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python \
  docs/research/935-local-gap-review-20261029/recheck_remaining_gaps.py \
  /private/artifact-root /private/new-rejected-patch-review
python scripts/check_935_scan_intersections.py --self-test
```

The private candidate is stored in
`~/Developer/PorschePartsArtifacts/935-scan-tools-20261029/alternate-gap-456-20261029/`.
Its OBJ SHA-256 is
`d09ca9e5f42c271e198975fc717ccd9d9429d280de393831a09333b408ac1608`.
The mask, NPZ and export-reload receipt are retained beside it.

This experiment neither resolves the remaining openings nor establishes the
meaning of the selected opening. Measured functional interfaces, hidden
geometry, alloy, loads, manufacturing parameters and process qualification
remain unresolved. `physical_closure_accepted` and `manufacturing_accepted`
remain false. The supplier draft remains unsent.
