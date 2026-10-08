# Two improved cooling programs: 993 and 935 architecture

Scope confirmed on October 3, 2026: two separate projects, with mass reduction
and an increase in useful air delivered to the engine in both cases.
PicoGK builds the editable geometries; calculations and measurements
establish the characteristics and feed the digital twins.

| Program | Architecture kept | Objective and dossier |
|---|---|---|
| `FAN-993-VERTICAL` | Rotor in a vertical plane; horizontal axis in the engine reference frame | Improve the 993 fan and its operation in the engine circuit: mass, blades, useful flow and distribution. [Existing program](../twins/993-engine-cooling-fan-system-f0/README.md) |
| `FAN-935-HORIZONTAL` | Rotor lying flat above the engine; vertical axis in the engine reference frame | Recreate the rotor, support, drive, housing and guide assembly of the 935 architecture, then improve it with current materials, processes and geometries. [System research](research/935-horizontal-cooling/README.en.md) |

The existing 993 program studies a hypothetical Turbo M64.60 reference;
the exact variant and its interfaces remain to be qualified before any
functional part.

Order confirmed by the owner on October 6, 2026 for the horizontal
program: first reproduce the system and its mounting on a **935**,
then develop a horizontal version adapted to a **993 engine**.
The first step keeps the documented historical geometry, layout and
interfaces; the adaptation has its own mounts, transmission, housing and
air guides. The exact variants of the 935 donor and of the receiving
engines remain to be identified. The `FAN-993-VERTICAL` program
stays separate from this horizontal adaptation.

## Reference and improved versions

Each program has a characterized reference, then `improved-*` variants
with their own geometry, materials, interfaces and results.
The reference is used to measure the gains. A redesigned internal region has
a redesign status; it is not declared as copied from the external scan.

The two programs may share tools, calculation methods and tests.
Their parameters, assemblies and simulation fields stay tied to their
identity. The scans the owner announced as 935 parts feed the
horizontal program; their former M64 classification does not demonstrate
993 compatibility.

## Measuring the gains

Compare separately rotor mass, rotating inertia and assembly mass,
with the material balance and standard components included. A lighter rotor
can change the transients without reducing the mass of the complete system as much.

Compare reference and variant at consistent rotor speed, air density, circuit
and back-pressure. Publish flow, pressure, torque, power and
distribution between engine zones. A second comparison at a common power
budget makes it possible to assess the cost of the flow gain. The drive ratio
establishes the link between engine speed and rotor speed.

The objective concerns the air that reaches the cooling passages and
the corresponding temperatures when the thermal loads are known.
Measurements and calculations must resolve the gains beyond their
uncertainties. No gain percentage is set before the measured reference.

The owner selected three families for additive manufacturing of the
improved versions: aluminum, magnesium and titanium. The
[material and process dossier](research/935-horizontal-cooling/ADDITIVE_MATERIALS.en.md)
documents AlSi10Mg, WE43 and Ti64 as starting candidates. The choice is
specific to each part and does not follow from the historical material.

The [alloy comparison report](../twins/fan-alloy-comparison-f0/README.en.md)
presents the mass, inertia and centrifugal calculations on the parametric 993
rotor, as well as the PicoGK trials of volumetric reconstruction of the 935 scan.

| Improvement lever | Effect to study | Constraints to check |
|---|---|---|
| Blade sections, chord, camber, twist and tips | Flow, pressure, efficiency, recirculation and noise | Roots, thicknesses, centrifugal load, clearance and manufacturing |
| Structure of blades, hub and support | Mass, inertia and stiffness | Deformation, modes, fatigue, temperatures and balancing |
| Current material and process | Mass and achievable properties | Material condition, defects, treatments, inspection and interfaces |
| Housing, inlet and guides | Losses and distribution over the engine | Packaging, sealing and maintenance access |
| Transmission and bearings of the horizontal system | Losses, mass and transmitted torque | Gear teeth, shafts, service life, lubrication and heat |

The variants seek a measurable trade-off between mass, useful air and
power consumed, under the mechanical and thermal constraints. Removing
material or raising the speed does not by itself demonstrate improved
cooling.

## Work order

1. Establish identities, units, reference frames and interface contracts for both projects.
2. Build their editable references, including the complete horizontal assembly.
3. Characterize these references: geometry, mass/inertia, drive,
   installed aerodynamics, structure, vibration and available thermal data.
4. Generate controlled variants and compare the gains under defined conditions.
5. Test the selected variants against experiments and build two twins
   tied to the correct geometries, conditions and measurements.

The [horizontal plan](research/935-horizontal-cooling/RECONSTRUCTION_PLAN.en.md)
details the reconstruction and system optimization. The
[993 validation plan](../twins/993-engine-cooling-fan-system-f0/program/VALIDATION_PLAN.md)
remains applicable to the missing evidence of that program. As of this date, the
audits and exploratory studies demonstrate no validated performance gain.
