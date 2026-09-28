# RUN_RECORD — 993-K16-COLD-SIDE-BASELINE-0001

Date: 2026-09-27 (Europe/Zurich). Executed by m64-writer (computational engine lane).
Status: **RAN SUCCESSFULLY** (first actual run of this deck; blockMesh/checkMesh/simpleFoam
exit code 0). This supersedes the untracked-claim smoke test mentioned in README.md
(image `3dprinting993-cadsim:dev`, 2026-08-30) — no run artifacts existed in the repo
working tree before this record.

## Environment

- Container image: `m64-engineering-worker:latest` (image id 1dc508c2bfab)
- Run as caller uid: `docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -e DOTNET_CLI_HOME=/tmp -v /home/lolman/repos/porscheparts:/repo ...`
- OpenFOAM: **v2312**, Build `_c39a0f64-20231220 OPENFOAM=2312 version=2312`
  (sourced from `/usr/lib/openfoam/openfoam2312/etc/bashrc`)
- **Version compatibility note:** case headers claim `Foam version 13`. The deck runs
  unmodified on v2312. Only warning: blockMesh flagged `convertToMeters` as a legacy
  (v1012) keyword, expecting `scale` in newer blockMesh syntax. Cosmetic; no action taken.

## Commands (run in case dir `/repo/simulation/993-k16-cold-side-baseline`)

```bash
. /usr/lib/openfoam/openfoam2312/etc/bashrc
blockMesh                        # exit 0
checkMesh -allTopology -allGeometry # exit 0 -> "Mesh OK."
simpleFoam                       # exit 0, endTime 500 reached, ExecutionTime 55.1 s
```

## blockMesh (verbatim key output)

```
Creating block mesh from "system/blockMeshDict"
--> FOAM IOWarning:
    Found [v1012] 'convertToMeters' entry instead of 'scale' in dictionary "system/blockMeshDict"
    Block 0 cell size :
        i : 0.0011361943 .. 0.0011361943
        j : 0.0020833333 .. 0.0020833333
        k : 0.0020833333 .. 0.0020833333
  boundingBox: (0 -0.034 -0.034) (0.09 0.034 0.034)
  nPoints: 50625
  nCells: 46080
  nFaces: 142656
  nInternalFaces: 133824
  patch 0 ... name: inlet ; patch 1 ... name: outlet ; patch 2 ... name: walls
```

## checkMesh — `Mesh OK.` (no issues; no grading changes needed)

Key lines (verbatim):

```
    Boundary openness (6.1197673e-17 4.7815668e-16 4.7577653e-16) OK.
    Max aspect ratio = 2.7060254 OK.
    Mesh non-orthogonality Max: 7.7182014 average: 3.7383519
    Max skewness = 0.24825096 OK.
    Cell determinant (wellposedness) : minimum: 0.053714455 average: 0.58028626
    Face volume ratio : minimum: 0.99108034 average: 0.99739677
Mesh OK.
```

## simpleFoam — 500 iterations completed, NO divergence

Solver: simpleFoam, RAS kOmegaSST, Newtonian nu=1.5e-5 m²/s, SIMPLE with
residualControl {p 1e-5, U 1e-6, (k|omega) 1e-6}, relaxation p 0.3 / U,k,omega 0.7
(unchanged from deck; no damping tweaks were needed since the run did not diverge).

Initial residuals (iteration 1, verbatim):

```
Solving for Ux, Initial residual = 1, Final residual = 0.053424397, No Iterations 1
Solving for Uy, Initial residual = 1, Final residual = 0.053424397, No Iterations 1
Solving for Uz, Initial residual = 1, Final residual = 0.053424397, No Iterations 1
GAMG: Solving for p, Initial residual = 1, Final residual = 0.045483183, No Iterations 5
Solving for omega, Initial residual = 0.001236257, Final residual = 2.1912046e-05, No Iterations 1
Solving for k, Initial residual = 1, Final residual = 0.011523217, No Iterations 1
```

Final residuals (iteration 500, verbatim):

```
Solving for Ux, Initial residual = 0.00040501896, Final residual = 2.3377103e-05, No Iterations 1
Solving for Uy, Initial residual = 0.0016159079, Final residual = 4.6002184e-05, No Iterations 1
Solving for Uz, Initial residual = 0.0016141294, Final residual = 4.5562184e-05, No Iterations 1
GAMG: Solving for p, Initial residual = 0.0025819407, Final residual = 7.5667977e-05, No Iterations 2
time step continuity errors : sum local = 0.068555158, global = -0.020730277, cumulative = -10.518077
Solving for omega, Initial residual = 0.00058163088, Final residual = 3.5934899e-05, No Iterations 1
Solving for k, Initial residual = 0.0022027954, Final residual = 0.00017744469, No Iterations 1
ExecutionTime = 55.1 s  ClockTime = 55 s
```

Continuity error evolution (sum local / global / cumulative):
iter 1: 12.238349 / 6.5156011 / 6.5156011 → iter 100: 0.30131281 / -0.11286048 / -12.503839
→ iter 250: 0.10700663 / 0.03787014 / -10.181815 → iter 500: 0.068555158 / -0.020730277 / -10.518077.

simulateTime: steady-state simpleFoam with `deltaT 1`, `stopAt endTime; endTime 500`;
simulated "time" = 500 pseudo-time-steps (not physical time; steady RANS).

**Convergence caveat:** the deck's `residualControl` (p 1e-5 / U 1e-6) was **NOT
reached** — the run ended at the hard endTime=500 with residuals plateaued around
2.3e-5 (U) / 2.6e-3 initial-vs-7.6e-5 final (p). Best residuals occurred near
iteration ~400 (Ux initial 1.23e-4). Residuals oscillate mildly at the end
(iter 490→500 initial residuals rise ~20%); the run is stable but only
**partially converged** — sufficient as a toolchain smoke test, not converged enough
for quantitative statements.

Post-processing function objects (in deck controlDict) final values (iteration 500):

```
surfaceFieldValue massFlowOut: sum(outlet) of U = (12480.695 100.14545 96.892198)
surfaceFieldValue inletPressure: average(inlet) of p = -433.70895
surfaceFieldValue outletPressure: average(outlet) of p = 0
forces (walls) Total = (0.3056744 -0.02150016 -0.021160012) N  [rhoInf=1.2 placeholder]
```

Note: `postProcess -func residualPrecision` is not available in this v2312 image
(`Cannot find functionObject file residualPrecision`); residuals were extracted from
the solver log instead.

## BC placeholder labels / flow-data conflict

- **Encoded case (P1):** inlet `fixedValue uniform (40 0 0)` m/s — an explicit
  PLACEHOLDER in `0/U`, not a 993 compressor-map value. Over the 50 mm equivalent
  inlet section this derives mass flow 0.09425 kg/s (parameters.json).
- **Flow-data conflict** (docs/TURBO_AIRFLOW_SIMULATION_DATA.md): 1210 l/s @ 5750 rpm
  vs 1010 l/s @ 6100 rpm. The deck's 0/U comment defines sensitivity run **P2**
  (uniform 257.2 m/s, derived from the 1010 l/s figure split over two banks) but
  P2 was **not run** in this session. The case as executed encodes neither flow figure
  — only the synthetic 40 m/s regression velocity. The conflict therefore does not yet
  affect this baseline; it must be resolved before BCs mean anything.
- Outlet: `fixedValue uniform 0` (p). Walls: noSlip. Turbulence kOmegaSST with
  default inlet k/omega (see `0/k`, `0/omega` — also placeholder-class).

## LIMITATIONS (read before using any number above)

> **EXPLORATORY.** Placeholder BCs (synthetic 40 m/s inlet; rhoInf=1.2 force
> placeholder). Geometry is a **synthetic rectangular equivalent-section diffuser
> block (blockMesh single hex) — NOT K16 geometry**: no compressor wheel, no CHRA,
> no volute, no housing. Not a representation of the K16 cold side. Toolchain smoke
> test only; residuals not converged to deck tolerance. No performance, durability,
> fitment, or manufacturing conclusion may be drawn. Not dimensional inspection,
> physical fitment, or professional engineering review.

## Artifacts kept (repo tidy policy)

- `RUN_RECORD.md` (this file)
- `residuals-summary.csv.gz` — 3000 rows `iter field initial final` extracted verbatim
  from the simpleFoam log (all 500 iterations, all 6 residual lines each).
- Removed: `constant/polyMesh`, time dirs `100..500`, `postProcessing/` (all regenerable
  with the two commands above).
- Pre-existing uncommitted working-tree edits in this case dir (NOT made by this run;
  additions only — comment block in `0/U`, `functions{}` post-processing block in
  `system/controlDict`, 66 insertions, 0 deletions vs HEAD f1d6092) were left in place
  and are what produced the function-object values quoted above.

## Minimal real inputs needed before results can inform a print decision

1. **Real geometry:** licensed CAD or dimensional scan of the K16 cold side (compressor
   inducer 40.6 mm / exducer 60.5 mm declared by suppliers — unverified, currently
   context-only). The equivalent-section block cannot resolve diffusion performance.
2. **Real BCs:** resolved compressor-map operating points (mass flow vs pressure
   ratio at relevant engine rpm) to settle the 1210 l/s@5750 vs 1010 l/s@6100 conflict
   and replace the 40 m/s placeholder; realistic inlet turbulence quantities.
3. **Materials & temperatures** per sub-assembly (thermal loads on printed material).
4. **Mesh/geometric convergence study** at real geometry with converged residuals.
5. Engineering review + bench test gate (already listed in parameters.json validation
   block) before any hardware/print decision.
