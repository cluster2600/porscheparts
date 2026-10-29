# 964 model-year search: original scan and body-control plates

Status, 29 October 2026: **review executed; model year remains unidentified**.
The owner reports a Carrera 2. Neither a model year nor a gearbox designation
has been independently identified. No geometry or engineering release follows.

## What was executed

The original `964widebodyunderside2poin13.obj` was read locally without changes:
2,400,031 vertices and 4,684,929 triangles. Its SHA-256 is
`f397909141e5af2529db961641c7699d39d40c355e05245cfb1573a2974c8dc5`.
[run.py](run.py) reapplies the retained frame parameters using the arithmetic
of `source/align.py`. Both the float32 vertex array and int32 triangle array
reproduce the **exact historical bytes** recorded in
[the registration receipt](../derived/scan-recalage-20260925.json).
This checks data continuity, not scanner accuracy or physical registration.

The existing interface review was rerun: 18 identities, ten projected XY
hypothesis pairs and zero validated XYZ anchors. Its CSV remains byte-identical
to the published sheet. The [receipt](interface-review.json) binds the corrected
ledger and source files. The former pending rerun is now executed.

Four native VTK views inspect the underside, each inner rear side, and the upper
rear region. They retain complete original triangles only: no hole filling,
surface repair, fitted mount or interpolated crop edge. The
[run receipt](run.json) records input hashes, versions, search bounds, camera
positions, triangle counts and local image hashes. Bounds are search/display
choices, never measured mounting positions or clearance limits.

## The plates contain one useful rear-span distinction

The original workshop-manual PDF was retrieved from the owner's reference
[Volume V Body](http://p914-6info.net/964_Manuals/Vol%205%20-%20Body.pdf).
Its 260 pages and SHA-256
`0fcb2571d8c8d4227cbd1d88b394ec9127e962359b561629cfb769fb6ed4f00c`
are recorded in [manual-review.json](manual-review.json). PDF pages 8 and 9
(one-based) were rendered and visually inspected, including enlarged labels.
The document and page images remain private, outside Git.

| Body feature | Plate 50-05, early group | Plate 50-05a, explicitly from model year 1991 | Dating value |
|---|---:|---:|---|
| P14 rear spring-strut mount pair | 601.5 +/- 2 mm | 616.6 +/- 2 mm | Nominal spans differ by 15.1 mm |
| P13 outer rear cross-tube mount pair | 1200 +/- 1 mm | 1200 +/- 1 mm | Common; cannot distinguish these groups |

**Transcription correction:** `MNL-964BC-0048` previously carried `1201` with no
tolerance. Page 8 actually prints `1200 +/- 1`. That entry and the ledger note
are corrected; the early and late records remain separate. There is no
one-millimetre P13 model-year change in these two plates. The existing interface
contract already used 1200 +/- 1, so this correction changes no geometry or FEA.

## What the scan review can conclude

The views show an assembled underbody with suspension, driveline and body
surfaces overlapping in projection. In the inspected crops, the upper region
is incomplete and **a defensible pair of P14 body-mount centres was not
identified**. No span was measured. This is a limitation of this inspection,
not a proof that every representation of the scan lacks all useful features.

The 616.6 mm already present in `monocoque-interface.json` comes from plate
50-05a. It is not an observation of this donor. Selecting points nearest to
that nominal value would make the date inference circular. The crop bounds,
lowest visible surface, point-cloud gaps and symmetry residual are likewise
not substitutes for identified mounts and measurement uncertainty.

Accordingly, `model_year`, `model_year_group` and `p14_measured_span_mm` stay
`null`. The candidate geometry families remain **up to MY1990** and **from
MY1991**. For an original Carrera 2, the early candidate is MY1990: Porsche
lists the C2 from MY1990 on its
[German model page](https://www.porsche.com/germany/accessoriesandservice/classic/models/964/964/).
That conditional restriction does not authenticate this modified donor.

The [Porsche manufacturer certificate dated 10 April 2003](https://www.motor-talk.de/forum/aktion/Attachment.html?attachmentId=717926)
also distinguishes rear damper references through MY1990 and from MY1991 on
PDF page 3. A replaceable damper identifies its installation, not necessarily
the birth year of the body. PDF page 4 explains the model-year character at
position ten of the chassis number: L=1990, M=1991, N=1992, P=1993, R=1994.
No donor chassis number was obtained, stored or published in this review.

## Next engineering action

Continue the common documentary layout while keeping the two P14 families
explicit. Do not freeze a donor-specific P14 position from this search.
An independently identified original P14 pair with a justified span uncertainty
could distinguish the geometry families; it would not by itself establish an
exact model year or rule out repair/conversion. The model-year character from
the donor's physical identification is a separate route to the exact year.
There is no need to repeat all the existing body-control dimensions.

The tunnel interior, installed gearbox, functional axes and mounting faces
remain separate questions. This study neither changes the S6 stiffness results
nor adds composite strength, manufacturing, road or circuit qualification.

## Replay and retention

Run with NumPy, Matplotlib, PyVista and VTK; see exact versions in `run.json`:

```sh
python twins/964-chassis/model-year-review-20261029/run.py \
  --scan /private/path/964widebodyunderside2poin13.obj \
  --output /private/path/new-model-year-review
python -m unittest discover -s tests -p 'test_964_model_year_review.py'
python -m unittest discover -s tests -p 'test_964_monocoque_interface.py'
```

The output must be new. Unknown scan bytes or changed replay arrays are rejected.
The script always leaves identification unset; it does not automate a visual
recognition decision. A completed `run.json` is written only after all views,
the interface review and the final unchanged-input check succeed.

Scan arrays, six review images and manual page extracts are retained locally;
redistribution rights remain unconfirmed. Only source code, factual corrections,
aggregate findings and hash receipts are published. Numerical replay can be
checked byte for byte; image bytes can vary with the renderer and driver.
