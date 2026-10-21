# 935 complete-system continuation — October 22, 2026

The target remains the horizontal 935 reference installation, followed later by
the separate 993 adaptation. This continuation follows the root README and
PR #274: retained scan-derived geometry → authored PicoGK → independent geometry
checks → reference solvers → numerical acceptance → optimization and twin review.
It does not substitute a small Warp benchmark for the complete-system objective.
All new documentation is English; historical, hash-pinned records remain intact.

The [machine-readable record](complete-system-20261022.json) identifies sources,
inputs and results. Meshes, arrays, detailed cases, images and solver outputs
remain in the [private evidence repository](https://github.com/cluster2600/porscheparts-935-private).

## Geometry and assembly actually executed

The new [PicoGK composition source](../../../twins/935-horizontal-cooling-system-f0/source/picogk-assembly-refresh/Program.cs)
combines the corrected 0.6-resolution rotor with the existing observed drive,
provisional shroud and six-cylinder packaging context. It retains each input
file byte for byte and uses native `Mesh.Append` for the combined mesh. It adds
no inferred gears, bearing fits or engine mounting coordinates. The previous
coarser rotor is no longer the rotor displayed by this refreshed assembly.

The combined mesh has **12,603,066 triangles**. An independent chunked comparison
checks every coordinate and triangle order against the four inputs. The
[review/export program](../../../twins/935-horizontal-cooling-system-f0/source/review_refreshed_assembly.py)
then checks GLB and USD round trips without decimation, preserves component
identities and produces four opaque inspection views. The views were inspected.
The engine remains a two-bank, six-cylinder packaging hypothesis, not an exact
935 engine reconstruction. No 917 geometry is introduced.

All source coordinates remain uncalibrated scan units. The legacy export applies
0.001 to obtain metre-valued coordinates under **H-SCALE: one assumed millimetre
per scan unit**. USD units are explicit, but this conversion does not establish
physical calibration. Existing `*_mm_hypothesis` result names retain this assumption.

## Warp on the complete rotor

The [real-mesh adapter](../../../benchmarks/warp-geometry/mesh_review.py) uses
PR #274's unchanged kernel. Kali1 executed Warp 1.18.0 / NumPy 2.2.6 natively on
x86_64 against **1,322,970 rotor triangles and 6,000 observed-surface probes**.
There were no missed queries; maximum absolute error against independent
Trimesh point-to-triangle distances was **1.23647e-5 scan units**, below the
declared 1e-4-unit numerical tolerance. This is a software geometry check.

The first experiment is retained as rejected: it compared full-mesh queries
with an older reference calculated on a cropped target patch. That target-scope
mismatch produced a 1.77475-unit discrepancy. Rechecking the worst points
against the complete mesh isolated the mismatch; a fresh full-target reference
was calculated for all probes. The adapter now rejects cropped reference scope.
This numerical tolerance is unrelated to scanner accuracy or machining tolerance.

## Mechanical formulation experiment

The [independent pure-bending witness](../../../twins/935-horizontal-cooling-system-f0/source/bending_witness.py)
is a synthetic rectangular beam with Poisson ratio zero and analytically
integrated end traction `M*z/I`. Its exact displacement field is stated in the
source. Three identical mesh/load pairs compare C3D8 and C3D8I. All six native
CalculiX 2.23 solves pass force/moment balance. C3D8I tip error is below 1e-7
relative; C3D8 tip errors are approximately 92.6%, 75.8% and 43.9%.
This demonstrates bending behavior on the witness, not accuracy of the rotor.

The [rotor adapter](../../../twins/935-horizontal-cooling-system-f0/source/prepare_formulation_comparison.py)
changes only the C3D8 element header to C3D8I. Nodes, mesh, material, centrifugal
load and the assumed bore band remain identical. The earlier C3D8 1.35 case
was also solved with 2.23 and reproduced the previous displacement.

| Grid pitch, assumed mm | Formulation | Maximum displacement, assumed mm | Maximum von Mises, MPa |
|---|---|---:|---:|
| 1.35 | C3D8, new native baseline | 0.603618 | 188.371 |
| 1.35 | C3D8I | 0.632069 | 174.235 |
| 1.20 | C3D8I | 0.800331 | 204.773 |

All three complete-output audits pass reaction balance. These are conditional
AlSi10Mg, 6,000 rpm, fixed-bore, isothermal centrifugal cases with assumed scale
and elastic properties. C3D8I changes the result, but the displacement difference
between its two grids remains **26.62%**. It does not meet the 5% convergence
criterion. Neither formulation establishes an allowable stress, speed or fatigue
life. The next structural study must assess a surface-conforming quadratic mesh
and local thin-section resolution; measured blades will not be thickened to
force numerical acceptance. The [CalculiX manual, section 6.2](https://www.dhondt.de/ccx_2.15.pdf)
explains the element formulations and the limits of C3D8I, including torsion.

## Complete-surface checks at the retained pose

[FCL review source](../../../twins/935-horizontal-cooling-system-f0/source/review_surface_contacts.py)
builds BVHs from every original triangle, with no welding or decimation. Native
Python-FCL 0.7.0.11 on Kali1 passes three independent analytic fixtures before
evaluating all six component pairs. [FCL's Python documentation](https://github.com/BerkeleyAutomation/python-fcl)
describes its collision and minimum-distance interfaces.

| Surface pair | Result at the retained pose, in scan units |
|---|---|
| Observed drive / provisional shroud | No crossing; minimum distance 6.83367 |
| Observed drive / corrected rotor | No crossing; minimum distance 3.83430 |
| Rotor / shroud | No crossing; minimum distance 6.25830 |
| Engine context / rotor | No crossing; minimum distance 113.236 |
| Engine context / shroud | No crossing; minimum distance 33.3665 |
| Engine context / observed drive | Crossing; original triangle IDs retained privately |

The earlier annular bounding test's 1,190,558 drive/shroud candidates were not
1,190,558 actual intersections. The full surface test resolves that ambiguity.
The engine/drive crossing concerns a solid packaging placeholder whose real
mounting recesses and interfaces are unknown. It is preserved for resolution,
not silently cut away and not presented as a demonstrated clash on a real engine.
Surface separation does not test solid containment, all rotation phases, contacts,
thermal growth, deformation or mounting fit. The existing conservative radial
rotor/shroud sweep bound remains a separate, assumed-scale result.

## Vast lifecycle and reproducibility

The user authorized a rental. One attempt selected a qualified PicoGK/Python
image by digest at **$0.431852/h including 100 GB disk**, with a two-hour deadline,
$4 attempt ceiling and a retained $10 goal ceiling. Before SSH readiness, another
task's rental appeared in the account. The existing guard requires exclusive
inventory and destroyed this attempt. Its exact ownership and verified absence
are recorded. The other task's instance was not changed. No workload, CUDA or
Omniverse execution is credited to this rental; the dedicated PR #274 image was
not published or run. Account credit movement is not an attributed invoice.

No automatic relaunch bypasses this guard. Retry requires an available qualified
offer, a new attempt manifest/readiness receipt and satisfied lifecycle checks.
Results are saved on the Mac, mirrored to Kali1 and archived privately before
closing the batch. No paid instance belonging to this batch remains running.

Key commands, from the repository root, with new private output names:

```bash
source_dir=twins/935-horizontal-cooling-system-f0/source
python "$source_dir/bending_witness.py" prepare work/NEW-witness
python "$source_dir/prepare_formulation_comparison.py" PARENT PINS.json work/NEW-prepared
timeout --signal=TERM --kill-after=15s 1200s bash "$source_dir/run_candidate_fea.sh" \
  work/NEW-prepared/rotor.inp DECK_SHA256 work/NEW-solved
cp work/NEW-solved/ccx.log work/NEW-solved/log.rotor
python "$source_dir/assess_mac_fea.py" work/NEW-prepared work/NEW-solved work/NEW-assessed
python benchmarks/warp-geometry/mesh_review.py CASE.json --device cpu --repeats 3 --output work/NEW.json
dotnet run --project twins/935-horizontal-cooling-system-f0/source/picogk-assembly-refresh \
  -p:PicoGKAssembly=PINNED_DLL -- CASE.json CASE_SHA256 work/NEW-native
python "$source_dir/review_refreshed_assembly.py" review work/NEW-native RECEIPT_SHA256 work/NEW-exports
python "$source_dir/review_surface_contacts.py" work/NEW-native RECEIPT_SHA256 work/NEW-surfaces.json
```

The solver log alias `log.rotor` must be an identical copy of `ccx.log` before
the unchanged full-output audit. Linux solver/test execution uses a native file
system, not a WSL shared mount. Exact versions, wheel/package identities,
cases, logs and hashes are retained. Keep the native PicoGK library directory
on the platform's loader path when running the C# composition.

The first Linux test snapshot lacked a Git index and inherited a group-writable
umask. Its failures are retained. The snapshot was initialized as a local Git
repository, its own permissions corrected, and subsequent tests use `umask 022`.
Kali1's system .NET SDK was 6.0; a later build test correctly refused a net9.0
target. SDK **9.0.317** was installed in an isolated study folder after checking
the downloaded tarball against Microsoft's official release SHA-512. These are
environment corrections; no test or engineering threshold was relaxed.

## Completion audit for the original objective

| Required outcome | Current evidence and remaining work |
|---|---|
| Exact 935 installation and scale | Family known; exact donor/engine, two independent calibration dimensions per scan and measured mounting datums remain unresolved. |
| Editable reconstruction | Native C#/parameters, observed surface fits and analytical hub/shaft portions exist. Hidden interfaces, complete BRep parts, fits and tolerances remain open. |
| Full mechanism and BOM | Seventeen interface contracts exist. Gear teeth/ratio, bearings, retainers, seals, pulley/belt definition, lubrication and engine fasteners still need specimen-specific evidence. |
| Assembly verification | Corrected rotor integrated; all six surface pairs checked at one pose. Engine-context crossing, solid occupancy, motion, elastic and thermal clearance remain unresolved. |
| Airflow characterization | No accepted curve for this geometry. Prepare the full rotor/casing case, three meshes, stationarity and mass-balance checks; do not transfer R0/V2/S1 curves to this rotor. |
| Structural/material qualification | New formulation diagnostic completed; convergence still fails. Contacts, modal/prestress, pressure/thermal loads, process-matched AlSi10Mg/WE43/Ti-6Al-4V properties and fatigue remain open. |
| Optimization and PhysicsNeMo | No accepted reference dataset yet. Keep direct solver verification before OpenMDAO coordination or surrogate ranking. |
| USD/Omniverse twin | Geometry exports and round-trip checks pass. Physical joints, mass/inertia, operating results and RTX review remain separate unfinished work. |
| Fabrication package and bench | No manufacturing release. Complete datum/tolerance drawings, process/inspection/assembly requirements and professional review; then execute the [bench protocol](BENCH_PROTOCOL.md). |

The complete-system goal remains active. A successful mesh export, synthetic
witness or code check does not close the missing mechanisms or fabrication gates.
