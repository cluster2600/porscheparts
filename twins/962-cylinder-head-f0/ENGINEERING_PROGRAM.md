# 962 C head: engineering execution programme

The owner requested all five stages on 16 October 2026. English is the working
language. The reference remains the water-cooled 962 C 3.0 L, with six engine
scenarios through 4.0 L and four actual head geometries. This programme tracks
the complete requested outcome; preparation or software tests do not complete
a physical engineering stage.

The geometry baseline is commit `79180221fa79f2f669cbf3c0b9104cbb662c39d6`.
Its [delivery receipt](derived/family/delivery-report.json), original outputs
and rejections remain intact. New views, assumptions and calculations receive
new paths and receipts. An unknown datum or material property remains unknown;
an explicit research assumption can support a conditional calculation.

| Stage | Required outcome | Current evidence and remaining work |
| --- | --- | --- |
| 1. English baseline | English review documents, captions, GitHub description and download guidance; traceable sources | Delivered at `9c35e27c`: English documents, sixteen actual-mesh views and four English review ZIPs. All twelve draft-release assets match local sizes and GitHub SHA-256 digests. Exact-head GitHub check run 38931794627 passes. Historical hash-bound evidence remains unchanged. |
| 2. Material, cooling and strength | Process-specific material comparison; accepted thermal/structural models for the family; converged results and an explicit operating envelope | Seven manufacturer recipes and the [actual point/mass comparison](ENGINEERING_MATERIALS.md) are recorded. [HXT meshing and independent audit](MESHING_ENGINEERING.md) produced an exact-boundary tetrahedral volume, but its near-degenerate elements prevent engineering acceptance. [Separate analysis-surface trials](ANALYSIS_SURFACE_ENGINEERING.md) retain topology, distance and intersection rejections. [Native constitutive witnesses](derived/engineering/constitutive-witnesses/README.md) verify temperature-dependent software laws. No head stress, thermal field, fatigue life or material selection is accepted yet. |
| 3. LPBF simulation | Verified process solver configuration; representative calibration and independent checks; full declared deposition/cooling/release sequence; distortion and residual-stress assessment | MOOSE constitutive witnesses verify variable elasticity, expansion and perfect-J2 yield. A [separate thermal birth witness](derived/engineering/thermal-birth-witness/README.md) verifies moving heat, k(T), cp(T), activation/history and nonlinear enthalpy. Three native time levels give continuous energy errors of 1.3048%, 0.6794% and 0.3481%, meeting their frozen criteria. Both families use hypothetical software cards. Whole-head deposition/cooling/release and process calibration remain open; corrected Adamantine/CalculiX coupon evidence stays separate. |
| 4. Omniverse twin | OpenUSD family assembly with correctly mapped computed fields, units, frames, time, provenance and physical correlation where available | [Native conversion readiness](derived/engineering/usd-conversion-readiness/README.md) is established. One original-head [vendor conversion](derived/engineering/usd-bore95-conversion/README.md) passes the official minimum USD check but loses 254 source triangles and fails exact oriented-triangle parity. It remains a rejected derivative. Full validation dependencies, source-exact family transfer, computed fields and physical correlation remain open. |
| 5. PhysicsNeMo | Accepted dataset, model comparison, training, independent evaluation, operating-domain limits and inference integrated into the twin | Current geometric STL/VDB files are not solved-field training labels. No accepted 962 reference dataset, trained surrogate or inference result exists. |

## Execution and acceptance

**Material and service calculations.** Bind each material point or curve to its
alloy, powder, machine, orientation, treatment and test condition. Compare the
same geometry and boundary conditions before attributing differences to the
material. First establish usable solid and coolant volume meshes and explicit
attachment, contact and load surfaces. Run numerical witnesses, force and
energy balances, mesh/time convergence and load/constraint sensitivity. Model
pressure, thermal expansion, retention of seats/guides, and fatigue/creep only
to the extent supported by the constitutive data and load histories. Report
conditional predictions separately from physical qualification. Intermediate
bores and different engine duty cycles require their own checks.

**Printing calculations.** Retain the existing corrected exporter and exact
synthetic coupon as verification anchors. The verified reduced Adamantine
profile excludes nonconstant properties and does not establish deposition,
plasticity, powder or support-removal behaviour. Verify the required expanded
configuration before using it for head predictions. Bind the process model to
the machine, material recipe, plate, supports, orientation, layer/scan history,
thermal boundaries and post-processing sequence. Progress through numerical
witnesses and representative measured coupons before interpreting the full
head. Carry the declared distortion/residual-stress state into the subsequent
service-strength calculation.

**Twin and learned models.** Compose the actual geometry and accepted field
results in OpenUSD with explicit source and case identities. Check coordinate
and field mappings against the native solver outputs, then correlate with
independent measurements. For PhysicsNeMo, split whole geometries/builds/load
cases before fitting normalisation; compare graph and geometry-aware operator
models with simple baselines. Evaluate conservation, hotspot errors,
uncertainty, extrapolation limits and end-to-end runtime. Recompute proposed
design improvements with the reference solvers before accepting them.

Missing physical inputs do not prevent preparation or clearly labelled
sensitivity studies. They prevent measured-fidelity, material-qualification,
life, calibrated-process or manufacturing claims. No fixture experiment,
render, import test or surrogate score closes those gates by itself.
The engineering input validator checks completeness, units and source binding;
even its `--require-qualification` option does not authenticate supplied
physical evidence or replace engineering acceptance.

The [thermal verification inputs and whole-head execution path](source/physics_witness/thermal_birth/README.md)
distinguish numerical activation tests from deposition of the actual head.
Its [later checker-hardening record](derived/engineering/thermal-birth-witness/POSTRUN_HARDENING_002.md)
preserves the original results and separately records rejection of invalid
refinement-error inputs. The portable runner's runtime/output guards are
tested; its complete three-level reproduction has not been repeated.

## Reproduction of English views

```sh
python3 twins/962-cylinder-head-f0/source/render_english_family.py \
  --bore 95 --output work/962-engineering/new-english-views/bore-95
```

This uses the retained local inspected meshes and requires VTK and NumPy. It
checks the report and mesh hashes before rendering, refuses an existing output
directory, records new image hashes and never regenerates the native geometry.
The other supported bores are 98, 100 and 102 mm. The
[English view receipts](derived/family/english-views/bore-95/render-report.json)
record a viewing operation, not a thermal, structural or process calculation.
