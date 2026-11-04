# CarGeometry 964 preview extraction — 4 November 2026

The public preview contains substantial dimensional information, and **all of
its displayed images are already held privately**. Purchase is not required to
inspect them. This continuation records which content can be read and why the
additional height sheets have not supplied functional body coordinates.

## Coverage and retrieval

The [964 listing](https://cargeometry.org/porsche/105-porsche-911-carrera-964-1989-1994-body-dimensions.html)
contains 24 images: one vehicle photograph and **23 technical images**. Eight
technical thumbnails have explicit larger-image links. All 24 best linked
files were visually reviewed and matched, by SHA-256, to the earlier
[30 October retrieval](../body-reference-research-20261030/manifest.json).
These images are indexed in Git; the copyrighted raster files are not.

The [alternate public listing](https://cargeometry.com/body-dimensions/2293-kuzovnye-razmery-porsche-911-carrera-964-1989-1994-body-dimensions.html)
was also examined. Its seven selected additional dimensional sheets — filename
suffixes 11, 13, 15, 16, 19, 20 and 21 — are **byte-identical** to the .org files.
This route supplies no extra pixels. Full URLs, native dimensions, hashes,
private paths and individual visual assessments are in [inventory.json](inventory.json).

The best public files are between 353 and 473 pixels wide. Some images combine
two or four source pages. Display enlargement was used to inspect the original
pixels; no generative restoration, AI super-resolution or scaling of drawing
lines supplied a number. A small local OCR trial on three header crops did not
produce usable dimensional evidence and supplied no admitted value.

## Findings by filename suffix

Suffixes below identify image files, not source page numbers or Porsche point IDs.

| Images | Content | Treatment |
|---|---|---|
| 00 | Vehicle photograph | No dimensions |
| 01–03 | Porsche floor-control and early/MY91+ assembly plates | Existing manual material; no additional measurement or independent corroboration |
| 04–08 | Repair procedures for front, floor, sills, pillars and rear/side structure | Feature/construction references; no new nominal XYZ set |
| 09–10 | Carrera RS body-in-white conversion scope | Preserve RS context; not a height table |
| 11 | Coupe lower/upper plan and profile tables | Candidate source for nominal points; contact symbols, small digits and revision remain unresolved |
| 12 | Cabriolet plan/profile tables | Separate body-style variant |
| 13 | Carrera 2 coupe, parts on and parts removed | Keep assembly states distinct; small values and full contact definitions remain unresolved |
| 14 | Carrera 2 Cabrio, parts on and parts removed | Separate body-style variant |
| 15–16 | Lower-body plan/profile, heights, chains and point symbols | No complete value + unit + datum + physical contact admitted |
| 17 | Coupe upperbody/opening diagrams | Potential scalar opening constraints; not continuous surface geometry |
| 18 | Cabriolet opening diagrams | Separate body-style variant |
| 19 | 1989–94 lower-body diagrams and symbol table | Upper-right label reads `2271`, but its meaning/unit is not admitted; no scale correction |
| 20 | 1992 Carrera 2/4 and Turbo Coupe underbody | Readable `2272 mm` wheelbase repeats the current reference; full point-coordinate transcription remains unresolved |
| 21 | Matching coupe upperbody, pillars and openings | Endpoint-detail views exist; complete numeric/contact reading unresolved |
| 22–23 | Cabriolet underbody/upperbody | Separate body-style variant |

The [extraction register](extraction-register.csv) records eight selected regions:
one readable existing nominal, one numeric label with unresolved meaning, and
six unresolved dimensional regions. It is a bounded attempt, not a count of
every dimension in the images. Blank numeric fields mean unknown. The only
populated nominal field is the wheelbase: it adds no new interface constraint.

The comparison uses the existing 2272 mm reference in the
[twin record](../../../catalog/twins/twin-964-chassis-floor-0001.json).
No wheel-centre coordinate, axle location or chassis point is reconstructed from
this global length. A 1992 drawing heading does not identify the donor year.

## Correction to the earlier image identification

The 30 October report incorrectly described filename suffixes **03 and 09** as
additional height/point tables. Image 03 is the familiar MY91+ Porsche assembly
plate; image 09 describes RS body-in-white conversion details. The additional
lower-body dimensional leads are **11, 13, 15, 16, 19 and 20**. Images 12, 14
and 22 cover Cabriolet alternatives. The earlier recorded bytes remain intact;
this report supplies the correction.

## Engineering effect

The source register now marks the **public previews** as available. The complete
commercial archive remains unacquired; whether payment would provide extra
pages, higher resolution or usable rights is unknown. No purchase is justified
by an assumption that those improvements exist.

The [current interface contract](../interface-exploitation-20261030/contract.json)
is unchanged. No new XYZ, axes, mating faces or tolerance has been admitted.
Source point letters/numbers cannot be equated with Porsche P-identities without
matching physical features. Hole centres, bolt-head contacts and parts-on versus
bare-body measurements must not be combined into one coordinate set.

This increment improves M1 source coverage and reading traceability. It does
not complete the M2 physical torsion test or change structural, manufacturing,
road/track or Omniverse qualification. The preview does not supply the complete
inner tunnel surfaces, every attachment face/axis, laminate properties or mould
definition needed to finish those phases.

The next useful input is a legible original of a selected candidate sheet with
its full point legend and datum conventions. Its existing title, variant and
image suffix are now identified. Another copy of these same raster bytes will
not resolve the remaining digits. A reference scan can still supply surfaces
that repair-control diagrams do not describe.

No source images, raw meshes or proprietary manuals are committed. No external
message, purchase, paid compute rental or structural solve occurred in this
continuation. The local files cited by the inventory are a retrieval cache,
not a durable private evidence release.
