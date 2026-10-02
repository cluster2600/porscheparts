# Passage-grounded Qwen pilot, version 3

Use **`grounded-v3/`** for the new pilot. V1/v2 remain historical exports: do not
combine their overlapping rows with v3. No model weights were downloaded and no
training or model evaluation was run during preparation.

## Selected model and pilot

The starting model is **Qwen/Qwen2.5-1.5B-Instruct**, revision
`989aa7980e4cf806f80c7fef2b1adb7bc71aa306`: a small general instruction model for
multilingual technical dialogue, not a measured winner over other variants.
The upstream model card and Apache-2.0 notice are pinned in
`grounded-input/model-card.md`. Tokenizer/template hashes and formatter versions
bind token arrays to this exact profile. Do not substitute v2's Coder-model arrays.

The future pilot uses single-GPU NF4 QLoRA, rank 8 on `q_proj`/`v_proj`, alpha 16,
dropout 0.05, learning rate 5e-5, one epoch, batch 1 and accumulation 8. These are
starting defaults, not optimized parameters. The runtime requires a CUDA GPU
supporting bfloat16; GPU memory use and the pinned training dependency stack
have not been measured or executed here.

## Files and scope

| Files | Content |
| --- | --- |
| `cpt_text/{train,valid,test}.jsonl` | 73 scientific sequences: 50/9/14 |
| `cpt_tokens/{train,valid,test}.jsonl` | All-token CPT labels, including one EOS |
| `sft_messages/{train,valid,test}.jsonl` | 90 grounded conversations: 53/16/21 |
| `sft_tokens/{train,valid,test}.jsonl` | Assistant content/EOS loss only |
| `passages.jsonl`, `provenance.jsonl` | Cleaned passages, identifiers, hashes and case families |
| `sources.json`, `coverage.json` | Attribution, licenses, partitions and topic/language coverage |
| `review-ledger.jsonl`, `legacy-review.jsonl` | Review worksheets and exclusion of the old explanations |
| `evaluation/questions.jsonl`, `evaluation/rubrics.jsonl` | Eight novel questions and criteria: four validation, four test |
| `quarantine.jsonl`, `near-duplicates.jsonl` | Exclusions and similarity findings |
| `manifest.json`, `model-profile.json`, `dataset_info.json` | Integrity, tokenizer profile and LLaMA-Factory mapping |

JSONL contains one independent row per line. Trainer files have only the trainer
schema; provenance is separate. Every SFT prompt includes the relevant English
paragraph. Targets contain a contextual answer, passage citation and, where
available, a verbatim supporting quotation. One case explicitly declines to
invent a certified powder property. This targets grounded reading with supplied
evidence, not closed-book expertise.

There are **40 distinct questions**, each in French and English. Two concepts
also have German, Chinese, Japanese, Spanish and Portuguese drafts. The 90
variants are not 90 independent questions. English evidence quotes are kept
verbatim. Translations remain assistant drafts pending independent review.

Ten independent English full-text articles expand the previous seven-article
scope. New CC BY 4.0 reviews cover residual stress, WAAM thermomechanical modeling
and quality monitoring. Six articles are training, two validation and two test.
An article/DOI and all its tasks/translations stay in one partition across CPT,
SFT and evaluation; old held-out articles remain held out. Validation now covers
microstructure and monitoring, and test titanium microstructure and WAAM.
Alloy/topic coverage remains uneven, as exposed in `coverage.json`.

## Checking and independent review

Preparation verifies snapshot hashes, DOI/title, authors, recorded license
evidence, passage hashes and supporting quotes. Detected formulas/images,
tables, captions and administrative text are quarantined. Recognized HTML
superscripts/subscripts are preserved as Unicode. Paragraph hashes describe
normalized extraction, not original HTML bytes; snapshot hashes cover original
bytes. Other numerical claims and unrecognized notation still need review.

Nested duplicate list text is excluded. Exact duplicates are rejected.
Cross-source five-word-shingle Jaccard similarity at least 0.8 is reported;
cross-partition matches block export until source families are regrouped. This
lexical detector does not prove absence of semantic duplication.

The new cases were authored after checking their paragraphs. The original 30
synthetic explanations are excluded pending passage review. Bibliographic drills
stay separate in v2 and are not mixed into this scientific pilot.

**Independent expert review remains pending.** Quotations do not establish that
every paraphrase, causal claim, unit or translation is correct. Copy the ledger
into `work/` rather than modifying hashed exports. Use pseudonymous reviewer IDs,
record accept/revise/reject and a rationale, and check material, process,
temperature, geometry, uncertainty, units and scope. A substantive specialist
release should incorporate accepted decisions in a new versioned export.
Do not label pending rows expert approved or treat this pilot as manufacturing
qualification.

## Preparation checks and reproduction

These commands use standard Python and do not load weights:

```sh
python3 training/qwen-metal-additive-20261002/verify_grounded.py
python3 training/qwen-metal-additive-20261002/train_pilot.py
python3 training/qwen-metal-additive-20261002/predict_pilot.py
python3 -m unittest discover -s tests -p 'test_qwen_metal*.py' -v
```

For reproduction, install the formatter library versions recorded in the
manifest and supply the exact tokenizer files from `model-profile.json`:

```sh
python3 training/qwen-metal-additive-20261002/prepare_grounded.py \
  --tokenizer /absolute/path/to/pinned-tokenizer \
  --output work/qwen-grounded-reproduced
python3 training/qwen-metal-additive-20261002/verify_grounded.py \
  --output work/qwen-grounded-reproduced
```

Generation refuses existing output directories, enforces complete-example
budgets and never truncates SFT targets. CPT paragraphs remain whole without
overlap. Training padding preserves prompt/padding labels of `-100`.

## Future training and comparison

Entrypoints inspect the release by default. Only an explicit `--run` downloads
weights or starts GPU work. Install `pilot-requirements.txt` in a suitable
separate environment, then use:

```sh
python3 training/qwen-metal-additive-20261002/train_pilot.py \
  --run --output work/qwen-metal-adapter
```

Trainer uses only SFT training rows and validation loss, preserves precomputed
labels and saves an adapter, tokenizer and reproducibility receipt. Test rows
and metadata exercises never enter Trainer. CPT is optional and not part of
this first experiment. The GPU path has not been executed; only preparation
and preflight checks are validated here.

Tune on validation, freeze the experiment, then compare base and adapter using
identical prompts, NF4 quantization and deterministic decoding:

```sh
python3 training/qwen-metal-additive-20261002/predict_pilot.py \
  --run --output work/base-predictions.jsonl
python3 training/qwen-metal-additive-20261002/predict_pilot.py \
  --run --adapter work/qwen-metal-adapter --output work/adapter-predictions.jsonl
python3 training/qwen-metal-additive-20261002/evaluate_grounded.py \
  --predictions work/base-predictions.jsonl --output work/base-review
python3 training/qwen-metal-additive-20261002/evaluate_grounded.py \
  --predictions work/adapter-predictions.jsonl --output work/adapter-review
```

The helper requires all eight prediction IDs exactly once. Citation presence,
reported separately for validation/test, is a syntax check rather than accuracy.
An independent reviewer scores correctness, grounding, scope/uncertainty and
units/numbers: 0 incorrect, 1 partial, 2 meets criteria. Worksheets contain
reference answers, criteria and prediction hashes. Re-run with
`--reviews path/to/completed-review.jsonl` to aggregate complete manual scores;
unfinished review produces no invented scientific score. No predictions or
model results are included in this release.

For MLX or another trainer, use `sft_messages/` with native template and assistant
masking applied once. For LLaMA-Factory use the supplied mapping, Qwen template,
cutoff 2048, prompt training disabled and packing disabled; check the installed
version. Never train on evaluation prompts, test rows or review worksheets.
