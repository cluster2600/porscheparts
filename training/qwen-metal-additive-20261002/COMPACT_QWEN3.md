# Compact Qwen3 evidence-grounded cycle

The Qwen2.5 1.5B corrective run learned source-ID syntax and refusal patterns,
but its explanations remained generic or incorrect. A quote-first two-example
profile did not reliably repair temperature dependence or Laves-phase reasoning.
Those runs are rejected on development, before any fresh final test is generated.

The next candidate is **Qwen/Qwen3-4B-Instruct-2507**, pinned to revision
`cdbee75f17c01a7cc42f958dc650907174af0554`, with 4,022,468,096 parameters and
Apache 2.0 license. This is still a compact model, though larger and slower than
the original 1.5B candidate on the available four-core CPU.

`compact-qwen3-v5/` contains 24 French/English examples in 12 source-grounded
case families, retaining all six training-source families. It emphasizes
facts and their verbatim evidence rather than repeated generic refusals.
Each complete example uses the pinned Qwen3 tokenizer/template and assistant-only
labels; no row is truncated. Total tokens per epoch: 11,479, including 1,388
assistant-target tokens. Maximum complete sequence length: 837.

The CPU BF16 LoRA profile uses rank 8 on q/v projections, learning rate 5e-5,
one epoch, accumulation 2 and gradient checkpointing for the 16 GiB runtime.
`compact-config.json` registers all conditions. Base and adapter development
predictions use the same evidence profile and deterministic output budget.
Actual optimizer steps, durations, dependencies and weight hashes are recorded
by `run_compact.py`. A stronger base must not be described as a measured LoRA
improvement; the paired base/adapter comparison separates those effects.

## Reproduce development

Use [CPU_PILOT.md](CPU_PILOT.md) to install the isolated CPU dependencies:

```sh
python3 training/qwen-metal-additive-20261002/run_compact.py
PYTHONUNBUFFERED=1 HF_HUB_DISABLE_XET=1 TOKENIZERS_PARALLELISM=false \
OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 work/metal-cpu-env/bin/python \
  training/qwen-metal-additive-20261002/run_compact.py \
  --run --output work/metal-qwen3-new-run --cache work/metal-model-cache
```

To regenerate the data in a fresh directory, run `prepare_compact.py --output
/fresh/path --snapshot /pinned/qwen3/snapshot`. The manifest hashes the producer,
model/tokenizer profile, license, training arrays and parent source release.

## Select the inference profile on development only

The original quote-first profile is retained as the executed training-run
control. Explicit source-tail v2 was rejected because it turned a compared wire
diameter into an optimum without explicitly rejecting certification. The longer
v3/v4 and verbatim v5 variants introduced unsupported technique attributes,
translation errors or inaccurate quotations and were stopped on development.

`concise-qualified-profile.json` and `concise_qualified_profile_v7.py` preserve
the measured concise v2 prompt for ordinary questions. A general keyword route
adds an explicit evidence boundary when the actual question requests
certification or qualification. It does not inspect expected answers, source
IDs or benchmark IDs. The source text is data, never routing instructions. The v7 helper explicitly
splits both REFERENCE and EXCERPT formats and uses a registered question field
when present. Its development messages are checked for byte-identical
equivalence to the actually executed v6 comparison; reused predictions are
labeled as reuse, not new generations.
These are inference instructions, not extra trained knowledge or a solver.

```sh
HF_HUB_DISABLE_XET=1 TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 \
work/metal-cpu-env/bin/python training/qwen-metal-additive-20261002/compare_concise_qualified_profile.py \
  --source work/metal-qwen3-new-run --output work/qwen3-profile-development \
  --cache work/metal-model-cache
```

For the archived v6 comparison, prove exact development-input equivalence after
fixing source-text routing (no new inference is claimed):

```sh
python3 training/qwen-metal-additive-20261002/bind_profile_equivalence.py \
  --source work/qwen3-profile-development --output work/qwen3-profile-equivalent
```

## Final evaluation and release

Inspect all eight development responses against the original passage rubrics.
Freeze the chosen model/adapter hash and profile before generating the 12 new
source-held-out questions or eight additional unseen-paragraph transfer questions.
See [CORRECTIVE.md](CORRECTIVE.md) for their distinct scopes and acceptance rules.
The final evaluator does not use either benchmark for checkpoint selection.

```sh
OMP_NUM_THREADS=1 work/metal-cpu-env/bin/python \
  training/qwen-metal-additive-20261002/audit_cpu_adapter.py \
  --adapter work/metal-qwen3-new-run/adapter/adapter_model.safetensors \
  --output work/metal-qwen3-new-run/adapter-audit.json
HF_HUB_DISABLE_XET=1 TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 \
work/metal-cpu-env/bin/python training/qwen-metal-additive-20261002/evaluate_compact.py \
  --source work/metal-qwen3-new-run --selection work/qwen3-selection.json \
  --output work/metal-qwen3-new-final --cache work/metal-model-cache
```

The selection file binds `development_receipt_sha256`,
`checkpoint_weights_sha256`, `inference_profile_sha256`,
`inference_helper_sha256`, `comparison_receipt_sha256`, `accepted_on_development` and the passage-by-passage
assistant assessment. Set `checkpoint: "adapter"` and
`independent_expert_validated: false`. Independent expert fields remain blank.

The package retains raw predictions, actual expanded questions, syntactic
screens, separate assistant assessment and integrity receipts. It includes
portable adapter tensors and the original saved configuration; only the public
base identifier and revision are normalized. Base weights and redundant
upstream tokenizer assets are excluded.

An assistant's assessment of a small registered benchmark does not establish
universal correctness, a validated numerical surrogate or manufacturing
qualification. Independent scientific and translation review remains pending.
Data attribution and CC BY 4.0 notices remain in
[grounded-v3/sources.json](grounded-v3/sources.json) and linked license evidence.

## Inspectable inference

The result adapter is loaded by `answer_metal.py` with the pinned base and v7
routing helper. Supply an explicit passage ID and question; the result returns
the excerpt, DOI/URL, reference check and response. Its guard rejects missing or
extra known-format references and incomplete generations. The guard does not
check scientific truth, perform retrieval or establish engineering validity.

```sh
HF_HUB_DISABLE_XET=1 TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 \
work/metal-cpu-env/bin/python training/qwen-metal-additive-20261002/answer_metal.py \
  --adapter training/qwen-metal-additive-20261002/runs/qwen3-compact-001/adapter \
  --cache work/metal-model-cache --passage '[NEW_WAAM:p46]' --language fr \
  --question 'Ce passage donne-t-il un diamètre de fil certifié pour ma pièce ?'
```

## Infrastructure interruption

The first registered final run was interrupted by an environment restart after
11 base responses. `resume_compact.py` preserves that exact partial output and
checks the frozen selection, original expanded questions, data, adapter config
and base hashes before generating only the missing base response, then the
adapter tests. It records an interruption receipt and its executed code hash.
No model, training data, profile or selection was changed after testing began.
Resumption wall time and total per-response generation time are separate.
