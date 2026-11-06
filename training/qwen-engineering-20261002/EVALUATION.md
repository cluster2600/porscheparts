# Evaluation record

Audit against the AGENTS.md local-training rule (source/model revisions,
disjoint evaluation data, measured results), 2026-11-05, issue #423.
Every value below is copied from the files cited; nothing was re-run and no
missing value was estimated. "Not published" means the value lives only in
private receipts outside the repository.

| Item | Record |
|---|---|
| Base model | `mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit` snapshot `b3252a2f97102b1fb1571fec2c9b27219a8536be` ([run.py](run.py)); weights SHA-256 `daeab4764fb420d161721791cf2e509e2de81a7af4223646e7bed2bf82c57b58` ([results.json](results.json) `base_sha256`) |
| Parent adapter | `coding-003/checkpoint-600` (`warm_start_adapter`); parent hash not published |
| Source revision | Registered code commit `a7fa1dbfbf72cdd58f82704092b4b03a258348c7`; helper files recovered from `57932831f0f4256abb5ebad95fe5094b21e43d4d` |
| Held-out split | 32 new validation and 32 fresh test rows (8 per domain) from [curriculum.py](curriculum.py), plus 70 earlier USD/PicoGK validation cases for retention. Fixture names are disjoint; task recipes are shared ([README](README.md#frozen-protocol)) |
| Measured results | New validation: Python 0 to 8/8, OpenFOAM 0 to 8/8, OpenUSD 8 to 8/8, PicoGK 0 to 4/8. Retention: USD 22 to 25/30, PicoGK 9 to 34/40. Regressions `usd-valid-004`, `usd2-valid-017` |
| Test set | Not opened (`selection.fresh_tests_opened: false`) |
| Decision | **Rejected** (`selection.decision`). Candidate adapter `eee6ac87e5f9b3f65a61238e5c54ab23cac419b31d94ccaaad056bb033dcdfd1` stays private as a record only and is not served. Default adapter unchanged |
| Gaps | Parent adapter hash not published |
