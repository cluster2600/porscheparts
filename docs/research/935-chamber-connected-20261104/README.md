# Chamber-search connectivity before smooth reconstruction

Status: executed and independently checked, 2026-11-04. All sixteen connected-
component plane/quadratic proposals still fail the fixed 0.01 mm digital
correspondence screen. No smooth surface is adopted. This is a new upstream
selection after the [full-mask rejection](../935-chamber-surface-admission-20261104/README.md),
not a replacement of its evidence or a change to its limits.

## Selection independent of fit outcomes

The [plan](plan.json) is fixed before execution. Decompose all eight original
masks using original shared triangle edges. Rank each mask's components by total
acquired triangle area, breaking exact ties by minimum original face ID. Select
exactly the first component from each region. A more favorable fit cannot choose
another component. All eight selections and their full parent ledgers are
written before any model is fitted. Controls explicitly test area ranking over
face-count ranking and the face-ID tie rule.

The eight parent masks contain **24,415 distinct source faces in 1,400 mask
components**. The selected eight components contain **14,023 source faces**;
the other **10,392 faces in 1,392 components remain retained observations**.
They are outside this fitting selection, not deleted physical geometry. These
counts do not identify head bodies, valves, holes or attached hardware.

No acquired coordinate, original face or index is altered. The original source
topology helper and the previous plane/quadratic fitter are reused byte for
byte, with pinned hashes. The original-ID holdout split, area-weighting rule,
three/six coefficients, minimum support and full-triangle Bernstein check are
unchanged. No higher degree, alternative split, crop adjustment or threshold
sweep is attempted.

## Results

| Historical region | Selected faces | Plane maximum (mm) | Quadratic maximum (mm) |
|---|---:|---:|---:|
| 0 | 2,697 | 0.345732 | 0.399687 |
| 1 | 1,884 | 0.147025 | 0.118762 |
| 2 | 2,086 | 0.398817 | 0.222321 |
| 3 | 509 | 0.169273 | 0.169621 |
| 4 | 820 | 0.152649 | 0.149753 |
| 5 | 2,653 | 0.336622 | 0.402059 |
| 6 | 1,674 | 0.164763 | 0.147114 |
| 7 | 1,700 | 0.249766 | 0.368845 |

These are full selected-mask maxima for the **fixed same-UV correspondence**.
The complete-triangle bounds coincide with acquired vertex maxima in these
sixteen cases. Each proposal demonstrably exceeds the predeclared correspondence
limit at an actual source vertex; rejection does not depend on a loose bound.
These maxima are not lower bounds on nearest-surface or Hausdorff distance, and
0.01 mm is not an accepted physical tolerance or scanner uncertainty.

Separation removes the previous mixture of disconnected regions from each fit,
but the input domain, training population and area weights change. Lower errors
on a smaller selected domain are not a controlled model-performance improvement
or evidence that unselected geometry can be discarded. The best full-mask
maximum remains 0.118762 mm, above the fixed digital screen. No valve-seat plane,
axis or complete chamber is accepted.

The inherited graph check applies only to projected original triangles. It does
not close gaps or extend hidden surfaces. Projection injectivity, admissible
trim topology and actual native exports would still need separate checks even
if the digital bound passed. No new native CAD, head solid or solver domain is
created by this trial; the [existing exact source reference](../935-fourth-region-cad-20261104/README.md)
remains unchanged.

## Independent verification and provenance

The verifier builds source adjacency with SciPy rather than the producer's
native-chart union-find, reconstructs every parent partition and area ranking,
checks all selected original memberships, and recomputes conditional training
frame/normal equations, source-ID holdout counts, scores and every triangle's
Bernstein certificate via the retained independent midpoint evaluator. All five
verification groups pass on eight components and sixteen proposals. Five
reason-specific controls refuse a wrong selected component, lost parent
partition, forged score, forged acceptance flag and changed source-split count.
Invalid inputs publish no successful verification result.

Area weights and inherited masks use complete selected-source geometry,
including held-out coordinates. Training-only coordinate checks are conditional
on those fixed weights; the evaluation remains transductive within the scan.
It is not independent metrology. Original OBJ and latest source-reference FCStd
hashes remain unchanged.

The two successful stages use the existing
[local-only sandbox](../935-observed-wall-cad-20261104/source/local-only.sb), with
600-second bounds. Study and verification take 1.32 s and 0.38 s respectively on
the Mac. Refusal controls are separate and have no sandbox claim. No external
model/CAD service, paid compute, supplier contact or fabrication order is used.

Private bundle:
`~/Developer/PorschePartsArtifacts/935-chamber-connected-20261104/`.
It retains original component membership ledgers, selected source IDs, model
parameters, certificates, actual argv/logs, controls and a manifest. Public Git
retains code, this fixed plan and the [aggregate receipt](connected.json), without
geometry, original IDs, model coefficients or raw fields.

Use the existing CAD Python environment (Python 3.12.11, NumPy 2.5.4, SciPy 1.18.1,
OCP 7.9.3.1 for the frozen topology helper) and fresh output paths:

```sh
"$CAD_PYTHON" "$SOURCE/study_connected.py" \
  --arrays "$EXACT_ARRAYS" --engineering "$ENGINEERING" \
  --intersections "$ORIGINAL_INTERSECTION_INDEX" \
  --fitter "$FROZEN_CHAMBER_FITTER" --topology "$FROZEN_TOPOLOGY_HELPER" \
  --plan "$PLAN" --output "$NEW_STUDY"
"$CAD_PYTHON" "$SOURCE/verify_connected.py" \
  --arrays "$EXACT_ARRAYS" --engineering "$ENGINEERING" --study "$NEW_STUDY" \
  --evaluator "$FROZEN_INDEPENDENT_EVALUATOR" --output "$NEW_VERIFICATION_JSON"
```

Actual job receipts retain `gtimeout`/`sandbox-exec` wrappers. Do not mutate frozen
helpers or rerun writers in a completed bundle. The [documented engineering chain](../../architecture/cadam-local-qwen.md)
retains all geometry, physical, material and manufacturing gates. Source
connectivity improves selection provenance; it does not supply hidden passages,
specimen dimensions, alloy or process calibration. The full goal remains active.
