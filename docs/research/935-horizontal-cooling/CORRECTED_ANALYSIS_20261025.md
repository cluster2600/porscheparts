# 935 corrected rotor: bounded analysis surface and fresh fluid-case input

This continuation uses the guarded PicoGK root correction reported in the
[preceding checkpoint](ROOT_MESH_RESUME_20261025.md). It concerns the **horizontal
935 rotor**. The shroud, drive, engine interfaces and complete cooling system
still require their own measured assembly and solver evidence.

The first, 0.6-source-unit root-closing STL is
`ee8f91167f6147edd125b2b4db9da65a5704aac95879a82f2aab6bada779f9ed`.
The independently indexed mesh is
`9128da15ba5ac3ea55373c792006478deb5dd77713d52d38a9eac7c4b70d0c8e`.
Both remain private. The [OFF preparation source](../../../twins/935-horizontal-cooling-system-f0/source/corrected-analysis-20261025/prepare_surface.py)
checks both hashes and reads back every coordinate and triangle. Its output
contains 660,003 vertices and 1,320,006 triangles, with SHA-256
`5cdd1b993029a80921f995636a3a980027a66af7c87fc33ba935f7bf3a6458cf`.

## Bounded simplification

The existing [CGAL simplifier](../../../twins/935-horizontal-cooling-system-f0/source/analysis-simplification/quality_preserving_simplify.cpp)
was built on macOS with the already documented
[input-facet protection patch](../../../twins/935-horizontal-cooling-system-f0/source/analysis-simplification/protected-input-patches-20261022.patch).
This preserves three rings around inherited thin facets rather than silently
removing them. The source and patch are unchanged. The local toolchain was
CGAL 6.2.1, Boost 1.92.0, Apple Clang 21.0.0 with `-O2 -std=c++17
-frounding-math`; Python 3.12.11, NumPy 2.3.5 and Trimesh 5.1.0 handled
independent readback.

| Check | Result |
|---|---:|
| Simplified surface | 438,652 vertices; 877,304 triangles |
| Simplified OFF SHA-256 | `c8aef379ac3a66188518ecc247fb1970ffe80fa33cea1b49b0b87db098959ac9` |
| Connected components / boundary or nonmanifold edges | 1 / 0 |
| Euler characteristic / genus | 0 / 1 |
| Original thin facets below quality 0.05 retained with identical coordinates and connectivity | 121 / 121 |
| Source-to-candidate and candidate-to-source complete envelope | Pass / pass |
| Envelope bound / reserved numerical margin | 0.0225 / 0.0025 source units |
| Candidate volume / relative difference from corrected rotor | 431,014.075493 source units³ / +0.00011006% |

The [independent continuous-envelope checker](../../../twins/935-horizontal-cooling-system-f0/source/analysis-envelope/tiled_envelope.cpp)
tested all 1,320,006 source triangles and all 877,304 candidate triangles.
Its self-test includes a counterexample in which vertex-only proximity would
incorrectly pass. Closed topology, valid triangle mesh and complete
self-intersection checks passed. The candidate retains the source's 121 very
thin faces; simplification has not claimed to repair those observed facets.
The bound is relative to the corrected *reconstruction*, not the raw scans or
an authenticated manufacturing tolerance.

## Fresh OpenFOAM input

The [case preparation source](../../../twins/935-horizontal-cooling-system-f0/source/corrected-analysis-20261025/prepare_fluid_case.py)
accepts only these exact source and candidate hashes and the passing
bidirectional certificate. It reuses the earlier Foundation 13 pilot's
unchanged system dictionaries, including mesh-quality SHA-256
`bafbc5ced7e83c5a1cc11291a0937c3499a6713e8e3411a83f93464381ba2c7d`,
and replaces the old rotor OBJ with the corrected candidate. The existing
export helper reads back every SI OBJ vertex and face. The new private case is
`work/935-corrected-analysis-20261025/fluid-case-001/`; its rotor OBJ is
`4ea77849439ac1b525d000386d8fa8e564a7f311552117262e4b55e29cb42528`.
One uncalibrated source unit is provisionally mapped to 0.001 m, as in the
earlier pilot; this is **not** a verified physical scale.

The later [0.7-root preparation program](../../../twins/935-horizontal-cooling-system-f0/source/corrected-analysis-20261025/prepare_root0p7_fluid_case.py)
now stages the protected 878,730-face rotor for the same pilot. It pins the
surface, template receipt and all six OpenFOAM system dictionaries; the SI OBJ
export was read back vertex by vertex and face by face. The new rotor OBJ has
SHA-256 `ee9357d46911fc0112342626064f7e731395af9db9a8bc340793cf22effb24a6`.
The private case is `work/935-corrected-analysis-20261025/fluid-case-root-0p7-002/`.
Its [archive](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
has SHA-256 `2a81b298df4f7db89298b2dc7dbe1979eafee2883d3afc34f46b92e483a9fb27`;
all nine members passed extracted hash readback, and the release digest matches.
This is a **meshing input**, not a native OpenFOAM mesh or CFD result. The
distribution shroud is still provisional and the engine air passages are not
specified.

An independent [private domain preflight](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
checked the exported OBJ against the unchanged pilot dictionaries. The rotor
bounding box lies within the 0.36 × 0.36 × 0.40 m block with at least 0.03882 m
axis-aligned clearance. `locationInMesh` is inside that block and 0.12930 m
above the rotor bounding box. The base block contains 24 × 24 × 32 = 18,432
cells. Its receipt SHA-256 is
`267abacd1bf4d17ef620814513ac1bcbdd60331b3006c16346c0b3df228d7d8a`,
matched by the uploaded asset. These bounding checks establish only that the
pilot inputs are spatially consistent; they do not establish connected fluid
cells, layer quality, a 935 shroud or an operational fan curve.

### Native OpenFOAM 13 surface gate for the corrected rotor

The pinned private OBJ was transferred to Kali1 without changing its SHA-256
(`ee9357d46911fc0112342626064f7e731395af9db9a8bc340793cf22effb24a6`).
The previously qualified rootless Bubblewrap image ran Foundation 13 build
`13-18870c24d21c`. Native `surfaceCheck -checkSelfIntersection` read all
878,730 triangles and 439,365 vertices. It found one closed, connected surface
with no illegal triangles, but **63 self-intersection locations** and three
pairs of nearby points. Nine reported locations lie near radius 22 mm and 54
near radii 85–89 mm under the unverified 1 mm/source-unit assumption. The
private plot maps every reported location; these are diagnostic coordinates,
not dimensional measurements of the historical rotor.

`blockMesh` and `checkMesh -allGeometry -allTopology` passed for the separate
18,432-cell *empty base block*. That check does not include the rotor. The
separate exploratory rotor mesh is described below; no CFD solve is credited. The earlier
independent surface certificate and OpenFOAM's native intersection test now
disagree. To exclude an OBJ-index or SI-coordinate transcription difference,
the same exported vertices and triangles were converted directly to OFF and
checked with the pinned CGAL binary (SHA-256
`69caa50a446cfef290a2735be90076aa4ea17907a2507e611704f68fddcd6ede`).
CGAL reports a closed valid mesh and **zero self-intersection pairs**. The
cross-check receipt SHA-256 is
`7b4d87584456d944dedf24fb0ab47d6b6e80c6484f52738ac93904a630da5a2a`;
its [private archive](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
contains the exact SI OFF and CGAL output, SHA-256
`9c6390f395af380ecca07702c6b917c82de1cb3c63df266583c5470593989486`.
This narrows the discrepancy to the controllers' intersection predicates or
tolerances; it does not prove which result is suitable for OpenFOAM meshing.
The discrepancy must be resolved before this OBJ is admitted for fluid meshing.
A closed surface alone is insufficient. The [private native diagnostic archive](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
contains the logs, 63 intersection points, plot and receipt, with archive
SHA-256 `85d5678bffadba633dc1272ef3b0ea249bb0cd5b76c340aab93615fa56444fc2`
and matching GitHub asset digest. The receipt SHA-256 is
`2b63d9ab02bc02caffd2d15ac95644d99fc5f180d9c87a3006e39746acd7e145`.

### Bounded rotor fluid-mesh trial (rejected)

A new private copy of the pinned case ran `snappyHexMesh -overwrite` on Kali1
with surface refinement levels reduced from 5/6 to **2/3**, at most 400,000
cells, and layer addition disabled. The process had an 8 GiB virtual-memory
limit and a 300 s wall-time limit. It completed in 140.78 s and produced one
connected fluid region with 236,898 cells and a closed rotor boundary patch.
Native `checkMesh -allGeometry -allTopology` nevertheless reported **13,772
concave cells and one failed mesh check**. This mesh is rejected for CFD; the
tool's “Finished meshing without any errors” message is not a quality pass.
Coarse refinement and the deliberately provisional conduit also preclude a
physical 935 airflow claim. The [private rejected-trial archive](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
contains the exact modified dictionary, polyMesh, both native logs and a
file-hashed receipt. Its SHA-256 is
`77b23218d57ed91bc7ee7f15fb6a51cf1f41ed655d879a75c17cd2dd45fad9a5`;
the receipt SHA-256 is
`be57e637ae36124ca316da55c2e3d274f8265fc5ce41f39096608fdb1cde4880`.

Three bounded controls then tested whether these concave cells were introduced
only by snapping or removed by a finer cut. All used the **same pinned rotor
OBJ**, disabled layers, an 8 GiB virtual-memory limit and Foundation 13:

| Surface levels | Snap | Final cells | Concave cells | Outcome |
| --- | --- | ---: | ---: | --- |
| 2/3 | on | 236,898 | 13,772 | `checkMesh` failed |
| 2/3 | off | 236,898 | 19,105 | `checkMesh` failed |
| 3/4 | on | — | — | Timed out at 420 s during snap; no final mesh |
| 3/4 | off | 708,822 | 64,800 | `checkMesh` failed |

The 2/3 on/off pair shows that snapping is **not the sole cause**: the
castellated-only mesh already fails. The 3/4 controls also change the
distance-refinement level from 1 to 2, so they do not isolate surface
refinement alone. None of these configurations is CFD-admissible. The
[private release](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
preserves the control receipts and logs, including the 3/4 no-snap polyMesh:

| Private archive | SHA-256 | Receipt SHA-256 |
| --- | --- | --- |
| `root0p7-no-snap-control-004.tar.gz` | `53423ec2fc33152a8ddd207e40ac67001bd5fb6f5cd7397288006e319ee4637e` | `d50b7994d02db94fec69cd29977409c2e8eabe744ceb0cbfba65b8d8e5d58207` |
| `root0p7-refine34-timeout-005.tar.gz` | `f50cd62c4acb843b1fd00be4f817876f29c1846a96e751b393b57d03c2e60b1f` | `57d55c8dec62b06ae97170c0d391a84ee7f95222f5d7995a2cffd9780461be60` |
| `root0p7-refine34-nosnap-rejected-006.tar.gz` | `14fd4c6336adcaa91efae38fd124e77e4221523fe2b155c0e807845de704ba6e` | `b66b326f296a5b588ed31b6fcbb44728a1c024ed11f1af4fac6560dafef59d72` |

### Native OpenFOAM check of the TetGen O5 alternative (rejected)

The existing pinned O5 TetGen output was also imported on Kali1 with
Foundation 13 `tetgenToFoam -noFaceFile`. Its transferred `.node`, `.ele` and
`.face` files matched the local SHA-256 values; `-noFaceFile` deliberately
ignored face markers for this *quality-only* conversion. OpenFOAM reconstructed
3,714,547 tetrahedra, one connected fluid region and a single closed
895,732-face `defaultFaces` boundary. Native
`checkMesh -allGeometry -allTopology` passed the topological and positive-cell-
volume checks but **failed five geometric checks**:

| Check | Count |
| --- | ---: |
| Faces over 70° non-orthogonality | 170,609 |
| Highly skew faces | 1,864 |
| Cells with determinant below 0.001 | 95,978 |
| Faces with interpolation weight below 0.05 | 11,685 |
| Faces with volume ratio below 0.01 | 1,135 |

The minimum positive cell volume was 1.92 × 10⁻¹⁷ m³ under the still
unverified scale. This route has no concave tetrahedra, but its other quality
failures independently reject it for CFD. It also has no separated inlet,
outlet or rotor patches because face markers were not imported. The
[private conversion archive](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
contains the complete OpenFOAM polyMesh, logs and per-file hashes. Its archive
SHA-256 is `4d4b4d0f3629d27c0eb8c1e1bea462af65526f048810b03cfe1a64dbe3674b06`;
the receipt SHA-256 is
`bc3146ef7de9b8bc9c691a6796718a8c764d79e51d58fb13b5743d38240ef70f`.
No solver run or flow curve is credited. The next meshing study must target
the weak rotor-boundary neighborhoods while preserving the certified surface
envelope and the separate mechanical interfaces.

### Exact localization of native mesh failures

`checkMesh -constant -allGeometry -allTopology -writeSets -writeSurfaces`
produced the native problem-cell and problem-face sets. The
[`audit_root0p7_openfoam_sets.py`](../../../twins/935-horizontal-cooling-system-f0/source/corrected-analysis-20261025/audit_root0p7_openfoam_sets.py)
script matches their indices to the unchanged O5 TetGen volume and its marked
boundary triangles. It refuses a different volume hash, inconsistent set
sizes, duplicate indices, or skew boundary faces missing from the TetGen
boundary. Its three focused parser/matching tests pass.

- **78,396 of 95,978** low-determinant cells share at least one complete rotor
  triangle; 17,262 touch no exterior boundary. These categories are not a
  partition because seam cells can touch more than one marked patch.
- **All 1,850 boundary skew faces** match the rotor marker exactly. The other
  14 skew faces are internal. All 170,609 non-orthogonal faces and all 11,685
  low-interpolation-weight faces are internal.
- In the conditional 0.001 m/source-unit coordinate map, the radius
  **0.08–0.10 m** contains 81,424 low-determinant cells and 1,208 skew rotor
  boundary faces. The plot shows the full radial/axial distribution; its axes
  are not calibrated 935 dimensions.

This focuses the next local volume-mesh investigation on the blade-root
neighborhood rather than the exterior block. It does not prove that the scan
itself is defective: the candidate reconstruction, surface triangulation and
volume mesher can each contribute. Any changed surface must repeat the full
bidirectional envelope, topology and self-intersection checks before another
OpenFOAM conversion. The
[private localization archive](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
contains the native sets, VTK outputs, exact boundary-face mapping, plot,
source copy and hash manifest. All 23 data/source members passed extracted
hash readback; its SHA-256 is
`4282502f521fc6b66dbda14ba137557575acdb7aac97e2d0974f17e76f113f0e`,
matching GitHub. The reproducible JSON receipt SHA-256 is
`d0e0b1d7ca8cf811e7084dcfa16672634f883e533f11bb3301a3d0708da7564d`.

```sh
python twins/935-horizontal-cooling-system-f0/source/corrected-analysis-20261025/audit_root0p7_openfoam_sets.py \
  work/935-cfd-root0p7-20261026-o5-audit/volume.npz \
  work/PRIVATE-LOCALIZATION/constant/polyMesh/sets \
  work/PRIVATE-LOCALIZATION/skew-boundary-faces.json \
  work/PRIVATE-LOCALIZATION/log.checkMesh.localization \
  work/NEW/native-failure-localization.json
```

A second pinned, private cross-check mapped all 1,850 skew rotor boundary
faces back to the analysis surface triangles. Their median equilateral
quality is 0.795; only 54 fall below 0.1 and 134 below 0.2. Just two skew
faces lie within 5 mm of the 63 `surfaceCheck` self-intersection points,
with a median nearest distance of 29.2 mm under the provisional 0.001 m/source
unit scale. Triangle quality and the checker points therefore do not, on
their own, explain most native skew-face failures. These are screening
statistics, not a proof of mesher causality. Inspect near-wall volume fill and
clearances before modifying measured geometry. The private cross-check
archive `root0p7-cross-modal-screen-009.tar.gz` has SHA-256
`68415bf565651ab14f000f8ecfe8c6d05b8f898a537fa83e4966db1e9f1f042d`;
its receipt has SHA-256
`136e575e4378d489e55f2aa56682b284966092a0cbbd4ee6fd10033104c19fa7`.

### Adjacent-cell dimensions explain the native skew screen

An exact boundary-face-to-tetrahedron lookup matched each of the 1,850
skew rotor faces to its unique adjacent O5 cell. A seeded sample of 1,850
other rotor faces provides a non-skew control. Median wall triangle areas
are similar: 1.35 × 10⁻⁷ and 1.28 × 10⁻⁷ m², respectively. Yet the skew
group's adjacent-cell height is **6.38 mm** versus **0.583 mm** in the
control, and its cell-center projection is **2.85 mm** off the wall-face
center versus **0.093 mm**. Dimensionless height divided by square root of
wall area is **16.67** versus **1.70**. These ratios isolate a steep,
lateral near-wall volume transition in the rejected TetGen mesh. They do
not prove which meshing setting caused it or establish an actual 935
dimension; the length unit remains conditional on the unverified scale.

The private `root0p7-wall-cell-screen-010.tar.gz` contains the hash-pinned
source, receipt and manifest. A second local run reproduced the receipt byte
for byte. Extracted hashes and the GitHub asset digest match archive SHA-256
`d8ea9456410c7617cb90f33bbb563aba8a2bceae1f17114fcb7ff8b76374cf70`;
the receipt SHA-256 is
`bddb64c1f54ad6fbcfee7810c4dbdc7396b16cf575d2653410ade082530ab4b2`.
The next mesh trial should control near-wall cell size and growth around the
rotor while retaining the protected surface envelope, then repeat native `checkMesh`
and all boundary/interface audits. No CFD run is admitted yet.

### Cell-specific volume refinement: rejected

TetGen 1.5.1's [documented `-r`/`-q`/`-a` route](https://www.wias-berlin.de/software/tetgen/1.5/doc/manual/manual005.html) was tested on the same O5
volume. A `.vol` file constrained the 1,850 cells uniquely adjacent to the
native skew rotor faces to one eighth of each cell's original volume and
left the other 3,712,697 cells unconstrained. The bounded command
`tetgen -rYq1.4/10aS50000Q fluid.1` completed in 50.7 s, used its full
50,000-point allowance and generated 4,023,860 tetrahedra.

All 817,235 input vertex coordinates were retained. Boundary face counts
and markers were unchanged, but 22,647 of 878,730 rotor face vertex triples
changed connectivity; `-Y` did not freeze every triangle in this refinement.
The new rotor surface has zero non-manifold or inconsistently wound edges.
The independent full bidirectional 0.0225-source-unit envelope, topology and
self-intersection certificate passed. This is a conditional reconstruction
envelope, not measured accuracy.

The tetrahedral median mean ratio improved to 0.7373 and the count below
0.01 fell from 2,929 to 1,727. However, one cell has a zero determinant
in double precision; exact arithmetic on its printed node coordinates gives
a *positive* six-volume of only 6.49 × 10⁻²⁷ m³ under the provisional scale.
This extreme sliver rejects the volume for CFD despite the median gain.
Kali1 did not respond over Thunderbolt or its previously observed LAN
address, so no native OpenFOAM `checkMesh` pass is claimed. The preserved
[private trial archive](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
contains the `.vol` input, complete output mesh, candidate OFF, logs and
receipts. All 15 extracted members passed hash readback; its SHA-256
`0dd9254131c30f455b38cc52cac5a7a4f182fd14433b47d1640a2373dae53bca`
matches GitHub. The disposition receipt SHA-256 is
`f90c1da6570ff8d86767a4b33dd872fa6155f7224717675c6a2c5de84de83f2c`.

### Native OpenFOAM conversion and precision check: rejected

The targeted 4,023,860-tetrahedron volume was converted with Foundation 13
`tetgenToFoam` in the pinned mesh-CFD image on the Mac. The first case omitted
`writePrecision`; its ASCII `polyMesh/points` rounded source coordinates by as
much as 5 × 10⁻⁷ m in the provisional SI frame and collapsed 27 of the
867,235 distinct TetGen vertices. A bounded `checkMesh -allGeometry
-allTopology -meshQuality` run reached geometry checks but was stopped after
15 minutes. It had already reported 130 zero/negative-volume cells, so this
case was rejected. These counts are not a completed quality verdict.

The case was rebuilt with `writePrecision 17` in `system/controlDict`. A
point-by-point audit found zero changed coordinates and zero collapsed
vertices. The complete native `checkMesh` still ended with **9 failed mesh
checks**: 7 zero/negative-volume cells, 1,211 highly skew faces, 760 low-quality
or negative face-decomposition tets, and 83,745 cells with determinant below
0.001. It wrote 189,881 unique faces to `meshQualityFaces`. Of those, 180,083
are internal and 9,798 are boundary faces. In the conditional rotor envelope
`r < 0.145 m, |z| < 0.04 m`, 189,539 error faces lie near the rotor; 165,359
lie in the `0.05 <= r < 0.10 m` radial band. This localization guides the next
surface-aware remesh but does not establish a measured rotor dimension.

The [reduced receipt](native-openfoam-precision-20261027.json) pins the input,
container, logs and counts. The private
[read-back-verified bundle](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-openfoam-precision17-20261027.tar.gz)
contains both logs, the exact case dictionaries, coordinate audits, the
quality-face set and the localization script/report. Its SHA-256 is
`a7d3fdf78315c9c4a50c0c7709fcf7171c227a09d8b1ec2764a39a272fcf5958`,
matching the private GitHub asset digest. The large scan-derived `polyMesh`
remains local. **No CFD solve is admitted** from either conversion. The next
mesh trial must control rotor-wall size and growth, preserve the boundary
contract, use 17-digit output and pass the full native quality gate.

### Rotor-boundary attribution: original facets still dominate

Under the provisional SI mapping, an exact coordinate bijection maps all
439,365 vertices of the converted rotor patch to the protected analysis
surface. TetGen reconnected 22,647 of its
878,730 triangles without moving these vertices. All 9,798 OpenFOAM error
faces on the boundary belong to the rotor patch: 9,401 retain an original
triangle, and 397 belong to the reconnected set. The latter set has a somewhat
higher error-face rate, but it accounts for only 4.1% of the rotor boundary
errors. TetGen's reconnection alone therefore cannot explain the defect ring.

The protected surface already has 24 triangles with mean-ratio-like triangle
quality below 0.01 and 16,574 below 0.1. The converted rotor patch has 27
and 15,750, respectively. Among its 9,798 error faces, 4,934 have triangle
quality below 0.1; their median is 0.099 versus 0.813 for all rotor faces.
The other error faces and the 180,083 internal error faces require volume-cell
analysis as well. These observations implicate the preserved local facets and
near-wall tetrahedral growth together; they do not uniquely assign a cause to
each failed cell. A read-only edge-flip screen was not applied because it
operated on the derived TetGen patch and has no complete surface-envelope
certificate.

The [reduced attribution receipt](native-openfoam-boundary-20261027.json) and
the [private read-back-verified analysis bundle](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-boundary-attribution-20261027.tar.gz)
pin the exact comparison. The bundle's SHA-256
`f023a7e83e3daacdba29ee2c000a492423e3708a6e3c960b1dc6eb2718446620`
matches GitHub. The next candidate must repair the local surface within the
complete bidirectional envelope and control near-wall volume growth, then
repeat topology, exact-volume and native OpenFOAM quality checks. No candidate
from this attribution step is admitted.

### Protected-surface edge-flip trial: valid surface, rejected volume

A separate exploratory trial operated on the protected analysis surface, not
the TetGen-reconnected boundary. Twelve disjoint edge flips kept every vertex
fixed and reduced the count of triangles below quality 0.01 from 24 to 22.
The independent CGAL checker passed closed topology, validity, zero
self-intersections and complete bidirectional containment within the
0.0225-source-unit envelope. The surface volume changed by
−6.78 × 10⁻⁹%. These are geometry checks against the reconstruction, not
evidence of measured 935 fit.

Gmsh 4.15.2 then generated 1,463,583 raw and 1,392,150 optimized
tetrahedra with the same settings used for the protected reference. Both
volumes had zero nonpositive six-volumes in the numerical audit. The optimized
boundary has an exact vertex and triangle multiset match to the trial
surface. Its count below tetrahedral mean ratio 0.01 was **3,226**, compared
with **3,255** in the reference optimization: a gain of only 29 cells, with
3,226 still weak. The candidate is therefore **not admitted for FEA**; this
rotor-solid volume does not provide a fluid-domain CFD mesh.
This trial shows that flipping only the most degenerate surface triangles is
insufficient; the annular surface and near-wall growth still need a broader,
envelope-certified treatment.

The [reduced trial receipt](edge-flip-trial-20261027.json) links the private
[source, meshes and complete audit bundle](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-source-flip-volume-20261027.tar.zst).
All 19 payload members passed extracted hash readback, and the bundle SHA-256
`eaf0a57c203945e5b59950fdc09968ea55945f1fd28f3b80e1c850a0812b4225`
matches the private GitHub asset digest. No operating-point, stress or
manufacturing result is inferred.

### Direct volume on the native PicoGK surface: improved, not admitted

The unsimplified PicoGK 0.7-source-unit rotor was compared with the protected
analysis surface using the same triangle-quality metric. In the annular
`85 <= r < 90` source-unit band, the native surface has 31 of 198,095
triangles below 0.1, versus 6,927 of 144,833 on the analysis surface. This
large difference shows that the simplification stage materially changes the
local facet shape; it does not by itself prove why each OpenFOAM cell failed.
The native 0.7 surface is still a reconstruction hypothesis with unverified
physical scale and fit.

Using the same Gmsh 4.15.2 Frontal settings as the preceding rotor-solid
control, a direct native-surface trial generated 2,202,340 raw and 2,159,530
optimized tetrahedra. The numerical shape audit found zero nonpositive
six-volumes in either volume. Every optimized boundary vertex and triangle
matches the native PicoGK input exactly. The optimized volume has 1,235
tetrahedra below mean ratio 0.01, versus 3,255 of 1,393,021 on the simplified
reference: 0.057% versus 0.234%. Its minimum mean ratio is still 0.000470,
so this remains an **exploratory solid volume, not an admitted FEA mesh**.
It is not a CFD fluid mesh, and no solver or convergence result is claimed.

The [reduced native-volume receipt](native-picogk-volume-20261027.json) and
the private [19-file source and volume bundle](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-native-picogk-volume-20261027.tar.zst)
retain the native PicoGK surface, raw and optimized volumes, scripts and
audits. All payload hashes passed extraction readback; bundle SHA-256
`7f4810c734b380811aa99b0a104eb95a4fc8126238b093d9de0e63f5f5ea6193`
matches the private GitHub asset. The fluid-domain trial below uses this native
PicoGK boundary and repeats the independent boundary and native OpenFOAM
quality gates before any pressure or flow solve.

### Native PicoGK boundary in the provisional fluid domain

The unsimplified 0.7-source-unit PicoGK rotor was inserted into the same
provisional outer duct used for the simplified-surface fluid trial. This duct is
an analysis enclosure, **not a measured 935 shroud**. Its assumed conversion
of 0.001 m per source unit is still uncalibrated. The closed PLC contains
668,240 vertices and 1,336,476 triangles, including 1,319,474 rotor faces.
The signed fluid volume is 0.05140884081894108 m³ under that conditional
scale.

TetGen 1.5.1 with `-pYq1.4O5MzCf` generated 5,698,705 tetrahedra and
preserved all four boundary markers. An independent complete audit found one
connected tetrahedral component, an exact coordinate/triangle/marker bijection
to the PLC, no repeated-node or non-manifold tetrahedra, and no zero or
negative exact cell volumes. Its exact total equals the PLC signed volume.
The full-cell mean-ratio screen found 18 cells below 0.01, all touching the
rotor, versus 2,929 in the earlier simplified-boundary `O5` trial. The new
minimum mean ratio is still only 0.0000425. Different boundary facet counts
and resulting cell counts prevent interpreting this comparison as a converged
CFD study.

OpenFOAM Foundation 13 imported the 5,698,705-cell mesh with four patches.
With `writePrecision 17`, all 1,237,026 imported point coordinates match the
TetGen nodes exactly. The full native `checkMesh -constant -allGeometry
-allTopology -writeSets -writeSurfaces` completed but **failed five mesh
checks**: 4 high-aspect-ratio cells, 3 highly skew faces, 7,516 low-determinant
cells, 815 low-interpolation-weight faces and 130 low-volume-ratio faces.
It also reported 8 short edges. Cell volumes, face pyramids, face tets,
concavity and one connected region passed. This improves on the earlier
simplified-boundary case's nine failed checks and 189,881 error faces, but
does **not** admit a CFD solve. The minimum cell determinant is zero under
OpenFOAM's quality definition. The 6,518 cells with two internal faces merit
inspection before boundary-layer meshing. Neither airflow nor fitment is
claimed from these checks alone.
The [reduced trial receipt](native-picogk-fluid-20261027.json) references the
private [PLC, TetGen output and audit bundle](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-native-fluid-tetgen-20261027.tar.zst).
All 14 payload files passed extracted SHA-256 readback. The bundle SHA-256
`313cd6e2c7d776a0fc52442661ac66616d96ac75a6db44a7c4177d1ed21698a3`
matches the private GitHub asset digest. No scan-derived mesh is committed to
the public repository. The private
[OpenFOAM mesh and complete `checkMesh` case](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-native-fluid-openfoam-20261027.tar.zst)
contains the four patches, quality sets, diagnostic surfaces, logs and
`writePrecision 17` settings. Its 26 files passed extracted hash readback;
archive SHA-256 is
`0cb81f5644482085768a1a82a207147f0d7ec11798aaffad0145c7d6302d0658`.

The [reduced machine-readable receipt](corrected-analysis-20261025.json)
identifies the source, candidate, case and private checkpoint. The private
[release](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
holds the OFFs, source copy, compiled controls, geometry receipts and case
without publishing scan-derived geometry in this repository. Its 20 archived
files were read back and hash-checked locally.

### Re-optimizing the targeted volume: bounded trial

The 4,023,860-cell targeted result above was also supplied to the same
TetGen 1.5.1 executable with `-rYq1.4/10O5Q fluid.2`. The three input
files were hard-linked into a new private trial directory; their SHA-256
digests matched the archived targeted output before and after the run.
The process used one CPU core, was observed at about 7.2 GB resident memory,
and was stopped at the pre-set 240-second limit. It produced no `fluid.3`
mesh or diagnostic text. Thus there is **no optimized candidate to audit**;
the earlier extreme sliver and CFD rejection stand. This timeout is a
resource-bound observation, not evidence that TetGen cannot improve the mesh.
The [trial receipt](targeted-volume-optimization-20261027.json) records the
input and executable hashes, command, limit and absent output.
The next mesh trial should address the rotor-wall transition and certify its
surface and volume before a native OpenFOAM check.

## Volume-mesh trials on the corrected surface

The private candidate OFF was also passed to Gmsh 4.15.2 on the Mac with its
877,304 triangles preserved as a discrete boundary. The Frontal algorithm
generated 1,462,151 raw and 1,387,601 optimized tetrahedra. Independent
readback found an exact coordinate-and-triangle bijection with the input
boundary, one connected tetrahedral region, no negative-volume cells and no
nonmanifold faces in either volume. **Both volumes contain 12 tetrahedra with
exactly zero volume, so both are refused for FEA.** All four vertices of each
zero-volume tetrahedron lie on the boundary, in two localized patches around
radial positions 84.87–88.87 uncalibrated source units. Altering those nodes
would change the certified surface and requires a new geometry assessment.

HXT generated a volume but volume elements referenced node tag 438653, absent
from both the exported node table and Gmsh's individual `getNode` lookup. Its
volume is refused. The Delaunay trial exceeded its 300-second controller limit
before writing a volume. No trial produced an admitted mechanical mesh.

The six attempts, independent audits, controller logs and a diagnostic plot
(`gmsh-trial-001/zero-cells-map-002.png`) are in the same private release as
`gmsh-volume-001.tar.gz`: SHA-256
`207986ede430ee98dc5db5f37c6615f186ac4c5f674d493ac0c79648ccf78be7`.
All 44 archive members were read back and hash-checked; GitHub's asset digest
matches the local archive. These trials are numerical evidence about this
particular analysis surface and mesher settings, not a strength calculation.

## Second hypothesis and inspection assembly

### Second root-closing hypothesis: 0.7 source unit

A fresh PicoGK reconstruction changed only the root-closing radius from 0.6
to 0.7 uncalibrated source unit. This parameter is a repair hypothesis, not a
measured historical dimension. Its private STL SHA-256 is
`5522ec1af957a4523244bc2b2f05ff902b52eb882e1cb3b2ef88b093ffb598eb`.
The surface audit found one closed genus-one component, with the original
outer and bore triangles preserved. The protected CGAL analysis surface has
878,730 triangles and SHA-256
`5d900f6da900b4bffac2fdacfd6e0a346f8c0259a19299725621d4fd1e48c12a`.
Complete bidirectional surface-envelope checks passed at a 0.0225-source-unit
bound relative to this reconstruction. The 0.7 native and analysis volumes
differ by +0.00015718%.

Gmsh 4.15.2 Frontal produced 1,464,371 raw and 1,393,021 optimized
tetrahedra. Independent exact-arithmetic readback found **zero zero-volume or
negative-volume tetrahedra** in both, an identical boundary, one connected
volume, and the expected analysis-surface volume. This clears the basic
geometric volume screen that the 0.6 candidate failed. It does **not** clear
mechanical mesh quality: the optimized mean-ratio minimum is
`1.77149e-05`, with 3,255 tetrahedra below 0.01. Netgen optimization did
not produce an output within 300 seconds; three TetGen attempts failed during
internal facet repair. No FEA result is accepted.

The private machine-readable numerical receipt has SHA-256
`c70dcfcd721f019c4e159dc378f6392d1376e135598de08a3946282ed2536859`.
The private `root-radius-0p7-001.tar.gz` has SHA-256
`ea2a611dd512d9e6ef50b0dc1539e0d93bc1f6509c568daa7eef3cf22cf11a0a`;
all 42 members and the GitHub asset digest were checked.

### PicoGK inspection assembly with the 0.7 rotor

The existing PicoGK assembly program was rebuilt without changing its source.
It placed this rotor with the observed 935 drive/support scan, a **provisional**
shroud, and a **917 engine scan used solely as comparative context**. The four
components contain 7,262,969 triangles. Independent export readback preserved
their transforms and triangle identities in GLB and SI-unit USD. At the
assumed, unverified scale, the rotor/shroud radial separation is 6.258 mm;
the conservative swept-annulus screens found zero candidate drive triangles.
These are surface screens at a hypothetical pose, not confirmed interfaces,
occupied-body interference checks, thermal clearances or a 935 engine fit.
The inspection render still shows incomplete blade sectors.

The native assembly, GLB, USD, four-view PNG and receipts are saved in the
same private release as `assembly-root-0p7-001.tar.zst`, SHA-256
`fb9b033ec360790395a92c2e3044e98e6728a5012b4a100965371b48ebe31c0d`.
Its 19 source members and GitHub asset digest were checked. The six
non-finite STL normals in the 917 context scan were zeroed in a display-only
copy; all triangle coordinates and the PicoGK source files were unchanged.

### Active six-cylinder 935 packaging study

The separate, already documented [935-only assembly](COMPLETE_SYSTEM_20261022.md)
was also refreshed with the 0.7 rotor. It combines the observed 935
drive/support, this corrected rotor, a provisional distribution shroud and a
**hypothetical two-bank, six-cylinder engine envelope**. No 917 geometry is
used in this active study; an actual 935 crankcase scan is still absent. The
PicoGK output has 12,599,570 triangles. Independent review found exact
coordinate and triangle-order preservation in the combined mesh and in the
SI-unit USD/GLB exports. Its four-view inspection image shows the assembly
and the remaining incomplete blade sectors.

The provisional rotor/shroud radial separation is 6.258 mm at the assumed
scale. The swept rotor-annulus screen found zero candidate support triangles,
but the support/shroud screen found **1,190,558 candidate triangles**. That
conservative count does not prove a collision; it motivated the full surface
contact study below. The duct cutout and support interface still need measured
mounting datums.
The engine envelope does not supply historical mounting datums, thermal
clearances or airflow resistance.

The complete active-scene evidence is saved privately as
`assembly-935-six-root-0p7-001.tar.zst`, SHA-256
`2ff700d4d4fc359cfd450a4d9bc25ae06b80c8d402cffb59713937ee065e1f16`.
Its 17 source files were extracted and individually hash-checked; the GitHub
asset digest matches. It includes
the native PicoGK scene, USD, GLB, PNG and receipts; no geometry is committed
to the public repository.

### Retained-pose contacts and one rigid revolution

The existing [FCL surface reviewer](../../../twins/935-horizontal-cooling-system-f0/source/review_surface_contacts.py)
was rerun against the 0.7 six-cylinder scene. It tested all six original
surface pairs without decimation. The conservative support/shroud candidate
count above is **not a collision**: the FCL surface distance is 6.83367
uncalibrated source units. The support/rotor distance is 3.83430 and the
rotor/shroud distance is 6.25830 at the retained pose. The observed support
does cross the **hypothetical** engine envelope near source coordinates
`(95, -8, -210)`; this same crossing existed in the earlier scene. It cannot
be interpreted as a clash with an actual 935 crankcase.

The new [rigid-sweep reviewer](../../../twins/935-horizontal-cooling-system-f0/source/review_rotor_sweep.py)
checks 240 equally spaced rotor phases about the assumed Z axis. The maximum
rotor radius is 143.74075 source units, so any intermediate point moves at
most `2R sin(pi/(2×240)) = 1.88155` units from its nearest sampled phase.
Subtracting that motion and a 0.0001-unit numerical reserve from the lowest
sampled FCL distance gives conservative lower bounds of **1.95136 source
units** to the support and **4.37637 source units** to the provisional shroud
through a rigid revolution. Analytic static and moving FCL controls passed;
the independent exploratory and final runs had identical phase results.

These bounds concern **surface separation under an assumed axis, fixed pose
and rigid, cold geometry**. They establish neither the missing torque-carrying
hub/shaft connection nor solid containment, thermal growth, elastic motion,
historical engine fit, operational speed or physical safety. Full reports,
logs and source hashes are in the private release as
`contact-and-sweep-0p7-002.tar.gz`, SHA-256
`1d05c5940698bb1806cd5b4114ba43ee7b668de67ab37954ee522f43227e033a`;
its 11 files and GitHub asset digest were checked. The earlier archive is
retained as an exploratory attempt. The private `rotor-sweep-0p7.png` plot has
SHA-256 `dadc6a2f38a043c0f30cf45a33704ea700f8a3d2a7861dc4826d4b270ade4447`.

### Output hub interface: geometric gap, unresolved coupling

An FCL nearest-point query puts the 3.83430-source-unit rotor/drive gap at
the reconstructed rotor bore, not at a blade. The nearest bore and observed
drive points lie at the same Z level, `-4.50417` source units, with radial
positions 11.45477 and 7.62052 respectively. Four separate five-unit
axial bands of the observed output patch give partial-arc circle-fit radii
6.93574–7.07082 source units. Their radial RMS residuals are 0.09877–0.13443,
and each band leaves a 176.8–183.9-degree angular gap in the acquisition.
An earlier bounded fit to the **original rotor scan** (SHA-256
`244d4caeb2c4ac4a692b650ec9d766bee2a8124335a0236a55a1d30c1b2b98ba`)
gave its observed hub patch a cylinder radius of 11.46191 source units,
0.19103-source-unit RMS on held-out sectors of the same scan, and a maximum
unobserved angular gap of 17.65°. The reconstructed bore is a full ring of
fitted radius 11.45601 source units. Its small fit residual describes the
**generated model**, not scanner accuracy; agreement with the original-scan
fit is not independent dimensional calibration or a tolerance claim.

The separate acquired 22-lobe shaft patch previously reported in the drive
study maps roughly 357 source units from the rotor axis and points 55.35°
away from the assumed rotor Z axis. It therefore cannot define the output
hub coupling. A spacer or keyed adapter may be required, but these partial
surfaces do not specify its fit, torque path, axial retention or historical
form. No functional adapter has been designed or released.

The private [release](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
contains the script, nearest-point receipt, four-band fits, plot and prior
input-side profile as `hub-output-metrology-001.tar.gz`, SHA-256
`741e4af6c3666b0ccb7d9e50c60a3ef8b20dee0f2f78596053d229da55778e58`.
All eight archive members and the GitHub asset digest were checked.
The earlier original-scan hub fit and plot are also archived privately as
`rotor-original-hub-fit-002.tar.gz`, SHA-256
`dec7c80b3acf07c51e9d70e925d5a025d129290fcee40ddbaff15f2cc97a5b41`;
the source OBJ hash, both archive members and GitHub asset digest were verified.

A follow-up axial coverage audit of the same hash-pinned assembly STL samples
sidewall face centroids in five-unit Z bands. The observed drive patch has
enough faces for partial-circle fits from Z = −40 to 0; the reconstructed
rotor bore is sampled from Z = −25 to +10. In their five shared bands,
Z = −25 to 0, the fitted drive radius rises from 6.80 to 7.07 while the
reconstructed bore is approximately 11.46 source units. The difference in
these **partial fitted radii** is 4.39–4.66 uncalibrated source units. The
drive's acquisition leaves about 177–189° unsampled in each shared band.
Face-centroid coverage cannot establish a continuous shaft, an actual radial
clearance or an adapter's mating geometry. The private
[axial-coverage archive](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/hub-output-axial-coverage-002.tar.gz)
contains the reproducible script, receipt and plot, not the scan meshes.
Its five members passed extraction hash readback; SHA-256
`29059f4c2d9b733eb6cdfccb74c0ba2af5b4366bb7183fe1cdc37b9a72df0176`
matches the GitHub asset digest. A measured mating datum and torque-transfer
feature remain prerequisites for a functional hub connection.

An angular audit of those five shared Z bands finds 36–37 occupied five-degree
bins per band, leaving approximately half of each circumference unobserved.
For all 6,879 selected sidewall face centroids, the STL normal points radially
outward and agrees with the triangle winding. The visible patch is therefore
**oriented like an exterior shaft wall**, rather than an inward-facing bore
wall, in this mesh. The largest absolute five-degree-bin median residual from
the respective partial-circle fit is 0.43 source unit. No key, spline or
retention feature is identified by this screen; their absence cannot be
inferred from the missing half-circumference or this angular resolution.
The private [angular-profile archive](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/hub-output-angular-profile-003.tar.gz)
contains the script, receipt, plot and its dependency, with no scan meshes.
All six archive members passed extraction hash readback; its SHA-256
`a5712841d75e989632cd8f91f35366f3e715bb57e4b7faf3c7a34bd2182a9b68`
matches the GitHub asset digest.

The fitted axis of the original rotor hub patch differs by **0.75106°** from
the reconstruction frame's Z axis. A follow-up geometric bound uses
the maximum rotor vertex distance from the assembly origin (146.46243 source
units): a rigid pose tilt of that angle can move any rotor point by at most
1.91989 source units. Subtracting this from the previously certified full-turn
surface bounds leaves **0.03147** source units to the observed drive and
2.45648 to the provisional shroud. The drive bound reaches zero at a tilt of
0.76337°, only 0.01231° beyond the fitted angle. This narrow positive bound
applies solely to a rigid tilt about the assumed origin with fixed cold
surfaces. The scan fit is not an independently verified bearing or shaft axis;
translation, metrology error, running deflection and thermal growth are absent.
It is **not an operating clearance or manufacturing tolerance**. The pinned
calculation and its self-check are in the private release as
`axis-pose-sensitivity-001.tar.gz`, SHA-256
`e79aa64e02f8f040d629cd1400a390a622736019cf5fc7c02712e61a4482543c`;
both members and the GitHub asset digest were checked.

A direct 240-phase FCL sweep at that one scan-derived tilt orientation found
no sampled surface crossings. Its continuous rigid-sweep lower bounds were
**1.96219** source units to the observed drive and **4.02328** to the
provisional shroud. This sharper result does not cover other tilt azimuths,
axis translations or dynamic deflection; the conservative all-direction
pose bound above remains the applicable bound for an arbitrary tilt of up to
0.75106° about the assumed origin. The private `tilted-sweep-001.tar.gz`,
SHA-256 `9bbb5e0aa375c4babae3f12d2c6991761f3f3e0529cf0897d605b2719cf3a83e`,
contains the script, all phases and log. Its three members and GitHub asset
digest were checked.

### Blade-tip coverage: the nine blades are present, the tips are not measured equally

The original rotor scan has nine segmented blade regions. Their phase pitches
range from 39.040° to 40.879° around a 40° mean. Original triangle-face
centroids beyond radius 139 source units occur only in `blade-05` (374 faces);
its maximum is 143.595. The other eight regions have acquired maxima of
135.519–137.313 and none beyond 139 under the stated sector and axial filter.
The PicoGK loft input already marks **every** section at radius 140 as
`constant_profile_root_or_tip_design`; the last `registered_acquired_reference_section`
varies by blade from radius 122 to 136. Even `blade-05` is registered only
through radius 126 because its outer observations were not accepted as a
reference profile. The exceptional outer patch therefore cannot establish a
common historical tip radius or justify copying one tip onto all nine blades.
These are source-coordinate coverage observations, not calibrated dimensions.
The private [release](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
contains `blade-tip-coverage-002.tar.gz`, SHA-256
`704b4b209b0d71fe1873efaad564bdb9cb64b47f81e3d2a3bd455983fe14eb6f`,
with the script, numerical receipt, plot and both pinned derived section
inputs. All five members and the GitHub asset digest were checked.

### PicoGK tip-radius sensitivity: an explicitly shorter design hypothesis

The existing nine-blade loft was rebuilt on Apple Silicon with PicoGK Core
26.2.0 at the same nominal 0.8-source-unit voxel size. The radius-140 control
reproduced the earlier blade-loft STL **byte for byte** (SHA-256
`5e9183026be266e03944a4fb4db47f06c99fabd1af73898b8edc414688e7e114`).
A second input removed only the radius-138 and radius-140 design sections;
every registered acquired reference section was retained. The shorter input
ends at radius 136. This is a controlled **design sensitivity**, not a claim
that the historical 935 blade ends there.

PicoGK blade-loft volume changed from 203,280.62 to 193,813.80 nominal cubic
source units (−4.657%). With the same hub and rotor construction, the full
rotor's independent, welded, watertight STL volume changed from 433,422.66 to
421,987.97 nominal cubic source units (−2.638%). Its polar second moment at
unit density changed from 3.63510×10⁹ to 3.41670×10⁹ nominal fifth-power
units (−6.008%). These ratios describe geometry at the same assumed scale;
they do not establish a material mass, strength, safe speed or airflow gain.
The independent STL volumes agree with the corresponding PicoGK volume
receipts within 0.11%. The three nonrotor full-assembly component STLs
(provisional engine context, observed drive and provisional shroud) have
identical hashes in both cases.

At the unchanged provisional pose, a 240-phase FCL surface sweep found zero
sampled crossings for either rotor. The shortest sampled separation from the
observed drive was 3.82486 source units in both cases. Separation from the
provisional shroud increased from 6.25805 to 13.99869 source units; the
respective rigid continuous-sweep lower bounds increased from 4.37640 to
12.21837. These are conditional *surface* distances in uncalibrated source
coordinates. They do not include the missing output coupling, a verified 935
engine interface, running deflection or thermal growth.

The 21 derived inputs, code, receipts, comparison plot and sweep reports are
archived in the private [release](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
as `tip-variant-r136-package-001.tar.gz`, SHA-256
`d3ad0d1b097564dce58dee658e67b3b7344fcc1edf6b85e1eecd1d440c72f5dd`.
Every archive member, its manifest and the GitHub asset digest were checked.

### Mechanical volume-mesh diagnosis and rejected surface-remesh trials

The protected 0.7-root surface produces 1,393,021 optimized Gmsh tetrahedra.
Of the 3,255 cells below mean ratio 0.01, **3,040 have all four vertices on
the boundary** and another 189 have three. The defects concentrate along the
blade/root annulus and outer blade regions. This locates the quality problem
at the triangulated surface rather than in a broad interior-volume pocket.

Gmsh 4.15.2's standard STL classification and reparametrization trial failed
after creating 253 discrete surfaces: `Wrong topology of boundary mesh for
parametrization`. A separate CGAL 6.2.1 isotropic remesh of the closed analysis
surface produced a 520,378-face unconstrained surface at target edge length
1.0 source unit. A second trial retained edges classified as sharp at 40°
and targeted 0.7 source unit, producing 1,035,442 faces. Both remained closed,
genus one and free of self-intersections under the independent checker.

On the unconstrained 1.0 trial, the optimized Gmsh mesh had 779,177 positive
tetrahedra, median mean ratio 0.23707 and 16 cells below 0.01. On the
feature-constrained 0.7 trial it had 1,555,572 positive tetrahedra, median
mean ratio 0.15388 and 46 cells below 0.01. The original median was 0.11501.
The feature-constrained surface changed enclosed volume by −0.01513% relative
to the protected surface. Yet the **complete bidirectional 0.0225-source-unit
surface-envelope test failed**. A fixed 20,000-point sample in each direction
found a maximum distance of 0.12268 source unit from protected surface to
candidate and 0.09130 in reverse. Those sample maxima are lower evidence
about the true global maxima, not guaranteed bounds. Neither remesh qualifies
as the reference geometry or an FEA input.

These results motivated the local, constrained trial below. Merely accepting
the better tetrahedral statistics would conceal a changed rotor shape. The private
[release](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
contains `remesh-quality-private-package-001.tar.gz`, SHA-256
`a041687336295c93b7befff10ffa90f704fdc375f93d009017a7ebc5e40177c4`,
with code, surfaces, volume meshes, failed and accepted trial receipts, exact
envelope result, machine-readable comparison and defect map. All 24 archive
members were read back against its manifest; GitHub reports the same asset
SHA-256.

### Targeted facet repair also rejected

Selecting faces within 1.5 source units of the 3,255 low-quality tetrahedron
centroids isolates **33,017 of 878,730** input faces (3.757%). CGAL then
remeshed only that patch with its boundary edges preserved, a 0.5-source-unit
edge target and sharp edges constrained at 40°. The output remained one closed
genus-one surface without self-intersections. Its enclosed volume changed by
only −0.000156%, but the **complete 0.0225-source-unit envelope still failed**.
In a fixed 20,000-point sample per direction, the largest surface distances
were 0.02755 and 0.04785 source unit; the sample is not a global bound.
In the companion unconstrained local 0.5 trial, projecting its 51,133 changed
vertices back onto the original surface moved them by at most 7.1×10⁻¹³
source unit. For that trial, the deviation comes from new triangle
connectivity across curved detail rather than off-surface vertices.

The new raw Gmsh volume had 1,603,495 tetrahedra, including **27 exactly
zero-volume and 8 inverted cells**; 12,514 had mean ratio below 0.01.
Optimization reported worst quality zero and had effectively plateaued after
184 seconds, so it was terminated. No optimized volume or FEA result is
accepted. The private archive `local-remesh-rejected-package-001.tar.zst`,
SHA-256 `582ac4629d2fef81628de46311dc0e5aad6af8821b5ab83f4b8277310ac36a53`,
contains the three local surface attempts, patch selector, source, raw volume,
exact-envelope result and defect map. All 21 archive members passed local
readback; GitHub reports the same asset SHA-256.

The next repair must preserve feature-aligned triangle connectivity as well
as the complete bidirectional surface envelope. It must then produce a
non-inverted volume with an independently audited quality distribution before
any load or modal calculation is accepted.

### CGAL Mesh_3 surface-domain trial

A separate local Apple Silicon trial used CGAL 6.2.1 Mesh_3 to discretize the
protected 878,730-face surface. The first run, using the default non-manifold
topology setting, produced 618,973 faces but one open and two non-manifold
edges; it was rejected before geometric comparison. The revised runs detected
sharp features at 60°, constrained feature edges, requested manifold topology
and generated only the domain surface. CGAL's OFF exporter emitted unoriented
faces, so an explicit adjacency traversal oriented them without moving any
vertex. Both revised surfaces then passed the independent topology and
self-intersection checks as one closed genus-one component:

| Facet size / distance, source units | Faces | Complete bidirectional 0.0225-unit envelope |
| --- | ---: | --- |
| 1.0 / 0.0225 | 610,362 | Rejected |
| 0.5 / 0.01 | 1,969,326 | Rejected |

Both envelope checks rejected the same source face, index 10846, at the start
of the tiled comparison. On the finer surface, its three vertices were
0.01200–0.01707 source unit from the candidate surface; its centroid and edge
midpoints were also within 0.0225. These isolated point distances **do not
establish containment of the whole triangle**. The independent full-triangle
envelope test still failed. CGAL's facet-distance setting is therefore not a
substitute for the acceptance check. Neither output was used for volume
meshing or FEA.

CGAL documents its polyhedral envelope as a **conservative** subset of the
Euclidean distance envelope: a rejection alone does not prove excessive
Hausdorff distance. We therefore ran its separate bounded-error Hausdorff
decision on the 0.5 / 0.01 candidate, with a 0.0225-source-unit limit and
0.0025 error bound. It reports the distance exceeds the limit in **both
directions**. A complete source-vertex-to-candidate-surface query independently
finds a 0.128938-source-unit deviation at source coordinate
`[-124.756508, -48.043331, 30.616766]`; this vertex witness alone disproves
the required bound. The candidate-to-source vertex maximum is only 0.000501,
so vertex-only checks would miss its reverse-direction triangle deviation.
The [CGAL envelope documentation](https://doc.cgal.org/latest/Polygon_mesh_processing/)
and [bounded-distance API](https://doc.cgal.org/latest/Polygon_mesh_processing/group__PMP__distance__grp.html)
describe these distinct predicates.

Reducing the sharp-feature threshold from 60° to 40° at the same 0.5 / 0.01
facet settings produced 1,843,616 faces. Its maximum source-vertex distance
fell to 0.096972 source unit, still over four times the 0.0225 limit. The
independent screen also found self-intersection despite a closed, genus-one
edge topology. A 20° trial remained in CGAL feature protection after more
than fifteen minutes of local CPU time and was terminated without an exported
surface; it has **no geometry acceptance result**. These trials show that
simply detecting more edges does not provide a qualified boundary. The next
volume-mesh attempt should preserve the protected surface itself or constrain
only a measured, localized correction, with the same independent distance and
self-intersection gates.
The private release also contains `mesh3-hausdorff-followup-private-001.tar.gz`,
SHA-256 `c6cba2bdf5b78334cbdb1a2dd94fdfe412e6cf8d7ca07f74f86bd9c5daf12c5a`,
with the Hausdorff and vertex-distance tools, 40° surface, trial receipt and
checksums. All nine payload members passed hash readback; GitHub reports the
same archive digest.

The private [release](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
contains `mesh3-surface-rejected-package-001.tar.gz`, SHA-256
`2d26fcf2c59fde544ab40adc34c0da78c7a7a3608db74716e71a25d0bf7fb540`,
with the trial code, raw and oriented surfaces, rejection receipt and checksums.
All ten payload members passed local hash readback; GitHub reports the same
archive digest. The next numerical step is to distinguish a local
full-triangle shape deviation from overly conservative tile selection at the
first rejected face. A boundary-preserving volume mesher on the protected
surface remains the alternative if the surface cannot be safely retessellated.

### TetGen reconstruction and boundary-preserving volume refinement

TetGen 1.5.1 was compiled natively on the Apple Silicon Mac from the archived
upstream source. An analytic single-tetrahedron control confirmed the
reconstruction and refinement commands. The existing Gmsh Frontal volume was
exported to TetGen's `.node`, `.ele` and `.face` formats without rounding its
coordinates; its source NPZ has SHA-256
`463991146aa0e5deed4ef3376371069f7a0ad2fb6a184f32cf7e97baf6c301af`.
The protected 878,730-face analysis surface has SHA-256
`5d900f6da900b4bffac2fdacfd6e0a346f8c0259a19299725621d4fd1e48c12a`.

`tetgen -rYQ rotor` reconstructed the original volume exactly by node
coordinates, unoriented cells and unoriented boundary faces. One bounded
refinement, `tetgen -rYq1.4/10S50000Q rotor.1`, added 50,000 interior
vertices. The first retained volume (`rotor.2`) has 494,676 vertices,
1,647,463 tetrahedra and 878,730 boundary faces. Its boundary triangles
changed connectivity but retained every original boundary vertex coordinate
exactly; there are no new boundary vertices. The independent full-triangle
polyhedral-envelope checker passed in both directions at **0.0225 source
unit**, including topology and self-intersection checks. This is a conservative
sufficient containment test, not a Euclidean Hausdorff measurement and not a
millimetre tolerance.

An independent all-face connectivity audit found one tetrahedral component,
zero non-manifold faces, and exact agreement between the 878,730 stored
boundary faces and actual exposed faces. Exact arithmetic found zero flat or
inverted tetrahedra and a signed volume of 431,159.924548 source units³.
The quality comparison is:

| Volume | Tetrahedra | Minimum mean ratio | Below 0.01 | Median mean ratio |
| --- | ---: | ---: | ---: | ---: |
| Gmsh source | 1,393,021 | 0.0000177149 | 3,255 | 0.1150 |
| TetGen first refinement (`rotor.2`) | 1,647,463 | 0.0000332920 | 686 | 0.3743 |
| TetGen second refinement (`rotor.3`) | 1,990,430 | 0.0000000002776 | 558 | 0.5775 |

The second refinement was rejected because it introduced an extreme sliver,
despite improving the median and count below 0.01. A flip-only pass on a
separate copy of `rotor.2` made no quality improvement. **No volume is admitted
for FEA**: the retained `rotor.2` still has 686 tetrahedra below mean ratio
0.01, and no mesh-convergence, load, mode or material study was run on it.
The scale and historical installation interfaces also remain unverified.

The private [release](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
contains `tetgen-preserved-volume-001.tar.zst`, SHA-256
`4af11a6c3a4c03b60e51512406c2848b6582b6c9e51310597b991bd3545dc0e3`,
with the retained and rejected TetGen outputs, exporter and audit scripts,
the analytic control, logs and input hashes. All 44 archive members passed
hash readback; GitHub reports the same archive digest. The next mechanical
step is local treatment of the residual low-quality cells followed by exact
orientation, full surface-envelope, connectivity and convergence audits.

### Follow-up refinement with boundary operations enabled

Starting from the first retained volume, two bounded passes of
`tetgen -rq1.4/10S50000Q` were run without `-Y`. The first reduced the count
below mean ratio 0.01 from 686 to 403; the second reduced it to **391**.
The latter has 495,085 vertices, 1,648,991 tetrahedra and the same 878,730
boundary faces. All original boundary coordinates remain exact and all 409
new vertices are interior. The complete bidirectional 0.0225-source-unit
polyhedral envelope, topology and self-intersection checks passed. A separate
volume-connectivity audit found one component, zero non-manifold faces and an
exact match between stored and exposed boundary faces. Exact arithmetic found
zero flat or inverted cells and a volume of 431,159.926128 source units³.
The minimum mean ratio remains only 0.0000934998; the median is 0.37395.
Of the 391 cells below 0.01, **235 use four boundary vertices**, so the
residual is strongly constrained by boundary connectivity. Additional
unfocused interior refinement is unlikely to remove it; localized boundary
work must be independently checked against the same envelope.

The private release contains `tetgen-boundary-split-001.tar.zst`, SHA-256
`c0a7e9001c5484430b2f0ebb7e534cc310dcaf5e8e44770df17144d142e767f9`,
with both raw volumes, geometric and exact audits, residual-cell map and logs.
All 24 archive members passed hash readback; GitHub reports the same archive
digest. The improved volume is still **not admitted for FEA**; no converged
stress, modal or fatigue claim follows from these mesh checks.

### Interior relocation and inversion repair

The 391 residual cells were classified by their four triangular faces. Of
these, 227 touch the exterior boundary; 164 do not. Among the boundary faces
with triangle quality below 0.1 that are incident to a residual cell, 74 were
already present in the input boundary and 31 were introduced by TetGen.
This distinction directs later surface repair toward both inherited and new
facets rather than treating every weak tetrahedron as the same defect.

Gmsh 4.15.2 `Relocate3D`, run with discrete-entity forcing and one iteration,
moved 38,594 interior nodes and left boundary coordinates and connectivity
unchanged. It reduced the positive-cell count below mean ratio 0.01 to 274,
but **inverted 48 cells**, so that raw output was rejected. A separate
`UntangleMeshGeometry` run worsened the result to 2,573 inverted cells and
was also rejected. An analytic interior-node control verified that the
relocation call moves the internal point while holding its four boundary
vertices fixed. The [Gmsh API documentation](https://gmsh.info/doc/texinfo/)
defines these mesh-optimization methods.

A bounded repair then halved the relocation only at interior vertices of
nonpositive cells, recalculating all 1,648,991 tetrahedra after each pass.
After nine passes, 46 vertices had reduced displacements. The result has
**271 cells below mean ratio 0.01**, down from 391, with zero flat or inverted
cells in an independent exact-arithmetic audit. Its minimum mean ratio is
0.0000934998 and median 0.39405. An independent connectivity audit confirms
one volume component and exact agreement of the 878,730 stored and exposed
boundary faces. The complete boundary OFF is byte-identical to the previously
accepted surface, so the earlier full bidirectional envelope, topology and
self-intersection result applies without a new approximate comparison.
Its exact volume remains 431,159.926128 source units³.

Of the 271 residual weak cells, 235 have four boundary vertices whose
coordinates were fixed; interior relocation cannot improve those cells
without changing their connectivity. Six cells became newly weak while 126
previously weak cells crossed above the threshold. The retained result is
**still not admitted for FEA**: the weak boundary cells and mesh-convergence
study remain unresolved.

The private release contains `gmsh-interior-optimization-001.tar.zst`,
SHA-256 `03d481eab05e915b8949d92eb550bf64864822d6abc00b41fa8e9a38cfe83caa`,
with the scripts, accepted exploratory volume, rejected outputs, exact and
connectivity audits, logs, and full residual-cell list. All 28 archive members
passed hash readback; GitHub reports the same archive digest.

### Higher-level TetGen optimization after interior repair

TetGen 1.5.1's [mesh-optimization switches](https://www.wias-berlin.de/software/tetgen/1.5/doc/manual/manual005.html)
were then tested on the exact-positive interior-repaired volume. An
optimization-only `-rYO5/7Q` pass changed no quality statistic. With bounded
refinement enabled, `-rYq1.4/10S50000O5/7Q` added 50,000 nodes and produced
1,981,741 tetrahedra. Its cells below mean ratio 0.01 fell from 271 to 142;
the median rose to 0.58350. A further bounded pass without `-Y` produced
**1,980,992 tetrahedra and 120 cells below 0.01**. The final median mean
ratio is 0.58363; the minimum remains 0.0000934998. Ninety-seven of the 120
weak cells use four boundary vertices.

Both refined volumes passed the independent full bidirectional
0.0225-source-unit polyhedral-envelope check, including topology and
self-intersection. For the final volume, exact arithmetic found zero flat or
inverted tetrahedra and a volume of 431,159.940061 source units³. A separate
all-face audit found one tetrahedral component, zero non-manifold faces and
exact agreement of the 878,730 stored boundary faces with the actual exposed
faces. Every original boundary vertex coordinate remains unchanged; the
surface connectivity changed, so its geometric acceptance rests on the full
envelope check rather than vertex-only comparison.

The private release contains `tetgen-opt5-001.tar.zst`, SHA-256
`41c4f2c44747685e4c959055c6b98dbe3b6f56214f0f7ebf7c414e52bde727a5`,
with both bounded outputs, exact and connectivity audits, surface checks,
quality receipts, residual-cell list and the TetGen binary hash. All 25
archive members passed hash readback; GitHub reports the same archive digest.
This is the best current **exploratory** mechanical volume, not a validated
FEA mesh. The remaining weak cells, uncalibrated scale, missing exact 935
interfaces, material data and convergence study still block strength,
fitment and manufacturing claims.

The 120 residual cells form **73 node-connected groups**. The largest group
contains 17 cells, all with four boundary vertices, around radius 108.97 and
Z 2.59 in uncalibrated source units. The group is a priority for a localized
boundary/connectivity inspection; node sharing alone does not establish that
the scan is defective. A hash-pinned [private localization receipt](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
lists every group and its original cell/node IDs. Its SHA-256 is
`2b5e90f4da7df1680859951d9767780c93f1a3848be20780352c44fa0c9b3b2a`,
matched by the uploaded release asset. Any altered patch must again pass the
full bidirectional envelope, topology, exact-volume and connectivity audits
before mechanical meshing is reconsidered.

A second local inspection compared that group's incident exterior facets with
the protected source OFF using exact original vertex order and unordered face
indices. Of 92 incident boundary triangles, **90 are inherited** and two were
introduced during meshing. Twenty-eight have equilateral-normalized triangle
quality below 0.1; the minimum is 0.0330. This points the first geometric
review at inherited thin facets, rather than only TetGen connectivity. It
does not prove that those facets are scan errors or justify moving them. The
private [patch receipt and XY inspection image](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
have verified SHA-256 values `4e5c922b1ebb7947c4bea913c27bda06e79dcd76ef33f5369e69e82f8c16d35e`
and `03a33292166d8f2367a81743733ce919e520ad562ffa5f6a0921fe56cf3f4199`.

### Local edge-flip hypothesis

Four disjoint edges around the 17-cell group were flipped without moving any
vertex. The affected face-pair minimum equilateral-normalized qualities rose
from 0.0330, 0.0567, 0.0762 and 0.0773 to 0.1512, 0.1849, 0.2123 and
0.1997. The complete 878,730-face candidate passed the independent
bidirectional 0.0225-source-unit polyhedral-envelope, closed-topology and
self-intersection checks. These are triangulation changes to a hypothetical
analysis surface, not corrections established against the original scan.

TetGen 1.5.1 refused this input at its default 0.1° near-overlap screen: one
adjacent face pair had a reported 0.008476° dihedral. A separate exploratory
run used the explicit `-p/0.001` facet-overlap tolerance. This changes the
mesher's acceptance setting, not the geometric certificate. After one
boundary-preserving and two boundary-enabled 50,000-point-limited refinements,
the volume had **1,938,298 tetrahedra and 141 cells** below mean ratio 0.01.
No weak-cell centroid remained within eight source units of the prior largest
group's centroid (16 in the previous 120-cell volume). The final surface again
passed the complete envelope/topology/self-intersection check, and all original
boundary vertex coordinates remained exact.

The global weak-cell count is worse than the preceding **120-cell** volume,
so that remains the preferred exploratory volume. The edge-flip variant is
retained only as evidence that local boundary connectivity matters; exact
tetrahedral orientation/volume and full volume-connectivity audits were not
completed for this inferior trial. The [private archive](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
contains the candidate surface, TetGen input, final volume, logs and manifest.
All 18 archived members and the uploaded SHA-256
`90c0487a7fb0360558716612322bc5c85859d618762881745f3ca92ebf6bc080`
were verified. Neither volume is admitted for FEA.

## Available cylinder-head scan and the 935 engine boundary

The local `935+Xtreme+Cyl+head.obj` was independently audited without repair,
scaling or geometry export. It contains 1,281,608 vertices and 2,466,040
triangles in four connected surface components. Its 99,876 boundary edges and
eight zero-area triangles mean it is an open acquisition. The file supplies
neither units nor an authenticated identity, and its name does not establish
historical 935 fitment. It therefore remains separate from the active
six-cylinder packaging hypothesis; it cannot replace a measured 935 crankcase
or establish the head/duct mounting datums. The original 917 context scan
remains comparative only.

The complete private [scan audit](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
has SHA-256 `19226a9974e597671d873e4a8d227c9f1e7ef67d8cac102c0f9bbf4f387bf6cb`,
matched by the uploaded release asset. No scan geometry was added to public
Git. The next assembly step still requires specimen-specific 935 engine
surfaces or independently measured crankcase, head and shroud datums.

## Corrected rotor: exploratory fluid volume

The corrected 0.7 rotor was substituted into the retained exploratory outer
fluid boundary without moving its outer vertices, triangles or patch markers.
The reusable
[`compose_root0p7_fluid_plc.py`](../../../twins/935-horizontal-cooling-system-f0/source/corrected-analysis-20261025/compose_root0p7_fluid_plc.py)
pins the SI rotor OBJ (`ee9357d46911fc0112342626064f7e731395af9db9a8bc340793cf22effb24a6`)
and prior boundary NPZ (`67835eacd4d1c7f9736b5fc826979f8ad48366397b422e672043ef720c027f86`).
The resulting PLC has 447,868 vertices, 895,732 triangles and a signed fluid
volume of 0.05140884014124352 m³ under the **unverified** source-to-SI scale.
An analytic nested-box control passed, and the complete rotor and fluid
surfaces passed closed-orientation and solid-hole winding checks. The outer
boundary is an exploratory duct, **not a measured 935 shroud or engine**.

On the Mac, TetGen 1.5.1 (`847c43da808f6e65dd4a6c5091c23384fcc42ff4ce32692ec336ca8da6ce08df`)
completed `-pYq1.4MzCf` in 201.5 s with 817,600 nodes and 3,727,134
tetrahedra. The existing independent full-volume audit established exact
positive orientation for every cell, one connected volume, no duplicate or
non-manifold faces, exact PLC volume equality, and a complete boundary
coordinate/triangle/marker bijection for all 895,732 exterior faces. Its
audited volume NPZ has SHA-256
`bcad2182f1e78e2cc6fe2ca90ddc5c277b0e93ca35dce4ddca9082b4a60e0420`.

The new [`audit_root0p7_tet_quality.py`](../../../twins/935-horizontal-cooling-system-f0/source/corrected-analysis-20261025/audit_root0p7_tet_quality.py)
measured every tetrahedron. Equilateral-normalized mean ratio has minimum
0.00002917, first percentile 0.04280 and median 0.72962. **3,461 cells**
fall below 0.01, 46,029 below 0.05 and 92,185 below 0.1. Thus this volume is
topologically valid but **not CFD-quality admitted**. It has no boundary-layer
study, native OpenFOAM `checkMesh`, grid convergence, operating-point solve or
measured 935 installation. No airflow, pressure, torque or thermal conclusion
can be drawn from it.

Of the 3,461 cells below 0.01, **3,425 touch rotor-wall nodes**, 27 touch
outer-boundary nodes, 22 touch both and 31 touch no boundary node. These sets
overlap; the counts do not establish whether the rotor surface, its sampling
or TetGen's near-wall fill is the root cause. The updated complete quality
receipt is stored [privately](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
as `935-cfd-root0p7-quality-v2.json`, SHA-256
`a5604df0106057af4f697933a5bd02016eb1da63ae2a4642ae97fd571875db46`,
matched by GitHub's asset digest.

An exact face-index comparison narrows this result: **1,743** of those weak
tetrahedra share at least one complete rotor boundary triangle, while 1,718
do not. The 1,989 incident rotor triangles have median equilateral-normalized
quality **0.2462**, versus **0.8121** for all 878,730 rotor triangles. Among
the incident triangles, 357 have quality below 0.1. This association directs
the next local remeshing study toward poor wall facets; it does not by itself
establish a scan defect or prove causation. The reproducible full-face audit is
in `audit_root0p7_tet_quality.py`; its [private result](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
is `935-cfd-root0p7-quality-face-audit-001.json`, SHA-256
`b0c70c9c45dbd9ef629e0524f78d810b9bfd51affbe8f88d7198e527e35adf84`,
matched by the uploaded digest.

The [reproducible private-view renderer](../../../twins/935-horizontal-cooling-system-f0/source/corrected-analysis-20261025/render_root0p7_weak_cells.py)
plots the complete weak-cell set over sampled rotor-wall vertices in top and
side views. The local regeneration was byte-identical. The
[private image](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
`935-cfd-root0p7-weak-cells-top-side-001.png` has SHA-256
`dcaa30c80d0348d164cd8c1a3b08875e34d879d5793059ba555e64b21212a650`,
matched by GitHub's asset digest. It visualizes a concentration near the inner
rotor annulus and selected blade junctions; this is an inspection observation,
not proof that those surfaces are inaccurate or that the whole assembly fits.

A second boundary-preserving TetGen attempt used `-pYq1.2/10O5MzCf` on the
same pinned PLC. It hit the 300 s limit with no mesh output; the process was
confirmed absent. The [private timeout receipt](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
has SHA-256 `c31a9e856b264b6d0876237a2b426924445fbb4cc45a04dc01bb63134c09f1a7`.
No quality comparison is inferred from that incomplete attempt.

### Local wall-triangle flip trial: rejected

The reproducible [`propose_root0p7_wall_flips.py`](../../../twins/935-horizontal-cooling-system-f0/source/corrected-analysis-20261025/propose_root0p7_wall_flips.py)
tested a local triangulation change at weak rotor-wall cells. It selected 32
disjoint edge flips from 119 proposals, changed 64 triangle rows and moved no
vertices. Both surfaces were closed and consistently wound. The independent
complete bidirectional envelope checker passed at **0.0225 uncalibrated source
units**, with 0.0025 units reserved numerical margin; this is not a measured
physical tolerance. The candidate OFF SHA-256 is
`59118742062e1c16eaf77217c7257ad636f4d16e685eebaa13c65ab11ba0a163`.

The [`prepare_root0p7_flipped_fluid_plc.py`](../../../twins/935-horizontal-cooling-system-f0/source/corrected-analysis-20261025/prepare_root0p7_flipped_fluid_plc.py)
reused the same exploratory outer boundary, SI scale assumption and TetGen
1.5.1 flags `-pYq1.4MzCf`. Its independent full-volume audit passed positive
cell orientation, one component, and exact boundary triangle/marker bijection
for all 895,732 faces: 817,964 nodes and 3,731,418 tetrahedra. The volume
NPZ SHA-256 is `788f42eb332c65da2dd7c61a430930f978e6189487a080a02fe9f3b592a556bf`.

The critical mean-ratio bin **worsened**: 3,461 to **3,761** cells below 0.01.
Counts below 0.05 improved from 46,029 to 45,314 and below 0.1 from 92,185
to 91,115, but those broader improvements do not admit this mesh for CFD.
The candidate is **rejected**, and the preceding baseline remains the reference
for further mesh work. No OpenFOAM solve, mechanical validation or airflow
claim follows from this trial. The private
[`935-cfd-root0p7-flip-trial-001.tar.zst`](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
archive contains the candidate, envelope result, PLC, TetGen output, full
audits and SHA-256 manifest; archive SHA-256 is
`2388e2224f132017fc713c708d67523997f0d2a53f617d095054d3ababa1f2c9`.
All 23 listed file hashes passed extraction readback.
The private GitHub release reports the same archive SHA-256 digest.

### Fixed-boundary TetGen optimization: improved, not admitted

The original, unchanged PLC (`32deebcc19f604454bb4cfe5d26d6a1e1e141fef06c0e1b095df58368e8c5bee`)
was remeshed locally with the same TetGen 1.5.1 executable and
`-pYq1.4O5MzCf`. The only switch change from the baseline was optimization
level `-O5`. TetGen completed in 395.8 s. The independent full-volume audit
passed exact positive orientation, one connected volume, complete boundary
coordinate/triangle/marker bijection for all 895,732 faces and exact PLC
volume equality. The output contains 817,235 nodes and 3,714,547 tetrahedra;
the audited volume NPZ SHA-256 is
`b62927d017b78a784bce79d8117a1899b05b6aefffe0fa2c926fa291ca2108d9`.

Equilateral-normalized mean ratio below 0.01 fell from **3,461 to 2,929**
(532 fewer; 15.4%). The counts below 0.05 fell from 46,029 to 43,964 and
below 0.1 from 92,185 to 89,765. The minimum rose from 0.00002917 to
0.00019493; the first percentile rose from 0.04280 to 0.04422. Of the 2,929
remaining cells below 0.01, **2,857 touch rotor-wall nodes**. This is useful
evidence that volume optimization helps, while rotor-near quality still needs
work. The median changed from 0.72962 to 0.72904, so improvement is not
uniform. **The mesh is not CFD-quality admitted**: boundary-layer evidence,
native OpenFOAM `checkMesh`, three-grid convergence and a measured 935
shroud remain absent.

The private
[`935-cfd-root0p7-o5-trial-001.tar.zst`](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
contains the pinned input PLC, TetGen output, execution receipt, full audit,
quality report and a SHA-256 manifest. Its SHA-256 is
`5afc64f5e8366c7483b5b42f41deb68c5c24ab5afa77ae343777c7a9b48d2bf3`;
all 10 listed files passed extraction readback. The preceding private archive
supplies the reference boundary NPZ and receipt needed to rerun the existing
`audit-tetgen-002.py` against this output.
The private GitHub release reports the same archive SHA-256 digest.

The [private four-view comparison](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
(`weak-cell-comparison.png`, SHA-256
`d139ea4810684d4915561884c16a5ee2bcb0f815aa4672e28a60713a531baffc`)
shows that the main weak-cell clusters persist near the inner annulus and
selected blade junctions. This is a visual localization, not proof of a scan
defect. The private release digest matches the local image.

An exact face-index audit of the `-O5` volume finds **1,357** weak cells
sharing a complete rotor boundary triangle and **1,572** without one. The
1,388 incident rotor triangles have median equilateral-normalized quality
0.492, versus 0.812 across the rotor surface; 209 incident triangles are
below 0.1. The [private face-audit receipt](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
(`weak-face-audit.json`) has SHA-256
`6dbf4c30954a0b71b4c58a81d633be3ed5b6071d285e61adf56c19b8aa620149`,
matching the release digest. This separates direct wall-face cells from
near-wall cells; further work must inspect both surface discretization and
volume filling. The counts do not identify a defect in the scanned shape.
The hash-pinned
[`audit_root0p7_o5_faces.py`](../../../twins/935-horizontal-cooling-system-f0/source/corrected-analysis-20261025/audit_root0p7_o5_faces.py)
reproduces the private receipt byte for byte from the archived audited volume:

```sh
mkdir -p work/NEW
uv run --no-project --python 3.12 --with numpy==1.26.4 python \
  twins/935-horizontal-cooling-system-f0/source/corrected-analysis-20261025/audit_root0p7_o5_faces.py \
  work/935-cfd-root0p7-20261026-o5-audit/volume.npz work/NEW/weak-face-audit.json
```

Two further runs used the **same PLC** and executable. A request for `-O10`
completed in 203.8 s, but inspection of the pinned TetGen 1.5.1 parser showed
that `-O` consumes one digit; that run actually used level **1**, not level 10.
Its independent audit passed exact cell orientation, one connected volume,
complete 895,732-face boundary bijection and PLC volume equality. However,
8,636 cells were below mean ratio 0.01, versus 3,461 in the baseline and
2,929 with `-O5`; level 1 is rejected on quality. The explicit `-O6` run
reached its 900 s limit with no mesh output and its process exited. These
trials do not improve the best known `-O5` result, which remains **not CFD
admitted**. The private
[`935-cfd-root0p7-o1-o6-rejected-trials-001.tar.zst`](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
stores both receipts and the full rejected level-1 output and audit; archive
SHA-256 is `6422279606d89592c707de56b16c35466552bcc293c583cd68f643a34df0fb12`.
All 12 files listed in its manifest passed extraction readback. The compact
private decision receipt `o1-o6-trials-receipt.json` has SHA-256
`2e14289baa298f5039e9d92f5f7f56a7638b162caf18213e3a40e78c78a04368`.
Both private release digests match the local files.

### Conditional rotor inertia and drive-load screen

The hash-pinned
[`screen_root0p7_rotor_dynamics.py`](../../../twins/935-horizontal-cooling-system-f0/source/corrected-analysis-20261025/screen_root0p7_rotor_dynamics.py)
uses the closed corrected 0.7 rotor surface and the existing ten material
cards. The rotor has 878,730 faces, volume 431,159.86 cubic **source units**
and polar volume inertia 3.58693×10⁹ source units to the fifth about the
candidate Z axis through the source origin. This axis is not an independently
measured shaft datum. The corresponding 0.6 PicoGK rotor receipt differs by
0.034% in volume and 0.031% in polar volume inertia; the two surfaces are
different model candidates, so these small differences are not a convergence
or dimensional-accuracy proof.

At the **unverified** scale of one millimetre per source unit, uniform-density
solid geometry gives the following conditional values. The 6,000 rpm cases are
direct *rotor* speed hypotheses, and the torque assumes linear deceleration
from that speed to zero in 0.1 s; it is not a measured fan torque or a safe
stopping load.

| Material card | Rotor mass | Polar inertia | Energy at 6,000 rpm | Inertial torque for 0.1 s stop |
|---|---:|---:|---:|---:|
| AlSi10Mg LPBF | 1.151 kg | 0.00958 kg·m² | 1,890 J | 60.2 N·m |
| WE43 magnesium candidate | 0.789 kg | 0.00656 kg·m² | 1,296 J | 41.2 N·m |
| Ti‑6Al‑4V LPBF | 1.897 kg | 0.01578 kg·m² | 3,115 J | 99.2 N·m |

Mass varies with the **cube** of the unknown scale; polar inertia, energy and
inertial torque vary with its **fifth power** at fixed rpm. The private
[`rotor-dynamics-screen.json`](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
contains all ten cards, three conditional scales (0.8/1.0/1.2 mm per source
unit), and the pre-existing hypothetical rotor speeds 3,000/6,000/8,500/
11,000 rpm. Its SHA-256 is
`e433e4fc6b8ef81f48f6e8edfac237884a689604bc1fde2ff335077f553446cf`,
matched by the private release digest. WE43's card uses a wrought density
surrogate and supplies no part strength allowable. The result excludes shaft,
gears, bearings, shroud, aerodynamic torque, balance, thermal growth, fatigue
and manufacturing effects. It establishes no safe speed or material choice.
The [private ten-material comparison plot](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
(`material-mass-inertia.png`) has SHA-256
`9affaf3da6360cadfc9e1cc85241a550269b41ae15906d903fa232b8719c0107`,
also matched by its release digest; it visualizes the same density-only screen.

The earlier 160-case transmission hypothesis used a simplified annulus. The
hash-pinned [`rebase_root0p7_drive_loads.py`](../../../twins/935-horizontal-cooling-system-f0/source/corrected-analysis-20261025/rebase_root0p7_drive_loads.py)
replaces only that annulus's stopping inertia with the corrected rotor's
inertia, retaining the original **unmeasured** fan torque, assumed 40 mm gear
pitch diameter and assumed 16 mm solid shaft. For the conditional 1 mm/source
scale, 6,000 rotor rpm, 0.1 s stop and 0.5 network-resistance multiplier:

| Card | Old annulus mass | Corrected rotor mass | Old → corrected stopping torque | Updated total torque | Gear tangential force | Shaft torsion stress |
|---|---:|---:|---:|---:|---:|---:|
| AlSi10Mg | 0.765 kg | 1.151 kg | 46.7 → 60.2 N·m | 62.4 N·m | 3,120 N | 77.6 MPa |
| WE43 | 0.524 kg | 0.789 kg | 32.0 → 41.2 N·m | 43.5 N·m | 2,174 N | 54.1 MPa |
| Ti‑6Al‑4V | 1.261 kg | 1.897 kg | 77.0 → 99.2 N·m | 101.4 N·m | 5,070 N | 126.1 MPa |

The corrected rotor raises this particular AlSi10Mg stopping-inertia estimate
by 28.8%; the preceding annulus was not a conservative load model. The
shaft stress is a nominal elastic torsion formula for the **assumed** solid
diameter, not an FEA result or a strength margin. Missing shaft/gear
measurements, scale calibration, fan torque, shock profile, material allowables
and fatigue data prevent any safe-speed or manufacturing conclusion. The
[private 160-case report](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
(`rebased-drive-loads.json`) has SHA-256
`dbc3a4e68aea7b47c6a34019f3ab400aa5ff981f84fab56ce42675e03c20d8f1`,
matched by its release digest.

```sh
mkdir -p work/NEW
python3 twins/935-horizontal-cooling-system-f0/source/corrected-analysis-20261025/rebase_root0p7_drive_loads.py \
  work/935-hypothesis-tests-20261007/accepted-results.json \
  work/935-cfd-root0p7-20261026-o5-audit/rotor-dynamics-screen.json \
  work/NEW/rebased-drive-loads.json
```

### Output coupling gap: ideal annular body screen

The scans still do not define a torque-carrying connection between the output
patch and rotor bore. The [annulus screen](../../../twins/935-horizontal-cooling-system-f0/source/corrected-analysis-20261025/screen_hub_annulus.py)
uses only the already reported nearest-point radii (7.62052 and 11.45477
uncalibrated source units) and the four observed axial bands spanning −20..0.
Under the **unverified** 1 mm/source scale, an ideal continuous annulus filling
that entire radial gap for 20 mm has 4.59549 cm³ of material and polar section
`J = π(Ro⁴ − Ri⁴)/2 = 2.17463×10⁻⁸ m⁴`. For the same hypothetical 6,000 rpm,
0.1 s stop and 0.5 network-resistance case above:

| Same material as rotor | Ideal annulus body mass | Nominal outer torsional shear `T Ro/J` |
|---|---:|---:|
| AlSi10Mg | 12.27 g | 32.87 MPa |
| WE43 density surrogate | 8.41 g | 22.90 MPa |
| Ti‑6Al‑4V | 20.22 g | 53.41 MPa |

These are **optimistic body-only section calculations**, not a sleeve design.
One closest-point pair does not measure the full shaft circumference; the
observed drive arc leaves about half the circumference unseen. A real adapter
would need machining clearance or interference, torque-transfer features,
axial retention and fillets that change the section and local stresses. Its
identity, fit, fatigue, thermal behavior and support loads remain unknown.
The [private 160-case report](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
(`hub-annulus-screen.json`) has SHA-256
`dd421f9c9731605c97ee2efda3ebb348fc406274eda6f80d451cfe00b23d7853`,
matching the release digest. It authorizes no manufacturing or speed limit.

```sh
mkdir -p work/NEW
python3 twins/935-horizontal-cooling-system-f0/source/corrected-analysis-20261025/screen_hub_annulus.py \
  work/935-assembly-0p7-20261025/hub-output-metrology-001.json \
  work/935-cfd-root0p7-20261026-o5-audit/rebased-drive-loads.json \
  work/935-cfd-root0p7-20261026-o5-audit/rotor-dynamics-screen.json \
  work/NEW/hub-annulus-screen.json
```

```sh
mkdir -p work/NEW
uv run --no-project --python 3.12 --with numpy==1.26.4 --with trimesh==4.9.0 python \
  twins/935-horizontal-cooling-system-f0/source/corrected-analysis-20261025/screen_root0p7_rotor_dynamics.py \
  work/935-root-quality-local-20261025/analysis-candidate.off \
  twins/935-horizontal-cooling-system-f0/vast-omniverse-screen/materials.json \
  work/NEW/rotor-dynamics-screen.json
```

Reproduce the private PLC with Python 3.12, NumPy 1.26.4, SciPy 1.13.1 and
trimesh 4.9.0. The Mac's existing SciPy 1.15.3 installation failed to load a
native module, so the isolated versions were used. Run the existing
`fluid-mesh-study-20261022/audit-tetgen-002.py` after a bounded TetGen run,
then the quality script above. The private archive
[`935-cfd-root0p7-20261026.tar.zst`](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
contains the inputs, mesh, execution log, complete audits and file manifest.
Its SHA-256 is `0b5071c7276d5c2bfedefe868b489b786e1af5a025cd0bbe7a7eb95b357d8277`.
All 16 listed file hashes passed an extraction readback, and the private
GitHub release reports the same SHA-256 digest. The archive is not a released
design or simulation result.

From the repository root, after restoring the hash-pinned private inputs:

```sh
uv run --no-project --python 3.12 --with numpy==1.26.4 --with scipy==1.13.1 --with trimesh==4.9.0 \
  python twins/935-horizontal-cooling-system-f0/source/corrected-analysis-20261025/compose_root0p7_fluid_plc.py \
  work/935-cfd-root0p7-new-plc
python3 twins/935-horizontal-cooling-system-f0/source/corrected-analysis-20261025/audit_root0p7_tet_quality.py \
  work/935-cfd-root0p7-20261026-audit/volume.npz work/935-cfd-root0p7-new-quality.json
```

## Remaining gates

No new OpenFOAM meshing or CFD solve has run on either corrected candidate.
The prior snapped case used the old rotor and failed the full native `checkMesh` with
316,996 concave cells and two duplicate-face warnings. Its numerical results
cannot validate the new input. Kali1's Thunderbolt bridge dropped during this
run, then recovered; SSH access and the previously known host key were
verified. The `lolman` account cannot access its Docker daemon, and the Mac
Docker daemon did not answer an eight-second read-only probe. Neither service
was changed. No new Vast rental was created.

The next computational gates are a quality-converged conforming volume for
mechanics and a fresh fluid mesh on the chosen rotor, with complete native
quality checks, boundary-layer evidence, resolved concavity and duplicate
faces, and a three-grid study. Airflow, pressure, torque, mechanical strength,
full 935 fitment and manufacturing remain unqualified until their
corresponding calculations, measurements and review exist.
