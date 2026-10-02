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
The owned worker has 64 effective CPU cores, approximately 125 GiB RAM and an
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

## Verification

The repository's Python suite completed: 3,260 tests, 152 skipped, no failures.
The additional imported-mesh rejection test also passed. `make check` reached
the Docker-only LPBF audit and stopped because this Mac has no running Docker
daemon; the complete target is therefore not green.

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
