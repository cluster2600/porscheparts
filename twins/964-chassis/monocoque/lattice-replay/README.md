# Graded lattice replay — 2026-10-28

The archived nine-cell graded probe had 32 exactly degenerate triangles. Two
new, unmodified raw meshes now pass the independent closed-surface topology
and CGAL self-intersection screens. An explicit subvoxel grid-phase shift
avoids the clipping degeneracy in these two runs. This is a diagnostic
continuation of [field-lattice](../field-lattice/README.md), **not a fitted
monocoque core, a new functional part or a strength calculation**.

The cell sizes and diameters still come from the frozen historical experiment.
Its stress demand came from the superseded, bending-locking S3 model described
in the [S6 correction](../README.md#s6-correction-2026-10-12-every-stiffness-redone).
Consequently the retained grading is useful for reproducing a geometry defect;
it is **not an accepted stress-based material distribution**.

## Results retained without repair

| Case | Voxel pitch (mm) | Raw triangles | Exact zero-area faces | Closed, oriented topology | CGAL intersecting pairs |
|---|---:|---:|---:|---|---:|
| Original global frame | 0.50 | 81,996 | 32 | Fail | Not run |
| Centred local frame | 0.50 | 81,996 | 32 | Fail | Not run |
| Original global frame | 0.25 | 328,044 | 144 | Fail | Not run |
| Centred local frame | 0.25 | 328,044 | 84 | Fail | Not run |
| Local frame with phase shift | 0.50 | 80,924 | 0 | Pass | 0, complete |
| Local frame with phase shift | 0.25 | 327,812 | 0 | Pass | 0, complete |

The global 0.50 mm replay reproduces the archived raw triangle coordinates
exactly. All six runs preserve the nine prescribed cell centres and pass a
native VDB field, voxel-pitch and translation-metadata round trip. No triangle
was deleted, welded by tolerance, smoothed or repaired. Exact-coordinate
indexing is used only by the independent inspection, without modifying STL.

Machine-readable evidence:

- [Frame/resolution replay](evidence/replay-audit.json), including all four
  rejected cases, source hashes and the unresolved interface survey.
- [Phase assessment](evidence/phase-assessment.json), including both candidate
  meshes and order-independent comparisons.
- [CGAL screen](evidence/intersections.json): CGAL 6.2.1 EPICK predicates on
  the stored mesh coordinates; an intact tetrahedron and two crossing triangles
  exercise the negative and positive controls before inspection.
- [Execution and retention receipt](evidence/execution.json): runtimes,
  dependency/source hashes and hash-verified local copies of all six raw runs.
- [Validation record](evidence/validation.json): six focused tests pass with
  each native program. Full local `make check` retains two failures in unchanged
  993 fan floating-point equality tests; the remaining make checks pass.
- The two candidate STL/VDB pairs are retained losslessly as
  `evidence/phase-{050,025}-raw.{stl,vdb}.gz`. Their decompressed SHA-256 values
  are checked against the assessment by the regression tests.

The old study and its evidence remain unchanged. The generated probe is
authored from repository parameters; no raw scan or proprietary manual is
included in this continuation.

## Frame, discretization and volume limits

The intended design remains the same nine 12 mm BCC cells, with the original
graded diameters and clipping envelope. F0 is millimetres, X forward, Y left,
Z up. The phase runs use a translation only:

```text
centre_F0 = (-1728, 708, 864) mm
origin_F0 = centre_F0 + voxel_pitch * (1/3, 2/5, 1/7)
point_F0 = point_local + stored_local_to_F0_translation_mm
```

Use the actually stored float32 translation from each receipt/VDB, not a
separately rounded reconstruction. STL does not store this frame. The change
moves the sampling grid relative to the intended solid; it does change its
discrete approximation. It is not a universal fix for PicoGK or a measured
surface tolerance.

The maximum symmetric nearest-neighbour **vertex-cloud** distances from the
global replay to the phase candidate are 0.395714 mm at 0.50 mm pitch and
0.217684 mm at 0.25 mm pitch. These are sampled-vertex distances, **not surface
Hausdorff bounds**. Global and centred-local replay clouds differ by less than
0.000075 mm. The first replay report also retains a 48 mm *array-index*
coordinate difference: raw triangle ordering changes between frames, so that
field is not a geometric distance. The phase assessment explicitly flags this
and supplies the order-independent metric.

PicoGK's reported volume changes with coordinate origin in these runs; the
underlying cause is not established. It is not used as mass evidence. An
independent float64 signed tetrahedral integration about the mesh bounding-box
centre gives 7,281.317 and 7,378.671 mm³ for the two phase candidates. Their
relative difference is **1.3194%** against the finer result. Two resolutions,
without an agreed convergence criterion, do not establish convergence.
Volume interpretation is conditional on a valid embedded closed surface; the
rejected meshes do not become valid by having a finite volume integral.

## What this unblocks, and what the body still needs

The accepted meshes can enter a later, separately specified meshing experiment.
They do not yet have a material, attachment, element-quality or mechanical
boundary-condition contract: `solver_ready=false`,
`manufacturing_authorized=false`. No new FEA, Qwen inference, fabrication
simulation, paid compute or vehicle qualification occurred in this replay.
Qwen proposals remain subordinate to independent geometry/physics checks.

| Next gate | Required evidence |
|---|---|
| Actual 964/993 attachment compatibility | Exact variant and measured bilateral XYZ, hole axes, mating faces, tolerances and uncertainties; separate 993 evidence |
| Tunnel and drivetrain packaging | Gear linkage through every gear and service access; for C4, shaft/flange/front-differential positions and swept envelopes |
| Comparable structural model | Corrected S6 baseline, convergence and equilibrated loads; ply/core/bond data and orientations; defined interfaces and load paths |
| Strength and durability | Layered stress/failure analysis, joint and insert checks, buckling, fatigue and physical correlation under an approved validation plan |
| Part and mould manufacture | Selected laminate/process, drape and cure data, tooling split/demoulding access, process simulation and inspection limits |
| Road/circuit acceptance | Professional engineering review, agreed physical tests and the applicable approval process; numerical checks alone are insufficient |

The [existing measurement plan](../../interface-measurement-plan.md) is the
working survey specification. Its 18 registered datums currently contain
**zero validated XYZ triplets; all 18 lack Z**. This is not a complete body
interface inventory. P12 is the **gearbox crossmember**, not rear suspension.
The 1,200 kg vehicle target does not specify axle loads, local mass attachment,
aerodynamic loads or suspension/inertial load cases. Unknowns remain unknown.

## Reproduce on the existing Mac installation

Run from the repository root. Outputs must be new directories/files. The
programs accept only the SHA-256-pinned archived report, and refuse overwrite.
The actual run used .NET SDK 10.0.402 targeting `net9.0`; PicoGK and all 59
ShapeKernel/LatticeLibrary source files match the archived execution hashes.
Managed/native runtime rebuild provenance is not newly established here.

```sh
study=twins/964-chassis/monocoque/lattice-replay
picogk_root=/Users/maxime/Developer/PicoGK
dotnet_exe="$picogk_root/sdk/dotnet"
python_exe=work/check-venv/bin/python

"$dotnet_exe" build "$study/Replay.csproj" \
  -p:LeapSources="$picogk_root/libraries" \
  -p:PicoGKAssembly="$picogk_root/runtime/PicoGK.dll" \
  -p:BaseIntermediateOutputPath="$PWD/work/replay-new-build/obj/" \
  -o work/replay-new-build/bin --configfile "$picogk_root/Workbench/NuGet.Config"
"$dotnet_exe" build "$study/Phase.csproj" \
  -p:LeapSources="$picogk_root/libraries" \
  -p:PicoGKAssembly="$picogk_root/runtime/PicoGK.dll" \
  -p:BaseIntermediateOutputPath="$PWD/work/phase-new-build/obj/" \
  -o work/phase-new-build/bin --configfile "$picogk_root/Workbench/NuGet.Config"
DYLD_LIBRARY_PATH="$picogk_root/runtime" "$dotnet_exe" \
  work/replay-new-build/bin/Replay.dll \
  "$study/../field-lattice/evidence/report.json" work/replay-new
DYLD_LIBRARY_PATH="$picogk_root/runtime" "$dotnet_exe" \
  work/phase-new-build/bin/Phase.dll \
  "$study/../field-lattice/evidence/report.json" work/phase-new
"$python_exe" "$study/audit.py" work/replay-new work/replay-new.json
"$python_exe" "$study/assess_phase.py" \
  work/replay-new work/phase-new work/phase-new.json
c++ -std=c++20 -O2 -I/opt/homebrew/include -L/opt/homebrew/lib \
  twins/m64-cylinder-head/source/wholebody/surface_intersections_cgal.cpp \
  -lgmp -lmpfr -o work/intersections-new
"$python_exe" "$study/intersections.py" \
  work/phase-new work/intersections-new work/intersections-new.json
DOTNET="$dotnet_exe" REPLAY_DLL="$PWD/work/replay-new-build/bin/Replay.dll" \
  "$python_exe" -m unittest discover -s tests -p test_964_lattice_replay.py -v
DOTNET="$dotnet_exe" REPLAY_DLL="$PWD/work/phase-new-build/bin/Phase.dll" \
  "$python_exe" -m unittest discover -s tests -p test_964_lattice_replay.py -v
```

The task-local Python environment uses Python 3.12.14, NumPy 2.2.6,
SciPy 1.17.1 and Matplotlib 3.10.8 for repository checks. The first replay
audit was executed with the existing Python 3.12.11 / NumPy 2.5.3 environment;
the phase and CGAL assessments used the task-local environment. Neither modifies
the Qwen training environment. Native runtime tests are optional in generic CI
and explicit in the commands above; pure numeric and retained-evidence tests
remain in the normal suite.
