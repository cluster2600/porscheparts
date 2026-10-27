# 935 hub space: conditional PicoGK geometry

This study places a separate PicoGK annulus in the unresolved space between the
observed 935 drive output and the reconstructed rotor bore. It is a **visual
occupancy envelope**, not a hub, coupling, fitted part, or historical replica.
The source-unit-to-millimetre scale, shaft identity, full circumference, torque
transfer, axial retention, tolerances, and hot clearances remain unverified.

## Input and candidate

- The four-band radial [screen](../../../twins/935-horizontal-cooling-system-f0/source/corrected-analysis-20261025/screen_hub_radial_window.py)
  is pinned by SHA-256 `05d52829fa35394fa017ae3ae9c5aae98f8d36468e52d17ba3b71db1517a2b36`.
- The retained PicoGK rotor and observed drive STL fingerprints are respectively
  `5522ec1af957a4523244bc2b2f05ff902b52eb882e1cb3b2ef88b093ffb598eb`
  and `fbae73f9c7182eebe5d0da5d4af991c42e06a59edd145d85f3221c128e7cef35`.
- The [PicoGK generator](../../../twins/935-horizontal-cooling-system-f0/source/picogk-hub-space/Program.cs)
  uses provisional radii 7.9 and 11.1 source units, axial interval −20 to 0,
  and voxel size 0.15 source units. Its runtime reports PicoGK 26.2.0. The
  millimetre labels in the native receipt assume 1 mm/source unit solely for
  the geometry generator; they are **not calibration evidence**.

## Independent review

The [review program](../../../twins/935-horizontal-cooling-system-f0/source/picogk-hub-space/review_hub_space.py)
checks the native STL with Trimesh and both observed surfaces with FCL. The
retained mesh has 301,984 triangles, is watertight with consistent winding and
Euler number 0, and its mesh volume is 3,818.21 provisional cubic units. That
is 0.052% below the ideal analytic annulus volume. At the retained cold pose,
the minimum triangle-surface distances are 0.27894 source units to the drive
and 0.35355 to the rotor. These positive gaps deliberately mean **no mechanical
connection**. They also do not exclude hidden interior overlap, motion,
thermal expansion, or a protrusion in the unscanned half of the drive.

Three PicoGK trials are retained privately:

| Inner radius, source units | Independent finding | Decision |
|---:|---|---|
| 7.5 | Watertight; crosses an observed drive triangle near z ≈ −5 | Reject |
| 7.8 | No observed surface crossing; native STL fails watertight review | Reject |
| 7.9 | Watertight; no crossing of the two observed surfaces at this pose | Retain for visual study only |

The [four-band image](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/hub-space-four-band-final.png)
shows the scanned drive arc, reconstructed bore, and visual annulus in each
axial band. Its SHA-256 is
`b28ace95a210e7ebec015dfc761d5efa833e9bf2e3b6afdeb27dd69f34b8561a`.
The [private archive](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-hub-space-trials-20261027.tar.gz)
contains all three native meshes and receipts, FCL results, image, and trial
summary; downloaded SHA-256 is
`2294cde48a0b2bcc8320d689dc47bbaf09525cec6a912d6b6732d9339f82d5a6`.

## Reproduce

On an Apple Silicon Mac with .NET 9 and the pinned PicoGK runtime, set
`PICOGK_DLL` to the local PicoGK assembly and `PICOGK_RUNTIME` to its native
library directory. Use new directories under ignored `work/`:

```sh
dotnet build twins/935-horizontal-cooling-system-f0/source/picogk-hub-space/HubSpace.csproj \
  -c Release -p:PicoGKAssembly="$PICOGK_DLL" -o work/NEW/bin
DYLD_LIBRARY_PATH="$PICOGK_RUNTIME" dotnet work/NEW/bin/HubSpace.dll \
  work/935-assembly-0p7-20261025/hub-radial-window-final-20261027.json \
  work/935-assembly-0p7-20261025/six-run-001/rotor_candidate.stl \
  work/935-assembly-0p7-20261025/six-run-001/drive_observed.stl \
  work/NEW/native
uv run --no-project --python 3.12 --with numpy==1.26.4 \
  --with python-fcl==0.7.0.10 --with trimesh==4.9.0 python \
  twins/935-horizontal-cooling-system-f0/source/picogk-hub-space/review_hub_space.py \
  work/NEW/native work/935-assembly-0p7-20261025/six-run-001 \
  work/NEW/surface-review.json
```

The native STL and scan-derived results remain private. No manufacturing or
safe-speed claim follows from this study. The next assembly task is to measure
the actual shaft and rotor attachment surfaces, identify a torque path and
axial retention, then replace this empty visual space with a documented
coupling design.
