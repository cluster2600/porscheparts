# Mezger German-source research increment

This separate pack prepares English CPT passages and synthetic, supplied-record
SFT conversations from reviewed German-language technical research. The input is
the attributed factual register
[`facts.json`](../../catalog/reference/mezger-german-sources-20261003/facts.json).
Exact accepted, excluded and partition counts appear in
[`manifest.json`](manifest.json). Public source records establish provenance;
the pack contains authored factual metadata, not copied manual or supplier text.

| Dataset | Train | Validation | Test |
| --- | ---: | ---: | ---: |
| CPT passages | 102 | 0 | 6 |
| Grounded SFT examples | 102 | 0 | 6 |

All 108 curated records are included; four explicitly teach uncertainty, 102
retain qualified-evidence status, and two are marked eligible. The six held-out
records inherit the earlier TTE or RUF source-family test assignment. The empty
validation files are intentional.

Each accepted fact produces one CPT passage and one native
`system`/`user`/`assistant` conversation. The SFT user supplies the authored
record, and the assistant extracts its findings with a record citation. Both
forms preserve the exact engine application, component, units, evidence status
and qualifications. An unspecified alloy stays unspecified. Factory material
statements, aftermarket specifications, racing variants and unresolved
definitions remain scoped to their reviewed application.

German terms such as *Leichtmetall* or *Aluminiumlegierung* do not establish a
numeric alloy grade. A material family, trade name, coating specification or
measured coating thickness does not establish the base alloy or the thickness of
an engine casting. English targets retain these distinctions and the curated
record's caveats. Records marked `exclude` create no targets; records that teach
uncertainty explicitly state that the value is not established in this review.
Source locators, including German section titles, remain separate provenance
metadata and are not repeated in English training targets.

This is grounded record extraction, not an independent engineering reasoning
benchmark or a test of unaided recall. Wording is synthetic; the reviewed source
facts are attributed metadata. This increment does not run training, tokenize
the text, evaluate model quality or produce weights. Token lengths, context fit
and assistant loss masking remain to be checked with the chosen model and
trainer before training.

## Rebuild and verification

Run from the repository root using Python's standard library:

```sh
python training/mezger-german-sources-20261003/prepare.py
python training/mezger-german-sources-20261003/verify.py
python training/mezger-german-sources-20261003/test_verify.py
```

The earlier [993 Turbo pack](../993-turbo-20261002/README.md) and
[Mezger materials pack](../mezger-turbo-materials-20261003/README.md) stay frozen.
The builder pins both earlier builders, split ledgers and exclusion lists by
SHA-256, reserves both packs' accepted and excluded record IDs, and inherits
their source-ID, source-family and exact reviewed-claim partitions. Source
families and identical reviewed claims form connected components. Any component
joining incompatible prior partitions fails the build. Official Porsche
documents retain their factory family when hosted on a public mirror.
Reviewed cross-domain aliases also retain their frozen brand/catalogue family:
`tte24.net` sells the previously held-out TTE650 product, the German RUF site
belongs to the previously held-out RUF brand, and MAHLE Aftermarket remains with
the earlier MAHLE family. The explicit aliases and their canonical SHA-256 are
recorded in the manifest. A shared split family does not assert that the RUF
TRIBUTE engine has the same architecture as a historic RUF 993 engine.

Components without an inherited partition stay in train. No new holdout anchors
are forced; validation or test files can legitimately be empty. Inherited
holdouts remain reserved even when merging the increments. These selected
records do not support a representative performance claim, and related
material concepts can recur across distinct applications.

The validator checks input/output hashes, canonical source-file closure,
unique IDs across all three packs, exact dataset/provenance coverage, native
message roles, citations, qualifications and combined partition isolation. It
reconstructs the connected components and expected inherited partition rather
than trusting the new ledger. Focused tests check altered targets, changed
frozen partitions despite refreshed hashes, reuse of a previously excluded ID,
translated TTE/RUF holdout leakage, scope/unknown preservation and byte-identical
isolated rebuilds. These checks
establish artifact integrity, not material suitability or engine qualification.

## Formats and training hand-off

`cpt_text/{train,valid,test}.jsonl` contains a `text` column.
`sft_messages/{train,valid,test}.jsonl` contains native `messages` with `role`
and `content`. [`provenance.jsonl`](provenance.jsonl) stores canonical source
links, applications, eligibility, split keys and per-row hashes separately from
trainer payloads. [`dataset_info.json`](dataset_info.json) provides conventional
LLaMA-Factory-style ShareGPT and CPT registrations; it is not a complete trainer
configuration.

Before a training run, pin model/tokenizer/trainer revisions, apply the model's
native chat template, audit lengths and truncation, and verify SFT assistant loss
masking. Keep every increment's validation and test partitions out of both CPT
and SFT training. No earlier pack or trained weights are modified here.

Public documents remain their publishers' property. No raw scans, proprietary
manual passages, supplier quotations, vehicle identifiers, private project
content or local research paths are included, and no source-document licence is
asserted or transferred.
