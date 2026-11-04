# Rejected periodic freeform wall reconstruction

Date: 2026-11-04. **One executed candidate, independently rejected. No replacement
CAD surface or solid was released.** This continues the
[observed-wall CAD review](../935-observed-wall-cad-20261104/README.md).
The [aggregate receipt](rejected-freeform.json) binds the plan, controls, native
verification, residual audit, runtime, sources and private manifest.

## Requirement and input admission

The functional goal requires faithful geometry before design optimization.
The earlier frozen cylindrical parameterization of observed region 1 exceeds its
exploratory projection screen. This experiment asks whether one compact freeform
surface can preserve that acquired wall more closely. It does not infer anatomy,
hidden galleries, a machining allowance or a manufacturing process.

The candidate uses the existing region-1 source mask: 1,700 original triangles,
1,032 vertices, 841 training vertices and 191 disjoint evaluation vertices.
Original vertex IDs and the registered modulo-five split are unchanged. Contract,
partition, source arrays and previous preparation hashes are checked before the
fit. The upstream native-source, zero-fold, nondegenerate-UV and nonoverlapping-
projection checks must pass. Region 2 has folded UV triangles and is not fitted.
Region 4 has no admitted source pair and is not invented. The source selection
was informed by previous geometric fits, so this is conditional within-scan
evaluation, not independent specimen metrology or unbiased segmentation truth.
The axial parameter normalization uses the complete acquired mask to define its
observed domain, including evaluation-point extrema. Only the 841 training
coordinates enter the coefficient solve. The held-out scores are therefore a
transductive within-scan check, not a blind generalization test.

## Registered model and acceptance screen

The model is a periodic cubic tensor-product B-spline with **16 angular × 6 axial
independent poles**. The angular knots are uniform, the axial basis has two
interior knots, and three angular pole rows wrap to impose positional and first-
derivative continuity. It is fitted once by linear least squares in Cartesian
coordinates. The previous scan frame is used only for parameter coordinates;
its origin and axes are not refitted. No degree, knot-count, regularization or
source-selection sweep is performed.

The trial plan is written before fitting the acquired points. It requires rank
96, condition number at most 1e8 and a maximum **0.01 mm** point-correspondence
error over all source vertices, including held-out points. This is a stricter
digital-preservation research screen than the previous 0.4 mm exploratory
primitive screen. It is not a physical interface tolerance, machining tolerance
or calibrated uncertainty of the scan. The prior cylindrical study and its
acceptance purpose are not retroactively changed.

The design matrix has full rank and condition number 67.80, so the recorded
failure is a geometric fidelity failure rather than a rank or conditioning
refusal. Independent analytic controls use a known lobed/tapered circular wall
with separate evaluation coordinates. Maximum analytic held-out error is
0.0007722 mm and periodic position error is zero within recorded arithmetic.

## Native independent result

A separate verifier imports no fitter function. It checks original source-ID
membership and disjoint splits, recomputes parameter coordinates from acquired
points, checks unchanged frame parameters/registered knots, constructs a native
OCCT B-spline from the saved poles, and evaluates the actual native geometry.

| Native comparison | Points | P95 / maximum (mm) | Above 0.01 mm |
|---|---:|---:|---:|
| Corresponding parameter, all source vertices | 1,032 | 0.125324 / 0.338390 | 940 |
| Corresponding parameter, held-out vertices | 191 | 0.114002 / 0.291760 | 177 |
| Projection onto untrimmed parameter rectangle, all | 1,032 | 0.122203 / 0.327093 | 894 |
| Projection onto untrimmed parameter rectangle, held-out | 191 | 0.108172 / 0.284431 | 171 |

Native correspondence reproduces the fitter's recorded maximum within 1e-9 mm.
The projection calculation uses OCCT's tree extrema algorithm with a 1e-9
tolerance on the complete parameter rectangle. It is a diagnostic, **not a
source-trimmed surface, formal global-distance bound or manufacturing export**.
No unobserved rectangular surface is delivered as accepted geometry. The
predeclared correspondence gate alone is already sufficient to reject this
candidate; trimming, sewing, volume meshing and solver work are not launched.

Native controls reconstruct an independently specified R=5 mm periodic circular
approximation: radial error stays below 0.000322 mm, and a deliberate 0.6 mm
radial displacement is measured as 0.600034 mm. The candidate's positional and
first-derivative seam discrepancies are respectively 1.78e-15 mm and 1.33e-15 mm
per unit angular parameter. Continuity does not establish source fidelity.

## Residual localization and refusal controls

Source-indexed localization finds errors in all 12 edge-connected acquired
components. The main component has 1,680 faces, 1,005 vertices and 914 over-limit
vertices. Across the whole mask, **1,693 of 1,700 triangles** touch an over-limit
vertex, and 1,342 have all three vertices above the screen. Discarding a small
fragment would not rescue this model. Residuals are failures of the proposed
smooth representation, not evidence that the measured points are defective or
deletable outliers.

The source mask has 418 boundary edges and no nonmanifold edges. Its internal
dihedral P95 is 28.12 degrees, with 89 internal edges above 30 degrees. These are
observation statistics, not identified threads, ports or other functional
features. Any later piecewise reconstruction must retain and inspect such local
variation rather than erase it to make a smooth model pass. No such subsequent
reconstruction is claimed here.

Three executed refusal controls pass: changed source IDs are rejected before
output creation; a forged zero maximum/acceptance flag is rejected by native
geometry; and an existing verification directory is refused while its sentinel
remains unchanged. Failed verification never produces a successful report.

## Chain, privacy and reproduction

This is scan-derived CAD research in the existing STEP/FreeCAD branch, separate
from the [local CADAM/Qwen coupon service](../../architecture/cadam-local-qwen.md).
No AI model authored or approved this surface. PicoGK and the Gmsh/OpenFOAM/
CalculiX/Adamantine admission requirements remain unchanged. No volume, physics,
metal build or physical-validation gate advances from a rejected fit.

The private bundle is
`~/Developer/PorschePartsArtifacts/935-freeform-wall-20261104/`. It retains the
private poles/parameters, source IDs, residual arrays, reports, logs, source
snapshots, runtime and manifest. The original arrays, original native engineering
baseline and previous native review were rehashed unchanged. Public files contain
no acquired coordinates, connectivity, geometry, model weights or secrets.

Native verification and the residual/refusal audit ran under the retained macOS
policy denying non-loopback outbound connections, including their child
processes. The initial least-squares fit is not claimed to have used that sandbox.
There was no external CAD/model service, paid rental, supplier message or order.
Recorded runtime is Python 3.12.11, NumPy 2.5.4, SciPy 1.18.1 and
`cadquery-ocp-novtk` 7.9.3.1.1; the native binary hash is retained.

Replay from the repository root into a fresh private directory; never write into
the frozen bundle:

```sh
set -e
ARTIFACTS="$HOME/Developer/PorschePartsArtifacts"
SCAN="$ARTIFACTS/935-scan-tools-20261029"
CAD_PYTHON="$SCAN/engineering-20261029/cad-venv/bin/python"
ARRAYS="$SCAN/other-tools/exact-source-arrays.npz"
PAPER="$SCAN/paper-feature-section-pairs-20261029"
PREPARATION="$ARTIFACTS/935-observed-wall-cad-20261104/preparation-002"
SOURCE="$PWD/docs/research/935-freeform-wall-study-20261104/source"
POLICY="$PWD/docs/research/935-observed-wall-cad-20261104/source/local-only.sb"
REPLAY="$(mktemp -d "$ARTIFACTS/935-freeform-wall-replay.XXXXXX")"
"$CAD_PYTHON" "$SOURCE/fit_periodic_wall.py" \
  --arrays "$ARRAYS" --paper "$PAPER" --preparation "$PREPARATION" \
  --output "$REPLAY/trial-001"
/usr/bin/sandbox-exec -f "$POLICY" "$CAD_PYTHON" \
  "$SOURCE/verify_periodic_wall.py" --trial "$REPLAY/trial-001" \
  --arrays "$ARRAYS" --paper "$PAPER" --preparation "$PREPARATION" \
  --output "$REPLAY/verification-001"
/usr/bin/sandbox-exec -f "$POLICY" "$CAD_PYTHON" \
  "$SOURCE/audit_rejected_wall.py" --trial "$REPLAY/trial-001" \
  --verification "$REPLAY/verification-001" --arrays "$ARRAYS" \
  --paper "$PAPER" --preparation "$PREPARATION" --cad-python "$CAD_PYTHON" \
  --output "$REPLAY/audit-001"
```

Successful execution of these CLIs means the **rejection was verified**; the
JSON acceptance flags remain false. The overall faithful functional-metal goal
remains incomplete. Full observed geometry and component separation, unobserved
internals, independently measured interfaces, specimen material/load data,
qualified machine/process data and professional/physical validation remain
necessary. The previously delivered exact references are retained, not replaced.

The subsequent [exact source-facet CAD charts](../935-source-shells-20261104/README.md)
preserve the original observed detail and edge adjacency, while explicitly
separating source vertex point contacts into incident-face fans. Independent
actual-STEP and native FreeCAD checks pass for those open reference surfaces;
they do not create a complete head or reverse this freeform candidate's rejection.
