# 935 rotor: conforming volume and native structural studies

This continues the [complete-system work](COMPLETE_SYSTEM_20261022.md) through
the [root README's software chain](../../../README.md#software-chain-qwen-and-picogk):
retained PicoGK geometry, independent mesh checks, CalculiX, then numerical
acceptance. The target remains the horizontal 935 installation. Generic mesh
arithmetic reused from other programs imports no other engine geometry.

The [machine-readable record](conforming-rotor-20261022.json) pins the programs,
inputs and numerical receipts. Detailed meshes, solver decks, arrays, rejected
attempts and images remain in the private 935 evidence repository. This is an
uncalibrated centrifugal study, not a manufacturing release.

The [sealed private core archive](https://github.com/cluster2600/porscheparts-935-private/releases/tag/conforming-rotor-20261022-core)
contains 7,587 entries in a 1,046,005,408-byte tarball. Every archived file was
stream-verified; the Kali1 mirror and all three GitHub asset digests match.
The separate 48 GiB quadratic retry was excluded while running, so it requires
its own later evidence snapshot. No new rental was created in this continuation;
the account's other tasks were left untouched when the existing exclusive
Vast preflight guard could not arm.

## Geometry transported without a replacement proxy

The retained corrected PicoGK rotor has 661,475 indexed vertices and 1,322,970
triangles. `prepare_conforming_surface.py` checks every triangle coordinate and
its order against the native binary STL, writes a full TetGen surface and
retains the original boundary. No simplification, rescaling, closure or smoothing
is performed. An analytical unit tetrahedron qualifies the mesher invocation.

Native TetGen 1.6.0 on Kali1, with `-pYMQzC`, produces 661,495 vertices and
**2,116,345 C3D4 cells** in 14.67 seconds. The extra 20 vertices are internal.
The complete boundary retains an exact coordinate/triangle bijection. Every
cell is tested using exact integer arithmetic on the stored floating-point
coordinates: zero negative cells, zero flat cells. Face incidence and adjacency
give one connected volume, no nonmanifold faces and no missing/extra boundary
triangles. Its volume differs from the input surface by less than 8e-16 relative.

These checks establish topology and numeric transport. They do not establish
element quality or physical fidelity. The all-cell quality report finds a
minimum mean ratio of 0.000178768 and a maximum Jacobian condition number of
316,091. Thin and stretched cells remain; no acceptance threshold was invented
after seeing them. A positive Jacobian is insufficient for a converged stress.

## Matched linear and quadratic preparations

`prepare_conforming_fea.py` generates C3D4 and C3D10 decks from the same parent
tetrahedra. The quadratic deck shares edge midpoints in CalculiX order and has
4,100,825 nodes. It does not replace the surface by a stepped hexahedral grid.
Every serialized quadratic cell passes a whole-simplex Jacobian perturbation
bound. The complete geometric transport bound is below 2.67e-14 scan units;
the 1e-9 budget is numerical, not a scanner or machining tolerance.

Both cases retain the earlier **assumptions**: one millimetre per scan unit,
AlSi10Mg elastic properties (70 GPa, Poisson ratio 0.33, density 2,670 kg/m³),
6,000 rpm about the retained Z axis, and all translations fixed in an annular
volume band of radius 11.4619 and half-width 1.5 assumed mm. The band is not an
identified bearing fit. Pressure, thermal loading, contact and fatigue are absent.

## Solver qualification and the Mac crash

The existing Linux CalculiX 2.23 solves the full C3D4 deck successfully.
Homebrew's arm64 2.23 passes six small bending witnesses but crashes on the
same full deck in `I2Ohash_insert` during SPOOLES factorization. The failed
attempt, initial binary identity and relevant crash symbols are retained.

The author publishes a [SPOOLES correction for large input decks](https://www.dhondt.de/ccx_2.23.SPOOLEScorrection.tar.bz2).
`build_ccx_macos.py` verifies the three upstream archive hashes, applies this
official correction and the documented platform compilation adjustments in a
fresh private tree. It preserves original source fragments and does not replace
the installed Homebrew binary. The initial build refusal is also retained:
expected replacement counts were incorrect; only the void function's return
is changed, preserving the pointer-returning thread function.

The patched build passes the same six bending controls and completes the same
full C3D4 rotor deck. Linux and Mac maximum displacement are both **0.2718113
assumed mm**. Across every nodal displacement component, the largest printed
difference is 1e-7 assumed mm; the largest difference in element peak von Mises
is 1.38e-5 MPa. This qualifies this runtime/deck comparison, not every solver mode.

## Reaction audit: RF is not the support reaction alone

CalculiX's [NODE PRINT documentation](https://www.dhondt.de/ccx_2.15.pdf)
defines RF as external nodal force, including applied distributed loads. The
centrifugal load therefore contributes directly at constrained nodes too.
Treating printed RF as reaction alone initially failed the independent balance;
that rejected assessment and its source are retained.

`assess_conforming_fea.py` subtracts the consistent centrifugal nodal loads at
the constrained nodes. It follows the pinned 2.23 `linstatic.c`/`e_c3d.f`
quadrature: one point for C3D4, four points for C3D10. A translated analytical
unit tetrahedron is solved independently in both formulations. These controls
distinguish centroid-only moment integration from the exact continuum moment
and verify the RF correction without fitting it to the rotor.

The complete C3D4 output audit checks 661,495 displacements, every support-node
force and all 2,116,345 integration points, rejecting duplicates, missing values,
nonfinite values or changed inputs. Both native rotor solves pass discrete
force and moment balance at relative errors below 1e-9. The one-point continuum
moment discrepancy remains separately reported (1.57e-5 relative).

The conditional mass is **1.14988 kg** at the assumed scale/density. Peak von
Mises is **1,044.28 MPa**; the 95th percentile of element peaks outside radius 25
assumed mm is **28.8925 MPa**. The peak is not an allowable stress result:
the clamp is hypothetical, poor-quality cells remain and mesh convergence is
not established. Linear/quadratic disagreement is a formulation diagnostic,
not an h-refinement convergence study. No operating speed is approved.

## Quadratic resource limit and rejected iterative shortcut

The first full C3D10 direct attempt is terminated at the declared **32 GiB
physical-footprint limit**, after 547.84 seconds. macOS compression makes RSS
under-report its actual footprint; the private native `proc_pid_rusage` monitor
therefore supplements the process-group RSS/time guard. The worker exits on
SIGTERM. No displacement or stress result is accepted from this attempt.

The built-in iterative Cholesky solver was tested on the six independent
bending cases before any full rotor launch. Four cases fail the unchanged
equilibrium criteria, despite reporting `Job finished`. The 2.23 source
`preiter.c` fixes its relative tolerance at 1e-4. This path is rejected; no full
rotor is credited to it and no validation threshold is relaxed. The experimental
adapter and its failed controls are retained privately, outside the accepted
workflow. A separate direct attempt may use more of the existing Mac's memory;
it needs its own execution, footprint and complete-result audits.

## Reproduction

Use new private output folders for every attempt. `CASE.json` contains pinned
private input paths and hashes; it is archived with the corresponding execution.
Source coordinates stay in uncalibrated scan units. Solver units are explicitly
N–assumed mm–tonne–s. The public receipt does not expose the source scans.

```bash
source_dir=twins/935-horizontal-cooling-system-f0/source
python "$source_dir/prepare_conforming_surface.py" CASE.json work/NEW-surface
# Run the pinned TetGen executable on rotor.smesh with -pYMQzC,
# retaining its command, input/binary hashes, exit and raw files in execution.json.
python "$source_dir/import_conforming_volume.py" \
  work/NEW-surface work/NEW-meshed work/NEW-volume
python "$source_dir/prepare_conforming_fea.py" FEA_CASE.json work/NEW-prepared
python "$source_dir/run_conforming_study.py" \
  work/NEW-prepared/P1 work/NEW-solved --max-rss-gib 12 --seconds 1800
python "$source_dir/assess_conforming_fea.py" \
  work/NEW-prepared/P1 work/NEW-solved work/NEW-solved.execution.json work/NEW-audit
# On macOS, if reproducing the corrected runtime:
python "$source_dir/build_ccx_macos.py" PRIVATE_ARCHIVE_FOLDER work/NEW-ccx
python -m unittest discover -s tests -p 'test_935_conforming*.py' -v
make check
```

`run_conforming_study.py` calls the existing solver worker, pins its executable
and input, monitors only its owned process group, and terminates it on RSS or
wall-time limits. Execution success and numerical acceptance remain distinct.
The private control scripts also retain their source and result hashes.

Twelve focused tests pass on the Mac, including the public receipt check.
Kali1's earlier native `make check` snapshot runs **4,766
Python tests successfully, 371 skipped**, plus the subsequent ten- and
seven-test checks, then stops on Docker daemon permission for the manufacturing
container target. That is a partial local `make check`, not a full pass. No
permission, package-lock or manufacturing gate is bypassed.

## Remaining system work

Resolve thin-cell quality and demonstrate h-refinement convergence before
accepting structural performance. Then add modal/prestress, pressure and thermal
loads and process-specific material data. Prepare an independent full-rotor/
casing OpenFOAM case; no previous R0/V2/S1 curve transfers to this geometry.
OpenMDAO optimization and PhysicsNeMo training still need accepted references.

The 17 mechanical interfaces, dimensional calibration, hidden transmission,
bearings, lubrication, real engine mounting and the engine-context/drive crossing
remain open as listed in the complete-system audit. Native meshes and solver
agreement do not resolve those physical inputs. The 993 adaptation stays separate.
