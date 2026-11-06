# Bounded numerical conditioning of the hypothetical 935 head

The numerical surface has fewer badly shaped triangles while preserving the
frozen printing master. One bounded Vast run on the conditioned surface reached
its 1,800-second head-meshing limit without exporting a final head volume mesh.
No head physics or manufacturing acceptance follows.

## Inputs and scope

This continues the [fixed-face audit](../935-local-physics-20261105/README.md),
using the [local hypothetical head](../935-bare-head-hypothesis-20261105/README.md).
The parent includes inferred closures and eleven provisional hardware cuts.
Its one-source-unit-equals-one-millimetre scale is an owner hypothesis, not
specimen calibration. The original OBJ SHA-256 remains
`4623d5d3b73fe3d03ca988a47543a8dd1be7834d3040e6f7efd1e1e95c766486`.
The owner now permits sending the original scan to Vast when useful. This run
transferred only a derived mesh; it sent no scan or message to a supplier or
external CAD service.

The independent admissibility verdict permits diagnostic tetrahedralization
only. It does not resolve physical interfaces, hidden passages, material,
engine loads or a calibrated metal process. The existing head/support 3MFs and
neutral contours remain unchanged. The conditioned surface is a separate
numerical study, without regenerated supports or manufacturing files.

## Fixed method and independent checks

One composition was fixed before execution, without an interior-size sweep:

1. Apply face-disjoint quad diagonal flips with a 0.0049 mm correspondence cap.
2. Relocate eligible vertices tangentially with a 0.0049 mm displacement cap.
3. Independently check changed-patch correspondence, unchanged protected
   geometry, volume drift and a complete surface topology/intersection audit.

All cut-cap faces and faces touching a dihedral above 30 degrees, together
with their vertices, are protected. Additional sharp-edge locks are computed
between the two stages. Neither operator invents a hidden passage. The fixed
combined displacement budget is 0.01 mm and the relative volume-change limit
is 0.0001; these are computational study limits, not manufacturing tolerances.
The predeclared quality target is at least 50% fewer faces with normalized
triangle shape below 0.01.

| Check | Executed result |
|---|---:|
| Vertices / triangles retained | 4,106,745 / 8,219,310 |
| Quad flips / moved vertices | 6,391 / 23,479 |
| Protected face rows / vertices, unchanged exactly | 1,106,232 / 948,924 |
| Faces with shape below 0.01, before → after | 33,721 → 3,469 |
| Reduction | 89.7126% |
| Independently bounded flip correspondence | 0.0021661043 mm |
| Maximum relocation | 0.0049000000 mm |
| Composed complete-surface correspondence bound | 0.0070661043 mm |
| Relative volume change | 9.11 × 10⁻¹¹ |
| Open, nonmanifold, winding, degenerate, intersection counts | all zero |
| Positive / negative shells | 1 / 0 |

The flip verifier uses a separate scalar-triple-product construction; the
relocation bound uses barycentric correspondence over every triangle. Controls
include known quads, concave/degenerate rejection, overlapping patch rejection
and a forged-bound rejection. These are double-precision analytical checks,
not interval proofs or physical metrology. The full unchanged native libigl
checker also reports vertex-manifold topology and positive volume.

The worst triangle shape remains `6.610639549568414e-7`. Faces forcing an
incident tetrahedron below mean ratio 0.01 decrease from 3,269 to 633, implying
at least 159 subthreshold tetrahedra while those exact faces remain. The
conditioning therefore improves the input without resolving every constraint.

## Fidelity to the complete acquired scan

Each direction uses 100,000 area-weighted samples. Removed protrusions remain
in the raw-scan denominator; inherited closures remain in the reverse
denominator. No anatomical exclusion or alignment refit hides these errors.

| Distance, mm under the scale hypothesis | Before P95 / P99 | After P95 / P99 |
|---|---:|---:|
| Complete raw scan → numerical surface | 0.097860 / 28.184238 | 0.097860 / 28.184238 |
| Numerical surface → complete raw scan | 1.523448 / 4.329602 | 1.534288 / 4.359549 |

On the same raw-scan sample points the largest distance change is
0.000845956 mm. The reverse distributions resample changed triangle areas:
equal random seeds do not establish identical physical points, and their
quantile difference is not a paired-point displacement measurement. These
sampled statistics neither certify global Hausdorff distance nor identify a
measured bare head. The separate composed bound concerns conditioning relative
to its hypothetical parent only.

## Actual paid diagnostic and recovery

The independently audited surface was uploaded after input hash verification.
The pinned mesh/CFD image used Python 3.12.3, NumPy 2.5.2 and Gmsh API 4.12.1
(distribution 4.12.1.dev1). An analytic cube control passed before the head run.
The head used HXT algorithm 10, 2 mm interior size, 32 threads, a real 48 GiB
child address-space limit and a 1,800-second timeout. Forty-eight effective
CPUs were offered; a larger host CPU/RAM report is not a dedicated allocation.
The ancillary GPU was unused. No image modification or blind job restart was
performed.

The head reached repeated tetrahedral improvement cycles but timed out before
exporting a final mesh. Intermediate log counts are not accepted volume meshes.
The worker failed closed and produced a terminal state and result manifest.
The recovery tools preserve logs, inputs' hashes and the negative result.
Financial and deletion receipts are recorded in [results.json](results.json).

An independent Mac guard was armed before creation. It limits its deletion
authority to the exact task-created instance, rejects pre-existing instance
IDs, enforces rate/time ceilings and observes absence independently. Fake
provider controls exercise both owned-resource cleanup and foreign-resource
preservation. This attempt has a $1.50 cap inside the existing $35 project
budget; it does not reset prior reservations. No recharge is requested.

## Phase ledger and replay

| Phase | Inputs / runtime / outputs | Verification / final state |
|---|---|---|
| Admission | Frozen head, cut tags, prior fixed-face audit | Diagnostic surface study only |
| Conditioning | `condition_surface.py`, native Mac scientific environment | Quality target passed; separate candidate |
| Preservation | `verify_conditioning.py`, frozen operators and independent verifier | Full protected geometry and bounded correspondence passed |
| Surface audit | Frozen `validate_build_final.py`, libigl | Full native checks passed |
| Scan distance | `check_scan_distances.py`, original arrays and frozen rigid frame | Complete sampled denominators; hypothesis errors retained |
| Rental controls | `guard_conditioned_rental.py`, scoped OpenBao wrapper | Controls passed; one actual paid instance |
| Native cloud job | `run_conditioned_cloud_mesh.py`, pinned image, input manifest | Cube passed; head timed out; no final volume mesh |
| Recovery | `collect_cloud_results.py`, `verify_cloud_recovery.py` | Archive/input/result hashes and closeout in aggregate receipt |
| Head physics / metal process | Valid domain, loads, properties, calibrated machine inputs | Not admitted by this increment |

Sources are in [source/](source/condition_surface.py). Their exact hashes,
private evidence manifest and execution receipts are in the aggregate result.
Each executable provides `--help`. Replay into a new private directory; never
write into frozen evidence. The private capsule retains exact commands,
source snapshots, controls, initial preparation without creation, terminal
logs, provider metadata and recovered files. Raw arrays, scan geometry and
provider connection details are excluded from Git.

Another identical HXT attempt or interior-size sweep is not justified by this
timeout alone. A subsequent trial needs a materially different, bounded
meshing/conditioning strategy, unchanged geometry checks and an explicit
quality target before more compute. The broader faithful reconstruction goal
remains active.
