# Native readback of the 935 centroid batch mesh

The [exactly verified centroid batch](../935-centroid-extreme-batch-20261105/README.md)
requires a new native check because its cell connectivity has changed. Actual
Gmsh 4.12.1 export and re-import preserve every coordinate, tetrahedron and
complete boundary row exactly. The resulting native mesh still fails the
positive shape-metric gate: **997 cells have nonpositive `minSICN`**. No engine
field solve, OpenFOAM/CalculiX admission or physical release follows.

The upstream mesh is
`7e4f514b548c5d215a78735c506bca5933d3d69a617a9bcd9c5d70322cfff156`,
with 4,181,321 nodes and 12,967,657 tetrahedra. Its complete positive orientation,
boundary pairing, exact condition census and failed absolute quality gate were
checked before this diagnostic. The represented domain is still the inherited
hypothesis, with unclassified boundaries, assumed closures and open specimen
metrology/material/process requirements.

The existing unchanged
[native exporter](../935-native-solver-admission-20261105/source/export_native_mesh.py)
is reused, SHA-256
`e9a4b8cb0805ddaa779f307ba7c0b89c17a679a3915028487a28879a73ecf484`.
Its positive and deliberately inverted literal tetrahedron controls exercise
all three native metrics. It requests no optimization, imports the verified
source arrays, writes binary MSH 4.1, clears Gmsh, reopens the actual file and
checks complete node-label mapping and array equality before its full metric
census. The single boundary group is explicitly unclassified; it supplies no
physical port, interface or load assignment.

| Native metric over every tetrahedron | Minimum | Nonpositive/nonfinite cells |
|---|---:|---:|
| `minDetJac` | `1.5317399711011945e-19` | 0 |
| `volume` | `2.5528999518353243e-20` | 0 |
| `minSICN` | `-2.0245344338430406e-13` | 997 |

No metric is nonfinite. These native shape-metric results do not overturn the
exact positive-orientation proof, and a negative shape indicator is not called
a measured negative physical volume. They remain a native admission failure;
exit zero, successful export and exact roundtrip do not waive that gate.
The earlier native discrepancy/origin diagnostics are historical evidence on
different connectivity, not current operator admission. No frame search,
threshold relaxation or field solve is used to hide the failure.

The actual private `solid.msh` is 915,499,733 bytes, SHA-256
`7677a060020d63a39d7555d9ef927f3bd63f315088b7ac7a603e9172aeba4724`.
It remains outside Git. [Results](results.json) retain the exporter/runtime
hashes, full metric values, rejected-cell-index hashes, source hashes, exact
roundtrip receipts and bounded-controller result. The Mac run uses Python
3.12.11, a 600-second kernel deadline, 4 GiB free-disk floor and existing
supervisor; it completes in about 22 seconds with sampled process RSS about
5.4 GiB. No new paid compute is used.

The private capsule `935-centroid-native-readback-20261105-001` is frozen only
after the worker is terminal and executed source, original inputs and actual
export are rehashed. Its immutable manifest and payload totals are recorded in
`results.json`; every payload is rehashed after making it read-only. Replay the
unchanged exporter with `--mesh`, `--input-report`, `--surface` and a new
`--output` directory in the pinned scientific runtime. The capsule retains the
exact command and input phase ledger.

The next numerical decision must use the source-relative poor-cell constraints
and native rejected-cell provenance. A successful local cavity proof or smaller
warning count cannot establish a converged, correlated engine solution. The
full faithful-CAD, simulation, metal-printing and physical-qualification goal
remains active; all functional/manufacturing release gates remain false.
