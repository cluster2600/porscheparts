# Two improved fan programmes: 993 and 935 architecture

Scope confirmed on 3 October 2026: two distinct projects, both targeting lower
mass and more useful air delivered to the engine. PicoGK builds editable
geometry; calculations and measurements establish characteristics and supply
the digital twins.

| Programme | Retained architecture | Objective and dossier |
|---|---|---|
| `FAN-993-VERTICAL` | Rotor in a vertical plane; horizontal axis in engine coordinates | Improve the 993 fan and its operation in the engine circuit: mass, blades, useful flow and distribution. [Existing programme](../twins/993-engine-cooling-fan-system-f0/README.md) |
| `FAN-935-HORIZONTAL` | Rotor flat above the engine; vertical axis in engine coordinates | Recreate rotor, support, drive, housing and guides of the 935 architecture, then improve them using current materials, processes and geometry. [System research](research/935-horizontal-cooling/README.en.md) |

The existing 993 programme studies an assumed Turbo M64.60 reference. Exact
variant and interfaces still require qualification before a functional part.
For the horizontal programme, the reference 935 specimen and recipient engine
for the improved version must be explicit in the installation contract. The
final target does not follow from the “935” name alone.

## Reference and improved versions

Each programme has a characterized reference, then `improved-*` variants with
their own geometry, materials, interfaces and results. The reference measures
gains. A redesigned internal region has redesign status; it is not claimed as
copied from the external scan.

Both programmes can share tools, calculation methods and tests. Their
parameters, assemblies and simulated fields retain their identity. Scans
described by the owner as 935 parts supply the horizontal programme; their
earlier M64 classification does not demonstrate 993 compatibility.

## Measuring gains

Compare rotor mass, rotating inertia and complete assembly mass separately,
including materials and standard components. A lighter rotor can change
transients without reducing complete system mass as much.

Compare reference and variant at consistent rotor speed, air density, circuit
and backpressure. Publish flow, pressure, torque, power and distribution among
engine regions. A second comparison at common power budget evaluates the cost
of increased flow. Drive ratio links engine and rotor speed.

The objective concerns air reaching cooling passages and corresponding
temperatures when thermal loads are known. Measurements and calculations must
resolve gains beyond their uncertainties. No gain percentage is fixed before
the measured reference.

The owner selected three material families for additive manufacturing of
improved versions: aluminium, magnesium and titanium. The
[material and process dossier](research/935-horizontal-cooling/ADDITIVE_MATERIALS.en.md)
documents AlSi10Mg, WE43 and Ti64 as initial candidates. Selection is specific
to each part and does not follow from historical material.

The [alloy comparison report](../twins/fan-alloy-comparison-f0/README.en.md)
presents mass, inertia and centrifugal calculations on the parametric 993
rotor and PicoGK volumetric reconstruction attempts on the 935 scan.

| Improvement variable | Effect to study | Constraints to verify |
|---|---|---|
| Blade sections, chord, camber, twist and tips | Flow, pressure, efficiency, recirculation and noise | Roots, thicknesses, centrifugal loading, clearance and manufacture |
| Blade, hub and support structure | Mass, inertia and stiffness | Deformation, modes, fatigue, temperatures and balance |
| Current material and process | Mass and attainable properties | Material condition, defects, treatments, inspection and interfaces |
| Housing, inlet and guides | Losses and engine distribution | Envelope, sealing and maintenance access |
| Horizontal system transmission and bearings | Losses, mass and transmitted torque | Teeth, shafts, life, lubrication and heat |

Variants seek a measurable compromise among mass, useful air and consumed
power under mechanical and thermal constraints. Removing material or raising
speed alone does not demonstrate improved cooling.

## Work order

1. Establish identities, units, coordinates and interface contracts for both projects.
2. Build their editable references, including the complete horizontal assembly.
3. Characterize references: geometry, mass/inertia, drive, installed aerodynamics,
   structure, vibration and available thermal information.
4. Generate controlled variants and compare gains under defined conditions.
5. Compare selected variants to tests and build two twins linked to the correct
   geometry, conditions and measurements.

The [horizontal plan](research/935-horizontal-cooling/RECONSTRUCTION_PLAN.en.md)
details system reconstruction and optimization. The
[993 validation plan](../twins/993-engine-cooling-fan-system-f0/program/VALIDATION_PLAN.md)
still applies to that programme's missing evidence. At this date, audits and
exploratory studies demonstrate no validated performance gain.
