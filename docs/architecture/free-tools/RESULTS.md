# Execution results — 25 October 2026

These results separate native software execution, documentary model quality,
host deployment and physical engineering acceptance. Source and runtime details
are retained in the [machine-readable report](../../../benchmarks/free-tools/results/mac-20261025.json).

| Check | Measured result | Scope |
|---|---|---|
| Frozen carrier inputs | SHA-256 verification and admission replay completed | Existing catalogue-selected geometry preserved; R2 remains unadopted |
| FTS5 evaluation | 10/10 references, 10/10 unknown boundaries, 5/5 conflicts, 5/5 hostile-document boundaries | Authored 30-case retrieval test, not model-answer accuracy |
| Production documentary index | Actual carrier record, authored report and allowlisted PorscheFanatics identity export imported; PorscheFanatics reference appears in top five | Local catalogue source revision and hashes recorded; no live website parity claim |
| DVC Mac recovery | Actual registered inputs restored into a fresh private cache and rehashed | Primary Mac store only |
| DVC failure controls | Two independent local test stores, corrupt/missing objects and simulated interruption checked | The two local test directories do not establish a Kali backup |
| OpenTURNS native | First-order indices 0.1994288501 and 0.8017120442 | Synthetic expected 0.2/0.8, absolute tolerance 0.03 |
| OpenMDAO native | Thickness 0.010455159171866592 m; independent target 0.010455159171494206 m | Synthetic constrained beam; separate analytical process and independent replay |
| Carrier external component | Executed admission replay; `blocked_engineering` | No new carrier FEM solve or optimization claimed |
| Local Qwen documentary inference | Actual MLX inference attempted; malformed draft rejected | Documentary adaptation is unqualified; original geometry command unchanged |
| CloudCompare | Native Linux controls passed: six points each at 0, 1 and 0 mm expected distance; all recovered exactly | CloudCompare 2.13.2, immutable CPU image, unsigned C2M; sampled diagnostics only |
| SALOME/NETGEN | Native Linux controls passed: cube 20 tetrahedra; bore 254 tetrahedra | Exact positive C3D4 determinants, unchanged boundary/groups and INP round-trip; native MED and raw connectivity retained |
| Kali independent recovery | Unexecuted | Thunderbolt peer observed; SSH port 22 did not answer; actual identity required |

The optional native Python suite ran 32 tests and passed with one explicit local
CloudCompare skip. CloudCompare was separately
[executed with SALOME in Linux CI](https://github.com/cluster2600/porscheparts/actions/runs/40196260525).
Its negative controls deliberately include an infeasible optimization, which
prints an optimizer failure while the test correctly verifies rejection.

Full `make check` passes in
[Linux CI](https://github.com/cluster2600/porscheparts/actions/runs/40194342447).
On this Mac it completed with two existing last-digit floating-point comparison
failures (`test_993_cooling_impeller_we43_f1` and
`test_993_fan_stator_alsi10mg_f1`), zero errors and 380 explicit skips. Their
historical reports and thresholds were not changed. Strict documentation links
report zero broken links; all three Mermaid views rendered with CLI 11.12.0 and
were visually reviewed.

The carrier's independent contract still lacks measured interfaces and loads;
the registered R2 comparison does not establish mesh convergence. The tools
therefore cannot authorize carrier optimization, fitment, strength, fatigue,
LPBF process suitability or manufacturing.

The actual carrier admission receipt also reports each blocked stage: no
registered scan/transform contract for CloudCompare, no independently reviewed
face-index groups in this pilot manifest for SALOME, no converged solver response
or qualified probability model for OpenTURNS, and no accepted native FEM replay
for OpenMDAO. The original 1,000 and 10,000 N/mm support-stiffness cases remain
documented scenarios; they are not a measured probability distribution. The
new external component currently wraps admission, so P6 numerical baseline
replay remains an outstanding integration step.

## Reproduction and pending deployment

Follow the [runbook](IMPLEMENTATION_TEST_PLAN.md) with fresh directories. Native
container execution is defined in
[the dedicated workflow](../../../.github/workflows/free-tools-native.yml).
Both geometry tools' receipts bind the tested source revision and local image
identities. A green CI container result is not a Kali host receipt. The PR stays
in draft until independent recovery and outstanding carrier/Qwen acceptance
work have been reviewed.

No model training, serving-default change, public artifact upload, paid rental,
scan migration or manufacturing release occurred. Raw model drafts and private
DVC metadata remain local. Public results contain hashes and scoped summaries.
