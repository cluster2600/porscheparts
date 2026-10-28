# 935 corrected-rotor CFD mesh: rejected uniform surface-level trial

The [native concavity-topology audit](ROOT_MESH_RESUME_20261025.md#28-october-topology-of-the-two-corrected-rotor-mesh-failures)
found 31,523 concave cells adjacent to the 3/4 refinement interface in the
spacing-3 baseline. This trial changes one line in `snappyHexMeshDict`: the
rotor surface level from `(3 4)` to `(3 3)`. The corrected PicoGK rotor, block
mesh, near-surface distance refinement, snap settings, quality thresholds and
Foundation 13 runtime are unchanged. It tests whether removing surface level 4
helps mesh quality, while checking the resulting loss of rotor-wall fidelity.

The baseline [native case](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-spaced3-rejected-20261028.tar.gz)
has SHA-256 `dec99a42ca61d290d89bf116f83ff583fd4afd4c46d386f7a42d58724be09b41`.
The [new rejected case](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-level33-rejected-20261028.tar.gz)
has SHA-256 `62b9411a409c56513a82575c7a8039e6a4c203173d89b5827e06555f412033be`.
Both native cases include inputs, the complete volume mesh and quality logs;
the new archive also includes the exported boundary STL. The baseline
[boundary STL](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/parent-boundary.stl.gz)
has SHA-256 `4f7fba20703cf431153dd79379b1dfa934b666c0fceb949ba035c9a2fc01d624`.
The transferred files match their private-release digests. No raw scan or
derived rotor mesh is committed to public Git.

| Native result | Surface `(3 4)` | Surface `(3 3)` |
|---|---:|---:|
| Final cells | 708,822 | 243,822 |
| Concave cells | 46,584 | 13,535 |
| Concave-cell fraction | 6.57% | 5.55% |
| Full `checkMesh` failures | 1 | 1 |
| New `snappyHexMesh` duration | — | 89.7 s |
| Rotor-wall unique vertices | 182,672 | 56,567 |
| Wall → rotor vertex-to-triangle p95 | 0.220 mm | 0.245 mm |
| Wall → rotor maximum | 0.543 mm | 1.098 mm |
| Rotor → wall vertex-to-triangle p95 | 0.126 mm | 0.107 mm |
| Rotor → wall maximum | 0.575 mm | 2.547 mm |

The distance values are **conditional** on the unverified
one-source-unit-to-one-millimetre scale. Every unique rotor and wall vertex was
queried against opposing triangles, but triangle-interior extrema and the scan's
physical scale remain unverified. The worst rotor-to-wall vertex in the new
case is at conditional coordinates `(0.017700, -0.133710, 0.024900)` m, near
the outer rotor radius. The reduction in overall cell count does not justify
this larger local geometric error.

The new native `cellLevel`, `owner`, `neighbour` and `concaveCells` files show
that **13,265 of 13,535 concave cells (98.0%)** still touch a refinement-level
transition. The 2/3 interface contributes 9,377 concave cells on its lower
side, with another 2,879 at 1/2 and 1,009 at 0/1. These counts classify
adjacency; they do not prove which meshing operation caused each bad cell.

The [independent comparator](../../../twins/935-horizontal-cooling-system-f0/source/snap-resume-study-20261025/compare_surface_level.py)
checks archive and unchanged-input hashes, the exact one-line dictionary
change, native quality logs, complete rotor-wall vertex distances and the
remaining transition topology. Its [private JSON report](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/level33-comparison-001.json)
has SHA-256 `262721448af04d0190f4fa90b36694936b0e8eff11b14fc2df986acc118b36c0`.
Run it with `numpy`, `scipy`, `trimesh` and `rtree` after restoring the three
private inputs under `work/`:

```sh
python3 \
  twins/935-horizontal-cooling-system-f0/source/snap-resume-study-20261025/compare_surface_level.py \
  work/935-cfd-concavity-20261028/935-spaced3-rejected-20261028.tar.gz \
  work/935-uniform-surface-20261028/935-level33-rejected-20261028.tar.gz \
  work/935-snap-tolerance-20261028/parent-boundary.stl.gz \
  work/935-uniform-surface-20261028/comparison-NEW.json
```

The uniform level-3 surface is **rejected for CFD**: the full native gate still
fails and rotor-wall fidelity worsens at the outer radius. It yields no MRF,
SST, flow, pressure or torque result. The next study should preserve fine
surface detail where the rotor requires it and change the location or shape of
refinement transitions, with the same native quality and wall-distance gates.
