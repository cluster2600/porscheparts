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
