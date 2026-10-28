# 935 corrected-rotor CFD mesh: rejected patch-smoothing trial

The [matched refinement-spacing study](ROOT_MESH_RESUME_20261025.md#28-october-matched-transition-spacing-trial-on-the-corrected-rotor)
left a 708,822-cell `snappyHexMesh` case with 46,584 concave cells and one
failed native mesh check. This follow-up tests one controlled change on Kali1:
`snapControls.nSmoothPatch` increases from 5 to 10. The corrected PicoGK rotor,
block mesh, surface refinement, other snapping parameters, quality dictionary,
rootless OpenFOAM Foundation 13 runtime, and conditional unit convention are
unchanged. It is a numerical trial, not a physical-scale calibration.

The parent case archive SHA-256 is
`dec99a42ca61d290d89bf116f83ff583fd4afd4c46d386f7a42d58724be09b41`.
Its 48,528,932-byte rotor OBJ SHA-256 is
`ee9357d46911fc0112342626064f7e731395af9db9a8bc340793cf22effb24a6`;
the unchanged `meshQualityDict` SHA-256 is
`bafbc5ced7e83c5a1cc11291a0937c3499a6713e8e3411a83f93464381ba2c7d`.
The native script and complete new case are in the
[private rejected-trial archive](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-smooth10-rejected-20261028.tar.gz),
SHA-256 `05b9405f30e3eec09eed8d02fa6f8e6b86d3afe19930ded9665440762c048d59`.
The archive was copied from Kali1 to the Mac, listed locally, and its digest
matched the GitHub asset digest. Both archives retain their raw input and
output geometry privately.

The [independent archive comparison](../../../twins/935-horizontal-cooling-system-f0/source/snap-resume-study-20261025/compare_smooth_patch.py)
checks both archive hashes, all common system files, the exact one-line
dictionary difference, native `snappyHexMesh` completion and the full
`checkMesh` logs. A synthetic parser fixture also runs before comparing the
native evidence. Its [private JSON report](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/comparison-001.json)
has SHA-256 `c185c6174902f4bbc193e909aefa99f63754c8f539f15a6858a87a017d6496fa`.

| Native result | `nSmoothPatch=5` | `nSmoothPatch=10` |
|---|---:|---:|
| Final cells | 708,822 | 708,822 |
| Concave cells | 46,584 | 46,669 |
| Small-determinant cells | 0 reported | 79 |
| Low interpolation-weight faces | 0 reported | 2 |
| Failed full `checkMesh` checks | 1 | 3 |
| New `snappyHexMesh` duration | parent receipt: 569.8 s | 856.2 s |

`snappyHexMesh` printed “Finished meshing without any errors” for the new
case, but `checkMesh` found three failures. This setting therefore **does not
improve the CFD admission state**. No MRF, SST, flow, pressure, or torque result
is inferred. A zero `checkMesh` process exit code would not override its
reported failed checks. The next controlled meshing attempt should address
near-wall topology or the snap/transition interaction while retaining a direct
wall-fidelity audit and all quality gates.

With the two private archives restored under `work/`, reproduce the comparison
with a fresh report path:

```sh
python3 \
  twins/935-horizontal-cooling-system-f0/source/snap-resume-study-20261025/compare_smooth_patch.py \
  work/935-cfd-concavity-20261028/935-spaced3-rejected-20261028.tar.gz \
  work/935-snap-smooth-20261028/935-smooth10-rejected-20261028.tar.gz \
  work/935-snap-smooth-20261028/comparison-NEW.json
```
