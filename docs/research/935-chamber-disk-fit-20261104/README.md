# Compact-surface admission on verified acquired disk domains

Date: 2026-11-04. Status: executed and independently checked. **All eighteen
tested plane/quadratic proposals fail the fixed 0.01 mm digital correspondence
screen.** No native surface is adopted or source reference replaced.

This follows the [source disk atlas](../935-chamber-disk-atlas-20261104/README.md).
It tests representations of acquired data, with all geometry, physical and
manufacturing gates retained. The full faithful functional-metal head remains
incomplete.

## Fixed scope and support

The [plan](plan.json) precedes computation. Retain all **405** admitted disk
domains and **14,023** original faces. Reuse the unchanged SHA-pinned
[primitive fitter](../935-chamber-surface-admission-20261104/source/study_surfaces.py)
and [topology helper](../935-source-shells-20261104/source/build_source_shells.py),
with original vertex-ID modulo-five holdout, training-only principal frame and
scale, full-source triangle-area vertex weights and complete-triangle Bernstein
bounds. No domain is merged, cropped, discarded or selected using fit scores.

Nine domains, containing **11,680 acquired faces**, meet the unchanged minimum
of 40 training and 10 held-out vertices. They receive both diagnostic models.
The other **396 domains / 2,343 faces** retain their exact native acquired-facet
references; no support threshold is reduced to fit them.

The inherited masks, domain construction and area weights use full-source
geometry. This remains transductive within-scan evaluation, not independent
specimen metrology or general model-quality validation. Smaller-domain scores
cannot be interpreted as a controlled improvement over earlier full-mask fits.

## Fitted-domain result

The maxima below cover complete source triangles under the fixed same-UV
correspondence, not exact nearest-surface or Hausdorff distances.

| Historical region | Fitted domains | Fitted source faces | Plane bounds mm | Quadratic bounds mm |
|---|---:|---:|---|---|
| 0 | 1 | 2,147 | 0.349490 | 0.380013 |
| 1 | 1 | 1,616 | 0.147800 | 0.120027 |
| 2 | 2 | 1,704 | 0.392705; 0.095750 | 0.217123; 0.041248 |
| 3 | 1 | 461 | 0.165832 | 0.134966 |
| 4 | 1 | 752 | 0.156049 | 0.150004 |
| 5 | 1 | 2,036 | 0.328461 | 0.385991 |
| 6 | 1 | 1,601 | 0.164580 | 0.146860 |
| 7 | 1 | 1,363 | 0.243246 | 0.356914 |

Every proposal already exceeds 0.01 mm at an actual source vertex; these
rejections do not depend on a loose interior bound. The best proposal is a
quadratic on a 54-face domain in region 2, with a 0.041248 mm full-domain bound.
None is eligible for native export.

The fitter computes a new training frame for each domain. Its parent-frame
projection admission is therefore not inherited silently. All nine new
projections pass a complete shared-simplex contact check, independently repeated
with exact Fraction predicates on the rounded computed UV coordinates. This
does not turn floating matrix products into interval physical certificates.

The trial rejects these particular least-squares proposals on these fixed data.
It does not prove that every possible plane/quadratic fit is impossible, that a
valve surface has been identified, or that observed detail may be smoothed away.
The 0.01 mm screen remains a digital study limit, not a manufacturing tolerance
or scanner uncertainty.

## Source boundaries, cut seams and point contacts

Each fitted model is checked on every original edge in its domain boundary.
Two fixed diagnostic families, plane and quadratic, are also checked across all
**1,890** existing source-edge cuts and **3,130** original shared-vertex/domain
pairs. An unfitted neighbor uses its exact acquired geometry. Rejected models
remain in these diagnostics deliberately; this is not an adopted hybrid CAD
assembly and does not describe gaps in the original scan or exact references.

A graph polynomial composed with an original straight edge gives a vector
quadratic in the edge parameter. For power coefficients a, b, c, its Bernstein
control vectors are a, a+b/2 and a+b+c. The curve is their convex combination,
so their greatest norm bounds its norm for the entire edge. The producer uses
this power-basis expression; the independent verifier evaluates endpoint,
midpoint and endpoint positions and obtains the middle Bernstein vector from
those values. Recorded sample norms are lower witnesses, not exact peak values.
Arithmetic is double precision, without outward-rounded interval claims.

A fixed **0.000001 mm numerical continuity screen** applies before any native
export eligibility; it is not a selected physical interface tolerance.
Interior fitting alone would not justify source-boundary or joint continuity.
All native eligibility flags remain false.

The [post-fit contact interpretation](vertex-contact-analysis.json) identifies
**477** shared-vertex/domain pairs with no shared cut incident to that vertex.
This interpretation does not change selections or acceptance rules. In region
5, the quadratic diagnostic reaches 0.301284 mm at such a vertex pair, while its
largest cut-curve upper bound is 0.281398 mm. Region 1 likewise has larger
shared-vertex discrepancies than any cut-curve bound. Checking only shared cut
edges would miss these contacts.

These are errors of the proposed replacements. The exact BREP/FreeCAD source
references already preserve their original point/edge sharing and remain
unchanged. Any later reconstruction proposal needs explicit boundary and
shared-contact constraints, as well as full-domain deviation and actual native
export checks.

## Independent verification and controls

The [producer](source/study_disk_fits.py) retains all raw parameters, scores and
per-edge certificates privately. The [verifier](source/verify_disk_fits.py)
imports no producer code. It checks frozen source membership, all 405 domain
support decisions, conditional training frame/scale/normal equations, held-out
and full-source scores, every triangle's Bernstein coefficients, all new-frame
projection contacts, every source boundary, cut curve and shared vertex.

[Aggregate results](results.json) and [independent verification](verification.json)
record zero accepted proposals. Four [analytic curve controls](controls.json)
cover an exact source plane, constant displacement, an interior bubble with
zero endpoint discrepancy, and a rigidly transformed bubble. The bubble's
endpoint error is zero, its midpoint witness is 1 mm and its conservative bound
is 2 mm; the test prevents endpoint-only acceptance. Five reason-specific
refusals reject a changed source split, coefficients, source-boundary certificate,
cut certificate and native-admission flag. None writes a successful verification.

All successful acquired-data stages and controls run on the existing Mac CAD
Python 3.12.11 / NumPy 2.5.4 / SciPy 1.18.1 environment, under the retained
local-only sandbox with 600-second process bounds. Elapsed runtimes were not
instrumented. No model service, paid compute, scan upload, supplier contact or
fabrication order is used.

## Reproduction and preservation

Use fresh directories, the existing CAD Python environment and pinned helpers:

```sh
"$CAD_PYTHON" -B source/study_disk_fits.py --arrays "$EXACT_ARRAYS" \
  --parent "$FROZEN_DISK_ATLAS_BUNDLE" --plan plan.json \
  --fitter "$FROZEN_PRIMITIVE_FITTER" --topology "$FROZEN_TOPOLOGY_HELPER" \
  --predicate "$FROZEN_DYADIC_PREDICATES" --output "$NEW_STUDY"
"$CAD_PYTHON" -B source/verify_disk_fits.py --arrays "$EXACT_ARRAYS" \
  --parent "$FROZEN_DISK_ATLAS_BUNDLE" --plan plan.json --study "$NEW_STUDY" \
  --evaluator "$FROZEN_INDEPENDENT_POLYNOMIAL" \
  --chart-verifier "$FROZEN_RATIONAL_CHART_VERIFIER" --output "$NEW_VERIFICATION"
```

Actual invocations wrap these commands in gtimeout and sandbox-exec. Private
bundle: `~/Developer/PorschePartsArtifacts/935-chamber-disk-fit-20261104`.
Its [manifest receipt](private-receipt.json) pins code, actual invocations,
all raw fits/certificates, refusals and verification. Original OBJ, existing
native references, all 1,008 frozen parent files and retained helpers are
rehashed unchanged. No raw geometry, original indices or fitted coefficients
are committed. The [documented engineering chain](../../architecture/cadam-local-qwen.md)
and full functional-metal-head goal remain active.
