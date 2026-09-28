# M64-Z-OL Oil Topology USD Harness — F1 Readiness Note

Status: `F1_placeholder_line_and_fitting_harness_not_part_geometry_or_SimReady`
Lane: M64-Z-OL (turbo lubrication / oil circuit), geometry-fidelity step from
the F1 topology-only artifacts toward the Omniverse assembly.

## What exists today (inputs, read-only)

Three F1 topology readiness contracts and their non-spatial USDA guides were
parsed and merged; none contains measured geometry:

| Circuit | Contract | Nodes | Edges | Known interface coords |
|---|---|---|---|---|
| Turbo lubrication control (PET 202-16) | `twins/catalogue-parts/turbo-lubrication-control-topology-readiness-f1.json` | 11 | 13 | 0 |
| Oil cooler circuit (PET 104-05) | `twins/catalogue-parts/oil-cooler-circuit-topology-readiness-f1.json` | 12 | 13 | 0 |
| Oil tank circuit (PET 104-01) | `twins/catalogue-parts/oil-tank-circuit-topology-readiness-f1.json` | 11 | 10 | 0 |

Node families covered: oil pump/source boundary, oil cooler core + cooling
air path, turbo K16 bearing-system feeds and drains, oil collection
containers, returns, vents, tank/storage boundaries, control box / wastegate
couplings. Every edge is a declared **hypothesis** (semantics ending in
`_hypothesis`); **no edge is a routed, dimensioned line**. All 36 turbo-circuit
engineering parameters (line lengths, IDs, roughness, fitting K-values, port
coordinates, materials, BCs) are
`unknown_source_or_measurement_required`; `known_interface_coordinates = 0`
in all three contracts.

## New artifact

`twins/catalogue-parts/engineering/993-oil-circuit-topology-harness-f1.usda`
(generated deterministically by
`scripts/generate_pet_993_oil_topology_usd_harness.py`, validated by
`scripts/validate_pet_993_oil_topology_usd_harness.py`).

- 86 prims: 34 node spheres + 36 in-circuit edge line-meshes + 5 cross-circuit
  `UnknownLink` line-meshes + scopes/metadata.
- Each circuit sits in a separate z-band (0 / 10 / 20 diagram units).
  Coordinates are **diagram bands, not vehicle positions**.
- Single placeholder radius configuration, explicitly tagged:
  root attributes `placeholderRadiusM = 0.08`,
  `placeholderTubeRadiusM = 0.0125`, `radiusTag =
  "placeholder_single_config_value_not_measurement"`, and every primitive
  carries `geometryState = "placeholder_not_measurement"`.
  These are **not measurements and not candidate diameters**.
- Edge `Mesh` prims store centerline `points` plus the placeholder radius as
  data; downstream consumers must sweep/tube them (Omniverse can render the
  centerlines with display color: orange=oil, blue=air/vent,
  green=control/electrical, grey=other, red=unknown cross-links).
- Source SHA-256 of each input USDA is recorded in the stage
  (`sourceSha256ByCircuit`) and per-circuit scopes.

### Validation evidence

- USD tooling: none preinstalled on host; used `usd-core` **26.8** (pxr) in a
  throwaway Python venv (Python 3.14.7). `usdcat` binary not present.
- `validate_pet_993_oil_topology_usd_harness.py` →
  `PASS: harness loads (pxr), 86 prims, all radii are the single placeholder
  config value, all cross-links tagged unknown` (exit 0).
- Deterministic regeneration confirmed: three successive generations produce
  byte-identical files,
  sha256 `7611975a6e4d8ee48b20eeefe35d26da6879bb2aa891f014bf65d4e799c90247`.
- Inputs verified untouched: turbo guide sha256 matches the value recorded in
  its own F1 contract
  (`d8b6e579c2806e58812c8e8cbe062ce0cc505bafe075604004d1c4d08bebd75b`).

## Open data needed to upgrade to a printable-manifold-candidate harness

1. **Line internal diameters and wall thicknesses** per line (TLC-GEO-002/009;
   PET refs 993 107 125/126/338/339 53 oil pipes, 993 107 311/312 vent lines,
   993 207 133/135 cooler pipes) — measured or OEM drawing. Until then no
   tube radius on this harness may be quoted.
2. **Routed 3D centerlines**: routing photos with scale references or a
   3D scan of the engine bay lines, registered to a vehicle reference frame
   (replaces diagram-band coordinates; TLC-GEO-001/006/010).
3. **Port/fitting definitions** (TLC-GEO-008, TLC-GEO-004): thread specs and
   coordinates at pump, cooler, tank, collectors, K16 bearing housings;
   fitting types and minor-loss K-values from PET refs (clamps 999 511 116
   02/03, unions 999 136 045 09, seals 965/944 111 205, O-rings 999 701
   xxx 40).
4. **Left/right and configuration resolution** per F1 `next_gate`
   (`resolve_202_16_configuration_topology_side_assignment_and_F2_interfaces`)
   — the 5 red `UnknownCrossLinks` tubes become real routed segments only
   after this.
5. **Collector internal volumes and heights** (TLC-GEO-005/006) for the drain
   side of any printable manifold.
6. Fluid/BC data (oil grade, viscosity vs T, supply/return pressures, per-turbo
   mass flow) — needed for the simulation lane, not for the manifold itself.

Gate: only after items 1–4 with provenance, plus F3 material/temperature/
pressure screening and professional review, may this placeholder harness be
replaced by a dimensioned manifold candidate for printing (per the F1
prototype disposition: nonfunctional fit/routing mockups first).

## Claim boundary

The harness is a placeholder line-and-fitting *guide* for Omniverse
visualization and handoff structure. It is not OEM geometry, not F2/F3
analysis geometry, not vehicle-positioned, and nothing here has been
presented or should be read as a measured diameter.
