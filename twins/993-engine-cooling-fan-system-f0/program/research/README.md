# 911 / 935 / 993 cooling impeller research

[Impeller program](../../README.md) · [English synthesis](SYNTHESIS.md) · [Complete index](source-index.json) · [Integration rules](INTEGRATION.md)

The separate [935 engine/horizontal cooling-system intake](../../../935-horizontal-cooling-system/research/README.md)
contains the 50-entry input matrix and four verified public synthesis views from
40 bounded language passes. Engine-data coverage remains partial; the four historical lanes below are
a separate earlier delivery.

The subsequent [material/process corpus](materials-20261003/ADMISSION.md)
adds eight original files, 143 property records, 25 sources and fourteen open
target-route process requirements. It has a separate immutable import manifest;
the historical twenty-file/four-lane registry below remains unchanged.

All four research deliveries from October 3, 2026 are integrated: **20 original
files, 140 source records and 130 URL groups**. Coverage is limited to the pages
and queries actually consulted. These groups are not 130 independent
measurements: translations, copies and accounts may share an origin. No
publication validates the project model, the scan's 935/993 identity or a part
for manufacturing.

## Four research lanes

| Lane | Report and limits | Complete data | Delivered coverage |
|---|---|---|---|
| OEM / history | [Report](corpus/oem/research_report.md) | [Records](corpus/oem/oem_research.json), [sources](corpus/oem/sources.json), [parameter CSV](corpus/oem/oem_parameters.csv) | 32 sources, 114 records; PET, variants, historical conditions |
| Aftermarket / manufacturers | [Report](corpus/aftermarket/aftermarket_fan_supplier_review.md), [queries and limits](corpus/aftermarket/aftermarket_search_log.json) | [Catalog](corpus/aftermarket/aftermarket_catalog.json), [85 quantitative claims CSV](corpus/aftermarket/aftermarket_parameters.csv), [source CSV](corpus/aftermarket/aftermarket_source_manifest.csv), [product CSV](corpus/aftermarket/aftermarket_products.csv) | 44 sources, 28 products; impeller, hub, fan housing and complete assembly distinguished |
| Multilingual forums | [Report](corpus/forums/multilingual_forum_research.md), [coverage and gaps](corpus/forums/coverage_and_gaps.md) | [Corpus](corpus/forums/forum_corpus.json), [source CSV](corpus/forums/forum_sources.csv), [claim CSV](corpus/forums/forum_claims.csv), [9 reported bench points](corpus/forums/reported_bench_series.csv) | 36 sources, 45 claims; copy lineage and sometimes unknown speed axes |
| Geometry / performance | [Notes](corpus/geometry/engineering-notes.md), [measurement checklist](corpus/geometry/measurement-checklist.md) | [Evidence](corpus/geometry/evidence.json), [104-parameter contract](corpus/geometry/parameter-contract.json) | 28 sources, 22 claims; nine computed quantities and seven acceptance gates |

The original research reports are preserved byte for byte, including multilingual
quotations and original terminology. The program's main navigation, synthesis
and integration instructions are in English. No third-party drawing,
photograph, manual, CAD file or scan is republished here. The
[import manifest](corpus/import-manifest.json) retains the transfer SHA-256 and
the digest of every original text.

## Traceability and deduplication

The [common index](source-index.json) retains every original source ID, lane,
file and JSON pointer or CSV row position. Added IDs `AF-P###` and `OEM-R###`
identify original rows without IDs; they do not replace their content.
Normalization groups identical URLs and page anchors in the same PDF without
merging editions, variants, conditions or conclusions. The lineage recorded
within each lane is still needed to recognize other copies.

PorscheFanatics and project pages are marked as non-independent. Other links
may be independent of the project without being primary measurements or
independent corroboration of one another. Original records retain access
status, locators, rights, uncertainty and contradictions.

The [English preliminary-ledger view](PRELIMINARY_LEDGER.md) explains the first
slice of eight sources and its historical assumptions. Its
[archived French source record](dossier.json) remains unchanged; the English
view has its own identity and does not claim the source file's digest.
**This preliminary slice is not the complete corpus.** The complete index and
four lanes are the research references. `catalog/parts/*.json` remains the part
catalog's source of truth. Documentary parameters are not automatically
promoted into geometry, meshes, boundary conditions or material properties.

## Reproducible checks

```sh
make fan-program-check
python3 twins/993-engine-cooling-fan-system-f0/source/build_research_index.py --check
python3 twins/993-engine-cooling-fan-system-f0/source/check_research_registry.py
```

These checks verify the twenty original hashes, source references for all
indexed records and the absence of promotion to engineering validation.
To regenerate only the index after a documented import, run
`build_research_index.py` without `--check`; preserve the originals.
