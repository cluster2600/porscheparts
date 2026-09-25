# Roadmap

## Phase 0 — Foundation

Status: **completed on August 28, 2026** (`v0.1.0`).

Goal: make the project open to contributions before adding a part.

- [x] Charter and safety limits
- [x] Free and open toolchain
- [x] Part record schema
- [x] Measurement and titanium manufacturing templates
- [x] Automatic catalog validation
- [x] GitHub contribution templates

Exit criterion: `make check` passes on a clean repository.

## Phase 1 — Source inventory

Detailed log: [docs/PHASE1_SOURCE_INVENTORY.md](docs/PHASE1_SOURCE_INVENTORY.md).

Additional research: [German-language batch of twenty candidates](docs/research/phase-1-recherche-allemande.md).

- [x] Survey official catalogs, legally accessible manuals and measurements
- [x] Survey 3D models with a verifiable license
- [x] Classify references by variant, year and availability
- [x] Identify missing or hard-to-obtain parts
- [x] Assess each source: provenance, license, accuracy, reuse

Exit criterion: twenty documented candidates, without importing unauthorized
content. Progress: 294 valid source records in `catalog/sources/`; acquiring
direct measurements remains to be done.

## Phase 2 — Physical inventory and twin assembly

Architecture: [docs/DIGITAL_TWIN.md](docs/DIGITAL_TWIN.md).

Active mode: **no printing**. The twin is fed by components whose size,
material, mass and application are all sourced. Mounting relationships are
recorded separately from spatial transforms.

- [x] Define fidelity levels `F0` to `F4`
- [x] Create the registry, schema and validations for sub-twins
- [x] Create the physical component and assembly registries
- [x] Admit the first size + material + mass batch: 17-inch Fuchs wheels
- [x] Logically assemble the documented front and rear pairs
- [x] Add the 18-inch Fuchs wheels and their 5x130 / 71.5 mm interface
- [x] Complete the 17-inch Fuchs wheel interface from the KBA type approvals
- [x] Document the block on Michelin PS2 N3 tires for lack of consistent manufacturer material and mass
- [x] Qualify the Carrera Brembo/ATE discs and document their block for lack of net mass and full grade
- [x] Research community CAD/3D work and qualify the windshield templates, the seat ring and a full scan
- [ ] Extend the inventory by subassembly family
- [ ] Complete the interfaces needed for spatial positioning
- [ ] Generate STEP/FreeCAD assemblies once the transforms are known
- [ ] Compute mass and center of gravity of positioned assemblies

Exit criterion: a first multi-component subassembly positioned in the vehicle
reference frame, with sourced mass, material, interfaces, uncertainties and
relationships for each component.

### Physical prototypes — suspended

Three non-critical parts selected, records created at status `concept`:

| Category | Part | Record |
|---|---|---|
| Simple geometry, caliper | Switch blank cover | `993-INT-SWITCH-BLANK-0001` |
| Organic, photogrammetry | Door pull handle | `993-INT-DOOR-PULL-0001` |
| Symmetric or missing | Seat rail cover | `993-INT-SEAT-RAIL-COVER-0001` |

- [x] Select three non-critical parts
- [x] Write a measurement plan per part
- [x] Write the measurement-driven master geometry (part 1)
- [ ] Resume only after an explicit decision to leave digital-only mode

The existing plans are kept as a backlog; they no longer drive the active phase
and no manufacturing file is generated.

Execution plan and handover dossier:
[docs/MEASUREMENT_CAMPAIGN.md](docs/MEASUREMENT_CAMPAIGN.md).

Preparation specifications from the manual and from Porsche Fanatics are mapped
in [docs/993/993_MANUAL_DATA_MAP.md](docs/993/993_MANUAL_DATA_MAP.md).
The exhaustive page-by-page register is in
[`catalog/manual/993-workshop-manual-measurements.json`](catalog/manual/993-workshop-manual-measurements.json).

Exit criterion: three prototypes fitted, photographed and measured.
**Conditional on a contributor who has the parts**: see the operating constraint
in [docs/PROJECT_CHARTER.md](docs/PROJECT_CHARTER.md).

### Body track opened in parallel

`993-BODY-FRONT-LID-0001`, composite front lid. Chosen as the first body pilot
because it combines four advantages: a **bolted-on** panel, with no structural
function or anti-intrusion beam; a **single, gently curved surface**, hence the
simplest mold on the car; an **original steel panel**, hence a real gain, with a
benchmark already set by Porsche Motorsport at 8 kg in aluminum; and an
**inexpensive used donor panel** to take the mold from, unlike rare mechanical
parts.

Original masses established by a German comparison table
(`SRC-FEDERLEICHTE-ELFER-993-WEIGHTS`), which finally makes it possible to put
numbers on the program instead of estimating it:

| Part | Original | Carbon | Gain |
|---|---:|---:|---:|
| Front lid | 14.0 kg | 4.1 kg | **9.9 kg** |
| Front fenders, pair | 14.4 kg | 4.4 kg | 10.0 kg |
| Rear spoiler | 12.5 kg | 4.8 kg | 7.7 kg |
| Rear bumper | 5.05 kg | 3.1 kg | 2.0 kg |
| Mirrors, pair | 1.8 kg | 0.25 kg | 1.6 kg |
| Rear light panel | 1.26 kg | 0.26 kg | 1.0 kg |
| **Total** | **49.0 kg** | **16.9 kg** | **32.1 kg** |

Thirty-two kilos without touching a single structural part or removing a single
safety element — against 0.45 kg for the titanium engine carrier.

Two lines of that table are deliberately left out. The **doors**, 32.0 kg against
5.9 kg, show the largest gain in the table, but the lightweight version is a
race door: the gain comes from removing the anti-intrusion beams, the window
regulator and the glazing, not from the material. The **roof**, 22.0 kg against
2.5 kg, is a welded structural panel. Neither is an equivalent replacement.

The historical plans require physical access to the vehicle and the parts. No
dimension is estimated in the meantime: `parts/993-int-switch-blank-0001/source/switch_blank.py`
refuses to build until the seven dimensions it requires are measured.

## Phase 3 — Titanium engineering twin, no manufacturing

Candidate under study: **engine carrier `993-ENG-CARRIER-0001`** (993 115 021 53).
Presumed critical in the sense of `SAFETY.md`. The benefit of titanium is not a
given: at identical geometry, the part would be roughly twice as flexible as in
steel. Load cases and process comparison to be filled in
`parts/993-eng-carrier-0001/evidence/load-cases.md` before any geometry.

- [ ] Choose a part where Ti-6Al-4V brings a real benefit
- [ ] Compare LPBF, CNC, sheet metal and casting
- [ ] Define loads, interfaces, environment and service life
- [ ] Perform FEA and a manufacturability review with a supplier
- [ ] Integrate geometry, loads and results at the `F3_engineering` level
- [ ] Correlate at least one calculation case with a physical test
- [ ] Build the virtual titanium component with documented material and process
- [ ] Numerically compare the steel, aluminum and Ti-6Al-4V variants

Exit criterion: a digital material, mass, stiffness, fatigue and
manufacturability report available. All manufacturing remains outside the active
phase.

## Cross-cutting goal — digital twin coverage

Twin progress is measured as the share of curb weight described by documented,
sourced parts, via `make twin`.

| Milestone | Coverage | State |
|---|---:|---|
| First survey | 30.5% | reached on August 28, 2026, 417.5 kg of 1,370 kg |
| Complete body and trim | ~45% | in progress |
| Detailed powertrain | ~60% | overall engine known, parts to be detailed |
| Running gear and brakes | ~75% | not started |
| Remainder | 100% | not started |

### Assembly skeleton — done

The factory parts catalog provided the framework: ten systems, 239 illustrations,
12,864 located references (`catalog/reference/993-assembly-skeleton.json`).

| System | References | Illustrations |
|---|---:|---:|
| 8xx Body and trim | 4,553 | 85 |
| 1xx Engine | 2,398 | 34 |
| 9xx Electrical and equipment | 1,499 | 29 |
| 3xx Transmission | 1,368 | 34 |
| 6xx Brakes and hydraulics | 820 | 13 |
| 4xx Steering and front axle | 624 | 14 |
| 2xx Fuel and exhaust | 611 | 11 |
| 7xx Controls and clutch | 494 | 8 |
| 5xx Rear axle and drivetrain | 326 | 7 |
| 0xx Consumables | 171 | 4 |

Two coverages coexist, and they do not say the same thing: **0.18% of
references** carry a documented mass, but those few parts account for **30.5%
of curb weight**. The twin fills up by mass before it fills up by count.

### Position — started with a reference envelope

A mass without a position gives no center of gravity, no distribution and no
inertia. A first 3D envelope and datum cage, based on seven dimensions from the
Porsche manual, is available in
[`twins/993-reference-envelope/`](twins/993-reference-envelope/). It serves as a visual datum for the US profile, but does
not reconstruct the body and does not yet position the parts.

The next step is to replace this cage with a licensed body-shell geometry or
with a scaled survey, then tie the anchor points and subassemblies to
verifiable measurements.

## Phase 4 — Public catalog

- [ ] Publish only the parts that have cleared their quality gates
- [ ] Generate catalog pages from the JSON records
- [ ] Add views, dimensioned drawings and manufacturing instructions
- [ ] Track versions, tested vehicles and field feedback

## Initially out of scope

- Selling parts
- Road homologation
- **Replacing the load-bearing structure**, in particular with a composite
  monocoque. The body shell carries the chassis number, occupant protection and
  crash absorption; a monocoque is designed as such and cannot be translated
  from a sheet-steel body shell; its validation requires physical crash tests.

  A necessary clarification: such a monocoque **exists commercially** for the
  964 and 993 (`SRC-ZESAD-CARBON-MONOCOQUE-964-993`), from €129,990 to
  €219,990. It is therefore not excluded from scope because it would be
  impossible, but because this repository can neither document, verify nor
  reproduce it: the product page publishes no mass, no torsional stiffness, no
  crash test and no homologation. A safety structure with no published
  structural data is exactly what `docs/QUALITY_GATES.md` prohibits entering in
  the catalog.

  Body panels, on the other hand, remain a legitimate goal: see
  `SRC-GUNTHER-WERKS-CARBON-993`, where the most advanced 993 restomod on the
  market clothes the car in carbon while keeping and reinforcing the steel body
  shell.
- Hosting protected manuals or scans
- Publishing unqualified critical parts
- Buying or operating an LPBF machine
- AI surrogate model before a coherent FEA/CFD corpus exists
