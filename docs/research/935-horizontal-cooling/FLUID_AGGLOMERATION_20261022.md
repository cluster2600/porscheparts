# 935 convex fluid-cell agglomeration — 2026-10-22

## Result and unchanged physical geometry

The [point-placement study](FLUID_POINT_PLACEMENT_20261022.md) left 448 failed
cell determinants. This continuation introduces mixed tetrahedral/polyhedral
air cells by joining **29 disjoint convex pairs**, reducing that count to
**419**. Nonorthogonal faces decrease from 866 to 862 and extended interpolation
failures from 26 to 25. Four native quality checks still fail. No new rotor PDE,
fan curve, strength result, material qualification or manufacturing claim is admitted.

The PicoGK design master is unchanged. All 199,423 mesh points remain byte-identical
in the native `points` file, and all 229,098 physical boundary triangles and
markers are retained. Only selected internal faces disappear. The final mesh
contains 890,720 original tetrahedra and 29 convex polyhedral unions, for a total
of 890,749 cells. This is an air-mesh change, not a modification of the fan.

The exact total volume remains the parent's PLC volume,
`0.05140958285727807 m³`, through a complete cell partition and exact local
volume equalities. The dimensional calibration of the scans remains unverified;
the numerical tolerances below are not machining tolerances.

## Exact pair selection and complete native addressing

The existing convex five-vertex cavity checker proves that each proposed pair
has positive parents, the required outer faces and an exact positive partition.
The reused finite-volume objective additionally requires fewer failed
determinants without worsening any selected failure count or severity. A batch
has disjoint affected neighbourhoods. This is a selection filter, not CFD admission.

The preceding 64-source pilot selected five pairs. After complete mixed-mesh
checks, one greedy pass examines all 345 multi-boundary source cells and selects
29 pairs. It also records 595 nonconvex candidate refusals, 29 quality refusals,
seven reserved neighbourhoods and six reserved source cells. These counts refer
to attempted neighbours or sources, as named; they are not all counts of unique
source cells. This pass is neither global optimization nor exhaustion of all
possible agglomerations. Both the pilot and full case start from the same
qualified tetrahedral parent; their selected pairs are not cumulative.

The [pair exporter](../../../twins/935-horizontal-cooling-system-f0/source/agglomerate_fluid_pairs.py)
independently verifies parent/proposal hashes, every native parent tetrahedron,
all coordinates and the complete boundary-marker bijection before writing a fresh
case. It maps native cell numbering explicitly rather than assuming it matches
the audit. For each pair it removes only the shared internal face, reverses a
retained face if owner/neighbour order changes, sorts internal addressing and
shifts patch starts while preserving patch contents. Synthetic tests exercise
reordered parent cells, a reversed retained face, empty neighbour lists, exact
unit volume and refusal of changed or incomplete inputs.

For each new cell, exact integer predicates check the oriented outer faces and
positive conical volume against the sum of its parent tetrahedra. Every parent
belongs to exactly one resulting cell. Unchanged cells retain their connectivity.
No boundary smoothing, coordinate relocation or new points are involved.

## Native and independent mixed-cell checks

The existing frozen, rootless and network-isolated Foundation 13 runtime reads
the mixed `polyMesh`, runs the original
`checkMesh -allGeometry -allTopology -meshQuality`, and writes native cell centres
and volumes through `foamPostProcess`. The original quality dictionary is
byte-identical. These are geometry/postprocessing commands, not a flow solve.
The primary implementations of
[writeCellCentres](https://raw.githubusercontent.com/OpenFOAM/OpenFOAM-13/master/src/functionObjects/field/writeCellCentres/writeCellCentres.C)
and [writeCellVolumes](https://raw.githubusercontent.com/OpenFOAM/OpenFOAM-13/master/src/functionObjects/field/writeCellVolumes/writeCellVolumes.C)
describe the geometry fields; the pinned runtime actually writes them as `C`
and `Vc`.

The [independent verifier](../../../twins/935-horizontal-cooling-system-f0/source/verify_agglomerated_fluid_mesh.py)
checks every retained face, its orientation, owner and neighbour, the complete
parent-cell partition, and all original boundary triangles/markers. It recomputes
each new cell's exact signed surface volume. VTK independently reads every
unchanged tetrahedron and every polyhedron's point/face connectivity.

Native double-precision centres agree with parent-volume weighting to a maximum
absolute difference of `3.11e-16 m`; maximum relative volume difference is
`1.91e-12`. The declared comparison bounds are `1e-12 m` absolute for centres
and `1e-9` relative plus `1e-21 m³` absolute for volumes. Exact partition checks
remain separate from those floating-point comparisons.

The installed VTK 9.6.2 OpenFOAM reader emits **float32 point coordinates**, even
with its 64-bit input setting enabled. The verifier checks the complete exact
forward conversion to that declared precision and computes VTK polyhedron
centroids against the converted geometry. Maximum display-coordinate rounding
is `7.46e-9 m` under the assumed scale. Solver coordinates remain exact native
doubles; their identity, volume and centre checks do not rely on the rounded VTK
points. Initial checks expecting a `V` filename or double VTK output are retained
as failed attempts; corrected, separately versioned checks pass.

| Case | Cells | Polyhedra | Failed determinants | Faces >70° | Weights <0.05 | Ratios <0.01 | Failed checks |
|---|---:|---:|---:|---:|---:|---:|---:|
| tetrahedral parent | 890,778 | 0 | 448 | 866 | 26 | 4 | 4 |
| five-pair pilot | 890,773 | 5 | 442 | 865 | 26 | 4 | 4 |
| full greedy pass | 890,749 | 29 | 419 | 862 | 25 | 4 | 4 |

Independent calculations from the complete serialized mesh and native geometry
fields reproduce all four extended quality counts. The native error-face union
falls from 1,077 to 1,064; full quality still rejects the mesh. A successful native
read, exact volume or lower defect count does not qualify airflow performance.

## Reproduction, preservation and next work

Use the existing numerical environment and a fresh private output directory:

```sh
export PYTHONPATH=twins/935-horizontal-cooling-system-f0/source
python "$PYTHONPATH/agglomerate_fluid_pairs.py" "$PARENT_AUDIT" "$PARENT_NATIVE_CASE" "$PAIR_PROPOSAL_FOLDER" "$NEW_CASE"
python "$PYTHONPATH/verify_agglomerated_fluid_mesh.py" "$PARENT_AUDIT" "$PARENT_NATIVE_CASE" "$NATIVE_CHECKED_CASE" "$NEW_READBACK_JSON"
python -m unittest discover -s tests -p test_935_fluid_agglomeration.py -v
```

The proposal folder contains `pairs.npz` and its hash-bound `receipt.json`. The
private checked runner executes the frozen native geometry commands before the
independent verifier. Proposal generation, rejected attempts, complete native
cases, field outputs and review images remain private. The
[machine-readable checkpoint](fluid-agglomeration-20261022.json) pins sources,
actual results, readback proofs and verified backups. Process limits remain
8 GiB address space, 2 GiB per file and 600 seconds per scientific command,
with 300-second native job limits. Work uses Mac/Kali1 without a new paid instance.

Next address the remaining internal-point and cavity quality, retaining exact
positive volume, physical walls and the unchanged full native gate. Star-shaped
cavities would need their own positive decomposition proof; convex-pair results
do not validate them. Scale, shaft registration, 17 interfaces, hidden
transmission, actual 935 mounting, domain/compressibility review, spatial
convergence, accepted fan curves, structural/fatigue qualification and bench
testing remain open. The complete system is not yet fabricable.
