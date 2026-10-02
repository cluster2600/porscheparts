# CPU LoRA pilot 001: measured results

A real one-epoch LoRA run completed on 2 October 2026 using the pinned
Qwen/Qwen2.5-1.5B-Instruct base. This is an experimental adapter, not a
scientifically validated model. The small validation-loss decrease did not
produce citation compliance on the registered evaluation. Do not promote this
adapter to an engineering serving default on this evidence.

| Measurement | Base | Adapter |
|---|---:|---:|
| Mean validation example loss (16 examples) | 2.843547 | 2.825056 |
| Expected citation present (8 answers) | 0/8 | 0/8 |
| Answers reaching the 256-token budget | 2/8 | 2/8 |
| Independent expert-scored answers | 0/8 | 0/8 |

The loss decrease is about 0.65%, without a statistical significance claim.
Loss is assistant-target cross-entropy averaged over examples, not scientific
accuracy. Citation presence is syntactic. Output truncation affects eval-001
and eval-006 for both models. Four prompts belong to validation sources and
four to test sources; all eight are French and provide their evidence passage.
These results do not evaluate free-standing knowledge or multilingual competence.

## Execution evidence

The fixed run used 53 training examples, 16 validation examples, one epoch,
seven optimizer steps, seed 42 and 1,089,536 trainable LoRA parameters. No test
examples entered training; no hyperparameters were changed after inspecting
predictions. See [run-receipt.json](run-receipt.json),
[training-metrics.json](training-metrics.json) and
[trainer-history.json](trainer-history.json).

The unquantized BF16 CPU run used four threads. Training plus its scheduled
validation and saving took 717.20 seconds; the complete run, including initial
download and before/after prediction, took 1,700.21 seconds. Peak process RSS
was 5.67 GiB. This does not measure the prepared GPU NF4 QLoRA profile.

The tensor audit found 112 finite tensors, with all 56 LoRA B matrices nonzero.
The trained tensor file SHA-256 is
`4117b91332c04a69330bcda6002d4a9909efefd338d5c56cd53b33bd34852c2d`.
The [package manifest](package-manifest.json) verifies the core run results and weights;
the original adapter configuration is retained separately. Portable configuration
changes only the base model identifier and pinned revision. Base weights are
not included. The full installed dependency inventory is `runtime-freeze.txt`.

## Qualitative inspection, pending independent review

The following are assistant observations from the saved predictions, not expert
scores or a calibrated scientific-accuracy benchmark:

- eval-002: both answers initially accept an always-harmful Laves-phase claim,
  then discuss beneficial effects that contradict that universal statement.
- eval-004: both answers incorrectly accept universal pore-prediction accuracy
  from a sensor-fusion study that only reports a contextual comparison.
- eval-005: both fail to explicitly distinguish validation against published
  results from qualification of the user's new component.
- eval-007: both accept replacing temperature-dependent thermal/mechanical
  properties with one constant, rather than establishing a supported validity
  range from the evidence.
- eval-008: both invent an optimal certified 0.8 mm wire diameter for the user's
  component from a comparative humping observation.

Inspect [base predictions](base-predictions.jsonl) and
[adapter predictions](adapter-predictions.jsonl). Review worksheets
[base-review.jsonl](base-review.jsonl) and
[adapter-review.jsonl](adapter-review.jsonl) contain the evidence, reference
answers and criteria. Their expert score fields remain blank.

## Next evidence needed

Have a materials/additive-manufacturing specialist review the examples and
translations, and score the saved paired responses. Expand reviewed training
coverage, especially missing-evidence abstention, scope of validation, source
citation and temperature-dependent properties. Register a new data release and
experiment for any change. Because these test answers have now been inspected,
use a fresh untouched test set for future model selection. Separately compare a
retrieval baseline on registered questions before recommending deployment.

For reproduction and portable adapter loading, see [CPU_PILOT.md](../../CPU_PILOT.md).
License: [Apache 2.0](MODEL-LICENSE.txt); data attribution remains in
[grounded-v3/sources.json](../../grounded-v3/sources.json).
