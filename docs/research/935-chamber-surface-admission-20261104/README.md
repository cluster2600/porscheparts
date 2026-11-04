# Historical chamber masks: smooth-surface admission

Status: executed and independently verified, 2026-11-04. **None of sixteen
plane/quadratic proposals passes the existing 0.01 mm digital reconstruction
screen.** No proposal is adopted or exported as native CAD. The original acquired
surfaces and the [latest exact reference](../935-fourth-region-cad-20261104/README.md)
remain unchanged. The full faithful functional-metal head is still incomplete.

## Purpose and fixed inputs

The [earlier engineering study](../935-scan-engineering-20261029.md) retained
eight source-face masks named as chamber planar candidates. Their convex-hull
circles did not establish valve-seat rims or axes. This trial asks whether those
same masks support a plane or quadratic graph without smoothing away observed
details. The names remain historical search labels, not anatomical evidence.

The [plan](plan.json) precedes fitting. Every face in all eight frozen masks is
included; there is no fit-dependent trimming, replacement mask, degree sweep or
changed threshold. Original array, mask, intersection-index and retained topology
helper hashes are required. All eight inputs pass the recorded intersection-index
screen and source-chart topology audit before fitting. They are eligible for
this diagnostic experiment, not qualified complete head surfaces.

The region masks are fragmented. Their numbers of original-edge-connected
components are 42, 851, 7, 81, 91, 80, 177 and 71. These are **mask components**,
not physical parts, valves or independent holes. A normal/distance-selected
mask is not automatically a single continuous trimmed CAD face.

## Fit and complete-triangle check

Original vertex IDs divisible by five are held out; all other IDs train the
fit. Each vertex receives one third of its incident acquired triangle areas.
Only training-point coordinates enter the weighted principal frame, centering,
chart normalization and least-squares equations. However, the inherited masks
and area weights use full-source geometry. This remains a **transductive,
within-scan evaluation**, not independent physical metrology or unbiased sensor
validation. The verifier's training-only checks are conditional on those fixed
area weights.

Fit a three-coefficient affine graph and a six-coefficient quadratic graph in
that fixed local frame. Evaluate each graph only over the union of projected
original triangles, without filling gaps or extending the domain. Projection
injectivity, trim topology and native export would require separate admission;
none is claimed here.

A vertex-only check can miss a quadratic bulge between perfectly matched
vertices. Over one original triangle, the difference between the quadratic graph
height and the acquired piecewise-linear height is a degree-two polynomial in
barycentric coordinates. Write its six Bernstein coefficients as the three
vertex residuals and three edge coefficients. The associated basis functions are
nonnegative and sum to one, so the largest absolute coefficient bounds the
height difference at **every point of that original triangle**. In the
orthonormal frame this is a Euclidean correspondence bound. Using precisely the
projected source-triangle domain provides a correspondence in both directions;
this is not a claim that the bound equals the exact Hausdorff distance or that
the projected patches form a valid native surface.

The producer obtains edge coefficients from quadratic curvature. The independent
verifier instead evaluates residuals at edge midpoints and inverts their
Bernstein interpolation formula. Both check every acquired triangle. Computation
uses double precision; this is not outward-rounded interval arithmetic or a
physical tolerance certificate. Three synthetic controls cover an affine graph,
constant displacement and a quadratic with exact vertices but nonzero interior
error. The last control prevents accepting a fit merely because its corners
match.

## Measured outcome

P95 uses only the fixed held-out source vertices. Maxima and complete-triangle
bounds cover the entire registered region, including training vertices.

| Historical region | Faces | Mask components | Holdout P95, plane / quadratic (mm) | Full-mask maximum, plane / quadratic (mm) |
|---|---:|---:|---|---|
| 0 | 2,828 | 42 | 0.282769 / 0.204415 | 0.333147 / 0.551997 |
| 1 | 7,445 | 851 | 0.257406 / 0.270923 | 0.711325 / 0.706215 |
| 2 | 2,093 | 7 | 0.327034 / 0.323628 | 0.466740 / 3.712587 |
| 3 | 1,944 | 81 | 0.293449 / 0.279412 | 0.385290 / 0.421145 |
| 4 | 1,287 | 91 | 0.306920 / 0.494727 | 0.384080 / 0.969112 |
| 5 | 2,998 | 80 | 0.305104 / 0.335602 | 0.358126 / 0.788597 |
| 6 | 2,499 | 177 | 0.066697 / 0.063659 | 0.330317 / 0.310152 |
| 7 | 3,321 | 71 | 0.280050 / 0.272664 | 0.428828 / 0.522716 |

For these actual sixteen fits the complete-triangle coefficient bound equals
the largest vertex residual; no larger interior bound is discovered. Every fit
already demonstrably fails 0.01 mm at acquired vertices. The rejection therefore
does not depend on conservatism of the Bernstein bound. Vertex failures refer
to the fixed same-UV correspondence; they are not lower bounds on nearest-surface
or Hausdorff distance. The threshold is the
existing digital study screen, **not** a selected physical manufacturing
tolerance or an estimate of scanner accuracy.

Quadratics worsen the full-mask maximum in six of eight regions. Region 2 is a
clear reason to retain maxima: its quadratic held-out P95 is 0.323628 mm while
one acquired training vertex differs by 3.712587 mm. Low area weight does not
remove that source point from inspection. No degree, split, region or limit is
changed after seeing these results. This does not show that the real head lacks
smooth surfaces; it rejects these two representations on these fixed masks.

## Independent verification and refusal controls

The verifier imports no fitting code. It requires the separately pinned original
engineering manifest, checks all original face/vertex memberships, independently
reconstructs mask connectivity, and checks the orthonormal training frame,
normalization, weighted normal equations, held-out scores, every full-face bound
and acceptance flags. All six verification groups pass across eight regions and
sixteen fits. Five reason-specific controls refuse forged scores, acceptance
flags, per-face certificates, changed coefficients and lost source membership.
Invalid inputs produce no successful verification artifact.

Both successful stages run under the existing
[local-only sandbox](../935-observed-wall-cad-20261104/source/local-only.sb) with a
600-second process bound. The initial study takes 1.16 seconds on the Mac; the
verifier runtime is recorded in the [aggregate receipt](admission.json). Refusal
controls run separately and do not inherit that sandbox claim. The original OBJ
and latest native reference are rehashed unchanged. No paid compute, external
model/CAD service, supplier contact or fabrication order is used.

## Reproduction and next admissible work

Use the existing CAD Python environment (Python 3.12.11, NumPy 2.5.4, SciPy
1.18.1, OCP 7.9.3.1 for the retained topology helper). The helper performs source
admission; it does not construct CAD in this experiment. Private bundle:
`~/Developer/PorschePartsArtifacts/935-chamber-surface-admission-20261104/`.
It retains the plan, sources, actual bounded argv/logs, model parameters,
per-triangle certificates, independent verification, refusals and file manifest.
Public Git retains only code, plans, hashes and aggregate results.

```sh
"$CAD_PYTHON" "$SOURCE/study_surfaces.py" \
  --arrays "$EXACT_ARRAYS" --masks "$ENGINEERING/chamber-candidates" \
  --intersections "$ORIGINAL_INTERSECTION_INDEX" --helper "$RETAINED_BUILDER" \
  --plan "$PLAN" --output "$NEW_STUDY"
"$CAD_PYTHON" "$SOURCE/verify_surfaces.py" \
  --arrays "$EXACT_ARRAYS" --engineering "$ENGINEERING" \
  --study "$NEW_STUDY" --output "$NEW_VERIFICATION_JSON"
```

Use fresh output paths; do not rerun writers in the frozen bundle. Actual jobs
wrap these commands with `gtimeout` and `sandbox-exec`. Any subsequent geometric
segmentation is a new upstream selection with its own predeclared contract and
source membership, not an undisclosed replacement for these rejected masks.
Connectivity and admissible trim domains must be resolved before increasing
model flexibility. The [CADAM/Qwen architecture](../../architecture/cadam-local-qwen.md),
PicoGK route and independent solver/process gates remain unchanged. No complete
bare-head domain, accepted functional interface or manufacturing file follows
from this diagnostic study. The full goal remains active.
