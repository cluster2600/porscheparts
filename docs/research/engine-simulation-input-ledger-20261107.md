# Four engine simulation cases: input and owner ledger

Issue #457; reviewed 2026-11-07 against repository revision
`429deaef606277ba81f5e895ff26aebc088cb4a6`.

All four cases remain blocked. This ledger names the missing inputs and the
action needed to receive them; it does not nominate a contributor who has not
agreed to do the work. The project owner must assign an external specimen/data
custodian and an independent engineering reviewer. Acquisition, paid computing,
physical testing and engineering release are not authorised by this ledger.

The governing records remain unchanged:
[load cases](../../twins/engine-simulation-contracts/load-cases-f1.json),
[components](../../twins/engine-simulation-contracts/components-f1.json),
[interfaces](../../twins/engine-simulation-contracts/interfaces-f1.json) and
[materials](../../twins/engine-simulation-contracts/materials-f1.json).
The [project charter](../PROJECT_CHARTER.md) and
[capture protocol](../CAPTURE_PROTOCOL.md) govern outside contributions.

## Shared admission and responsibilities

For each case the project owner must select one exact variant and anonymous
specimen, appoint a data custodian and obtain explicit rights for the geometry
and operating data. The custodian must supply source revisions and hashes,
units, frames, calibration and uncertainty. A reviewer independent of the
contributor must admit those inputs against interfaces and predeclared checks.
No 917 or 935 scan establishes a measured 993 assembly.

The solver maintainer must then select and lock an exact solver version, its
dependencies, commands and acceptance tolerances. The F1 contract names solver
families, not qualified numerical runtimes. A passing software test cannot fill
any missing operating input. Each case needs independently checked boundaries,
mesh convergence, residual/conservation criteria, output hashes and a physical
holdout before acceptance. PhysicsNeMo remains disabled until accepted reference
fields, a parameterized training domain, disjoint held-out data and declared
error thresholds exist.

## LC-993-VALVE-THERMAL-STEADY

- **Variant and editable geometry:** not selected. The intake/exhaust envelopes
  are proxies; seat, guide, keeper, margin and neck interfaces remain unresolved.
  Declared Carrera 42.5 mm and Turbo 43.5 mm exhaust envelopes must not be mixed.
  Owner action: select the application; the external custodian supplies lawful,
  editable, measured valve/seat/guide geometry and its independent interface check.
- **Material:** EOS LPBF Ti64 intake and aged-bar INCONEL 751 exhaust are only
  candidates. Wrought TIMET thermal data do not qualify LPBF material.
  Owner action: material/process supplier provides the actual route, lot,
  treatment and temperature-dependent card; the reviewer admits its range.
- **Operating inputs and loads:** all eight contract inputs remain null:
  `seat_and_guide_geometry`, `gas_side_temperature_c`,
  `seat_temperature_c`, `guide_temperature_c`,
  `gas_side_convection_w_m2_k`, `contact_conductance_w_m2_k`,
  `emissivity`, `qualified_material_property_set`.
  Owner action: the appointed test-data custodian supplies the exact operating
  point, measurement uncertainty and independently justified heat-transfer model.
- **Runtime and acceptance:** CalculiX or JAX-FEM is undecided; no exact version
  is admitted. After the above gates, the solver maintainer must bind the thermal
  boundary map and verify energy balance, temperature convergence and a
  separately measured temperature holdout. No thermal solve is authorised now.

## LC-993-VALVE-DYNAMIC-CYCLE

- **Variant, rights and geometry:** the same unresolved valve family is used,
  but a complete measured cam/follower/spring/seat/guide/keeper assembly is
  additionally needed. Owner action: select the engine/valvetrain and obtain
  the custodian's geometry and reuse grant; do not use layout lobes as lift data.
- **Material:** candidate cards above do not establish hot contact, wear or
  fatigue behaviour. Supplier and independent reviewer must qualify the
  delivered condition and applicable temperature/load range.
- **Operating inputs and loads:** all eight inputs remain null:
  `cam_lift_profile`, `engine_speed_rpm_cases`, `spring_force_curve`,
  `moving_masses_kg`, `hot_clearances_mm`,
  `seat_contact_and_friction_model`, `damping_model`,
  `measured_component_temperatures_c`.
  Owner action: the external valvetrain custodian supplies phase-resolved
  kinematics, force curves, masses, hot clearances and temperature evidence;
  the reviewer admits contact/friction/damping choices independently.
- **Runtime and acceptance:** CalculiX or an MBD solver remains undecided.
  The solver maintainer must lock the selected version, establish time-step
  and contact convergence, and compare displacement/contact-load predictions
  with an untouched operating holdout. No dynamic cycle is admitted now.

## LC-935-PORT-COLD-FLOW

- **Variant, rights and geometry:** `CMP-935-HEAD-ENVELOPE` remains an
  unidentified, unscaled envelope; `low_B` and `high_B` are candidate local
  domains, not identified ports. Owner action: the scan custodian establishes
  variant, specimen, lawful reuse and independent scale; then supplies editable
  port, valve and seat geometry with an inlet/exhaust identity review.
- **Material:** the head alloy remains unassigned. A cold-flow fluid model is
  still required; no thermal or structural material assignment follows from it.
- **Operating inputs and loads:** all nine inputs remain null:
  `port_identity`, `valve_and_seat_geometry`, `valve_lift_mm_cases`,
  `inlet_total_pressure_pa`, `outlet_static_pressure_pa`,
  `air_temperature_c`, `air_property_model`, `wall_roughness_m`,
  `mesh_independence_plan`.
  Owner action: the external flow-bench custodian supplies calibrated
  pressure/temperature/lift observations and an independent flow holdout;
  the reviewer approves the fluid and roughness model.
- **Runtime and acceptance:** OpenFOAM is named without an admitted version.
  The maintainer must lock one, pass geometry/topology admission first, then
  verify mesh independence, mass conservation and pressure/flow correlation.
  Neither candidate domain is ready for a solver or surrogate.

## LC-917-EXTERNAL-COOLING

- **Variant, rights and geometry:** the reference mesh has unconfirmed units and
  component identity. The historical preparation assumed one OBJ unit equals
  one millimetre, and explicitly left that assumption unconfirmed. No editable,
  measured assembly is admitted. Owner action: the scan custodian supplies
  explicit reuse rights, same-specimen scale and identified component surfaces.
- **Material:** assignments remain unknown per component. Supplier/custodian
  must identify each alloy, treatment and coating before any conjugate model.
- **Operating inputs and loads:** all eight inputs remain null:
  `checkmesh_clean_result`, `confirmed_scale_m_per_obj_unit`,
  `air_velocity_or_mass_flow`, `air_temperature_c`,
  `ambient_pressure_pa`, `surface_heat_flux_or_internal_temperature_map`,
  `component_material_assignments`, `mesh_independence_plan`.
  Owner action: the external engine-test custodian supplies the measured flow,
  thermal and ambient operating case; the reviewer admits each boundary map.
- **Runtime and acceptance:** the retained historical `checkMesh` log identifies
  OpenFOAM Foundation 13, build `13-18870c24d21c`. The contract image is
  `ghcr.io/cluster2600/3dprinting993-mesh-cfd@sha256:a1db60cbf61bbcca52c171e50cab01ed0b6ec860b227e7c5fc50f7b809659b4f`.
  This identifies a historical method runtime, not an admitted physical case.
  The solver maintainer's next action is to recover the exact historical
  `polyMesh` and independently inspect the surface flags below. No refinement
  sweep is justified before that upstream audit.

## Executed 917 surface audit

The private retained case has nine files: three dictionaries, the 300,000-facet
STL, preparation/validation JSON and three original logs. It has **no
`constant/polyMesh`**. Therefore the original `checkMesh` cannot be rerun
from this retained case without reconstructing a new mesh.

[Input hashes](engine-simulation-admission-20261107/input-hashes.json) bind all
nine retained files. The 15,000,084-byte STL has SHA-256
`8ec141564af2e41f578f3be254945a611953346a109f4180fe00b6cf620934d4`.
The original `checkMesh.log` has SHA-256
`ce5eee3b2dd6c39b374a0433ebb9cbe42856be034c049b6c0f1402d40c746078`.
It reports 130,208 cells, 76 highly skew faces, 6,111 concave cells and two
failed checks. The log supplies maximum non-orthogonality 64.6794 degrees,
although the historical summary leaves that field null. Neither file was edited.

A fresh, bounded, offline read-only surface audit used native Linux/arm64
OpenCFD 2406, image
`opencfd/openfoam-run@sha256:1db0df068a490178efda0e30831a34f8ebdfa9ba06c7413f4063a46dc0887532`.
This is a separate diagnostic implementation, **not** a replay of Foundation 13.

```bash
source /usr/lib/openfoam/openfoam2406/etc/bashrc
cd /tmp
timeout --signal=TERM --kill-after=5s 45s surfaceCheck \
  -checkSelfIntersection /input/constant/triSurface/917-engine-exterior.stl
```

The case was mounted read-only at `/input`; the container had no network,
two CPUs, 2 GiB memory, 128 processes, no capabilities, no new privileges,
read-only root and a 128 MiB temporary filesystem. The command exited zero.
[Diagnostic log](engine-simulation-admission-20261107/surfaceCheck.log),
SHA-256 `4c2c7baa5d9d4d999a9937e95e1a6c97b3fdfd8520d4b539932ac8144ef372fe`,
reports a closed, single connected surface **and 139,114 self-intersection
locations**. These are tool flags awaiting an independent triangle-level
witness, not an established count of physical intersections. The zero exit
code and closed topology do not admit the surface.

The generated intersection-point diagnostic was temporary and was not retained;
only the log and input identities support this audit. Raw scans/STLs remain
private. No geometry was repaired, no mesh regenerated, no flow/thermal solver
run and no surrogate enabled. The next methodological action is independent
surface diagnosis and recovery of the missing historical mesh, not tuning
around the flags. Physical acceptance additionally needs all inputs above.

### Independent crossing witness

A bounded libigl 2.6.3 search on the unchanged STL found a non-coplanar
intersection between zero-based facets **8 and 354** after testing 14
non-adjacent candidate pairs. Their six vertex coordinates share no vertex.
The segment length is 0.0005655837319969354 in the historical STL coordinates;
this is not a physically calibrated length. The search stopped at the first
witness and does not establish the total intersection count.

A separate standard-library rational-arithmetic check reread both facets
straight from the binary STL at offsets `84 + 50 * face_id`, verified the
input SHA-256, and matched their coordinates exactly to the search witness.
It converted each binary floating-point coordinate to its exact rational
value, intersected each triangle with the other triangle's plane, and found a
strictly positive overlap of their line segments. The common midpoint lies
exactly on both planes and has strictly positive barycentric weights in both
triangles. Thus this is an interior crossing, not a shared-edge contact or
only an OpenCFD flag. A crossing and a disjoint synthetic fixture passed
before the libigl search.

The four private audit artifacts are retained beside the raw case audit;
vertex coordinates and intersection points are not redistributed:

| Artifact | SHA-256 |
|---|---|
| `independent_witness.py` | `8dd633933ba35a5cec18f0350169741b4a1d0fb690b7bb6341edc17970b247dd` |
| `independent_witness.json` | `1f07a267614cf11954703c6cee33c7545ca72740db66f9a291d46f5f0504d95a` |
| `exact_witness.py` | `084274d119a6d5177d19816e06e17b725af94f279e80c26871ef22fca2799bb8` |
| `exact_witness.json` | `d984fd4cb4631c7776f836ef08700fb66469fcd3eacef36b9adbd8aa794e1a39` |

**Admission verdict: rejected for remeshing as supplied.** At least one
self-intersection is independently confirmed in the derived surface. The
139,114 OpenCFD locations are not independently enumerated or all confirmed.
A reviewer must trace the crossing back to the acquired surface and establish
an admissible revision before further meshing; automatic repair or parameter
sweeps cannot establish source fidelity. The historical failed case stays
unchanged. No physical geometry, flow or thermal acceptance follows.
