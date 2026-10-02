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
training.

## Coding-007 result

The run completed 600 steps and 121,935 training tokens, with reported
validation loss 0.001 and peak memory 3.274 GB. USD validation improved from
22/30 to 27/30; PicoGK improved from 9/40 to 39/40. All 30 USD answers pass the
available native checks, and all 40 PicoGK answers compile and run.
However, `usd-valid-004` and `usd2-valid-004` lose their previous passes because
the model selects small when large is requested. The candidate is rejected.
Coding-003 remains selected, and final model tests remain closed. See the
[machine-readable receipts](composition-results.json).

The previous Docker blocker is resolved on Kali2: all 15 F37 audit tests pass
in the existing pinned image. The first whole-repository attempts exposed user
CAD-package incompatibilities, missing isolated NumPy and file-mode assumptions.
Their logs are retained. Full repository validation will use the CI-pinned
NumPy/Matplotlib packages, an isolated Python environment and standard umask 022.

## Registered paired-selection follow-up — coding-008

This final follow-up tests a specific failure hypothesis: previous examples
correlate object naming patterns with small/large selection. Add 96 training
examples in matched pairs that keep the scene fixed and change only the final
selection. The references explicitly set the requested final variant. Add eight
fresh test cases in four matched pairs; preserve every existing validation case.
The new namespace is disjoint from earlier prompts. Verify every new reference
using the unchanged native authoring, snapshot and validation functions.

Continue coding-007 step 600 for **400 steps**, with the same 16-layer LoRA,
rank 8, scale 20, seed 42, batch 1, learning rate 1e-5, 1,024-token limit and
USD replay weight 2. Keep the 288 three-object examples. There are 720 USD / 704
PicoGK unique training rows, 1,440 / 704 effective rows, 30 / 40 validation cases,
and 68 / 56 final tests. Only the final checkpoint is eligible, compared against
coding-003 under the same strict per-case retention rule. Optimizer state restarts.
This is another adaptive validation-driven attempt; scores are not independent
replications. If it fails, retain coding-003 and stop this experiment family.

Use `openusd.py generate --variant-selection` and `verify`, combine its reviewed
rows with the frozen coding-007 extra USD rows, and pass that JSONL via
`--usd-extra`. Use the previous run command with `--iterations 400`, output
`work/m64-qwen/coding-008`, and warm start `coding-007/checkpoint-600`.
