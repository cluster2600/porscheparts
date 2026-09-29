# Engine scene v1 status — zone coverage

Scene: `usd/993-engine-assembly-v1.usda` · Manifest: `assembly-engine-v1.json`
(`M64-ENGINE-SCENE-V1`) · BOM source (read-only):
`twins/m64-engine-system/bom/m64-bom-v1.json`

Status: **research layout, not fitment.** All positions are engine-local layout
hypotheses on the documented coordinate frame. No interface, clearance or
collision is asserted.

Coverage classes: **real** = reference to an existing USD asset in
`twins/catalogue-parts/usd/`; **proxy** = box sized from BOM-sourced envelope
dimensions; **env-unknown** = envelope-unknown marker with an arbitrary size so
the zone stays visually present without overclaiming.

| Zone | Label | Real | Proxy | Env-unknown | Prims | BOM lines represented |
|---|---|---:|---:|---:|---:|---|
| M64-Z-CC | crankcase, cylinders, front covers, fasteners | 0 | 2 | 3 | 5 | CC-001, CC-004, FG-001, FG-002, FG-003 |
| M64-Z-HD | cylinder heads | 0 | 0 | 2 | 2 | HD-001 |
| M64-Z-VT | camshafts, rockers, valves, springs, covers, timing drive | 0 | 0 | 8 | 8 | VT-001 … VT-007 |
| M64-Z-TR | K16 turbochargers and thermal shields | 3 | 0 | 0 | 3 | TR-001, TR-002, TR-004 |
| M64-Z-CL | cooling fan, drive, ducting, thermal screens | 0 | 1 | 5 | 6 | AS-002, CL-001 … CL-005 |
| M64-Z-OL | dry-sump lubrication | 0 | 1 | 3 | 4 | CC-002, CC-003, OL-001, OL-002 |
| M64-Z-EX | heat exchangers, wastegates, pre-cat sections | 0 | 0 | 6 | 6 | IN-003, IN-004, TR-003 |
| M64-Z-CA | intake tract, intercoolers, charge-air plumbing | 6 | 1 | 1 | 8 | IC-001 … IC-005, IN-001, IN-002 |
| M64-Z-CC-ROT | crankshaft, rods, pistons | 0 | 2 | 2 | 4 | CR-001, CR-002, CS-001, PS-001 |
| M64-Z-ASM | engine carrier, brackets, mounts | 1 | 0 | 2 | 3 | MT-001, MT-002, MT-003 |
| M64-Z-FW | flywheel, drive plate, clutch | 0 | 0 | 4 | 4 | CT-001, CT-002, FW-001, FW-002 |
| M64-Z-SN | engine sensors, ignition, harness | 1 | 0 | 7 | 8 | AS-001, SN-001 … SN-007 |
| **Total (12 zones)** | | **11** | **7** | **43** | **61** | **55 / 57 BOM lines** |

BOM ids abbreviated: `M64B-` prefix omitted in the line lists.

## Declared unrepresented BOM lines (2)

| BOM line | Reason (from manifest `bom_coverage.unrepresentation_reasons`) |
|---|---|
| M64B-CS-002 | Intermediate shaft gear / balance drive: no local evidence record (all evidence fields missing, BOM sources list empty); declared here instead of adding a zero-evidence prim. |
| M64B-CY-001 | Cylinder barrels represented inside the Crankcase zone by the CrankcaseHalvesMarker (CC-001): bore 100 is sourced but the skirt/case interface and fin pitch are unknown (M64-ACQ-0004), so a separate marker would imply a nonexistent datum. |

## Real asset references (11 prims, 10 distinct assets)

`993-turbocharger-k16-left.usda`, `993-turbocharger-k16-right.usda`,
`993-turbo-heat-shield-cover-left.usda`, `993-intercooler-replacement-aks.usda`
(×2 prims), `993-intercooler-pressure-hose-left.usda`,
`993-intercooler-pressure-hose-right.usda`, `993-intercooler-air-duct.usda`,
`993-intercooler-bracket-reinforced.usda`, `993-engine-carrier-turbo.usda`,
`993-intercooler-temperature-sensor.usda` — all under
`twins/catalogue-parts/usd/`. Note: each referenced asset is itself an F0/F1
documentary proxy mesh, not measured component geometry.

## Validation status (2026-09-29)

| Check | Command | Result |
|---|---|---|
| Manifest JSON well-formed | `python3 -m json.tool assembly-engine-v1.json` | passed |
| Manifest contract + scene structure + evidence attrs + reference arcs | `source/validate_engine_scene.py --report …` | passed (9/9 checks) |
| Catalogue validator | `python3 scripts/validate_catalog.py` | passed (34 records) |
| Deterministic rebuild | rerun builder over committed scene | byte-identical |

`source/validate_usd_assemblies.py` (pxr) additionally reruns the structure and
evidence checks as `engine_v1_*` when the pipeline image executes it; it was
not runnable at authoring time (pxr not installed on the authoring host), so
the stdlib validator above is the authoritative structural gate for v1.
