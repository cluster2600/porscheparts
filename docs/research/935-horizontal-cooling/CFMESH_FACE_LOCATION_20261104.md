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
