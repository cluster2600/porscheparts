# Qwen3 precision iteration

The first [compact trial](runs/qwen3-compact-001/RESULTS.md) failed the registered
primary criterion (10/12 primary, 7/8 supplemental). Its raw outputs and
assessment are frozen. That test is now retired for development. A causal
addition and technical translation errors motivate this second iteration.

The base remains Qwen/Qwen3-4B-Instruct-2507 at
`cdbee75f17c01a7cc42f958dc650907174af0554` (Apache 2.0). No measured LoRA gain
is claimed without a paired base/adapter assessment.

## Training data and inference

`precision-qwen3-v7/` contains 59 examples: all 53 original factual targets,
plus six French/English corrections on three retired supplemental-test
paragraphs from training-source families. The original targets are unchanged;
all examples use the native Qwen3 chat template and assistant-only masks.
There are 28,898 sequence tokens, 2,282 supervised assistant tokens and a
maximum complete length of 903. All six training-source families and seven
languages remain represented. The earlier `precision-qwen3-v6/` export of 53
examples was prepared, but was not used for this run.

The new profile preserves exact property types, asks only for requested facts
and separates observation from causality. Its French glossary distinguishes
molten deposited beads from droplets, melt pool from a deposited track, and
recoil pressure from a generic reaction pressure. The glossary is an assistant
translation aid, not independently reviewed material data. The training data
and every prompt still carry licensed source text and references.

`precision-config-v7.json` uses CPU BF16 rank-8 q/v LoRA, one epoch, accumulation
2, gradient checkpointing and learning rate 2e-4. The new factual curriculum
avoids oversampling generic refusal templates. Actual steps, durations, losses,
base hashes and adapter hashes are recorded by `run_precision.py`.

## Actual outcome

The actual run completed 30 optimizer steps in 1,642.87 seconds, with mean
training loss 2.15966. It was **rejected on development**, before generating
any new final-test prediction: several answers became bare refusals, and one
confused substrate thickness with layer height. The complete trained adapter,
raw development answers and receipts are retained in
[runs/qwen3-precision-development-001](runs/qwen3-precision-development-001/RESULTS.md).
A lower training loss did not establish better scientific answers.

## Registered evaluation policy

The 12 development prompts comprise the eight old prompts plus two failed
primary questions and two supplemental questions from the retired first final
set. Three retired training-family paragraphs also enter corrective SFT, so
those development questions are not held-out accuracy evidence.

`precision-final-test.jsonl` has 12 questions in FR8/EN2/DE1/ZH1 on 12 unused
paragraphs of article-held-out Ti6Al4V and WAAM sources. Four test qualification
boundaries are critical. `precision-domain-benchmark.jsonl` has eight French
questions on eight unused training-family paragraphs, including three critical
boundaries. Neither set shares a paragraph with actual SFT or any earlier
benchmark. Historical untrained CPT full-text exports may contain these
paragraphs. Some concepts, including COMET and Ti6Al4V-to-copper scope, have
been evaluated before; fresh paragraphs do not establish new concepts.

The manifests register exclusions and source/file hashes before candidate
training. Acceptance uses the same policy as the first trial: all expected
references, at least 11/12 primary and 7/8 supplemental scientifically acceptable
answers, and every critical boundary correct. Lexical screens are necessary
reference checks, not scientific scores; assistant reviewers assess each answer
against the passage. Independent expert scores and reviewer fields stay blank.
If this test fails and a candidate changes, retire it and register a new test
before claiming untouched final evaluation again.

## Reproduce

Install the isolated CPU dependencies in [CPU_PILOT.md](CPU_PILOT.md).

```sh
python3 training/qwen-metal-additive-20261002/run_precision.py
HF_HUB_DISABLE_XET=1 TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 \
work/metal-cpu-env/bin/python training/qwen-metal-additive-20261002/run_precision.py \
  --run --output work/metal-qwen3-precision-new --cache work/metal-model-cache
```

`prepare_precision_v7.py --output /fresh/directory --snapshot /pinned/snapshot`
reproduces the actual dataset. Its manifest binds the producer, inference
profile/helper, original frozen releases, license and all resulting files.

For a future candidate that passes development, freeze a selection file with the training
receipt, weights, profile/helper hashes and per-question assistant decisions,
then run `evaluate_precision.py` with `--source`, `--selection`, `--output` and
`--cache`. It generates paired 12-question base/adapter results plus eight
adapter supplemental responses without reselection. `package_precision.py`
retains raw results and portable tensors; `verify_precision_package.py` verifies
provenance and recomputes screens. The earlier failed trial remains separately
available and is bound by its manifest hash.

This text model explains supplied evidence. The benchmark does not validate a
numerical solver, a material-property surrogate, fatigue life or any Porsche
part. Scientific and multilingual translation review by qualified people is
still pending. Sources and CC BY 4.0 attribution remain in the frozen
`grounded-v3/sources.json` and linked license evidence.
