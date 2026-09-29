# M64 valvetrain components — parametric PicoGK geometry (wave 2)

`parts/m64-valvetrain-0001` implements the best-evidenced M64/60 valvetrain
components as parametric PicoGK C# field functions:

| Component | Class | Evidence state |
|---|---|---|
| Intake valve (P/N 993 105 409 02) | `Valve` | head Ø49 mm / stem Ø8 mm sourced; functional length unknown |
| Exhaust valve (P/N 993 105 419 01 set) | `Valve` | Turbo variant Ø43.5 mm head / Ø8 mm stem / ~109 mm envelope stated; suffix unresolved |
| Valve spring seat | `SpringSeat` | installed-length spec registered (A=36.7/35.7 +0.3 mm); seat diameters unknown |
| Cam follower (bucket tappet, OHV-2V lineage form) | `CamFollower` | form ASSUMPTION; hydraulic lash compensation is public fact |
| Camshaft, per bank | `CamshaftParametric` | base circle + configurable lobe ONLY — M64 cam profile absent from public domain (M64-ACQ-0002) |

**Lineage note.** These are OHV-2V-lineage bucket-and-flat-tappet components
(901/911/964-type follower envelope) used as the layout-grade valvetrain
elements for the M64 digital twin until the actual DOHC components are scanned.
The 4-valve M64 head module itself is owned by the separate `wt-head` lane
(`parts/m64-cylinder-head-0001/`) and is deliberately not touched here.

## Layout

- `source/picogk/Valvetrain.cs` — parametric field functions and CLI driver.
- `source/picogk/Valvetrain.csproj` — net9.0, ProjectReference to `/upstream/PicoGK`.
- `source/picogk/build-in-station.sh` — compile/run inside the qualified
  `picogk-station` image.
- `provenance.json` — per-field provenance (sourced / declared / assumption /
  optimization), every non-sourced value labelled.
- `printability.md` — honest LPBF assessment against `SAFETY.md`.
- `validation/` — compile/run report from the picogk-station container
  (`run-report.json` + a `COMPILE_VERDICT.md` summary). Absence of a report
  means "authored, not compiled" — never a faked mesh.

## Status language (binding)

Nothing here is measured, fitted, tested, safe or manufacturing-ready.
Engine-critical parts are `prohibited_pending_engineering` per
[SAFETY.md](../../SAFETY.md): a calculation never authorizes manufacturing.
The camshaft is a layout hypothesis, not a claimed M64 cam profile.
