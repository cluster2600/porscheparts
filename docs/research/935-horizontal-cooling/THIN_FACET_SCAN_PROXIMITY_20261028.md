# 935 rotor: thin-facet proximity to the aligned scan

This diagnostic targets the 24 triangles below normalized quality 0.01 on the
protected 0.7-root analysis surface. It does not establish historical
dimensions, measured-surface identity, or permission to manufacture. The
scan's source unit is uncalibrated; its acquisitions and functional axis
remain independently unverified.

## Input frame and method

The [frame audit](../../../twins/935-horizontal-cooling-system-f0/source/gmsh-fluid-study-20261028/verify_scan_frame.py)
checks the original OBJ hash, the derived axis-aligned scan hash, the stored
rigid transform and its inverse. All 624,492 vertices match the transformed
original with maximum error `1.41753e-13` source unit. This verifies numeric
transport of the stored vertex coordinates. It does **not** validate the
physical datum, correct misaligned scan acquisitions, or calibrate the unit.

The [proximity probe](../../../twins/935-horizontal-cooling-system-f0/source/gmsh-fluid-study-20261028/probe_thin_facets_scan.py)
checks the 113 analysis triangles below quality 0.05. For each it measures
nearest distance to the aligned scan triangles at seven points: the three
vertices, three edge midpoints and centroid. These are point samples, not a
whole-triangle or bidirectional surface bound. Distances of 0.5 and 1.0 below
are **diagnostic bins in unknown source units**, not scanner tolerances.

| Sample group | Faces | Median of each face's largest sampled distance | Faces with all samples within 0.5 | Faces with at least one sample beyond 1.0 |
|---|---:|---:|---:|---:|
| Quality below 0.01 | 24 | 2.7902 | 9 | 15 |
| Nearby faces with quality at least 0.2 | 24 | 2.7887 | 9 | 15 |

Each control is a distinct good-quality analysis face selected nearest to a
thin-face centroid. Median and maximum distances between paired centroids are
0.1222 and 0.1506 source unit. The similar scan distances in this small,
location-matched sample show that a large distance can be shared by good and
poor triangles nearby. They do not establish why a face is thin, whether the
local scan is complete, or which surface is historically correct.

The [section-station screen](../../../twins/935-horizontal-cooling-system-f0/source/gmsh-fluid-study-20261028/audit_thin_facet_sections.py)
assigns each thin-face centroid to the nearest of nine blade phases, projects
it onto that blade's section direction, and compares the projection with the
last registered acquired section of that blade. Nine of 24 lie beyond that
station; eight of those nine also have at least one sample farther than one
source unit from the scan. The maximum phase offset is 17.36°. This is a
positional screen, not proof that a face is measured or reconstructed. The
upstream section pipeline fits observed cuts and records any short-gap
interpolations; a registered-section label does not certify every profile
point as directly acquired.

The [private visual overlay](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/thin-facet-scan-proximity.png)
has SHA-256 `f04b5a1ed0c3c75efd2b16c992eb980ce2a8bb8b050f984f0473e64b4b33a5fa`.
The [private evidence package](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/thin-facet-scan-proximity-20261028.tar.gz)
contains the scripts, receipts and visual, SHA-256
`79e37ea6bd8f114225c5b56e7cb2d56730805b92f291bcc1f7396c4909a22609`.
All eight package members passed hash readback, and the release asset
digests matched. Raw scan and rotor geometry are not included in the package.

## Reproduction on Apple Silicon

The successful run used Python 3.12.11, NumPy 2.5.4, SciPy 1.18.1,
trimesh 5.2.0 and Rtree 1.4.1. Set `ROTOR_SCAN_OBJ` to the private original
OBJ and use fresh outputs under `work/`. The other inputs are private
derived artifacts already retained by this project.

```sh
src=twins/935-horizontal-cooling-system-f0/source/gmsh-fluid-study-20261028
out=work/935-facet-provenance-20261028
uv run --no-project --python 3.12 --with numpy==2.5.4 \
  python "$src/verify_scan_frame.py" "$ROTOR_SCAN_OBJ" \
  work/935-reconstruction-20261005/surfaces-002/rotor/axis-aligned.npz \
  work/935-reconstruction-20261005/surfaces-002/rotor/axis.json "$out/NEW-frame.json"
uv run --no-project --python 3.12 --with numpy==2.5.4 --with scipy==1.18.1 \
  --with trimesh==5.2.0 --with rtree==1.4.1 \
  python "$src/probe_thin_facets_scan.py" \
  work/935-root-quality-local-20261025/analysis-candidate.off \
  work/935-reconstruction-20261005/surfaces-002/rotor/axis-aligned.npz "$out/NEW-proximity.json"
uv run --no-project --python 3.12 --with numpy==2.5.4 --with trimesh==5.2.0 \
  python "$src/audit_thin_facet_sections.py" \
  work/935-root-quality-local-20261025/analysis-candidate.off \
  work/935-native-six-20261012/individual-sections-002/sections.json \
  "$out/NEW-proximity.json" "$out/NEW-frame.json" "$out/NEW-sections.json"
```

Repeated runs on this Mac reproduced all three receipt hashes. Because the
section screen pins the complete preceding receipt bytes, a change of numeric
runtime or platform can require a fresh, independently reviewed receipt rather
than silently accepting different values.
