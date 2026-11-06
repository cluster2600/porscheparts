# Dashboard F0 interface and measurement contracts

Issue #567, revision 2026-11-06. Source of truth:
[interface-contracts.json](interface-contracts.json). Check it with
`python3 scripts/check_993_dashboard_interface_contracts.py --check`.

**Status: proposed, awaiting independent review.** Nothing in these contracts
is measured. Every value, uncertainty, tolerance, hole pattern, axis and
transform is `null`. They were written before any functional CAD. Nothing was
taken from the PicoGK F0 trim, its STL, the build123d concept or the 1/8-scale
model.

## What the contracts fix

For each of the 13 interfaces in [assembly.json](assembly.json), the contract
records:

- the part-side and host-side **measurands**: id, side, kind, allowed methods,
  at least three repetitions, and a link to the trim plan's D01–D14 where one
  exists;
- **attachments**: count, fastener identity, hole pattern and axes, all null
  until measured;
- **mating faces** and **motion or clearance** requirements;
- the **load paths** it belongs to (all four are covered) and the **images**
  required;
- **acceptance rules**, and a **tolerance** that only the independent
  interface reviewer may set;
- the **catalogue identity** per candidate variant, with PET plate, page and
  position.

| Interface | Safety | Part / host measurands | M564-LHD identity | RS identity (M002 / M003) |
|---|---|---|---|---|
| IF_BODY_PANEL_TO_SHELL | yes | 0 / 3 | group 502 only | not audited |
| IF_TRIM_TO_BODY_PANEL | no | 6 / 4 | unmapped | trim + plate fasteners, 809-02 |
| IF_HOOD_TO_TRIM | no | 2 / 2 | unmapped | not transcribed |
| IF_CLUSTER_TO_HOOD_PANEL | no | 2 / 2 | unmapped | not transcribed |
| IF_VENTS_TO_TRIM_DUCTS | no | 3 / 3 | unmapped | vents, defroster, foam strip |
| IF_GLOVEBOX_TO_HOST | yes | 1 / 4 | unmapped | M002 compartment, lock, striker |
| IF_CONSOLE_TO_DASH | no | 1 / 3 | unmapped | not transcribed |
| IF_CONTROLS_TO_PANEL | no | 1 / 2 | unmapped | not transcribed |
| IF_SWITCHES_TO_HOST | no | DT-01 / 2 | unmapped | not transcribed |
| IF_KNEE_STRIP_TO_ORIGINAL_MOUNTS | yes | 1 / 3 | unmapped | strips + plate fasteners |
| IF_COLUMN_CLEARANCE | yes | 1 / 2 | 403-07 heading | 403-07 heading |
| IF_AIRBAG_CONFIGURATION | yes | 0 / 3 | option-code definition | plate title |
| IF_PILLARS_AND_WINDSHIELD | no | 2 / 3 | unmapped | not transcribed |

The one catalogue identity the M564 target does get is the steering column.
Plate 403-07, page 266, lists outer tube `964 347 013 02` /LL and shaft
`964 347 051 00` /LL under a heading that names both CARRERA RS and M564.

## Rules that keep the contracts independent

- **Three evidence layers.** Catalogue identity is PET text, and it never
  supplies a dimension. Proposed measurements are the null measurands.
  Admitted physical evidence is empty today.
- **Vehicle frame from the body.** The origin and axes are defined only from
  the A-pillars, the windshield-base flange and the tunnel centreline. The
  trim plan's origin, at the central support, stays a part-local datum.
- **Host readings on the host.** A host reading is taken with the part removed.
  The `derived`, `model` and `assumed` methods are refused for host
  measurands, and so is any evidence path into the F0 concept or a mesh.
- **Specimen first.** Readings enter only for a specimen that
  `admit_specimen()` from #566 admits, through records that pass
  `validate_measurements.py`.
- **Uncertainty and contradictions.** Each reading carries a bounding
  half-width. Two readings of one measurand on one specimen whose intervals
  do not overlap block the interface, and `find_contradictions()` flags them.
  A proposed ratio of uncertainty to half the tolerance awaits the interface
  reviewer.
- **Reviewers.** The five roles are preparer, measurement, interface,
  rights/privacy and professional engineering. No person holds two roles for
  one interface. No model, agent or generator holds any role. All five
  safety-relevant interfaces need the professional engineering reviewer.

## Fastener assignment is unknown

Plate 809-02 lists the trim's speed nuts, washers and B 4,2 tapping screws, but
only the illustration shows which joint each one serves, and it is not
transcribed. The contracts list them as a **plate inventory** with the
assignment left unknown. A count from the plate is not a hole count.

## Not done here

- No measurement, no transform, no positioned component.
- No fit, clearance, airflow, thermal, occupant-safety or manufacturing verdict.
- RS identities for the hood, cluster, console, controls and pillars were not
  transcribed. They are marked `not_transcribed`, not absent.
