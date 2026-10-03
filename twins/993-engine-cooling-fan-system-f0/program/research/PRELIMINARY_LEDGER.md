# Preliminary research ledger — English reading view

[Research home](README.md) · [Complete index](source-index.json) · [Archived French source](dossier.json)

This is an English reading view of the historical preliminary slice: eight
sources, five claims, ten parameters and four open contradictions. It is not
the complete research corpus and does not replace its more detailed records.
Original source IDs, numerical values, units and preliminary statuses are
retained. The French JSON is preserved byte for byte as a source archive;
this translated Markdown is a separate artifact, not the original bytes.

Archived source SHA-256: `fd6c2fb2c70d4f0696e082615f8ad20e733a02c865099ffb73980c366df585c6`.

## Eight source records

| Stable source ID | English description / locator | Preliminary access status | Independent of project |
|---|---|---|---|
| `oem-originale-05` | Porsche ORIGINALE 05, PDF 7 / printed page 83 | `reviewed_in_existing_mission` | Yes |
| `oem-pet-993-de` | German Porsche PET 993, 1998 catalog edition; plate 105-00, PDF 77–79 | `reported_pending_targeted_verification` | Yes |
| `oem-training-964-mirror` | Porsche P10-L 964 training, Club911 copy; printed 22 / PDF 26 and printed 28 / PDF 32 | `reported_pending_targeted_verification` | Yes |
| `sae-920789` | Cooling System Layout for High Performance Cars, Hochkönig/Michael, 1992; abstract, full curve not consulted | `reported_pending_targeted_verification` | Yes |
| `supplier-carpoint-sheet` | Carpoint impeller/alternator dimension sheet; single page, application and datums unclear | `reported_pending_targeted_verification` | Yes |
| `project-reference-params` | Repository Turbo reconstruction parameters; `source/picogk-reference/reference.json` | `reviewed_local` | No |
| `project-research-20260928` | Project research inventory dated September 28; `reference-research.json` | `reviewed_local` | No |
| `project-related-porschefanatics` | PorscheFanatics Carrera 96410601531 record; “All models” application not accepted for Turbo | `independent_corroboration_excluded` | No |

Direct URLs, language metadata and local references remain in the archived
source and the complete index. External publications are independent of the
project, but independence between publications must be checked separately.
Project outputs and related pages do not independently corroborate the project.
All eight records permit reference only: no document or geometry redistribution;
geometry licenses are unknown.

## Five preliminary claims

| Stable claim ID | English claim and scope | Source / status |
|---|---|---|
| `c-oem-turbo-carrera-distinct` | ORIGINALE distinguishes Turbo impeller 96410601522 and Carrera 96410601531. PDF 7 / printed 83 does not identify the scan. | `oem-originale-05`; `documented_identification` |
| `c-oem-rs-distinct` | German PET report lists Carrera .31, RS M64.20 .40, Turbo M64.60 .21/.22 and Turbo fan housing 99310666750. Application and edition notes belong in the full OEM corpus. | `oem-pet-993-de`; `reported_pending_verification` |
| `c-964-ratios-separate` | Training report separates impeller ratio 1.6 from Tiptronic alternator ratios 2.23 → 2.68. PDF 26 does not automatically transfer to 993 Turbo. | `oem-training-964-mirror`; `reported_pending_verification` |
| `c-935-family-unresolved` | “935” covers horizontal flat-fan and vertical 935/78 arrangements; scan identity is unresolved. This was a preliminary question awaiting detailed references. | No source in this slice; `research_question` |
| `c-no-scan-rescale` | The 245 mm working diameter does not authorize rescaling the private scan. It is a model parameter without scan calibration. | `project-reference-params`; `project_boundary` |

Every claim retains `engineering_validation=false`.

## Ten preliminary parameters

| Stable parameter ID | Value / unit | Variant and conditions | Source / status |
|---|---|---|---|
| `p-model-turbo-diameter` | 245 mm | `turbo-reference-20260928`; earlier reported FVD envelope, not OEM measurement or scan datum; `rotor_diameter_mm` | `project-reference-params`; `project_assumption` |
| `p-model-turbo-blades` | 11 / `1` | `turbo-reference-20260928`; earlier photographic count, not scan identity; `blade_count` | `project-reference-params`; `project_assumption` |
| `p-model-turbo-pitch` | 48 deg | `turbo-reference-20260928`; PicoGK convention, distinct from CFD control 36° and candidate 42°; `blade_pitch_deg` | `project-reference-params`; `project_assumption` |
| `p-964-training-blades` | 12 / `1` | `964_Carrera`; training page, no inferred 993 Turbo geometry; PDF 26 | `oem-training-964-mirror`; `reported_pending_verification` |
| `p-964-training-stator` | 17 / `1` | `964_Carrera`; fan housing/stator for this application; PDF 26 | `oem-training-964-mirror`; `reported_pending_verification` |
| `p-964-training-fan-ratio` | 1.6 / `1` | `964_Carrera`; impeller ratio, separate from Tiptronic alternator; PDF 26 | `oem-training-964-mirror`; `reported_pending_verification` |
| `p-964-training-flow` | 1,010 L/s | `964_Carrera`; no speed in the reported table, not a performance curve; PDF 32 | `oem-training-964-mirror`; `reported_incomplete_conditions` |
| `p-supplier-11-diameter` | 244.5 mm | `supplier_11_blade_unspecified`; datum, tolerance and exact application unknown; single-page 11-blade column | `supplier-carpoint-sheet`; `reported_pending_verification` |
| `p-supplier-12-diameter` | 254 mm | `supplier_12_blade_unspecified`; datum, tolerance and exact application unknown; single-page 12-blade column | `supplier-carpoint-sheet`; `reported_pending_verification` |
| `p-scan-unit` | `null` value and unit | `private_935_scan`; OBJ declares no units, independent measurement required; `program/SCAN_INTAKE.md` | No source; `missing` |

`1` denotes a dimensionless count or ratio. Uncertainty is `null` for all ten
parameters, and every `engineering_use_approved` flag remains false. Unknown
uncertainty is not zero uncertainty.

## Four open contradictions

| Stable contradiction ID | Affected records | Resolution still required |
|---|---|---|
| `x-diameter-scope` | `p-model-turbo-diameter`, `p-supplier-11-diameter`, `p-supplier-12-diameter` | Verify application, datum and rounding differences; neither average values nor rescale the scan. |
| `x-drive-ratios` | `c-964-ratios-separate`, `p-964-training-fan-ratio` | Identify component, pulley, speed, model and installation before use. |
| `x-935-993-identity` | `c-935-family-unresolved`, `c-no-scan-rescale` | Exact Porsche reference, configuration, metrology and scan rights remain required. |
| `x-self-corroboration` | `project-related-porschefanatics`, `project-research-20260928` | Trace author and primary source; group copies into one provenance chain. |

## Coverage and historical missing inputs

| Stable coverage ID | Lane / preliminary source IDs |
|---|---|
| `search-oem-history` | OEM/PET/history; `oem-pet-993-de`, `oem-training-964-mirror`, `oem-originale-05` |
| `search-aftermarket` | Aftermarket/manufacturers; `supplier-carpoint-sheet` |
| `search-forums` | Multilingual 911/935 forums; no source ID in this slice |
| `search-geometry-performance` | Geometry/performance/parametric data; `sae-920789` |

The source record marks all four lanes `lane_delivered_scope_bounded` and links
their delivered files. Requested languages were de/en/fr; its
`queries_executed` arrays remain empty rather than inventing an exhaustive query
log. Full lane files describe actual coverage, conditions, contradictions and
access. See the complete index and lane reports for the subsequently delivered
32 / 44 / 36 / 28 source records.

The preliminary missing-input list asked for detailed lane corpora/locators/logs,
scan identity/units/calibration/datum/rights, airflow curves with pressure/
impeller speed/bench conditions/uncertainty, and measured OEM/aftermarket
interfaces, drive and load path. The detailed research deliveries are now
available; retaining that historical list does not make them a current blocker.
Physical inputs remain subject to the [validation plan](../VALIDATION_PLAN.md).
