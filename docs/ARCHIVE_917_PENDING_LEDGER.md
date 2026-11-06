# Pending items left in the archived 917 dossiers

Issue #426. `archive/**` is never edited, so the outcome of every item still
open in the four archived dossiers below is recorded here instead. The 917 line
is retired as a product ([ARCHIVE.md](ARCHIVE.md)).

**Status of this ledger:** dispositions *proposed* on 2026-11-06 by an agent
from the dossiers and the current repository. They become final when the owner
confirms them on #426. "Abandoned" means not pursued for the 917 line: nothing is
deleted, and the archived dossier stays the record.

| # | Archived dossier | Pending item, as the dossier states it | Current state (checked 2026-11-06) | Proposed disposition |
|---|---|---|---|---|
| 1 | [F18 boundary human review](../archive/917/docs/917_BOUNDARY_HUMAN_REVIEW_F18.md) | 944 boundary components with `human_review_state: pending` (19 `candidate`, 925 `unclassified`, zero interfaces confirmed) | The F18 inventory is unchanged; no review record exists | **Carried into #461**, scan segmentation, datums and the F8 missing-interface list. The review is the first step of that issue. |
| 2 | F18 | After review, a second physical measurement or a variant-specific primary source for each potentially functional shape, then a separate interface-contract proposal | No measurement, no contract | **Carried into #461** (measurement, external-blocked) |
| 3 | [F27 physical metrology campaign](../archive/917/docs/917_PHYSICAL_METROLOGY_CAMPAIGN_F27.md) | Execute the campaign (frozen protocol, chain of custody, three scale checks, orientation, variant adjudication); the local JSON moves to `campaign_execution_complete_pending_binding_review` only after real execution | The template is still `blank_template_not_executed`; no campaign was run | **Carried into #461** for the measurements, and into **#462** for the scan's licence and provenance |
| 4 | F27, "Suite après F27" | A separate binding adapter that consumes the signed report, raises the scan's evidence level and opens CAD inputs case by case | Not started; it depends on item 3 | **Abandoned for the 917 line.** Reopen only if the 917 product is revived and item 3 is accepted. |
| 5 | [F42b GPU component factory](../archive/917/docs/917_COMPONENT_FACTORY_F42B_GPU.md) | `runtime.qualified_image_ref` is `null` and the runtime is `pending` at creation | **Done:** `twins/reference-917-engine/component-factory-f42b-gpu.json` now records `qualification_status: qualified_public_linux_amd64_digest`, with evidence `evidence/f42b-gpu-runtime-qualification.json` | **Closed.** No action. |
| 6 | F42b | The GPU enrichment run: the `connecting_rod` pilot, then the five remaining families, gated by a 10,800 s projection | Contract status `specified_pending_qualified_runtime_and_private_inputs`; never executed (paid GPU, private inputs) | **Abandoned for the 917 line.** The SimReady path is exercised on current parts instead; see #459 and #561 for its blockers. |
| 7 | [Modular compute stack](../archive/917/docs/917_MODULAR_COMPUTE_STACK.md) | Split the monolithic GPU image into five images (`simready-core`, `cae-reference`, `physicsnemo-cae-cu12`, `ovrtx-vlm-cu129`, `media-cpu`) | `containers/physicsnemo-cae-cu12.lock.json` and `containers/cae-reference-f31.Dockerfile` exist; the other three were never built under these names | **Carried into #404 / #406**, the versioned rebuild of every image recipe |
| 8 | Modular compute stack, migration step 7 | A full modular run that reproduces the SimReady artefacts and compares cost, start-up time and transfer size with the monolithic run | Never run | **Abandoned for the 917 line**; the stack comparison belongs to #404 for current workloads |

## What would change a disposition

- The owner reviving the 917 product reopens items 4, 6 and 8 as new issues
  that cite this ledger.
- An accepted item 3 campaign reopens item 4.
- None of these items carries a physical, manufacturing or engine-start claim;
  every archived gate stays closed.
