# Deeper M64 dimensional research increment

This separate pack prepares authored English CPT passages and synthetic,
supplied-record SFT conversations from the reviewed
[dimensional register](../../catalog/reference/m64-dimensions-deep-20261024/facts.json).
It prepares data only: no model training, tokenization, context-fit evaluation or
weights are produced.

| Dataset | Train | Validation | Test |
|---|---:|---:|---:|
| CPT passages | 40 | 0 | 0 |
| Grounded SFT examples | 40 | 0 | 0 |

The register contains 49 records: 39 produce qualified-evidence targets, one
teaches explicit uncertainty, and nine excluded leads produce no targets. The
40 accepted records comprise 38 nominal records, one clearance and one
documentary scope record. These are counts of scoped evidence records, not
counts of unique new dimensions: a record can contain several dimensions,
historical declarations or related-product comparisons. The exact counts and
hashes appear in [manifest.json](manifest.json).

No physical component was measured. Every record retains
`physical_measurement_performed: false` in its complete measurement metadata.
Supplier replacements, aftermarket products, factory reproduction text, verified
factory page photographs and related racing engines keep their stated scope.
Research concerning a 993 Turbo above 550 PS provides context; these documentary
values do not establish fit, manufacturing readiness, durability, a validated
power target or engineering approval.

All six new connected components inherit train or remain unassigned and default
to train. Empty validation and test files are intentional. This increment adds
no held-out evaluation set; earlier holdouts remain reserved and must stay out
of both CPT and SFT training when combining packs.

Each accepted fact creates exactly one CPT passage and one native
`system`/`user`/`assistant` conversation. The SFT user supplies the authored
record narrative and complete measurement object; the answer extracts that
supplied evidence and cites its stable record ID. This is supplied-record
extraction, not an independent engineering reasoning benchmark or a test of
unaided factual recall. Authored wording is synthetic; the attributed source
facts are not invented.

Every target retains application, component, parameter, value, units, evidence
status, qualification and the full `measurement_metadata` object. Its required
fields are `measurement_kind`, `datum`, `conditions`, `tolerance` and
`variant_basis`; additional reviewed fields remain intact. Complete metadata
also appears in passages and per-row provenance. Unknown tolerances, maximum-only
limits, checking conditions, exact part identity and geometric datums retain
their reviewed definitions.

The SM exhaust record preserves the primary 42.5 mm declaration alongside the
frozen secondary 43.5 mm declaration and their different product scope. The
intake record preserves SM 49.1 mm and FVD 49 mm as separate product/source
precisions; rounding and dimensional equivalence remain unverified. The literal
25-degree supplier seat-angle anomaly stays in the uncertainty record. Neither
that anomaly nor another product's nominal catalogue size becomes a factory
manufacturing instruction.

## Rebuild and verification

Run from the repository root with Python's standard library:

```sh
PYTHONDONTWRITEBYTECODE=1 python training/m64-dimensions-deep-20261024/prepare.py
PYTHONDONTWRITEBYTECODE=1 python training/m64-dimensions-deep-20261024/verify.py
PYTHONDONTWRITEBYTECODE=1 python training/m64-dimensions-deep-20261024/test_verify.py
```

The [993 Turbo](../993-turbo-20261002/README.md),
[Mezger materials](../mezger-turbo-materials-20261003/README.md),
[German-source](../mezger-german-sources-20261003/README.md), and
[first M64 measurement](../m64-measurements-20261024/README.md) packs remain
frozen. Their four builders, split ledgers and exclusion lists are pinned by
SHA-256. Every earlier accepted and excluded ID remains reserved. New IDs use
the `M64-DEEP-` namespace.

Source IDs, conservative publisher families and exact reviewed claims inherit
all four packs' partitions. The earlier exact-claim fingerprint remains present;
a second fingerprint includes component identity and the complete measurement
metadata, using the same convention as the fourth frozen pack. Sources and
identical claims joined by a record form one connected component. A component
joining incompatible frozen partitions fails instead of moving earlier records.
No new holdout anchors are forced.

Official Porsche documents retain the factory family when mirrored or presented
as identified factory reproductions. MAHLE manufacturer attribution, including
the historical public trade-site mirror, remains in the existing MAHLE family.
RUF and TTE aliases and the inherited FIA, Melett and Federal-Mogul policies stay
explicit. Source co-citations connect the new SM records to their frozen
Partworks/FVD comparison sources. These groupings protect partition isolation;
they do not establish product interchangeability or independent corroboration.
Policy definitions and hashes appear in the manifest and ledger.

The verifier checks full input/output hash closure, canonical accepted-source
records, reserved IDs, count summaries, reconstructed connected components,
all four prior partition constraints, exact trainer registrations, native message
roles, stable citations, exact authored answers and complete measurement
metadata. Each accepted record must appear once in each dataset; refreshed
hashes and inflated counts cannot legitimize duplicated targets.

All 23 focused tests pass. They cover fourth-pack accepted/excluded ID
reservation, frozen dependency coverage and partition corruption; exact legacy
and metadata-aware fingerprints; metadata and qualification retention; forged
publisher families and component summaries; rehashed duplicate amplification;
trainer train-to-holdout redirection; omitted output hashes; and byte-identical
isolated rebuilds. Artifact integrity does not establish suitability for
manufacture or component qualification.

## Formats and training hand-off

`cpt_text/{train,valid,test}.jsonl` contains a `text` column.
`sft_messages/{train,valid,test}.jsonl` contains native messages with `role` and
`content`. [provenance.jsonl](provenance.jsonl) records canonical public source
links, complete measurement definitions, scope, split keys and per-row hashes.
[dataset_info.json](dataset_info.json) supplies conventional LLaMA-Factory-style
ShareGPT and CPT registrations, not a complete trainer configuration.

Before training, pin model/tokenizer/trainer revisions, apply the model's native
chat template, audit sequence lengths and truncation, and check assistant loss
masking. Complete metadata can increase sequence length; this preparation does
not prove that a future tokenizer/trainer will preserve it without truncation.
Empty evaluation registrations must not be treated as populated datasets. No
model or token quality was assessed.

Public sources remain their publishers' property. Only factual metadata and
authored paraphrases are included; raw manuals, supplier PDFs, scans, copied
passages, private paths and vehicle identifiers are excluded. Where only a
text-reader capture was acquired, source provenance identifies that capture;
it is not described as acquired raw PDF bytes. Raw research captures remain
outside the repository.
