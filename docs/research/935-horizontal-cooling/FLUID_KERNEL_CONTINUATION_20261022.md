# 935 interior fluid-mesh continuation — 2026-10-22

## Result and scope

This continues the [fluid-topology study](FLUID_TOPOLOGY_CONTINUATION_20261022.md)
at the meshing stage of the root README software chain. Adding **1,537 interior
air-mesh points** reduces failed cell determinants from **2,090 to 519 (75.2%)**.
The complete native mesh still fails four quality checks. No new rotor PDE is
run, and no airflow, strength or manufacturing claim follows from this change.

The PicoGK master and every physical CFD boundary remain unchanged. The new
points belong to the computational air volume, not the rotor. All 197,819
original mesh coordinates remain an exact prefix of the final coordinate array;
all 229,098 boundary triangles and their markers are identical. Native `points`
file hashes legitimately change because interior points are appended.

The reference 935 installation remains the objective. The existing assembly view
shows the scan-based rotor, observed drive exterior and provisional shroud over
a generic two-bank, six-cylinder packaging envelope. It does not establish
historical engine geometry, measured mounting or functional transmission.

## Reuse of the constrained kernel

The [new edge-star recipe](../../../twins/935-horizontal-cooling-system-f0/source/rebuild_fluid_edge_stars.py)
reuses the existing `optimize_interior_stars.kernel_target` linear program and
the frozen reconnection quality filter. No numerical dependency is installed.
The first native launch refused to import a missing helper in the partial Linux
checkout; copying the exact existing helper into the new experiment directory
resolved that environment issue. The refusal log is retained.

An interior edge's incident tetrahedra define a cavity. The recipe preserves its
outer triangles and cones them to one new interior point. The LP maximizes the
minimum distance from that point to the oriented cavity-face planes. Translation
and span normalization avoid treating millimetre-scale coordinates as unit-scale
constraints. Unit and translated/scaled right-tetrahedron controls recover the
analytic incenter and prove exact positive volume partition on Mac and Linux.
The installed native runtime uses NumPy 2.2.6 and SciPy 1.17.1; the
[SciPy API documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linprog.html)
describes the inequality/bound convention, independently of that runtime version.

Candidate edges touch cells with at least two boundary faces; marked boundary
edges are excluded. Edge valence is restricted to 3–32 and each invocation to
at most 5,000 index-stratified edges. Four fixed fractions, `1, .75, .5, .25`,
between the edge midpoint and LP target are tested. Exact predicates require
positive children, identical outer triangles and identical rational cavity
volume. A disjoint-neighbourhood batch retains only changes that reduce failed
determinants without worsening any selected count or normalized severity.
This local filter selects candidates; the independent full native audit decides
whether they are admissible.

## Complete native checks

The 100-edge pilot selects 82 cavities. Subsequent full sweeps select 1,136,
262, 51 and six. The last sweep tests all 394 eligible edges and accepts none;
its candidate array archive is byte-identical to its parent. This only exhausts
the stated LP-target/four-fraction family on these edges. It does not establish
global optimization or spatial convergence.

| Candidate | Fluid cells | New points in batch | Failed determinants | Faces >70° | Weights <0.05 | Volume ratios <0.01 | Failed native checks |
|---|---:|---:|---:|---:|---:|---:|---:|
| prior topology result | 883,746 | — | 2,090 | 903 | 58 | 5 | 4 |
| pilot | 884,101 | 82 | 2,005 | 901 | 56 | 5 | 4 |
| full 1 | 889,099 | 1,136 | 840 | 875 | 31 | 4 | 4 |
| full 2 | 890,250 | 262 | 576 | 872 | 28 | 4 | 4 |
| full 3 | 890,463 | 51 | 525 | 872 | 28 | 4 | 4 |
| full 4 | 890,488 | 6 | 519 | 872 | 28 | 4 | 4 |

Every changed mesh passes the existing full exact-orientation, indexed
connectivity and coordinate/triangle/marker audits. The exact volume remains
`0.05140958285727807 m³` under the assumed calibration. All final 890,488
tetrahedra have positive orientation; the mesh is connected and its boundary
matches the original PLC. Independent Mac VTK/ASCII readback verifies every
native cell, coordinate and named patch against those arrays, then separately
checks the original-coordinate prefix and unchanged boundary arrays.

Foundation 13 runs `checkMesh -allGeometry -allTopology -meshQuality` using the
unchanged quality dictionary, rootless runtime and network isolation. Maximum
skewness remains 2.99560867. The final local dictionary also flags seven faces
with interpolation weight below 0.02; its union contains 1,078 faces. The
extended geometry checks still reject 519 cell determinants, 28 interpolation
weights and four volume ratios. Process exit zero is not treated as acceptance.

The private before/after image projects the actual retained rotor wall in grey
and independently recomputed native failed-cell centres in red. Its counts
exactly reproduce the two native logs. This is a mesh diagnostic, not a stress,
airflow or physical-failure prediction. Private geometry and renders stay outside
public Git; the machine-readable receipt pins their hashes.

## Reproduction, preservation and next action

Use the existing scientific environment and fresh private outputs:

```sh
export PYTHONPATH=twins/935-horizontal-cooling-system-f0/source
python "$PYTHONPATH/rebuild_fluid_edge_stars.py" --self-test
python "$PYTHONPATH/rebuild_fluid_edge_stars.py" "$PARENT_AUDIT" 5000 "$NEW_PROPOSAL"
python "$PYTHONPATH/export_fluid_kernel_candidate.py" "$PREPARED_PLC" "$PARENT_AUDIT" "$NEW_PROPOSAL" "$NEW_MESH"
python "$PYTHONPATH/fluid-mesh-study-20261022/audit-tetgen-002.py" "$PREPARED_PLC" "$NEW_MESH" "$NEW_AUDIT"
python -m unittest discover -s tests -p test_935_fluid_kernel_stars.py -v
```

The existing private converter then imports the audited mesh through the pinned
native runtime. The bounded controller applies an 8 GiB address-space limit,
2 GiB file limit and 600-second process limit; native conversion retains its
own 300-second job limits. All work uses Mac/Kali1, with no new paid instance.
Frozen earlier recipes, geometry and evidence are not edited.

The [machine-readable checkpoint](fluid-kernel-continuation-20261022.json) pins
sources, six full native cases including the baseline, independent readback,
visual inspection and private backups. Tests include analytic kernel controls,
exact partition, nonmanifold/degenerate refusal and export rejection when
original coordinates, boundary triangles or markers are changed, even if the
candidate's hash is recomputed.

Next optimize interior point positions against the direct finite-volume
objective inside guarded cavities, or assess a suitable hybrid mesh. Retain the
full native gates before a new rotor PDE. The snapped-wall deviation bound,
compressibility/domain review, three-grid CFD convergence, accepted fan curves,
physical scale, shaft registration, 17 interfaces, hidden transmission, actual
935 mounting, process-matched material data, structural convergence, fatigue and
bench validation remain open. The complete system is not fabricable yet.
