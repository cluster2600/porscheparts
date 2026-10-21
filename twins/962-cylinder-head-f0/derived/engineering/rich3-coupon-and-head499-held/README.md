# Additional coupon correction and proposed head-mesh adapter

The synthetic coupon was run once with **three Richardson updates instead of
two**. No physical input, material assumption, observer, mesh or acceptance limit
changed. A separate offline END181 diagnostic also completed once.

**The extra update resolved none of the failed equilibrium checks:** the same
12 of 36 diagnostic aggregates and 3 of 12 native aggregates still fail. Failed
magnitudes decreased by approximately 0.31%–6.09%. This is a diagnostic change;
convergence, its cause and component qualification remain unproved.

| Native constrained component | Previous result | Three-update result | Unchanged absolute limit |
|---|---:|---:|---:|
| Fx, N | −2.29850465416348e−6 | −2.2529896739342803e−6 | 1e−7 |
| My, N·m | −9.236246114596725e−7 | −9.205978130921721e−7 | 1e−7 |
| Mz, N·m | 1.0408839443698525e−6 | 9.787181625142694e−7 | 1e−7 |

The [complete diagnostic](originals/rich3-END181-equilibrium-execution-001/diagnostic.json)
reports **66,590 scalar comparisons with zero exceedances**.
Root and the saved-result reviewer independently recomputed both reports'
1,275 saved component rows and all 36 force/moment aggregates. The complete
scalar/QP table is not serialized and was not independently replayed. The
reviewer authored the literal diagnostic rebind; that affiliation is retained in
the [saved comparison review](originals/rich3-END181-equilibrium-result-peer-001/review.json).
The [root disposition](originals/rich3-END181-equilibrium-root-result-review-001/review.json)
records the separate arithmetic checks and remaining failures.

The [inventory](manifest.json) links the byte-exact generated source, reports,
comparisons and review records. Earlier results remain in the
[two-update diagnostic](../native005-END181-equilibrium/README.md) and
[quadrature arithmetic audit](../native005-END181-QP-arithmetic/README.md).
Frozen `HELD`, `UNRUN` and historical schema labels describe those records at
creation; later execution is established by its separate result records.

## Native execution and accounting limits

Outer, caller and native return codes are zero, with saved reap observations,
no stop signals and a final group-absence observation. The 75 sampled RSS
observations peak at 251,674,624 bytes; this does not prove a true peak or quota.

The [operational accounting review](originals/cp1-oneway-cooling-release-richardson3-terminal-resource-review-001/review.json)
preserves the first post-return audit, which failed after incorrectly counting installed runtime
identity bodies against the 512 MiB **artifact** cap. Its source and failure
remain preserved. The corrected audit uses the original reviewed artifact
scope and records 460,256,667 bytes, including the additional review, below the
unchanged cap. The 164,143,319 bytes of installed identity bodies are accounted
for separately. No limit was relaxed and no native rerun occurred.

**The full external startup-through-corrected-census 115-second interval is
unproved.** Clean exits and the corrected byte count do not pass that whole
operational resource gate. The offline diagnostic has its own completed
20-second/32 MiB scope: 17,361,031 bytes and approximately 0.756 seconds through
its census. Late tool-return records and later reviews are separately identified;
an exact companion preserves the original tool output after an earlier nested
boolean serialization error. Scientific files are unchanged.

Raw scientific CSV/Exodus/PETSc bodies, native console, host process tables and
installed software bodies are excluded from this publication. Their selected
identities and derived findings are retained; nested descriptors are not copied.

## Head-mesh work remains unrun

The proposed HEAD499 adapter connects the existing emitter, session transport,
binary64 mapper and independent word validator. It requires all 11 blocks to
return SAT, all 48 coordinate mappings and validation of all 499 affected cells
before even proposing local word acceptance. It adds no geometry application.

The adapter, author review and
[independent source review](originals/head-star-current24-qfnra-head-adapter-source-peer-001/review.json)
are source preparation. Its actual solver/model
printing, performance, external resource observations and 499-cell outcome are
unverified. **The 24 poor head cells remain.** Earlier toy results do not grant
head acceptance.

## Continuation in the requested order

1. **Strength and material:** resolve head-mesh quality and establish operating
   loads, measured interfaces and a documented alloy/process/heat-treatment
   state. Existing assumed sensitivity results do not select a production alloy.
2. **LPBF:** inspect the captured residual/correction vectors before selecting
   another numerical experiment; verify the complete deposition, cooling and
   support-release trajectory, then calibrate with matching process measurements.
3. **Omniverse:** repair the six substantive USD profile failures and attach
   accepted fields with checked units, frames, associations and time.
4. **PhysicsNeMo:** build accepted reference cases, split whole geometries,
   builds and loads before normalization, then train, evaluate and connect
   checked inference to the twin.

All new work stays in English. This checkpoint does not complete head strength,
material/process qualification, calibrated LPBF, a correlated twin, a trained
surrogate or manufacturing qualification. The
[engineering programme](../../../ENGINEERING_PROGRAM.md) tracks those stages.
