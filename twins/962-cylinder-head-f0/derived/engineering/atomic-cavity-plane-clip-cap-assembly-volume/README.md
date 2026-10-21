# Assembled HXT volume: quality rejection and saved-file audit

The raw HXT volume mesh is **rejected at the unchanged minimum SICN 0.1 quality gate**: its minimum is **3.784626658982107e-9**, with **285,573 of 2,989,608 cells below 0.1**. A separate read-only saved-file audit completed and has independent stopped-result review. Diagnostic completion does not accept this volume or authorize a PDE solve. [Saved-file report](readback/report.json), [result peer](reviews/readback-result-peer.json).

The single unoptimized HXT trial used the unchanged assembled analysis surface `9d62…` (871,731 vertices; 1,743,878 oriented triangles), native Gmsh 4.15.2, two software threads, maximum size 1.75 mm and `Mesh.Optimize=0`. The controller returned RC2 naturally, without a deadline/RSS stop, after a 130.73795687500387 s native-process window (131.9985842499882 s root outer execution). The saved MSH is SHA256 `4a17567e6394bcda8571b0ff07f74471338bc7f3be60b0153a20020f654c6b41`, 205,789,862 bytes. Its complete identity is bound by the native and independent saved-file ledgers. No MSH/BIN is included or newly read to assemble this capsule.

| Saved observation | Result |
|---|---:|
| Nodes / tetrahedra | 950,032 / 2,989,608 |
| Referenced interior / orphan nodes | 78,301 / 0 |
| Minimum SICN | 3.784626658982107e-9 |
| SICN below 0.1 / nonpositive | 285,573 / 0 |
| Minimum Jacobian | 5.529727786779404e-10 |
| Minimum signed tetra volume | 9.216212977965672e-11 mm³ |
| Signed tetra-volume sum | 915,453.1236217882 mm³ |

The saved-file reader returned RC0, reproducing all four tagged node/coordinate/tetra hashes, complete explicit source-boundary coordinate/connectivity equality, metric counts/extrema and the referenced/orphan-node census. It counted all 285,573 positive cells below SICN 0.1 without weakening the gate. No generate, optimize, mesh-write or solve call occurred. Its query window was 12.711658374872059 s, controller window 14.050119708990678 s, and root outer window 14.606338375015184 s. Root and independent stopped reviews verified the six-file closure and all 80 current inputs, including source/runtime/previous native associations. No native or metric query was replayed by the result peer or during publication assembly.

`nonpositive_SICN_tetrahedra=[]` makes `fixed_boundary_only_nonpositive_cells=true` an **all(empty) vacuous value**. It does not say that the 285,573 positive poor cells lie on the boundary. Their boundary/interior participation is not classified in this capsule. Full tetra-exterior incidence and internal-face orientation in the readback are explicitly retained from the native worker; this reader did not repeat full tetra-face sorting. The positive volume sum and bookkeeping agreement do not establish convergence or thermal resolution.

The earlier scoped [numerical surface-admission record](admission/surface-admission.json), original hash `035c45d0…`, is preserved. It concerns the assembled polygonal analysis surface and does not accept this volume. The separate stronger Mesh_2 criterion still has **414 failures** and remains false for admission. No OEM/factory accuracy, inner-roundoff/CAD certificate, accepted head volume, head PDE, strength, material, LPBF process or manufacturing qualification follows.

The original HXT guard run retains 11 passes and 1 failure: its mock fixture supplied an admission digest of `'a'*64` despite writing different bytes. A test-only successor computes the fixture's actual digest. Production source `b7d3de89…` remains byte-identical, and all 12 selected guards pass. The failed review, explicit log-line projection, old/new test sources and exact one-literal test delta are included. Separately, all 10 readback-runner mocks pass, including the 17 s Popen creation-time budget check and a valid exited RC0 after 121 s which must refuse without a timer callback. No test was rerun to assemble this capsule.

Both controllers preserve nonraising SIGTERM ownership, stop/reap/finally restoration and synchronous elapsed-time refusal. Native/readback watchdog budgets are 300/120 s, with respective sampled RSS stops of 8/4 GiB and two software threads for each run. These are not hard OS CPU/address-space quotas or exact peak-memory measurements; blocked calls and cleanup duration are not given an absolute cancellation guarantee. The saved reader's observed maximum RSS was 1,735,999,488 bytes from 28 samples, not a certified peak. No automatic retry occurred.

Exact own source/snapshot associations, source/child/result reviews and safe stopped records are included. The native worker projection omits only its private `runtime.executable` locator, preserving every other numerical/control/hash value. The controller receipt omits private host argv and its duplicate embedded worker report; the separately bound worker projection retains that report's observations. Contract maps retain all original 49/75/80 pin digest values, with three runtime locator keys replaced by explicit roles. Private-path log lines are omitted by original line number; retained text is exact. `original-records.json` distinguishes exact-copy and selected-projection roles and records original/payload hashes. These projections are not executable contracts, and the public seal covers selected files rather than every private input or artifact byte.

Historical HELD fields such as unrun tests, future source copies and the preparation's unobserved MSH hash remain unchanged in their source records and projections. The later exact materialized sources, root test outcomes, current file checks and completed result peer are separately bound. They are not retrospective claims about the earlier preparation.

Reuse the existing [assembled research-model ZIP](https://github.com/cluster2600/porscheparts/releases/download/untagged-3dc4679a17c16edf0fb4/962-bore95-plane0-assembled-unadmitted-review.zip), SHA256 `8ba6fc5dca47f3a51bc6298f481aaa334ac1096608552a96159a1d4688f6a4d5`; no geometry or download asset is duplicated. A separate rejected-MSH review archive has not been prepared here. No upload or Git action is performed by this capsule assembly.

Run `python3 verify.py` in this directory to check the selected capsule's hashes, byte counts and complete file closure. This standard-library byte check performs no geometry or scientific assessment and grants no engineering or manufacturing approval.
