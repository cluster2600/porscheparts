# Prescribed-strain material reference sensitivity

**qualification=false.** This completed arithmetic study is an adjunct to head-strength work. Production alloy and qualified material card remain `null`. No head strength, yielding, failure, plastic response, life or validated material law is established.

The one authorized local call returned **0**, with complete [stdout](stdout.log) and empty [stderr](stderr.log). [execution.json](execution.json) preserves the raw tool result and invocation. The selected interpreter was Python 3.12.11 with `-B -I -S`; the source created no child process or thread pool. Its main timer reported 1,399,417 ns, excluding interpreter startup/imports and later sealing. This is not a benchmark.

## Reference and assumptions

[calculate.py](calculate.py) reads exactly `/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993/work/962-engineering/material-assumed-reference-proposal-001/proposal.json`, SHA-256 `e3f8aee9be38df911b489101fe5e3361df142e1bd70a434326dafba91b04c1eb`, 7,545 B. Source, input and selected interpreter pins match before and after the calculation; their complete identities are in stdout.

Only the five 20–400 °C model-input rows from [Crystals 2022, 1309](https://www.mdpi.com/2073-4352/12/9/1309), Tables 2–3, are used. These published parameters are not a newly measured, state-matched coupon dataset. Materials 2023 remains a separate measured thermal lead; none of its observations is blended into this calculation.

Assume uniform temperature, a homogeneous one-dimensional uniaxial small-strain elastic trial, free lateral contraction and zero transverse stress. The prescribed mechanical strains are 0, 0.0005, 0.001, 0.002 and 0.004. They are declared sensitivity inputs, not measured or computed head strains or thermal/pressure/retention loads.

For each temperature, `trial_MPa = E_GPa × 1000 × strain`; compare `trial/Y` with the published scalar parameter Y, and calculate its trial-parameter crossing `Y/E_MPa`. Fractions are exact; ratio decimal displays use 50 significant digits, ROUND_HALF_EVEN. No interpolation, extrapolation, fitting, expansion interpretation or plastic integration is used. The formula is the uniaxial specialization of the documented [small-strain elastic relation](https://mooseframework.inl.gov/source/materials/ComputeLinearElasticStress.html).

## Calculated response

Elastic trial stress in MPa; an asterisk means only that the trial exceeds the published scalar parameter.

| Temperature (°C) | E (GPa) | Y (MPa) | 0% | 0.05% | 0.1% | 0.2% | 0.4% |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 20 | 69 | 195 | 0 | 34.5 | 69 | 138 | 276* |
| 100 | 67 | 150 | 0 | 33.5 | 67 | 134 | 268* |
| 200 | 62 | 105 | 0 | 31 | 62 | 124* | 248* |
| 300 | 53 | 70 | 0 | 26.5 | 53 | 106* | 212* |
| 400 | 41 | 30 | 0 | 20.5 | 41* | 82* | 164* |

The five exact dimensionless trial-parameter crossings are 13/4600, 3/1340, 21/12400, 7/5300 and 3/4100 in ascending temperature order. [results.json](results.json) retains all 25 points, all five crossings, full exact fractions, decimal displays, assumptions and missing-property nulls. [results.csv](results.csv) contains the 25-point comparison.

The reference becomes more sensitive to a fixed imposed mechanical strain at the hotter rows when normalized by Y. An above-parameter elastic trial is not the material's predicted post-yield stress. The actual head strain demand, multiaxial response, plastic hardening, heat state, orientation, property measurement provenance and scatter remain unresolved.

## Remaining engineering work

Expansion definition/reference temperature, yield criterion, full plastic curves and rate/dwell association remain `null`, as do hot fatigue, TMF, cyclic response, creep/relaxation, statistical life and LPBF calibration properties. The density/Poisson and thermal rows were not used. No missing property is inferred.

The next strength calculation still needs accepted head meshes, actual loads and constraints, state-matched constitutive data and appropriate verification. The 24 head-mesh and 12 aggregate mechanical gates are unchanged; Phase 5 is not complete. No solver, geometry/scientific body, coupon/card, PUB or Git change occurred. Independent root verification of these 25 arithmetic rows remains separate.

