# m64-cooling-fan-0001 — status

Lane: wave2 fan STEP/geometry (`wave2/fan-stp-20260929`).
Status: `parametric_source_ready_unvalidated` (2026-09-29).

## Deliverables in this branch

- `geometry/M64Fan.cs` + `geometry/fan-config.json` (+ `.csproj`): parametric
  11-blade rotor and housing, PicoGK implicit, STL export.
- `geometry/M64CrankcaseInterface.cs` + `geometry/crankcase-interface-config.json`
  (+ `.csproj`): parametric ventilated-crankcase (carter ventilé) collector
  interface to the housing inlet; placeholder topology, STL export.
- `STEP_EXCHANGE.md`: honest STEP route — the pipeline provably emits STL
  only; STEP is a declared OCCT conversion target, not an output.

## Verifications actually run (2026-09-29, host kali2)

1. Host `dotnet build` (SDK 6.0.400) on `geometry/M64Fan.csproj`:
   **failed with NETSDK1045** (SDK 6 cannot target net9.0). This is an
   environment limitation, not a source defect.
2. Build + generation inside the local qualified image
   `ghcr.io/cluster2600/3dprinting993-picogk-m64:station-20260928-persistent-4f58a4e28ab7`
   (.NET SDK 9.0.317, `/app/PicoGK.dll` + native `picogk.26.2.so`):
   - `M64Fan.csproj`: **build succeeded, 0 warnings, 0 errors**.
   - `M64CrankcaseInterface.csproj`: **build succeeded, 0 warnings, 0 errors**;
     program executed with `--network none --cpus 2 --memory 4g`, wrote
     `m64-crankcase-interface-mm.stl` (volume 71 024.4 mm³, 636 364 triangles,
     reference mass 189.6 g at 2.67 g/cm³) and `generation.json` with
     `parametric_reconstruction_unvalidated`.
   - Runtime note: the program's checks pass; the STL/BOFF claim is limited
     to STL — `PicoGK.xml` in the pinned assembly lists only
     `SaveToStlFile/mshFromStlFile/SaveToCliFile/SaveToVdbFile` sinks.
   - The generation run for `M64Fan.cs` itself (rotor + housing) was last
     evidenced by the earlier lane commit; only the crankcase interface was
     (re)generated on 2026-09-29. Meshes from this run stayed in the
     container scratch dir and are **not** committed (large binaries keep
     raw evidence outside Git per lane convention).

## What this does NOT prove

Nothing here is dimensionally correct, fitted, flow-validated, safe,
released, or manufacturing-ready. All crankcase-interface dimensions are
engineering assumptions or mirrors of the fan config; no measured M64
crankcase surface is represented. Raw STLs have not been audited for
zero-area triangles / manifoldness, and no STEP file has been produced.
