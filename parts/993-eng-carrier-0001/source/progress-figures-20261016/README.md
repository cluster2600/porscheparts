# Work-in-progress images — 16 October 2026

Open `index.html` to browse the plates in this directory offline. The PNG
files remain available individually at full resolution.

The navigation also gives access to the mechanical maps already computed:
[rigid supports](mechanics.html), [compliant supports](mechanics-springs.html),
and to the [corrected surfaces of the right region](right-supports.html).
Each plate keeps its own receipt and its computation scope.

The [local plate of the left skin](chart002-local-20261016/README.md)
completes these five views. It keeps its own three real JSON files, its own
render script and its own receipt; it does not modify the historical evidence of the
five initial plates.

The [two plates of the seven native envelopes](sealed-envelopes-20261016/README.md)
add the build volumes in the real pose and the enlargements
of the small regions 003/009. Their own receipts keep the seven meshes,
the render sources and the scale-bar checks. The replay from
a separate copy reproduces the two PNGs byte for byte. These volumes precede the
support grids and layers, still being computed.

The [two plates of the computed support surfaces](calculated-surfaces-20261017/README.md)
show regions 003/009/010 in the kept pose, then their grids,
skins and teeth in detail. The three checkpoints are re-verified locally;
the check of the seven regions and of the layers is still in progress. A replay from
a separate copy and another current directory reproduces the two PNGs
byte for byte. The PDF, SVG, sources and receipts accompany these images.

The two new views use the adopted STL and the support triangles
of trial `real-support-source-008-015`. The dimensions, the mesh comparison
and layer 518 are identical copies of the figures computed earlier.
The [receipt](figures.json) keeps their digests and those of the inputs.

The part weighs 1.262212621 kg against a limit of 1.30 kg. The perforated support
trial shown is refused: 26 components, i.e. 35.66 mm² of surfaces,
lack the two required anchors. It represents the right region alone,
not an admitted complete preparation. The detail view projects the triangles
into their real plane; no additional surface fills the gaps.

Regeneration from the repository root, with the reproduced PySLM runtime:

```sh
work/part-workflow/runtimes/pyslm-coverage-reproduced-012/env/bin/python \
  scripts/render_carrier_progress.py \
  work/part-workflow/run-001 \
  work/carrier-process-20261016/real-support-source-008-015 \
  work/part-workflow/progress-images-new
```

The output directory must be new. The render refuses identity
divergences between STEP, mass, CAD/mesh audit and STL, as well as between the
anchoring graph and the triangles it colours. VisPy uses a depth
buffer for the 3D views; Matplotlib draws the detail in the real plane.

The five images were reviewed visually; the digests of the copies and
the targeted graph-colouring test pass. The intermediate framings
are kept in `work/part-workflow/progress-images-001` to `003` with
their reason for editorial refusal.

The [plate of the large zone 000](region000-material-20261017/README.md)
shows its 171,694 original triangles: 322 grids and 15 skins, with a connected
material graph. It keeps the refusal of the strict cutter and states the
triangulation correction in progress. The sources, arrays, group indices
and PNG/SVG/PDF exports are included; the render was run from a separate copy.

The [local plate of chart 152 of region 008](chart008-local-20261017/README.md)
shows two bands already contained in the source domain, with their dimensions
and the exact receipts kept. The contacts of the component remain not validated;
no regional or global admission is deduced from this image. The
[publication review](chart008-local-20261017/publication-validation.json)
links the exact copies to the inspection of the PNG and the PDF by root.

The [plate of encoded points already covered](encoded-point-coverage-20261017/README.md)
explains the complete diagnosis of skin 13 of zone 000: 703 events
checked over the 1,034 heights, with the rational cuts kept and
a non-zero witness from the same group for each encoded point. The data, the
evidence and the PNG/SVG/PDF exports are included. The other groups and the
exposure graphs remain to be checked with this new rule.
The [replay from a separate copy](encoded-point-coverage-20261017/replay-validation.json),
launched from `/tmp`, reproduces the three exports byte for byte.
The [following check of the 17,384 events](../process-point-encoding-20261017/README.md)
also completes the 1,034 heights with all the required witnesses; this
capsule keeps the helper, the tests and the complete evidence. The plate
remains tied to its historical diagnosis of skin 13 alone.

The [envelope plate of the current pose](machine-envelope-20261017/README.md)
projects the 587,404 real triangles in XY and XZ. It shows the 500 mm
plate, a nominal 650 mm chamber, the margins and the two height
conventions of the documented machines. The manufacturer sources are linked in
the directory. A [replay from the published copy](machine-envelope-20261017/publication-validation.json),
launched from `/tmp`, reproduces the PNG/SVG/PDF byte for byte.

The [plate of imposed shrinkage and unclamping](wholepart-release-20261017/README.md)
shows the four native double-precision fields on the whole part.
The uniform case passes the initial strain threshold of 10⁻⁷. Under the imposed
quadratic field and the provisional clamping, the maximum displacement after
release is 58.090 µm; the visual amplification of 500 is stated.
The 103,534 nodes and the four fields are kept in the local data.
The [replay by root from a separate copy](wholepart-release-20261017/publication-validation.json)
reproduces the three formats byte for byte. This mechanical sensitivity remains
distinct from the thermal computation of the printing process.
The [capsule of the complete native case](../design-20261016/wholepart-native64-20261017/README.md)
also supplies the compressed inputs, the four states and the restoration
and re-analysis commands, without a new solver run.

The [plate of the region 000 contacts](region000-contacts-20261017/README.md)
shows the first real cut of the 337 support groups, then a detail
at the same coordinates. It keeps all the contact intervals before
and after segment encoding. Three contacts that became points create no
additional anchor. The 129,023 certificates were re-verified separately
with exact fractions; the scope remains one layer and one region.
The [three formats replayed from the published copy](region000-contacts-20261017/publication-validation.json)
accompany the compact data and the standalone render script.

[Plate 20 of the four peaks at the integration points](peak-IP-location-20261017/README.md)
locates the real maxima of the two meshes and the two support conditions,
on the real undeformed EF7 mesh. The two mesh9 peaks are exactly
superimposed and remain visible through concentric symbols, without jitter.
The MPa values, the measured h and the distances to the nodes alone are kept;
no continuous stress map or mesh convergence is deduced.
The three exports of the real render were copied byte for byte. A
[real replay from a separate copy and the cwd `/`](peak-IP-location-root-publication-20261017.json)
reproduces PNG, SVG and PDF byte for byte; root inspected the PNG and the first
page of the PDF. The capsule's historical receipt remains kept at its date.


[Plate 21 of the local refinement](local-refinement-20261017/README.md) compares
the real EF7 mesh before/after, with all the edges of the measurement perimeter
in two fixed boxes and the targets verified at unrounded values.
The mesh is geometrically checked; stress convergence
remains to be studied. The mechanical results are documented separately.
The [three formats replayed byte for byte and root's PNG/PDF QA](local-refinement-root-publication-20261017.json)
are linked to the complete data, sources and receipts of the capsule.


[Plate 22 of the native R1 fillet](native-fillet-20261017/README.md) shows the shape actually built, before/after in a common CAD section. The R1 belongs to the 3D fillet of the candidate BREP; it is not a redrawn arc. The status remains CAD prototype, STEP exchange under check. The [three formats replayed from the final copy](native-fillet-root-publication-20261017.json) are identical byte for byte; this replay only draws the points already extracted. The parent CAD files, not included, remain linked by their digests.


[Figure 26 — original C1 and the preserved terminal taper](C1-terminal-taper-profile-20261017/README.md) compares complete actual native profiles on common oblique U/Z axes. Only the taper profile was newly extracted; figure 25 supplies the closed original profiles. The original-C1 ray is not transferred to the taper. Its saved Build result retains the original law refusal and remains unqualified. The [actual English draw and ROOT PNG review](C1-terminal-taper-profile-20261017/rendering/root-terminal-review-001.json) are closed; this picture does not grant meshing, protected-interface, FEA or global thickness qualification.


[Figure 27 — actual terminal-taper stress and displacement](C1-terminal-taper-fields-20261017/README.md) shows both closed new-mesh linear-static cases, every boundary triangle and all global stress/displacement maxima on common scales at true displacement ×1. Full field/deck results belong to the separately bound native delivery capsule. The original law refusal is preserved; these numerical results do not establish stress convergence, a strength allowable or physical qualification. ROOT inspected the actual PNG; the PDF has metadata checks only.


[Figure 28 — coarse and raw-refined terminal-taper fields](C1-terminal-taper-four-case-fields-20261017/README.md) compares four closed cases at true displacement ×1 with common axes/scales and every boundary triangle. Rigid global VM rises from 697.3 to 1,218.1 MPa and K1000 from 1,977.8 to 3,716.0 MPa, while displacement remains near 2.794 and 18.17 mm. Original volume, law and STEP refusals remain intact: no H2 qualification, stress convergence or strength admission follows. Full fields belong to the dependent numerical capsule.


[Figure 29 — complete seven-edge radius law](C1-seven-edge-radius-law-20261017/README.md) compares the rebuilt-stock Build refusal with the patched toolkit's closed exact law result. The scalar graph and seven physical intervals retain smoothstep on edge 431 and R1 on the other six; full native coefficients and Fraction proof are separate from sampled visuals. No stock post-Build curve is fabricated. Geometry status is the historical law-observation snapshot; this figure grants no geometry or mechanical qualification.


[Figure 30 — actual complete functional-law candidate](C1-functional-law-candidate-20261017/README.md) shows the retained 637,850-triangle STL and a conservative source-datum junction crop in the original coordinates. The separate native mass is 1.262364410 kg. Actual PNG and rasterised PDF page were reviewed; image and source markers are display evidence only, with no mechanical or manufacturing qualification. Original runtime refusals remain separate from the later accepted render.


[Figure 31 — current complete-law coarse stress and displacement](C1-functional-law-fields-20261018/README.md) compares the actual rigid and K1000 cases using common scales and true displacement x1. Global VM is 690.250571 / 1898.691353 MPa and all-node displacement is 2.794908 / 18.181958 mm. All global peak ties and independent energy checks remain linked. These are current 07b354 coarse results, with no stress-convergence claim. The actual PNG and rasterised PDF page were reviewed; external full-field dependencies are listed explicitly.

[Figure 32](first-window-stock-comparison-20261018/README.md) compares the actual previous 07b and stock-only STL surfaces with a common camera/scale and four matched first-window closeups. The main cut-profile inset is 1.5 → 2.8 mm, not wall thickness; the stock design also omits the old blend. Native masses are 1.262364410 / 1.267835378 kg, a 5.47 g increase under 1.30 kg. The actual PNG and rasterised PDF page were reviewed. The compact capsule preserves the render and source evidence; it transfers no old FEA or engineering qualification.


## Figure 33 — stock stress and displacement

[Figure 33](index.html#first-window-stock-fields) shows both actual rigid and K1000 fields for stock `42da92cc`, with common scales, true displacement ×1 and all global integration-point peaks. [PNG](first-window-stock-fields-20261018/carrier-first-window-stock-stress-displacement.png), [SVG](first-window-stock-fields-20261018/carrier-first-window-stock-stress-displacement.svg), [PDF](first-window-stock-fields-20261018/carrier-first-window-stock-stress-displacement.pdf), [evidence and scope](first-window-stock-fields-20261018/README.md), and [stored-byte inventory](first-window-stock-fields-20261018/archive.json). The initial-mesh maxima are 621.141462 MPa and 1633.128570 MPa; stress convergence and strength acceptance remain open. The later 1.274798 kg rib trial has local geometry checks only and does not inherit these fields.

## Related figure scripts (English note, 2026-11-05)

Two carrier figure scripts are not called by any Makefile target, because
both read private `work/` inputs that are not in the repository. Their bytes
are recorded by SHA-256 in the carrier process evidence, so they are
documented here rather than edited:

- `scripts/render_carrier_region.py <prepared-region-dir> <new-output-dir>`
  draws one hash-verified prepared region. Its frozen copy and command are in
  [regional-support-004](regional-support-004/README.md).
- `scripts/render_carrier_workshop_drawing.py <stl> <study.json> <output>
  (--sha256 <hex> | --identity-receipt <json>)` draws a binary STL against the
  end centres and four central bolt centres of an interface study (for example
  `../bionic-20261011/correction-20261013/interface-study.json`). It refuses an
  STL whose hash differs from `--sha256` or the receipt's
  `candidate_STL_sha256`. The drawn interface dimensions are the study's
  **assumed** values, not measured ones; the drawing proves no fit.
