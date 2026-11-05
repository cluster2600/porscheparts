# Evaluation record

Audit against the AGENTS.md local-training rule (source/model revisions,
disjoint evaluation data, measured results), 2026-11-05, issue #423.
Every value below is copied from the files cited; nothing was re-run and no
missing value was estimated. "Not published" means the value lives only in
private receipts outside the repository.

| Item | Record |
|---|---|
| Base model | Qwen2.5-Coder-1.5B-Instruct 4-bit at `b3252a2f97102b1fb1571fec2c9b27219a8536be`, weights SHA-256 `daeab4764fb420d161721791cf2e509e2de81a7af4223646e7bed2bf82c57b58` ([README](README.md#fixed-runtime-and-training-protocol)) |
| Parent adapter | Retained r3, SHA-256 `2f5da92d4cf9dff0f8b6bac8b28d5c34d26323ca780adf18cdcf11dd88249e1f` (`baseline_adapter_sha256`) |
| Source revision | Work began on merge commit `39bb313f3a33d02c6ab58dd227616ed980a51c15` (PR 205); the exact runner commit is not published |
| Held-out split | 720 train, 60 validation, 60 reserved test; each explicit parameter tuple occurs in only one partition; recipe and grammar families are shared |
| Measured results | First continuation: validation 19 to 58/60, old plans 43/48 software (47/48 semantic), code retention 8/16. Corrective continuation: 19 to 57/60, old plans 48/48, code 16/16, three categories below the floor ([results.json](results.json)) |
| Test set | Not opened for either candidate |
| Decision | **Both candidates rejected** (`eligible: false`; `completed_rejected_by_development_gate`). Adapters `49932d886a4014b3ac200065d6a974fada79b009c28b73213b2590a18b62454d` and `f51ea1acbfee302303cd617d87f515f747d569830f148a7dcee7a56092960260` stay private as records only; serving adapter unchanged |
