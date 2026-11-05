# Bounded whole-study quad flips

Date: 2026-11-04. One executed pass changes connectivity on the complete frozen
reconstructed assembly study surface. **Geometric checks pass, but the 50%
triangle-quality improvement gate fails. No volume mesh or solver is launched.**
The [aggregate receipt](bounded-quads.json) binds the plan, controls, independent
assessment, source/runtime hashes and private manifest.

## Input admission and purpose

The input is the same coarse study boundary used by the earlier
[retained-volume audit](README.md), not the raw acquired surface. It has
1,048,504 vertices and 2,099,584 triangles. A fresh native CGAL inspection accepts
it as a closed study surface with zero degenerate triangles or intersections.
Frozen solid and protection-mask hashes are checked before execution and again
after collection. The ordered parent OFF matches the previously verified bridge
hash `7124f38238782e6f7a07c3d2cfe73c0c988f6147bd8ac734748e8d0c83b5111a`.

This admission is **conditional study geometry**. Its inferred closures,
head/hardware identity and incomplete observation support remain unresolved.
The original scan's separate audit still records eight zero-area triangles and
180 intersection pairs; this experiment neither repairs nor removes them.
The [exact source CAD charts](../935-source-shells-20261104/README.md) remain a
different reference branch. No anatomical interface, material or printing
tolerance is inferred from a successful numerical geometry screen.

The earlier nearly-planar flip barely improved quality. Projected remeshes
improved quality but exceeded deviation or intersection limits. This different
method changes a pair of triangle diagonals without moving any vertex and bounds
the resulting surface change analytically. It does not project onto a potentially
different nearby branch of the parent surface.

## Registered operator and bound

Consider old oriented triangles `abc` and `bad`, sharing diagonal `ab`. The new
triangles are `cad` and `dbc`, sharing `cd`. Project the four points onto the
plane normal to their summed original area normals. Require a strictly convex
projected quadrilateral, interior diagonal intersection and positive orientation
for every old/new projected triangle. Refuse an existing replacement diagonal,
protected faces, degenerate charts and insufficient numerical margins.

The two triangulations have a common subdivision into four projected triangles.
Their corresponding 3D maps agree at the four boundary corners. At the projected
diagonal intersection their separation is `D`. On each common triangle the
difference is affine, so its norm is bounded by `D`. This bounds both directed
surface distances for that patch. Production computes `D` from projected
diagonal parameters; the separate verifier uses the scalar triple product:

```text
e = b - a; h = d - c; n = unit summed original area normal
D = abs(((a - c) dot (e cross h)) / (n dot (e cross h)))
```

Changed original face pairs are disjoint, with identical boundary edges. Every
surface point therefore belongs to an unchanged face or one changed patch;
the maximum patch bound is also an upper bound for the complete parent/candidate
surface correspondence. The verifier checks actual source-row provenance and
refuses overlapping patches. This is a **double-precision analytic calculation**,
not an interval-arithmetic certificate or specimen-metrology claim.

The single-pass plan uses a 0.0099 mm candidate limit and a 0.01 mm admission
limit, relative volume change at most 1e-4, unchanged vertices/protected face
rows, unchanged topology, zero degeneracies/intersections and at least 50%
reduction of triangles below quality 0.01. The digital limits are study choices,
not manufacturing tolerances. Candidates must strictly improve worst pair
quality and reduce its bad-triangle count. Deterministic greedy selection takes
face-disjoint pairs, with no new-diagonal conflicts. No parameter sweep occurs.

## Actual independent results

| Check | Result |
|---|---|
| Registered protected triangles | All 111,463 original rows unchanged |
| Coordinates and face count | Entire ordered vertex array and total face count unchanged |
| Applied flips / changed original face rows | 1,609 / 3,218 |
| Bad triangles, quality < 0.01 | 8,489 → 6,876, a 19.001% reduction |
| Worst triangle quality | Unchanged at 3.3035686e-6 |
| Maximum independent patch bound | 0.008534347724 mm |
| Native geometry | Closed, zero degenerate faces, zero intersection pairs |
| Global topology | One component; Euler characteristic −1,288; opposite winding across every shared edge |
| Signed volume, before / after | 1,106,103.0255224346 / 1,106,103.0255226304 mm³ |

The independent assessor rebuilds the source boundary from the frozen solid,
checks every changed face pair and its replacement against source-row IDs,
recomputes convexity/bounds using a different expression, checks all protected
rows and verifies exact NPZ/OFF coordinate/connectivity agreement. It also
recomputes global edge valence, winding, connectivity, Euler characteristic,
quality and signed volume. Thus the actual OFF consumed by the native detector
is the same candidate independently assessed from NPZ.

Seven synthetic controls cover three known twisted-quad bounds, a degenerate
chart, a concave chart, zero planar distance and asymmetric quality improvement.
Separate negative controls reject a forged bound and overlapping patch records.
The full inspection and both command-line drivers complete successfully; that
success means the experiment and its **rejection** were verified.

## Decision and feasibility limit

The 50% quality gate fails, so `accepted_for_volume_meshing=false`. Passing the
other digital checks does not override that decision. The unchanged worst
quality also precludes claiming that the earlier stress-convergence problem is
resolved. No new Gmsh, OpenFOAM, CalculiX, Adamantine or machine-job result follows.

The registered original-edge enumeration finds 1,615 qualified candidates among
22,725 eligible edges. Even a perfect face-disjoint choice from **that recorded
list** could remove at most two bad triangles per flip: a loose ceiling of
3,230 triangles, or 38.049%, already below 50%. More effort changing the greedy
ordering cannot meet this contract. This ceiling is conditional on the recorded
enumeration and one-pass operator; it is not an impossibility claim about
multi-step methods, vertex placement or other remeshers.

Further conditioning needs a materially different constrained operator, with a
new preservation argument and independent admission. For example, a future
fixed-connectivity relocation would need to bind every final vertex displacement
to the frozen original and retain protected features; it has not been executed
here. Simply relaxing the digital limit, inventing interfaces or repeating an
interior mesh-size sweep does not resolve the demonstrated failure.

## Evidence and reproduction

Private bundle:
`~/Developer/PorschePartsArtifacts/935-bounded-quad-flips-20261104/`.
It contains 18 hash-bound files: source/helper snapshots, original/candidate OFF,
candidate NPZ, private quad/source-row provenance, native audits, independent
verification, logs and selection-ceiling analysis. Raw geometry remains outside
Git. The commands use the existing repair environment: NumPy 2.5.4, SciPy 1.18.1,
libigl 2.6.3 and PyMeshLab 2025.7.post1; the latter is loaded by the unchanged
retained helper, not used as this candidate's remesher. The native inspector is
the previously qualified CGAL binary, with its hash bound in the trial plan.
The separately hash-bound `935-bounded-quad-flips-20261104-commands.json` beside
the bundle records the actual controller/driver/verifier argument lists and
their two thread-limit environment overrides; the frozen bundle is unchanged.

Replay from the repository root into fresh output directories:

```sh
set -e
ARTIFACTS="$HOME/Developer/PorschePartsArtifacts"
SCAN="$ARTIFACTS/935-scan-tools-20261029"
PYTHON="$SCAN/repair-trial/venv/bin/python"
SOLID="$SCAN/hypothesis-run-20261029/science-recovery/coarse-tet/solid.npz"
MASK="$ARTIFACTS/935-masked-isotropic-20261104-v2/trial-001/protected-parent-face-ids.npy"
INSPECTOR="$ARTIFACTS/935-surface-flip-20261104/inspect_surface"
SOURCE="$PWD/docs/research/935-mesh-admission-20261104/source"
REPLAY="$(mktemp -d "$ARTIFACTS/935-bounded-quads-replay.XXXXXX")"
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 gtimeout --signal=TERM --kill-after=10s 600s \
  "$PYTHON" "$SOURCE/trial_bounded_quad_flips.py" --solid "$SOLID" \
  --protected "$MASK" --inspector "$INSPECTOR" --output "$REPLAY/trial"
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 gtimeout --signal=TERM --kill-after=10s 600s \
  "$PYTHON" "$SOURCE/verify_bounded_quad_flips.py" --trial "$REPLAY/trial" \
  --solid "$SOLID" --protected "$MASK" --output "$REPLAY/verification"
```

On native Linux use its `timeout` executable for the same bounds. No new model,
paid rental, supplier message, fabrication order or functional head release was
created. The overall faithful functional-metal objective remains incomplete.
