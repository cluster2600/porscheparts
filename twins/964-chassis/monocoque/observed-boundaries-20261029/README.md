# Observed boundaries before physical component extraction

**Executed locally: connected components cannot isolate the floor from the
central cover candidate.** Their dominant observations share a source component
containing 3,765,948 triangles. The previous rectangular search regions also
introduce artificial boundaries. Neither their outlines nor connected-component
extraction is admitted as a physical part contour for the replacement cell.

This is a geometry-input audit following the
[component identity review](../component-review-20261029/README.md). It changes
the reconstruction decision using the acquired scan, without fitting a surface,
adding thickness, repairing holes or inferring an interior. The requested
central monocoque, mould and structural validation remain open.

## Executed result

The original scan and both registered arrays were hash-admitted. The complete
4,684,929-triangle input has **7,086,599 unique edges**, **118,411 open edges**,
**176 edge-connected surface components**, no edges with more than two incident
faces and no same-direction two-face edges. One triangle has exactly zero area
when its stored coordinates are evaluated in Float64; its source indices are
retained privately. It was not deleted. Self-intersections and used-vertex
manifoldness were not checked, so the mesh is not declared valid for CAD or FEA.

The three existing floor/centre search regions retain 507,149 original faces:

| Search region | Region boundary edges | Original open edges | Edges opened by selection | Local surface components |
|---|---:|---:|---:|---:|
| FloorLeftSearch | 1,607 | 223 | 1,384 | 3 |
| FloorRightSearch | 1,871 | 469 | 1,402 | 2 |
| CentralRouteSearch | 3,479 | 2,114 | 1,365 | 5 |
| Total | **6,957** | **2,806** | **4,151** | — |

An original open edge belongs to one original triangle. A selection cut belongs
to two source triangles, only one of which is retained in that search region.
Shared region interfaces can therefore appear in more than one row; the total
counts region-edge occurrences, not unique edges of the complete scan.

An original open edge can be an acquisition gap, occlusion, physical rim or
other unresolved feature. It is not automatically a hole to fill. The selected
boundary graphs contain 96 simple cycles and one branched component; these are
topological observations, not 97 identified vehicle openings. Zero non-manifold
edges does not establish manifold vertices.

Of the regional faces, 175,271 left-floor, 174,546 right-floor and 156,969 centre
faces belong to the same 3,765,948-face source component. A shared mesh component
does not establish a structural joint between real parts: acquisition or
meshing may connect adjoining surfaces. It does establish why a whole-component
extraction would include unrelated body/mechanical geometry.

## Views and OpenUSD

Private outputs are retained under
`work/964-observed-boundaries-20261029/review-001/` and `view-001/`:

- `boundary-review.usdc` references the unchanged source USD and overlays exact
  source-edge endpoints. Only the three inspected regions are visible.
- `boundary-underbody.png` and `boundary-oblique.png` show original open edges
  in orange and selection cuts in blue. Line width is a display setting.
- `boundary-orbit.mp4` is a five-second, 120-frame, 24 fps H.264 inspection orbit
  at 1600 × 1000. The two stills and decoded frames 0, 30, 60 and 90 were inspected.
- Original face IDs, boundary endpoint IDs and classifications are retained in
  private arrays. No source triangles or coordinates are changed.

The media is rendered locally by VTK from the reopened USD. It is neither
native Omniverse RTX evidence nor a photograph of a manufactured part. The
original scan-derived pixels and geometry remain private. The overlay's reader
checked all 507,149 displayed faces and 6,957 edge occurrences against original
indices and coordinates; strict `usdchecker` passed.

## Verification and retained rejection

[inspect_boundaries.py](inspect_boundaries.py) constructs Int64 edge keys and
checks that both endpoint IDs can be recovered exactly. The first private
scratch calculation used Int32 multiplication, which overflowed. Its counts
were rejected and retained under `trial-001-int32-rejected/`; they are not used
in this result. A large-index regression control covers that error.

[verify_boundaries.py](verify_boundaries.py) does not import the author. It
recomputes edges using lexicographically sorted endpoint pairs and interleaved
face edges, then checks the saved boundary indices, origin classifications,
component partitions, sizes and overlaps. Its boundary-contour check uses an
explicit traversal; both programs use SciPy for face connected components.
This is independent representation and recomputation, not independent physical
identification. All 7,086,599 source edges and 6,957 region boundary occurrences
passed. A changed boundary-origin label was rejected even after its file hash
was updated; omitting a required region was also rejected.

Seven focused controls cover a square's original-versus-cut diagonal, large
Int32 source indices, non-manifold incidence, vertex-only contact, inconsistent
winding, a foreign edge and failure before output publication. The executed
[run](run.json), [verification](verification.json), [media](media.json),
[video probe](video-probe.json) and [visual review](media-review.json) retain
settings, counts, hashes and claim limits.

## Consequence and next input

Keep these original source patches as observations. Do not use the blue window
outlines as CAD perimeters, turn the orange gaps into automatic filled patches,
or treat one connected mesh as one vehicle part. Physical boundary extraction
still needs identified seams and coverage on the specimen; the tunnel also
needs its interior and installed controls. The existing
[interface survey](../../interface-measurement-plan.md) remains the acquisition
contract. No new torsion, strength, manufacturing or paid Omniverse run is
admitted by this audit.

## Reproduce

Use new private directories. `SCAN` points to the original OBJ, and `ARRAYS` to
the retained registered arrays. Processing uses the NumPy/SciPy environment;
visualization uses the native OpenUSD/PyVista environment, `usdchecker`, FFmpeg
and FFprobe.

```sh
SOURCE=twins/964-chassis/monocoque/observed-boundaries-20261029
ARRAYS=work/964-model-year-review-20261029/replay-001
REVIEW=work/964-boundary-new/review
VIEWS=work/964-boundary-new/views

work/check-venv/bin/python "$SOURCE/inspect_boundaries.py" --scan "$SCAN" \
  --vertices "$ARRAYS/verts_vehicle.npy" --faces "$ARRAYS/faces.npy" --output "$REVIEW"
work/check-venv/bin/python "$SOURCE/verify_boundaries.py" \
  --vertices "$ARRAYS/verts_vehicle.npy" --faces "$ARRAYS/faces.npy" --review "$REVIEW"
work/omniverse-venv/bin/python "$SOURCE/render_boundaries.py" --review "$REVIEW" \
  --source-stage work/964-cell-scan-coverage-20261029/review-002/observed-underbody.usdc \
  --vertices "$ARRAYS/verts_vehicle.npy" --faces "$ARRAYS/faces.npy" --output "$VIEWS"
work/check-venv/bin/python -m unittest discover -s tests -p test_964_observed_boundaries.py -v
```

The USD contains a relative reference to the retained private source stage.
Keep that dependency and verify its digest when moving the review; this is not
a self-contained product delivery bundle.
