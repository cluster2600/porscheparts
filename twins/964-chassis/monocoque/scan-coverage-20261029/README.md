# Source-preserving underbody workspace for central-cell reconstruction

**29 October 2026: executed locally; observed source geometry, not a new carbon
monocoque.** After the [whole-body architecture rejection](../shape-review-20261029/README.md),
this increment establishes a traceable spatial workspace from the owner's scan.
It supplies the observations against which the central cell can be reconstructed.

The original scan and its retained registration were hash-admitted. The private
OpenUSD assembly contains all **4,684,929 original oriented triangles exactly
once**, with their original registered coordinates. Seven search windows retain
**2,169,002 triangles**; the other **2,515,927** remain visible as context.
These counts describe the input partition, not the proportion of a complete
vehicle or a completed reconstruction. No smoothing, repair, rescaling,
hole-filling, decimation or synthetic body surface was applied.

## Delivered and inspected

The private output is `work/964-cell-scan-coverage-20261029/review-002/`:

| File | Content |
|---|---|
| `observed-underbody.usdc` | Millimetre, Z-up workspace with separately selectable source-face groups and original vertex/triangle IDs |
| `underbody.png` | Complete underside in context, with colour-coded search windows |
| `oblique.png`, `left_side.png` | Assembled mechanical context and the missing upper-cell coverage |
| `central_floor.png` | Deliberate close-up of the floor/central-route search regions |
| `sections.png` | Three transverse and three longitudinal original-triangle intersection plots |
| `*.npz` | Private section endpoints and source triangle IDs, without gap joining |
| `underbody-orbit.mp4` | 1600 x 1000, 24 fps, 120 frames, five-second local orbit |

The images and movie are rendered by VTK **from the reopened USD**, not by
Omniverse RTX. They are computed scan views, not photographs of a manufactured
part. The whole-underbody view and three other views were inspected, along
with the six-section plot and decoded video frames 0, 30, 60 and 90.
[media-review.json](media-review.json) records the observations and hashes.
Raw scan-derived geometry, image files and video stay outside Git while
redistribution rights remain unconfirmed; this folder commits source, settings,
aggregate receipts and hashes only.

The first private attempt is retained but rejected: camera updates did not
refresh PyVista's off-screen buffer, so all four screenshots repeated the first
view. The corrected run explicitly renders after each camera update and rejects
identical inspection views or quarter-orbit frames. The successful geometry
check on that first attempt did not make its media acceptable.

## What the regions mean

| Region | Original triangles | Interpretation after visual review |
|---|---:|---|
| FloorLeftSearch | 175,467 | Ribbed lower surface visible; interior geometry and material unverified |
| FloorRightSearch | 174,553 | Ribbed lower surface visible; interior geometry and material unverified |
| CentralRouteSearch | 157,129 | Long lower surface visible; no tunnel interior, mechanism or clearance established |
| SillLeftSearch | 101,214 | Edge/sill search only; the geometric window is not a component boundary |
| SillRightSearch | 123,238 | Edge/sill search only; the geometric window is not a component boundary |
| FrontTransitionSearch | 667,347 | Mixed assembled surfaces; further body/mechanical separation required |
| RearTransitionSearch | 770,054 | Mixed assembled surfaces; further body/mechanical separation required |
| Context | 2,515,927 | Every face outside the admitted windows, including crossing triangles |

The bounds in [regions.json](regions.json) are inspection choices in the
existing provisional frame. They are not new measured part limits, datum
coordinates or tolerances. A face is assigned only if all three original
vertices lie within a window; first matching window owns it. Crossing triangles
are preserved in context instead of being cut. The source correspondence
therefore remains exact even at the coloured boundaries.

Six explicit empty requirement nodes retain the unestablished interior
footwells, tunnel, front/rear bulkheads, door interfaces and upper load paths.
They carry no fabricated surfaces. Rendering the reverse side of a scanned
sheet does not reveal its interior side or thickness.

## Independent checks and numerical scope

The authoring script is [build_review.py](build_review.py). The separate reader
[verify_review.py](verify_review.py) does not call its partition or section
functions. It recomputes selection from triangle extrema, opens the USD afresh,
checks every source index, coordinate and oriented face, and compares the
section endpoints with a separate edge-intersection calculation.

[verification.json](verification.json) records a passing comparison of every
source triangle and **11,868 section segments**. The six section counts are
1,407 / 1,385 / 1,363 / 2,492 / 2,483 / 2,738. Numerical plane-touching triangles
would be counted and excluded, rather than ambiguously stitched; none occurred
in these cuts. The `1e-6 mm` plane tolerance is a numerical comparison setting,
not scanner accuracy or a production tolerance.

Strict native `usdchecker` passed. Ten focused controls exercise crossing
triangles, overlapping windows, hand-computed plane intersections, coplanar
exclusions, output isolation, reopened USD fidelity, shifted/reversed source
geometry, an invented section endpoint and a false interior-completion flag.
Four controls require the native OpenUSD Python runtime; run them explicitly
if the general test environment lacks `pxr`.

The original tyre-derived frame is still provisional. No body hardpoint,
installed gearbox, model year, material, structural thickness, laminate,
force path or manufacturing process is qualified by these checks. No new FEA,
PicoGK solid reconstruction or native Omniverse job was run for this increment.

## Reproduce

Use the local Python environment with NumPy, PyVista/VTK, Matplotlib and
OpenUSD, plus `usdchecker`, `ffmpeg` and `ffprobe`. The executed versions and
input hashes are in [run.json](run.json). `SCAN` below must point to the retained
original OBJ; do not use a repaired or rescaled substitute. `ARRAYS` must point
to the byte-identical registered arrays from the
[model-year replay](../../model-year-review-20261029/README.md).

```sh
PYTHON=work/omniverse-venv/bin/python
SOURCE=twins/964-chassis/monocoque/scan-coverage-20261029
ARRAYS=work/964-model-year-review-20261029/replay-001
OUTPUT=work/964-cell-scan-coverage-new

"$PYTHON" "$SOURCE/build_review.py" --scan "$SCAN" \
  --vertices "$ARRAYS/verts_vehicle.npy" --faces "$ARRAYS/faces.npy" \
  --output "$OUTPUT"
"$PYTHON" "$SOURCE/verify_review.py" --scan "$SCAN" \
  --vertices "$ARRAYS/verts_vehicle.npy" --faces "$ARRAYS/faces.npy" \
  --review "$OUTPUT"
"$PYTHON" -m unittest discover -s tests -p test_964_scan_coverage.py -v
```

The output must be a new directory under private `work/`; failure does not
publish a partial bundle. The verifier refuses to overwrite its receipt.

## Next reconstruction input

Use these source-indexed regions to identify actual body surfaces and their
boundaries before fitting CAD. Obtain the missing interior and upper-cell
surfaces and the identified mounting interfaces described in the existing
[survey](../../interface-measurement-plan.md). The available underside and body
control measurements remain useful; they do not justify arbitrary interior
volumes. Keep C2, C4 and 993 applicability separate. The requested final
monocoque, tooling, mechanical validation and completed Omniverse review remain
open.
