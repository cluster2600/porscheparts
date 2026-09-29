# M64/60 Engine BOM — Coverage Summary (Wave 1)

Companion to [`m64-bom-v1.json`](m64-bom-v1.json) — master bill of materials for
the Porsche 993 Turbo M64/60 3.6 L twin-turbo digital twin
(`M64-WHOLE-ENGINE-TWIN-0001`). Generated 2026-09-28 by the Wave-1 research
task. Everything below is honest evidence accounting: **no part is measured by
this project**; "sourced" means declared by a citable local record, and
official workshop-manual torques are classed `measured_source` (factory spec,
never a fidelity promotion).

## Totals

| Metric | Value |
|---|---|
| Part line items | 57 (≈177 units at nominal quantities) |
| Subsystems | 18, all mapped to program zones (`twins/m64-engine-system/program.json`) |
| Lines with a Porsche part number | 16 / 57 (28 %) |
| Lines with identity evidence (sourced) | 28 / 57 (49 %) |
| Lines with sourced primary dimensions | 20 / 57 (35 %); 110 / 177 units (62 %, boosted by valve/hose/fastener multiples) |
| Lines with zero local source at all | 5 (see gaps) |
| Verified fidelity | **F0_reference everywhere** — per program cross-zone rule, nothing exceeds F1_envelope before the common engine metrology frame exists |

## Per-subsystem coverage

| Subsystem | Lines | % with sourced dims | Notes |
|---|--:|--:|---|
| turbos (K16 pair) | 3 | 100 % | Best-evidenced zone: PET identity, 4 PN suffixes, vendor envelopes, wheel/A/R data; compressor map still missing (M64-ACQ-0003) |
| charge_air (intercoolers/plumbing) | 5 | 80 % | OE numbers come from aftermarket cross-refs (level C); needs PET line confirmation |
| fasteners_gaskets | 3 | 66 % | Head studs 12×M8×22 and O-ring 102×2 are FACT_public; gasket thickness unknown |
| valvetrain | 7 | 57 % | Valves F1-proxied with declared dims; spring installed lengths forum-declared; cam profile absent (M64-ACQ-0002) |
| cylinders / pistons | 1 / 1 | 100 % (bore only) | Bore/stroke FACT_public; pitch, deck height, crown, skirt interface all missing (M64-ACQ-0004) |
| intake | 2 | 50 % | Only an aftermarket funnel set; OEM tract unrecorded |
| conrods | 2 | 50 % | Strong PAUTER aftermarket datum; **OEM rod dims absent** |
| cooling fan + ducting | 6 | 33 % | Airflow 1010 l/s @ ~6100 rpm published; wheel geometry unresolved (M64-ACQ-0005) |
| heads | 1 | 0 % | Scan proxy is a 935 head; 3 scale dims blocking (M64-ACQ-0001) |
| crankcase / crankshaft | 3 / 1 | 0 % | Torques only; skeleton blocked on pitch/deck height |
| exhaust_manifolds | 3 | 0 % | PET group 107-20 nomenclature exists (65 lines) but was never transcribed line-by-line |
| oil | 4 | 0 % | Topology contract F1 exists; no geometry, no line diameters |
| mounts | 3 | 0 % | PET-verified identity (carrier 993 115 021 53); no geometry |
| flywheel / clutch | 2 / 2 | 0 % | Torques + Luk DMF identity only |
| sensors | 8 | 12 % | MAF and CAT sensor identified; the rest are torque-registered mounts |

## Top missing-evidence items (blocking value)

1. **Cylinder pitch, deck height, case interface** — blocks F2 for the whole
   short block and the engine coordinate frame (M64-ACQ-0004).
2. **PET 107-20 line-level transcription** — cheapest identity win available:
   official numbers for manifolds, wastegate hardware and charge-air plumbing
   already exist in the audited-but-untranscribed group
   (`docs/PORSCHEFANATICS_993_TURBO_AUDIT.md`).
3. **OEM conrod geometry** — only the PAUTER aftermarket datum exists.
4. **Fan wheel geometry + pulley diameters** — the flagship study has published
   airflow but no confirmed wheel (M64-ACQ-0005; scan analysis inconclusive).
5. **Cam profile + valvetrain masses** (M64-ACQ-0002).
6. **K16 compressor map** (M64-ACQ-0003) — gates calibrated CFD/1-D for zone TR.
7. **Oil system geometry** — tank, lines, cooler: zero dimensional evidence.
8. **Dry mass conflict** 232 kg vs 268 kg and **compression ratio conflict**
   9.5:1 vs 8.0:1 recorded in `m64-bom-v1.json.known_conflicts` — unresolved,
   left null at assembly level.
9. Five lines with **no local source at all**: intermediate-shaft drive,
   throttle body (OBJ lead untriaged), oil cooler, clutch disc/release bearing,
   wiring harness.

## Recommended geometry wave order (derived from evidence strength)

1. **Wave A — valvetrain & valves (F1→F2 candidates).** Valves have part
   numbers, declared head/stem/mass, installed spring lengths, an F1 build
   pipeline (`build_valve_variants.py`) and Omniverse assets already wired.
   Cheapest route to a defensible F2 component.
2. **Wave B — turbo cold side & charge-air plumbing (F1).** Identity is
   4-reference cross-checked; vendor envelopes exist for intercoolers, hoses,
   duct, heat shield; the cold-side prototype and CFD baseline
   (`simulation/993-k16-cold-side-baseline`) are in place. Close the OE
   intercooler-number check against PET first.
3. **Wave C — exhaust manifold nomenclature → envelope.** Transcribe PET
   107-20/107-45 (a documentation task, no hardware), then build envelopes from
   the Fabspeed scan lead. Unblocks zone EX.
4. **Wave D — short-block skeleton.** Requires M64-ACQ-0004 (pitch/deck
   height). Until then keep the F1 layout beams (`twins/m64-engine-system/picogk`).
5. **Wave E — cooling fan wheel.** Blocked on blade-count confirmation
   (M64-ACQ-0005); the fan is the project's headline study but currently the
   weakest geometry evidence relative to its ambition. Do the scan study first.
6. **Last: oil system, flywheel/clutch, harness** — acquire before modelling.

## Redesign-interest (3D-print candidate) flags

- **High**: conrods (aftermarket datum exists), pistons, intake funnels, valve
  covers, heat shield, intercooler hoses/duct/bracket, fan wheel, insulation
  covers.
- **Med**: cylinders, turbos (shroud/duct work), clutch Tiptronic drive plate,
  chain housing, throttle body, CAT sensor boss, intercooler, oil tank, engine
  bracket.
- **Low**: case, crank, mounts, fasteners — replace only on evidence.

## Validation performed

- `m64-bom-v1.json` parses (`python3 -m json.tool`).
- The BOM is a new document class (registry), not a catalogue part record, so
  `schemas/part.schema.json` does not apply; no file under `catalog/parts/` or
  `catalog/sources/` was modified, and `make check` (catalogue/source/
  measurement/twin validators + turbo checks) was run to confirm the tree
  stays green.
- Every `sources` entry is an exact local path inside the repository or the
  read-only `porschefanatics.com` data directory.
