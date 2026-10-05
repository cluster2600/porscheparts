# Mezger turbo materials research increment

This separate pack turns reviewed, attributed materials research into authored
CPT text and synthetic, excerpt-grounded SFT messages. Its canonical input is
[`facts.json`](../../catalog/reference/mezger-turbo-materials-20261003/facts.json).
The earlier [993 Turbo pack](../993-turbo-20261002/README.md) is left unchanged.
Exact row counts and evidence classifications are recorded in
[`manifest.json`](manifest.json).

| Dataset | Train | Validation | Test |
| --- | ---: | ---: | ---: |
| CPT passages | 173 | 18 | 9 |
| Grounded SFT examples | 173 | 18 | 9 |

The curated register contains 203 records: 200 become training/evaluation
examples and three are excluded. Five accepted records teach explicit uncertainty.

Each accepted fact produces one CPT passage and one native
`system`/`user`/`assistant` conversation. The user supplies the authored evidence
record, and the assistant extracts it with a record citation. This is supplied
record extraction, not an independent engineering reasoning benchmark or a
test of unaided recall. Both CPT wording and SFT wording are synthetic; the
underlying attributed factual metadata is not invented. No model has been
trained, no weights produced, and no tokenizer, context-fit or model-quality
evaluation performed.

Factory material statements retain their precise engine and component scope.
Aftermarket piston/rod/head/exhaust products and related engine generations do
not establish original Porsche materials by analogy. Family-level data,
supplier specifications and unresolved material grades retain their status and
caveats. Records marked `exclude` are listed separately and create no targets.

## Rebuild and integrity checks

Run from the repository root, using Python's standard library:

```sh
python training/mezger-turbo-materials-20261003/prepare.py
python training/mezger-turbo-materials-20261003/verify.py
python training/mezger-turbo-materials-20261003/test_verify.py
```

The generator reads curated factual metadata and canonical public source
records; it does not fetch documents or copy manual/supplier text. It imports
the earlier pack's source-family policy, adds an official-Porsche mirror rule,
and joins records that share source families or identical reviewed claims.
Previous source, family and exact-claim partition assignments constrain the
new connected components. Conflicts fail the build rather than altering the
frozen earlier pack.

Porsche, MAHLE and LN Engineering families stay in train. Independent Pauter
records are eligible for validation; independent Xtreme or Kline records are
eligible for test. Earlier partition constraints and shared training families
take priority over new holdout anchors. Empty partitions are permitted and
explicitly represented as empty JSONL. The actual source-family assignments
and any inherited constraints appear in
[`split-ledger.json`](split-ledger.json). These small, selected holdouts are not
a representative performance benchmark. Common material concepts can recur
across distinct products and applications.

The validator checks every input and output SHA-256, source-file closure,
unique record IDs, exact dataset-to-provenance coverage, native message roles,
citations, qualifications, prohibited private/raw-content markers, and combined
partition isolation with the earlier pack. Hash and schema checks establish
artifact integrity, not the engineering validity of a material selection.
Focused checks also exercise corrupted targets, frozen-source leakage, missing
grade handling, preservation of scope and byte-identical isolated rebuilds.

## Formats and hand-off

`cpt_text/{train,valid,test}.jsonl` contains a `text` column.
`sft_messages/{train,valid,test}.jsonl` contains native `messages` with `role`
and `content`. Attribution, applications, eligibility, split keys and content
hashes are stored in [`provenance.jsonl`](provenance.jsonl), separate from the
trainer payload. [`dataset_info.json`](dataset_info.json) provides conventional
LLaMA-Factory-style ShareGPT role and CPT text-column registrations; it is not
a complete trainer configuration.

Before training, pin the model, tokenizer and trainer revisions, apply the
model's native chat template, audit lengths and truncation, and verify assistant
loss masking for SFT. Keep validation and test out of both CPT and SFT training,
including when combining increments. Use validation for settings and reserve
test for final assessment. No existing frozen data or trained weights are
modified by this pack.

Public documents remain their publishers' property. This increment contains
factual metadata templates and source links, not raw scans, proprietary manual
passages or copied supplier prose. No source-document licence is asserted or
transferred. Private project content, personal data, vehicle identifiers and
local research paths are excluded.
