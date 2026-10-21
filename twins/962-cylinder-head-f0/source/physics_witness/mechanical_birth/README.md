# Mechanical material birth and support release

**Hypothetical numerical verification only. No head, alloy or LPBF calibration.**
The synthetic card uses mm, MPa, N and K, E=1000 MPa, nu=0, perfect J2 yield
1 MPa and alpha=1e-5/K. No parameter is a manufacturing allowable.

Two equal 10 mm segments form a 1 x 1 x 20 mm serial bar with four HEX8
elements. Segment A is initially active. It loads to 0.003 strain, accumulating
plastic strain diag(-0.001,-0.001,0.002), then unloads to 0.0025 strain.
At time 3, B activates into the existing affine displacement field. Shared
displacements and A's material history remain; B's incremental material
strain/stress/plastic state starts at zero. The former internal axial support
is removed and the new end is held at 0.05 mm. Uniform cooling to 260 K follows
at time 4. Removing the end support at time 5 releases the bar quasistatically;
only the base and rigid-motion constraints remain.

| State | Axial stress in active segments (MPa) | End displacement (mm) |
| --- | ---: | ---: |
| Initial | 0 | 0 |
| A plastic preload | 1 | 0.030 |
| A elastic unload | 0.5 | 0.025 |
| B born, serial equilibrium | 0.25 | 0.050 |
| Cool with end held | 0.65 | 0.050 |
| Release and subsequent hold | 0 | 0.037 |

The reference first applies the uniaxial J2 return, then equal-section force
equilibrium and total serial extension. At release A's axial strain is 0.0016
and B's physical axial strain is 0.0021. B's incremental strain is relative to
its birth field, rather than its total gradient relative to the original mesh.
A retains its plastic tensor; B remains unplasticized. Quasistatic release
does not verify a transient dynamic energy balance.

All geometry, seven states, complete nodal and tensor reference tables,
event order and tolerances were frozen before execution. Pinned
[primary semantics](primary-semantics.json) distinguish official source
inspection from the independently hash-checked installed binary. The native
runtime has read-only rootfs, no network, 2 GiB RAM, no swap, two CPU quota and
a 100 s deadline. Attempt 001 refused input setup before any timestep because
global displacement coupling reached the inactive placeholder kernel.
Attempt 002 only overrides that inherited coupling to empty. The card,
references, tolerances and original assessor are identical across both freezes.

The six equilibrium solves in attempt 002 completed in 0.668 s. The original
assessor passed 5514 numerical comparisons. They include every active nodal
displacement and reaction-force component, pre-step old/shared/new nodal
histories, and all six symmetric components of stress, plastic strain,
mechanical strain and total strain at **every** 2x2x2 Gauss point. A value-only
AD-to-real conversion exposes those exact quadrature properties without cell
averaging. Independent boundary reactions match axial stress times unit area
and balance at every state. Maximum errors are 1.11e-14 mm displacement,
2.71e-15 strain, 6.00e-13 MPa stress and 3.67e-13 N force.

The input, frozen assessor, original assessment and native artifacts remain
unchanged. A later guard hardening requires all consumed files in the native
manifest, exact integer IDs, all eight distinct Cartesian Gauss locations and
the independently retained original SSH capture/receipt digests. Current and
frozen checker hashes are reported separately. Rehashing a modified CSV and
native receipt cannot pass the retained-result check. No native solve was
repeated for checker hardening.

The [public capsule](../../../derived/engineering/mechanical-birth-witness/README.md)
contains exact CSV fields and clean log, freezes, source snapshots, assessments
and safe hash projections. Its example reproduces numerical comparisons.
Complete original capture authentication also requires the private retained
bundle; public hash-only projections do not reproduce transport contents.

With the retained private bundle present, use a fresh assessment filename:

```sh
python3 -B twins/962-cylinder-head-f0/source/physics_witness/mechanical_birth/assess.py \
  work/962-engineering/moose-mechanical-birth-001/attempt-002 \
  --contract work/962-engineering/moose-mechanical-birth-001/frozen-contract-002.json \
  --output /path/to/new-assessment.json
```

To perform a distinct reproduction on an existing Linux runtime, use
`run_local.py --rootfs /path/to/runtime/rootfs --output /path/to/new-directory`.
It does not install or download software. It freezes and checks new inputs,
runs once and reproduces numerical comparisons with its own local receipt;
it does not claim to recreate the original SSH transport. This portable
wrapper is later code and has not repeated the retained native solve.
Its current hardened version executes `/opt/moose/bin/moose-opt` explicitly
and rejects changed runtime/input hashes or missing equilibrium solves before
field comparison. The capsule preserves the earlier wrapper snapshot.

The original native attempt used bare `moose-opt` after sourcing `/environment`.
It recorded the expected target binary hash and matching source banner, rather
than an original process `execve` record. A separately retained, read-only
postrun resolution probe confirms that this startup resolves `moose-opt` to
the checked `/opt/moose/bin/moose-opt` hash. That corroborates current runtime
resolution; it is not original process attestation. The
[later wrapper/probe addendum](../../../derived/engineering/mechanical-birth-wrapper-hardening-001/README.md)
keeps this boundary separate from the immutable numerical evidence.

Whole-head meshing, coupled build history, physical calibration, annealing,
supports/contact/process validation and manufacturing authorization remain open.
