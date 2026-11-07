# Installed cooling: native source and conversion checks

For [issue #452](https://github.com/cluster2600/porscheparts/issues/452), the
retained full-resolution source and its actual OpenCFD ingestion are now
independently checked. Two new hexahedral trials remain rejected. A bounded
full-resolution tetrahedral trial also failed to produce a mesh. **No volume
mesh is admitted and no flow solver ran in these trials.**

This follows the [exact-subdivision investigation](../installed-cooling-subdivision-20261107/README.md).
The [result](result.json) preserves numerical findings and private artifact
identities. All original source files, historical evidence and failed attempts
remain unchanged. Raw meshes and native exports stay outside Git.

## Recover the retained full-resolution surface

The existing [geometry review](../../../twins/993-installed-cooling-f1/derived/geometry-review.json)
identifies separate input and cleaned-STL hashes. The first strict check used
the earlier input hash and correctly failed. The retained gzip instead matches
the review's compressed-file hash and contains the documented **cleaned STL**,
SHA-256 `4d91f2518aa7a92f2628783852ec77a13fcb772d5d31a35614b7fc8cff32d025`.
It is not claimed byte-identical to the earlier input.

Indexing exactly equal coordinates preserves all 918,136 triangles and 459,068
vertices without welding tolerance or geometry edits. Units remain millimetres
for this source audit. The complete CGAL 6.2.1 intersection check reports zero
pairs; all five positive/negative predicate controls pass. Independent topology
finds one component, paired oppositely oriented edges and circular vertex links.

The minimum descriptive triangle quality `4 sqrt(3) area / sum(edge_length²)`
is 0.204098, compared with 0.000429 for the historical decimated CFD surface.
No full-resolution triangles fall below 0.01; the longest edge is 2.639562 mm.
These are source-conditioning observations, not new engineering acceptance
thresholds. The source volume is about 31,980,383.8286 mm³, versus about
31,969,668.7840 mm³ for the decimated surface. This source selection is explicit;
the two surfaces are not treated as identical.

The current NumPy `port_labels` function assigns the eight patch names and
independently reproduces every one of the 91,812 historical CFD patch labels.
Its source and study hashes differ from the historical preparation; the current
inputs are pinned separately, not claimed byte-identical. Importing the entire
module initially failed because PyVista was absent. The reader extracts the
exact current function from its parsed source and needs no mesh-decimation
import. No historical source or installed dependency was edited.

## Verify the actual native ingestion

The new ASCII STL uses metres and 17 significant digits, with every vertex token
parsed back to its expected binary64 value during export. Nevertheless, all
6,494 extracted feature points initially failed exact comparison against those
binary64 coordinates. They match the same coordinates rounded to binary32.
That failed strict comparison remains recorded.

The first `surfaceMeshConvert` OBJ export used only six significant digits and
is retained as an insufficient comparison artifact. The same pinned OpenCFD
2406 image's `surfaceConvert -precision 17` then exported through its triSurface
path. The [independent reader](verify_ingestion.py) verifies **all 459,068
vertices** against binary32 rounding exactly, and all **918,136 oriented
triangles with their eight patch labels**. The maximum coordinate change is
`1.478195188475695e-8 m`. No vertices collapse. A complete CGAL check of this
verified ingested surface also finds zero intersection pairs.

The 6,732 extracted feature edges are all original source triangle edges after
that verified conversion. Their bounding boxes overlap both rejected-cell
locations. This proves source traceability, not that the feature constraints
will repair the volume mesh. The conversion is a verified runtime behavior;
its rounding bound is not a physical tolerance.

## Two rejected hexahedral trials

Both runs use the retained OpenCFD 2406 Linux/arm64 image, four CPUs, 8 GiB,
no network and a 600-second deadline. Both exit zero without OOM or timeout.
The first replaces only the source STL. Its dictionaries and quality limits
are unchanged from the reproduced 5 mm baseline.

| Trial | Cells | Standard | Extended | Concave-face warnings | Elapsed |
|---|---:|---|---|---:|---:|
| Full-resolution source | 254,962 | Pass | 2 concave cells | 17 | 23.282 s |
| Explicit feature snapping | 254,962 | Pass | 8 concave cells | 45 | 41.240 s |

The full-source failed cells are 209810 and 209833, both wall-touching hexahedra
near mirrored locations `x ≈ ±0.123 m`, `y ≈ -0.052 m`, `z ≈ 0.208 m`.
Independent raw-face/point readback confirms their identities. VTK Float32
output is used only for point identities; original ASCII mesh coordinates
remain the coordinate authority.

The second trial adds the verified feature file at refinement level zero and
changes `nFeatureSnapIter` from zero to ten, with explicit snapping enabled.
The extraction angle is 150 degrees, the complement of the unchanged
30-degree feature angle. The iteration count follows the
[OpenCFD user-guide example](https://www.openfoam.com/documentation/user-guide/4-mesh-generation-and-conversion/4.4-mesh-generation-with-the-snappyhexmesh-utility);
it is one bounded trial, not an iteration sweep. Other meshing and quality
settings remain unchanged. Failures persist around the same two junction
regions, with additional wall failures. This change is rejected.

The [full-source standard](full-source-standard.log) and
[extended](full-source-extended.log) logs, and the
[feature-snap standard](feature-snap-standard.log) and
[extended](feature-snap-extended.log) logs retain every native finding.
A zero process exit is not mesh admission.

## Tetrahedral route and converter control

Gmsh 4.15.2 received the independently verified full-resolution ingested surface,
with unchanged 5 mm sizing, two threads and fixed supplied boundary triangles.
The run stopped at its 4 GiB sampled-RSS limit after 170.656 seconds, before its
180-second deadline. Peak sampled RSS was 4,317,855,744 bytes. No mesh was
exported; boundary preservation and volume quality remain unverified.

Separately, the existing synthetic unit-cube mesh was converted using native
`gmshToFoam`. The first control failed because `checkMesh` required missing
`fvSchemes`; a fresh case adds the unchanged existing `fvSchemes`/`fvSolution`
files and preserves the failure. Both standard and extended checks then pass.
The [independent reader](verify_converter.py) confirms nine points, twelve
positive-volume cells, all six patch names and oriented boundary triangles,
and **exactly 1 m³** total volume using rational arithmetic. Point output agrees
with the declared ten-digit write precision. This qualifies the tested cube
conversion only; it does not admit a duct mesh.

The readers retain their private experiment layouts and filenames; restore the
hash-bound inputs before replay. No private payload is supplied by this report.
An admissible duct volume mesh, three-resolution sensitivity, stationary flow
checks and physical correlation remain outstanding. The full-resolution source
is still an uncalibrated packaging study, not a measured installed assembly.
