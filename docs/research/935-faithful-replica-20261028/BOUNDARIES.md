# Observed boundary inventory — 28 October 2026

The full original scan contains **928 disconnected boundary curves comprising
99,876 edges**. Every curve has simple-cycle graph topology: its vertices have
boundary degree two. This does not mean that the surface is closed, nor that a
curve is geometrically simple, planar, a missing patch or a functional opening.
Self-intersections have not been evaluated.

Only four vertices have exactly duplicated coordinates. These do not explain the
large number of open edges; there is no basis for treating the missing surface
as a trivial duplicated-vertex seam. Of the 928 curves, 123 have at most ten
edges. Size alone does not authorise filling a curve.

## Reproducible inspection input

The new [inventory script](../../../scripts/inventory_935_scan_boundaries.py)
reuses the frozen auditor's topology extraction. It refuses an unexpected source
hash and an existing output directory. It leaves all source coordinates and
triangles unchanged. No millimetre conversion, smoothing or hole filling occurs.

```sh
python scripts/inventory_935_scan_boundaries.py "$SOURCE_OBJ" "$NEW_OUTPUT"
```

The output contains four private payloads plus a SHA-256 manifest:

- `source-boundary-edges.npy`: original OBJ vertex-index pairs;
- `edge-component-labels.npy`: curve assignment for every corresponding edge;
- `review.csv`: one row per curve, ready for human review;
- `inventory.json`: full bounds, graph properties and least-squares plane residuals.

Component IDs follow the original vertex ordering and are stable when the same
edge rows are reordered. They must not be transferred to a remeshed or altered
scan. Plane residuals describe a contour fit, not a machined datum or measurement
uncertainty; collinear/point-like contours cannot define a plane and have null
plane-residual fields. A noisy scan of a nominal plane may have numerical rank
three. No nominal interface is accepted from this test.

Kali1 executed the inventory against the original hash. All four retrieved
payloads match their manifest. The [execution receipt](boundary-inventory-execution.json)
contains aggregate results and hashes; coordinates, edge arrays and full review
records remain outside Git. Nine focused tests passed on Kali1, including the
five new cases for curve indexing, branched boundaries, invalid edges, degenerate
plane fits and incorrect source identity. Existing scan-audit code and receipts
were preserved.

## Reconstruction decisions still required

For each curve, examine the indexed source faces and neighbouring surfaces and
record a classification, its evidence and uncertainty. Distinguish a functional
opening, interrupted scan coverage, contact with separate hardware and an
unresolved region. An observed contour alone does not establish the geometry of
the surface beyond it. An inferred patch needs a separate candidate, a source
mask, deviation checks and appropriate independent evidence before admission.

**0/928 contours have an accepted physical classification; 0 were filled.**
The older planar hardware-cut script removes protrusions as well as hardware,
so its output is not admitted as semantic head/stud separation for this replica.
This inventory makes the unresolved regions individually addressable; it does
not close the faithful-CAD, simulation or manufacturing gates. No Vast resource
was created and task spending remains USD 0.
