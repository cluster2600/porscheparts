# Output-mesh check disposition: piston gallery and headlamp hook (2026-11-05)

Issue #468. The evidence files named below are frozen under `evidence/**` and
were not edited.

## Headlamp spring hook (`twins/993-headlamp-spring-hook-alsi10mg-f0`)

The two `FAIL` statuses are the top-level and rule status of one finding in
`evidence/simready-f0/raw-validation.json`: `UsdAsciiPerformanceChecker` flags
large arrays stored in the intermediate ASCII stage
`work/headlamp-hook/usd-conversion/headlamp_spring_hook_f0.usda`. That is a
storage-format performance rule, not a geometry or integrity defect. The
committed binary asset was validated separately and
`evidence/simready-f0/binary-validation.json` reports `PASS` with no failed
rule; `evidence/summary.json` cites the binary report for its
`nvidia_usd_asset_validation` gate.

Verdict: no failing check applies to the committed asset. The raw report is
kept as the record of the ASCII intermediate.

## Piston gallery (`twins/993-m64-60-piston-gallery-f0`)

`evidence/picogk-f0/picogk-output-integrity.json` reports
`failed_output_mesh_integrity`: all six PicoGK STL variants carry 27 to 109
non-manifold edges, with no repair attempted. The STLs are outside Git and were
not found on this host, so the audit cannot be re-run without regenerating them
with `source/run_picogk_optimization_screen.cs` in the pinned PicoGK image.

Even a clean re-run would not allow a design selection. The screen records
`selected_variant: null` and `eligible_for_selection: false` for every
variant: all fail the provisional 1.50 ambient plate margin, and selection also
needs hot material allowables, measured interfaces, transient loads, CHT and
nonlinear fatigue analysis. No design selection is recorded.

Verdict: blocked. Next step is a PicoGK re-run with a manifold output stage
(a meshing fix in the generator, not a post-hoc repair of the frozen meshes),
written to a new evidence directory; selection stays blocked on the engineering
inputs above.
