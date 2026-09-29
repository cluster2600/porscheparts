# Validation — compile attempt (M64-SHORTBLOCK-0001)

Verdict: **compiled clean** in the pinned station image (0 warnings, 0
errors) after three first-time compile fixes (see below). Execution,
voxelization and export remain unrun; "geometry validated" is still NOT
claimed.

## Environment

- Host: kali2, ext4 worktree `/home/lolman/repos/wt-geo-sb`, branch
  `wave2/geo-sb-20260929`.
- Image: `picogk-station:qualified-final-20260928` (image ID
  `fd50c61399fd`, = `ghcr.io/cluster2600/3dprinting993-picogk-m64:station-20260928-final-fd50c61399fd`),
  PicoGK 2.3.0 at `/upstream/PicoGK`.
- Host dotnet is 6.0.400 (cannot target net9.0), hence the container build.

## Exact command

```sh
timeout 170 docker run --rm \
  -v /home/lolman/repos/wt-geo-sb:/work \
  -w /work/parts/m64-shortblock-0001/source/geometry \
  picogk-station:qualified-final-20260928 \
  bash -lc "dotnet build ShortBlock.csproj -c Release -nologo"
```

## History of attempts (2026-09-29)

1. First attempt (commit `bcdae48`): **FAILED** — 1 error.
   `ShortBlock.cs(381,43) error CS1001/CS1003`: parameter named `base`
   (reserved keyword) in `BuildFinnedCylinder`.
2. After rename `base` → `basePt`: **FAILED** — 7 errors:
   - CS1657 ×5: `Merge(ref using-var, ...)` on `using`-declared `Voxels`
     (`capCuts`, `barrel`) — `ref` cannot alias a using variable;
   - CS1501/CS8422: 6-argument `Annulus(...)` call in the rod shank builder
     (helper takes 5: `lib, a, b, rOuter, rInner`), plus the `base` cascade.
3. Fixes applied (commit `c48b133`):
   - `BuildFinnedCylinder(..., Vector3 base, ...)` → `basePt`
     (call sites pass a local already named `cylBase`; signature-compatible),
   - `Merge(ref Voxels, ...)` → `Merge(Voxels, ...)` (target is only mutated
     via methods; `ref` was never semantically required),
   - shank call corrected to `Annulus(lib, a, b, shankR, 0.0f)` — a solid
     round-section beam, matching the documented "round-section shank
     hypothesis envelope" (was passing widths as if a box API existed).
   No geometry intent was changed beyond the shank call completing the
   documented intent.
4. Final attempt: **Build succeeded. 0 Warning(s), 0 Error(s)** (elapsed
   ~15 s, within the 170 s timeout). Output
   `bin/Release/net9.0/M64ShortBlock.dll`. Build by-products (`bin/`,
   `obj/`, root-owned from the container) removed; a part-local `.gitignore`
   excludes them.

## Record

- `dotnet build -c Release` inside the pinned image: **PASS** at commit
  `c48b133` (this branch), 0 warnings / 0 errors.
- `dotnet run` (voxelization, STL/vdb export, run-report, volume sanity):
  **not executed** — next validation step; requires a headless station run
  with an output dir writable by the container.
- `dimensional_correctness_verified`: **false** (compile ≠ measurement).
