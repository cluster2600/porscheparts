# Horizontal fan studies: status and reproduction

[Home](../../README.md) · [CAD and renders](README.en.md) ·
[R0 parameters](parameters/R0.json) · [V5 parameters](parameters/V5.json) ·
[Mechanical comparison](results/mechanics/mechanical-two-grid-comparison.csv) ·
[LPBF screening](results/lpbf/lpbf-screen.json) · [OpenUSD scene](omniverse/studies.usda)

These studies continue the existing work: [PR103](https://github.com/cluster2600/porscheparts/pull/103),
[PR105](https://github.com/cluster2600/porscheparts/pull/105),
[993 programme](../../twins/993-engine-cooling-fan-system-f0/README.md),
[PR121](https://github.com/cluster2600/porscheparts/pull/121),
[PR123 CFD diagnosis](https://github.com/cluster2600/porscheparts/pull/123) and
[PR126 horizontal system references](https://github.com/cluster2600/porscheparts/pull/126).
The geometry and results of earlier studies remain distinct from R0/V5.
The PR106 cylinder head is another project.

## Identity, provenance and assumptions

The scan was located in the owner's iCloud downloads and retained locally.
Its historical identity, unit and any 935/993 equivalence are unproven. The raw
scan has openings and intersections; it is neither the CFD domain nor a part
ready for manufacture. Private availability does not grant a public licence.
The owner's express permissions of 4 October 2026 cover reconstructions, renders,
scripts, parameters and sanitized calculation reports; the raw scan remains
excluded. These permissions grant no additional reuse rights.

R0 is an original analytical reconstruction guided by relative scan proportions.
The 275 mm diameter, nine blades, profiles, pitches, thicknesses, 1.1 mm cold gap,
axes, bore and interfaces are assumptions. +Z is the rotation axis and +X the
bevel drive input axis. The eight components have valid BReps with volume checks
after STEP reread; the rotor is one connected solid. The assembly contains nine
solids because the two pinion envelopes remain separate. Teeth, bearing seats,
sealing and tolerances are undefined.

V5 changes only the supporting web: thickness +30%, rotor volume +12.76%.
Historical calculation identifiers begin with `private_scan_informed` and remain
unchanged for evidence traceability. No scan file is included.

## Rotation and natural modes

CalculiX 2.23, Gmsh 4.15.2 and quadratic C3D10 tetrahedra are used, with the
Gmsh/CalculiX permutation checked against reference coordinates. Assumed material:
E = 70 GPa, ν = 0.33, ρ = 2700 kg/m³; units mm–N–s–tonne. All translations of
nodes on the single assumed bore are fixed; rotation is 6000 rpm. Twelve modes
are calculated without rotation prestress. All eight jobs terminate normally.

| Case | C3D10 | Maximum displacement (mm) | Maximum radial extension (mm) | First mode (Hz) | Nodal von Mises peak (MPa) |
|---|---:|---:|---:|---:|---:|
| R0, size 4.5 mm | 30825 | 0.5043 | 0.2276 | 377.79 | 189.25 |
| R0, size 3.6 mm | 51796 | 0.5100 | 0.2307 | 376.00 | 225.93 |
| V5, size 4.5 mm | 31443 | 0.2982 | 0.1568 | 511.38 | 182.39 |
| V5, size 3.6 mm | 60821 | 0.3033 | 0.1599 | 507.97 | 192.17 |

Displacements and the first mode vary by less than 2% between these two meshes;
this does not establish complete convergence or physical correlation. The global
V5 improvement appears on both meshes: maximum displacement about −40.5% and
first mode about +35.1% on the finer mesh. Stresses remain mesh dependent: the R0
peak increases 19.38% and V5 5.36% between sizes. Peaks occur at blade roots,
r ≈ 83.897 mm, rather than the fixed bore at r = 13.75 mm. The analytical junction
has no measured fillet and makes these peaks mesh sensitive. No fatigue ranking,
safe speed or minimum hot clearance follows.

Reports retain raw maxima and solver file hashes. Rotation/modal logs are published
with LF endings and no trailing whitespace; before/after hashes for this sole
normalization are [recorded](results/runtime/text-normalization.json). Solver
report hashes still identify archived originals. Complete fields and large inputs
remain in a verified private archive without the scan. The mechanical uncertainty
budget is an initial snapshot; its historical 22-cell CFD entry is superseded for
the current state by the CFD reports and this validation status. Percentiles are
node weighted, not volume weighted. Images show actual calculated nodal fields
at undeformed positions without clipping. Rotation prestress, gyroscopic effects,
bearings/contact, temperature and aerodynamic loads are excluded.

![R0 CalculiX fields](results/mechanics/R0-fields.png)

![V5 CalculiX fields](results/mechanics/V5-fields.png)

V2 is also calculated under the same assumptions with the original structural
mesher: 33219 and 48699 C3D10 elements, positive Gauss4 Jacobians and volume
checked against CAD. The [six R0/V5/V2 results](results/mechanics/three-variant-comparison.json)
retain both grids. V2 gives Umax 0.493745 / 0.497753 mm, radial extension
0.213118 / 0.215046 mm and first mode 377.033 / 375.642 Hz. Between grids:
Umax +0.81%, extension +0.90%, f1 −0.37%; nodal peaks 202.942 / 205.291 MPa
(+1.16%), without local convergence evidence. Against R0 on the finer grid:
mass −0.10%, displacement −2.39%, f1 −0.096%. The [render](results/mechanics/V2-fields.png)
uses every actual node, complete maxima and undeformed coordinates; it represents
neither failure nor alloy validation.

![Calculated V2 mechanical fields](results/mechanics/V2-fields.png)

## Aerodynamics and CFD admission

The scalar blade element model is a screening method. Its assumed polars are
clipped on 100% of R0/V1/V2 sections, so it cannot rank 42° against 36° pitch.
Scalar flow sensitivity to ±11% scale is about −14.9% / +15.5%.
No flow improvement is demonstrated.

The fluid domain reconstructed directly with OCC retains the same rotor and
housing interior. The best initial mesh passed the standard check but failed the
extended check: 22 cell determinants below 0.001. The independent formula
reproduces exactly the 22 IDs. Convex unions fail at small local concavities;
no partial union was applied. Refining diagnosed neighbourhoods through exact
nine-blade symmetry resolves the defect without changing CAD or thresholds:
148373 cells, minimum 0.00232225, maximum non-orthogonality 72.903°, maximum
skewness 0.9801. Both independent checks pass. Discrete volume differs from CAD
by about 0.025%; this does not establish metrological fidelity to a real part.

The [frozen protocol](parameters/reference-flow-protocol.json) defines the
6000 rpm reference before solving: air ρ = 1.2 kg/m³, ν = 1.5×10⁻⁵ m²/s,
upper inlet at zero total pressure, lower outlet at zero static pressure, MRF +Z,
expected flow −Z. The model is steady incompressible SST with first order
convection. Residuals, mass balance, flow stability and torque stability must all
pass. Wall layers, aerodynamic mesh independence and an installed engine remain
absent. The first 200-iteration pilot terminates normally but fails frozen
residual criteria; its measurements are not admitted performance. The separate
600-iteration continuation preserves conditions and thresholds and passes all
frozen criteria: mean outgoing flow 1.23587 m³/s, rotor torque −5.25296 N·m,
corresponding mechanical power 3300.53 W. These are conditional outputs of the
isolated model; no improvement is proven. Maximum calculated local Mach is about
0.383: compressibility sensitivity requires checking alongside wall resolution
and mesh independence. The [200](results/cfd/reference-flow-200-summary-complete-fields.json)
and [600-iteration reports](results/cfd/reference-flow-600-summary-complete-fields.json)
retain criteria, checked fields and measurement hashes.

The [36° V2 variant](V2-assembly.step) retains other R0 parameters
([exact parameters](parameters/V2.json)). Its first two attempts fail the extended
check: 36 cells / 22 faces, then 51 cells / 15 faces. These failures are retained.
Diagnosis finds nine 0.176 mm edges, against a 1.278 mm minimum for R0. CAD was
not repaired: a healing attempt changed volume and was rejected. Local resolution
of these short edges with an explicitly reduced minimum size lets V2 pass both
unchanged checks: 223300 cells, minimum determinant 0.0021815, maximum
non-orthogonality 72.411°. The [reports](results/cfd/V2-common-h7-mesh-report.json)
and [gate](results/cfd/V2-common-h7-independent-mesh-gate.json) trace this recovery.

At 600 iterations, [V2 passes frozen criteria](results/cfd/V2-common-h7-flow-summary.json):
flow 1.14659 m³/s, torque −3.83969 N·m, power 2412.55 W. R0 was then recalculated
with the same spatial size fields and 0.015 mm minimum: 262047 cells, both gates
pass and [600 iterations admitted](results/cfd/R0-common-h7-flow-summary.json),
flow 1.23472 m³/s and power 3303.89 W. This establishes a comparison at the same
pressure conditions and meshing rules, not mesh independence. V2 reduces both
flow and power; flow/power is a screening indicator, not efficiency or proof of
better installed engine cooling.

The finer common grid reduces overall size from 7 to 5.6 mm. Its first R0 mesh
(476657 cells) fails the extended check: three cells at blade/web roots and four
faces with insufficient interpolation. Their positions and nine symmetry images
define the [additional local recipe](parameters/common-grid-refinement-fine-repair1.json)
without changing CAD or thresholds. [Refined R0](results/cfd/R0-common-h5p6-independent-mesh-gate.json)
has 594940 cells and both gates pass. An initial 300-iteration batch reaches its
570 s internal limit before its checkpoint and remains an archived failure.
Four planned 150-iteration batches, each bounded at 600 s, yield checkpoints
150/300/450/600; first restart times are checked (1/151/301/451).
The [native measurement cadence audit](results/cfd/measurement-cadence-audit.json)
withdraws historical fine R0 admission at 600 and 750. A global `writeInterval`
replacement changed the three flow/force functions from 1 to 150 along with
checkpoint cadence. The summarizer silently accepted two rows as a twenty-row
window. The 39 tables from 13 cases exactly match original hashes; no loss or
rewrite was found. Only the two common cases have required consecutive
measurements; eleven finer phases are undersampled. Pressure residuals and
complete fields remain independently usable. Earlier summaries remain unchanged
for audit, but their finer-grid admission and “last window” labels are superseded
by this audit and the [corrected comparison](results/cfd/matched-grid-comparison.json).

Fine V2 at [600](results/cfd/V2-fine-150steps-phase600-summary.json) and
[750](results/cfd/V2-fine-continuation750-summary.json) still exceeds the pressure
threshold: 1.2306×10⁻⁴ and 1.2442×10⁻⁴ against 10⁻⁴. Paired sensitivity reduces
relaxation from 0.25 to 0.15 without changing criteria, mesh or physics.
[V2 at 900](results/cfd/V2-fine-pressure015-900-summary.json) still fails pressure
(maximum 1.5667×10⁻⁴). [R0 at 750](results/cfd/R0-fine-pressure015-750-summary.json)
has compliant residuals, but admission is withdrawn for a missing measurement
window. No finer-grid ranking or fine/common difference is accepted.

| Case | Cells | Admission / final iteration | Mean Q over final 20 iterations, m³/s | Mean input P, W | Final port Δpt, Pa | Final port energy ratio, unqualified |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| R0, common 7 mm grid | 262047 | admitted / 600 | 1.234720 | 3303.895 | 1960.672 | 0.732745 |
| V2, common 7 mm grid | 223300 | admitted / 600 | 1.146586 | 2412.549 | 1541.226 | 0.732475 |
| R0, fine 5.6 mm grid, relaxation 0.15 | 594940 | **admission withdrawn** / 750 | unavailable | unavailable | 1998.375 | 0.740207 |
| V2, fine 5.6 mm grid, relaxation 0.15 | 453496 | **not admitted** / 900 | unavailable | unavailable | 1569.574 | 0.744361 |

Final finer-grid fields are snapshots, distinct from means or admission: R0
Q = 1.230172 m³/s and P = 3321.160 W; V2 Q/P are recorded in the corrected
comparison. The [historical comparison](results/cfd/matched-grid-comparison-sampling-v1-historical.json)
is retained as superseded evidence without current admission authority.

On the admitted common pair, V2 reduces Q by 7.14%, P by 26.98% and Δpt by
21.39%. Q/P rises 27.17%, but the port energy ratio varies by −0.037% relative:
this does not demonstrate superior efficiency. Conditions describe an isolated
fan with imposed zero gauge pressures and no engine resistance curve. Neither a
final installed cooling tradeoff nor mesh independence is established.

The [pressure diagnosis and next protocol](PRESSURE_FOLLOWUP.en.md) prepare bounded
numerical discrimination, then Q–Δp–P points at a common objective.
[Executed D1](D1_EXECUTION.en.md) remains incomplete: control960 is not admitted on p;
the strict branch stops after29 iterations within the initial budget. At that
historical stage, D2 batches had not launched and awaited a coordinated window.

The balance independently reconstructs pressure torque from surfaces and checks
rotor wall velocity against Ω × r. At 6000 rpm, Ω = 628.319 rad/s, blade tip speed
86.394 m/s and tip Mach 0.252 with assumed sound speed 343 m/s. Local absolute and
rotor-relative Mach are also analyzed; tip Mach alone does not qualify
incompressibility. The [cross-checked R0 balance](results/cfd/R0-common-h7-balance-v4.json)
retains actual exported pressures and fluxes. Inlet total pressure and outlet
static pressure are zero gauge; calculated outlet total pressure includes axial
kinetic energy and swirl. Δpt uses signed-flux weighted port means and energy is
integrated from final fields. Only common-grid Q/P means use a complete
twenty-measurement window; finer-grid means are unavailable. Local outlet
backflow must be distinguished from net flow.

Reconstructed absolute flux through the stationary housing is about
1.3 to 3.6×10⁻¹² m³/s (numerical rounding); relative MRF fluxes are not leaks.
Gross outlet backflow is 0.1268 / 0.1318 m³/s for common V2/R0, separate from
net flow. Torque × Ω confirms input power, but the simplified mechanical balance
remains unclosed. Calculated mean viscous/turbulent transfer lacks qualified
closure of turbulent transport, work and numerical losses. The port energy
ratio must not be presented as physical efficiency. Closure deficit after this
transfer remains 25.29% / 25.57% of power for common V2/R0 and 23.53% for fine R0.
Face `phi` in MRF is relative to the rotating frame; absolute flux reconstruction
distinguishes it from a stationary wall leak. High local speeds warrant
compressibility sensitivity. The isentropic calculation bounding this assumption
is ideal screening, not a simulated density correction:
[NASA isentropic relations](https://www.grc.nasa.gov/www/k-12/airplane/isentrop.html).

## Additive manufacturing

[Geometric screening](results/lpbf/lpbf-screen.json) uses the actual R0 rotor STL.
Explicit scenario: assumed AlSi10Mg powder, unselected LPBF machine, assumed
250 × 250 × 300 mm envelope, 10 mm margins on each side, 50 µm layers and 45°
overhang criterion. Of ten poses, only the vertical pose at 45° azimuth fits with
margins. Sections of 1105 layers in the horizontal pose are calculated; integrated
volume differs from STL by 0.111%. The support proxy adds vertical columns with
possible overlap. It is neither generated supports, laser paths nor a
thermomechanical simulation.

A shrinkage/release mechanical comparison has been executed on **R0 and V5**,
distinct from older studies on another geometry. The [12 cases](results/lpbf/manufacturing-comparison.json)
reuse checked C3D10 and generic elasticity E = 70 GPa, ν = 0.33. The contraction
field is `ε* = −a(0.5 + 0.5s²)(I − 0.7nnᵀ)`; amplitude `a`, normalized height `s`
and build normal `n` are expressly assumed. CalculiX initializes initial strain
storage then uses `INITIAL STRAIN INCREASE`; no temperature-dependent plasticity
law or calibrated inherent strain is invented. Attachments are lowest surface
nodes in raster cells, fully fixed: rigid column proxies without support solids
or thermal contact. The second state releases them and retains six gauge
constraints to remove rigid motion.

| Variant / scenario, amplitude 0.001 | Maximum released displacement (mm) | Maximum release increment (mm) | Maximum deformation after rigid motion removal (mm) |
|---|---:|---:|---:|
| R0, diagonal edge pose, 5 mm raster, 4.5 mm size | 0.096015 | 0.196200 | 0.093672 |
| V5, same conditions | 0.096054 | 0.180054 | 0.093714 |
| R0, flat, build +Z, 5 mm raster | 0.214339 | 0.209967 | 0.130655 |
| V5, same conditions | 0.211377 | 0.207043 | 0.129899 |
| R0, diagonal edge pose, 3.6 mm size | 0.098434 | 0.190741 | 0.093502 |
| V5, same conditions | 0.098447 | 0.175210 | 0.093656 |

The native uniform contraction analytical benchmark passes. Zero amplitude gives
exactly zero displacement and stress; doubling amplitude reproduces displacement
to about 1.6×10⁻⁶ relative. Changing raster 5 → 10 mm increases release increment
but leaves the final elastic state unchanged: the prescribed field is process-path
independent and the model does not simulate support-induced plastic/thermal
evolution. This limits the method; it does not validate a support strategy.

Maxima after rigid motion removal vary by 0.18% (R0) and 0.06% (V5) on the finer
mesh while nodal RMS changes 5.27% and 7.38%. Attachments change from 518 to 521
nodes: this combines mesh and proxy sampling sensitivity without proving complete
independence. Final released displacement is almost identical for R0/V5; V5
reduces the release increment about 8.23% in the reference scenario. Attached
elastic peaks of 720/661 MPa concentrate at point attachments and are neither
physical process stresses nor manufacturing allowables.

![R0 shrinkage, actual native fields](results/lpbf/R0-manufacturing-release.png)

![V5 shrinkage, actual native fields](results/lpbf/V5-manufacturing-release.png)

The qualification review is prepared in English in the
[BLT manufacturer dossier](MANUFACTURING_REVIEW.md). BLT in Xi'an is the review
target communicated by the coordinator; no machine, material, condition, recipe
or service is automatically selected. The commercial AlSi10Mg/S400 case documents
a capability, not this rotor. Thermal calibration, layer activation, laser paths,
porosity and microstructure are not simulated. Manufacturing remains **unvalidated**:
workshop data, drawings/tolerances, calibration, dimensional measurements, NDT/CT,
coupons, treatment and physical tests are required. Manufacturer acceptance and
in-service rotor qualification are separate decisions. No order is placed.

## OpenUSD and Omniverse

[Comparative scene](omniverse/studies.usda), [R0](omniverse/R0.usda),
[V5](omniverse/V5.usda). Coordinates come from actual CAD tessellation without
visual cutting: eight meshes per model, +Z/+X axes, `metersPerUnit = 0.001`,
visual aluminium `UsdPreviewSurface`, hashes and parameter/result links.
The scene separates the two configurations only for comparison.

Parsing, composition, closed topology, units and material binding are verified in
OpenUSD 25.11; 24 generic validators run without findings. The Sdr shader rule is
blocked by missing `shaderDefs.usda` in the existing USD runtime and remains
explicitly unvalidated. No NVIDIA GPU runtime, RTX rendering, SimReady
qualification or physical twin correlation is established. The asset solves no
equations; external calculations remain linked separately.

The [release scene](omniverse/manufacturing-studies.usda) contains actual released
C3D10 boundaries: 40480/41060 nodes, quadratic faces subdivided into linear
triangles; every edge has two opposite orientations, areas are positive, and CAD
volume differences are 0.0021% / 0.0014%
([R0](results/lpbf/R0-native-boundary-verification.json),
[V5](results/lpbf/V5-native-boundary-verification.json)). Units are metres, +Z,
deformation scale 1, with node IDs and displacement vectors retained. Every
coordinate is [checked in text](results/lpbf/field-export-authored-coordinate-verification.json)
against native fields; maximum decimal error is about 5×10⁻⁸ mm. Independent
checking of every value actually loaded as OpenUSD `point3f` measures at most
7.63×10⁻⁶ mm ([R0](results/lpbf/R0-USD-field-coordinate-verification.json),
[V5](results/lpbf/V5-USD-field-coordinate-verification.json)). This numerical
representation bound is not a manufacturing tolerance.
[Composition checks](omniverse/manufacturing-scene-validation.json) pass with the
same Sdr shader reservation. No validated process twin or SimReady asset follows.

## Reproduction commands

Use existing tools: build123d 0.13 / OCP 8, Gmsh 4.15.2, CalculiX 2.23, NumPy,
Matplotlib, Foundation OpenFOAM 13 and OpenUSD 25.11. Outputs must be new.
STEP timestamps and dependencies can change regenerated hashes; check volumes,
topology and parameters as well as hashes. Original meshers are retained to
reproduce report hashes: `build_analytical_mesh_original.py` (65df79b8) and
`build_analytical_mesh_netgen_original.py` (09acff31).

From this directory:

```sh
python source/verify_study.py
python source/build_analytical_system.py parameters/R0.json work/R0
python source/build_analytical_system.py parameters/V5.json work/V5
python source/render_analytical_system.py work/R0 work/R0.png --display-label 'R0 horizontal fan reconstruction study'
python source/build_analytical_mesh_original.py work/R0 work/R0-h3p6 --mode structural --size-mm 3.6 --rpm 6000
(cd work/R0-h3p6 && ccx rotation && ccx modal)
python source/summarize_analytical_fem.py work/R0-h3p6 work/R0-h3p6/summary.json
python source/render_analytical_fem.py work/R0-h3p6/summary.json work/R0-h3p6/fields.png
python source/screen_analytical_variants.py parameters/R0.json work/scalar-screen.json
python source/screen_lpbf_geometry.py work/R0 work/lpbf
python source/build_openusd_asset.py work/R0 work/R0.usda --label R0
python source/validate_openusd_asset.py omniverse/studies.usda work/USD-validation.json
python source/build_analytical_mesh.py work/R0 work/fluid --mode fluid --size-mm 7 --netgen --local-refinement parameters/targeted-refinement-symmetric.json
python source/prepare_analytical_cfd.py work/fluid work/CFD parameters/R0.json
```

The OpenFOAM gate and runner expect the case mounted at `/case` under existing
image `ghcr.io/cluster2600/3dprinting993-mesh-cfd@sha256:a1db60cbf61bbcca52c171e50cab01ed0b6ec860b227e7c5fc50f7b809659b4f`.
Run `source/run_analytical_cfd_gate.sh` first, copy the frozen protocol into the
case as `reference-protocol.json`, then use `source/run_reference_pilot.sh`.
The gate fails closed on any failed check. A mesh result is not a flow result.
The bounded runner limits each isolated job through affinity, nice, memory and
deadline; no unrelated service or process is modified.

The historical commands below describe undersampled finer phases. Corrected
helpers now separate checkpoints and telemetry; the summarizer rejects incomplete
windows. These commands do not authorize automatic V2 continuation. For
reproduction, place sources in a new calculation directory on the existing Linux
runtime, with recipe CAD directory names (`private-R0-v3`, `private-V2`) and JSON
recipes at its root. Names identify analytical studies; no scan is required.
Scripts call the bounded runner and reject another active container for this
study. `gate-local.sh` is an exact copy of `source/run_analytical_cfd_gate.sh`;
the MPI runner requires `run_parallel_pilot.sh` at the root. Check the four
physical cores locally with `lscpu` before reusing the CPU set.

```sh
# In the new calculation directory; Foundation image already present.
python run_matched_cfd.py R0-common-h5p6-repair1 private-R0-v3 common-grid-refinement-fine-repair1.json --size-mm 5.6 --minimum-size-mm 0.01 --mesh-only
python run_existing_grid_sensitivity.py cfd-R0-common-h5p6-repair1 R0-fine-150steps --protocol-template V2-common-h7-protocol.json
python run_matched_cfd.py V2-common-h5p6-repair1 private-V2 common-grid-refinement-fine-repair1.json --size-mm 5.6 --minimum-size-mm 0.01 --mesh-only
python run_existing_grid_sensitivity.py cfd-V2-common-h5p6-repair1 V2-fine-150steps --protocol-template V2-common-h7-protocol.json
python continue_admitted_mesh_flow.py cfd-V2-fine-150steps-phase600 V2-fine-continuation750
python continue_admitted_mesh_flow.py cfd-R0-fine-150steps-phase600 R0-fine-pressure015-750 --pressure-relaxation .15
python continue_admitted_mesh_flow.py cfd-V2-fine-continuation750 V2-fine-pressure015-900 --pressure-relaxation .15
```

Scenario scripts use existing R0/V5 mechanical meshes `mesh-R0-h4p5`, `mesh-R0-h3p6`,
`mesh-V5-h4p5`, `mesh-V5-h3p6` and benchmark `unit-eigenstrain.inp`. Existing results
are checked before resuming; completed jobs are not rerun. New output directories
serve independent reproduction.

```sh
python build_manufacturing_scenarios.py
python run_manufacturing_cases.py
python compare_manufacturing.py . manufacturing-comparison.json
python verify_native_benchmark.py manufacturing-analytic-benchmark native-verified.json
python export_manufacturing_bundle.py manufacturing-R0-diagonal-edge R0-manufacturing-native.npz
```

From the published directory, using NumPy/Matplotlib for export and existing
OpenUSD 25.11 for validators (`work/` outputs are new):

```sh
python source/render_manufacturing_fields.py results/lpbf/R0-manufacturing-native.npz work/R0-manufacturing-release.usda work/R0-manufacturing-release.png --label R0
python source/create_native_coordinate_reference.py results/lpbf/R0-manufacturing-native.npz work/R0-native-reference.json
python source/verify_usd_field_coordinates.py omniverse/R0-manufacturing-release.usda work/R0-native-reference.json work/R0-coordinate-check.json
python source/validate_openusd_asset.py omniverse/R0-manufacturing-release.usda work/R0-field-validation.json --expected-meshes 1 --meters-per-unit 1
python source/compare_matched_flow.py . work/matched-grid-comparison.json
python source/compare_mechanical_studies.py . work/three-variant-comparison.json
```

## Missing data for a validated part and twin

Independent specimen identity and scale; measured datums, interfaces and
tolerances; real fillets, material/condition and bearings; speeds, transients,
temperatures and fan/system curves; professional test plan. LPBF requires a
qualified scenario and process calibration. Omniverse requires the appropriate
runtime and profile validation, then physical correlation data. Catalogue statuses
remain unchanged: no part is released.

## Repository verification

GitHub CI ran `make check` successfully on the first CAD commit
2a9dba8cb3d06a3b2208c60a848dbe5f2a63899d. Local Linux checks encountered documented
incompatibilities in the [runtime report](results/runtime/repository-checks.json)
and are not claimed green. Final commit CI governs repository software, without
validating physics. Specialized checks above apply only to their artifacts and
assumptions. The coordinator merged PR129 into main
`8283155cb2b1275b0bf3e22d4d7459d4ac76b059`; these additions were isolated on a new
review branch. That historical delivery did not request automatic merging of the
new branch. See the [software evidence matrix](SOFTWARE_CHAIN.en.md).
[Private native evidence](results/runtime/native-archive-verification.json)
contains 1197 files (2.08 GB compressed), every member SHA-256 checked on the
runtime; the local transfer has exactly the same size and hash. Raw scan and MPI
field replicas are excluded; authoritative reconstructed fields, inputs, histories
and receipts are retained. The archive remains private; only its sanitized
receipt is public. All delivery jobs have ended; no unrelated process or service
was stopped or modified.

## D1C: current numerical state

The [single D1C calculation](D1C_EXECUTION.en.md), from the same checkpoint 900,
completes 60 iterations and passes original criteria with `consistent yes`:
maximum initial p residual 7.6223×10⁻⁵, decrease 45.01%. The control is still not
admitted and historical fine R0 admission remains withdrawn. Backflow is 10.76%
of net flow, local fields are sensitive, and compressibility/mesh/walls/installed
conditions remain unqualified. No cooling improvement or additional phase follows.
