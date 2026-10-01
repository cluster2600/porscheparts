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

## Conservative follow-up registration — coding-006

Coding-005's completed USD validation scores 16/30 and loses the same seven
previous USD passes as coding-004. Its PicoGK validation is still finishing
at registration of this follow-up; no final tests have been opened.

The second and final training trial in this continuation starts directly from
the retained `coding-003/checkpoint-600`, instead of the rejected 16-layer
candidate. It updates only the original last four LoRA layers for 800 steps at
`1e-5`. USD training examples are replayed four times; the 64 original PicoGK
training examples are also replayed four times. This gives 1,344 USD and 896
PicoGK rows (2,240 total), with the same 1,040 unique training cases. Rank, scale,
batch, context, masking, seed, validation/test splits, graders and selection
rule are unchanged. Only step 800 is eligible. Optimiser state restarts.

This adjustment uses validation results from the same experiment family. It
does not turn previously observed validation cases into an independent test.
Raw receipts will be saved under `work/m64-qwen/coding-006/`.
