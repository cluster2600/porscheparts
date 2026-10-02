# Corrective Qwen experiments

The first CPU pilot exposed missing citations, unsupported qualifications,
contradictory generalizations and poor French terminology. Its eight inspected
questions are now **development only**, including the four originally marked
as test. Their answers cannot establish a fresh generalization result.

`corrective-v4/` is a new, immutable release derived from the licensed v3 source
passages. It retains 53 original training examples across seven languages and
adds 138 French/English examples with verbatim evidence windows. Added tasks
include quoting evidence, distinguishing a study from qualification of a new
component and declining a certified fatigue life absent from the excerpt.
Repeated targets teach behavior; they are not independent experimental evidence.
No validation/test-source text or target enters training. Translation and
scientific review remain assistant drafts pending independent expert review.

The release has 191 examples, 46,785 sequence tokens and 7,182 assistant-target
tokens per epoch. Maximum sequence length is 737 with no truncation. A separately
registered final benchmark has 12 new questions from unused paragraphs of two
source-held-out papers, in French, English, German and Chinese. Questions and
rubrics are frozen before candidate generation. This is small and does not
measure comprehensive expertise in metallurgy or other languages.

An additional eight-question domain benchmark covers copper conductivity and
units, heat losses, powder-model temperature limits and melt-pool forces. Its
passages are absent from training examples but come from training source
families. Report that transfer check separately from the source-held-out test.
It is registered before candidate predictions in `corrective-domain-manifest.json`.

## Experiment and selection

The CPU BF16 experiment starts from the same pinned public base, uses rank 8
LoRA on q/v projections, two epochs, learning rate 3e-4 and accumulation 4.
Each epoch produces a checkpoint. Development predictions use the same short
answer system instruction and deterministic 192-token budget for the base and
all checkpoints. Gradient checkpointing is disabled in this short-example run.
See `corrective-config.json` for the registered profile.

Development screens require exact source citations and flag affirmative answers
to critical scope questions. They are lexical checks, not semantic scores.
Inspect all eight candidate answers against the saved passage rubrics before
accepting a checkpoint. Freeze the chosen checkpoint hash and the development
assessment before generating any final-test prediction.

Final acceptance requires all 12 expected citations, at least 11/12 answers
passing passage-by-passage assistant assessment and no invented qualification,
unsupported certified parameter or failed critical boundary. Automated keyword
screens are reported separately; independent expert scores remain blank.
If the final test fails, retire it into development and register a fresh held-out
benchmark before another selection cycle. Do not tune against the same final
answers and describe them as an untouched test.

## Commands

Use the CPU environment documented in [CPU_PILOT.md](CPU_PILOT.md). The default
runner audits immutable data without importing an ML framework:

```sh
python3 training/qwen-metal-additive-20261002/run_corrective.py
PYTHONUNBUFFERED=1 HF_HUB_DISABLE_XET=1 TOKENIZERS_PARALLELISM=false \
OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 work/metal-cpu-env/bin/python \
  training/qwen-metal-additive-20261002/run_corrective.py \
  --run --output work/metal-corrective-new-run --cache work/metal-model-cache
```

After inspecting development responses, write a selection record containing
`accepted_on_development`, `checkpoint`, `checkpoint_weights_sha256`,
`development_receipt_sha256`, the assistant assessment and
`independent_expert_validated: false`. The final evaluator rejects an absent
acceptance, changed inputs or a different checkpoint:

```sh
HF_HUB_DISABLE_XET=1 TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 \
work/metal-cpu-env/bin/python training/qwen-metal-additive-20261002/evaluate_corrective.py \
  --source work/metal-corrective-new-run --selection work/selection.json \
  --output work/metal-corrective-new-final --cache work/metal-model-cache
```

The final evaluator records both base and adapter responses under identical
conditions, timing and integrity hashes. Review worksheets preserve reference
answers and evidence; independent reviewer and score fields stay blank.

For data reproduction, run `prepare_corrective.py --output /fresh/path
--tokenizer /pinned/snapshot`. Source authors, DOI, URL and CC BY 4.0 attribution
are retained in [grounded-v3/sources.json](grounded-v3/sources.json), its linked
license evidence and frozen parent manifest. Model license is
[Apache 2.0](MODEL-LICENSE.txt). New text answers remain evidence-conditioned
explanations, not validated numerical surrogates or manufacturing qualification.

## Ask a question against inspectable evidence

`answer_metal.py` loads the pinned base and the selected portable adapter. Supply
an explicit passage ID from `grounded-v3/passages.jsonl`; the result includes
the exact passage and its DOI/URL. This avoids treating a guessed retrieval
match as sufficient evidence. The command withholds output that omits its source,
invents an additional reference or exhausts the generation budget. That guard
checks syntax/completeness, not scientific truth, and is separate from raw model
evaluation. It does not select or tune a checkpoint.

```sh
OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 work/metal-cpu-env/bin/python \
  training/qwen-metal-additive-20261002/answer_metal.py \
  --adapter /path/to/selected/adapter --cache work/metal-model-cache \
  --passage '[MET002:p22]' \
  --question 'Augmenter toujours la puissance laser garantit-il un meilleur résultat ?'
```
