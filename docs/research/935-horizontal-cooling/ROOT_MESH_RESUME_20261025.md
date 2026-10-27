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
