# Separate raw-volume construction from tetrahedral optimization

This local diagnostic continues the [conditioned-surface trial](../935-local-conditioning-20261105/README.md).
The paid trial reached its limit during tetrahedral improvement and exported
no final head mesh. This increment explicitly disables optimization before
generation, preserving the same surface and 2 mm interior size. It measures
construction and independent cell quality separately; export alone grants no
physics admission. No additional paid resource is created.

## Fixed rationale and prerequisites

The [Gmsh 4.12.1 implementation](https://github.com/live-clones/gmsh/blob/gmsh_4_12_1/src/mesh/meshGRegionHxt.cpp#L531)
passes `Mesh.Optimize` to HXT's optimization flag, and
`Mesh.OptimizeThreshold` to its quality target. The source-tag file is retained
privately by hash. Installed-library behavior is checked independently by
recording actual options immediately at `generate(3)` and observing the native
log. The threshold is not changed to make a poor mesh pass.

The input SHA-256 is
`7adc8f931feac78eb6298e1415c8d49b7a92bced5dde5dbcc6bc3afd2e9e947f`.
Its independent correspondence and complete native surface checks already pass.
The admissibility verdict remains **diagnostic only**: the parent is a
hypothetical head with inferred closures and provisional cuts. Its protected
poor boundary faces remain, and no hidden geometry or physical interface is
created by this run. Both the frozen printing master and the conditioned
surface are unchanged.

One bounded Mac run uses the existing isolated Gmsh 4.12.1 runtime, eight
threads, a 900-second head limit and a sampled 40 GiB RSS limit. The controller
also checks remaining disk space, terminates the exact child process group on
a limit and reaps it. The runtime and the frozen authoring recipe are not
edited. A separate wrapper sets `Mesh.Optimize=0` and
`Mesh.OptimizeNetgen=0`, then witnesses them at the real generation call.

Before the head, the same path must export an analytic unit cube. A separately
fixed cube surface and an independent all-cell/all-face inspector must confirm
positive cells, exact source boundary/orientation and unit volume. The
inspector also exercises inverted-cell and missing-boundary refusal controls.
Synthetic cube dimensions do not calibrate the specimen.

## Execution and admission

The raw file exports in 148.895 seconds with 4,181,898 nodes and 13,252,408
actual tetrahedra. HXT's internal 27,892,088-cell log count includes entries
that are not retained material cells; it is not the delivered denominator.
The sampled peak RSS is 26,844,592 KiB. Native minSICN and the independent
mean-ratio metric are distinct and are reported separately.

The original inspector fails closed on a nonpositive floating determinant.
A separate all-cell audit finds one floating negative and one floating zero;
exact rational determinants of both and the eight worst cells are positive.
The rejection is retained as a precision diagnostic, without reordering cells
or editing coordinates. This does not waive the 0.01 mean-ratio criterion.

A new independent inspector encloses each determinant using outward-rounded
binary64 intervals, expanding every arithmetic operation by one neighbouring
value. Ambiguous signs use exact fractions of the stored coordinates. This
covers representation-level numerical signs, not physical measurement error.
Its positive cube and deliberate inverted-cell/missing-boundary controls run
through the actual CLI. It then checks the complete head face/cell incidence,
source boundary and orientation. The outcome is in the aggregate receipt.

The complete robust inspection passes cell positivity and face/boundary
consistency in 55.215 seconds: 13,251,617 cells are proven positive by intervals
and 791 by exact fractions. All 22,395,161 internal face pairs have opposite
orientations; the complete 8,219,310-face boundary and all source vertices remain
exact. Relative volume disagreement is 4.45 × 10⁻¹⁶. No geometry is repaired.

Quality still fails: 527,342 cells are below mean ratio 0.01, 149,424 are below
0.0001, and the minimum is 2.91459 × 10⁻¹². A consistency pass does not admit
this ill-conditioned volume for head CFD/FEA. The surface audit already proved
that retaining 633 particular boundary triangles forces low-quality cells;
interior optimization cannot satisfy the same minimum criterion everywhere
without revisiting that constraint. No empty interior-size sweep follows.

Actual export, independent head inspection, quality bins and terminal receipts
are recorded in [results.json](results.json). A raw construction is retained
even when the diagnostic mean-ratio criterion rejects it. In particular,
disabling optimization does not waive low-quality cells, convergence,
conservation checks, loads, physical calibration or process qualification.

The independent inspector checks all cells, all face incidences and paired
orientations, exact retained source nodes, exact actual outer boundary and
signed-volume agreement. It does not exhaustively test every pair of
tetrahedra for intersection, and its consistency pass is not a physics release.

| Phase | Concrete input / command source | Output / check |
|---|---|---|
| Admission | Conditioned mesh and full native geometry receipt | Fixed input hash and diagnostic-only verdict |
| Cube | `run_diagnostic.py` → `mesh_without_optimization.py` | Real export and separate full-cell control |
| Head construction | Same path, HXT, 2 mm, eight threads, optimization off | Bounded terminal and exported bytes if complete |
| Initial head inspection | Frozen `inspect_tetrahedra.py`, exact conditioned surface | Floating-sign rejection retained |
| Defect audit | `audit_failed_cells.py`, every cell, exact selected signs | Separate rounding diagnosis; no repair |
| Robust head inspection | `inspect_interval_volume.py`, outward intervals and exact fallback | Complete face/cell consistency and unchanged quality criterion |
| Physics and manufacturing | Qualified domain, material/loads and calibrated machine recipe | Remain separate unfulfilled gates |

The private capsule retains exact commands, source snapshots, runtime identity,
options at generation, logs, numerical arrays and hashed inspection receipts.
Only executable sources and aggregate results are committed. Replay into a
new private directory, using each source's `--help`; never write into frozen
capsules. The complete engineering goal remains active.
