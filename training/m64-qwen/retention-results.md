# OpenUSD retention continuation

## Predeclared experiment — 2 October 2026

Run `coding-005` continues `coding-004/checkpoint-800` on the existing Mac,
using the pinned Qwen2.5-Coder-1.5B-Instruct 4-bit base and MLX-LM 0.31.3.
The purpose is to recover OpenUSD retention while preserving PicoGK gains.
Only the final checkpoint is eligible: 600 additional steps, learning rate
`5e-5`, last 16 LoRA layers, rank 8, MLX scale 20, batch 1, context 1,024,
prompt masking and seed 42. Optimiser state restarts, adapter weights continue.

The unchanged `coding-004` corpus contains 336 USD and 704 PicoGK training
cases. Fourfold USD replay gives 1,344 USD and 704 PicoGK training rows.
Validation (30 USD, 40 PicoGK) and tests (36 USD, 56 PicoGK) are never replayed
or added to training. Inputs, source code and starting weights are hashed.

Selection keeps the existing rule against the retained `coding-003` adapter:
strictly more PicoGK validation passes, with no loss of any previously passing
USD or PicoGK validation case. No threshold or grader is changed. The rejected
`coding-004` validation results informed this continuation. This is one adaptive
experiment family, not an independent replication.

Only after validation selection may final inference open the 24 `pico3-test-*`
cases. Those model tests remain untouched at experiment registration; their
reference programs were previously checked natively. All older tests are
development-informed regression checks. Shared task grammar limits the claim;
none of these checks validates CFD, a cylinder head or a manufactured part.

## Execution

Results are pending. The existing selected adapter remains
`work/m64-qwen/coding-003/checkpoint-600/` until the continuation is evaluated.
Raw status, training logs and receipts will be under `work/m64-qwen/coding-005/`.
