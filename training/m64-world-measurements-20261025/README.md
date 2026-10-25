# Multilingual M64 measurement training data

This separate increment prepares authored English CPT passages and synthetic,
supplied-record SFT conversations from the reviewed
[measurement register](../../catalog/reference/m64-world-measurements-20261025/facts.json).
It prepares data only. No model training, tokenization, context-fit evaluation or
weights are produced.

| Dataset | Train | Validation | Test |
|---|---:|---:|---:|
| CPT passages | 30 | 0 | 0 |
| Grounded SFT examples | 30 | 0 | 0 |

The register contains 30 records and excludes 0 from targets.
Counts describe scoped evidence records; one record can group several dimensions
or preserve a source discrepancy. They do not count unique new dimensions.
Exact eligibility, measurement-kind and evidence-status counts and input/output
hashes appear in [manifest.json](manifest.json).

No physical component was measured. Every curated record must retain
`physical_measurement_performed: false`. Supplier replacements, aftermarket
products, historical editions and related racing engines retain their stated
application. Research for a 993 Turbo above 550 PS provides context; these data
establish neither fit nor engineering approval for a modified engine.

Each accepted record produces exactly one CPT passage and one native
`system`/`user`/`assistant` conversation. The SFT user supplies the authored
record narrative and complete measurement object. The answer extracts that
supplied evidence and cites its stable record ID. This is supplied-record
extraction, not an independent engineering-reasoning benchmark or a test of
unaided factual recall. Authored wording is synthetic; attributed source facts
are not invented.

All targets preserve application, component, parameter, value, units, evidence
status, caveats and complete `measurement_metadata`. Required metadata fields
are `measurement_kind`, `datum`, `conditions`, `tolerance` and `variant_basis`;
additional reviewed fields remain intact. Full metadata also appears in
[passages.jsonl](passages.jsonl) and per-row [provenance.jsonl](provenance.jsonl).
Nominal catalogue sizes, lookup windows, conversions, catalogue discrepancies
and checking conventions retain their different meanings. Supplier profile
names such as GT2 EVO, 934 or RUF BTR do not certify identity with a factory cam.

## Rebuild and verification

Run from the repository root using Python's standard library:

```sh
PYTHONDONTWRITEBYTECODE=1 python training/m64-world-measurements-20261025/prepare.py
PYTHONDONTWRITEBYTECODE=1 python training/m64-world-measurements-20261025/verify.py
PYTHONDONTWRITEBYTECODE=1 python training/m64-world-measurements-20261025/test_verify.py
```

The [993 Turbo](../993-turbo-20261002/README.md),
[Mezger materials](../mezger-turbo-materials-20261003/README.md),
[German-source](../mezger-german-sources-20261003/README.md),
[first M64 measurement](../m64-measurements-20261024/README.md), and
[deeper M64 dimension](../m64-dimensions-deep-20261024/README.md) packs remain
frozen. Their five builders, split ledgers and exclusion lists are pinned by
SHA-256. All earlier accepted and excluded IDs remain reserved. New records use
the `M64-WORLD-` namespace.

Source IDs, conservative publisher families and exact reviewed claims inherit
all five packs' partitions. Legacy claim fingerprints remain present alongside
fingerprints containing component identity and complete measurement metadata.
Co-cited sources and identical claims form connected components. A component
joining incompatible frozen partitions fails instead of moving earlier records.
No new holdout anchors are forced. All 7 current components inherit train or
remain unassigned and default to train; the empty validation and test files are
intentional. Earlier holdouts remain reserved when combining these packs.

KTS Turbobillet X catalogue and datum documents hosted by Real Turbo and
EPARTRADE share the `ktsturbobilletx.com` family. CP-Carrillo's own and identified
mirrored catalogues share `cp-carrillo.com`. These rules use explicit original
publisher attribution, not a global alias for a trade or retailer website.
MAHLE's EPARTRADE mirror retains its separate frozen MAHLE family. Inherited
Porsche, FIA, Melett, Federal-Mogul, RUF and TTE policies remain explicit.
Turbosmart's identified GCG catalogue mirror, manufacturer-linked NetSuite guide
and own product page share `turbosmart.com`. None of these host rules treats a
generic retailer or document platform as a manufacturer.
Publisher grouping protects partition isolation; it does not establish product
interchangeability or independent corroboration.

The frozen Pauter family belongs to validation. New comparison metadata may cite
prior Pauter record IDs without treating those records as new training targets.
This increment does not move Pauter evidence into train. Any future accepted
Pauter evidence must inherit its existing partition.

The verifier checks complete input/output hashes, canonical source provenance,
reserved IDs, counts, reconstructed connected components, all five prior
partition constraints, exact trainer registrations, native message roles,
stable citations, exact authored answers and full measurement metadata. Each
accepted record appears once in each dataset; refreshed hashes and inflated
counts cannot legitimize duplicated targets.

All 28 focused tests pass. They cover deterministic isolated rebuilds, frozen
fourth/fifth-pack dependency coverage, accepted/excluded ID reservation,
partition corruption, metadata-aware fingerprints, complete qualification and
measurement retention, explicit publisher mirrors, forged source families and
component summaries, duplicate amplification, trainer train-to-holdout
redirection, omitted output hashes and unsupported physical-measurement claims.
Artifact integrity does not establish suitability for manufacture.

## Formats and training hand-off

`cpt_text/{train,valid,test}.jsonl` contains a `text` column.
`sft_messages/{train,valid,test}.jsonl` contains native messages with `role` and
`content`. [dataset_info.json](dataset_info.json) supplies conventional
LLaMA-Factory-style ShareGPT and CPT registrations, not a complete trainer
configuration.

Before training, pin model/tokenizer/trainer revisions, apply the native chat
template, audit sequence lengths and truncation, and check assistant loss
masking. Complete metadata can increase sequence length. This preparation does
not prove a future trainer will preserve it without truncation. Empty evaluation
registrations must not be treated as populated datasets. No model or token
quality was assessed.

Public sources remain their publishers' property. Only factual metadata and
authored paraphrases are included; raw manuals, supplier PDFs, scans, copied
passages, private paths and vehicle identifiers are excluded. Source provenance
distinguishes acquired document bytes from other reviewed representations.
