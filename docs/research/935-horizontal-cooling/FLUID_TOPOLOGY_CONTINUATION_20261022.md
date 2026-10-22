# 935 fluid-topology continuation — 2026-10-22

## Scope in the root README chain

This continues [fluid-mesh correction](FLUID_MESH_CORRECTION_20261022.md) at
case preparation and meshing. The PicoGK master, every fluid-mesh vertex
coordinate, and every rotor/duct boundary triangle remain unchanged. There is
no new part geometry, alloy qualification or historical mounting claim. The
935 reference installation remains the objective; the 993 adaptation is separate.

The preceding centroid subdivision lowered one defect count but strongly
worsened non-orthogonality. This experiment instead changes local connectivity.
It retains the complete native quality check and does not run another rotor PDE
calculation on a mesh that still fails that check. All computation uses the
existing Mac/Kali1 environments; no new paid instance is created.

## Local reconnection with explicit refusals

The new [reconnection recipe](../../../twins/935-horizontal-cooling-system-f0/source/reconnect_fluid_tetrahedra.py)
tries a 2-to-3 tetrahedral flip around an internal face. Two parent cells become
three children using the same five vertices. Exact integer predicates require
a strictly convex, nondegenerate cavity, positive children, the same exact volume
and all six original outer faces. An already existing proposed edge is refused.
Changes in a batch have disjoint affected cell neighbourhoods.

The local selection filter checks five quantities: counts and squared normalized
severity of non-orthogonality above 70°, interpolation weight below 0.05 and
0.02, neighbour volume ratio below 0.01, and cell determinant below 0.001.
Every selected count must not rise and the failed-determinant count must fall.
Only the severity sum admits a `1e-10` floating-point comparison allowance;
no native acceptance threshold changes. This is a selection filter, not an
independent acceptance test.

Two sweeps select **139 and 15** disjoint changes. A third selects none. Its
node, element, marked-face and PLC files are byte-identical to the preceding
candidate, so the unchanged native conversion and quality test are reused.

A separate bounded **3-to-2** experiment reverses the same exact cavity checker.
It considers three tetrahedra around a valence-three edge and replaces them
with two, requiring the reverse 2-to-3 operation to reproduce all three original
cells. Existing proposed faces are refused, and the same local quality filter
applies. Its source, synthetic reverse controls, exporter and bounded continuation
runner remain in the private checkpoint. The first sweep selects 878 cavities.
The following sweeps select 130, eight and zero cavities. A final forward sweep also selects zero. Thus the restricted five-vertex family is exhausted for the targeted multi-boundary cells; this is not global mesh-optimization or physical convergence. In total, 1,170 local changes reduce failed cell determinants by 35.9%.

These are standard local tetrahedral transformations, used here with a separate
finite-volume objective. [TetGen's primary manual](https://www.wias-berlin.de/software/tetgen/1.5/doc/manual/manual002.html)
describes constrained boundaries and exact-predicate triangulation; passing
TetGen's shape criterion alone is not assumed to satisfy this CFD contract.

## Independent complete-mesh checks

Every changed candidate passes the existing complete indexed-connectivity,
exact-positive-volume and coordinate/triangle/marker boundary audit before
native import. The exact rational volume remains that of the original PLC.
The fluid volume is `0.05140958285727807 m³` under the existing assumed scale.
All 197,819 input vertices and 229,098 boundary triangles remain present.

The frozen Foundation 13 runtime imports each audited candidate and restores
the four named patches. The original `meshQualityDict` is byte-identical.
`checkMesh -allGeometry -allTopology -meshQuality` remains the final gate;
its process exit status alone does not establish acceptance.

| Candidate | Fluid cells | Failed determinants | Faces >70 degrees | Weights <0.05 | Failed native checks |
|---|---:|---:|---:|---:|---:|
| baseline | 884,608 | 3,261 | 929 | 63 | 4 |
| two_to_three_1 | 884,747 | 3,122 | 926 | 58 | 4 |
| two_to_three_2 | 884,762 | 3,107 | 926 | 58 | 4 |
| three_to_two_1 | 883,884 | 2,228 | 906 | 58 | 4 |
| three_to_two_2 | 883,754 | 2,098 | 903 | 58 | 4 |
| three_to_two_3 | 883,746 | 2,090 | 903 | 58 | 4 |

The native face-set union need not decrease monotonically when the number of
failed cells decreases: after the second 2-to-3 sweep, faces touching a failed
determinant cell rise from 296 to 300. This is retained rather than hidden by
the local objective. Native full-quality failures still prevent CFD admission.
The minimum volume and maximum non-orthogonality are also checked independently;
a lower defect count is not a convergence or airflow result.

Complete independent VTK/ASCII readback checks every native coordinate, cell and
patch marker against the audited arrays. The native `points` file retains the
original SHA-256 `bf19425e43e7cc301c08ec04e7872fdd27b68f4a595fd8fc5c49fb5ece7d1d59`.
The private review image shows actual failed-cell locations against the retained
CFD rotor wall in top projection. Red marks are mesh diagnostics, not stress,
airflow or failure predictions for a physical rotor.

## Reproduction and remaining work

Use a fresh private output directory and the existing numerical environment:

```sh
export PYTHONPATH=twins/935-horizontal-cooling-system-f0/source
python "$PYTHONPATH/reconnect_fluid_tetrahedra.py" "$PREPARED_PLC" "$PARENT_AUDIT" "$NEW_CANDIDATE"
python "$PYTHONPATH/fluid-mesh-study-20261022/audit-tetgen-002.py" "$PREPARED_PLC" "$NEW_CANDIDATE" "$NEW_AUDIT"
python -m unittest discover -s tests -p test_935_fluid_reconnection.py -v
```

The private runner applies an 8 GiB address-space limit, 2 GiB output-file limit
and 600-second per-process wall limit. Native conversion uses the previously
qualified rootless image and its network isolation. Existing frozen sources,
mesher attempts, logs and evidence are preserved without in-place edits.

The [machine-readable checkpoint](fluid-topology-continuation-20261022.json)
pins public sources, private experiment hashes, actual native quality results,
independent readback and backup receipts. Synthetic tests cover exact unit-volume
partition, convexity/degeneracy rejection, face ownership, independent quality
refusal, monotone selection and an unchanged all-refused sweep. Full Linux
`make check` and delivery status are preserved separately after publication.

Mesh-quality admission remains incomplete. The complete snapped-wall deviation
against the retained analysis surface, domain/outlet behaviour, compressibility,
three-grid convergence and stationary fan curves remain open. Physical scale,
shaft registration, the 17 interfaces, hidden transmission, actual 935 mounting,
material/process data, structural convergence, fatigue and bench tests remain
required before a manufacturing or physical-validation claim.
