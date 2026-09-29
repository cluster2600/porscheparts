# Status — M64-SHORTBLOCK-0001 (short-block geometry lane, wave 2)

Branch `wave2/geo-sb-20260929`, worktree `/home/lolman/repos/wt-geo-sb`.
Updated 2026-09-29.

## Gate board

| gate | state | evidence |
|---|---|---|
| G1 source geometry authored | **PASS** | `source/geometry/ShortBlock.cs` (parametric, 4 sources + run report) |
| G2 compiles in pinned station image | **PASS** | `validation/build-log.md`: dotnet build 0 warnings / 0 errors in `picogk-station:qualified-final-20260928` at commit c48b133 (after 3 syntax/arg fixes; first attempt FAILED, honestly recorded) |
| G3 runs (voxelize + STL/vdb export + run report) | **OPEN** | `dotnet run` not yet executed; needs headless station run with writable output dir |
| G4 provenance recorded per value | **PASS** | `provenance.json` (machine-readable, json.tool-validated); every dimension tagged measured/sourced/project_input/assumed/derived/missing |
| G5 printability selection | **PASS (concept)** | `printability.md`: finned cylinder primary, crankcase halves secondary, piston dummy-only, rod no-print; fin gate FinMinLPBF ≥ 0.8 mm, voxel ≤ 0.75 mm required for print-study builds |
| G6 dimensional correctness | **BLOCKED** | no metrology; `dimensional_correctness_verified: false` |
| G7 release (fit/test/safe) | **NOT STARTED** | repo rule: highly loaded engine parts need professional review + validation plan |

## M64-ACQ-0004 (blocking layout truth)

Unknown, not public, **never baked**:

- **cylinder pitch** — runs on PROVISIONAL 86.4 mm (stroke + 10 assumption);
  env override `M64_PITCH_MM`;
- **crank-to-deck height** — runs on PROVISIONAL 0.0 (deck = split plane);
  env override `M64_DECK_MM`;
- bank station X is a scaffold assumption (`M64_BANK_X`).

The run report embeds a warning whenever pitch/deck are not overridden. ACQ
path: physical layout metrology on a donor engine or OEM drawing; until then
all inter-cylinder registration is assumption-class.

Related missing parameters (own BOM lines): piston compression height /
pin location / crown (M64B-PS-001), fin pitch/count (M64B-CY-001).
Rod datum is sourced-hypothesis (PAUTER, level B, aftermarket) — the OEM
baseline remains unconfirmed.

## Next actions (in order)

1. `dotnet run` in station image → STL/vdb + run-report (closes G3).
2. Print-study geometry pass: voxel 0.5 mm, fin root fillets, evacuation
   ports (closes G5 at specimen level per printability.md gate list).
3. ACQ-0004 metrology → re-run with env overrides; geometry re-issue without
   editing baked values (parameters already wired).

## Honesty rules this lane follows

- No inferred geometry, simulation output, or printed mesh is presented as
  measured, fitted, tested, safe, or manufacturing-ready.
- Compile success ≠ geometric or dimensional validation.
- The rod contour is a hypothesis envelope; the piston is a nominal-bore
  envelope.
