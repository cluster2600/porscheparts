# COMPILE_VERDICT — m64-valvetrain-0001

Verdict: **COMPILED AND RAN in the qualified station image.** Layout proxies
only. No dimensional, fit, test, safety or manufacturing claim is made.

## What was verified

- Environment: `picogk-station:qualified-persistent-20260928`
  (image id `4f58a4e28ab7`), .NET SDK **9.0.317**, PicoGK C# source
  **2.3.0** at `/upstream/PicoGK`, native runtime `/app/picogk.26.2.so` with
  `LD_LIBRARY_PATH=/opt/picogk-native/lib`.
- `dotnet build -c Release Valvetrain.csproj`: **Build succeeded,
  0 Warning(s), 0 Error(s)**.
- Run: `M64Valvetrain /out/m64-valvetrain-run 1.0` → exit 0, stage marker
  `M64_PICOGK_VALVETRAIN_PASS`, 5 STLs + `run-report.json` in `run/`.
- All five STL sha256 values in `run/run-report.json` re-verified against the
  files on disk (2026-09-29): match.

## PicoGK API conformance (checked against installed /upstream sources, not invented)

| Call site in `Valvetrain.cs` | Installed API (PicoGK 2.3.0) | Status |
|---|---|---|
| `Library(float fVoxelSizeMM)`, `using` | `Library/Library.cs` `public Library(float)` , `IDisposable` | OK |
| `Voxels(Library, in IBoundedImplicit)` | `Base/Voxels.cs` `public Voxels(Library, in IBoundedImplicit)` | OK |
| `IBoundedImplicit` with `BBox3 oBounds { get; }` and `float fSignedDistance(in Vector3)` | `Base/Voxels.cs` `IImplicit`/`IBoundedImplicit` | OK |
| `Voxels.CalculateProperties(out float, out BBox3)` | `Base/Voxels.cs` line ~812 | OK |
| `Mesh(in Voxels)` | `Base/Mesh.cs` | OK |
| `mesh.SaveToStlFile(path, Mesh.EStlUnit.MM)` | `IO/MeshIo.cs`, `enum EStlUnit { AUTO, MM, ... }` | OK |
| `mesh.nTriangleCount()` | `Base/Mesh.cs` | OK |
| `new BBox3(minX,minY,minZ,maxX,maxY,maxZ)`, `vecMin`/`vecMax` | `Types/BBox.cs` | OK |

## Host-side check limitation (honest)

The workstation's system dotnet SDK is **6.0.400**, which cannot target
net9.0: a host-side `dotnet build` fails with **NETSDK1045** ("current .NET
SDK does not support targeting .NET 9.0"). This is an SDK-version limitation
of the host, **not** a defect of the code: the same project builds and runs
cleanly in the station image (SDK 9.0.317) as recorded above. The station
container is the qualified build/run path for this lane; host builds are not
representative.

## Run specifics

- Voxel size: 1.0 mm (coarse screen; bounds/volumes are voxel-level, not
  metrology).
- Components: valve intake Ø49 proxy, exhaust Ø43.5 Turbo-variant proxy,
  spring seat, bucket follower, parametric camshaft (cosine-rise placeholder
  lobe — M64 profile is absent from the public domain, M64-ACQ-0002).
- `run-report.json` schema `m64-picogk-valvetrain-run-v1`, status
  `layout_geometry_job_completed_not_physics_validation`,
  `dimensional_correctness_claimed: false`,
  `manufacturing_authorized: false`.

## What this does NOT prove

- The distribution remains a **concept**: no metrology exists for the M64
  valvetrain components; every diameter/length carries its provenance tag
  (`SOURCED` / `declared` / `ASSUMPTION` / `UNKNOWN`) in the source comments.
- Guides and seats: **not validated** — no guide or seat geometry is modelled
  or inspected here; the spring-seat and valve-seat geometry are placeholders.
- The camshaft is a layout hypothesis, not a cam profile claim.
- `provenance.json` and `printability.md` promised by the lane README are
  **still missing**; the in-code evidence tags are the current provenance
  record until those files are authored.
- Per SAFETY.md: a calculation never authorizes manufacturing; engine-critical
  parts stay `prohibited_pending_engineering`.
