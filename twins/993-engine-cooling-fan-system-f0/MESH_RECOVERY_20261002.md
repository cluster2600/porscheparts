# Blade and tip-clearance mesh recovery — 2 October 2026

This follows the [Qwen/PicoGK campaign](QWEN_CHAIN_20261002.md). The task is to
repair the fluid mesh and run a matched 36°/42° rotor comparison. Both repaired
meshes now pass standard and full extended OpenFOAM checks. The two flow solvers
are running; no converged flow result is reported yet.

## Geometry and scope

Both rotors originate from PicoGK. The 42° candidate is the previously recorded,
bounded proposal from the local fine-tuned Qwen workflow. Diameter, cup, hub,
vents, blade count and nominal thickness stay fixed for this comparison.

The computational rig is a 248 mm diameter, 360 mm long cylinder around the
nominal 245 mm rotor: 1.5 mm nominal radial clearance. Rotation is −3,000 rpm
about +Z. These are modelling assumptions, not measured Porsche interfaces.
The PMB alternator, its supports, shaft and installed cooling shroud are absent.
This study cannot establish airflow delivered to the engine or authorize a part
for manufacture or installation.

The [PMB 240 A listing](https://pmbperformance.com/products/high-output-240a-alternator-for-porsche-964-and-993-90-99),
rechecked on 2 October, identifies a Classic Retrofit unit with a custom
large-case Denso housing. It recommends a serpentine belt and tensioner for
the 240 A version. The [WOSP manufacturer flyer](https://www.wosperformance.co.uk/clientarea/files/downloads/Porsche%20911%20WOSP%20Alternator%20Flyer.pdf)
lists LMA339 as a 964/993 240 A alternator. Neither source supplies a dimensioned
housing or mounting drawing; the flyer alone does not establish that SKU as
the exact PMB item. Dimensions from the photographed 997 alternator must not
be substituted for the selected 964/993 unit.

WOSP's [LMA339/LMA498 spacer instructions](https://www.wosperformance.co.uk/ClientArea/files/Downloads/LMA339%20LMA498%20Spacer%20Instructions.pdf)
do provide axial spacer selections: 7 mm for the RS arrangement, 17 + 7 = 24 mm
for the stock dual-pulley hub, and 17 + 7 + 2 = 26 mm for an early 964 Turbo
housing. A separate bearing-side spacer must remain in place; its thickness is
not given. These stacks are not dimensions of the alternator body or a verified
shaft datum for this project. [Classic Retrofit's installation note](https://classic-retrofit.com/forum/index.php?/topic/2521-993-alternator-install/)
explains the inset-bearing compensation and specifies retaining the rear cone
because it distributes the alternator nut loads. The installed model must account
for these parts after confirming the actual alternator and pulley arrangement.

## Surface correction

The earlier heavily decimated triangulation contained narrow triangles.
`source/remesh_fan_surface.py` applies six iterations of PyMeshLab isotropic
remeshing, with a 0.8 mm target edge length and a 0.04 mm local distance limit.
An independent two-way sampling audit checks the result against the original
PicoGK STL. The local remeshing limit and sampled distances are **not** global
Hausdorff error bounds.

| Surface | Triangles | Minimum triangle quality | Relative volume change | Maximum sampled distances, mm |
| --- | ---: | ---: | ---: | --- |
| 36° control | 624,568 | 0.24938 | −0.00206% | 0.06362 / 0.05680 |
| 42° candidate | 618,286 | 0.26401 | −0.00228% | 0.06665 / 0.05086 |

Both exports are watertight, consistently oriented, single bodies, with no
self-intersecting faces detected by PyMeshLab. Minimum vertex-to-analytic-duct
radial clearance remains about 1.500 mm. PhysicsNeMo GPU audits independently
verify cell areas, finite normals and matching millimetre/metre exports; these
audits are not aerodynamic predictions.

## Volume-mesh diagnosis

The conforming Gmsh mesh preserves the rotor surface instead of decimating it
again. HXT generates tetrahedra; Netgen optimizes them in the original native
model in millimetres, before the metre export to OpenFOAM.

The 2.74-million-cell attempt passed standard OpenFOAM 14 checks but failed
extended checks: 7,865 low-determinant cells and 102 low-interpolation-weight
faces. Location extraction showed that most problem points were on the outer
wall away from the rotor. Fine wall triangles adjacent to much larger volume
cells were a principal defect; improving the blade surface alone was insufficient.

Making the wall fine everywhere while retaining a 12 mm far-field target also
failed. The successful recipe retains a 1 mm axial wall spacing and caps the
far-field volume target at 2 mm. It leaves only 15 low-determinant control cells
and 8 candidate cells plus one candidate interpolation-weight failure.

A first unrestricted fusion attempt introduced concave cells and was rejected.
The final repair selects **disjoint** adjacent cell pairs, preventing overlapping
merges from making large malformed groups. The control required 15 internal-face
removals followed by one more; the candidate required nine. OpenFOAM's native
`removeFaces` performs the topology changes. Both resulting meshes pass the
unchanged standard and full extended checks:

| Final mesh | Cells | Minimum determinant | Minimum interpolation weight | Maximum non-orthogonality |
| --- | ---: | ---: | ---: | ---: |
| 36° control | 8,182,775 | 0.00104216 | 0.0506669 | 78.3671° |
| 42° candidate | 8,170,973 | 0.00104393 | 0.0525804 | 79.0170° |

The actual rotor patches were extracted from the repaired OpenFOAM meshes. Both
remain watertight single bodies with consistent winding. Two-way sampled errors
against the remeshed surfaces are below 0.000004 mm; absolute volume changes are
below 0.000005%. This is a numerical surface-preservation check, not manufacturing
precision. Fluid-side normals point into the rotor and therefore give negative
signed solid volumes, as expected.

A parallel, shared 24-zone local-refinement experiment was generated as a fallback.
It is not the selected CFD mesh and has no accepted OpenFOAM result in this report.
All failed attempts are retained; quality thresholds were not lowered.

## Runtime and acceptance

Vast was provisioned through the approved API wrapper, without browser access.
The owned worker exposes 64 CPU cores with a 61.44-core cgroup quota, approximately 125 GiB RAM and an
RTX PRO 6000 GPU. Its quoted base rate was USD 1.4708888889/hour. The pinned
SimReady image passed its GPU smoke check; OpenFOAM Foundation 14 package
20260724 was then installed explicitly. OpenFOAM runs on CPU; PhysicsNeMo
surface auditing uses the GPU.

`source/run_reference_cfd.sh` now supports an explicitly supplied conforming
Gmsh mesh, converts rotor and duct patches to walls, and requires both standard
and extended `checkMesh` success before decomposition or the solver. The
existing snappyHexMesh path remains available. `--existing-mesh` supports a
repaired conforming case and reruns both checks before solving. Negative tests
verify that failed checks never start the solver in either import mode.

The intended comparison uses the same pressure boundary conditions, SST k–ω,
second-order velocity convection and numerical convergence windows. Flow and
shaft power are measured from OpenFOAM function-object histories. A run ending
at its iteration budget is not, by itself, convergence. Wall-layer qualification,
grid independence and physical bench validation remain outstanding.

The cold-start runs initially used SIMPLE with pressure relaxation 0.25 and
velocity/turbulence relaxation 0.5. A live switch to SIMPLEC was requested at
observed iterations 261 (control) and 259 (candidate), retaining the same linear
solver tolerances and two non-orthogonal corrections. Pressure relaxation became
1 and equation relaxation 0.7. Growing control residuals prompted a reduction of
all three equation relaxation factors to 0.5 on both cases, requested at observed
iterations 343 and 346. Control residuals continued growing, so both cases reverted
to the original SIMPLE dictionary at observed iterations 382 and 389. The request
iterations are not exact application times:
OpenFOAM reloads modified dictionaries asynchronously. Original dictionaries,
SHA-256 change journals and an independent iteration-200 checkpoint are retained.
Acceptance criteria were not changed.

The control's perturbed state did not recover promptly after reverting SIMPLE;
its large negative torque made that branch unsuitable for comparison. It was
stopped normally and retained as a rejected numerical attempt. A separate
`control-restart-flow` case restarts the independently preserved iteration-200
fields with the original SIMPLE settings. Checkpoint hashes and restart provenance
are retained. Failed-branch histories are not spliced into the restarted history.
The 42° case continues with the restored original SIMPLE settings.

The restarted control subsequently showed growing residuals and nonphysical
torque with the original component-wise `linearUpwind` convection too. Both
active cases therefore switched to `bounded Gauss limitedLinearV 1`, requested
at observed iterations 332 (restarted control) and 592 (candidate). This applies
a common vector limiter near steep gradients; it locally approaches upwind and
must not be described as uniformly second-order accurate. The mesh and acceptance
thresholds remain unchanged. See the Foundation
[numerical-schemes guide](https://doc.cfd.direct/openfoam/user-guide/fvschemes).

The vector limiter brought control torque back to a positive value. An added
boundary-flux diagnostic then detected substantial outlet return flow in the
42° checkpoint at iteration 600: `sum(abs(phi))` was 0.59526 m³/s, substantially
above its approximately 0.456 m³/s net flow. The fixed-static-pressure outlet
was therefore replaced with `totalPressure`, `p0 = 0`, on **both** cases. This
retains ambient static pressure for outflow and accounts for dynamic pressure
on incoming ambient air; it does not impose an outlet flow rate. See the
[Foundation boundary-condition definition](https://cpp.openfoam.org/v14/classFoam_1_1totalPressureFvPatchScalarField.html).

Both runs stopped normally and resumed from their saved fields at iterations
408 and 672. Native `foamDictionary` changed only the outlet entry in pressure
fields; serialized internal pressure values were verified identical in all 66
modified files. Original files, logs and change hashes are retained. The final
convergence windows must lie entirely in the new boundary-condition segments.
The generator now applies this ambient-reservoir boundary to future pilots and
records both net and absolute opening fluxes. Domain-length sensitivity is still
required before treating the rig as boundary-independent.

After the convection and boundary fixes, convergence remained slow. Independent
control/candidate checkpoints at iterations 800/1000 were preserved before a
more conservative SIMPLEC retry, requested at observed iterations 812/1083.
Pressure relaxation is 1 while velocity and both turbulence equations retain
0.5 relaxation. The previous 0.7 equation relaxation is not reused. Physical
boundary conditions, spatial schemes, linear tolerances and acceptance limits
are unchanged; the algorithm request and dictionary hashes are recorded.

The extended SIMPLEC runs still did not satisfy all integral windows and showed
renewed flow/torque fluctuations. They stopped and reconstructed normally at
iterations 1477 and 1753. Complete field checkpoints, dictionaries and histories
were preserved before a native `localEuler` pseudo-time trial. This follows the
installed OpenFOAM 14 `incompressibleFluid/pitzDailyLTS` tutorial: PIMPLE with one
outer iteration, two pressure correctors, `maxCo = 1`, smoothing coefficient 0.1
and maximum local time step 1. The two non-orthogonal correctors and existing
linear tolerances are retained. Algebraic under-relaxation is removed; the local
time derivative supplies damping. Geometry, rotation, boundary conditions,
turbulence model and spatial schemes are unchanged.

This is a warm-start experiment, **not a physical transient simulation**. Its
initial budget is 500 pseudo-time iterations per case, with earlier stopping
possible if the same integral windows pass. Any candidate result must then return
to `steadyState` and the saved SIMPLEC dictionary for a separate confirmation
segment. Passing a pseudo-time window alone does not qualify the comparison.

## Rotating-frame interface correction

The pseudo-time retry was stopped before acceptance to investigate a common
geometric defect in both rotating zones. Cell-centre box selection on the
unstructured tetrahedral mesh produced a ragged internal MRF interface. A native
OpenFOAM audit measured 43,445 / 43,507 interface faces, respectively, with
area-mean absolute rotation-normal velocities of 0.03526 / 0.03537 metres per
radian. At 3,000 rpm these correspond to approximately 11 m/s on an artificial
internal interface; maxima reach approximately 38.8 m/s. Neither old result is
accepted. This is a numerical-interface diagnostic, not measured physical flow.

For the **isolated rotor in the axisymmetric duct only**, fresh cases now assign
all fluid cells to the rotating frame. This removes the internal interface;
`MRFnoSlip` remains on the rotor and absolute `noSlip` on the stationary duct.
Both cases start from their original uniform fields, without reusing old-frame
`phi` or `Uf`. Mesh connectivity, geometry hashes, rpm, physical boundaries and
SST model are unchanged. Native audits confirm all 8,182,775 / 8,170,973 cells
belong to the respective rotating zones and zero internal interface faces.
Both meshes again pass standard and full extended checks. Fresh steady SIMPLEC
runs use the unchanged flow, torque and mass-conservation acceptance windows.

The shared runner now rejects a non-tangent internal rotating interface before
starting the solver. The full-domain method is **not applied to the non-axisymmetric
stationary alternator assembly**: that future calculation needs a conforming
local interface or an appropriate moving-mesh method. Duct faceting, wall
resolution, mesh/domain sensitivity and installed-assembly validation remain
unresolved. The two new calculations must still converge before comparison.

After the first 300 full-frame iterations, both cold starts remained monotonic
but slow. Complete iteration-300 restart fields and dictionaries were preserved.
At observed iterations 307 / 306, velocity, k and omega relaxation changed
from 0.5 to 0.7 in both cases; pressure relaxation stayed at 1. This is a matched
iteration-acceleration change, not a change to physical conditions or acceptance
thresholds. Each case records its timestamp and old/new dictionary hashes in
`relaxation-change.json`. These runs still require the full convergence checks.

## Verification

The repository's Python suite completed again after the interface correction and English presentation update:
3,264 tests, 153 skipped, no failures. The completed-short-run monitor regression
and focused runner checks are included. The new common-colour-scale rendering
check was separately run in the PhysicsNeMo environment and passed, including
rejection of clipped, zero and nonfinite ranges.
The additional imported-mesh rejection test also passed. The latest `make check` completed with exit status 0, including catalogue,
source, documentation and existing manufacturing-evidence checks. It does not
run a new physical printing test or qualify the fan manufacturing process.
The pushed correction separately passed the repository's GitHub
[check workflow](https://github.com/cluster2600/porscheparts/actions/runs/37021055598/job/110883928616).
The pressure-integral audit now accepts an explicit CUDA device. Its analytical
triangle self-check passed both on the Mac CPU and on the Vast GPU. This checks
the audit implementation; it is not an aerodynamic validation result.
The actual candidate pressure field saved at iteration 1753 was also exported
and integrated on CUDA. Relative force and moment errors against OpenFOAM are
3.89 × 10⁻⁷ and 4.47 × 10⁻⁷ respectively. This confirms the independent pressure
integration on a real field; that checkpoint still failed the flow/torque windows.
Its rotor-wall `y+` spans 0.0020–75.24, with a reported average of 14.90; the duct
average is 8.56. These diagnostics are retained in `log.yPlus-before-lts` and do
not qualify the wall resolution or replace a wall-layer/grid-sensitivity study.

Primary implementation references: [PyMeshLab filters](https://pymeshlab.readthedocs.io/en/latest/filter_list.html),
[Gmsh reference manual](https://gmsh.info/doc/texinfo/gmsh.html).

## Reproduction of the selected mesh

On the prepared Python runtime, use the remeshed rotor in millimetres:

```sh
python source/build_fan_tetmesh.py rotor-mm.stl new-mesh \
  --preserve-surface --resolve-gap --graded-interior \
  --algorithm 10 --optimize-netgen --far-wall-step 1 \
  --far-field-size 2 --threads 16
```

On the OpenFOAM 14 worker, compile `source/select_fan_merge_faces` with `wmake`.
The Foundation distribution's `applications/utilities/mesh/advanced/removeFaces`
utility was also compiled with `wmake` in this campaign.

Perform corrections only in a **new copy** of a case whose standard check passes.
Generate fresh sets with `checkMesh -allGeometry -allTopology -writeSets
-writeSurfaces`. If the only rejected criteria are low determinants/interpolation
weights, `selectDisjointFaces` writes candidate internal faces to `mergeSlivers`;
`removeFaces mergeSlivers -noFields` applies the change. Save each round's logs.
Before checking a modified mesh again, remove the two old generated error sets
(`underdeterminedCells`, `lowWeightFaces`) so that labels from the previous mesh
cannot be mistaken for current errors. An absent set is meaningful only after a
fresh complete check.

Do not infer acceptance from successful face removal or a geometry-only check.
Run standard and full extended checks, export and audit the actual rotor patch,
and only then run the repaired case with `run_reference_cfd.sh CASE
--existing-mesh`. The checked case archives, surface audits and file hashes are
the authoritative run inputs.

The checked inputs and meshing-attempt logs are available in the experimental
[evidence release](https://github.com/cluster2600/porscheparts/releases/tag/fan-cfd-mesh-recovery-2026-10-02).
Downloaded local files and GitHub's uploaded asset digests agree:

| Archive | SHA-256 |
| --- | --- |
| `checked-cfd-inputs.tar.gz` | `265ab1aa066c1b3278abc09f57b7f0cbc1c1426984c6a6fb223b67837ba5bf8f` |
| `mesh-recovery-attempt-logs.tar.gz` | `c7c08773fc26430569b0fc9220d171536882e6103794203117b125cb111a1356` |
| `rejected-lts-and-interface-evidence.tar.gz` | `1cf3873df6e465e75d89042f9a0cf5700f3366a2f3e66988d2c77819edb877ef` |
| `simplec-pre-lts-checkpoints.tar.gz` | `5426daad8fed5c2d891f57cdc32b59fedad297619d364216541be0f7c2fe6c5b` |
| `control-restart-and-rejected-branch.tar.gz` | `55b6793b8099325ab00947f8d936221996e085ff95661b6c7ec082a4f6cf1ed0` |

The input archive captures the initial solver setup before the SIMPLEC changes.
Runtime journals and the final dictionaries must accompany any reported result.
The restart archive contains the independent control checkpoint at iteration 200
and the rejected first control branch's final fields at iteration 418; neither
is a final airflow result.

The rejected-LTS archive preserves the final pseudo-time trial fields, complete
histories, interface diagnostics and the actual iteration-1753 pressure export.
It supplements the unchanged mesh archive and is not an accepted airflow result.
