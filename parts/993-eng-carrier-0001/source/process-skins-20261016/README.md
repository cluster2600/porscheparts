# Support preparation for revision ad12

This branch keeps the part layer engine `process-coverage-20261016/build_pyslm.py` unchanged. It replaces the construction of the envelopes, grids and skins; the old rejected passes remain distinct historical evidence.

The mixed store with seven envelopes is now readable and transportable. The surface checkpoints and their graphs remain distinct from the global admission: an accepted graph can still keep native material that the exact band check rejects. The new v2 generations also check this predicate before reuse. The full slicing and the exposure audit must be run on their actually admitted results.

## Current path

The [v6 recipe](../../../../manufacturing/workflows/993-carrier-lpbf-v6.json)
chains 37 steps with 293 pinned inputs. Its
[review](cold-v6-recipe-evidence/assessment.json) covers identities and
commands; the results of the real campaign remain separate.
The current CLIs are `generate_prism_region_v7.py` and
`generate_legacy_region_v7.py`, then `build_cached_v6.py` with the six checks
of `admissions_v3.py`. The arguments remain those of the variants detailed
below.
The recipe command uses `scripts/run_part_workflow_v2.py`: the seven
generations and the two assembly/slicing steps each have a timeout of
14,400 s, with no change to the geometric thresholds.

The [combinatorial construction](README-combinatorial.md) keeps the whole free
domain and adds only attested edge strips. The
[exact incremental assembly](README-incremental.md) keeps the same
contours, decisions and receipts, while avoiding repeated full
reconstructions. The generator and the admission load this version from pinned
private modules. The tests and the large-surface benchmark do not
replace the admissions and audits of the seven regions actually delivered.

The [redundant-strip variant](redundant_strip_interfaces.py) handles the
case of an attested interface bordering a re-entrant corner: it omits its extension
only if the whole quadrilateral is already contained in the domain, with
exact proof. It keeps the coordinates, the roles and the source domain.
The [dedicated tests](../../../../tests/test_carrier_redundant_strip_interfaces.py)
also keep the rejections of partially exterior strips. The
[per-surface log](chart_progress.py) keeps the input and output geometries
with their complete receipts. The preparer chooses the authority recorded
in each receipt; earlier results are not relabelled.

The v7 producers reuse the exact areas already computed. The
[v6 preparer](README_parallel_exact_admissions.md) distributes the replays
across four processes; the `exact-admission-replays.json` receipt binds their
execution and their results to the six admissions. The authorities and the old
receipts remain identified separately.

The following details also keep the v1/v2 versions and their historical
witnesses; the recipe above designates the variants to use.

## Environment

The versioned installer `../process-coverage-20261016/setup_pyslm.py` rebuilds an isolated environment from the pinned versions and patch. The modules in this directory use that environment without modifying the installed PySLM code. An independent reinstallation of the same state was run in `work/part-workflow/runtimes/pyslm-coverage-reproduced-012`; the receipt `work/part-workflow/pyslm-reinstall-012-validation.json` compares the 37 versions and the 775 files relevant to the part layers.

The separate native installers are `../native-pymesh-20261016/setup.py`, `../native-cgal-20261016/setup.py` and `../native-cgal-distance-20261016-v3/setup.py`. They produce their own installation receipts. The Boolean computation keeps exact coordinates between operations of the same CSG tree; the final IEEE export is then checked separately. Differences in versions, parameters, inputs or receipts are grounds for rejection.

## Inputs and admissions

`prepare_exact_envelopes_v2.py STL OUTPUT --identity-receipt MESHING.json --reduce-horizontal` exports the body in its build pose, each prism chain, each original positive roof and each required XY mask. `--sha256 SHA` is the exclusive alternative for an already frozen input. The new manifest is `inputs-v2.json`; the historical manifest `inputs.json` stays separate. The reduction of strictly horizontal sheets keeps the boundaries and source coordinates. The subtraction covers the full body; overlapping free intervals are not replaced by a maximum height.

The per-region native CLI is `run_native_envelope_case.py INPUTS/inputs-v2.json CASES/source-NNN --source-index N --runtime NATIVE_RUNTIME.json`. It distinguishes the two positive-prism cases 0/2 and the five historical CSG trees 1/3/8/9/10, with their explicit operation orders. Its terminal `case.json` has the status `executed` only if the case's own gates and the closure of the scopes are achieved. `seal_envelopes_v2.py INPUTS/inputs-v2.json CASES CASES STORE` consumes these terminals and keeps the native evidence with unique names and relative references. The third argument can also be an explicit historical manifest of the two prism cases.

After the native computations, `audit_envelope_case.py` checks the final IEEE mesh with the independent detector, then the rational contact classifier. `seal_envelopes.py INPUTS.json CASES OUTPUT` gathers the inputs, the seven results and their evidence into a self-contained store. A `status: passed` field without receipts bound to the exact hash of the mesh is not enough.

The unversioned local prototype `run_native_envelopes.py` is not an input of the recipe. The recipe uses the seven bounded steps of `run_native_envelope_case.py`, then a separate sealing. The variant `../native-pymesh-clip-20261016/setup.py` subtracts the body intersected with a box that strictly encloses the chain; the set identity is justified in its receipt and the exact coordinates stay in the same tree. This prefiltering cuts no useful portion of the body. A failure keeps the log and prohibits the final sealing.

The [v2 recipe](../../../../manufacturing/workflows/993-carrier-lpbf-v2.json) contains 37 steps and 211 pinned versioned inputs. The [review receipt](cold-recipe-evidence/assessment.json) keeps the check of the digests, of the 25 commands after the CAD/computation prefix and of output immutability. The first twelve step objects and the 45 inputs of the initial recipe are identical. This review does not claim to have run the 37 steps on the carrier: the real generations and audits keep their own receipts. The complete real store with seven envelopes exists; on its own it is not an admission of the support surfaces and trajectories.

For each region, the store must pass: closed and oriented topology, zero intersections outside the shared simplex, a return from the exact kernel, complete face lineage and bidirectional drift under the declared bound. The repair precision is fixed at 51 bits and five iterations; the bound is computed from the three native grid steps, with no extra margin. A partial result or a `false` return remains rejected.

## Sheets and trajectories

`peripheral_skins.py` uses the real vertical walls of the envelopes. The unfolding separates the junctions of the XY paths before the native infill and teeth, then remaps each piece without shortening the corners. `grid_intervals.py` checks the whole triangles of the grids within the real free sections and within the declared vertical penetration band of the teeth. The supports are sheets and trajectories; no solid volume is attributed to these open surfaces.

Each material component has an identifier, a face interval, its WKB and its source interfaces. `../process-scanpath-audit-20261016/exact_contacts_both.py` computes the intersection of the source interfaces with the free domain and the material, in rational arithmetic on the IEEE coordinates. The fractions stay exact until a single final encoding. The WKB and SHA of the free domain and of the material accompany each contact and face group. The GEOS diagnostics are kept separately. A component without its own contact must obtain proof of a real 3D connection; a projection, a bounding box or a contact point does not establish it.

The `--solid-sheets` option of `diagnose_support.py` and `build_cached.py` requests the native PySLM mode `generateTrussGrid=False`: sheets without truss perforations, with the native tooth preparation. The small adapter `solid_sheets.py` converts the paths returned by this mode into its native PolyTree object. It does not fill the spaces between sheets and attributes no volumetric thickness to them. The same checks of contacts, 3D connection and exposure remain mandatory. The box witness passes. The second real trial on the large right-hand region generated 105,712 faces and 946 groups in 321 s; its graph still rejects fourteen isolated groups, representing 1.028245 mm² intrinsic. All fourteen have positive exposure on the real schedule and therefore remain required. The native counter-case without teeth serves only to diagnose fragmentation; no new strategy is admitted by this result.

The distinct strategy `--solid-sheets --continuous-interfaces` rebuilds an interval when its native teeth fragment the material or miss a required contact. It keeps its whole connected free domain D and adds only vertical sweeps of its attested interfaces, limited to the declared penetration of 0.2 mm and to Z ≥ 0. An overlap that would join two distinct free intervals is rejected. This is a **new construction**, with the added and removed native areas declared; it is not a normalisation identical to the toothed material. Native fragments outside the real strips can thus disappear. Continuous contacts increase the surface to be detached and remain identified in each receipt. The native horizontal-roof witness passes at the real 60 µm planes, with exposed contact at Z = 1.05 mm thanks to the penetration up to Z = 1.2 mm. The real region keeps its diagnostic status until the same admissions and the full exposure audit.

Horizontal edges shorter than one cycle, which PySLM keeps without teeth, can lose their contact after Clipper quantisation. `quantized_contacts.py` restores only an existing edge at its identified source Z, under the measured native half-cell; it keeps the displacement and the before/after coordinates in the receipt. Contours that the native full-edge mode erases under its cell are kept in their exact source coordinates, with an explicit decision.

A chart is excluded from support only if `layer_schedule.py` proves an empty or point section on every real exposure plane concerned. There is no area or height threshold for this decision. The receipt keeps the faces, the area, the bounds, the SHA of the schedule and the neighbouring layers; the source envelope stays whole. The verified count is `expected = generated + explicit_excluded`, and the admission recomputes this evidence from the source mesh. The groups actually generated must then all appear in the exposure audit.

An encoded triangle with exactly zero rational area may be removed only after proof that its segment or its whole point is covered by the non-zero triangles of the same component. `exact_zero_face_coverage.py` keeps the rational witnesses; no triangle of positive 3D area is removed. This normalisation of the IEEE set is not proof of conservation of an intrinsic area that would already have collapsed at remapping.

The continuous construction proves the closed inclusion D ⊆ material ⊆ strip on the IEEE coordinates treated as exact fractions. A hole produced by the overlay is removed only if its whole domain is certified within the intentional union D + sweeps and within the authorised strip; its exterior coordinates and the other holes remain identical. The preflight of 33 modified units passes these inclusions. The check of the 662 final results recovers exactly the normalised boundaries of the individual components, with no new bridge. The versioned compact receipts are `continuous-verification.json` and `continuous-union-verification.json`; they are not an admission of the whole part.

The new check in `continuous_prism_interfaces.py` uses `exact_band_union_v2.py`, the primitives of the frozen helper `exact_band_union.py` and the rational convex subtraction `exact_convex_union.py`. It certifies the same intentional union of vertically swept triangles, before its GEOS overlay. The positively oriented triangles must reproduce exactly the boundary chain and the source area. Each material triangle must then be covered by the closed union; the first positive remainder gives a rejection witness, never a partial PASS. The primitives, the 0.2 mm penetration and the Z ≥ 0 clipping remain explicit.

This version also rebuilds a native result whose confinement proof fails, with the reason `native_material_not_confined_to_intended_band`. The inherited strategy name still contains `only_for_native_fragmented_intervals`; the reasons and per-interval evidence describe its extended scope. The GEOS deviations remain diagnostics, with no area threshold used to accept a residual. The domains, the exported material and the rational receipts are bound by WKB and SHA; the admission recomputes the proof from these polygons. The six other criteria and the layer audit remain independent.

`region_checkpoints.py` keeps a successful region with the identities of the posed part, the envelope, the attested interfaces, the parameters, the schedule, the sources and the runtime before/after. The loader `PreparedRegion(directory).geometry(block)` rejects a difference and rechecks the three files and the receipt before/after loading and reuse. The status `region_geometry_completed_no_global_admission` replaces none of the six global checks.

`collect_prepared_regions.py STORE REGIONS PREPARED.json` requires the seven successful `REGIONS/source-NNN/region-checkpoint.json` and binds their order to the SHA of the store. Relative paths are resolved from the manifest. `build_cached.py STL OUTPUT --identity-receipt MESHING.json --envelopes STORE --part-cache CACHE --region-checkpoints PREPARED.json --solid-sheets --continuous-interfaces` assembles the regions, then produces six separate receipts: envelopes, regions, skins, grids, contacts and collisions. `--supports-only` separates this sealing from the layer computation; a new call with `--reuse-support-stage SUPPORTS` verifies that checkpoint and its exact prepared manifest before slicing. `admissions_v2.py` adds the rational inclusions, their binding to the materials actually exported and the rejection of a region without an explicit continuous strategy. The part cache must be complete and compatible with the same parameters, pose and sources; its arrays are read back without recomputing hatches.

The exact support section hook remains distinct from the part engine. The complete independent audit `../process-scanpath-audit-20261016/audit_complete_supports_hybrid.py PROCESS AUDIT --source-stl STL --part-cache CACHE` must then check all recorded layers, the confinement of whole segments and the contacts actually exposed, with rational contact intersections down to the real part section. It loads the hybrid store from the exact sources of the result. Its receipt and the trajectory sub-receipt must carry `rational_part_contact_intersections=true` and `hybrid_envelope_store_verified=true`; the coverage must also carry `every_material_group_exposed=true`. The six geometric admissions do not replace this last receipt.

## Diagnostics and witnesses

`diagnose_support.py PART.npz VOLUME.npz INPUTS.json OUTPUT --source-index N --solid-sheets --continuous-interfaces` freezes its sources and generates a single real region. Its status explicitly keeps the unproven contacts; this command does not create a manufacturing admission. It seals a reusable checkpoint only if the real material graph is accepted and all identities have remained unchanged. This current CLI decodes the old CSGTree cases; the adapter for the two new positive-prism cases is separate.

The new generators are `generate_legacy_region_v2.py PART VOLUME INPUTS OUTPUT --source-index N --solid-sheets --continuous-interfaces` for the CSGTree cases and `generate_prism_region_v2.py PART NATIVE_AUDIT ROOFS INPUTS OUTPUT --source-index N` for the prisms. The second receives the original native package, where `local-evidence-map.json` is the sibling of the receipt; the nine repaired faces on the left keep their unknown-interface status. Both CLIs freeze the additional sources and their hook, check their hashes before/after, and return a failure without an actually successful checkpoint. The outputs are compacted by serialisation only, without removing mathematical fields.

The witnesses comprise a box, an interior opening, two separate Z intervals, a surface at several heights over the same XY, a segment crossing a hole and a floating material island. The tests are in `tests/test_carrier_skin_geometry_20261016.py`. Each real rejection is kept in a new directory; no rejected receipt is rewritten to take the status of a later pass.
