# Fan relaxation trial: terminal rejection

Refs #453. This follows [final-field recovery](../fan-final-field-recovery-20261107/README.md).
It is a numerical recovery experiment on the historical control case, not an
installed-airflow prediction, pitch-42 result or engineering qualification.

The recovered iteration-2000 fields were repartitioned from 32 ranks to four and
reconstructed bit-for-bit before restarting. Relative to the historical setup,
only velocity relaxation changed from 0.9 to 0.7; pressure stayed at 1 and
k/omega at 0.7. Foundation 14-a4867fc914c1 differs from the historical
14-7b05503f98a8 runtime. That runtime change and the four-rank decomposition are
explicit experimental differences, not hidden equivalence claims.

An initial 8 GiB attempt was killed by the memory limit. Its failed output was
retained. A fresh 10 GiB attempt used four CPUs, no swap above the RAM cap,
256 PIDs, 128 MiB temporary storage and a 6,000-second native timeout. It exited
124 at that timeout without OOM, completing iterations 2001–2163. The final
iteration-2164 heading contains no completed iteration. The original saved
fields were hash-verified unchanged after termination.

The iteration-2100 checkpoint was preserved through hard links to its 32 files
before any later purge could remove it: 1,032,227,223 bytes. The
[checkpoint manifest](checkpoint-2100.json) identifies those private fields;
this report does not contain the fields or claim a reconstructed 2100 solution.

## Unchanged acceptance

The [terminal diagnostic](diagnostic.json) excludes the initial-state row at
2000. The existing strict reader rejects 163 completed iterations because two
complete 100-iteration windows are required. No shorter windows or padding with
historical rows were substituted; between-window drift remains null.

The last complete 100 iterations, 2064–2163, also fail independent conditions:

| Quantity | Observed | Required |
|---|---:|---:|
| Relative mass imbalance, maximum | 0.0000043653 | < 0.001 |
| Relative flow peak-to-peak | 0.00059649 | < 0.002 |
| Relative torque peak-to-peak | 0.00490871 | < 0.002 |
| Maximum initial velocity residual | 0.00178737 | ≤ 0.0001 |
| Maximum initial pressure residual | 0.03768768 | ≤ 0.001 |

Mean outlet flow was 0.3877621 m³/s and mean fluid torque 0.4403431 Nm; these are
unconverged numerical diagnostics only. k and omega residuals were below their
0.001 limits. Passing those individual conditions does not establish convergence.
Wall resolution and mesh independence remain unqualified.

Run the independent diagnostic replay against the retained log and three tables:

```sh
python docs/reports/fan-relaxation-terminal-20261107/verify_diagnostic.py
```

The [execution receipt](recovery-execution.json) binds the plan, runner and final
log hashes. The [collection receipt](collection.json) also records the two
magnitude tables and plan retained privately; only the three tables consumed by
the diagnostic are included here. Raw fields remain private. No restart,
acceptance-threshold change, paid compute or manufacturing authorization follows
from this result.
