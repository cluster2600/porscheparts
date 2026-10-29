# 935 scan — first paper-guided feature experiment

Status: completed local analytic experiment. It retains four planar fits and
three short cylinder hypotheses; it does not replace the existing CAD baseline,
complete the head or admit physics/manufacturing work. Private geometry and
source-ID selectors remain outside Git.

## Research translated into an experiment

[Point2CAD (CVPR 2024)](https://openaccess.thecvf.com/content/CVPR2024/html/Liu_Point2CAD_Reverse_Engineering_CAD_Models_from_3D_Point_Clouds_CVPR_2024_paper.html)
connects surface fitting and topology reconstruction. Its published code requires
points labelled by individual surface; the four broad geometric regions in our
[previous study](935-scan-engineering-20261029.md) are not those labels. This
experiment prepares and inspects limited analytic surface candidates. It does
not execute Point2CAD's neural fitting, intersection/clipping or complete pipeline.

The [October 9, 2026 hole-detection preprint](https://arxiv.org/abs/2610.13466v1)
supplies an area-weighted cavity statistic in equations 10–12. We independently
implement that statistic and a deliberately restricted straight-cylinder CAD
adapter. The paper's general face-set search, expansion, learned models and
benchmark are not reproduced. No published benchmark accuracy is claimed.

## Input admission and fixed checks

The original OBJ and decoded arrays must match the existing hashes. Units remain
the owner's confirmed **1 OBJ unit = 1 mm**. The frozen baseline manifest and each
consumed mask, frame, feature record and STEP file are verified before execution.
Output inside the repository or an existing study directory is refused.

Each run writes its contract and all source-ID partitions before fitting.
Training uses original vertex IDs with remainder 1–4 modulo 5; evaluation uses
remainder 0. Overlapping region memberships are excluded from every fit. Duplicate
coordinates are not welded. Evaluation points never enter the fitting functions.

The exploratory cylinder gates are P95 residual at most 0.4 mm, at least 3 mm
observed axial span, at least 300 degrees of angular support in each of three
axial bins, and an axis within 15 degrees of the frozen search direction. They
are study checks, not manufacturing tolerances. Source-plane masks and the
section-pair corridor use previous fits, so this is conditional within-scan
evaluation rather than independent sensor metrology or unbiased segmentation
ground truth.

## Two recorded input policies

| Policy | Input | Outcome |
|---|---|---|
| Broad ROI | Fixed radius/depth/normal search around four historical passage hints | Four planes retained; all four cylinder fits rejected, with P95 approximately 0.80–3.70 mm |
| Frozen section pairs | Only the three previously retained circle pairs at C = −91 and −94; no axial extrapolation; a radial corridor equal to the 0.4 mm check limit | Four planes and three short cylinder hypotheses retained; fourth passage has no admitted pair and is not fitted |

The second policy changes the upstream surface-selection evidence rather than
relaxing the fit gates. It is a separate recorded experiment, not an undisclosed
replacement of the rejected broad run. Both attempts and their source masks
remain available.

| Passage candidate | Held-out points | Cylinder P95 (mm) | Frozen-circle axial reference P95 (mm) | Observed axial span (mm) |
|---|---:|---:|---:|---:|
| 1 | 191 | 0.2002 | 0.1915 | 3.7648 |
| 2 | 211 | 0.2391 | 0.2947 | 3.8679 |
| 3 | 145 | 0.1791 | 0.1705 | 3.5426 |

The reference column extrapolates the frozen section-circle candidate along its
search axis onto the identical evaluation points. It is a numerical comparison,
not a pre-existing cylindrical CAD wall or physical inspection. Only candidate 2
improves this metric. Additional axis parameters do not provide a consistent
improvement, so none of these hypotheses automatically replaces the baseline.

## Topology controls and abstention

Six native CAD controls cover a plate, through-hole, blind hole, convex boss,
two through-holes and an unsupported stepped blind cavity. Fixture volumes are
checked against independent analytic values. The adapter identifies the simple
cavities, rejects the boss and abstains on the unsupported step. A separate
partial-face regression verifies that an isolated rim cannot establish depth.
Periodic seam edges are counted by their two uses, even when both uses belong
to the same face. A reversed solid with negative oriented volume is refused;
its normals cannot provide the required outward-orientation evidence.

The actual baseline contains 13 open faces and zero solids. Its 1,882 internal
trim wires yield no circular rim under the registered size/shape checks. These
wires include support-mask fragmentation; their number is not a physical hole
count. Solid-based through/blind classification is refused for the whole input.

## Deliverables and independent checks

The section-pair run exports 64,213 unchanged original training vertices with
seven surface-candidate labels in `(x, y, z, surface_id)` form. The other
1,217,395 original vertices are not exported: they include evaluation points and
unassigned geometry. This is a partial labelled dataset, not a complete head
segmentation or proof that Point2CAD can reconstruct it.

The separate read-only validator checks the registered contract/partition hashes,
all source-ID memberships and disjoint splits, exported coordinates/labels, and
held-out distances using an expression different from the optimizer and the
initial inspector. It also recomputes angular support and retention. Regression
tests reject forged scores, angular coverage, acceptance flags and lost/leaked
evaluation points. The fit thresholds and original frozen evidence are unchanged.

Private study directories under
`~/Developer/PorschePartsArtifacts/935-scan-tools-20261029/` are:

- `paper-feature-study-20261029/`: broad run, including all rejected cylinders.
- `paper-feature-section-pairs-20261029/`: section-bounded run and labelled points.
- `paper-feature-campaign-20261029/`: audit plots, reports, source snapshots and hashes.

Public drivers contain no private geometry:

```sh
"$STUDY_PYTHON" -m unittest discover -s tests -p 'test_scan_feature*.py' -v
"$STUDY_PYTHON" -m scripts.study_935_paper_features \
  --source "$SOURCE_OBJ" --arrays "$SOURCE_ARRAYS" --baseline "$BASELINE" \
  --output "$NEW_PRIVATE_OUTPUT" --support-policy frozen_section_pairs
"$STUDY_PYTHON" -m scripts.validate_scan_feature_study \
  --study "$NEW_PRIVATE_OUTPUT" --arrays "$SOURCE_ARRAYS" --baseline "$BASELINE" \
  --contract-sha256 "$REGISTERED_CONTRACT_SHA256" \
  --partitions-sha256 "$REGISTERED_PARTITIONS_SHA256"
```

Use the existing NumPy/SciPy/OCCT environment. No pretrained weights, GPU rental,
upstream code redistribution or solver execution is required. Keep expected
contract/partition hashes with the run record. Replays use new output directories;
do not overwrite frozen predecessors. The next technical question is whether
additional surface classes and connected trim topology can be recovered without
inventing missing observations; these results do not answer it yet.
