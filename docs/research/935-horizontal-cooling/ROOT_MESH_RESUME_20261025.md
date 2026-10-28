# 935: guarded root correction and actual mesh reconstruction

The resumed programme has a locally corrected PicoGK rotor and a working
Foundation 13 reconstruction step. The corrected surface passes the complete
independent intersection check. The fluid mesh still fails full native quality.
**No new airflow, operating-strength or manufacturing approval results.**

The [numerical receipt](root-mesh-resume-20261025.json) pins sources and results.
The [22 October pause checkpoint](HEX_MESH_CONTINUATION_20261022.md) is unchanged.
The active goal resumed on 25 October. Kali1 SSH was recovered over Thunderbolt
IPv6 using its existing trusted identity. No new paid instance was created.

## Correct the inferred roots

A tree–cotree audit locates twelve independent cycles on the retained analysis
surface, whose genus is six. These are a topological basis, not twelve physical
openings. Five small passages occur at inferred blade-root/cup junctions in the
missing blade-root region; the central bore is retained. The method follows
the [surface homology construction](https://jeffe.cs.illinois.edu/teaching/comptop/2023/notes/22a-homology.html).
Sphere, torus winding, unsigned-index, large-index and malformed-surface controls
exercise the implementation. Every vertex link must be one circle.

The existing native root-screening program first showed that revoxelization
alone changes the topology. That route remains diagnostic because it also
changes the reference surface outside the repair. The retained correction
instead inserts a guarded addition into a fresh copy of the original C# recipe,
before its first mesh export.

The zero-closing control reproduces the original STL **byte for byte**:
`f32bbabab3e5f7d9ca7c5283d18703cfe7cedbd3eb2c72a57a1c222c0a9df1e5`.
PicoGK Core 26.2.0, its managed assembly, the original recipe and SDF helper are
pinned. Original files are never edited. The
[C# fragment](../../../twins/935-horizontal-cooling-system-f0/source/snap-resume-study-20261025/root-repair-fragment-002.cs.txt)
retains only added occupancy in r = 25…95 and z = −30…40 source units.

| Closing parameter | Surface result | Decision |
|---|---|---|
| 0 | Original genus six, 1,322,970 triangles | Exact reproduction control |
| 0.6 source unit | Genus one, 660,003 vertices, 1,320,006 triangles | Geometric candidate retained |
| 1.2 source units | Native export completes; independent closure check fails | Refused |

The 0.6 candidate closes the five inferred passages. Independent comparison
preserves exactly **544,882 triangles touching r ≥ 98** and **83,376 triangles
touching r ≤ 24**, including coordinates. These guards compare with the original
PicoGK reconstruction, not directly with raw scans or measured hardware.
The pinned CGAL 6.2.1 check finds **zero self-intersection pairs** on the complete
candidate, with counts matching the independent indexed readback. Closed, open
and intersecting tetrahedral controls respectively pass, fail closure and
detect intersections on the current native runtime.

Candidate STL:
`ee8f91167f6147edd125b2b4db9da65a5704aac95879a82f2aab6bada779f9ed`.
The closing parameter is a voxel operation, not a measured historical fillet
radius. Cup, root closures, scale and installation remain hypotheses. The
private before/after figure renders every triangle; orange marks triangle
identity changes, including retessellation, rather than displacement or stress.

## Conditional mass update

Triangle integration gives 431,013.601 source units cubed, an increase of
348.031, or **0.080812%**, from the original master. Native added-field volume
is a different voxel estimator and is not substituted for surface integration.
Masses assume **one source unit equals one millimetre** and reuse ten frozen
screening cards. Mass scales with the cube of any later length calibration.
WE43 uses the existing surrogate density, not a qualified LPBF allowable.

| Existing card | Conditional mass, kg |
|---|---:|
| AlSi10Mg | 1.151 |
| AlF357 | 1.151 |
| WE43 | 0.789 |
| Ti-6Al-4V | 1.896 |
| 316L | 3.405 |
| 17-4PH | 3.340 |
| IN718 | 3.513 |
| CoCr MP1 | 3.577 |
| Maraging M300 | 3.448 |
| CuCrZr | 3.793 |

The receipt also retains centroid and inertia integrals. No new stress, fatigue,
balancing, speed limit or material-selection approval is supplied. These need
calculations on the revised geometry and process-specific data.

## Fix Foundation 13 reconstruction

The four-rank snapping run finishes ten morph iterations in 1,786.87 s. Its
parent run finishes in 1,915.09 s. It uses the previously saved analysis
geometry, **not the new root candidate**, and requests no boundary layers.

`reconstructParMesh` in the pinned Foundation 13 runtime prints a deprecation
message and returns zero without reconstructing a mesh. An existing global
mesh therefore lets a subsequent `checkMesh` inspect the previous mesh. The old
static cube proved parallel quality and coordinate exports, but did not prove
reconstruction after a processor mesh change. That narrower reconstruction
claim is withdrawn here; frozen receipts remain unchanged.

The [new control](../../../twins/935-horizontal-cooling-system-f0/source/snap-resume-study-20261025/qualify-reconstruction-002.py)
moves every processor point by 0.125 along x, copies no global mesh and removes
copied processor addressing in its fresh case. The legacy command returns zero
and creates no mesh. `reconstructPar -constant -noFields -noSets -noLagrangian`
then recovers all **343 expected coordinates exactly**; full native cube quality
passes. The source cube stays unchanged.

The [real reconstruction](../../../twins/935-horizontal-cooling-system-f0/source/snap-resume-study-20261025/reconstruct-snap-002.py)
also starts without global mesh primitives or stale addressing. It retains only
the identical scalar `level0Edge` reference needed to reconstruct refinement
metadata. The preceding trial, which omitted that reference, is retained with
its fatal-error log. The corrected run completes in 141.83 s and preserves all
source inputs.

## Fluid-mesh result and next work

The real reconstructed case contains **4,666,166 cells, 6,056,698 points and
15,223,252 faces**. Its rotor wall has 1,083,640 polygons and 1,249,452 points.
Global hashes and counts differ from the saved pre-snap case. The full command
remains:

```sh
checkMesh -case /workspace -allGeometry -allTopology -meshQuality
```

The quality dictionary remains
`bafbc5ced7e83c5a1cc11291a0937c3499a6713e8e3411a83f93464381ba2c7d`.
Cell volumes are positive; maximum non-orthogonality is 69.9843 degrees,
maximum skewness 3.99798, minimum interpolation weight 0.0557474 and minimum
cell determinant 0.00134483. Nevertheless, the complete check reports
**316,996 concave cells and one failed mesh check**. It also warns about
**two duplicate non-baffle faces**. Both findings remain unresolved.

No solver runs on this refused mesh. Complete addressed point readback,
wall/volume fidelity, layers and three-grid convergence remain open. The next
mesh must use the corrected rotor hash, locate the remaining concavity and
duplicate-face causes, and pass the same full checks. Measured interfaces,
hidden transmission, historical shroud and engine installation remain separate
open work. PhysicsNeMo has no newly accepted fan dataset.

## 28 October: native concavity localization on Kali1

Kali1 was reached over its existing IPv6 Thunderbolt address. A **new copy** of
the rejected `reconstructed-snap-002` case retained the original six input-file
hashes and unchanged `meshQualityDict` SHA-256
`bafbc5ced7e83c5a1cc11291a0937c3499a6713e8e3411a83f93464381ba2c7d`.
OpenFOAM 13 build `13-18870c24d21c` ran the same complete check with
`-writeSets -writeSurfaces`. The utility exited zero but its log still says
**one failed mesh check**, **316,996 concave cells**, and two duplicate
non-baffle faces. The exit code is not treated as quality acceptance.
`postProcess -func writeCellCentres -constant` then wrote centre coordinates
for all **4,666,166** cells in this copied case.

The [localization program](../../../twins/935-horizontal-cooling-system-f0/source/snap-resume-study-20261025/localize_concave_cells.py)
checks the copied and parent input hashes, parses the native `concaveCells` set
and centre field, and walks internal owner/neighbour faces from cells touching
the rotor wall. Every cell is counted once in the radial and axial summaries.

| Internal-face graph hops from rotor wall | New cells | New concave cells | Cumulative share of concave cells |
|---:|---:|---:|---:|
| 0, touches rotor | 1,058,173 | 18,549 | 5.85% |
| 1 | 1,053,943 | 18,257 | 11.61% |
| 2 | 959,045 | 45,515 | 25.97% |
| 3 | 591,902 | 115,587 | 62.43% |
| 4 | 384,529 | 52,372 | 78.95% |
| 5 | 210,252 | 25,142 | 86.89% |
| More than 5 | 408,322 | 41,574 | 100% |

Only 410 concave-cell centres lie outside the conditional axial slab
−0.05 to +0.05 m, but almost all cells are refined inside that slab. The
**relative** failure rate is 1.75% among rotor-touching cells, 19.53% in the
third graph ring, and 10.18% beyond five rings. This points to the volume
and refinement transition as a candidate for the next controlled meshing
experiment; it does not prove the causal algorithm or exempt the rotor surface
from independent fidelity checks. No CFD result is admitted.

The [private plot](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/concavity-localization-final.png)
and [numerical report](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/concavity-localization-final.json)
were downloaded with SHA-256 respectively
`776d78baa00d210d865098d69e917668e55eba0c8101da177171568da4f2df27`
and `f402d4acd40f7ad3ffc545209ec0d610bf7facaff709c58ab2b7ceecb2bab56c`.
The [private native archive](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-concavity-diagnostic-final-20261028.tar.gz)
includes the centre field, cell set, logs, receipts, program copy and results;
its downloaded SHA-256 is
`163a1f19e3a57c1351b2f1ac7f470c344cff789f5c52e238b055b1f2177fbe76`.
It excludes the unchanged 1.2 GB mesh, which remains in the earlier native
checkpoint and on Kali1. The program is run against that restored copied case
with a new private output directory:

```sh
python3 twins/935-horizontal-cooling-system-f0/source/snap-resume-study-20261025/localize_concave_cells.py \
  /home/lolman/935-snap-resume-20261025/concavity-localization-001 \
  /home/lolman/935-snap-resume-20261025/NEW-concavity-map
```

## Reproduction and retention

### Native refinement-transition correlation, 28 October

The [follow-up program](../../../twins/935-horizontal-cooling-system-f0/source/snap-resume-study-20261025/correlate_concavity_refinement.py)
uses the unchanged rejected case, its native `cellLevel` list, the checked
`concaveCells` set and internal owner/neighbour faces. It independently verifies
the copied mesh inputs and partitions all 4,666,166 cells. A transition-adjacent
cell shares at least one internal face with a cell at a different native
refinement level. The largest observed level jump is one.

| Group | Cells | Concave cells | Concave fraction |
|---|---:|---:|---:|
| Adjacent to a level change | 2,381,357 | 311,850 | 13.095% |
| No adjacent level change | 2,284,809 | 5,146 | 0.225% |

Thus **98.38% of rejected cells** are transition-adjacent, though 51.03% of
all cells are in that group. Level 4 contains 154,307 rejected cells, the
largest count by level. These are correlations on the **old rotor** mesh; they
do not identify which OpenFOAM operation caused each concavity. In particular,
5,086 rejected level-6 cells have no adjacent level change. The next controlled
experiment should compare two new meshes of the **same corrected PicoGK rotor**,
varying only transition spacing, then run full native `checkMesh` and a
wall-fidelity audit on both. This report admits no CFD solver result.

The [private figure](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/refinement-correlation-final-20261028.png)
and [numerical report](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/refinement-correlation-final-20261028.json)
have downloaded SHA-256 values
`1a7e1acef231292c72d82e424199dc89c5c87454045ff26175964d11360c1b31`
and `a692599e7563b92a2828497bfc28a56198a77127e1982fdbcbfaa9251622ad4f`.
The [private native archive](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-refinement-correlation-final-20261028.tar.gz)
contains the level list, rejected-cell set, execution receipt, exact program
copy and outputs; downloaded SHA-256 is
`2381076a92e4087e76b17fe4493fe5c15034f9130aba52f47ca3e302dede3db0`.
Its other mesh inputs are retained in the previous native checkpoint. To
reproduce after restoring that copied case on Kali1:

```sh
python3 twins/935-horizontal-cooling-system-f0/source/snap-resume-study-20261025/correlate_concavity_refinement.py \
  /home/lolman/935-snap-resume-20261025/concavity-localization-001 \
  /home/lolman/935-snap-resume-20261025/NEW-refinement-correlation
```

The [experiment snapshots](../../../twins/935-horizontal-cooling-system-f0/source/snap-resume-study-20261025/)
are executed recipes, not another coordinator. Preserve originals and derive
new copies with fresh private output paths for another attempt. Restore private
dependencies first. Mac geometry uses the qualified Python 3.12 environment;
`hashlib.file_digest` requires Python 3.11 or later.

```sh
TASK_PYTHON=work/935-complete-system-20261022/geometry-venv/bin/python
export PYTHONPATH=twins/935-horizontal-cooling-system-f0/source
"$TASK_PYTHON" -m unittest discover -s tests -p 'test_935*.py'
```

Sources retain pin checks, immutable-input checks, bounded native jobs, fresh
outputs and refusal results. The private
[release](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
holds geometry and native mesh checkpoints with per-file manifests. Repeated
native-case files refer to identical archived payloads; no case file is dropped.
The receipt records local and server verification. Raw scans and derived images
remain private. Public Git contains sources, tests, reduced numerical receipts
and this English report.

## 28 October: matched transition-spacing trial on the corrected rotor

Two fresh Foundation 13 cases used the same **root-0.7 PicoGK rotor** OBJ
(`ee9357d46911fc0112342626064f7e731395af9db9a8bc340793cf22effb24a6`),
surface refinement levels 3/4, 1.5 million-cell configured limit, snapping on,
layers off and the same quality dictionary SHA-256
`bafbc5ced7e83c5a1cc11291a0937c3499a6713e8e3411a83f93464381ba2c7d`.
The only difference between the two final `snappyHexMeshDict` files is
`nCellsBetweenLevels`: 3 versus 5. Both ran in Kali1's existing rootless
OpenFOAM 13 runtime with an 8 GiB virtual-memory limit and a 1,200-second
timeout. Each `snappyHexMesh` finished without its own error; the full
`checkMesh -allGeometry -allTopology -meshQuality -writeSets -writeSurfaces`
then rejected **both** with one failed check. Exit code zero from `checkMesh`
was not taken as acceptance.

| Input spacing | Snap time | Final cells | Concave cells | Concave fraction | Rotor patch faces | Cell cap reached |
|---:|---:|---:|---:|---:|---:|---|
| 3 | 569.8 s | 708,822 | 46,584 | 6.572% | 164,263 | No |
| 5 | 919.3 s | 1,303,737 | 49,778 | 3.818% | 174,266 | Yes |

The [independent comparison program](../../../twins/935-horizontal-cooling-system-f0/source/snap-resume-study-20261025/compare_root0p7_spacing.py)
verifies matching rotor and quality-input hashes, confirms that the two
snappy dictionaries differ only in spacing, parses both native logs, and reads
the actual rotor-patch owner-cell levels. At spacing 3, 15,406 rotor faces
border level-3 cells and 148,857 border level-4 cells; at spacing 5 the counts
are 11,514 and 162,752. This establishes the **nominal levels present** at
the wall, not a bounded distance from that wall to the scanned surface.

The lower rejected-cell fraction at spacing 5 is accompanied by 3,194 more
concave cells, 594,915 more total cells, a longer run, and a hit on the
configured cell cap. It does **not** establish a quality-passing improvement
or isolate the effect at equal resolved fidelity. Both cases remain refused;
no MRF/SST solver or airflow curve was run. The next mesh study needs enough
cell budget to avoid clipping the intended transition, a direct wall-distance
audit, and an independent strategy for the remaining concavity.

Private readback hashes for the
[spacing-3 case](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-spaced3-rejected-20261028.tar.gz),
[spacing-5 case](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-spaced5-rejected-20261028.tar.gz),
[comparison archive](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-spacing-comparison-20261028.tar.gz),
[JSON report](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/spacing-comparison-final-20261028.json)
and [figure](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/spacing-comparison-final-20261028.png)
are, respectively,
`dec99a42ca61d290d89bf116f83ff583fd4afd4c46d386f7a42d58724be09b41`,
`8cd471d0394212deaa821262075e52dcdd7e3314c6ef65a8989a3460ef55d185`,
`d2f96a3f120e66258f5320cd3cc51bdcdf839ffef937c93b2c286052a74aa579`,
`066cbf6a1d7e3642d62a934377097d2df97700ea485828fc05141a7fbc29fd45`
and `9a338818823e6c2ce27d72638101a6dfd81ffe30efc2748460a9906105778cf9`.
The case archives include the generated meshes, native logs, inputs and exact
preparation/execution/check scripts. The comparison archive contains the
program copy and outputs. No scan or derived geometry is in public Git.

## 28 October: corrected-rotor wall-vertex distance audit

Foundation 13 `foamToSurface -constant -tri` exported the boundary from a
**new copy** of each rejected root-0.7 case. The `solid rotor` group was
extracted separately; the other duct, inlet and outlet groups were excluded.
The spacing-3 and spacing-5 rotor-wall STL SHA-256 values are
`d1d56bd0f3dc7bafbfd83cb3b11629037c640c1c1736b0780aec012fa5e63d79`
and `2458f4877b0d6c3bb50b8906ba9f0c08d8e3215d65545a6d584bfa63a6acc7ee`.
Both are compared with the same corrected rotor OBJ hash given above.

The [vertex audit](../../../twins/935-horizontal-cooling-system-f0/source/snap-resume-study-20261025/audit_root0p7_wall_vertices.py)
uses exact closest-point queries to the opposing **triangles** for every
unique vertex, in both directions. Distances below assume the conditional
conversion of one source unit to one millimetre; that scale has not been
calibrated to the original 935 component.

| Spacing | Wall vertices | Wall → rotor p95 / max | Rotor vertices | Rotor → wall p95 / max |
|---:|---:|---:|---:|---:|
| 3 | 182,672 | 0.220 / 0.543 mm | 439,365 | 0.126 / 0.575 mm |
| 5 | 193,617 | 0.220 / 0.408 mm | 439,365 | 0.129 / 0.575 mm |

The maximum rotor-to-wall distance occurs at the same rotor vertex in both
cases, at conditional SI coordinates
`(-0.1380872, -0.0258405, 0.0102432)` m, near the outer radius.
These are exhaustive **vertex-to-triangle** distances, not a mathematical
bound on distances from the interiors of all triangles. Neither the true
scan-to-reconstruction error nor the 935 installation dimensions are proved.
The meshes still fail native quality; no CFD is admitted. The figure plots
20,000 rotor vertices for display, while the numerical audit checks all
vertices.

The [private JSON report](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/wall-vertex-distances-final-20261028.json),
[figure](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/wall-vertex-distances-final-20261028.png)
and [native audit archive](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-wall-vertex-audit-20261028.tar.gz)
have downloaded SHA-256 values
`8513c1bcb46d85a71e0c9fbe01c3a50feaefb704ea812d3d8822daf6b2e685a7`,
`12b3a8588f1938d2e6330825c23927d796083da53a8a024c9d5d1eee89230f0a`
and `a562eb67f53357d424f283f6be96c71a8d68476ebba7b6bc65aac080dcd840c9`.
The archive contains both wall STLs, the corrected rotor OBJ, the native export
logs, the source copy, the JSON, the figure and per-vertex distance arrays.
The source hash recorded in the report is
`77f7ceb55a5e605eabe776287aeb614ac16cb16f45013a0325ed55a1caf76470`.

## 28 October: topology of the two corrected-rotor mesh failures

The [topology audit](../../../twins/935-horizontal-cooling-system-f0/source/snap-resume-study-20261025/compare_root0p7_concavity.py)
reads the native `concaveCells` sets, cell refinement levels, and internal
owner/neighbour faces from both rejected meshes above. It verifies the case
inputs and native receipts before counting. A cell is *transition-adjacent*
when at least one internal face joins it to a cell of a different refinement
level. This is a graph classification, not a determination of the meshing
operation that created the defect.

| Spacing | Transition-adjacent concave / cells | Other concave / cells | Share of all concave cells at transitions |
|---:|---:|---:|---:|
| 3 | 45,507 / 355,476 (12.80%) | 1,077 / 353,346 (0.305%) | 97.69% |
| 5 | 48,688 / 409,930 (11.88%) | 1,090 / 893,807 (0.122%) | 97.81% |

At each level-change interface, the concave cells touching that interface are
on the lower-level side. The 3/4 interface contributes 31,523 concave cells
with spacing 3 and 34,610 with spacing 5. Increasing spacing therefore did
not remove the dominant defect: it added 3,194 concave cells while moving
more of them farther from the rotor wall in the internal-face graph. This
localizes the next investigation to refinement transitions; it does not prove
that the transition algorithm alone causes concavity. Both full native
`checkMesh` results remain failed, so neither mesh is admitted to CFD.

The [private JSON](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/concavity-topology-final-20261028.json),
[figure](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/concavity-topology-final-20261028.png),
and [native archive](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-concavity-topology-20261028.tar.gz)
have download-verified SHA-256 values
`8e5ebf02b6ea86ed4a8e11f77e9609bb3bd0cbf102dd327c4d690779168eef9a`,
`90933dadf3325301ba01bcf4a66b0f4d49e5903062cd6646003b6c41be688d05`,
and `7a676c78b180208d1469d778d0723e63ce60fd28a76e77335d447d0f924f7ec8`.
The report records source SHA-256
`846863313ef1c7e8280f89ea4f8bc8621654d2c1f2341456e2467ac8ab897233`.

## 28 October: direct conforming Gmsh fluid-volume trial

The [reproducible Gmsh study](../../../twins/935-horizontal-cooling-system-f0/source/gmsh-fluid-study-20261028/README.md)
uses the **same** corrected-rotor fluid PLC as the TetGen trials above:
`boundary.npz` SHA-256
`9fcd93a5c54ebfc98b8cd86d4550e3a416d3e62fb217e5ebfb67eb2f2a9f2085`.
Gmsh 4.15.2 was run natively on the Apple Silicon Mac. Four discrete surface
entities preserve the inlet, outlet, exploratory duct and rotor markers; the
fluid volume uses the rotor surface as an interior void. The outer duct is
still **not** a measured 935 carter, and its SI scale is conditional.

The completed Delaunay volume has 1,029,194 nodes and 4,915,307
tetrahedra. An [independent full-volume audit](../../../twins/935-horizontal-cooling-system-f0/source/gmsh-fluid-study-20261028/audit_fluid.py)
found every tetrahedron positively oriented, with volume sum
`0.05140884014124352` m³. Every one of the 895,732 source boundary triangles
and all four patch labels is preserved by coordinate-set comparison; the
maximum nearest boundary-node difference is below `1e-16` m. This is mesh
boundary preservation, **not** scan accuracy or confirmed 935 fitment.

| Volume | Tetrahedra | Mean ratio < 0.01 | Mean ratio < 0.05 | Native OpenFOAM quality |
|---|---:|---:|---:|---|
| TetGen `-O5` | 3,714,547 | 2,929 | 43,964 | Not admitted |
| Gmsh Delaunay | 4,915,307 | 1,169 | 1,769 | Failed seven checks |

The two volumes have different cell counts; these bins are diagnostic, not a
grid-convergence or solver comparison. A Gmsh `optimize("Netgen")` pass on the
saved volume left all measured shape counts unchanged. OpenFOAM Foundation 13
could not read the Gmsh 4.1 file directly; a small control established that
its `gmshToFoam` accepts ASCII MSH 2.2. The full converted file SHA-256 is
`5bf08e05e7f25fdddccbedd81245258a43d489b7c53dc85e4cf7a09626b9f422`,
verified again after transfer to Kali1. The rootless native import recovered
4,915,307 tetrahedra and four patches. Full native
`checkMesh -constant -allGeometry -allTopology -meshQuality -writeSets
-writeSurfaces` found one region and volume `0.051408840141249142` m³, but
reported **seven failed mesh checks**: 58,976 severely non-orthogonal faces,
54,127 cells with determinant below 0.001, 839 high-aspect-ratio cells,
70 highly skew faces, 4 concave cells, and additional interpolation and volume
ratio failures. Its exit code was zero despite the failed checks. Thus this
candidate remains **rejected for CFD**, with no MRF/SST solve or airflow
claim. The next mesh must pass the complete native gate and a multi-grid
study before the intended simulations can proceed.

The [private Gmsh volume bundle](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-gmsh-root0p7-volume-evidence-20261028.tar.zst)
contains the original PLC, both Gmsh encodings, full numerical audits,
execution logs and source copies. Its downloaded SHA-256 is
`c6cf8560235773f618d0bcc1cd5e03f35a202c3af75e48b33f277ba3b2bfee56`.
The [private native OpenFOAM bundle](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-gmsh-root0p7-openfoam-native-20261028.tar.zst)
contains the converted `polyMesh`, case controls, logs and execution receipts;
its downloaded SHA-256 is
`d4f5e95175deb93aba667ec47c8fbf71dc24cc72c7055a495aae540f0095dd6d`.
Both download hashes match the uploaded local archives. No geometry from
either bundle is committed to public Git.

The [full weak-cell localization program](../../../twins/935-horizontal-cooling-system-f0/source/gmsh-fluid-study-20261028/localize_weak.py)
found that **all 1,169** tetrahedra below mean ratio 0.01 touch rotor-wall
nodes; none touches the outer duct. In the
[private top/side figure](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/gmsh-root0p7-weak-cells-20261028.png),
their centres cluster at the inner annulus and selected blade roots. This is
a location, not proof of whether the wall facets or near-wall volume fill
caused the poor shapes. The [private JSON](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/gmsh-root0p7-weak-localization-20261028.json)
and [complete cell data](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/gmsh-root0p7-weak-cells-20261028.npz)
have downloaded SHA-256 values
`9362b1635a60d660041da290ffc4606167b42000c3c8c1d5aaf9194a65575473`
and `bdcfde4eef36e39d9e2efa29c464e3e6ab5d7db8588a4398eb4f02717070f7a4`;
the figure has downloaded SHA-256
`0e1e2bc42defac49c7a959603874957d878a6154514f6aefd355f6793579c910`.

The [exact rotor-face incidence audit](../../../twins/935-horizontal-cooling-system-f0/source/gmsh-fluid-study-20261028/audit_wall_faces.py)
shows that 1,109 of the 1,169 weak cells share a complete rotor boundary
triangle. The 1,748 incident rotor faces have median normalized triangle
quality 0.1876, compared with 0.8121 over all rotor faces; 404 incident
faces are below 0.1. Under the unverified scale, 961 weak-cell centres lie
at radial distance 70–100 mm. This prioritizes an inner-annulus/blade-root
facet study with an independently checked scan-envelope bound. It does not
establish whether the wall facets or volume-filling algorithm caused each
bad cell.
The [private face-audit receipt](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/gmsh-root0p7-wall-face-audit-20261028.json)
has downloaded SHA-256
`3d5bafb00eb9e0ea1ff572ab69597accb3a7e3613e79f9c2e5d1d4709a961f2e`.

A second Gmsh 4.15.2 trial changed the 3D algorithm from Delaunay (1)
to Frontal (4), retaining the same PLC and nominal size settings. It reached
the 900-second wall limit while generating the volume, produced no mesh, and
its process exited. There is no quality comparison with Frontal. The
[private source/log archive](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-gmsh-frontal-timeout-20261028.tar.zst)
and [timeout receipt](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/gmsh-root0p7-frontal-timeout-receipt-20261028.json)
have downloaded SHA-256 values
`576b8c13dfea80969443d855637ff21ad0676da7c98672c67d6e1b8a33b7bccc`
and `6d386ede2a21dc9c7299b6ff1dcd0e6ada6cd9bc65d92d66cfe654548f579882`.

The previously envelope-checked 32-edge-flip rotor candidate was then passed
through the **same** Gmsh Delaunay settings as the baseline. Both complete
audits preserved their respective 895,732 input boundary triangles. The
flipped volume has 4,765,504 positive tetrahedra, with 1,248 below mean
ratio 0.01 versus 1,169 in the unmodified volume. Its minimum ratio fell
from `2.71e-5` to `5.29e-6`, and the sub-0.05 count rose from 1,769 to
1,863. The candidate is **rejected** for this route; no native OpenFOAM
check or CFD solve was run on the inferior volume. The
[private full trial](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-gmsh-flipped32-evidence-20261028.tar.zst)
and [comparison receipt](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/gmsh-flipped32-comparison-20261028.json)
have downloaded SHA-256 values
`60b34de0b4cb43dc4c7e6804a48db31b56dccf1cbb9f0c7dca4902768eaf49af`
and `0c027000b145522495993cb2d2bcbf68580cc6a3ca4f6bb059f6770e61383c80`.
This does not rule out other local surface reconstructions; every new
candidate must again pass envelope, topology and volume-quality checks.

The next study matched the weak Gmsh cells to source rotor faces by exact
triangle connectivity after coordinate mapping. Only **2 of 1,169** weak
Gmsh cells touched one of the earlier 32 flipped pairs. A new selection
targeted the Gmsh incident faces directly. Its 32 disjoint flips passed the
complete bidirectional CGAL envelope check on Kali1 at the retained 0.0225
uncalibrated-unit bound. The matched Gmsh volume nevertheless worsened to
**1,236** cells below mean ratio 0.01 and **1,819** below 0.05, from 1,169
and 1,769 in the unmodified baseline. The 4,852,988 tetrahedra were positive
and all boundary triangles were preserved, but this candidate is **rejected**.
The [private full trial](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-gmsh-targeted-flips-20261028.tar.zst)
was downloaded and matched SHA-256
`a04528da2666e63ddbf1d15a92982766d0c354b69ad4f39da59ae1b476bb6602`.
The [reproducible mapping and proposal](../../../twins/935-horizontal-cooling-system-f0/source/gmsh-fluid-study-20261028/README.md)
remain public without private mesh data. A bounded local remesh of the
annulus/blade-root region, or a conforming volume strategy that resolves the
near-wall fill, is the next numerical experiment; no airflow result is
accepted yet.

Two other Gmsh 4.15.2 algorithms were probed on the unchanged PLC.
HXT (`Mesh.Algorithm3D=10`) stopped with a volume-tag error when using the
built-in volume; an alternative discrete volume produced zero tetrahedra.
R-tree (`=9`) stopped after boundary recovery with an ANN near-neighbor
error. Neither created a fluid volume, so neither has a quality or CFD
comparison. The private scripts and logs are archived and hash-verified;
the [reproduction notes](../../../twins/935-horizontal-cooling-system-f0/source/gmsh-fluid-study-20261028/README.md)
give the exact results and evidence links. These trials do not alter the
accepted/rejected status of the original Delaunay mesh.

A further [protected-surface short-edge sweep](../../../twins/935-horizontal-cooling-system-f0/source/gmsh-fluid-study-20261028/README.md#protected-surface-short-edge-sweep)
tested CGAL edge limits of 0.001, 0.005 and 0.020 uncalibrated source units.
The best 0.001 case reduced Gmsh mean-ratio-below-0.01 cells from 1,169 to
910, and below-0.05 cells from 1,769 to 1,429, with all input boundary faces
preserved. Native OpenFOAM 13 still reported **seven failed mesh checks**;
CFD remains blocked. Larger edge limits worsened volume quality relative to
the 0.001 case even though they improved surface triangle quality. The CGAL
bound applies only between each repaired surface and the protected analysis
surface; it does not establish an original-scan bound, verified scale, or
935 fitment. The inner annulus and blade-root wall remain the main observed
weak-cell concentration.
