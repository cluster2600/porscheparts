# m64-exhaust-0001 — compile record (authored geometry, container build)

Date: 2026-09-29. Branch: `wave2/geo-ex-20260929`. Owner: m64-writer.
Scope: managed compile check of `source/picogk/` only. This is **not** a
runtime test, not a voxel-render check, and not physical validation.

## Environment

| item | value |
|---|---|
| image | `picogk-station:qualified-final-20260928` (local id `fd50c61399fd`) |
| SDK in image | `dotnet 9.0.317` at `/usr/local/bin/dotnet` |
| PicoGK project in image | `/upstream/PicoGK/PicoGK.csproj` |
| host SDK | 6.0.400 — cannot target `net9.0` (NETSDK1045), hence the container |

## Command (timeout-capped, 170 s)

```
cd parts/m64-exhaust-0001/source/picogk
docker run --rm -v "$PWD":/work -w /work -e UpstreamRoot=/upstream \
  picogk-station:qualified-final-20260928 bash -lc 'dotnet build -nologo -v q'
```

## Result: BUILD SUCCEEDED

- Attempt 1 failed with exactly two `CS0019` errors (`Vector3 ± float` is not a
  defined operator in the pinned PicoGK / System.Numerics surface):
  - `Program.cs:244` — `SdRoundedBox.fSignedDistance`, `... + m_fRadius`
  - `Program.cs:558` — `HeatShield` ctor, `vecHalf - oParams.WallMm`
- Fix (syntax only, **no geometry change**): broadcast the scalar as
  `new Vector3(v)`, which subtracts/adds the same value on all three axes —
  identical semantics to the intended isotropic rounding/inset.
- Attempt 2: `Build succeeded. 0 Warning(s) 0 Error(s)` in ~21 s.

## What this does and does not prove

- Proves: the C# compiles against the pinned PicoGK API surface under
  `net9.0` in the qualified station image (csproj wiring is complete and
  correct with `-e UpstreamRoot=/upstream`).
- Does **not** prove: the program runs (native PicoGK runtime not exercised),
  the voxels render, the STL exports, or any dimension is correct. Every
  input remains tagged `ASSUMPTION`/`SYNTHETIC` in `../source/picogk/provenance.json`.
- Voxel render + STL export (`Mesh.SaveToStlFile`) remain open work items once
  PET-dependent dimensions are sourced (see `status.md`).
