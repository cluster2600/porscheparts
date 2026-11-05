# Evaluation record

Audit against the AGENTS.md local-training rule (source/model revisions,
disjoint evaluation data, measured results), 2026-11-05, issue #423.
Every value below is copied from the files cited; nothing was re-run and no
missing value was estimated. "Not published" means the value lives only in
private receipts outside the repository.

| Item | Record |
|---|---|
| Base model | `mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit` revision `b3252a2f97102b1fb1571fec2c9b27219a8536be` ([results.json](results.json) `model`) |
| Parent adapter | None; a fresh adapter from the base |
| Source revision | Protocol, receipt and source commitments as SHA-256 in `evidence_commitments_sha256`; no source commit published |
| Held-out split | **None disjoint.** Five exposed training rows in two dependent source groups and one exposed comparison case. Reserved evaluations stayed closed |
| Measured results | Source-only format passes: base 0, adapter 0 (two blinded reviews). Compilation and geometry not evaluated |
| Decision | **No model was kept for use.** Adapter `93f4d64cde2567fa8cffb222360131338fac1f1b737f52584d3bd5c9288c845e` not selected (`adapter_selected: false`); the base output was also rejected |
| Gaps | No disjoint evaluation data, so the run supports no improvement claim |
