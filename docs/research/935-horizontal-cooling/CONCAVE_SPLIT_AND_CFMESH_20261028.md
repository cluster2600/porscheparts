# Corrected 935 rotor: concave-cell split and cfMesh trials

These are exploratory fluid-volume mesh trials using the corrected root-0.7
rotor and an unmeasured duct. Source-to-SI scale remains conditional. Neither
trial establishes 935 fitment, airflow, torque, strength, or print readiness.

## Native OpenFOAM `splitCells` trial: rejected

The parent was the 708,822-cell Foundation 13 snappyHexMesh case with one failed
full `checkMesh` check and 46,584 concave cells. Its corrected rotor OBJ had
SHA-256 `ee9357d46911fc0112342626064f7e731395af9db9a8bc340793cf22effb24a6`.
On Kali1, `splitCells -case /workspace -set concaveCells 180` made 45,845 cuts
across five passes (`37011, 8470, 361, 3, 0`). The child contains 754,667
cells, 98,746 concave cells, and **nine** failed checks. The new failures
include four non-orthogonal faces, 20 incorrectly oriented face pyramids,
36 highly skew faces, 418 low-quality or negative face-tet decompositions,
nine small-determinant cells, 11 low-weight faces, and two low-volume-ratio
faces. It is rejected for CFD.

The [public comparator](../../../twins/935-horizontal-cooling-system-f0/source/snap-resume-study-20261025/compare_split_cells.py)
pins both native archives and unchanged geometry, checks the cut-count
identity, and extracts full `checkMesh` outcomes. The private child archive is
[`935-split180-rejected-20261028.tar.gz`](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-split180-rejected-20261028.tar.gz),
SHA-256 `beeb96ef0cd472c4eda07c094cf6952a1575a372162fa8a22f56c1c85243f40f`.
The private comparison receipt is
[`split180-comparison-001.json`](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/split180-comparison-001.json),
SHA-256 `7e7ef9c28eaec453400e85ba260bb1dcfca2e326fb64c4de1a3e2403e882838b`.

## cfMesh Foundation 13 port: input preparation

An isolated build on Kali1 uses the [Foundation 13 cfMesh fork](https://github.com/Ultravis66/cfMesh-OpenFOAM13)
at commit `c91594cc8d86de11043c328c97f4a1dd996d789a`. The fork needed one
local source fix: add `<vector>` to `boundaryLayerCells.C`; its saved patch
has SHA-256 `157f39bc91e568207e72fb3f660bf5006dd83e69b8d3f39fa8c03388f4d2e63b`.
The resulting `cartesianMesh` binary has SHA-256
`783d217e0c486104b8c36e8c3e7d24df58ea34d46a12e978288b8038279c4cab`.
This build is an experiment, not a repository or system installation.

The [STL exporter](../../../twins/935-horizontal-cooling-system-f0/source/gmsh-fluid-study-20261028/export_cfmesh_stl.py)
reads the pinned private fluid PLC with SHA-256
`9fcd93a5c54ebfc98b8cd86d4550e3a416d3e62fb217e5ebfb67eb2f2a9f2085`.
It writes four named solids without changing triangle vertices: inlet 2,304,
outlet 2,304, duct 12,394, and rotor 878,730 faces. Its ASCII STL has SHA-256
`5982ea677297537ec3dfff9825a70a3665b534666751050889a8f567ff4a7ffb`;
the Kali1 copy matched this hash. The first cfMesh case uses 12 mm maximum,
4 mm boundary, 1 mm minimum, and 2 mm rotor local cell sizes under the
conditional scale, without prism layers. Native `surfaceCheck`,
`cartesianMesh`, and full `checkMesh` are separate gates. Passing the mesher
alone does not admit the volume for CFD.

The exact [first-case `meshDict`](../../../twins/935-horizontal-cooling-system-f0/source/gmsh-fluid-study-20261028/cfmesh-meshDict-001)
has SHA-256 `736d74e38e28371841a2004f97221a3bec5e04f54fd8507bb1d1be7dc7c7c6a1`.
The private STL can be regenerated from the repository root with:

```sh
uv run --no-project --python 3.12 --with numpy==2.5.4 \
  python twins/935-horizontal-cooling-system-f0/source/gmsh-fluid-study-20261028/export_cfmesh_stl.py \
  work/935-cfd-root0p7-20261026-repro/boundary.npz \
  work/935-cfmesh-20261028/NEW-boundary.stl
```

In the isolated Foundation 13 environment, place the STL under
`constant/triSurface/boundary.stl`, copy the pinned dictionary to
`system/meshDict`, and provide a standard `system/controlDict`. Run
`surfaceCheck` first, then `cartesianMesh -case CASE`, then
`checkMesh -case CASE -constant -allGeometry -allTopology -meshQuality
-writeSets -writeSurfaces`. The first `surfaceCheck` found 895,732 legal
triangles, a closed surface with two connected parts, and all four expected
patch names and counts. It also reported a minimum triangle quality of
`2.57316e-05`; closure alone does not establish a suitable volume mesh.

## cfMesh first volume: rejected

`cartesianMesh` finished and wrote 995,392 polyhedral cells, 3,442,783 faces,
and four boundary patches. The full Foundation 13 `checkMesh` used the same
quality dictionary as the snappy parent, SHA-256
`bafbc5ced7e83c5a1cc11291a0937c3499a6713e8e3411a83f93464381ba2c7d`.
It found **eight failed mesh checks**: one high-aspect-ratio cell (maximum
2,141.43), six highly skew faces (maximum 5.18223), 74 face-tet decomposition
errors, 354 small-determinant cells, 63,013 concave cells, 92 low-weight
faces, and 132 low-volume-ratio faces. There were also 51 severely
non-orthogonal faces. The mesh volume was `0.0514032` m³ under the conditional
scale. Exit code zero from `checkMesh` does not override its eight reported
failed checks. This first cfMesh volume is **rejected for CFD**. No flow,
pressure, torque, efficiency, or thermal result was calculated from it.
The private case, full logs, build patch, and run scripts are saved in
[`cfmesh-case001-rejected-20261028.tar.zst`](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/cfmesh-case001-rejected-20261028.tar.zst),
SHA-256 `01e15c547ba0b9361ca1ba26726d2baa9956c031e1ad82f7d0a30721a6080819`.
The GitHub release asset digest matched this archive after upload.

The `checkMesh -writeSurfaces` VTK points localize all six skew-face surfaces,
all 74 low-quality face-tet surfaces, and all 51 non-orthogonality error
surfaces within the provisional rotor-neighbourhood screen
`hypot(x,y) < 0.145 m` and `abs(z) < 0.05 m`. The same screen includes all
points on low-weight and low-volume-ratio face surfaces. It includes 99.07%
of the points on the concave-cell surface; the remaining 0.93% extend toward
the exploratory duct boundary. These fractions count exported VTK points,
not distinct cells or independent physical defects. They direct the next
surface/mesh repair toward the rotor neighbourhood and do not justify
discarding the duct checks.
The [private top/side diagnostic image](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/quality-defects-20261028.png),
SHA-256 `ca6c11d4e6ae0c1dcbc2b00de79877529bb2a9a53c64dab55a3ad9b2e0e662b8`,
overlays sampled rotor vertices with those three face-defect sets. Its
millimetre axes use the still-conditional source scale; the image is a
location aid, not an engineering drawing.

## Matched short-edge surface sweep

Three previously protected-analysis-surface-bounded short-edge candidates
(limits 0.001, 0.005 and 0.020 source unit) were exported by the same
[four-patch STL program](../../../twins/935-horizontal-cooling-system-f0/source/gmsh-fluid-study-20261028/export_cfmesh_stl.py).
The unchanged inlet, outlet and duct and the first-case `meshDict` and
`meshQualityDict` hashes were retained. Native `surfaceCheck` found each
input closed with four expected patches. Full `cartesianMesh` and full
Foundation 13 `checkMesh` completed in each case. The
[four-case audit program](../../../twins/935-horizontal-cooling-system-f0/source/gmsh-fluid-study-20261028/audit_cfmesh_sweep.py)
pins all four STL and dictionary hashes before parsing the native logs.

| Case | Rotor surface | Rotor faces | Cells | Severe nonorthogonal faces | Face-tet errors | Small-determinant cells | Concave cells | Failed checks |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 001 | unchanged | 878,730 | 995,392 | 51 | 74 | 354 | 63,013 | **8** |
| 002 | 0.001 short-edge limit | 878,716 | 995,392 | 52 | 73 | 354 | 62,993 | **8** |
| 003 | 0.020 short-edge limit | 878,646 | 995,392 | 50 | 74 | 354 | 63,019 | **8** |
| 004 | 0.005 short-edge limit | 878,698 | 995,392 | 50 | 76 | 354 | 63,010 | **8** |

The [private four-case audit JSON](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/cfmesh-four-case-audit-20261028.json)
has SHA-256 `8796836a1da740693b32ec1cddd5d7f5fbfb876d656fe546daf3fbca0ed3e6a7`.
The [private native case archive](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/cfmesh-shortedge-four-case-20261028.tar.zst)
contains cases 002–004, their run scripts, and the audit; SHA-256
`43e17838c96d8db5a453329101699e3d5f389e9d1e3b4eb3901c28a4c0a2658a`.
Case 001 is in the earlier single-case archive. Both release asset digests
matched after upload.
All cases also have six highly skew faces and one high-aspect-ratio cell.
Small differences among the cases do not constitute a CFD-quality volume.
This comparison suggests the first cfMesh resolution is insensitive to these
small surface changes. It does not prove that the same changes would be
ineffective at a finer mesh resolution.

The candidates were bounded against the protected root-0.7 **analysis
surface**, not directly against the original scan. Their prior CGAL
certificate and Gmsh outcomes are recorded in the
[short-edge study](../../../twins/935-horizontal-cooling-system-f0/source/gmsh-fluid-study-20261028/README.md).
No candidate acquires historical dimensional or physical validation from
these numerical comparisons.

## Rotor-local resolution trial

The unchanged four-patch STL from case 001 was remeshed with a different
[second `meshDict`](../../../twins/935-horizontal-cooling-system-f0/source/gmsh-fluid-study-20261028/cfmesh-meshDict-002),
SHA-256 `d8ed88bf0a58e54de54396762b8d68d7f8864e06f49b1057d552af68358d2431`.
Only `minCellSize` changed from 0.001 to 0.0005 m and rotor-local `cellSize`
from 0.002 to 0.001 m under the conditional scale. The 12 mm maximum and
4 mm general boundary sizes, STL, four patches, and quality dictionary were
unchanged. Native `surfaceCheck`, `cartesianMesh`, and full `checkMesh`
completed. The [resolution audit](../../../twins/935-horizontal-cooling-system-f0/source/gmsh-fluid-study-20261028/audit_cfmesh_resolution.py)
pins both dictionaries, the unchanged STL, and both full quality logs.

| Metric | Case 001 | Fine case 005 |
|---|---:|---:|
| Cells | 995,392 | 2,426,066 |
| Severe nonorthogonal faces | 51 | 76 |
| Highly skew faces | 6 | 30 |
| Low-quality face tets | 74 | 186 |
| Small-determinant cells | 354 | 574 |
| Concave cells | 63,013 | 187,175 |
| Low-weight faces | 92 | 120 |
| Low-volume-ratio faces | 132 | 252 |
| Failed mesh checks | **8** | **8** |

The finer volume is **rejected for CFD**. The concave-cell fraction rose from
about 6.33% to 7.72%; the absolute counts of every listed quality defect
increased. These are two mesh settings, not a three-grid convergence study.
Their failure does not prove that all resolutions or all conforming meshers
will fail, but further global resolution increases alone are not supported
by this evidence. The [private resolution receipt](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/cfmesh-resolution-audit-20261028.json)
has SHA-256 `896d3c8977f44b812dcbca6c0533cfb5250ce6e68a1420281c414058604ae484`.
The [private native fine case](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/cfmesh-rotor1mm-rejected-20261028.tar.zst)
has SHA-256 `f5b82cd95d4a1ff9f4dc53360e06f91f4b0e4119dd25b8f3cd06c7e80c85fafc`.
Both release asset digests matched after upload.

## Bounded next geometry step

The unchanged rotor contains 24 faces below normalized quality 0.01 and 113
below 0.05. A conservative edge-flip proposal requiring nearly coplanar
adjacent faces and no vertex movement found only one eligible disjoint pair.
That proposal reduced the count below 0.05 from 113 to 111, but left all 24
worst faces. It has **not** passed a complete original-scan or protected-
surface envelope check and was not used as a CFD input. The
[private proposal archive](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/one-flip-proposal-20261028.tar.gz),
SHA-256 `b6dbe507fcdfab53764a7613b358eba9a91d4244c20a69573ce2ea7e5c50a4ee`,
retains the candidate and selection code without promoting it as a repair.
An exploratory second proposal allowed adjacent-normal differences up to 30°
and accepted a smaller quality gain. It selected nine disjoint flips,
reducing faces below quality 0.05 from 113 to 102 while leaving all 24 faces
below 0.01. It was stopped before envelope and volume admission because it
did not address the worst facets. The [private proposal archive](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/nine-flip-proposal-20261028.tar.gz)
has SHA-256 `ce766b916c7179a35e16754f52576716e4ef4c58e257938224040f8ff271403f`;
the release asset digest matched. This proposal is not a reference surface.

The next numerical geometry trial should reconstruct the affected rotor
surface patch under independent boundary, self-intersection, and complete
bidirectional scan-envelope checks, then rerun the same native volume-quality
gate. The current conditional scale and unknown 935 mounting dimensions still
prevent fitment or fabrication claims, irrespective of mesh quality.
The [thin-facet scan-proximity screen](THIN_FACET_SCAN_PROXIMITY_20261028.md)
adds a verified coordinate-transport check and location-matched controls.
The subsequent [broader local facet repair](BROADER_FACET_REPAIR_20261028.md)
improves surface quality but its provisional volume meshes still fail checks.
