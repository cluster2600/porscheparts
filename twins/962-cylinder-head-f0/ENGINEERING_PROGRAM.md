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
| 1. English baseline | English review documents, captions, GitHub description and download guidance; traceable sources | Delivered at `9c35e27c`: English documents, sixteen actual-mesh views and four English review ZIPs. The original twelve draft-release assets, six USD-review assets and three later analysis-review assets match local sizes and GitHub SHA-256 digests. The [new numerical-candidate download](derived/engineering/analysis-quality-review-delivery/README.md) includes exact BIN/PLY geometry and scoped evidence; all 18 preceding asset identities remain unchanged. The latest pushed baseline, `14735ae5`, passes full CI run 38945414192 (4,150 main-suite tests, 229 skips, plus the remaining Make targets). Historical hash-bound evidence remains unchanged. |
| 2. Material, cooling and strength | Process-specific material comparison; accepted thermal/structural models for the family; converged results and an explicit operating envelope | Seven manufacturer recipes and the [actual point/mass comparison](ENGINEERING_MATERIALS.md) are recorded. [HXT meshing and independent audit](MESHING_ENGINEERING.md) produced an exact-boundary tetrahedral volume, but its near-degenerate elements prevent engineering acceptance. [Separate analysis-surface trials](ANALYSIS_SURFACE_ENGINEERING.md) retain topology, distance and intersection rejections. [A new original-source quality candidate](ANALYSIS_QUALITY_ENGINEERING.md) removes all 744 facets failing the necessary face-quality bound; full-array, topology, global-intersection and scoped feature checks pass. Its [separate continuous-distance audit](derived/engineering/analysis-quality-distance/README.md) bounds deviation by 0.07192053 mm. These are surface checks. One [bounded HXT volume trial](derived/engineering/analysis-quality-volume/README.md) stopped at its 300 s deadline inside optimization, before any MSH export; final tetrahedral quality and interior DOFs are unknown. Volume quality and thermal resolution remain open. [Native constitutive witnesses](derived/engineering/constitutive-witnesses/README.md) verify temperature-dependent software laws. No head stress, thermal field, fatigue life or material selection is accepted yet. |
| 3. LPBF simulation | Verified process solver configuration; representative calibration and independent checks; full declared deposition/cooling/release sequence; distortion and residual-stress assessment | MOOSE constitutive witnesses verify variable elasticity, expansion and perfect-J2 yield. A [thermal birth witness](derived/engineering/thermal-birth-witness/README.md) verifies moving heat, k(T), cp(T), activation/history and nonlinear enthalpy; three time levels give energy errors of 1.3048%, 0.6794% and 0.3481%. A [mechanical birth and support-release witness](derived/engineering/mechanical-birth-witness/README.md) passes 5,514 full-field comparisons; its [independent review](derived/engineering/mechanical-birth-review-001.json) also verifies original capture bytes, all nodal histories, quadrature fields and force balance. All three use hypothetical software cards. Whole-head deposition/cooling/release and process calibration remain open; corrected Adamantine/CalculiX coupon evidence stays separate. |
| 4. Omniverse twin | OpenUSD family assembly with correctly mapped computed fields, units, frames, time, provenance and physical correlation where available | [Four exact solid USD exports](derived/engineering/usd-exact-family/README.md) preserve every source triangle, coordinate, winding and bound; all pass the official eight-check minimum reference in identity Z-up/mm frames. [Four review ZIPs are uploaded and verified](derived/engineering/usd-review-delivery/README.md) in the existing draft delivery. The vendor derivative losing 254 triangles stays rejected. [The full native CPU validation dependencies are now ready](derived/engineering/usd-full-validation-bore95/README.md). Actual validation of the unchanged bore95 export reports missing normals and six formal-profile findings; a physics-category check without authored physics grants no physical validation. Fluids/assembly, conformance repairs, computed fields and physical correlation remain open. |
| 5. PhysicsNeMo | Accepted dataset, model comparison, training, independent evaluation, operating-domain limits and inference integrated into the twin | Current geometric STL/VDB files are not solved-field training labels. No accepted 962 reference dataset, trained surrogate or inference result exists. |

The [source-envelope meshing follow-up](ANALYSIS_ENVELOPE_ENGINEERING.md)
preserves both memory-limit failures and a recovered complete checkpoint.
An [exact fixed-face certificate](FIXED_FACE_QUALITY.md) proves that checkpoint
cannot meet the unchanged tetrahedral SICN gate. The separately declared
[12 GiB trial](derived/engineering/analysis-envelope-trial-003.json) stopped at
its soft deadline without an out-of-memory kill and preserved a complete
1,408,636-face candidate. Full fixed-face screening and a separate exact
rational proof reject that final boundary for linear tetrahedra requiring
SICN ≥ 0.1. No further distance, intersection or tetrahedral run was attempted on that
rejected checkpoint. The separately named quality candidate starts from the
original inspected source and preserves this earlier rejection unchanged.

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
