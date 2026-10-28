# 935 corrected-rotor CFD mesh: rejected uniform level-4 trial

The [uniform level-3 trial](UNIFORM_SURFACE_LEVEL_TRIAL_20261028.md) removed
most fine surface cells but lost rotor shape near the outer radius. This
controlled opposite bound changes only the rotor `refinementSurfaces.level`
from `(3 4)` to `(4 4)`. It retains the corrected PicoGK rotor, block mesh,
near-surface distance refinement, snapping settings, quality thresholds and
native OpenFOAM Foundation 13 runtime. The baseline is the same spacing-3
case used in the previous trial.

The baseline [native case](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-spaced3-rejected-20261028.tar.gz)
has SHA-256 `dec99a42ca61d290d89bf116f83ff583fd4afd4c46d386f7a42d58724be09b41`.
The [new private case](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-level44-rejected-20261028.tar.gz)
has SHA-256 `693ad93790eb576a1dc3f786bd83483968cc6cebc5d879abb8ae0d95b332b48b`.
The baseline [boundary export](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/parent-boundary.stl.gz)
has SHA-256 `4f7fba20703cf431153dd79379b1dfa934b666c0fceb949ba035c9a2fc01d624`.
The native run used the same 8 GiB address-space and 1,200-second command
limits. These files and the report were hash-matched after transfer to the
private release; raw geometry remains outside public Git.

| Native result | Baseline `(3 4)` | Uniform `(3 3)` | Uniform `(4 4)` |
|---|---:|---:|---:|
| Final cells | 708,822 | 243,822 | 907,500 |
| Concave cells | 46,584 | 13,535 | 50,261 |
| Concave-cell fraction | 6.57% | 5.55% | 5.54% |
| Full `checkMesh` failures | 1 | 1 | 1 |
| New `snappyHexMesh` duration | — | 89.7 s | 442.7 s |
| Rotor-wall unique vertices | 182,672 | 56,567 | 225,155 |
| Wall → rotor vertex-to-triangle p95 | 0.220 mm | 0.245 mm | 0.223 mm |
| Wall → rotor maximum | 0.543 mm | 1.098 mm | 0.393 mm |
| Rotor → wall vertex-to-triangle p95 | 0.126 mm | 0.107 mm | 0.135 mm |
| Rotor → wall maximum | 0.575 mm | 2.547 mm | 0.575 mm |

Distances assume the still-unverified conversion of one source unit to one
millimetre. Every unique vertex was queried against opposing triangles in both
directions; these results do not bound triangle-interior error or calibrate the
scan. A smaller wall-to-rotor maximum under `(4 4)` does not make the mesh
admissible because the full native quality check still fails.

The new `cellLevel`, `owner`, `neighbour` and `concaveCells` files place
**49,173 of 50,261 concave cells (97.8%)** adjacent to a refinement transition.
The lower-level side of the 3/4 interface contains 36,827 concave cells; the
2/3 interface contains another 8,805. This is adjacency evidence, not proof
that the transition operation alone created each defect. The `(3 3)` case
removed the 3/4 interface but was still poor at 2/3 and lost outer-radius
fidelity. Uniform `(4 4)` preserves detail but retains a large 3/4 interface.

The [pinned comparator](../../../twins/935-horizontal-cooling-system-f0/source/snap-resume-study-20261025/compare_surface_level4.py)
uses the shared [native and wall audit](../../../twins/935-horizontal-cooling-system-f0/source/snap-resume-study-20261025/compare_surface_level.py).
It checks the three input hashes, the one-line dictionary change, complete
`checkMesh` logs, rotor-wall distances and transition topology. The previous
`(3 3)` report was reproduced byte-for-byte after sharing the audit code. The
new [private JSON report](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/level44-comparison-001.json)
has SHA-256 `1c9678ffcb3be6245f6641bbde6d08c7aaa5126fb50b7fe47c9102b856a966e6`.
Run with `numpy`, `scipy`, `trimesh` and `rtree` after restoring the private
inputs under `work/`:

```sh
python3 \
  twins/935-horizontal-cooling-system-f0/source/snap-resume-study-20261025/compare_surface_level4.py \
  work/935-cfd-concavity-20261028/935-spaced3-rejected-20261028.tar.gz \
  work/935-uniform-level4-20261028/935-level44-rejected-20261028.tar.gz \
  work/935-snap-tolerance-20261028/parent-boundary.stl.gz \
  work/935-uniform-level4-20261028/comparison-NEW.json
```

Uniform `(4 4)` is **rejected for CFD**. Neither uniform bound satisfies both
rotor-wall fidelity and native mesh quality. The next meshing study must
change how transitions are constructed or placed, while preserving the
fine rotor surface; no MRF, SST, airflow, pressure or torque result is inferred.
