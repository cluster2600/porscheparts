# Corrected 935 rotor: direct Gmsh fluid-volume trial

This is a **private-geometry, exploratory CFD mesh study**, not a validated
935 shroud or an airflow result. The input is the corrected 0.7-root rotor in
an unmeasured outer duct. Its source-to-SI conversion remains conditional.
The `.npz`, `.msh`, OpenFOAM case and output images belong in ignored `work/`
or the private evidence release; do not add them to public Git.

## Reproduce the first volume on Apple Silicon

Use the archived `boundary.npz` with SHA-256
`9fcd93a5c54ebfc98b8cd86d4550e3a416d3e62fb217e5ebfb67eb2f2a9f2085`.
The programs require a fresh output directory/file and refuse to overwrite
existing evidence. From the repository root:

```sh
uv run --no-project --python 3.12 --with gmsh==4.15.2 --with numpy==2.5.4 \
  python twins/935-horizontal-cooling-system-f0/source/gmsh-fluid-study-20261028/generate_fluid.py \
  work/935-cfd-root0p7-20261026-repro/boundary.npz \
  work/935-cfd-root0p7-20261026-repro/NEW-gmsh-volume

uv run --no-project --python 3.12 --with gmsh==4.15.2 --with numpy==2.5.4 --with scipy==1.18.1 \
  python twins/935-horizontal-cooling-system-f0/source/gmsh-fluid-study-20261028/audit_fluid.py \
  work/935-cfd-root0p7-20261026-repro/boundary.npz \
  work/935-cfd-root0p7-20261026-repro/NEW-gmsh-volume/fluid.msh \
  work/935-cfd-root0p7-20261026-repro/NEW-gmsh-volume/audit.json
```

`generate_fluid.py` creates four discrete Gmsh surface entities from the
existing PLC markers (inlet, outlet, duct, rotor), reconstructs their
topology, then creates one fluid volume with the rotor as an interior void.
The surface triangles are reused rather than remeshed. This follows Gmsh's
[discrete-surface and volume workflow](https://gmsh.info/doc/texinfo/gmsh.html).
The trial uses Gmsh 4.15.2 Delaunay 3D, 2–20 mm nominal size limits under the
conditional SI scale, and standard mesh optimization. The independent audit
compares every surface triangle by coordinates and marker after meshing and
checks every tetrahedron's orientation and mean-ratio quality.

For OpenFOAM Foundation 13, convert the Gmsh 4.1 result to **ASCII MSH 2.2**:

```sh
uv run --no-project --python 3.12 --with gmsh==4.15.2 \
  python twins/935-horizontal-cooling-system-f0/source/gmsh-fluid-study-20261028/convert_msh22.py \
  work/935-cfd-root0p7-20261026-repro/NEW-gmsh-volume/fluid.msh \
  work/935-cfd-root0p7-20261026-repro/NEW-gmsh-volume/fluid-22.msh
```

The exact MSH 2.2 file is transferred to Kali1 with a SHA-256 readback. In
the existing rootless OpenFOAM 13 bundle, `gmshToFoam -case /workspace
/workspace/fluid-22.msh` creates the native mesh. Run
`checkMesh -case /workspace -constant -allGeometry -allTopology -meshQuality
-writeSets -writeSurfaces` and read its full log. Its process exit code alone
is **not** an acceptance result: this trial returned zero while reporting
seven failed mesh checks.

## Observed first trial and decision

The Delaunay trial has 1,029,194 nodes and 4,915,307 positive-volume
tetrahedra. All 895,732 input boundary triangles and four marker groups are
preserved by coordinates to a maximum nearest-point difference below
`1e-16` m. The volume sum is `0.05140884014124352` m³ under the unverified
scale. Mean-ratio quality is below 0.01 in 1,169 cells, so the mesh is not
CFD-quality admitted. A separate `optimize_netgen.py` call on the imported
volume yielded the same cell counts and complete quality statistics; it is
retained as a rejected follow-up, not an improvement.

OpenFOAM imported 4,915,307 tetrahedra and four patches. Full `checkMesh`
reported **seven failed checks**, including 58,976 severely non-orthogonal
faces, 54,127 cells with determinant below 0.001, and four concave cells.
The imported patch mapping is `patch0` inlet (2,304 faces), `patch1` outlet
(2,304), `patch2` exploratory duct (12,394), and `patch3` rotor (878,730).
The native volume was `0.051408840141249142` m³. These are numerical mesh
diagnostics, not pressure, flow, torque, strength, fitment, or fabrication
evidence. A quality-passing mesh and measured 935 installation geometry are
still required before CFD or release claims.

The [weak-cell locator](localize_weak.py) checks all 4,915,307 tetrahedra and
finds that **all 1,169** cells with mean ratio below 0.01 touch a rotor-wall
node; none touches the outer duct. Its top and side views show concentrations
at the inner annulus and selected blade roots. This localizes the remaining
shape problem but does not prove whether the surface triangles or the 3D fill
caused it. The complete private cell indices, ratios, centres and figure are
retained for the next local mesh experiment.

The [exact face-incidence audit](audit_wall_faces.py) then found that 1,109 of
the 1,169 weak cells share a complete rotor boundary triangle. Those incident
rotor triangles have median normalized quality 0.1876, versus 0.8121 for all
rotor triangles; 404 of the 1,748 incident faces are below 0.1. Under the
conditional scale, 961 weak-cell centres have radius 70–100 mm. This makes
the inner annulus and blade-root wall facets a specific target for a
triangulation study with an independent scan-envelope bound; association
does not prove cause.

An otherwise matching Gmsh trial changed `Mesh.Algorithm3D` from 1 to 4
(Frontal). It reached a 900-second wall limit during volume generation, with
no mesh output. Its source and full log are retained privately. This is a
resource-bound incomplete trial, not a measured Frontal mesh comparison.

The earlier 32-edge-flip candidate, whose separate scan-envelope audit had
passed, was also meshed with the same Delaunay settings. Its complete
independent audit preserved all 895,732 boundary triangles but found 1,248
tetrahedra below mean ratio 0.01, versus 1,169 for the unmodified rotor. The
minimum ratio fell from `2.71e-5` to `5.29e-6`; the sub-0.05 count rose from
1,769 to 1,863. This candidate is rejected for this volume-mesh route. No
native OpenFOAM check or CFD solve was run on the worse candidate.

## Gmsh-specific facet targeting

The [flip-overlap audit](audit_flip_overlap.py) maps every Gmsh rotor triangle
back to its retained source-face identifier using all three vertex coordinates.
It found a maximum coordinate mismatch of `5.62e-17` m and a bijection for all
878,730 rotor faces. Only **2 of the 1,169** weak Gmsh tetrahedra share a rotor
face touched by the earlier 32-flip candidate. The earlier candidate was
chosen from weak *TetGen* cells, so its worse Gmsh result does not establish
that local surface repair cannot help this mesher.

The [Gmsh-targeted proposal](propose_targeted_flips.py) instead starts with
the 1,748 source faces incident to weak Gmsh cells, including 404 with
normalized triangle quality below 0.1. It found 106 geometrically eligible
edge-flip pairs and selected 32 disjoint pairs without moving vertices. This
is a candidate selection, not a validated fluid or manufacturing geometry.
The private candidate has SHA-256
`f6c8029795d830264496d6760fbafb9863a03335e9efb893f630161dc2c332a6`.
A full bidirectional CGAL envelope check on Kali1 passed over all 878,730
triangles at the existing 0.0225 uncalibrated-source-unit bound. Volume-mesh
quality and native OpenFOAM checks remain separate gates.

With the private baseline mesh and original rotor OFF in their documented
`work/` paths, reproduce the mapping and proposal as follows:

```sh
uv run --no-project --python 3.12 --with gmsh==4.15.2 \
  --with numpy==2.5.4 --with scipy==1.18.1 --with trimesh \
  python twins/935-horizontal-cooling-system-f0/source/gmsh-fluid-study-20261028/audit_flip_overlap.py

uv run --no-project --python 3.12 --with numpy==2.5.4 --with trimesh \
  python twins/935-horizontal-cooling-system-f0/source/gmsh-fluid-study-20261028/propose_targeted_flips.py
```

The first script writes only private face identifiers and a JSON receipt. The
second writes the private OFF candidate and its receipt. The public Git tree
contains neither scan vertices nor the candidate mesh.

The matched Gmsh 4.15.2 Delaunay run on this candidate produced 4,852,988
positive tetrahedra. The independent audit confirmed all 895,732 boundary
triangles and four patch groups to a maximum coordinate difference of
`9.62e-17` m. However, its mean-ratio count below 0.01 was **1,236**, compared
with 1,169 for the unchanged rotor; below 0.05 it was 1,819 versus 1,769.
The minimum remained approximately `2.71e-5`. This second 32-flip candidate
is **rejected**. The result suggests that isolated edge flips do not remove
the root-region volume-fill difficulty under the current meshing settings.
It does not establish that a larger, scan-bounded local surface remesh or a
different conforming volume strategy will fail. No CFD solve or native
OpenFOAM acceptance check was run on this worse candidate.
The private evidence archive is
[`935-gmsh-targeted-flips-20261028.tar.zst`](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-gmsh-targeted-flips-20261028.tar.zst),
SHA-256 `a04528da2666e63ddbf1d15a92982766d0c354b69ad4f39da59ae1b476bb6602`.

## Alternative 3D algorithms on the unchanged PLC

The [Gmsh 4.15.2 manual](https://gmsh.info/doc/texinfo/) identifies HXT
(`Mesh.Algorithm3D=10`) and R-tree (`=9`) as alternative 3D algorithms. Three
private runs kept the same 895,732-triangle PLC and nominal size
settings and Gmsh version. HXT with the existing built-in volume stopped
after boundary recovery with `Invalid volume tag 1 in mesh size calculation`
(process exit 134). Replacing that volume with a discrete volume did not
solve the interface issue: Gmsh exited normally but reported **zero**
tetrahedra. Neither output is a fluid mesh. The
[private HXT scripts and logs](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-gmsh-hxt-interface-trial-20261028.tar.zst)
were downloaded and matched SHA-256
`c644e1d0fc350ddd7714b47f36a3ee9241dfe57766295fac0a53895d8b9a0020`.

R-tree with the original volume reached boundary recovery, then stopped with
`Requesting more near neighbors than data points` (exit 1); it produced no
volume. Its [private source and log](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-gmsh-rtree-failure-20261028.tar.zst)
were downloaded and matched SHA-256
`3733e9ca722f9eeba50de702c8a7873cd34f33bb03c8f2ede1e5b93754b4d7ad`.
These failures are specific to this discrete-surface setup and inputs; they
do not measure the general quality of HXT or R-tree. The remaining numerical
route is a scan-bounded local surface reconstruction or an independently
verified conforming volume workflow. No CFD result is available yet.
