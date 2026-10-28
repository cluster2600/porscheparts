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
