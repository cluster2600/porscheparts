# 935 interior-relocation exclusion and boundary-only topology control

Moving interior nodes cannot reach the fixed volume-quality target on this
checkpoint. Complete classification finds 392,770 of the 526,110 cells below
mean ratio 0.01 have **all four vertices fixed on the source boundary**. At
fixed connectivity, their coordinates and quality cannot change. This leaves
at most 133,340 repairable cells, below the 263,055 required for the predeclared
50% reduction. The exclusion applies to fixed-connectivity interior relocation,
including a version that clips the preceding native proposal to prevent
inversions. It does not exclude topology changes or qualify any solver.

The native default optimizer subsequently passes a distinct analytic 3-to-2
topology witness. Its bounded head attempt reaches the 900-second worker alarm
without returning a final mesh. Exact phase states and numerical receipts are in
[results.json](results.json). The directory identifier retains the initial
constrained-relocation plan; the upstream audit changed the chosen next action.

## Input admission and complete coverage

The [preceding native relocation](../935-native-relocation-20261105/README.md)
retains a rejected target-coordinate proposal: 24,992 interior nodes move while
264 cells invert. Its native connectivity is unchanged. The proposed positions
are reused only as targets in this audit; the rejected embedding is never an
accepted input mesh. The admitted diagnostic input remains the
[positive raw checkpoint](../935-corner-provenance-20261105/README.md), whose
complete boundary, source coordinates and internal face pairing were checked.
It is a hypothetical envelope with failed shape quality and unestablished
physical interfaces, material, hidden geometry and process qualification.

`audit_proposal_coverage.py` recomputes quality on every original cell using
outward determinant intervals and exact fractions in 792 ambiguous cases.
Only 94,031 subthreshold cells touch any of the 24,992 proposed moving nodes.
Even repairing every affected bad cell, while creating none, could remove only
17.9% of the original bad bin. Limiting those same displacements to preserve
orientation cannot enlarge their coverage. No constrained head move is executed.

`audit_fixed_boundary_cells.py` extends the bound to **all** 74,980 interior
vertices, independent of the previous proposal. Of all 13,250,576 cells,
7,178,879 have no interior vertex. This includes 392,770 cells below 0.01 and
149,055 of the 149,190 below 0.0001. The global minimum, 2.914590667e-12, also
belongs to this fixed subset. Arbitrary motion of every interior node could
repair at most 25.3% of the bad 0.01 bin at the same connectivity. The complete
0-to-4-interior-vertex partitions and all five quality bins are retained.

A further `verify_quality_partition.py` recomputes all 13,250,576 bin predicates
using the frozen inspector's exact floating arithmetic order. It reproduces
every partition and proposal-coverage count, with zero predicate disagreements
in all five bins. The tiny last-bit difference in the algebraically equivalent
minimum evaluation is not used to change a gate. These are stored-coordinate
numerical bounds, not measured engine limits or formal physical error bounds.

## A control for the topology-changing capability

The previous default-optimizer cube control remains rejected: it requires
movement of a near-corner interior node. It does not demonstrate the different
capability now required by the fixed-boundary-only cells. The new plan declares
a synthetic convex bipyramid with five fixed boundary vertices, three thin
tetrahedra around an internal edge, and an independently known two-tetrahedron
alternative across the equatorial face. Its coordinates are explicit in
[the controller](source/run_topology_optimization.py); they are synthetic, not
Porsche dimensions and never calibrate the head.

Exact-fraction supporting-face tests establish the convex boundary. Each
positive source/reference cell and both total volumes equal the independent
analytic volume `2 * (1 + epsilon) / 3`, with `epsilon` the stored binary64
coordinate corresponding to 0.000001. The frozen whole-cell/face inspector
checks both representations before invoking the optimizer.

The acceptance rule keeps the previous minimum floor of 0.01 and factor-of-ten
improvement, and additionally requires exactly the independently known 3-to-2
connectivity change. One native Gmsh default call passes: minimum mean ratio
improves from 0.000085714273 to 0.80000032, every boundary coordinate stays
exact, and the complete resulting cell set matches the two-cell reference.
The original failed cube receipt is neither replaced nor retroactively passed.
This witness supplies admission for one diagnostic head call only.

The actual native method is the empty-string default optimizer argument,
eight threads, fixed 2 mm size field, `force=True` and `niter=1`. Reused audit and
export recipes retain a `Netgen` request label; the separate actual-method
receipt establishes the method executed. The API iteration argument does not
assert the kernel's internal iteration count. The exact-array GEO region
adapter and complete native node-reference checks remain in the path.

## Phase ledger and immutable evidence

The actual head worker exits with signal 14 (`SIGALRM`) after 900.275 seconds,
with sampled peak RSS 10,093,904 KiB. The controller's wall/RSS/disk limit is not
the terminating condition: the worker's kernel alarm ends the call. No native
raw capture, candidate export or complete head inspection report is produced.
The native log retains 145 stale-edge-cavity warnings; these are native
messages, not an independent reclassification of the admitted positive input.
The child is reaped and its exact process is freshly observed absent. No
larger time-limit or parameter sweep follows this negative benchmark.

The next method needs a bounded, traceable topology operation on the fixed
boundary-only bad cells, with complete positive-cell and boundary-preservation
checks. The analytic witness establishes one possible local operation; it
does not establish that such cavities cover enough of the head's bad cells.
That coverage must be audited before a new head trial. Interior relocation
alone remains mathematically excluded under the unchanged target/contract.

| Phase | Inputs and runtime | Output / admission |
|---|---|---|
| Original input | Frozen raw MSH/NPZ, complete interval inspection and source surface | Positive consistent diagnostic input; shape failure and physical limits retained |
| Proposal coverage | Rejected raw target coordinates; original cells | 94,031 potentially affected bad cells; insufficient for 50% |
| All-interior bound | All original cells and exact protected-vertex prefix | 392,770 fixed bad cells; all fixed-connectivity interior relocation excluded |
| Reference arithmetic | Frozen inspector formula, all cells and both partitions | Zero bin-predicate disagreement; all counts reproduced |
| Analytic topology control | Exact convex bipyramid and known two-cell alternative | Full independent inspection and native 3-to-2 change pass |
| Head topology attempt | Same admitted raw checkpoint, one Gmsh default API call | 900-second kernel alarm; no final raw capture, export or admitted head result |
| Field and AM validation | Case-specific mesh admission, loads/materials, calibrated machine/process | Still pending; no printing or functional release |

The preflight capsule is the private `preflight-release` subdirectory of
`935-constrained-relocation-20261105-001`. Its 53 indexed files (67,377 bytes,
excluding the manifest) are rehashed and read-only, with manifest SHA-256
`b447e77605658adee0d1348788cdcc2dea65964b11dc7b4f857f257c2e3895bf`.
It contains completed audits, sources, synthetic controls and commands. Its
timestamped launch observation describes the then-live worker; the later
terminal receipt supersedes it for head status. The complete closed capsule
now contains 117 indexed files (161,284 bytes, excluding its root manifest),
including that unchanged preflight release. All files are rehashed and read-only
after every task process terminates. The complete capsule manifest SHA-256 is
`a04010b3443b357376808b5f1943991c30cd4f22cafb06d480828505aa681859`.
Original MSH/NPZ and surface hashes are rechecked unchanged. No raw scan or
derived head mesh is committed.

All five sources under [source](source/audit_proposal_coverage.py) provide
`--help`. Use the frozen Python 3.12.11 / NumPy 2.5.4 / arm64 Gmsh 4.12.1
runtime with the scientific site on `PYTHONPATH`. The topology controller also
takes `--scientific-site`, `--retained-sources`, `--repository`, explicit original
mesh/surface/report arguments, and a **new** private `--root`. Exact commands
and source/input hashes are retained privately. Never replay into frozen data.

Each audit has a 300-second kernel alarm. Native controls have a 60-second alarm;
the head worker has a 900-second kernel alarm. The retained controller monitors
40 GiB sampled RSS, wall time and 4 GiB free disk, terminates only its child
group and reaps it. Every head output requires complete independent cell,
boundary and face-pair checks before the unchanged relative-quality comparison.
No new field solve, paid resource, supplier message or printing-master change
is created by these preflight results. The full engineering goal remains active.
