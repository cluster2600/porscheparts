# Catalogue schema changes

## Twin record — `twin.schema.json`

### 1.1.0 — 2026-11-06 (issue #509)

One contract now covers every record in `catalog/twins/`, 993 and 964 alike.
`scripts/validate_twins.py` executes the schema itself with a stdlib
evaluator (the CI virtualenv has no `jsonschema`), and refuses to load a schema
that uses a keyword the evaluator does not implement. Where `jsonschema` is
installed, `tests/test_validate_twins.py` checks that the reference
implementation reaches the same verdict on every record and every negative case.

**Why.** Version 1.0.0 hardcoded generation 993, model years 1993–1998 and
narrower value sets, while the validator had been widened in code for the 964
floor-pan twin. The schema was never executed. Run against the records, 1.0.0
refused `twin-964-chassis-floor-0001` (13 errors) and
`twin-993-m64-engine-system-0001` (11 components without `part_id`, which the
validator never checked).

**Vocabulary carried into the schema** (the validator already accepted it):

| field | 1.0.0 | 1.1.0 |
|---|---|---|
| `vehicle.generation` | `993` | `993`, `964` |
| `vehicle.model_years` | 1993–1998 | per generation: 993 → 1993–1998, 964 → 1989–1994 |
| `scope.purposes` | six values | adds `datum_frame`, `envelope`, `repair_control` |
| `interfaces[].kind` | five values | adds `datum`, `registration` |
| `interfaces[].status` | four values | adds `partially_satisfied` |
| `interfaces[].components` | exactly 2 | exactly 2 for contact, clearance, fastener, clip, motion; 2 or more for datum and registration |
| `coordinate_system` | five keys | optional `vehicle_transform_note`, `vehicle_transform_provenance` |
| `validation` | three keys | optional `checks_passed` |
| root | — | optional `materials`, with declared keys only and a required `source` |

The validator's generation `911` (any year 1963–1998) is dropped: no record used
it, and its range admitted any year.

**Rules added to both layers.** Each refuses a claim the record cannot support:

- an interface whose status is not `missing_data` needs non-empty
  `validation.evidence`;
- a non-empty `checks_passed` needs evidence;
- a known `vehicle_transform` needs `vehicle_transform_provenance`;
- `F2_interface` or above needs evidence, a known vehicle transform, no
  interface at `missing_data`, and a known `accuracy_mm` on every host and
  candidate component;
- `F4_correlated` needs `validation.status` `physically_correlated`;
- `geometry_ready` or above needs evidence, a master geometry and a known
  `accuracy_mm` on every component;
- `digitally_checked` or `physically_correlated` needs at least `F2_interface`
  and every interface at `passed` or `failed`;
- the master file matches its format (`build123d` → `.py`, `FCStd` → `.FCStd`,
  `STEP` → `.step`/`.stp`, `none` → empty);
- `part_id` must be present, `null` when no part record is linked; an unknown
  `accuracy_mm` stays `null` and `0` is refused; unknown keys are refused at
  every level; text fields must not be blank; lists of ids, purposes, variants,
  measurements, derived files and evidence must not repeat.

**Rules only the validator applies**, because JSON Schema cannot express them:
`model_years.from <= to`; a `TWIN-<generation>-` id prefix must match
`vehicle.generation`; component and interface ids are unique; interfaces
reference declared components; geometry, master, derived and evidence paths
stay inside the repository and resolve case-exactly to files.

**Migration.** Version 1.0.0 is retired: the validator refuses it and points
here. All ten records and the template moved to 1.1.0. Only two records needed
more than the version label, and neither change adds a value:

- `twin-993-m64-engine-system-0001`: `"part_id": null` written on its eleven
  components, where the key had been omitted;
- `twin-993-wheel-hub-interfaces-0001`: four evidence paths corrected from
  `catalog/components/COMP-FUCHS-*.json` to the files that exist,
  `catalog/components/comp-fuchs-*.json`.

No `twin_id`, fidelity, status, measurement or evidence file changed. No twin
record is pinned by a lock or an evidence contract.

### 1.0.0

Initial 993-only zone record.
