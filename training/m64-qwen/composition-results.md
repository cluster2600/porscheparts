# Qwen three-object USD continuation

## Registered protocol — 2 October 2026

Coding-007 tests whether explicit three-object USD examples address the
composition failures seen in the rejected [retention trials](retention-results.md).
The earlier USD training corpus teaches one or two objects; its validation
includes three. This experiment adds 288 independently parameterized synthetic
training examples across the same six API recipes, plus 24 fresh final-test
instances. The source is the repository's authored OpenUSD generator. All new
reference programs must pass the existing bounded Pixar checks before training.
No validation answers are added to training, and the existing 30 USD / 40 PicoGK
validation cases and acceptance functions remain unchanged.

The run starts from the 16-layer coding-004 step-800 adapter, whose previous
validation was USD 17/30 and PicoGK 40/40. It uses the pinned 4-bit
Qwen2.5-Coder-1.5B-Instruct base, MLX-LM 0.31.3, rank 8, MLX scale 20,
batch 1, 1,024 tokens, prompt masking, seed 42, learning rate 1e-5 and
**600 additional steps**. Only the final checkpoint is eligible. Optimizer
state restarts. All USD training rows repeat twice; PicoGK rows appear once.
The corpus therefore has 624 USD / 704 PicoGK unique training rows and
1,248 / 704 effective training rows. This is an adaptive validation-driven
experiment, not an independent replication or an isolated causal comparison.

Selection requires a strict PicoGK validation gain over retained coding-003
and preservation of **every** previous USD and PicoGK validation pass. The
baseline is rerun. If the gate fails, keep coding-003 and leave final model
tests closed. If it passes, evaluate once on the old regression cases plus
the 24 untouched pico3-test cases and 24 new usd3-test cases. Fresh instances
still share API recipes with training; report their scores separately.

The Mac performs MLX training. Kali2 can run the previously blocked repository
Docker checks using the unchanged pinned image. Neither task requires a GPU
rental. These checks do not establish engineering or manufacturing validation.

## Execution

Run receipts and weights belong in ignored `work/m64-qwen/coding-007/`.
Generate with `openusd.py generate --composition`, verify the reference programs
with `openusd.py verify`, then pass that verified JSONL via `improve.py --usd-extra`.
Use `--focus-picogk --iterations 600 --num-layers 16 --learning-rate 0.00001
--usd-replay-weight 2 --previous work/m64-qwen/coding-003
--warm-start work/m64-qwen/coding-004/checkpoint-800` with the existing pinned
model and native runtime paths. Freeze hashes and this protocol's commit before
training. Execution results will be appended after the run finishes.
