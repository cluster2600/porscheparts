# Qwen3 source and condition fidelity

This iteration keeps the actually trained conservative Qwen3 LoRA tensors and
changes the inference profile separately. It requests relevant source facts,
preserves qualifiers and keeps each property attached to its own conditions.
A generic question-language rule selects a scope/qualification prompt or a factual
extraction prompt. No source ID, material name, numeric answer or predefined
response enters that rule. The factual prompt uses French translation aids only
when the term occurs in the excerpt. Both backend profiles/helpers are pinned
by the task profile, independently of the original training profile.
In particular, quasi-static strength and stress rupture remain distinct.
No numeric answer from the registered new test is embedded in the profile.

The base is Qwen/Qwen3-4B-Instruct-2507, revision
`cdbee75f17c01a7cc42f958dc650907174af0554` (Apache 2.0). The adapter SHA-256 is
`fb6ab78bf8868a1e77e3c1c5e156eeef63b0b3e42378aaa1410e8c7cfaf1d5cb`.
Actual CPU BF16 rank-8 q/v LoRA trained 24 French/English examples from all six
training-source families, with 1,388 supervised assistant tokens. Twelve steps
and one epoch took 686.19 seconds. Its 144 finite tensors contain 2,949,120
trainable parameters. This model explains an explicitly supplied passage; it
is not a trained numerical solver or a material-property surrogate.

## Actual final results

The [verified package](runs/qwen3-fidelity-001/RESULTS.md) passes the registered
prototype threshold: **11/12 primary and 7/8 supplemental**, all 20 citations
and all seven critical qualification boundaries. The paired base scores
**12/12 primary**. No LoRA gain is demonstrated; the base preserves a requested
gradual transition that the adapter omits. The supplemental base was not tested.
The other failed adapter response adds an unsupported dominant-influence claim.
Raw predictions, conservative and peer decisions, portable weights and exact
input provenance are packaged. These scores are assistant-reviewed, with human
scientific and translation review pending.

## Recorded failures and development

The first compact final test failed with 10/12 primary and 7/8 supplemental
answers. A larger 59-example SFT run was rejected on development. The source-v10
profile was rejected after two primary failures made its >=11/12 requirement
impossible. A first shorter fidelity profile then failed a property-condition
association during development. Each rejected experiment retains its raw
outputs and actual completion scope; interrupted runs do not claim full scores.

Two further development profiles were rejected for a property-condition error
and an incomplete passage copy. A separate erratum corrects an earlier
assessment claim: fatigue does occur in the Laves source; the rejection is
justified by the wrong property-temperature association.

The task-routed profile is developed on fifteen retired questions:
eight initial development questions, four earlier final/domain corrections,
and three failed questions from the retired precision primary test. Eleven
actual predictions are reused after proving byte-identical expanded messages,
unchanged weights/config and frozen source-code/raw evidence. Four changed
inputs were actually generated. Timings and origins are explicit. None is
reported as unseen development accuracy. No held-out-source article enters
SFT. Those articles have nevertheless appeared in development prompts, and
the public base model's pretraining exposure is unknown.

`fidelity-final-test.jsonl` has twelve questions (FR8/EN2/DE1/ZH1) on unused
paragraphs from the two articles held out of project SFT. The eight-question
French `fidelity-domain-benchmark.jsonl` uses unused training-family paragraphs.
The manifests exclude all earlier training/evaluation paragraphs and bind their
source/file hashes. Some concepts remain familiar: fresh paragraphs do not
prove generalization to entirely new concepts or engineering tasks.

The registered rule requires all twenty expected citations, >=11/12 primary
and >=7/8 supplemental scientifically acceptable answers, and all seven
critical boundaries. Lexical screens are not scientific accuracy. Each answer
is assessed against the paragraph by assistants; independent human scientific
and translation review remain pending.

## Reproduce

Use the pinned CPU environment in [CPU_PILOT.md](CPU_PILOT.md). Original executed
training remains `run_compact.py` with `compact-config.json` and its original
training profile. The final inference profile is separately hashed; training
receipts are never rewritten as if that later profile trained the tensors.

```sh
python3 training/qwen-metal-additive-20261002/audit_fidelity.py
OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 HF_HUB_DISABLE_XET=1 TOKENIZERS_PARALLELISM=false \
work/metal-cpu-env/bin/python training/qwen-metal-additive-20261002/compare_task_routed_profile.py \
  --source work/metal-qwen3-run-001 \
  --comparison work/metal-source-precision-profile-001 \
  --condition-archive training/qwen-metal-additive-20261002/runs/qwen3-condition-development-001 \
  --output work/metal-task-routed-profile-new --cache work/metal-model-cache
```

Reuse is allowed only for the same actual trained run and byte-identical model
inputs. When retraining produces different tensors/receipts, regenerate the
source and condition development runs rather than reusing published answers.

After scientifically reviewing development answers, freeze a selection that
binds the base revision, weights, training receipt, inference profile/helper,
comparison receipt and actual per-question decisions. Then:

```sh
OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 HF_HUB_DISABLE_XET=1 TOKENIZERS_PARALLELISM=false \
work/metal-cpu-env/bin/python training/qwen-metal-additive-20261002/evaluate_fidelity.py \
  --source work/metal-qwen3-run-001 --selection work/qwen3-fidelity-selection-001.json \
  --comparison work/metal-task-routed-profile-001 \
  --output work/metal-qwen3-fidelity-final-new --cache work/metal-model-cache
```

The evaluator generates adapter primary and supplemental answers, followed by
paired base answers with PEFT adapters disabled. The base weights, evidence,
profile, deterministic decoding and generation limits stay identical between
controls. `package_fidelity.py` exports actual raw predictions and portable
tensors. `verify_fidelity_package.py` checks integrity, expanded questions,
recorded decisions and the acceptance rule. No LoRA improvement is claimed
without an actual paired semantic comparison.

`answer_metal.py` selects an explicit licensed source paragraph and returns the
answer, excerpt, DOI and URL. It checks the package weights/config and the exact
inference profile against the evaluated receipt. Citation/completeness checks
are output guards, not scientific validation. Sources and CC BY 4.0 attribution
remain in the frozen `grounded-v3/sources.json` and linked licensing evidence.

## Use the published adapter

```sh
python3 training/qwen-metal-additive-20261002/verify_fidelity_package.py \
  --output training/qwen-metal-additive-20261002/runs/qwen3-fidelity-001
work/metal-cpu-env/bin/python training/qwen-metal-additive-20261002/answer_metal.py \
  --adapter training/qwen-metal-additive-20261002/runs/qwen3-fidelity-001/adapter \
  --cache work/metal-model-cache --passage '[MET001:p33]' --language fr \
  --question 'Quels deux effets pilotant l’écoulement sont cités dans le modèle de bain de fusion ?'
```

The full base model downloads separately; it is not duplicated in Git. The
benchmark requires the exact frozen profile. An explicit source paragraph is
required for every answer. Compare future adapters with the stronger base
control before adopting them.

The [actual exported-adapter smoke response](runs/qwen3-fidelity-smoke-001.json)
correctly names recoil pressure and Marangoni convection, cites the paragraph
and includes the DOI/source URL. Its separate receipt pins the CLI and package.
