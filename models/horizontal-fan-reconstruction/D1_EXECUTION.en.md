# D1 executed and stopped within the initial budget

The diagnosis received an explicit Kali2 window after the Ti pilot was released.
It does not produce a complete comparison at 960: the control finishes, the
strict branch is interrupted. No result is admitted and no solver is restarted
after the limit. [Native report](results/cfd/D1-bounded-result.json) ·
[Actually computed residuals](results/cfd/D1-residuals.png) ·
[Input hashes](results/cfd/D1-diagnostic-input-manifest.json).

## Execution and exact measurements

The first preparation stops in 8.24 s before any solver: copying processor
directories dereferenced their `900/uniform` links, creating four extra files
in one branch. The strict partition guard rejected the difference. The fix
retains those links (`symlinks=True`); no physics, condition, tolerance, cell,
initial field or iteration is added. The
[initially prepared code](source/run_d1_in_container_setup_v1.py) and
[initial manifest](parameters/D1-prepared-pair-manifest-setup-v1.json) remain
preserved. The corrected partition is identical before both solvers.

The repair, preparation diagnosis and both solvers stay within the same
initial ten-minute limit: the outer envelope is recalculated with 202 s
remaining, then stops only the D1 container. The native ledger measures
**590.318 s from initial launch**, without exceeding 600 s. The first
preparation calculated zero flow iterations.

| Branch | Completed iterations | Measurements per table, including initial state | New measurements | Final 941–960 window | Final 960 fields | Status |
| --- | ---: | ---: | ---: | --- | --- | --- |
| relTol 0.01 | 60, 901–960 | 61 | 60 | twenty verified measurements | reconstructed, five complete fields of 453496 cells | unadmitted: pressure |
| relTol 0 | 29, 901–929 | 30 | 29 | absent | absent; only restart 900 exists | incomplete, not evaluated for admission |

Iteration 930 is entered but completes only two of three p corrections;
it has neither complete flow/torque measurement nor `ExecutionTime`.
It is excluded from statistics and rendering. Original thresholds remain
unchanged. The [control at 960](results/cfd/D1-control-960-flow-summary.json)
passes U, turbulence, mass, stability, direction and finite-field criteria,
but its maximum initial p residual over the last twenty iterations is
1.38616×10⁻⁴ against 10⁻⁴. Mean flow 1.15229935 m³/s, power 2429.758 W;
these values are not admitted performance.

## Convergence difference over the common prospective window

Only the first planned window 901–920 has twenty complete measurements for
both branches. The strict 921–940 window is incomplete; strict 941–960 is
absent. They are not replaced by a window selected after calculation.

| Measurement 901–920 | relTol 0.01 | relTol 0 |
| --- | ---: | ---: |
| Maximum initial p residual | 1.30859×10⁻⁴ | 1.31086×10⁻⁴ |
| Maximum final linear p residual | 9.60328×10⁻⁷ | 9.90354×10⁻⁹ |
| Mean linear p iterations, sum of three corrections | 11.20 | 29.95 |
| Mean flow, m³/s | 1.152299245 | 1.152299252 |
| Mean power, W | 2429.7772 | 2429.7775 |

The final linear residual decreases by a factor of 96.97 and linear-iteration
cost increases by a factor of 2.674. The initial residual maximum changes by
only +0.174 % and stays above the threshold. Initial curves nearly overlap
over the twenty-nine available strict iterations. On this window, this weakens
the explanation that linear stopping alone causes the exceedance.
Nonlinear coupling, mesh/wake and outlet effects remain to be distinguished.
No physical oscillatory phenomenon, confidence interval, variant ranking or
improved efficiency is established. The incomplete strict 960 target prevents
a final paired conclusion.

![Native D1 residuals, without extrapolating the interrupted branch](results/cfd/D1-residuals.png)

## Preserved evidence and released resources

The observed container respects 4 CPU, cpuset 0/2/4/5, 5 GiB RAM and
memory+swap, no networking, UID 1000, dropped capabilities and read-only
mounted sources. It is no longer active; at 17:07:52 UTC only the two
pre-existing services remain. No installation, rental or service change.

The retrieved private archive preserves both attempts, logs, measurements,
protocols, partition evidence and the control's 960 checkpoint: 63 files,
47047995 compressed bytes, SHA-256
`362c82e93a3ed2ae27532f1c7aaa62115b8c02e49146f900caba2fbf1c411dc2`.
Members and transfer are verified; the 900 checkpoint and mesh are already
retained in the initial native archive. The twenty small inputs used in
analysis match that archive's hashes. Post-calculation archiving took 1.72 s,
bounded at 1 CPU/1 GiB; it restarts no solver. Complete fields/logs remain
private. The [archive evidence](results/runtime/D1-native-archive-verification.json)
attests preservation without publishing complete outputs.

Historical fine R0 admission remains withdrawn; D1 supplies none of its
missing measurements. A final strict comparison would require a newly
explicitly coordinated window: no restart or extension is launched.
Physical interfaces and installed-cooling scenarios also remain to be established.

The [local analysis of preserved fields and proposed next trial](D1_NEXT_DIAGNOSTIC.en.md)
complements this result without new execution. The
[installed subsystems](SUBSYSTEM_PARAMETERS.en.md) remain symbolic and without
measured dimensions.
