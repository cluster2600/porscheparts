# 935 finite-volume point-placement study — 2026-10-22

## Result in the README software chain

The [preceding interior-kernel study](FLUID_KERNEL_CONTINUATION_20261022.md)
stabilized at 519 failed cell determinants using four points on the line from
each interior-edge midpoint to its maximum-face-height LP target. Searching
three-dimensional cavity point placement now selects **67 additional interior
air-mesh points** and reduces that count to **448**, a 13.7% reduction. Severe
nonorthogonality falls from 872 to 866 faces; extended interpolation failures
fall from 28 to 26. Four native quality checks still fail. This remains a mesh
study, with no new rotor PDE or accepted fan curve.

The PicoGK master and physical geometry do not change. Every original coordinate
remains an exact prefix, including the initial 197,819 mesh vertices; all 229,098
boundary triangles and markers are identical. The final mesh has 199,423 points
and 890,778 positive tetrahedra. Its exact rational volume remains that of the
original PLC, `0.05140958285727807 m³` under the existing assumed calibration.
No new paid instance or numerical dependency is introduced: computation uses
the existing Mac and Kali1 environments.

## Bounded direct search with existing guards

The [point-placement recipe](../../../twins/935-horizontal-cooling-system-f0/source/optimize_fluid_edge_stars.py)
reuses the frozen cavity construction, exact partition checker, normalized LP
target and finite-volume filter. It adds the edge midpoint as a fifth control
and a seeded SciPy differential-evolution search over three normalized point
coordinates. Linear face-plane constraints keep candidate cones inside the
cavity kernel; exact predicates independently check a selected partition.

The search uses `rng=0`, Sobol initialization, `popsize=5`, at most 15
generations, one worker and no polishing. Its maximum is 256 DE objective calls
plus five explicit controls per tested cavity. These are exploration bounds,
not a convergence certificate. The scalar search cost combines normalized
severity with penalties for worsening severity or failure counts. Admission
still requires the existing filter: fewer failed determinants, no increase in
any selected count, and no worsening normalized severity beyond its existing
floating-point comparison allowance. Neighbourhoods in a batch are disjoint.

The installed native SciPy version is 1.17.1. The current
[SciPy API reference](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.differential_evolution.html)
documents population sizing, initialization, reproducibility and constraints;
actual versioned execution and unit/translated-scale controls are recorded
separately. Optimizer `success` is not used as an engineering gate. Budget-limited
searches can supply guarded candidates while global optimality remains unproved.

The CLI considers only interior edges touching cells with at least two boundary
faces, with valence 3–32, and caps each invocation at 512 sampled edges. The
32-edge pilot selects four cavities. Full sweeps test 390, 329 and 327 eligible
edges and select 61, two and zero cavities. The unchanged final candidate archive
is byte-identical to its parent. This only records the stated bounded seeded
experiment, not exhaustion of all possible point positions or cavity choices.

Independent attribution reconstructs every selected parent cavity from removed
tetrahedra and appended-point children, checks its complete outer boundary, then
recomputes the original LP target. **63 of 67 points lie off the original
midpoint-to-target line**; four coincide with control points. The improvement
therefore includes actual three-dimensional search, rather than only a denser
sampling of the earlier line.

## Complete audits and the remaining defects

Every changed volume passes the existing exact positive-orientation, connected
indexed-volume and complete boundary-coordinate/triangle/marker audits before
native import. Independent Mac VTK/ASCII readback checks every native coordinate,
tetrahedron and named patch against the final audited arrays. A separate direct
comparison verifies the retained coordinate prefixes and boundary arrays.

The frozen rootless, network-isolated Foundation 13 runtime and original
`meshQualityDict` run `checkMesh -allGeometry -allTopology -meshQuality`:

| Candidate | Fluid cells | Added points | Failed determinants | Faces >70° | Weights <0.05 | Ratios <0.01 | Failed checks |
|---|---:|---:|---:|---:|---:|---:|---:|
| preceding kernel mesh | 890,488 | — | 519 | 872 | 28 | 4 | 4 |
| pilot | 890,506 | 4 | 515 | 872 | 28 | 4 | 4 |
| full 1 | 890,772 | 61 | 450 | 866 | 26 | 4 | 4 |
| full 2 | 890,778 | 2 | 448 | 866 | 26 | 4 | 4 |

Maximum skewness remains 2.99560867 and the local interpolation dictionary still
flags seven faces below 0.02. The native error-face union improves only from
1,078 to 1,077: reducing one defect count does not imply overall mesh admission.
Independent diagnostics reproduce all native determinant and nonorthogonality
counts. Of the final determinant failures, 345 cells have two internal faces,
75 have three and 28 have four. The four-internal-face category rises from 27
to 28 even though the total falls; the filter does not require each subclass
to improve. Native full-quality rejection remains authoritative.

The private before/after image shows the unchanged CFD wall in grey and actual
failed-cell centres in red. It is not an airflow field or structural-failure
prediction. Images and geometry remain private; the public receipt contains hashes.

## Reproduction and next work

```sh
export PYTHONPATH=twins/935-horizontal-cooling-system-f0/source
python "$PYTHONPATH/optimize_fluid_edge_stars.py" --self-test
python "$PYTHONPATH/optimize_fluid_edge_stars.py" "$PARENT_AUDIT" 512 "$NEW_PROPOSAL"
python "$PYTHONPATH/export_fluid_kernel_candidate.py" "$PREPARED_PLC" "$PARENT_AUDIT" "$NEW_PROPOSAL" "$NEW_MESH"
python "$PYTHONPATH/fluid-mesh-study-20261022/audit-tetgen-002.py" "$PREPARED_PLC" "$NEW_MESH" "$NEW_AUDIT"
python -m unittest discover -s tests -p test_935_fluid_point_placement.py -v
```

The existing private native converter follows the complete volume audit.
Process limits remain 8 GiB address space, 2 GiB per file and 600 seconds per
scientific command, with the converter's existing 300-second native job limit.
The [machine-readable checkpoint](fluid-point-placement-20261022.json) pins
sources, four complete native cases including the baseline, attribution,
independent readback, actual diagnostics and private backups. Tests cover analytic
unit/scaled controls, noncontiguous local/global index agreement, unchanged
original points, finite budgets and rejection of non-improving or incomplete
parent evidence.

The next mesh work must address rank-two cells with topology changes or guarded
convex cell agglomeration, and optimize existing interior points for the remaining
nonorthogonality/interpolation defects. Native quality thresholds stay unchanged.
Mixed polyhedral cells would require their own partition, exact volume and
independent readback proofs. Scale, the 17 interfaces, hidden transmission,
historical mounting, domain/compressibility review, spatial convergence, accepted
fan curves, structural/fatigue qualification and physical tests remain open.
The 935 installation is still an engineering study, not a fabricable system.
