# Evaluation record

Audit against the AGENTS.md local-training rule (source/model revisions,
disjoint evaluation data, measured results), 2026-11-05, issue #423.
Every value below is copied from the files cited; nothing was re-run and no
missing value was estimated. "Not published" means the value lives only in
private receipts outside the repository.

| Item | Record |
|---|---|
| Base model | `mlx-community/Qwen3.8-27B-4bit` revision `10c35caafbb80f7dc6a7a432cdd11af10a6d4818`; native signature SHA-256 in [results.json](results.json) `model.native_signature_sha256` |
| Training | **None.** No adapter or optimizer was used (`permissions_and_scope.adapters_loaded: false`); inference-only pilot |
| Source revision | Per-case and provenance hashes in [cases.json](cases.json) and [results.json](results.json); no source commit published |
| Held-out split | **None.** Eight exposed, owner-authored development requests; no disjoint or reserved test set |
| Measured results | 8/8 correct against 6/8 for the deterministic parser; complete proposals 4/4 against 2/4; critical 4/4 against 4/4; exact two-sided p = 0.5, descriptive only |
| Decision | **No model was kept.** No weights were produced; the deterministic parser is retained (`baseline_retained: true`) |
