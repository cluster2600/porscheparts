# Evaluation record

Audit against the AGENTS.md local-training rule (source/model revisions,
disjoint evaluation data, measured results), 2026-11-05, issue #423.
Every value below is copied from the files cited; nothing was re-run and no
missing value was estimated. "Not published" means the value lives only in
private receipts outside the repository.

| Item | Record |
|---|---|
| Base model | `mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit` snapshot `b3252a2f97102b1fb1571fec2c9b27219a8536be`, weights SHA-256 `daeab4764fb420d161721791cf2e509e2de81a7af4223646e7bed2bf82c57b58` (asserted in [train.py](train.py)) |
| Parent adapter | `work/qwen-engineering-005/checkpoint-1200`, SHA-256 `70142a4583f5c95a74b3a5dd6661d8243e85e7846dc7aba6e8b4ab3c6a3f29d4` (asserted in [train.py](train.py)) |
| Source revision | Written as `registered_commit` into the private `runtime.json`, whose hash appears in [results-001.json](results-001.json) `files_sha256`; the commit itself is **not published** |
| Held-out split | 677 train, 40 validation, 40 test. All appearances of a part number share one partition; manual partitions are grouped by page; prompt recipes are shared ([README](README.md)) |
| Measured results | Validation 10 to 40/40, test 13 to 40/40, no regressions (4 categories of 10). Free-question checks rejected (`natural_language_checks`) |
| Test set | Opened once, after the validation gate passed |
| Decision | Adapter `89f03a87582fe287c6f718e7fef17745171441716ea4d99e83514a0cf12064ca` kept as a **separate experimental adapter**: `default_replaced: false`, `qualified: false`. Coding retention was not measured, so it is not eligible for general promotion |
| Gaps | Source commit not published; coding retention not measured |
