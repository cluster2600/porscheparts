# PicoGK-focused continuation

## Measured result — 1 October 2026

The 800-step continuation raises PicoGK validation from **9/40 to 40/40**.
OpenUSD validation falls from **22/30 to 17/30**, losing seven previous passes
while gaining two. It fails the predeclared retention rule, so the combined
assistant keeps `coding-003/checkpoint-600`. The new weights remain an
experimental candidate at `work/m64-qwen/coding-004/checkpoint-800/`.

| Validation domain | Previous adapter | New candidate | Previous passes lost |
|---|---:|---:|---:|
| PicoGK | 9/40 | 40/40 | 0 |
| OpenUSD | 22/30 | 17/30 | 7 |

These are validation results, not a final-test or engineering qualification.
The 24 fresh PicoGK tests remain unopened. No acceptance threshold was relaxed
to turn the candidate into a passing combined assistant. The
[machine-readable report](focused-results.json) records per-case outcomes,
response hashes, frozen inputs, adapter hashes and recovery receipts.

The run trained 137,913 tokens, reported 3.105 GB peak memory and validation
loss 0.010. All 40 validation C# answers ultimately pass the complete native and
semantic contract. This is a substantial improvement on the bounded graph tasks;
it does not establish performance on independent tasks or a cylinder head.

## Fixed experiment

Run `coding-004` continues the selected `coding-003` adapter on the existing Mac.
The experiment is fixed before execution: 800 steps, learning rate `1e-4`, rank 8,
MLX scale 20, last 16 layers, batch 1, 1,024-token context and seed 42. Existing
four-layer weights are loaded; the additional LoRA layers start with zero output.

The curriculum adds 512 training graphs, 16 validation graphs and 24 final test
graphs with new seeds and identifiers. Original training records and USD replay
are retained. Prior test partitions stay excluded from training. All previous
tests are now regression cases; only `pico3-test-*` is fresh in this experiment.
Shared grammar still limits what this benchmark demonstrates.

Every generated reference is checked against the literal beam parser and semantic
signature. Native checks cover the first 24 new training examples and every new
validation/test reference (64 programs), rather than claiming that all training
examples were individually run in PicoGK.

Only the final checkpoint is considered. Selection requires a strictly higher
PicoGK validation pass count and no lost validation passes in either PicoGK or USD.
Final tests are opened only after that rule passes. A rejected candidate does not
replace the previous adapter, and no model output authorises a cylinder-head build.

## Run

```sh
PICO="${PICOGK_RUNTIME_ROOT:?Set the reviewed PicoGK runtime directory}"
work/m64-qwen/venv/bin/python training/m64-qwen/improve.py \
  --focus-picogk --num-layers 16 --iterations 800 --learning-rate 0.0001 \
  --previous work/m64-qwen/coding-003 --output work/m64-qwen/coding-004 \
  --usd-reviewed work/m64-qwen/coding-002-prep/usd-verified.jsonl \
  --model work/m64-qwen/model-cache/models--mlx-community--Qwen2.5-Coder-1.5B-Instruct-4bit/snapshots/b3252a2f97102b1fb1571fec2c9b27219a8536be \
  --usd-python "${USD_PYTHON:?Set the reviewed OpenUSD Python executable}" \
  --sdk "$PICO/dotnet/dotnet" --dll "$PICO/picogk-bin/PicoGK.dll"
```

Status and raw receipts are saved under `work/m64-qwen/coding-004/`.

## Execution recovery

Disk exhaustion interrupted native validation after 20 generated answers and
also interrupted a repository test run. The original logs and partial receipts
are retained. Recovery reuses all 20 saved answers, reruns the one compilation
affected by `No space left on device`, and generates only the 20 remaining
validation answers with the same weights, prompts, greedy decoding and graders.
The recovered receipt covers the same ordered 40 case IDs. The USD scores had
already completed and were retained unchanged. Dataset/source hashes were
checked before recovery, and dataset hashes were checked again afterward.

Earlier runs' rebuildable compiler products were archived, with every archived
file checked against its original CRC and size. Duplicate binaries are stored
once in `work/m64-qwen/coding-002-003-compiler-products.tar.gz`; sources, model
weights, datasets and logs stay in place. No new model or cloud GPU was acquired.
Remaining disk space limits another training attempt. A future retention trial
should rebalance USD training replay, with the same untouched final-test gate.

## Repository verification

The recovered main suite passes 3,255 tests, including 160 optional-runtime
skips. Catalogue and additive-process validation, generated part pages and
tables, titanium screening, preview consistency and strict documentation links
pass (zero broken links across 645 Markdown files). The initial catalogue-count
failure was resolved by registering the new head in both material screens;
unknown service temperature now blocks titanium screening explicitly.

Full `make check` remains incomplete: it reaches the existing F37 LPBF Docker
audit and stops because the Docker daemon is unavailable. This is recorded as
an outstanding check, not a pass. No merge, manufacturing release or physical
validation is implied.
