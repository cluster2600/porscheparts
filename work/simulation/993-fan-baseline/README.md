# 993-FAN-BASELINE — fan-zone OpenFOAM experiment deck

First runnable CFD deck for the M64/993 cooling-fan zone (M64-Z-CL). Experiment
lane only: everything here is a **surrogate with placeholder boundary
conditions** and stays exploratory. See `RUN_RECORD.md` for run state, version
stamps, and the explicit proves/does-not-prove statement; see `PARAMETERS.md`
for every dimension with its provenance tag.

Two geometry cases, both run to completion 2026-09-27 in
`m64-engineering-worker:latest` (OpenFOAM v2312):

- `caseA_published/` — F0 housing throat 252 mm **as published**; documented
  geometric failure (−14 mm radial clearance vs the 280 mm F0 impeller
  hypothesis, see `docs/993/993_ENGINE_COOLING_FAN_SYSTEM_F0.md` on
  `origin/main`). Run for comparison only.
- `caseB_corrected/` — throat 284 mm for the 2 mm radial clearance required by
  the F0 integration screen. **This is the informative case.**

Fan = actuator-disc surrogate (fvOptions `vectorCodedSource` over a cellSet:
quadratic blockage proxy + prescribed static rise). Blade count UNKNOWN
(M64-ACQ-0005) and deliberately not invented.

Regenerate + rerun: `python3 make_case.py && ./run_case.sh caseB_corrected &&
./run_case.sh caseA_published && python3 post_report.py`.

Solver output (time directories `100/` and `200/`, `postProcessing/` and the
`*.log` files of both cases) is no longer tracked (issue #417). Its digests and
the commit it can be recovered from are in
[`catalog/registers/untracked-solver-output.json`](../../../catalog/registers/untracked-solver-output.json);
the rerun command above regenerates it locally. `run_metrics.json` keeps the
numerical result.
