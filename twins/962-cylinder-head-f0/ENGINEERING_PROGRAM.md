# 962 C head: engineering execution programme

The owner requested all five stages on 16 October 2026. English is the working
language. The reference remains the water-cooled 962 C 3.0 L, with six engine
scenarios through 4.0 L and four actual head geometries. This programme tracks
the complete requested outcome; preparation or software tests do not complete
a physical engineering stage.

The [bore95 atomic-cavity surface checkpoint](ATOMIC_CAVITY_ENGINEERING.md)
repairs the remaining 266 poor facets and passes independent full-array,
global topology/intersection and two-sided continuous-distance checks. Its
deviation upper bound is 0.0328639663163803 mm against the unchanged 0.0625 mm
budget. All 228 local disks and eight designated opening-point screens pass.
No accepted volume mesh or solved head field follows yet; the other bore
geometries need their own engineering checks.
The [exact repaired BIN/PLY review](derived/engineering/atomic-cavity-review-delivery/README.md)
is uploaded in the existing draft release. Complete independent checks cover all
143 archive members; GitHub digests and sizes match its three new assets, and
all 33 preceding asset records remain unchanged.
The [later raw-volume trial](ATOMIC_VOLUME_ENGINEERING.md) exports 3,058,267
tetrahedra. Independent saved-file reading verifies positive volumes and exact
boundary/tagged arrays, while confirming 283,853 cells below the unchanged SICN
0.1 gate. The volume remains rejected; the next repair needs separate evidence.
Its [exact MSH review download](derived/engineering/atomic-cavity-volume-raw-review-delivery/README.md)
preserves the rejection and completed readback. All 34 archive members pass
independent full-byte checks; the three uploaded assets match GitHub digests
and sizes while preserving all 36 preceding assets.
The [subsequent optimizer and diagnosis](derived/engineering/atomic-cavity-volume-followup/README.md)
record the separate 1,200-second stop with no saved result, followed by complete
poor-cell classification. With boundary coordinates and connectivity fixed,
interior movement cannot alter 245,420 of the 283,853 poor tetrahedra. The next
trial must address connectivity or a separately declared boundary variant.
The [separate z=0 finishing study](derived/engineering/atomic-cavity-plane-clip/README.md)
passes four unchanged clipping literals with exact-construction arithmetic.
The head proposal still has 3,112 faces below the unchanged surface-quality
threshold; surface admission, volume meshing and head fields remain open.
The [later full-array readback](derived/engineering/atomic-cavity-plane-clip-readback/README.md)
verifies retained coordinate bytes and confines all 3,112 poor faces to the
cap (2,396) and its rim (716). The later census and global reference below
establish their recorded local-complex and topology/intersection observations;
repair, cap/feature continuity and distance acceptance remain open.
The [rejected clipped-surface download](derived/engineering/atomic-cavity-plane-clip-raw-review-delivery/README.md)
contains exact BIN/coordinate IDs, lossless PLY and the three review capsules.
All 129 archive members pass independent byte checks; GitHub verifies the three
new asset identities while preserving all 39 prior records.
The [new local-complex census](derived/engineering/atomic-cavity-plane-clip-patch-census/README.md)
finds 758 poor-face edge groups sharing 760 contact vertices. Their complete
incident union is one manifold region with Euler −4 and six boundary cycles,
requiring fresh repair constraints; the earlier disk-only assessor cannot apply.
The [new global topology/intersection reference](derived/engineering/atomic-cavity-plane-clip-topology/README.md)
measures one connected component and Euler −208 with zero manifold defects and
zero global intersection pairs. This establishes a pre-repair baseline while
the 3,112 poor triangles still prevent surface admission.
The [completed read-only repair reference](derived/engineering/atomic-cavity-plane-clip-repair-reference/README.md)
verifies that the exterior-only and legacy fixed masks coincide and that the
complete planar cap is an abstract annulus with two boundary cycles. Both exact
shortest-edge scenarios have 476 groups; the separate mixed-face subset has
506. These observations select no repair target, keeper or acceptance policy.
The [subsequent cap-aware repair trial](derived/engineering/atomic-cavity-plane-clip-cap-aware-repair/README.md)
records an exact rim obstruction, a direct cap plot and two source revisions
whose four native fixtures pass independent saved-array checks. The original
2,700-edge head graph is refused before launch because 48 groups occupy
separated boundary runs. The separately compiled boundary-only successor uses
2,212 edges and 510 contiguous groups. Its single native head trial reports
1,122 remaining poor faces and rejects the proposal without exports. Mapped-cap
coverage is a native observation; later global/patch topology, neighbor and
envelope gates were not reached. No accepted volume or head field follows.
The [later mixed-side and cap refinement](derived/engineering/atomic-cavity-plane-clip-cap-refinement/README.md)
records a separate mixed-side census with zero poor survivors and a cap-only
necessary q≥2/29 pass on all 8,976 saved triangles. It preserves 38 fixed cells
and adds 3,092 interior points. The stronger Mesh_2 shape criterion retains
414 active failures. Assembly, complete surface checks and volume admission
remain pending; the cap result does not admit the full head.
The [separate material follow-up](MATERIAL_CONDUCTIVITY_FOLLOWUP.md) supplies
measured AlSi10Mg conductivity points. The [two native bar witnesses](MATERIAL_CONDUCTIVITY_WITNESS.md)
now verify the separate assumed piecewise-linear Z/XY laws with 109 final-field
checks each. Head material selection and thermoelastic inputs remain open.

The geometry baseline is commit `79180221fa79f2f669cbf3c0b9104cbb662c39d6`.
Its [delivery receipt](derived/family/delivery-report.json), original outputs
and rejections remain intact. New views, assumptions and calculations receive
new paths and receipts. An unknown datum or material property remains unknown;
an explicit research assumption can support a conditional calculation.

| Stage | Required outcome | Current evidence and remaining work |
| --- | --- | --- |
| 1. English baseline | English review documents, captions, GitHub description and download guidance; traceable sources | Delivered at `9c35e27c`: English documents, sixteen actual-mesh views and four English review ZIPs. The original twelve draft-release assets, six USD-review assets, three analysis-review assets, three rejected-volume review assets and three rejected-sized-volume review assets match local sizes and GitHub SHA-256 digests. The [new numerical-candidate download](derived/engineering/analysis-quality-review-delivery/README.md) includes exact BIN/PLY geometry and scoped evidence; the [separate rejected-volume download](derived/engineering/rejected-volume-seed-review-delivery/README.md) adds the exact raw MSH and its rejection evidence. The [later sized-volume download](derived/engineering/rejected-sized-volume-review-delivery/README.md) adds the sized MSH and its independent rejection evidence; all 24 preceding asset identities remain unchanged. Verified baseline `8168ff8c` passes full CI run 38955794356 (4,168 main-suite tests, 229 skips, plus the remaining Make targets). Historical hash-bound evidence remains unchanged. |
| 2. Material, cooling and strength | Process-specific material comparison; accepted thermal/structural models for the family; converged results and an explicit operating envelope | Seven manufacturer recipes and the [actual point/mass comparison](ENGINEERING_MATERIALS.md) are recorded. [HXT meshing and independent audit](MESHING_ENGINEERING.md) produced an exact-boundary tetrahedral volume, but its near-degenerate elements prevent engineering acceptance. [Separate analysis-surface trials](ANALYSIS_SURFACE_ENGINEERING.md) retain topology, distance and intersection rejections. [A new original-source quality candidate](ANALYSIS_QUALITY_ENGINEERING.md) removes all 744 facets failing the necessary face-quality bound; full-array, topology, global-intersection and scoped feature checks pass. Its [separate continuous-distance audit](derived/engineering/analysis-quality-distance/README.md) bounds deviation by 0.07192053 mm. These are surface checks. One [bounded HXT volume trial](derived/engineering/analysis-quality-volume/README.md) stopped at its 300 s deadline inside optimization, before any MSH export; final tetrahedral quality and interior DOFs are unknown. A [separate raw seed](derived/engineering/analysis-quality-volume-seed/README.md) saves 3,096,408 tetrahedra with exact boundary/readback and positive volume, but 1,478,281 elements fail SICN 0.1 and only three interior nodes exist. Independent saved-file reading confirms the rejection. A [separate 1.75 mm sized seed](derived/engineering/analysis-quality-volume-sized/README.md) increases referenced interior nodes to 77,307 and reduces the below-0.1 count to 284,806. Its 3,059,463 tetrahedra retain the exact boundary, volume and saved-array checks, but the unchanged quality gate still rejects it. Independent readback locates two nonpositive-SICN cells made exclusively from fixed boundary nodes, so interior-only relocation cannot repair them. A [saved-cube default optimizer](derived/engineering/saved-cube-default/README.md) changes internal connectivity and passes the later independent cube quality check (minimum SICN 0.1909054), while its original post-export API audit failure remains recorded. A [separate head post-export optimizer](derived/engineering/analysis-quality-volume-postexport/README.md) reaches its 300 s deadline before returning or exporting a mesh; its cache-refresh step is not reached. Volume quality and thermal resolution remain open. That earlier surface also exceeds the unchanged finest 0.0625 mm representation budget; a closer surface is required for the complete refinement study. [Native constitutive witnesses](derived/engineering/constitutive-witnesses/README.md) verify temperature-dependent software laws. No head stress, thermal field, fatigue life or material selection is accepted yet. |
| 3. LPBF simulation | Verified process solver configuration; representative calibration and independent checks; full declared deposition/cooling/release sequence; distortion and residual-stress assessment | MOOSE constitutive witnesses verify variable elasticity, expansion and perfect-J2 yield. A [thermal birth witness](derived/engineering/thermal-birth-witness/README.md) verifies moving heat, k(T), cp(T), activation/history and nonlinear enthalpy; three time levels give energy errors of 1.3048%, 0.6794% and 0.3481%. A [mechanical birth and support-release witness](derived/engineering/mechanical-birth-witness/README.md) passes 5,514 full-field comparisons; its [independent review](derived/engineering/mechanical-birth-review-001.json) also verifies original capture bytes, all nodal histories, quadrature fields and force balance. All three use hypothetical software cards. Whole-head deposition/cooling/release and process calibration remain open; corrected Adamantine/CalculiX coupon evidence stays separate. |
| 4. Omniverse twin | OpenUSD family assembly with correctly mapped computed fields, units, frames, time, provenance and physical correlation where available | [Four exact solid USD exports](derived/engineering/usd-exact-family/README.md) preserve every source triangle, coordinate, winding and bound; all pass the official eight-check minimum reference in identity Z-up/mm frames. [Four review ZIPs are uploaded and verified](derived/engineering/usd-review-delivery/README.md) in the existing draft delivery. The vendor derivative losing 254 triangles stays rejected. [The full native CPU validation dependencies are now ready](derived/engineering/usd-full-validation-bore95/README.md). The original bore95 export retains its missing-normal findings. A [separate full normal-only derivative](USD_NORMALS_ENGINEERING.md) now passes all eight minimum checks and generic, Geometry and Physics CPU checks; the substantive formal profile still has six failed feature rows. There are no authored bodies, colliders or material bindings, so the Physics-category pass grants no physical validation. Fluids/assembly, remaining conformance repairs, computed fields and physical correlation remain open. |
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

The [actual GMRES/HYPRE affine witness](derived/engineering/gmres-boomeramg-affine/README.md)
now verifies one installed-runtime solve, its exported operator and Newton
correction, all 64 spatial nodes and six individual face fluxes. Independent
NumPy and Decimal calculations agree within the frozen criteria. This supplies
an iterative-solver verification anchor; head import, resolution and convergence
remain separate requirements.

The [imported-cube witness](derived/engineering/head-imported-cube-witness/README.md)
now checks the separate nine-node ASCII2.2 import, discrete P1 solution and
complete Exodus geometry, sideset and nodal-field readback. The original
binary-format refusal and incorrect-sign assessor failure remain preserved;
the corrected saved-output assessment uses the unchanged native data. This
normalized w field is in mm². Its 25% continuum flux deficit remains unresolved,
so the discrete software pass does not establish head or mesh convergence.

The [endpoint-collapse reference cases](derived/engineering/finest-endpoint-fixtures/README.md)
now pass complete saved-array checks: the corrected helper removes the known
cube sliver while both declared stagnation controls remain unchanged. A
[separate original-head pass](derived/engineering/finest-endpoint-head-001/README.md)
hits its 4 GiB memory limit before exporting a proposal. All inputs remain
unchanged and the owned process is stopped and reaped. No closer head surface,
distance certificate or volume-quality admission follows from that attempt.

The [version003 patch-envelope references](derived/engineering/finest-endpoint-003-fixtures/README.md)
now pass both the direct subset witness and complete saved-array checks. The
unchanged 0.0625 mm rule uses only exact immutable original patch triangles;
this is a stricter candidate-to-original screen, with reverse coverage still
requiring its own complete-surface check. The
[separate version003 head run](derived/engineering/finest-endpoint-003-head/README.md)
finishes under the same 4 GiB limit in a 15.360 s controller window. Independent
readback confirms 284 collapses, every retained coordinate's original identity,
all 900,845 fixed vertices and all exterior oriented faces. Deficient facets
decrease from 744 to 266, so this proposal remains rejected. No distance,
intersection, volume or head-physics run follows that rejection.
The [separate English review download](derived/engineering/finest-endpoint-003-review-delivery/README.md)
now publishes the exact rejected BIN, coordinate-origin map and independently
verified PLY. Its 26-member ZIP and two metadata files are verified in the
existing draft release; all 27 preceding assets remain intact. The
[inventory correction](derived/engineering/ENDPOINT003_INVENTORY_CORRECTION.md)
distinguishes the executable input binding from the twelve head phase artifacts.

The [actual final-profile diagnosis](derived/engineering/remaining266-native-profiles/README.md)
queries all 135 remaining short edges without changing the saved head. Each
passes native topology and yields a custom placement, then fails the ordinary
squared-area ratio guard. Three native literal references precede this query;
independent arithmetic agrees with all 182 reported fixture/head pair classes.
The retained final-state obstruction is not a historical queue trace. No mesh,
solver or physical admission follows from this diagnostic.

The [later atomic cavity repair](ATOMIC_CAVITY_ENGINEERING.md) exports a separate
local candidate with 901,727 vertices, 1,803,870 triangles and zero remaining
facets below 2/29. Full root and independent peer readback confirm every point,
origin and oriented face, the fixed exterior, boundaries and all 933 affected
neighbor comparisons. The native immutable-patch envelope remains 0.0625 mm.
Its [actual compilation and three synthetic fixtures](derived/engineering/atomic-cavity-fixtures/README.md)
are retained separately. This local result supplies no global distance,
intersection, feature, volume-mesh or head-physics admission.
The subsequent [independent global surface checks](ATOMIC_CAVITY_ENGINEERING.md)
now pass topology/intersection and both continuous-distance directions for
that exact atomic candidate. Maximum deviation is bounded by 0.0328639663163803
mm against the unchanged finest 0.0625 mm budget. All 228 local disks retain
their exact fixed boundaries, and all eight designated opening points remain
strictly outside metal in the separate full-surface query. Volume-mesh
admission remains a separate requirement.

The [native USD normal-only software fixture](derived/engineering/usd-face-normals-fixture/README.md)
passes authoring, complete ordered-geometry/canonical-property checks and a
separate known-array readback. All five analytic face normals match their
predeclared binary32 values. The genuine tiny-source preflight and all three
native steps finish with unchanged inputs and reaped workers. This establishes
the small software path; no head derivative or head-validator pass is credited.
The later [full bore95 normal-only checkpoint](USD_NORMALS_ENGINEERING.md)
adds and independently verifies all 1,804,706 face normals without changing
ordered geometry or other authored content. Its eight minimum checks and
generic, Geometry and Physics CPU reports pass. The substantive formal profile
still fails six feature rows; its findings and single-component exception remain
visible. The original 744 deficient triangles remain in this USD, distinct from
the separate rejected 266-triangle endpoint003 proposal. These asset checks
provide no accepted mesh, material assignment or solved head field.

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
