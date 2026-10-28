# 935 inspection USD: one provisional rotor revolution

This checkpoint extends the [four-component inspection assembly](ORIGINAL_BOUND_ASSEMBLY_20261028.md)
and the [eight PicoGK flange witnesses](USD_FLANGE_WITNESS_20261028.md)
with an inspectable rotor revolution in USD. It uses the same original-export-
bounded PicoGK rotor mesh and the already reviewed 240-phase rigid surface
sweep. This is a **kinematic preview**, not a physical joint, operating model,
or installed 935 digital twin.

## Construction and verification

The [USD composer](../../../twins/935-horizontal-cooling-system-f0/source/compose_kinematic_usd.py)
pins the two input USD layer hashes, the four-component and eight-witness
identities, and the rigid-sweep report SHA-256
`656c15ff50002192f9df19d2ba2c2888e9666f2471ffd6b5bc5c9f85aab60146`.
It preserves the base and composed USD layers byte for byte and adds one
stronger layer, `kinematic-inspection.usdc`, with a Z-rotation override on
`/World/rotor_candidate`. The stage has 241 time samples, frames 0–240, in
1.5° steps, closing the revolution at 360°. The arbitrary 60 frames per
second is for preview playback only; it is **not a fan speed**.

The new stage is reopened and checked for Z-up, metres-per-unit, its component
and witness identities, and all time samples. An independently calculated
rotation of a rotor vertex agrees with every authored USD transform; the
largest readback difference is `1.25e-16` m (rounded upward). The source
coordinates remain uncalibrated. The USD layer uses the pre-existing assumed
factor of `0.001` from source unit to stage metre solely for display.

The pinned rigid sweep reports positive continuous **surface-separation
bounds** of 1.95136 source units against the observed drive and 4.37637
source units against the provisional shroud. Those bounds apply only to the
frozen surfaces, assumed Z axis and relative pose. They do not establish a
shaft-to-hub joint, occupied-volume clearance, thermal running clearance,
structural safety, or installation on a 935 engine.

The [four-pose renderer](../../../twins/935-horizontal-cooling-system-f0/source/render_kinematic_usd.py)
reads the authored USD angles and plots sampled original component triangles
at 0°, 90°, 180° and 270°. The [private preview image](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/kinematic-four-poses.png)
has SHA-256 `0f11c04bbb7f5c0014c5ec2c59a401a60dfdf873a514833bc0849abe8be3cbea`.
Its XY projection overlaps components at different Z levels; use the 3D
surface sweep for the stated separation result.

## Reproduce and private package

With the pinned private USD and sweep inputs restored, use fresh output
directories under ignored `work/`:

```sh
uv run --no-project --python 3.12 --with usd-core --with numpy==2.5.4 python \
  twins/935-horizontal-cooling-system-f0/source/compose_kinematic_usd.py \
  work/935-usd-flange-witness-20261028/composed-002 \
  work/935-original-bound-assembly-20261028/sweep-002.json \
  work/935-kinematic-usd-20261028/composed-NEW

uv run --no-project --python 3.12 --with usd-core --with numpy==2.5.4 \
  --with matplotlib==3.10.7 python \
  twins/935-horizontal-cooling-system-f0/source/render_kinematic_usd.py \
  work/935-original-bound-assembly-20261028/native-002 \
  work/935-kinematic-usd-20261028/composed-NEW \
  work/935-kinematic-usd-20261028/render-NEW
```

The [private self-contained archive](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-kinematic-inspection-20261028.tar.zst)
contains all three USD layers, the composition and render reports, and the
preview image. Its SHA-256 is
`1d649592bda872e33892fdef6091fbf8f3d519d1d1bec43acbe3f551fc128ac9`;
`zstd -t` passed. The authored kinematic USD SHA-256 is
`5a6c2651a0b4ccc78ca68ea2b9a778d04b608de8f82b100d24190de7bf0b020b`.
All private geometry remains outside public Git.

The next physical-twin gate is the measured rotor-to-output coupling, shaft
axis, supports and engine mounting faces, followed by independently calibrated
units. A real revolute joint, inertia and loads can then be assigned to the
verified components rather than to this display animation.
