# M64 dimensional research increment

This separate pack prepares authored English CPT passages and synthetic,
supplied-record SFT conversations from the reviewed
[measurement register](../../catalog/reference/m64-measurements-20261024/facts.json).
Exact accepted/excluded counts, measurement kinds and partition sizes appear in
[manifest.json](manifest.json). It prepares data only: no model training,
tokenization, context-fit evaluation or weights are produced by this increment.

| Dataset | Train | Validation | Test |
|---|---:|---:|---:|
| CPT passages | 89 | 0 | 0 |
| Grounded SFT examples | 89 | 0 | 0 |

The register contains 107 records: 89 produce targets and 18 unresolved FIA
leads are excluded. Of the accepted records, 86 retain qualified-evidence
status and three teach explicit uncertainty. Their measurement classifications
are 80 nominal records, seven clearances, one derived calculation and one
documentary conflict. No physical measurement was performed on a project part;
every accepted metadata object retains `physical_measurement_performed: false`.

All new connected components either inherit train or have no earlier assignment
and therefore stay in train. Empty validation and test files are intentional;
this increment supplies no new held-out evaluation set. The earlier packs'
holdouts remain reserved and were not moved into this training partition.

Each accepted fact creates one CPT passage and one native
`system`/`user`/`assistant` conversation. The SFT user supplies the complete
authored record and the answer extracts that evidence with its stable citation.
This is supplied-record extraction, not an independent engineering reasoning
benchmark or a test of unaided factual recall. Authored wording is synthetic;
the underlying source-attributed numerical metadata is not invented.

Every target retains the application, component, value, units, evidence status,
caveat and full `measurement_metadata` object. Its required fields are
`measurement_kind`, `datum`, `conditions`, `tolerance` and `variant_basis`.
Additional reviewed fields remain intact. The complete object also appears in
passages and per-row provenance. Unknown tolerances remain unknown; lower/upper
deviations, maximum-only limits, checking temperatures and geometric datums are
not replaced with generic size labels.

Factory nominal dimensions, service limits, homologated values, aftermarket
specifications and derived conversions keep their exact scope. A documentary
value is not a physical measurement performed on the project engine. A catalogue
size does not establish its manufacturing tolerance, and related Carrera/racing
dimensions do not automatically identify M64/60 hardware. Records marked
`exclude` create no targets. Uncertainty records preserve the unresolved value
or contradiction rather than selecting a plausible number.

## Rebuild and verification

Run from the repository root with Python's standard library:

```sh
python training/m64-measurements-20261024/prepare.py
python training/m64-measurements-20261024/verify.py
python training/m64-measurements-20261024/test_verify.py
```

The [993 Turbo](../993-turbo-20261002/README.md),
[Mezger materials](../mezger-turbo-materials-20261003/README.md), and
[German-source](../mezger-german-sources-20261003/README.md) packs remain frozen.
Their three builders, split ledgers and exclusion lists are pinned by SHA-256.
All accepted and excluded IDs stay reserved. Source IDs, conservative publisher
families and exact reviewed claims inherit all three packs' partitions.

The earlier exact-claim fingerprint remains present for cross-increment
isolation. A second fingerprint adds component identity and the complete
measurement metadata. Sources or identical claims joined by a record form one
connected component. A component that would join incompatible frozen partitions
fails the build instead of moving an earlier record.

Official Porsche documents keep their factory family when mirrored. Earlier
MAHLE, RUF and TTE aliases remain unchanged. FIA homologation documents share an
applicability family; Melett documents and their retailer-hosted technical
mirrors share a publisher family; Federal-Mogul engine catalogues remain together.
These groupings protect partition isolation and do not imply parts
interchangeability or independent corroboration. The explicit policies and their
hashes are recorded in the manifest and ledger.

Unassigned components stay in train. No new holdout anchors are forced, so
validation or test files may be empty. Keep inherited holdouts out of both CPT
and SFT training when combining increments. Related geometric or material
concepts can still recur across independently scoped products; these selected
holdouts are not a representative model-performance benchmark.

The verifier checks complete input/output hash closure, canonical sources,
reserved IDs, count summaries, connected-component reconstruction, prior
partition isolation, exact trainer registrations, native message roles,
citations, exact authored answers and complete measurement metadata.
Focused tests exercise corrupted targets, changed frozen partitions
despite refreshed hashes, source-family forgery, reserved IDs, removed tolerance
metadata, rehashed CPT metadata loss, additional-field preservation,
train-to-holdout registration redirection, omitted output hashes and
byte-identical isolated rebuilds. Artifact integrity does not establish that a
dimension is suitable for manufacture or that a component is qualified.

## Formats and training hand-off

`cpt_text/{train,valid,test}.jsonl` contains a `text` column.
`sft_messages/{train,valid,test}.jsonl` contains native messages with `role` and
`content`. [provenance.jsonl](provenance.jsonl) records canonical public source
links, complete measurement definitions, scope, split keys and per-row hashes.
[dataset_info.json](dataset_info.json) provides conventional LLaMA-Factory-style
ShareGPT and CPT registrations, not a complete trainer configuration.

Before training, pin model/tokenizer/trainer revisions, apply the model's native
chat template, audit lengths and truncation, and check assistant loss masking.
The complete measurement object can increase sequence length; its inclusion here
does not prove that a future tokenizer/trainer will retain it without truncation.
Empty validation/test registrations must not be treated as populated evaluation
datasets. No earlier pack, evidence contract or existing model weights is edited.

Public sources remain their publishers' property. Only factual metadata and
authored paraphrases are included; raw manuals, supplier PDFs, scans, copied
passages, private project paths and vehicle identifiers are excluded.
