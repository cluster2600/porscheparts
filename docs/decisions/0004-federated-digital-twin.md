# ADR 0004 — Digital twin federated by functional zones

## Status

Accepted on August 29, 2026.

## Context

The project must test parts numerically in their environment before printing. A
complete mesh of the car, however visually convincing, provides neither the
interfaces, nor the clearances, nor the uncertainty needed for a fit check.

## Decision

The 993 twin will be a federation of functional sub-twins. Each zone contains
the candidate part, the host geometry, the relevant neighboring parts and
computable acceptance rules.

The fidelity levels are cumulative:

| Level | Content | Authorized use |
|---|---|---|
| `F0_reference` | visual shape, incomplete scale or provenance | orientation only |
| `F1_envelope` | scaled envelope and documented reference frame | rough packaging |
| `F2_interface` | measured interfaces, tolerances and uncertainties | fit, clearance, collision |
| `F3_engineering` | materials, contacts, loads and boundary conditions | exploratory FEA/CFD |
| `F4_correlated` | results correlated with physical measurements or tests | documented decision within the validated domain |

The global vehicle frame follows the project convention: origin on the plane of
symmetry, vertically below the front axle center on the nominal ground plane;
`X` forward, `Y` to the left and `Z` up. A sub-twin may have a local frame, but
its transform to the vehicle frame must be documented before integration into
the global twin.

The master dimensional geometry stays in open, revisable solid CAD:
build123d/CadQuery scripts, FreeCAD and STEP. FreeCAD Assembly is used to review
constraints and motion. An OpenUSD scene may federate the zones for navigation
and variants; it is never the source of dimensions.

Every test uses a worst-case margin that includes measurement uncertainties. A
sub-twin cannot reach `digitally_checked` if a required interface is missing or
if the accuracy of its geometry is unknown.

## Consequences

- The first target is the switch blank housing in the dashboard.
- The complete vehicle is built progressively from the useful zones.
- A public scan without scale can dress the scene at level `F0`, never qualify a
  part.
- Neural Concept remains a later FEA/CFD surrogate-model layer; it first needs a
  corpus of consistent geometries, parameters and results.
