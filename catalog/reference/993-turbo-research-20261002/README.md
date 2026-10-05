# Porsche 993 Turbo research reference

This supplement records the 2026-10-02 review of the stock 408 PS Porsche 993
Turbo M64/60 and related factory variants, hybrid turbos and comparison engines.
It contains original factual notes and synthesis with source attribution. It is
not a manufacturing definition, a measured engine dataset or an exhaustive
factory-document collection.

## Files and record contract

| File | Content |
| --- | --- |
| `engine-facts.json` | 164 facts, calculations and qualified statements |
| `turbo-evidence.json` | 36 detailed source records, six secondhand engine-curve series, supplier comparison and measurement requirements |
| `calculations.json` | Four speed examples and 20 assumed engine-flow operating points |
| `unknowns.json` | 19 unresolved documentary or measurement questions |
| `audit.json` | 15 corrections/conflicts, an additional FVD actuator correction and historical-artifact precedence |
| `source-crosswalk.json` | 125 original research references mapped to canonical catalogue source IDs, including explicit exclusions |
| `manifest.json` | File integrity and collection counts |

Every engine fact has a stable `ENGINE-Dnnn` ID, English `parameter`, `value`,
`unit`, `application`, `evidence_status`, `source_ids`, `locator`, `caveat` and
`training_eligibility`. Values may be numbers, strings or arrays. A part number
or a published range remains text; it is not converted into inferred geometry.
`research_id` retains the ID in the original report. Sources resolve to records
in `catalog/sources/`; research IDs resolve through `source-crosswalk.json`.

Turbo records have stable `TURBO-*` IDs, `source_research_ids`, canonical
`source_ids`, `evidence_kind`, `application`, extracted `data`, `limitations`
and `training_eligibility`. Their heterogeneous `data` objects preserve the
available geometry, power-unit wording, map reference conditions and missing
evidence rather than pretending every source provides a measured map.
Secondhand curve points live in `research_context.ruf.curves`; their provenance
and unresolved power/torque inconsistency remain attached.

## Evidence and training rules

- `eligible`: source-qualified fact or explicitly calculated result; preserve
  application, evidence status and caveats in every training example.
- `qualified_only`: supplier claim, related architecture, secondary evidence
  or unresolved convention; teach it with its qualification.
- `exclude_unvalidated_hypothesis`: never teach the value as established fact.
  The conditional fan ratio 1.84 is in this category.
- `documentary_lead_only`: no technical claim may be promoted from unread or
  insufficient source content.
- `teach_uncertainty_only`: answer what remains unknown and what evidence is
  needed. Absence in this corpus does not prove universal absence.

The 300 kW / 408 PS engine is separated from 430/450 PS variants and aftermarket
capacity claims. Published hp, bhp and PS labels are preserved and unit conflicts
are identified. The BorgWarner 950/980 C figures belong to an upgrade table;
balancing test rpm and plotted map speed lines are not mechanical operating
limits. No exact stock K16-6735/6736 compressor or turbine map was verified.

The 20 matching points use declared assumptions, equal bank flow and stated
reference conditions. They are not a measured map, a horsepower prediction or
proof that a hybrid will reach those points. Read the equations and limitations
in `calculations.json` before comparing them with manufacturer maps.

The correction ledger takes precedence over the superseded source notes for
this supplement and its derived training corpus. Historical twins, geometry,
physics inputs and frozen training datasets retain their provenance; these
corrections do not establish that those artifacts were rerun or requalified.

## Rights, privacy and retained context

Raw manuals, scans, copied maps, supplier quotation collections, specific-car
identifiers, private-project blobs and local scratch paths are excluded. The
private project-registry source has an explicit exclusion in the crosswalk.
Published factory engine-number applicability ranges remain service metadata;
they do not identify a project owner's vehicle.

The existing Carrera workshop registry is referenced by path and count only:
2,496 records include 2,190 OCR occurrences, not 2,496 verified Turbo facts. It is
not duplicated or included as stock Turbo training data.

The training-ready derivative is maintained separately in
[`training/993-turbo-20261002`](../../../training/993-turbo-20261002/).

The report, public French exports and publication record are in
[`docs/research/993-turbo-20261002`](../../../docs/research/993-turbo-20261002/).
