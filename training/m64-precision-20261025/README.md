# Scoped M64 dimension training data

This separate increment prepares authored English CPT passages and synthetic,
supplied-record SFT conversations from the reviewed
[dimension register](../../catalog/reference/m64-precision-20261025/facts.json).
It prepares data only. No model training, tokenization, context-fit evaluation or
weights are produced.

| Dataset | Train | Validation | Test |
|---|---:|---:|---:|
| CPT passages | 20 | 0 | 0 |
| Grounded SFT examples | 20 | 0 | 0 |

The register contains 20 records and excludes 0 from targets.
A record can group several dimensions or retain a source discrepancy; counts do
not describe the number of unique new numerical discoveries. Exact eligibility,
measurement-kind, evidence-status and input/output hashes appear in
[manifest.json](manifest.json).

No physical component was measured. Every curated record must explicitly retain
`physical_measurement_performed: false`. Factory references, supplier products,
related engines and unresolved unit or datum conflicts retain their own scope.
Neither supplier declarations nor prepared data establish physical fit, a
machining approval or a modified-engine load or speed limit.

Each accepted record produces exactly one CPT passage and one native
`system`/`user`/`assistant` conversation. The SFT user supplies the authored record
narrative and full measurement object. The answer extracts that evidence and
cites its stable record ID. This is supplied-record extraction, not an
independent engineering-reasoning benchmark or a test of unaided factual recall.
Authored wording is synthetic; attributed source facts are not invented.

All targets preserve application, component, parameter, value, units, evidence
status, caveats and complete `measurement_metadata`. Required metadata fields
are `measurement_kind`, `datum`, `conditions`, `tolerance` and `variant_basis`;
additional reviewed fields remain intact. Metadata also appears in
[passages.jsonl](passages.jsonl) and per-row [provenance.jsonl](provenance.jsonl).
Nominal product dimensions, machining references, service limits, physical
measurement, conversions and unit conflicts remain distinct. Missing units or
unseen drawing datums must not be repaired by inference.

## Rebuild and verification

Run from the repository root using Python's standard library:

```sh
PYTHONDONTWRITEBYTECODE=1 python training/m64-precision-20261025/prepare.py
PYTHONDONTWRITEBYTECODE=1 python training/m64-precision-20261025/verify.py
PYTHONDONTWRITEBYTECODE=1 python training/m64-precision-20261025/test_verify.py
```

The [993 Turbo](../993-turbo-20261002/README.md),
[Mezger materials](../mezger-turbo-materials-20261003/README.md),
[German-source](../mezger-german-sources-20261003/README.md),
[first M64 measurement](../m64-measurements-20261024/README.md),
[deeper M64 dimension](../m64-dimensions-deep-20261024/README.md), and
[multilingual measurement](../m64-world-measurements-20261025/README.md) packs
remain frozen. Their six builders, split ledgers and exclusion lists are pinned
by SHA-256. All prior accepted and excluded IDs remain reserved. New records use
the `M64-PREC-` namespace.

Source IDs, conservative publisher families and exact reviewed claims inherit
all six packs' partitions. Legacy claim fingerprints remain present alongside
fingerprints containing component identity and complete measurement metadata.
Co-cited sources and identical claims form connected components. A component
joining incompatible frozen partitions fails instead of moving earlier records.
No new holdout anchors are forced; new unassigned components default to train.
This build contains 5 components. Empty validation or test files are
intentional when no new component inherits those partitions. Earlier holdouts
remain reserved when combining packs.

LN Engineering's knowledge base shares its existing `lnengineering.com` family.
TurboKraft's parts store shares `turbokraft.com`; Metelli's manufacturer documents
share `metelligroup.it`; Würth regional manufacturer documents share `wuerth.com`.
ARP manufacturer catalogues and identified instruction mirrors share `arp-bolts.com`.
This publisher-only rule does not regroup Pauter documents whose titles mention
ARP materials. Rules use explicit original-publisher attribution rather than a global alias for
a retailer or mirror host. Inherited KTS, CP-Carrillo, Turbosmart, MAHLE, Porsche,
FIA, Melett, Federal-Mogul, RUF and TTE policies remain explicit. Family grouping
protects partition isolation; it does not establish independent corroboration or
product interchangeability. The frozen Pauter family remains in validation.

The verifier checks complete input/output hashes, canonical source provenance,
reserved IDs, reconstructed connected components, all six prior partition
constraints, exact trainer registrations, native message roles, stable citations,
exact authored answers and full measurement metadata. Each accepted record
appears once per dataset; refreshed hashes and inflated counts cannot legitimize
duplicated targets.

All 32 focused tests pass. They exercise deterministic isolated rebuilds,
accepted/excluded ID reservation, fourth/fifth/sixth-pack hash dependencies,
partition corruption, metadata-aware fingerprints, complete qualification and
measurement retention, publisher mirrors, forged families/components, duplicate
amplification, trainer redirection, omitted output hashes and unsupported
physical-measurement claims. Artifact integrity is separate from physical
engineering qualification.

## Formats and training hand-off

`cpt_text/{train,valid,test}.jsonl` contains a `text` column.
`sft_messages/{train,valid,test}.jsonl` contains native messages with `role` and
`content`. [dataset_info.json](dataset_info.json) supplies conventional
LLaMA-Factory-style ShareGPT and CPT registrations, not a complete trainer
configuration.

Before training, pin model/tokenizer/trainer revisions, apply the native chat
template, audit sequence lengths and truncation, and check assistant loss masking.
Complete metadata can increase sequence length. This preparation does not prove
a future trainer will retain it without truncation. Empty evaluation registrations
must not be treated as populated datasets. No model or token quality was assessed.

Public sources remain their publishers' property. Only factual metadata and
authored paraphrases are included; raw manuals, supplier PDFs, scans, copied
passages, private paths and vehicle identifiers are excluded. Source provenance
distinguishes acquired document bytes from other reviewed representations.
