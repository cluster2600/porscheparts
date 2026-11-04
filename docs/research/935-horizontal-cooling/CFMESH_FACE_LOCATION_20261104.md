# Location of rejected cfMesh faces — 4 November 2026

This read-only diagnostic classifies the OpenFOAM face sets from the existing
case 006 of the [broader facet trial](BROADER_FACET_REPAIR_20261028.md). It
uses the serialized `boundary` face ranges, not geometric proximity. The
[script and aggregate receipt](../../../twins/935-horizontal-cooling-system-f0/source/cfmesh-face-location-20261104/)
record SHA-256 hashes of each input. The complete native case is in the
private archive cited in the earlier report. The labels are case-local indices;
they do not identify a location on the physical scan.

| `checkMesh` face set | Internal | Rotor boundary | Other boundaries |
|---|---:|---:|---:|
| skewFaces | 0 | 6 | 0 |
| nonOrthoFaces | 49 | 0 | 0 |
| lowWeightFaces | 91 | 0 | 0 |
| lowVolRatioFaces | 134 | 0 | 0 |
| meshQualityFaces | 232 | 211 | 0 |
| concaveFaces | 11,694 | 150 | 0 |

Sets can overlap and use different criteria; they must not be summed. Internal
faces may still be adjacent to the rotor. These counts do not establish the
cause of defects, the original scan coverage, or distance to a blade feature.
The case remains rejected for CFD, and the [admissibility record](../../../twins/935-horizontal-cooling-system-f0/admissibility.json)
continues to apply. The useful next diagnostic is to map internal bad-face
centres and their adjacent cells against the rotor surface and identify local
clusters before proposing a new geometry or mesh experiment.

Reproduce on the retained ASCII OpenFOAM case, with its `constant/polyMesh`
directory as the first argument:

```sh
python3 twins/935-horizontal-cooling-system-f0/source/cfmesh-face-location-20261104/classify_faces.py \
  "$CASE/constant/polyMesh" skewFaces nonOrthoFaces lowWeightFaces \
  lowVolRatioFaces meshQualityFaces concaveFaces
```

The script checks the set counts, uniqueness and boundary-range continuity.
It does not parse the full faces file or independently rerun `checkMesh`.

## Distance screen on Kali1

A follow-up [screen](../../../twins/935-horizontal-cooling-system-f0/source/cfmesh-face-location-20261104/distance_screen.py)
compares the arithmetic mean of each selected face's vertices with the nearest
of 349,542 vertices on the **meshed** rotor patch. The corresponding
[aggregate receipt](../../../twins/935-horizontal-cooling-system-f0/source/cfmesh-face-location-20261104/case-006-distance.json)
records the input hashes. Because a patch vertex is a point on the mesh, this
is an upper bound to the distance from the selected face's vertex mean to that
patch; it is not the exact closest-triangle distance or a face-to-face bound.

| Internal face set | Count | Median upper bound | Maximum upper bound |
|---|---:|---:|---:|
| nonOrthoFaces | 49 | 0.00014565 | 0.00027935 |
| lowWeightFaces | 91 | 0.00015165 | 0.00030535 |
| lowVolRatioFaces | 134 | 0.00013106 | 0.00030535 |

Distances are in case coordinates, treated as metres only under the unverified
0.001 m/source-unit assumption. All selected vertex means are within 0.001 case
unit of a rotor patch vertex. The sets overlap; proximity is not proof of a
causal geometric defect and does not establish physical blade dimensions.
The result supports inspecting the rotor-adjacent cells rather than assuming
that every internal defect is remote from the wall. No mesh is admitted and no
fluid solution follows from this screen.

```sh
python3 twins/935-horizontal-cooling-system-f0/source/cfmesh-face-location-20261104/distance_screen.py \
  "$CASE/constant/polyMesh" nonOrthoFaces lowWeightFaces lowVolRatioFaces
```

Kali1 ran Python with NumPy 2.3.5 and SciPy 1.16.3. Exact patch-surface
closest-point checks and spatial clustering remain future diagnostics.

## Cell connectivity to the rotor patch

The [connectivity screen](../../../twins/935-horizontal-cooling-system-f0/source/cfmesh-face-location-20261104/adjacency_screen.py)
reads OpenFOAM owner and neighbour labels and forms the set of cells owning a
rotor boundary face. Input hashes and counts are preserved in the
[aggregate receipt](../../../twins/935-horizontal-cooling-system-f0/source/cfmesh-face-location-20261104/case-006-adjacency.json).
A synthetic four-face case checks the owner/neighbour logic, including a face
with both cells on the wall and rejection of a boundary face in an internal set.

| Internal face set | Faces | At least one wall-adjacent cell | Both cells wall-adjacent |
|---|---:|---:|---:|
| nonOrthoFaces | 49 | 49 | 49 |
| lowWeightFaces | 91 | 91 | 91 |
| lowVolRatioFaces | 134 | 134 | 131 |

Here, wall-adjacent means the cell owns at least one face in the serialized
rotor patch. It does not mean that the flagged face itself is on the wall or
that a specific scan defect caused its quality failure. Sets overlap. The
rejected trial's topology motivates local inspection of these cells and their
associated rotor faces, not a CFD performance claim.

```sh
python3 twins/935-horizontal-cooling-system-f0/source/cfmesh-face-location-20261104/adjacency_screen.py \
  "$CASE/constant/polyMesh" nonOrthoFaces lowWeightFaces lowVolRatioFaces
```

The flagged faces touch 92, 138 and 231 distinct rotor-owner cells for the
three sets respectively. Those cells own 257, 335 and 651 of the 341,555 rotor
boundary faces. These are incidence counts, not distinct spatial clusters or a
fraction of acquired scan surface. A separately written calculation reproduced
the counts. The next inspection should map these boundary faces to surface
regions and distinguish measured, interpolated and reconstructed areas where
that provenance can be established.

## Connected subsets of incident wall faces

Among the 257 rotor faces incident to cells touching `nonOrthoFaces`, the
[edge-connectivity screen](../../../twins/935-horizontal-cooling-system-f0/source/cfmesh-face-location-20261104/wall_components.py)
finds 44 components; the largest contains 10 faces. The
[receipt](../../../twins/935-horizontal-cooling-system-f0/source/cfmesh-face-location-20261104/case-006-wall-components.json)
records the input hashes. Connectivity uses shared whole mesh edges **only
between selected faces**. Unselected wall faces may connect these components,
so this count is neither the number of physical defects nor proof of spatial
separation. A synthetic control checks edge sharing and vertex-only contact.
No physical coordinates or private mesh are published.

## Private spatial view

The [three-view plot](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-wall-reach-20261104.png)
shows vertex-mean positions of the 257 incident wall faces against one sampled
face in 20 from the case's rotor patch. SHA-256:
`f59cc6b413e698ed0fb55785e98bd2eb49733da2abf06952d39058423d33a411`.
The highlights appear on multiple sectors, including near blade tips. This is
the rejected provisional CFD boundary, not a direct scan overlay; perspective
and marker overlap do not establish how many physical defects exist. The
[renderer](../../../twins/935-horizontal-cooling-system-f0/source/cfmesh-face-location-20261104/render_wall_reach.py)
reads the retained case and refuses to overwrite its output.

## Point-sampled proximity to the aligned scan

The incident wall-face vertex means and a 1-in-20 wall-face sample were exported
from the retained case. Their [private coordinate archive](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-wall-centres-20261104.npz)
has SHA-256 `fd93d57463e616e3b1940ecf9ff8d7931c0db17fcdd95e01a258e245a0ad7954`.
The [scan screen](../../../twins/935-horizontal-cooling-system-f0/source/cfmesh-face-location-20261104/scan_proximity.py)
multiplies case coordinates by 1,000, reversing the recorded provisional
0.001 conversion, and measures each point against scan triangles. The aligned
scan and the numeric transform are previously documented; their physical
registration and scale remain unverified.

| Point sample | Count | Median scan distance | 95th percentile | Over 1 source unit |
|---|---:|---:|---:|---:|
| Incident wall-face means | 257 | 0.0586 | 4.8701 | 39 |
| Distinct nearby sampled-wall controls | 257 | 0.0621 | 4.6822 | 64 |

Controls are selected from the sparse wall sample, with a median separation
of 1.953 and maximum 5.882 source units from their paired target. These are
not tightly matched surface patches. The distances concern one point per face,
not full-face containment. Similar medians do not identify why the volume
mesh failed, establish measured-surface identity, or validate the frame.
[Aggregate receipt](../../../twins/935-horizontal-cooling-system-f0/source/cfmesh-face-location-20261104/case-006-scan-proximity.json).

## Sampled distance to the mesher input

The [input-distance screen](../../../twins/935-horizontal-cooling-system-f0/source/cfmesh-face-location-20261104/wall_input_distance.py)
compares the 257 incident wall-face vertex means and 2,048 deterministic points
from the sampled wall to triangles of the broader-repair rotor input. It uses
case coordinates multiplied by 1,000, the inverse of the provisional export
conversion. A single-triangle analytic distance control passed. The
[aggregate receipt](../../../twins/935-horizontal-cooling-system-f0/source/cfmesh-face-location-20261104/case-006-input-distance.json)
pins both inputs.

| Sample | Median distance | 95th percentile | Maximum |
|---|---:|---:|---:|
| Incident face means, 257 | 0.000398 | 0.027698 | 0.327132 |
| Sampled wall means, 2,048 | 0.000693 | 0.044979 | 0.383747 |

All figures are in uncalibrated source units. A vertex mean need not lie on a
concave polygon, and these samples do not bound complete polygons or provide
the reverse input-to-output distance. Thus they are a diagnostic only, not a
surface-fidelity admission, physical tolerance, or proof that a local feature
caused the volume-quality failures.

## Reverse sampled vertex bound

The [reverse screen](../../../twins/935-horizontal-cooling-system-f0/source/cfmesh-face-location-20261104/reverse_vertex_bound.py)
selects 4,096 deterministic input-triangle centroids and queries the nearest
of 349,542 vertices of the cfMesh rotor boundary. The median nearest-vertex
distance is 0.2846 source unit, p95 is 0.6880 and maximum is 0.9906. All
figures use the unverified scale conversion described above. Since a mesh
vertex lies on the boundary, each value is an upper bound on that sampled
point's distance to the polygonal wall; it is not the exact surface distance.
Values over a chosen threshold therefore do not prove an actual wall deviation.

The [aggregate receipt](../../../twins/935-horizontal-cooling-system-f0/source/cfmesh-face-location-20261104/case-006-reverse-vertex-bound.json)
pins the rotor and wall-vertex hashes. The wall vertices are stored in the
[private archive](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-cfmesh-rotor-vertices-20261104.npz),
SHA-256 `0d7b4fa7d7456670cd22970c3f772be7f8d852c40e55fb6680233dbba22bfef7`.
The result is not a complete bidirectional surface bound and cannot admit the
mesh for CFD. Polygon-aware closest-point and coverage checks remain open.

## Reverse sample against a triangulated wall

OpenFOAM 13 `foamToSurface -constant -tri` produced a four-patch OBJ for the
retained case. Its default six-digit output was rejected for this comparison.
With a temporary `writePrecision 17` controlDict, every one of the 445,416
exported boundary vertices had an exactly matching native mesh point. The
rotor group contains 699,084 triangles. The [private rotor OBJ](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/cfmesh-rotor17-20261104.obj)
has SHA-256 `60f8564a87add660078b8609b09d6bfe6b8e439f146afe02ad6de91457b37f35`.
The entire four-patch OBJ hash is
`ef55f2f8da305459209538c5580a438d4998abea4f28425ad1b84e584733958b`.
The coordinate check does not independently certify every triangulated polygon.

The [reverse triangle screen](../../../twins/935-horizontal-cooling-system-f0/source/cfmesh-face-location-20261104/reverse_triangle_sample.py)
compares the same 4,096 deterministic input-triangle centres to the exported
rotor triangles. In uncalibrated source units its median is 0.03998, p95 is
0.18500 and maximum is 0.58706; three sampled points exceed 0.5. The
[aggregate receipt](../../../twins/935-horizontal-cooling-system-f0/source/cfmesh-face-location-20261104/case-006-reverse-triangle-sample.json)
records hashes. This is a sampled comparison to OpenFOAM's triangulation, not a
whole-surface Hausdorff bound or a tolerance decision. The provisional scale,
scan coverage, boundary fidelity and failed volume checks remain unresolved.

## Spatial review of the three reverse-sample outliers

The three sampled input points over 0.5 source unit from the triangulated wall
appear on different rotor sectors; their minimum pairwise separation is 69.67
uncalibrated source units. This does not identify the cause, establish a
physical dimension, or exclude additional errors between samples. The
[private view](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/reverse-outliers-20261104.png)
has SHA-256 `d7509f4bc84a9477904e51ed6ee2eb1572c5b4a64a46949373145a4bd09a8f5b`.
The [private point archive](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/reverse-outlier-points-20261104.npz)
has SHA-256 `8436da55838c6e3963dfd397c4e8edf9f0d310fe38af138b25d89d33ab7cc59f`.

## Three outliers against the aligned scan

The [point comparison](../../../twins/935-horizontal-cooling-system-f0/source/cfmesh-face-location-20261104/outlier_scan_comparison.py)
queries the aligned scan triangles for each of the three input points and its
nearest point on the triangulated cfMesh wall. Its
[receipt](../../../twins/935-horizontal-cooling-system-f0/source/cfmesh-face-location-20261104/case-006-outlier-scan-comparison.json)
pins both private inputs. All distances below are uncalibrated source units.

| Point | Input to cfMesh wall | Input to scan | Wall point to scan |
|---|---:|---:|---:|
| 1 | 0.5570 | 0.1277 | 0.5461 |
| 2 | 0.5871 | 0.0134 | 0.4937 |
| 3 | 0.5019 | 0.1542 | 0.4613 |

For these three points the input is closer to the aligned scan than its
nearest exported cfMesh-wall point. This indicates local displacement in the
provisional wall representation relative to that input, under the existing
unverified registration. The nearest scan point can differ between the two
queries; the comparison does not establish which surfaces were directly
measured, prove the cause of poor volume quality, or validate the complete
rotor. The three locations should be considered when choosing a future
boundary-preserving reconstruction or meshing method; the existing CFD gate
remains closed.
