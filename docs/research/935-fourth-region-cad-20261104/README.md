# Fourth search region: exact acquired-surface CAD

Status: constructed and independently checked, 2026-11-04. This advances the
[fourth-passage source audit](../935-fourth-passage-audit-20261104/README.md) into
a private native CAD reference. The earlier circular proposals remain rejected.
This region's physical identity, mounting role and tolerances remain unaccepted.
No cylinder, hidden surface or closure is inferred.

## Fixed selection and upstream admission

The [selection plan](selection-plan.json) was written before measurement and CAD
construction. Its search box comes from all three independently replayed legacy
profiles, with a 1 mm A/B search margin and the original outer section planes.
That margin is a crop parameter, not a physical dimension or tolerance.
Whole original triangles with overlapping bounding boxes are eligible. Keep
every source-edge-connected eligible component containing an original profile
face. No clipping, normal filtering, circle fit or coordinate adjustment is used.
Do not interpret this search box as an exact body/hardware separation.

The fixed rule finds **2,790 acquired faces / 1,536 original vertices**, in one
edge-connected component. All original seed faces are retained. The mask has no
zero-area triangles, ambiguous coincident vertices or faces in the original
indexed intersection inventory. It passes the predeclared 60,000-face local CAD
bound. The native builder additionally checks winding, edge manifoldness and
vertex fans. No fallback mask or adjusted crop was tried.

## Actual geometry and boundary origins

The STEP preserves all 2,790 original triangles, 4,327 original edges, 1,536
vertices and their adjacency as **one open shell and zero solids**. In this
region no source vertex requires fan splitting, so original vertex-contact
topology is retained as well. The exact source-facet representation is a review
reference; it does not claim smooth parametric reconstruction of the full head.

There are **284 boundary edges**. A separate complete-original-mesh incidence
audit distinguishes **140 original scan-boundary edges** from **144 selection
cuts**. These are edge counts, not independent hole counts. Neither group is
closed. Treating every cropped-region boundary as an acquired hole would be
incorrect. A two-triangle shared-square fixture checks the distinction between
an original boundary and a selection cut.

The new region has zero original-face-ID overlap with the previous three wall
references and acquired axial sheet. The combined reference retains **21,472
unique acquired faces** in 24 open shells and five native feature objects.
This is 0.8707% of original triangle identities, **not head completion or new
physical scan coverage**. No observations have been created.

## Independent exported-byte and native checks

The retained independent verifier inspects the actual STEP against the original
arrays. All eight source/topology checks pass: every original triangle exactly
once, orientation, straight edges, full edge-to-face adjacency, vertex fans,
shell components, native validity and zero solids. The adapter explicitly counts
native solids and checks every native plane against all its triangle corners.
Recorded vertex-coordinate error is 0.0 mm, normal-dot error 4.44e-16 and maximum
plane/corner discrepancy 1.27e-11 mm. These floating-point digital checks are not
scanner accuracy or physical tolerance evidence.

FreeCAD 1.1.4 creates a **new** combined reference document, saves, closes and
reopens it. A separate read-only reopen checks all five features' placements,
counts, source-STEP hashes, shape validity and manufacturing flags, then exports
the actual saved fourth-region feature. The independent original-array checks
pass again on that STEP, with the same counts and errors. The FCStd checksum is
unchanged by the read-only export. The original OBJ and preceding native master
were freshly rehashed and remain unchanged.

The builder's shared-edge/point-contact controls and four reason-specific
refusals pass. Three additional controls reject output reuse, a wrong original
array hash and a substituted actual STEP, without publishing successful output
for invalid inputs. The [receipt](region.json) pins source and deliverable hashes.

Selection, CAD construction, positive STEP checks, boundary classification,
native creation and actual saved-feature export run under the existing
[local-only sandbox profile](../935-observed-wall-cad-20261104/source/local-only.sb),
each with a 600-second process bound. Selection takes 0.78 s, construction 2.57 s,
initial verification 2.53 s, native save/reopen 26.83 s, read-only native export
3.46 s and saved-export verification 2.42 s. These timings describe this local
run, not a benchmark against other tools. Refusal tests and illustrative rendering
are separate and do not inherit the sandbox claim.

## Reproduction

Use the existing CAD Python environment: Python 3.12.11, NumPy 2.5.4, SciPy
1.18.1 and OCP 7.9.3.1. Original arrays, frame, registered section archives and
the original intersection index must match the source-pinned hashes. Copy the
retained builder/verifier from
[source-shell helpers](../935-source-shells-20261104/source/) or use the
byte-identical private snapshots. Frozen outputs must not be overwritten.

```sh
"$CAD_PYTHON" "$SOURCE/select_region.py" \
  --arrays "$EXACT_ARRAYS" --frame "$SOURCE_FRAME" --sections "$REPLAYED_SECTIONS" \
  --intersections "$ORIGINAL_INTERSECTION_INDEX" --plan "$SELECTION_PLAN" \
  --output "$NEW_SELECTION"
"$CAD_PYTHON" "$SOURCE/reference_region.py" build \
  --selection "$REGISTERED_SELECTION" --arrays "$EXACT_ARRAYS" \
  --helper "$RETAINED_BUILDER" --output "$NEW_CAD"
"$CAD_PYTHON" "$SOURCE/reference_region.py" verify \
  --selection "$REGISTERED_SELECTION" --arrays "$EXACT_ARRAYS" \
  --helper "$RETAINED_VERIFIER" --step "$ACTUAL_STEP" --output "$NEW_VERIFICATION"
```

The CAD adapter pins the completed registered selection by hash; an exact replay
of the selector in a new path can have identical geometric NPZ bytes but a
different selection-report hash if provenance paths change. Do not bypass the
registration check. Preserve the fresh receipt, independently compare it, and
register a new adapter rather than modifying a frozen one. The private job
receipts retain the actual bounded/sandboxed argv used for this execution.

The generic native creator reads `PORSCHE_SOURCE_CHART_JOB`; each item specifies
a verified STEP, its hash, feature name and expected topology counts. The new
read-only exporter additionally reads `PORSCHE_REGION_ROUNDTRIP_DIR` and exports
`ObservedFourthRegion`. Native CLI exit status alone is insufficient: require
the expected report and completion marker, followed by the independent actual
STEP check.

## Deliverables and limits

Private bundle:
`~/Developer/PorschePartsArtifacts/935-fourth-region-cad-20261104/`.

| Private path | Purpose |
|---|---|
| `selection-001/selected-source.npz` | Exact selected source coordinates, indices and original IDs |
| `cad-001/observed-fourth-region.step` | Source-facet BRep reference with original topology |
| `deliverables/935-observed-fourth-region-reference.FCStd` | Five-feature combined native review document |
| `native-roundtrip/saved-fourth-region.step` | Actual saved feature exported for independent inspection |
| `boundary-audit-001/source-boundary-origins.npz` | Every selected boundary edge and its full-original incidence |
| `preview-002/observed-fourth-region.svg.png` | Private three-view illustration; red acquired boundaries, gold selection cuts |

The preview is visually checked for legibility and shows the incomplete acquired
wall. It is an illustrative projection, not a dimensional test or anatomical
classification. The earlier cropped thumbnail and its renderer are retained
privately; the accepted square-canvas preview avoids that display issue.
Geometry-bearing bytes and original IDs remain private; public Git contains
code, plans, hashes and aggregate numerical results only.

The [CADAM/Qwen architecture](../../architecture/cadam-local-qwen.md) keeps the
local coupon aid separate from this acquired-source reconstruction. Gmsh,
OpenFOAM, CalculiX and Adamantine receive no new admitted complete-head domain
from this open reference. All eight functional interfaces and the full-head,
material, process and physical-validation gates remain unclosed. No paid
resource, supplier contact, external model/CAD upload or fabrication order is
used for this increment. The full faithful-head goal remains active.
