# Corpus coverage for the Qwen3 continuation

This is a coverage snapshot at repository commit `09f2728a646d0cf6e30c07df28800f26454a5276` (main after PR 119), with the new corrective-data manifest inspected separately. **The selected Qwen3 adapter has not trained on the complete Porscheparts guide or all collected project data.** Its actual curriculum is 24 rows, 12 objectives and 11 paragraphs from six source families. The current correction pack has 20 rows, 10 objectives and 10 paragraphs from those same six training families. Counts of translations, paragraphs, weighted replay instances, citations, source records and parameter definitions are different quantities.

The phrase “guide de Porsche Parts” does not identify one unique file in this checkout. This audit covers the root [README](../../README.md), [documentation index](../../docs/README.md), explicitly named training guides and the complete impeller research index. An external site/wiki guide is not assumed to have identical contents. The machine-readable [coverage ledger](corpus-coverage.json) binds the inspected files and records the scope and limits. No reviewer directory, private-session journal or new test pool was opened.

## Metal additive manufacturing: PR 110 / 111 / 113 / 116

| Material | Exact inventory | Actual state for this continuation |
| --- | --- | --- |
| Discovery/source register | 79 research records; initially seven licensed English full-text articles | Bibliographic/reference coverage; public visibility and metadata are not training permission |
| V1 exports, PR 110 | CPT 81/17/18; SFT 47/5/6, train/validation/test | Historical, overlapping; incorrect MET004 snapshot attribution was corrected in v2 |
| V2 exports, PR 111 | CPT 36/5/8; technical SFT 27/1/2; optional metadata SFT 20/4/4 | Prepared historical formats; tokenizer-bound arrays are alternate representations, not more examples |
| Grounded v3, PR 113 | 10 English CC BY articles, 405 cleaned paragraphs: 256 train / 86 validation / 63 test. CPT 50/9/14; SFT 53/16/21, covering 40 questions in 90 language variants | Corpus prepared; separate CPU general-Qwen2.5 pilot used 53 SFT rows. No evidence here that CPT was trained |
| V3 exclusions | 658 quarantine records; 30 old explanations excluded; zero detected cross-source lexical near-duplicates | Excluded pending review. The duplicate detector does not establish semantic independence |
| Selected Qwen3 compact curriculum, PR 116 | 24 FR/EN rows, 12 objectives, 11 paragraphs, six training families; 1,388 supervised assistant tokens, 12 optimizer steps | Actually trained; identical tensors retained by the fidelity inference-profile iteration |
| Other corrective/precision exports | Corrective v4: 191 rows / 22 paragraphs. Precision v6: 53 / 22. Precision v7: 59 / 25 | Historical development; v7 candidate was trained and rejected. These overlapping exports cannot be summed |
| Current corrections | 20 FR/EN rows, 10 objectives, 10 paragraphs, six families | Data prepared and provenance-checked. New training and evaluation completion must be read from their own receipts |

The selected six training families are `MET001`, `MET002`, `thermal_en_prediction`, `thermal_en_critical`, `thermal_en_flow` and `NEW_RESIDUAL`. Original v3 validation families are `MET003` and `NEW_QUALITY`; original test families are `MET004` and `NEW_WAAM`. Historical split labels are retained for provenance. Inspected/exposed historical material is development for this continuation and is not claimed to be newly blind. Source/article exposure, concept familiarity and unknown base-model pretraining exposure limit generalisation claims.

The historical fidelity evaluation has 12 primary and eight supplemental questions: adapter 11/12 and 7/8; paired base 12/12 primary, with no supplemental base run. **No LoRA gain was demonstrated.** The adapter omitted the requested gradual transition and added an unsupported dominant-influence inference. The current pack corrects qualifier/inference behaviour using original training-family prose; it copies neither those retired fidelity passages nor held-out-source answers. Independent scientific and translation review remains pending.

## Impeller research: PR 118 / 119

The [complete research index](../../twins/993-engine-cooling-fan-system-f0/program/research/source-index.json) contains 20 preserved original files, 140 source records in 130 URL groups and 294 indexed records. Its lanes contain 32 OEM, 44 aftermarket, 36 forum and 28 geometry sources. Indexed content comprises 114 OEM records, 28 aftermarket products, 85 quantitative aftermarket claims, 45 forum claims and 22 geometry claims. These heterogeneous counts do not represent independent measurements.

The parameter contract defines **104 parameter fields**, nine conditional computed quantities and seven acceptance gates, all open. It contains no implication that all fields have measured values. There are **zero impeller SFT rows** in the current correction pack. This corpus is a traceable reference/RAG candidate, with variant, origin, uncertainty and contradictions preserved. Forums, hypotheses, supplier assertions and unknown values remain at their evidence levels. No copied PDF/manual, photograph, commercial scan or private geometry is admitted into the training set.

The delivered metadata records CC BY 4.0 for generic FAN-01 dataset `GEO-S009`, but its archives were not downloaded or internally inspected. The separately licensed arXiv paper `GEO-S010` is not shown to permit CC BY prose reuse. Neither is a measured Porsche impeller. Other OEM/supplier/manual/scan reuse rights are not established by public access.

## Separate Porsche documentary and engineering programmes

| Corpus/programme | Exact inventory or receipt | Boundary |
| --- | --- | --- |
| Porsche document extraction / private RAG | 14,101 index records: 12,864 PET occurrences, 111 technical entries, 195 torque rows, 235 procedure-index entries, 15 site-review records and 681 full-text pages (674 PET + seven ICE review). 6,013 reference union; 452 illustration groups. Training sampled 677 rows, with 40 validation and 40 test rows | Separate Qwen2.5-Coder/MLX adapter, 320 recorded steps. Narrow field extraction improved; free-question outputs failed or remained incomplete. Raw corpus/weights stay private and were not reopened here. Workshop/book integration remains incomplete |
| 993 Turbo preparation pack | 248 authored CPT passages, split 237/3/8; 251 synthetic grounded SFT rows, split 238/4/9; 51 source IDs used | Prepared, untokenized and untrained. `ENGINE-D163` fan-ratio hypothesis and 2,496 unreviewed Carrera OCR rows excluded. Calculations and supplier claims retain labels; source documents are not copied |
| PicoGK/OpenUSD/Python/OpenFOAM engineering pilot 001 | 576 training rows: Python 96, OpenFOAM 96, OpenUSD 192, PicoGK 192; 102 validation rows | Separate Qwen2.5-Coder-1.5B/MLX programme; rejected on graph and retention gates |
| Engineering refinement 005 | 3,224 training records, 3,177 unique prompts, 4,776 weighted instances; historical filtered comparison 150 cases | Distinct code curriculum. Final PicoGK 7/8 misses its 95% domain floor. Exposed cases are regression/development evidence; 33 validation and 44 test rows previously repeated training prompts |
| Engineering research registers | Initial nine scientific + nine API/dataset records; eight follow-up records; 27 refinement research records | Registers overlap and are not independent publication totals. Zero third-party dataset rows were imported; methodologies/API references informed authored exercises |

The scientific Qwen3 model/tokenizer revision is `cdbee75f17c01a7cc42f958dc650907174af0554`. The distinct MLX Coder snapshot is `b3252a2f97102b1fb1571fec2c9b27219a8536be`, with base weights SHA-256 `daeab4764fb420d161721791cf2e509e2de81a7af4223646e7bed2bf82c57b58`, pinned in its runners and executed refinement receipt. The general CPU Qwen2.5 pilot uses revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`. The JSON ledger links these exact profile/receipt paths.

These model weights, datasets and metrics cannot be merged with the Qwen3 scientific results. Native C# execution, dependency-graph checks, USD scene checks, solver witnesses and repository CI establish their checked software contracts; they do not qualify material properties, physical field predictions, fit, fatigue life or manufacturing. Declared licences for FutureCAD/BRepGround, PicoGK examples, ShapeKernel and rStar-Coder still require input-quality and contamination audits. CAD-Recode’s noncommercial licence, missing GenCAD dataset licence and vision/text task mismatch block automatic admission. No third-party thesis or dataset text is treated as already trained.

The root catalogue currently contains 453 source JSON files and 38 part records, all at `validation.status=concept`. The README’s introductory 34-part count is stale relative to its generated 38-part section and the catalogue. Guide-linked CAD, OpenUSD, simulation evidence and test code have not all been converted into eligible Qwen3 training data. Catalogue records remain the status source of truth. A separate ingestion task (`01a101f9-662f-70f9-bb7d-9836d9cb50b4`) owns further Porscheparts/PorscheFanatics processing; this audit creates no duplicate ingestion.

## New independent reserve and remaining work

The parent supplied only custodian metadata: sealed at `2026-10-03T12:48:43Z`, 24 questions (16 primary + eight supplemental), 10 critical cases, FR 12 / EN 12, four source families. State: `sealed_closed_not_executed`; numerical-gate amendment C is pending. Received registration SHA-256: `d2a72858a98e5b6541e433bf427a46561d8fa3d39979ceb46e2ef58e1f0b0344`. The registration, commitments, IDs, prompts, gold answers and reviewer directory were **not opened** by this audit. No result or stronger independence claim is inferred from these counts.

Remaining work is explicit: review science/translations, complete authorized documentary access gaps, audit provenance/licences before any impeller fact ingestion, preserve task/source families in future splits, and compare new tensors with the pinned base using identical evidence, prompts and decoding. No universal model success or fabrication validity is established by coverage, training loss, citations or code tests.
