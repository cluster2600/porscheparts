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
