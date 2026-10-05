# Qwen retention continuation

## Measured result — 2 October 2026

Two further local training trials completed **1,400 steps and 241,737 training
tokens**. Neither passes the unchanged retention rule. The selected coding
adapter remains `work/m64-qwen/coding-003/checkpoint-600/`; default inference
was not changed. The 24 fresh PicoGK final model tests remain unopened.

| Validation checkpoint | OpenUSD | PicoGK | Previous USD / PicoGK passes lost | Decision |
|---|---:|---:|---:|---|
| Retained coding-003 | 22/30 | 9/40 | — | Keep selected |
| Earlier focused coding-004 | 17/30 | 40/40 | 7 / 0 | Rejected |
| USD replay coding-005 | 16/30 | 25/40 | 7 / 2 | Rejected |
| Conservative coding-006 | 19/30 | 7/40 | 4 / 4 | Rejected |

Every loss above is relative to coding-003, not merely a net count change.
The [machine-readable report](retention-results.json) contains both new trials,
per-case outcomes, response hashes, source/data/weight hashes and log receipts.
The [earlier focused result](focused-results.md) and [selected coding result](coding-results.md)
remain separate historical records.

Coding-005's 30 USD answers pass the bounded native stage checks, but only 16
satisfy the requested scene contract. It produces 32 compiling PicoGK answers,
31 nonempty geometries and 25 complete passes. Coding-006 produces 21 native
USD passes and 19 complete passes; its PicoGK outputs include 38 compiling
answers, 36 nonempty geometries and only seven complete passes. A compiling
program or a lower token loss is insufficient for selection.

## Fixed experiments

Both trials use the pinned Qwen2.5-Coder-1.5B-Instruct 4-bit base on the Mac,
MLX-LM 0.31.3, rank 8, MLX scale 20, batch 1, 1,024-token context, prompt masking
and seed 42. Optimiser state restarts; adapter weights continue.

| Setting | coding-005 | coding-006 |
|---|---|---|
| Starting adapter | coding-004, step 800 | coding-003, step 600 |
| Trainable final LoRA layers | 16 | 4 |
| Additional steps | 600 | 800 |
| Learning rate | 5e-5 | 1e-5 |
| USD training replay | 4 | 4 |
| Original PicoGK training replay | 1 | 4 |
| Effective USD / PicoGK rows | 1,344 / 704 | 1,344 / 896 |
| Trained tokens | 105,813 | 135,924 |
| Reported validation loss | 0.012 | 0.024 |
| Peak memory | 3.106 GB | 2.118 GB |

The unique corpus is unchanged from coding-004: 336 USD and 704 PicoGK training
cases, 30 USD and 40 PicoGK validation cases, and 36 USD and 56 PicoGK final-test
cases. Repetition applies only to training. All split hashes were checked, and
validation/test files match coding-004 byte for byte. The same 64 native PicoGK
reference programs pass in each run; these are repeated checks, not 128 unique
programs. All fresh reference beam literals pass the semantic parser.

Only each trial's final checkpoint is eligible. Selection requires strictly
more PicoGK validation passes than coding-003, without losing any of its passing
USD or PicoGK validation cases. Graders and thresholds were not changed.
Both baselines were rerun and reproduced 22/30 USD and 9/40 PicoGK.

The first protocol was committed before its evaluation in `2e993ac`; the second
in `57aa24a`, after the first USD validation had failed but before the second
training began. Full commit and protocol hashes are in the registration receipts.
These are validation-driven trials in one adaptive experiment family. No claim
of an independent replication or new test-set accuracy is made.

## Reproduce

From the managed engineering checkout, with the existing pinned runtimes:

```sh
PICO="${PICOGK_RUNTIME_ROOT:?Set the reviewed PicoGK runtime directory}"
MODEL=work/m64-qwen/model-cache/models--mlx-community--Qwen2.5-Coder-1.5B-Instruct-4bit/snapshots/b3252a2f97102b1fb1571fec2c9b27219a8536be
USD_PYTHON="${USD_PYTHON:?Set the reviewed OpenUSD Python executable}"

work/m64-qwen/venv/bin/python training/m64-qwen/improve.py \
  --focus-picogk --num-layers 16 --iterations 600 --learning-rate 0.00005 \
  --usd-replay-weight 4 --previous work/m64-qwen/coding-003 \
  --warm-start work/m64-qwen/coding-004/checkpoint-800 \
  --output work/m64-qwen/coding-005-reproduction \
  --usd-reviewed work/m64-qwen/coding-002-prep/usd-verified.jsonl \
  --model "$MODEL" --usd-python "$USD_PYTHON" \
  --sdk "$PICO/dotnet/dotnet" --dll "$PICO/picogk-bin/PicoGK.dll"

work/m64-qwen/venv/bin/python training/m64-qwen/improve.py \
  --focus-picogk --num-layers 4 --iterations 800 --learning-rate 0.00001 \
  --usd-replay-weight 4 --replay-weight 4 --previous work/m64-qwen/coding-003 \
  --output work/m64-qwen/coding-006-reproduction \
  --usd-reviewed work/m64-qwen/coding-002-prep/usd-verified.jsonl \
  --model "$MODEL" --usd-python "$USD_PYTHON" \
  --sdk "$PICO/dotnet/dotnet" --dll "$PICO/picogk-bin/PicoGK.dll"
```

Outputs must not already exist. The run manifest records exact commands,
revisions and hashes. Model inference is offline. No paid GPU, Kali execution,
model-hub upload or default-model replacement was performed.

The new adapters remain at `work/m64-qwen/coding-005/checkpoint-600/` and
`work/m64-qwen/coding-006/checkpoint-800/`. Weights and raw responses remain in
ignored `work/`; GitHub contains the code and measured reports. Their weight
SHA-256 values are respectively:

- `64e3c57827d867f052c095efc84265d6bcb8509cf548aea3946826c40c5ddfb4`
- `1bd3d039e63a5dab87149af7a3762ab56099dc42b8364d732afcc8b5de56db4f`

The retained coding-003 adapter SHA-256 remains
`a1014c6f71b46d879c09462c4a57d17d00df8f11b8178dd53bf6d5f2ac2f778a`.

## Verification and limits

The repository test suite passes: 3,256 tests run with 160 optional-runtime
skips. After report generation, all six focused tests also pass, including a
new experiment-identity and receipt-consistency check. The added replay check verifies that repetition cannot add validation or
test records to training or duplicate evaluation cases. Full `make check`
stops at the existing F37 LPBF audit because the Docker daemon is unavailable.
Catalogue-generated pages/tables, the reports index, titanium screening,
previews and help checks pass. Strict links pass across 646 Markdown files
with no broken links.

The checks cover bounded literal PicoGK beams and selected Pixar Python APIs.
They share task grammar with training. Older model test cases are already
exposed regression cases; only the 24 pico3-test cases remain untouched by
model inference. Their reference programs were checked independently. The
installed Pixar wheel still excludes ShaderPropertyTypeConformanceChecker
because shader-discovery resources are absent.

Additional USD replay alone did not recover retention, and the smaller update
also regressed. These observations do not establish that further steps will
help. A subsequent experiment needs a different hypothesis, such as broader
reviewed USD composition data or a larger backbone, with a newly registered
protocol and the same honest separation of validation and final tests.
No OpenFOAM competence, cylinder-head fidelity, material qualification,
manufacturing release or physical validation is established by these scores.
