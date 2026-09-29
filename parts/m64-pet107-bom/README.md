# PET107 print / buy / manufacture BOM (lane candidate, v1)

`PET107-BOM-V1` — the print-buy-manufacture view of the master engine BOM,
restricted to parts that the PET107 wave-2 lane judges printable in a
polymer FDM/FFF (PETG-PET-class) route or buyable as catalog consumables.

**Status of every line:** candidate only. Nothing here is fitted, tested,
safe, released, or manufacturing-ready — no line has metrology or physical
validation. All master-BOM fidelity is `F0_reference` (see
`twins/m64-engine-system/program.json` cross-zone rules).

## Files

| File | Role |
|---|---|
| `pet107-bom-v1.json` | Generated BOM (authoritative output, 14 lines) |
| `pet107-bom-v1.csv` | Generated editable CSV mirror, same 15 columns |
| `selection-pet107.json` | Hand-edited lane selection record (the editable input) |
| `selfcheck_pet107_bom.py` | JSON-schema + CSV + evidence-rule self-check |
| `../../scripts/generate_pet107_bom.py` | Deterministic generator (stdlib only) |

## Regenerate

```sh
python3 scripts/generate_pet107_bom.py                 # rc=0
python3 parts/m64-pet107-bom/selfcheck_pet107_bom.py   # rc=0
```

The generator joins `selection-pet107.json` onto
`twins/m64-engine-system/bom/m64-bom-v1.json` by `bom_id_local`, inherits
name/part number/subsystem/quantity/source citations from the master BOM,
derives the evidence level, and emits JSON+CSV in selection-file order.
Output is deterministic: reruns on unchanged inputs reproduce the files
byte-for-byte.

## Selection rules (how a master-BOM part earns a PET107 line)

1. **Print path** — the part must be non-structural, out of the oil-wet and
   hot zones (or explicitly flagged process `UNKNOWN`), and either carry a
   master-BOM print-candidate note or belong to the classic polymer
   duct/cover family. The lane judgement itself is always recorded as an
   ASSUMPTION in `selection_basis`; it promotes nothing.
2. **Buy path** — the part is a commercial consumable with a purchasable
   identity (published size, part number, or fitment record).
3. **Exclusions** — hot-side parts (manifolds, cat section, turbine wheels,
   wastegate), oil-wet parts (tank, cooler, pump), structural/safety parts
   (carrier `993 115 021 53` is PET safetyLevel 7, mounts, clutch, flywheel,
   head studs), and assembled catalogue units (turbos, intercooler cores).
   Rationale per exclusion is in `selection-pet107.json` → `excluded_notes`.

## Evidence levels

Per line, `evidence_level` is derived mechanically from the master-BOM
evidence fields and citations (mapping rules in `selection-pet107.json`):

- `FACT_public` — published by Porsche (brochure / official parts guide).
- `measured_source` — official 993 Repair Manual torque values registered in
  `catalog/manual/993-workshop-manual-measurements.json`; factory-specified,
  not project-measured.
- `SINGLE_SOURCE` — one secondary source (includes vendor-declared data).
- `UNKNOWN` — no local evidence; kept only as study targets with caveats.
- `CROSSCHECKED` / `ASSUMPTION` are in the ladder but no line currently
  derives to them.

The ladder itself follows
`docs/research/m64-public-engine-data-2026-09-27.md`.

## Self-check rules (selfcheck_pet107_bom.py)

- R1 every `evidence_level` on the fixed ladder.
- R2 no blank fields: unevidenced values must say `UNKNOWN`.
- R3 every `status` is the fixed disclaimer; the words fitted/tested/safe/
  released/manufacturing-ready may only appear negated ("not ...").
- R4 decision/process coherence (print ⇒ FDM/FFF PETG-PET-class or UNKNOWN;
  buy ⇒ buy-catalog).
- R5 quantities are positive integers.
- R6 CSV and JSON mirror each other cell-for-cell; selection record and BOM
  cover the same part ids.

## Known gaps

- 10 of 14 lines are `SINGLE_SOURCE` or `UNKNOWN`: printed geometry does not
  exist yet for any line (no CAD, no scan triage of the intake OBJ lead).
- Part numbers UNKNOWN on 7 lines; PET group 107-20/107-45 per-line
  transcription (see `docs/PORSCHEFANATICS_993_TURBO_AUDIT.md` and the
  `pet_reference_gaps` note in the master BOM) is the cheapest closure path.
- Print process parameters (temperature, layer, infill, anneal) are UNKNOWN
  on every print line — no material coupon testing exists.
- Heat-adjacent candidates (heat shield, insulation covers) carry process
  `UNKNOWN`: PET-class behaviour near the turbo is unevidenced.
