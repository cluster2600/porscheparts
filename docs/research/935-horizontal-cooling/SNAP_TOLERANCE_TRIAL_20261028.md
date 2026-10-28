# 935 corrected-rotor CFD mesh: rejected snap-tolerance trial

The [patch-smoothing trial](SNAP_SMOOTHING_TRIAL_20261028.md) showed that
doubling `nSmoothPatch` did not remove the concave-cell failure. This trial
instead reduced `snapControls.tolerance` from `2.0` to `1.0` on the earlier
`nSmoothPatch=5` case. [OpenFOAM defines this tolerance](https://doc.cfd.direct/openfoam/user-guide-v10/snappyhexmesh)
as the attraction distance divided by the local maximum edge length. The
corrected PicoGK rotor, block mesh, surface refinement, quality thresholds,
other snap settings and Foundation 13 runtime were unchanged.

The baseline archive SHA-256 is
`dec99a42ca61d290d89bf116f83ff583fd4afd4c46d386f7a42d58724be09b41`.
The [private new case archive](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-tolerance1-rejected-20261028.tar.gz)
has SHA-256 `5ce390801d28af9590affc0e41f382eeb82a936320450c5cef39ceacf9876c63`.
It contains the native run script, complete case, boundary export and logs.
The baseline [boundary export](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/parent-boundary.stl.gz)
has SHA-256 `4f7fba20703cf431153dd79379b1dfa934b666c0fceb949ba035c9a2fc01d624`.
All three transferred files were hash-matched against their private GitHub
assets. Raw geometry remains outside public Git.

| Native result | Tolerance 2.0 | Tolerance 1.0 |
|---|---:|---:|
| Final cells | 708,822 | 708,822 |
| Concave cells | 46,584 | 46,643 |
| Failed full `checkMesh` checks | 1 | 1 |
| New `snappyHexMesh` duration | — | 528.2 s |
| Rotor-wall unique vertices | 182,672 | 182,636 |
| Wall → rotor vertex-to-triangle p95 | 0.220 mm | 0.220 mm |
| Wall → rotor maximum | 0.543 mm | 0.543 mm |
| Rotor → wall vertex-to-triangle p95 | 0.126 mm | 0.125 mm |
| Rotor → wall maximum | 0.575 mm | 0.537 mm |

The distance values assume a **conditional** one-source-unit-to-one-millimetre
conversion. They measure every unique vertex against the opposing triangles in
both directions, but do not bound error over all triangle interiors or verify
the original scan's physical scale. The baseline rotor-wall result agrees with
the earlier [wall audit](ROOT_MESH_RESUME_20261025.md#28-october-corrected-rotor-wall-vertex-distance-audit).

The [independent comparator](../../../twins/935-horizontal-cooling-system-f0/source/snap-resume-study-20261025/compare_snap_tolerance.py)
verifies the three artifact hashes, unchanged input files, exact one-line
dictionary change, native logs, rotor-wall extraction and all vertex distances.
Its [private JSON result](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/tolerance-comparison-001.json)
has SHA-256 `3a8bb0870f2d54722edde50f809338bb5b75644e5d9ca8694410231e4ca7d48c`.
The pinned comparison runs with `numpy`, `scipy`, `trimesh` and `rtree`:

```sh
python3 \
  twins/935-horizontal-cooling-system-f0/source/snap-resume-study-20261025/compare_snap_tolerance.py \
  work/935-cfd-concavity-20261028/935-spaced3-rejected-20261028.tar.gz \
  work/935-snap-tolerance-20261028/935-tolerance1-rejected-20261028.tar.gz \
  work/935-snap-tolerance-20261028/parent-boundary.stl.gz \
  work/935-snap-tolerance-20261028/comparison-NEW.json
```

The lower attraction distance slightly improves the worst sampled rotor-to-wall
distance, while adding 59 concave cells. The full native `checkMesh` gate still
fails. **The case is rejected for CFD**, and no MRF, SST, flow, pressure or torque
result follows from it. The next meshing experiment should alter the
near-wall refinement topology or transition placement with an independent
wall-fidelity check; another unmotivated snap-parameter sweep would not address
the localized transition evidence.
