# m64-cylinder-head-0001 — status

**F2 coherent parametric assembly. Research geometry only: not dimensionally correct end-to-end, not fitted, not tested, not safe, not released.**

## Proven (to the level stated)
- PicoGK station build compiles and exports (`export/picogk-run-report.json`, voxel 2 mm): envelope with bore register, 4V valve pockets/guides, seat inserts, twin plug wells, 12-stud pattern.
- Valve layout carried from the V2 four-valve module audit; seat geometry from the G3 candidate; register/carrier/stud-pattern values are the 935-scan *candidates*, honestly labeled.

## Hypothesis
- Head envelope, deck thickness, seat band, insert wall/depth, stud depth (see provenance.json ASSUMPTION rows).

## Open gaps
- **ACQ-0004** cylinder pitch + deck height: parameterized via `--params` (null by default, never baked).
- Chamber volume not yet audited vs compression target; no seat contact pressure study; STEP is a tessellated conversion (watertight=false on the source mesh at 2 mm voxel), not a B-Rep.

## Files
- `source/picogk/` — PicoGK C# (Program.cs + Head4vEnvelope.csproj), ACQ-0004 loaded from params file
- `export/` — STL (PicoGK), STEP (FreeCAD conversion), conversion-report.json, run reports
- `provenance.json` — per-dimension authority tags
