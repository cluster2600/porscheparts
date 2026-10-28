# Additional engine dimensions register

This increment contains 107 records: 89 accepted documentary/supplier records
and 18 excluded FIA leads. It links 20 source records, including 17 new entries.
No physical part was measured. Published specifications, clearance intervals,
derived comparisons and unresolved conflicts remain distinct.

The [research report](../../../docs/research/m64-measurements-20261024/README.md)
explains the main interfaces. The [training pack](../../../training/m64-measurements-20261024/README.md)
provides deterministic build and verification commands.

| File | Contents |
|---|---|
| [facts.json](facts.json) / [facts.csv](facts.csv) | Values, component/application, source locators, caveats and full measurement metadata |
| [source-crosswalk.json](source-crosswalk.json) / [sources.csv](sources.csv) | Editions, URLs, representation hashes and distinction between original-document bytes and reader/availability receipts |
| [research-gaps.json](research-gaps.json) | Missing original dimensions, unsupported routes and conflicts |
| [additional-readings.json](additional-readings.json) | Supplementary readings and acquisition scope |
| [manifest.json](manifest.json) | SHA-256 closure of the register and its canonical sources |

Every record keeps measurement kind, datum, conditions, tolerance, variant basis
and `physical_measurement_performed: false`. Nominal dimensions are not measured
geometry; standard bearing intervals are not wear limits; ring axial heights
are not radial depths or end gaps. A rounded catalogue diameter is not a
manufacturing tolerance. Generic or aftermarket values retain that application.
Excluded image-only FIA rows have null values and create no training targets.

Public documents remain their publishers' property. Only original factual
paraphrases and metadata are included. Existing manual registers, canonical
source files and the three earlier training packs are preserved unchanged.
