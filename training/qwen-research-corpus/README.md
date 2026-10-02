# Multilingual research data for Qwen

The preparation command builds a private retrieval index and a small,
source-conditioned training pilot from the owner's 2 October 2026 research
collection. Preparation does not update weights or select an adapter. The
separate runner below performs one registered local experiment. Raw documents,
generated data and model weights stay outside Git.

The [first completed local pilot](results-001.md) improved bounded validation
from 0/10 to 6/10 and retained 16/16 coding smoke cases, but failed the research
gate. Its final tests remain closed and the candidate is not selected.
It reuses the existing [page/search utilities](../qwen-porsche-corpus/corpus.py)
and [exact JSON scorer](../qwen-porsche-corpus/train.py).

## What is prepared

- An SQLite FTS5 index of source metadata, authored research summaries and every
  retained PDF text page, deduplicated by the PDF SHA-256.
- An attributed candidate case pool with explicit admission flags; blocked
  source-derived cases are never included in the active SFT exports.
- MLX-compatible `data/train.jsonl` and `data/valid.jsonl`, using `messages`.
  Test cases and their targets stay under `evaluation/`, outside the data folder.
- XLSX cells retain sheet, row, cell address, raw value and formula. No formula
  executes. Unknown units/column semantics remain unresolved. Japanese phonetic
  annotations are not appended to the displayed cell text.
- A separately reviewed NIMS fatigue transcription preserves specimen identity,
  MPa stress amplitude, observed cycles, failure/runout, missing fracture origin,
  room-temperature conditions and provenance. All rows stay in the same source
  partition; they are not component allowables or an extrapolation benchmark.
- Image/table/text-quality and rights/reading review queues; figures are not
  automatically turned into a vision training dataset.

The summary admission policy accepts observed CC BY notices and read source
sections for **authored, cited inventory summaries**. It does not import full
article passages or clear excluded third-party figures. Unknown, NC, ND, SA or
distribution-only notices require separate review. The NIMS dataset notice
explicitly identifies the XLSX under CC BY 4.0; its checked notice and file
hashes are retained separately. This policy is a curation rule, not a legal
opinion about every possible use.

## Prepare, check and freeze

Use a new output directory. The builder refuses an existing directory and
preserves the source collection. The token check uses the existing tokenizer
offline and loads no model weights. `tokens` needs the installed Transformers
runtime; preparation, search, scoring and checks otherwise use the standard
library and the existing `pdftotext` executable.

```sh
python3 training/qwen-research-corpus/prepare.py self-check
python3 training/qwen-research-corpus/prepare.py prepare \
  --collection /absolute/path/to/2026-10-02-multilingual \
  --output /absolute/path/to/new-data
python3 training/qwen-research-corpus/prepare.py tokens \
  --output /absolute/path/to/new-data --tokenizer /absolute/path/to/pinned-tokenizer
python3 training/qwen-research-corpus/prepare.py freeze \
  --output /absolute/path/to/new-data
python3 training/qwen-research-corpus/prepare.py verify \
  --output /absolute/path/to/new-data
```

For the current Mac, run `tokens` with the existing Python interpreter under
`work/m64-qwen/venv/bin/python` in the managed Qwen coding checkout. Frozen data
contains the four helper files needed to reproduce preparation and verification.
Keep the original collection available: verification checks its source hashes.
An existing frozen dataset must never be extended in place; make a new version.

The self-check covers source alias union, licence/reading exclusions, partition
leakage, exact-answer grading, right-censored fatigue records, XLSX phonetic
annotations, tokenizer mapping/list formats and path containment.

## Retrieval and evaluation

```sh
python3 training/qwen-porsche-corpus/corpus.py query \
  --output /absolute/path/to/new-data --text 'K16' --limit 5
python3 training/qwen-research-corpus/prepare.py score \
  --cases /absolute/path/to/new-data/evaluation/valid-cases.json \
  --answers /absolute/path/to/validation-responses.json
```

Responses must be a JSON list of answer strings, one per case in the frozen
order. The exact scorer checks the JSON values, citation IDs and missing-data
wording of this bounded task. A paraphrase can fail it; it is not a general
scientific-answer grader. Unknown citations and optimistic unsupported targets
must not be accepted. Do not open final model evaluation for checkpoint tuning.

Source families join identities, DOI aliases, identical files, cross-references
and declared related studies before splitting. Original synthetic fixtures
have separately authored train/validation/test scenarios. Task schemas are
shared, so this measures source-conditioned extraction and evidence handling,
not independent mastery of novel engineering task families. The full retrieval
index contains all partitions for browsing; do not mine held-out content from
it for additional training while preserving the same evaluation labels.

Before a later LoRA run, register the parent adapter/hash, matched baseline,
training settings and checkpoint selection rule. Preserve coding/native-engine
regressions in a separate retention assessment. Require at least 95% in each
evaluated category and no lost baseline pass before considering a candidate;
this small pilot cannot establish those gains in advance. Never make the
candidate the default automatically. Raw texts, staged blocked examples,
unreviewed cells and test targets are outside the training input directory.

The preparation itself proves file integrity, extraction coverage and admission
boundaries. Research summaries remain inventory claims rather than independently
reproduced scientific results. Missing M64 interfaces, original K16 maps, cam
data and fan measurements remain missing. Geometry, material or solver output
needs its own engineering evidence.

## Run a local pilot

Use the existing MLX interpreter, the frozen dataset and a new experiment
directory. The runner reuses the exact JSON scorer and the bounded native
OpenUSD/PicoGK evaluator; no new dependencies are installed.

```sh
python3 training/qwen-research-corpus/run.py self-check
/absolute/path/to/m64-qwen/venv/bin/python \
  training/qwen-research-corpus/run.py run \
  --dataset /absolute/path/to/frozen-data \
  --output /absolute/path/to/new-pilot
```

The parent is the existing engineering-005 step-1200 adapter, checked by its
SHA-256. It is continued for exactly 320 steps at learning rate 0.000005,
batch size two, seed 1042, with prompt masking, 16 LoRA layers, rank eight and
scale 20. The installed MLX defaults for rank/scale match the checked parent
configuration. Only train/validation JSONL is copied into the training input.
There is no automatic replacement of an existing adapter.

Before generating any answers, the runner records the dataset, code, model,
parent, native runtime and selected case hashes, generation settings and
selection rule. It checks 16 reference programs natively, measures the matched
baseline, trains, and measures the candidate. Only the fixed final checkpoint
is assessed. Final research tests open only if validation has at least 95% in
each category and no lost baseline pass. With this ten-case validation, every
case must pass. The separate retention sample uses eight OpenUSD and eight
PicoGK cases drawn deterministically from previously used development data;
it is a smoke test, not a new general coding benchmark.

The output contains `protocol.json`, incremental answer receipts, per-case
scores, native witnesses, `training-command.json`, `training.log`, a separate
adapter and `results.json`. A partial run remains evidence of an interrupted
experiment; the runner refuses to overwrite it. A lower loss alone does not
qualify the candidate. Failed research or retention gates are recorded without
changing the grader or using final test targets to tune training.
