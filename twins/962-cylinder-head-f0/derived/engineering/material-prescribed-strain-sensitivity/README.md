# Material sensitivity: prescribed mechanical strain

The completed reference calculation contains **25 exact strain/temperature comparisons and five parameter crossings**. Root independently recomputed all points, ratios, decimal displays and CSV rows from the frozen input table. Nine elastic trial values exceed the published scalar parameter. **No production alloy or qualified material card is selected.**

| Temperature (°C) | E (GPa) | Scalar parameter (MPa) | Trial stress at 0.1% strain (MPa) | Trial stress at 0.2% strain (MPa) |
|---|---:|---:|---:|---:|
| 20 | 69 | 195 | 69 | 138 |
| 100 | 67 | 150 | 67 | 134 |
| 200 | 62 | 105 | 62 | 124 |
| 300 | 53 | 70 | 53 | 106 |
| 400 | 41 | 30 | 41 | 82 |

Read the [full study](originals/material-prescribed-strain-study-001/README.md), [25-point JSON](originals/material-prescribed-strain-study-001/results.json), [CSV](originals/material-prescribed-strain-study-001/results.csv) and [independent root review](originals/material-prescribed-strain-root-review-001/review.json).

The explicit trial is `stress_MPa = E_GPa × 1000 × mechanical_strain`, using five declared strains from 0 to 0.4%, uniform temperature and uniaxial small-strain elasticity. Strains are sensitivity assumptions, not computed head strains. The five exact parameter crossings are 13/4600, 3/1340, 21/12400, 7/5300 and 3/4100, in ascending temperature order. An above-parameter elastic trial does not predict yielding, plastic response, failure or life.

The input rows are published model inputs from [Crystals 2022, 1309](https://www.mdpi.com/2073-4352/12/9/1309), preserved in the [separate proposal](originals/material-assumed-reference-proposal-001/proposal.json). Matched heat treatment, orientation and property measurement provenance are unresolved. The separate measured thermal research lead is not blended into this study. Expansion interpretation, plastic curves, hot fatigue, creep, scatter and LPBF calibration properties remain unknown.

The [execution capture](originals/material-prescribed-strain-study-001/execution.json) records one local Python 3.12.11 `-B -I -S` call, raw exit 0, complete 3,536-byte [stdout](originals/material-prescribed-strain-study-001/stdout.log) and empty [stderr](originals/material-prescribed-strain-study-001/stderr.log). Named source/input/interpreter identities match before and after. The operator's 1,399,417 ns main timer excludes startup and sealing and is not a benchmark. No solver was run. Root verified saved arithmetic without importing or executing the archived calculation.

[FILES.json](FILES.json) binds nine byte-exact originals. Absolute paths are provenance, not portable commands; runtime bodies are excluded. The 24 poor head cells and 12 aggregate mechanical failures remain unresolved. Continue through [strength/material → LPBF → Omniverse → PhysicsNeMo](../../../ENGINEERING_PROGRAM.md) with accepted meshes, actual operating loads and state-matched properties.
