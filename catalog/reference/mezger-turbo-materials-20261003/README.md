# Mezger turbo materials research reference, 3 October 2026

This separate increment contains 203 original factual records linked to 46 canonical sources: 20 air-cooled/OEM applicability records, 41 racing/documentary records, 74 water-cooled/GT comparison records, 33 material/process records and 35 aftermarket supplier records. Forty-one catalogue sources are new; existing source files and pinned evidence are retained unchanged.

| File | Purpose |
| --- | --- |
| [facts.json](facts.json) / [facts.csv](facts.csv) | Machine-readable facts with exact application, component, locator and qualification |
| [source-crosswalk.json](source-crosswalk.json) / [sources.csv](sources.csv) | Catalogue source paths, URLs, editions and hashes of inspected local-only captures |
| [additional-readings.json](additional-readings.json) | Additional inspected Porsche articles retained as bibliographic leads; excluded from technical targets |
| [research-gaps.json](research-gaps.json) | Missing material specifications, dimensional definitions and documentary acquisition routes |
| [manifest.json](manifest.json) | Reference and canonical-source integrity hashes |

Record IDs use MEZGER-A, -R, -W, -M and -P prefixes. Each fact has `application`, `component`, `parameter`, `value`, `unit`, `evidence_status`, `source_ids`, `locator`, `caveat` and `training_eligibility`. Arrays retain published ranges; objects retain composite specifications. Unknown values remain null, not estimated manufacturing dimensions.

There are 30 `eligible`, 165 `qualified_only`, five `teach_uncertainty_only` and three `exclude` records. These labels govern the derivative corpus, not material certification. A source-confirmed generic family still has an unknown exact grade. The SAE abstract leads and unmapped Ferrea application record are excluded from technical training. Absence is explicitly limited to the inspected corpus.

The detailed [research synthesis](../../../docs/research/mezger-turbo-materials-20261003/README.md) distinguishes the air-cooled original family, mixed-cooling racing variants, water-cooled 996/997 descendants, GT3 comparisons and later non-Mezger boundaries. [Training preparation](../../../training/mezger-turbo-materials-20261003/README.md) preserves those distinctions and the old pack's partitions.

Only original factual paraphrases and provenance metadata are published. Raw manuals, third-party brochures, copied charts, scans, internal review excerpts and local capture paths are excluded. Capture hashes identify reviewed material; they do not grant redistribution rights. Canonical literature product URLs and the actual reviewed public mirror URL are distinguished where necessary.
