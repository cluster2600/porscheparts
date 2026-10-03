# Evidence-based Qwen3 explanations

The candidate pairs the actually trained conservative 24-example Qwen3 LoRA
adapter with the `source-v10` inference profile. The profile requests a direct
answer and a short justification from the supplied licensed passage. It keeps
residual stress, yield strength, deposited beads and recoil pressure distinct.
The generic glossary is a translation aid, not independent expert review.

The base is Qwen/Qwen3-4B-Instruct-2507, pinned to
`cdbee75f17c01a7cc42f958dc650907174af0554`. The unchanged adapter tensors have
SHA-256 `fb6ab78bf8868a1e77e3c1c5e156eeef63b0b3e42378aaa1410e8c7cfaf1d5cb`.
Actual CPU BF16 rank-8 q/v LoRA training completed 12 optimizer steps and one
epoch in 686.19 seconds. It supervised 1,388 assistant tokens in 24 French and
English examples from all six training-source families. Its 144 finite tensors
contain 2,949,120 trainable parameters. The public base weights are downloaded
separately, using the pinned revision; they are not copied into the repository.

## Actual outcome

This profile was rejected early on the second registered primary test. Twelve
base predictions and two adapter predictions were generated. The two adapter
answers add unsupported restrictions/comparisons, making the required 11/12
primary score impossible. No domain answer was generated; no complete final
score is claimed. See
[runs/qwen3-source-profile-001](runs/qwen3-source-profile-001/RESULTS.md).
The full second benchmark is retired for future final evaluation.

## Selection and evaluation

The first final test is retired after its failed 10/12 primary result. A second,
59-example training run was rejected on development for factual errors and
unhelpful answers; its tensors and evidence remain archived. Development of
the new inference profile uses only the twelve retired development questions.
The conservative weights are unchanged, so any improvement over the first
trial also involves a prompt change. A paired base/adapter evaluation uses the
same profile; do not attribute success to LoRA without measured evidence.

The new registered evaluation consists of twelve unused paragraphs from two
article-held-out sources (French, English, German and Chinese) and eight unused
paragraphs from training-source articles (French). Some concepts have appeared
before; this tests fresh paragraphs rather than entirely new task concepts.
The manifests bind excluded inputs and paragraph identities. The rule requires
all twenty expected citations, at least 11/12 primary and 7/8 supplemental
scientifically acceptable answers, and every one of seven critical boundaries.
Assistant assessments are separate from lexical screens. Human scientific and
translation review remain pending.

## Reproduction

Use the isolated CPU environment documented in [CPU_PILOT.md](CPU_PILOT.md).
`run_compact.py` and `compact-config.json` reproduce the actual conservative
training. `compare_source_precision_profile.py` generates paired development
answers with the new profile and writes its provenance receipt. Freeze a
selection only after reviewing the development answers, before any new final
prediction. The selection binds the exact weights, base revision, training
receipt, inference profile/helper and development comparison receipt.

```sh
OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 HF_HUB_DISABLE_XET=1 TOKENIZERS_PARALLELISM=false \
work/metal-cpu-env/bin/python training/qwen-metal-additive-20261002/evaluate_selected.py \
  --source work/metal-qwen3-run-001 --selection work/qwen3-evidence-selection-001.json \
  --comparison work/metal-source-precision-profile-001 \
  --output work/metal-qwen3-evidence-final-new --cache work/metal-model-cache
```

`package_selected.py` preserves raw predictions, assistant assessment, receipts,
portable adapter tensors and both the training and inference profile identities.
`verify_selected_package.py` recomputes integrity, question expansion, reference
screens and the recorded acceptance rule. Hashes establish provenance, not
scientific truth. Do not reuse a failed final test as an untouched test after
changing the candidate.

This is a text explanation model using an explicitly supplied passage. It is
not a numerical simulator, material property surrogate, fatigue-life predictor
or certification of any manufactured part. Sources and CC BY 4.0 attribution
remain in `grounded-v3/sources.json` and their linked licensing evidence.
