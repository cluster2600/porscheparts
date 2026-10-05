# Prospective D1 preparation — snapshot before execution

This document describes preparation before launch. The
[current result](D1_EXECUTION.en.md) reports the completed control and interrupted
strict branch, without admission. At the date of this preparation, the batch
awaited explicit coordinated release of Kali2. The Ti pilot retains its window;
no D1 solver, container or mesh copy was launched. Small V2/900 dictionaries
were read-only and cross-checked against the private native archive: eight
files, 8027 bytes. Fields and mesh remain on their original resource.

## Comparison frozen before calculation

The [prepared-pair manifest](parameters/D1-prepared-pair-manifest.json)
links nine 900-checkpoint files, thirteen constant files, prepared
configurations and sources. The two branches are:

| Branch | Pressure GAMG relTol | Absolute tolerance | p relaxation | Iterations |
| --- | ---: | ---: | ---: | --- |
| control | 0.01 | 10⁻⁸ | 0.15 | 901–960 |
| absolute | 0 | 10⁻⁸ | 0.15 | 901–960 |

Model, physical conditions, CAD, mesh, other tolerances and original criteria
are unchanged. The future executor copies the same 900 state, verifies copy
hashes, decomposes once and copies the same initial MPI partition into both
branches before the first solver. Cases are sequential. It reruns no failed
case.

Checkpoints have interval 60 and the three flow/force functions interval 1.
The admission window requires twenty measurements at 941–960. The prospective
report also requires all sixty measurements for its three windows:
901–920, 921–940, 941–960. p/U/turbulence residuals, mass, flow/torque stability,
direction and complete finite fields remain required at original thresholds.
The expected 453496-cell count is linked to the native 900 field summary.

Each window reports mean, standard deviation, min/max and CV where the mean
is nonzero: Qin/Qout, total torque, initial and final linear p residual,
global continuity. Differences between final branch means and their CVs are
descriptive. These steady-iteration variations are not physical noise,
independent observations, a confidence interval or a rotor frequency.
No significance threshold is adjusted after calculation. A newly admitted
diagnosis never restores missing historical fine-grid measurements or
retroactively restores fine R0 admission.

## Bounded future execution

The launcher is [launch_d1_pair.py](source/launch_d1_pair.py), with an
[isolated executor](source/run_d1_in_container.py). It uses only the already
available frozen Foundation 13 image, without networking or download:
4 CPU, cpuset 0/2/4/5, 5 GiB RAM and memory+swap, tasks at nice 10.
It requires 6 GiB available at admission and rejects another container of
this image. The overall ceiling is 600 s, including preparation/copies;
container work is capped at 580 s, each MPI at 270 s, without extension.
The launcher reserves time to stop only its named container on timeout,
then preserves logs and receipts. No third-party service is touched.
Estimate: 4–6 min; ceiling: 10 min. Native execution of these new helpers is
not yet verified: that verification awaits the window.

After release and transfer of the local preparation capsule, the Kali2 command
will have the following form. This block documents future execution; it was
not executed.

```sh
python D1_CAPSULE/source/launch_d1_pair.py NATIVE_V2_900_CASE D1_CAPSULE NEW_D1_OUTPUT --coordinated-release COORDINATOR_RELEASE_REFERENCE
```

To reproduce only local preparation, without solver or mesh:

```sh
python source/prepare_d1_configurations.py NATIVE_SMALL_CONFIG SOURCE_IDENTITY_JSON NEW_CONFIG_OUTPUT
```

## Visible subsystems, dimensions pending

The [qualitative contract](parameters/qualitative-subsystem-contract.json)
distinguishes four subsystems to document before functional reconstruction:
installed plenum, front pulley/belt train, ribbed support and observed
central envelope. All parameters and interfaces are unknown (`null`).
The video confirms only a general layout; it measures no diameter, ratio,
attachment axis, material or tolerance. R0 remains an analytical rotor,
housing and transmission; its own model supplies none of the new subsystems'
missing measurements. No new dimensioned geometry or fit evidence is generated.

The [exact publication supplied by the parent](https://www.instagram.com/patrickmotorsports/reel/DeC4x04yjNP/)
claims a “935 3.5L Flat Fan MoTeC EFI” assembly and a 993 6-speed transaxle;
this identifies neither the engine base as 993 nor fan equivalence.
Third-party images remain private. Public engine research is not duplicated here.
