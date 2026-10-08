# Local Qwen / PicoGK rerun — tunnel, October 2, 2026

An executed geometric study, **not a finished monocoque**. The new run takes up
the assumptions of the [published concept](https://github.com/cluster2600/porscheparts/blob/135dcc8ef6e71ac483e1ed3036217536562c80a1/twins/993-carbon-safety-cell/design-space.json),
without rebuilding or modifying the scan, the measured interfaces or the
historical evidence. The earlier CAD and simulations are kept.

## Result

Qwen2.5-Coder-1.5B-Instruct 4-bit with the Mac adapter
`coding-003/checkpoint-600` reproduced exactly the three requested cylinders:
coordinates, radii and flat ends. This is a **constrained transcription**,
not autonomous design, new learning or a measurement.
`coding-007`, seen in training at the start of this rerun and then at status
`no_validation_improvement`, did not replace the retained checkpoint.
LM Studio, which requires authentication, was not used.

PicoGK rebuilds five local volumes: the two tunnel walls, the cover, the nose and
the tunnel floor strip. The positions are taken from the concept's `build_cad.py`,
whose dimensions are **hypothetical**. Its earlier section checks did not cover
the longitudinal collisions or the one with the lever tower.

| Envelope against the initial tunnel | Intersection at 4 mm (mm3) | At 2 mm (mm3) | Analytical calculation (mm3) |
|---|---:|---:|---:|
| C2 shift linkage | 0 | 0 | 0 |
| C4 central tube against the nose | 670,614 | 670,408 | 671,515 |
| C4 guide against the nose | 30,111 | 30,294 | 30,561 |
| C2 lever tower against the cover | 965,291 | 985,619 | 990,000 |

Two meshes do not demonstrate general convergence: the central tube error does
not decrease monotonically. All three interferences are found at both
resolutions, with a maximum volume deviation from the analytical value of 2.50%
at 4 mm and 0.88% at 2 mm. These deviations are not manufacturing tolerances.

The variant subtracts these envelopes from the nose and the cover. The residual
is zero on each same grid, **by construction**, with zero additional clearance.
The probes for the front passage, the service opening and the walls conform to
the requested model. No inference is drawn about stiffness, fatigue or fire
resistance. An opening in the cover still requires a hatch and seal design;
a passage through the nose requires reinforcements, protection and a review of
the load paths.

The [rerun receipt](../../derived/qwen-picogk-tunnel-20261002.json) keeps the
Qwen responses, the native reports, the inputs and the digests. The STL files and
the sections stay in `work/qwen-picogk-monocoque-20261002/`, with no raw scan.
`tunnel-relief-study.stl` is a derivative; the editable master is `Program.cs`
with the JSON parameters, not a production STEP/BREP.

## Reproduce with the environments already installed

Every output directory must be new. No weight download, training, server change,
Vast rental or arbitrary Qwen code is executed. The Qwen output is checked by the
PicoGK parser already used for training; only the numbers compared exactly are
passed to C#.

```sh
MONO_TRAIN=/Users/maxime/.codex/worktrees/m64-local-architecture-qwen/3dprinting993
MONO_PICO=/Users/maxime/projects/3dprinting993/work/m64-private-20260907/nemo-picogk-20260928.ADELugEK
MONO_SOURCE=twins/964-chassis/source/qwen-picogk-tunnel
MONO_OUT=work/monocoque-qwen-new-run
mkdir -p "$MONO_OUT"
"$MONO_TRAIN/work/m64-qwen/venv/bin/python" "$MONO_SOURCE/prepare.py" \
  --training "$MONO_TRAIN" \
  --design /Users/maxime/projects/3dprinting993/twins/993-carbon-safety-cell/design-space.json \
  --output "$MONO_OUT/inference"
"$MONO_PICO/dotnet/dotnet" build "$MONO_SOURCE/Tunnel.csproj" -c Release \
  -p:PicoGKPath="$MONO_PICO/picogk-bin/PicoGK.dll" \
  -p:BaseIntermediateOutputPath="$PWD/$MONO_OUT/obj/" -o "$MONO_OUT/bin"
DYLD_LIBRARY_PATH="$MONO_PICO/picogk-bin" "$MONO_PICO/dotnet/dotnet" \
  "$MONO_OUT/bin/Tunnel.dll" "$MONO_OUT/inference/input.json" "$MONO_OUT/native-4mm" 4
DYLD_LIBRARY_PATH="$MONO_PICO/picogk-bin" "$MONO_PICO/dotnet/dotnet" \
  "$MONO_OUT/bin/Tunnel.dll" "$MONO_OUT/inference/input.json" "$MONO_OUT/native-2mm" 2
work/964-scan-recalage-20260925/runtime/bin/python "$MONO_SOURCE/sections.py" \
  "$MONO_OUT/native-4mm" "$MONO_OUT/sections.png"
python3 -m unittest discover -s tests -p 'test_964_*.py' -v
```

Runtime actually used: .NET SDK 9.0.317, runtime 9.0.19,
PicoGK source `0e6cf6b6f4993ec16dbcd72d8f27f26b999980f3` and the Mac native
library `picogk.26.2.dylib`. This profile does not change the one used by the
earlier Linux jobs.

The [follow-up rerun on Kali](../picogk-abi-probe/README.md) documents the
Docker computations and the isolated fix of a PicoGK boolean binding on
Linux. It does not replace the present Mac receipt and does not validate every
use of the library.

## Verification of October 2, 2026

- Native build: no errors or warnings; runs at 4 and 2 mm completed.
- Targeted suite `test_964_*.py`: six tests passed, including the check of the
  receipt digests and the upkeep of the manufacturing prohibitions.
- `make check`: main suite of 3,037 tests OK (120 skipped), then a stop
  in `917-manufacturing-f37-lpbf-audit-check`: the Mac's Docker socket is
  absent. The global check is therefore **not validated**; the following steps
  were not executed. No server or Docker setting was changed.
- `git diff --check`: passed.

## Limits and next steps

The unit tests cover the coordinates, radii, ends, segment counts and collision
formulas. The two native runs cover the requested geometry; the sections come
from the meshes, not from a generated image. This separation follows the test
strategy and visualization skills.
The four vehicle variants are **not** validated by these two packages.
The concept's frame is X rearward, Y left, Z up; no overlay with the 964 scan,
whose X points forward, is performed without a transformation.

The next product steps remain the [measurement plan](../../interface-measurement-plan.md),
then the complete interfaces and surfaces, the laminates and assemblies,
correlated composite calculations, tooling and testing. The complete monocoque,
the molds, manufacturing and road/track fitness remain not validated.
