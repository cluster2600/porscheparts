# M64 — G1, CadQuery parametric skeleton

September 14, 2026. Code: [`m64_head_skeleton.py`](../../twins/m64-cylinder-head/source/parametric/m64_head_skeleton.py),
parameters: [`parameters.json`](../../twins/m64-cylinder-head/source/parametric/parameters.json),
evidence: [`evidence/g1-parametric-20260914/`](../../twins/m64-cylinder-head/evidence/g1-parametric-20260914/manifest.json).

**This is neither a master geometry nor a manufacturing authorization**
(`master_geometry: false`, `manufacturing_authorized: false`).

![XZ section of the G1 parametric cylinder head skeleton at y = valve_y_offset](../../twins/m64-cylinder-head/evidence/g1-parametric-20260914/m64-head-skeleton-section-xz.svg)

*Generated XZ section of the skeleton; it shows the placeholder layout, not sourced M64 dimensions or a manufacturable head.*

## Contents

One cylinder. It contains the block, the spigot below the sealing plane and a
land relief. The chamber is a simplified volume. Added to these are four
seat counterbores and four inclined guide bores (2 intake, 2
exhaust), the central spark plug well, four stud holes and two
camshaft bearing bores. The reference frame is described in `parameters.json`.

## Provenance rule (fails closed)

- `sourced`: the parameter must cite a non-null `contract_path`, carried by an
  entry with a registered source and locator, with the same unit and an identical
  value. A path to `critical_interfaces` requires the status `found`.
- `unsourced`: this is a placeholder. It may cite no path, and it
  is rejected as soon as the contract sources the corresponding interface (`found`).
- Any other provenance, modified value or withdrawn source is rejected.

## Generation result

| Item | Value |
|---|---|
| Sourced parameters | 3: chamber Ø = 100 mm bore (P3, historical reference); valves 40 / 33 mm (S2, Swindon benchmark) |
| Unsourced parameters | **19**, listed in the manifest, including register, land, studs, valve axes and inclinations, guides, spark plug and camshafts |
| BRepCheck_Analyzer | valid |
| Volume | 1,074,651.8 mm³, **without physical meaning** (block dimensions unsourced) |
| Outputs | STEP (368 KB), SVG XZ section at y = `valve_y_offset`, manifest with SHA-256 (STEP, section, parameters, contract, generator) |

The STEP header contains a timestamp: the digest changes on every regeneration.
The manifest points to the committed copy.

The 14 mm diameter of the spark plug well remains **unsourced**. The M14 × 1.25 thread
is only a partial fact of the contract: 993 Carrera, table not re-read.

## Tests

`tests/test_m64_g1_parametric_skeleton.py` covers valid, non-master
generation, rejection of a modified sourced value, rejection of a source withdrawn from the
contract, rejection of a placeholder presented as sourced and consistency of the list
of unsourced parameters.

## Next steps

Replace the placeholders as the measurements from the
[G0 list](M64_G0_INTERFACE_CONTRACT_20260914.md) enter the contract. Registration
against the scan remains to be done when it becomes available.
