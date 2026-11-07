# Fan control: final fields recovered without a solver restart

For [issue #453](https://github.com/cluster2600/porscheparts/issues/453), all
eight global control files at iteration 2000 have been reconstructed from the
32 retained partitions. **Every file matches its original worker SHA-256 and
size exactly.** This restores the saved state; it does not improve convergence.

The [October backup account](../../../twins/993-engine-cooling-fan-system-f0/program/EXECUTION_20261003.md#final-field-backup)
correctly records that the original transfer was interrupted and reconstruction
had not then been attempted. Its historical records remain unchanged. This
new recovery uses the surviving partition files, not the incomplete global
file or a fresh simulation. The candidate's final fields remain unavailable
in that backup.

## Execution and independent comparison

All 897 recovered source files were rehashed against the historical recovery
manifest: 5,891,292,356 bytes, zero mismatches. A fresh native Linux staging
directory received 675 required files (2,509,625,828 bytes), including all 256
final partition files. Every staged file was checked before and after execution.

The retained Foundation 14 image ran `reconstructPar -case /case -time 2000
-noLagrangian -noSets`, after sourcing `/opt/openfoam14/etc/bashrc`. Its build
is `14-a4867fc914c1`; the original solver used `14-7b05503f98a8`. Same-family
compatibility was not assumed sufficient: the original worker manifest was
the independent byte-level comparison target.

The case inputs were mounted read-only, with a separate writable output
directory. Limits were two CPUs, 8 GiB, 128 processes, a 600-second timeout,
128 MiB temporary storage and a 1,048,576,000-byte per-file output limit.
Networking was disabled. The utility completed in 5.272 seconds, exit zero,
without timeout or OOM. No `foamRun` command was executed.

An initial container launch failed before execution because the nested output
mountpoint did not exist in the read-only case. Creating an empty mountpoint
in the staged copy corrected that launch; the failed attempt is retained.
Historical source bytes did not change.

The [comparison and execution identities](result.json) and
[native reconstruction log](reconstructPar.log) record the result. The seven
fields `U`, `Uf`, `k`, `nut`, `omega`, `p`, `phi`, plus `uniform/time`, match
all eight original hashes. A second private copy on the Mac was independently
rehashed against the same worker manifest. Raw fields remain outside Git.

## Saved-state wall diagnostic

The recovered control also permits a native `foamPostProcess -solver
incompressibleFluid -func yPlus -time 2000` diagnostic. The seven saved fields
and `uniform/time` were mounted read-only and rehashed afterwards; no solver
time step ran. The same image completed in 16.967 seconds within two CPUs,
8 GiB and a 180-second timeout, with no network or OOM. New outputs used a
separate directory and a 512 MiB per-file limit.

| Wall patch | Faces | Minimum y+ | Median y+ | Maximum y+ | Mean y+ |
|---|---:|---:|---:|---:|---:|
| Rotor | 624,557 | 0.004717 | 13.4731 | 64.0132 | 12.9116 |
| Duct | 552,960 | 0.207832 | 1.29537 | 22.8119 | 1.82263 |

Independent binary64 readback checks the field layout and patch sizes, all
1,177,517 wall values are finite and nonnegative, and both patches' minimum,
maximum and arithmetic mean agree with the native output. The
[independent result](yplus-result.json) preserves quantiles and descriptive
interval counts; those intervals are not acceptance limits. The
[native diagnostic log](yplus.log) records model selection and patch statistics.
The original `nutkWallFunction` and `omegaWallFunction` settings are unchanged.
This is a wall-resolution diagnostic of the unconverged control, not an
accepted wall treatment or a mesh-independence study.

## Remaining acceptance gates

The existing independent auditor was rerun on both retained native receipt
sets and reproduced both historical audit results exactly. Both cases still
fail velocity and pressure residual limits and torque amplitude. Final mass
balance and flow drift pass their individual limits; they do not establish
overall convergence. The [unchanged validation plan](../../../twins/993-engine-cooling-fan-system-f0/program/VALIDATION_PLAN.md)
still requires two complete 100-iteration windows, qualified wall treatment
and mesh independence. Those acceptance gates remain open.

The restored control can now support field diagnostics without recalculating
its first 2000 iterations. Candidate recovery or regeneration remains separate.
The isolated uncalibrated rotor is not an installed engine assembly; measured
interfaces, fan/system curves and physical correlation remain unresolved.
No paid compute, physical qualification or issue closure is claimed.
