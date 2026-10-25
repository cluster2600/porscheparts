# Execution results — 25 October 2026

These results separate native software execution, documentary model quality,
host deployment and physical engineering acceptance. Source and runtime details
are retained in the [machine-readable report](../../../benchmarks/free-tools/results/mac-20261025.json).

| Check | Measured result | Scope |
|---|---|---|
| Frozen carrier inputs | SHA-256 verification and admission replay completed | Existing catalogue-selected geometry preserved; R2 remains unadopted |
| FTS5 evaluation | 10/10 references, 10/10 unknown boundaries, 5/5 conflicts, 5/5 hostile-document boundaries | Authored 30-case retrieval test, not model-answer accuracy |
| DVC Mac recovery | Actual registered inputs restored into a fresh private cache and rehashed | Primary Mac store only |
| DVC failure controls | Two independent local test stores, corrupt/missing objects and simulated interruption checked | The two local test directories do not establish a Kali backup |
| OpenTURNS native | First-order indices 0.1994288501 and 0.8017120442 | Synthetic expected 0.2/0.8, absolute tolerance 0.03 |
| OpenMDAO native | Thickness 0.010455159171866592 m; independent target 0.010455159171494206 m | Synthetic constrained beam; separate analytical process and independent replay |
| Carrier external component | Executed admission replay; `blocked_engineering` | No new carrier FEM solve or optimization claimed |
| Local Qwen documentary inference | Actual MLX inference attempted; malformed draft rejected | Documentary adaptation is unqualified; original geometry command unchanged |
| CloudCompare | Separate native Linux workflow required | Local Docker daemon did not answer the bounded check |
| SALOME/NETGEN | Separate native Linux workflow required | Pinned third-party distribution; no local native result claimed |
| Kali independent recovery | Unexecuted | Thunderbolt peer observed; SSH port 22 did not answer; actual identity required |

The optional native Python suite passed with one explicit CloudCompare skip.
Its negative controls deliberately include an infeasible optimization, which
prints an optimizer failure while the test correctly verifies rejection.

The carrier's independent contract still lacks measured interfaces and loads;
the registered R2 comparison does not establish mesh convergence. The tools
therefore cannot authorize carrier optimization, fitment, strength, fatigue,
LPBF process suitability or manufacturing.

## Reproduction and pending deployment

Follow the [runbook](IMPLEMENTATION_TEST_PLAN.md) with fresh directories. Native
container execution is defined in
[the dedicated workflow](../../../.github/workflows/free-tools-native.yml).
Workflow receipts must be inspected before upgrading either geometry tool's
execution status. A green CI container result is not a Kali host receipt.

No model training, serving-default change, public artifact upload, paid rental,
scan migration or manufacturing release occurred. Raw model drafts and private
DVC metadata remain local. Public results contain hashes and scoped summaries.
