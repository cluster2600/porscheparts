# 935 native interior relocation with complete reference checks

This separate study tests Gmsh's documented `Relocate3D` method on the unchanged
raw checkpoint after the [Netgen native-label rejection](../935-volume-optimization-20261105/README.md).
It changes the method rather than repeating the rejected Netgen call. The
actual-method receipt takes precedence over request labels retained by reused
export/audit code. Full terminal results and admission decisions are recorded
in [results.json](results.json).

## Admission and controls

The [regularized numerical surface and raw volume](../935-corner-provenance-20261105/README.md)
remain the upstream inputs. Every stored cell is positive, the complete source
boundary and internal face pairing pass, but volume shape quality fails.
This remains a hypothetical envelope: measured interfaces, exact hidden
geometry, specimen scale/material and process qualification are not supplied
by this numerical experiment. The original printing master is unchanged.

The one-call Netgen/default controls and native-label diagnosis are retained
without modification. Native `Relocate3D` is documented as node relocation in
the installed Gmsh 4.12.1 API. It offers a distinct interior-movement route
without requesting Netgen topology changes. No option sweep is performed.

The new method must pass the same distorted-cube control before any head call:
all cells, complete oriented boundary and source coordinates must pass the
independent inspector, and minimum mean ratio must reach
`max(0.01, 10 * before)`. The fixed cube improves from 0.000094494173 to
0.627409721, passing those checks. No boundary acceptance rule is relaxed.

The head then receives one `Relocate3D` API call with eight threads, the same
2 mm size field, `force=True` and `niter=1`. That API argument does not assert
the kernel's internal iteration count. Before the call, the retained region
adapter proves every coordinate and connectivity array unchanged when moving
from a discrete to a GEO-owned volume. This is entity ownership, not analytic
head CAD. After the call, native node labels, raw coordinates and connectivity
are saved before any coordinate indexing. Every reference must resolve to a
unique node; missing labels abort before sign evaluation.

The retained outward-interval/exact-fraction audit then checks every sign.
Only a complete exported candidate can reach the separate whole-volume
inspector. That inspector checks every cell, complete oriented source boundary,
source coordinates and opposite internal face pairs. Its documented scope
does not include an exhaustive tetrahedron-pair intersection search.

The predeclared head screening target is unchanged: at least 50% fewer cells
below mean ratio 0.01, no increase below 0.0001, and no worse minimum. Passing
that relative target alone would not establish adequate conditioning,
convergence, case boundary conditions or physical/manufacturing qualification.

## Execution ledger and reproduction

The head export completes in 98.101 seconds including native readback/audit and
compression, with sampled peak RSS 7,615,792 KiB. All 4,181,299 native labels are
unique and every reference resolves. Every one of the 13,250,576 original
tetrahedral index rows remains exactly unchanged. The native method moves
24,992 nodes, with maximum interior displacement 9.552196 mm; all 4,106,319
source boundary vertices remain exactly fixed. Complete boundary connectivity
is unchanged too. A separate source/raw comparison checks these claims on the
head and on the cube, which moves only its one interior node.

The raw sign audit finds 13,250,312 positive and **264 negative** cells, with no
exact-zero cell. It uses exact fractions for 791 interval-ambiguous cases.
Since every input cell was independently positive and native connectivity/row
order are unchanged, those 264 signs are genuine orientation inversions caused
by node motion, rather than a new connectivity convention. The retained
exporter swaps 264 index rows to positive local orientation, but that is not a
repair of the inverted embedding. The independent whole-volume inspector
rejects the resulting candidate at its opposite-internal-face-pair check,
after 54.655 seconds. No successful head inspection report or downstream
quality comparison is admitted.

The rejected normalized export has SHA-256
`3dc6a82bb4601b65e4351c86242baf1b1c7c199d548e4f276c48abea8084c1be`;
the earlier raw tagged output has SHA-256
`65b77a5b91e220a242a8e78262ff41f9190a5ee6012c790ad6c37f249beb4521`.
Neither is an accepted simulation domain. Merely making each local determinant
positive can conceal an inverted embedding; complete face consistency remains
mandatory. A subsequent relocation method must constrain each accepted move
to preserve original cell orientation before it can be tried on this checkpoint.
This result does not justify another unconstrained iteration-count sweep.

| Phase | Concrete inputs / source | Expected output and check |
|---|---|---|
| Upstream audit | Frozen surface/native geometry report, raw MSH/NPZ, independent interval report | Positive consistent raw volume, shape-quality failure retained; diagnostic use only |
| Cube control | `run_relocation.py`, unchanged frozen cube with displaced interior node | Minimum 0.627409721; all independent cell/face checks pass |
| Region conversion | Retained `optimize_geometric_volume.py` | All checkpoint arrays exactly unchanged |
| Actual method | `optimize_relocated_volume.py` | One native `Relocate3D` call; explicit actual-method receipt |
| Raw reference/sign audit | Retained `optimize_audited_volume.py` | Raw native capture; unique/complete labels before exact sign checks |
| Independent head inspection | Frozen interval inspector and cell/face helpers | Rejected opposite-internal-face pairing; candidate not admitted |
| Relative quality | Fixed bin counts and minimum comparison | Not reached because consistency fails; no automatic solver admission |
| CFD/FEA and AM | Case-specific admission, material, loads and calibrated process | Still separate requirements |

The head worker has a 900-second kernel alarm. The controller samples exact
child RSS against 40 GiB, enforces wall time and 4 GiB free disk, terminates only
its own child group and reaps it. The cube has a 60-second kernel alarm.
All raw outputs and logs stay in the private capsule. Sources and hashes alone
are published. No paid compute or supplier message is created.

The [controller](source/run_relocation.py) provides `--help` and takes the same
explicit arguments as the preceding study, plus `--retained-sources` pointing
to its unchanged [source directory](../935-volume-optimization-20261105/source/optimize_audited_volume.py).
Set `PYTHONPATH` to the scientific site before running it; pass that same site
as `--scientific-site`. Use the frozen Python 3.12.11 / NumPy 2.5.4 / arm64
Gmsh 4.12.1 runtime. `--root` must be a new private directory. Exact commands,
input hashes, sources, terminal receipts and output hashes accompany the
private release. Reproduction must never write into frozen evidence.

The separate private capsule contains 51 indexed files (435,854,849 bytes,
excluding its manifest), all rehashed and made read-only after task processes
terminated. Its manifest SHA-256 is
`d6e8a46896c967f34b29406d6988b48d9bae1cf192db179d6f8bfc6b006ff092`.
The original raw MSH/NPZ and regularized surface are rehashed unchanged. The
preceding capsule and execution-hashed sources are untouched.

The full engineering goal remains active. No result here replaces the printing
master, supplies measured interfaces or authorizes a functional metal head.
