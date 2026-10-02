# Porsche 993 Turbo research training pack

This pack prepares attributed research on the stock 3.6 litre M64/60, related
turbo maps, aftermarket K16/K24 conversions, RUF configurations and distinct
restomod engines. It contains **248 CPT passages and 251 synthetic SFT examples**.
No model has been trained, no weights have been produced, and no tokenization or
model-quality evaluation has been performed.

| Dataset | Train | Validation | Test |
| --- | ---: | ---: | ---: |
| CPT text | 237 | 3 | 8 |
| Grounded SFT messages | 238 | 4 | 9 |

The source of truth is
[`catalog/reference/993-turbo-research-20261002`](../../catalog/reference/993-turbo-research-20261002/).
It contains all normalized research and source cross-references. Training is a
curated derivative: 163 eligible or qualified engine records, 42 authored turbo
and methodology passages, 20 matching scenarios, four rotation examples and 19
explicit research gaps. The conditional fan ratio in `ENGINE-D163` is excluded.
[`coverage.json`](coverage.json) identifies turbo records represented by source
paraphrases and those retained only for retrieval. It does not imply that every
catalog field is an SFT target.

## Evidence and reuse

Both CPT wording and SFT question/answer wording are authored and synthetic. The
underlying facts, attributed supplier claims and computed values are drawn from
the reviewed registers. CPT is a compact authored reference corpus, not raw
source-document text. SFT is excerpt-grounded: each user message supplies an
authored research record, and the assistant cites its ID. Training these examples
does not demonstrate unaided recall, engineering competence or factual accuracy
on a particular engine.

Raw scans, manual text, unreviewed OCR, supplier quotations, private project
content, vehicle identifiers and local scratch paths are excluded. The 2,496
unreviewed Carrera-context OCR records are not imported. Public source visibility
does not grant a licence to redistribute the original documents; this pack
contains factual metadata and original paraphrases only. Source URLs, canonical
catalog paths and input hashes preserve attribution. No original publisher's
document licence is asserted or transferred.

Stock M64/60 data, family-level architecture, Carrera context, aftermarket
geometry, supplier capacity claims, other engines and calculations retain their
labels. Supplier 650 PS claims are not factory ratings, operating maps, measured
dyno results or durability approval. The corpus has not established exact stock
K16-6735/6736 maps, operating speeds, all OEM alloy grades, or the absolute Turbo
fan ratio. Uncertainty examples state limits of this review, not proof that a
document does not exist.

## Rebuild and verify

Run from the repository root; Python's standard library is sufficient:

```sh
python training/993-turbo-20261002/prepare.py
python training/993-turbo-20261002/verify.py
python -m unittest discover -s tests -p test_993_turbo_training_research.py
```

`prepare.py` reads normalized catalog references, public source metadata and
[`input/authored-passages.json`](input/authored-passages.json). It writes stable
UTF-8 JSONL, provenance, split assignments, coverage and SHA-256 manifests.
`verify.py` checks exact row coverage, native message roles, citations, input and
output hashes, source closure, prohibited content markers and partition isolation.
An export lacking catalog inputs can use `--skip-input-hashes`; that mode provides
weaker verification and is reported in the result.

Partitioning keeps each document family together. Records citing several
families, and identical reviewed claim IDs, join those families into one connected
component. TTH products are held out for validation; TTE products and RUF
specifications are held out for test. The source and claim ledger is auditable in
[`split-ledger.json`](split-ledger.json). These small, deliberately selected
holdouts test excerpt grounding; they are not a representative benchmark. Shared
technical concepts can recur across different products. Training and evaluation
must respect the same partitions for CPT and SFT.

## Trainer hand-off

`cpt_text/{train,valid,test}.jsonl` contains a `text` column.
`sft_messages/{train,valid,test}.jsonl` contains native `messages`, each with
`system`, `user`, `assistant` roles and `content`. Metadata is kept in
[`provenance.jsonl`](provenance.jsonl), rather than sent as an unintended target.
[`dataset_info.json`](dataset_info.json) provides LLaMA-Factory-style ShareGPT
role mappings and a CPT text-column mapping. Dataset registration alone is not a
complete trainer configuration.

The existing repository profile for Qwen/Qwen2.5-1.5B-Instruct is referenced in
the manifest as an advisory starting point. This pack remains model independent.
Before a run, choose and pin the exact tokenizer and trainer revision, apply the
model's native chat template, audit length and truncation, and train on the train
partition only. For SFT, configure loss on assistant tokens and verify masking;
do not train on supplied user evidence or system instructions by accident.
Select settings using validation only, and reserve the test partition for final
evaluation. Keep CPT holdouts out of pretraining as well. Existing metal-additive
packs and their frozen partitions have not been edited or merged into this pack.
