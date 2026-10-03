# Qwen3 scientific continuation

This is a bounded research continuation of the historical Qwen3 scientific
adapter, kept separate from Qwen2.5-Coder/MLX. The current native MLX registration
is [candidate D](protocol-candidate-d.json). [PROTOCOL.md](PROTOCOL.md) records the
scientific gates and trial history. No gain or manufacturing qualification is
established by finishing training.

[The completed D result](RESULTS.md) is negative: 13/20 acceptable development
answers versus 14/20 for the base, zero gains and one critical regression under
two independent blinded assistant reviews. D is rejected, the reserve remains
closed and the broader training objective is unmet. [The next-data plan](NEXT_DATA_PLAN.md)
records coverage gaps and required admission gates before another trial.

The [data manifest](data/manifest.json) binds twenty FR/EN corrective rows:
ten objectives and ten source paragraphs from six licensed historical training
families. [The source ledger](data/source-ledger.json) records provenance,
licences and exclusions. Independent assistant review found these gold answers
consistent with supplied excerpts for a bounded trial; human scientific and
translation review remain pending. [Corpus coverage](CORPUS_COVERAGE.md) explains
which other project datasets are prepared, conditional or excluded. Impeller
research, forum statements, hypotheses and unknown parameters are not SFT here.

## Reproduction and integrity

Preparation and synthetic control tests need only the standard library:

```sh
python3 training/qwen3-continuation-20261003/audit.py data
python3 -m unittest discover -s tests -p 'test_qwen3*.py'
```

The checks bind excerpt/licence/provenance hashes, original training boundaries,
retired-test exclusions and exact `task_routed_v14` expansion. They do not prove
the original studies physically correct. All historical model tests are now
development. The new reserved pool remains under independent custody until a
candidate passes development and its selection is frozen.

[mlx_run.py](mlx_run.py) uses the exact local public Qwen3 revision with the
existing official [MLX dependency versions](requirements-mlx.txt). It never
installs or downloads. Source weights stay BF16 and tied, with no quantization
or separate output head. The original 144 FP32 PEFT LoRA matrices are transposed
exactly into 36 layers of q/v adapters: rank 8, scale 2, dropout 0.05. Native MLX
rounds the LoRA delta before addition; PEFT rounds after addition. No parity with
the historical PEFT runtime is claimed. Base, initial adapter and D are all
compared in the same native runtime with identical messages and greedy decoding.

Supply the model snapshot and the two complete zero-update MLX gate receipts:

```sh
python training/qwen3-continuation-20261003/mlx_run.py train \
  --protocol training/qwen3-continuation-20261003/protocol-candidate-d.json \
  --snapshot /path/to/pinned/snapshot --mlx-python /path/to/existing/mlx/python \
  --gate-receipt /path/to/mlx-probe-003/mlx-probe-receipt.json \
  --gate-supervisor /path/to/mlx-probe-003/supervisor-receipt.json \
  --output work/qwen3-candidate-new
```

D is one epoch of twenty rows and ten updates, using a new AdamW optimizer from
the original historical adapter. Every loss and all 144 gradients must be
materialized and finite before updates; saved arrays reload exactly. All 398
frozen base tensors are hashed before and after. Checkpoints are retained at
steps 4, 8 and 10, without checkpoint selection. A supervisor rejects GPU errors
even with exit zero and stops only its own child on resource/deadline failure.
The bounds are 30 minutes, 24 GiB worker RSS, 20 GiB MLX active allocation,
512 MiB cache, at least 16 GiB system availability and at most 256 MiB swap growth.
`nice=10` and two-thread environment variables are CPU targets; receipts record
actual CPU utilization, including authorized transient startup peaks.

These commands describe reproducibility, not permission to repeat or retune the
registered experiment. Further training requires a separate pre-output
registration and authorization. Native weights are `adapter/adapters.safetensors`
and `adapter/adapter_config.json`; they are not PEFT adapter files.

## Comparison and admission

Development question records include raw and exactly expanded messages, source
identity, language, paragraph identity and canonical input hashes. Registration
pins the file bytes and ordered roster. Generate all three controls together:

```sh
python training/qwen3-continuation-20261003/mlx_run.py evaluate \
  --protocol training/qwen3-continuation-20261003/protocol-candidate-d.json \
  --snapshot /path/to/pinned/snapshot --mlx-python /path/to/existing/mlx/python \
  --adapter work/qwen3-candidate-new/adapter \
  --questions work/development/questions.jsonl \
  --registration work/development/registration.json --historical-control \
  --output work/qwen3-development-new
```

Reserved generation needs both `--selection` and `--reservation-amendment`,
binding D's protocol/runner/weights to the unchanged original reservation. Gold
answers remain with the custodian. Two independent assistant reviewers grade
anonymized outputs; disagreements fail conservatively. Scientific qualification,
quantitative fidelity, causal support and useful answers are separate checks.
The reserved pilot gate requires at least 22/24 acceptable answers, net gain at
least two, all ten critical items correct and no critical regression, unsupported
citation, units/conditions error, causal overclaim or token-budget truncation.
Paired gains/losses, source families and exact descriptive McNemar uncertainty
are reported. Two gains without losses give p=0.5; a small pilot pass alone does
not establish reliable general improvement.

## Preserved failures and limits

A stopped for a non-finite metric; B stopped before update five for non-finite
gradients. C's separate frozen FP32 output projection passed its complete
zero-update gate but training emitted a Metal command-buffer error and stalled.
C is quarantined; origin and impact remain unknown. A/B's initial two-trial
ceiling, C's separate numerical-recovery authorization and D's separate native
MLX authorization remain explicit. Their configurations, logs and receipts are
preserved; no rejected checkpoint initializes D.

No model score certifies a part, supplies missing measured interfaces or validates
a material process. Familiar source families, unknown base-pretraining exposure,
small dependent FR/EN samples and missing human engineering review limit claims.
