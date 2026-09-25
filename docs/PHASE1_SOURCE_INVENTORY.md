# Phase 1 — Source inventory

This document tracks Phase 1 progress. It hosts no protected content: it records
where a piece of information lives, how it was consulted, and what its legal
status permits.

## Batch 1 — Official catalogs, legally accessible manuals and measurements

Consulted on August 28, 2026. Every URL was opened before being entered; access
failures are kept on the same footing as successes.

### Official catalogs and documents

| Record | Content | Access | Reuse | Evidence |
|---|---|---|---|---|
| `SRC-PORSCHE-PET-993` | Porsche Classic Genuine Parts catalog | available | prohibited | A |
| `SRC-PORSCHE-NEWSROOM-993` | History dossier and model range | available | prohibited | A |
| `SRC-PORSCHE-NEWSROOM-993-30Y` | Press kit "30 years of the 993" | available | prohibited | A |
| `SRC-PORSCHE-SHOP-TECHLIT` | Official technical literature for purchase | available, empty catalog | prohibited | not rated |
| `SRC-PORSCHE-CLASSICSHOP-USA` | Former Classic shop (993 manuals) | out of service (DNS) | prohibited | not rated |

### Accessible manuals and technical data

| Record | Content | Access | Reuse | Evidence |
|---|---|---|---|---|
| `SRC-9XXTEILE-PET-DIAGRAMS` | Exploded views and part numbers | free | prohibited | C |
| `SRC-PCA-993-ALIGNMENT` | Factory suspension alignment settings | free | prohibited | C |
| `SRC-WIKIPEDIA-993` | Vehicle envelope and variants | free | attribution required | D |
| `SRC-STUTTCARS-993-PARTS` | Advertised PET diagrams | paid | unknown | not rated |
| `SRC-STUTTCARS-993-TORQUE` | Engine tightening torques | paid | unknown | not rated |
| `SRC-PORSCHEFANATICS-993-MANUAL-DATA` | Public index and data derived from the manual: 235 procedures, 195 torques and 111 technical values | available | reference only | C |

### Measurements and dimensional data

| Record | Content | Access | Reuse | Evidence |
|---|---|---|---|---|
| `SRC-CARGEOMETRY-993-BODY` | Body shell and underbody measuring points | purchase (20 USD) | prohibited | B |
| `SRC-WHEEL-SIZE-993` | Wheels, offsets, bolt pattern | free | unknown | C |
| `SRC-CARFOLIO-993` | Masses and dimensions by variant | free | prohibited | D |
| `SRC-ELFERCLASSIC-993-TECHNICAL-DATA` | German compilation: envelope of the 993 Carrera 2 ROW (4,245 × 1,735 × 1,300 mm), wheelbase, tracks, ground clearance and geometry references | access expired | not redistributable | C |
| `SRC-RENNLIST-993-FORUMS` | Community workshop measurements | blocked to bots | unknown | C |
| `SRC-PELICANPARTS-964-993-FORUM` | Community workshop measurements | blocked to bots | unknown | C |

## Rejected sources

Rejected without being entered in the registry. The reason is kept so they are
not re-examined.

| Source | Reason |
|---|---|
| Scribd, SlideShare, eManualOnline, eManuals, workshopcarmanuals | Redistribution of the Porsche workshop manual with no demonstrable right |
| GitHub mirror of the booklet `Technical Specifications 911 Carrera (993)` | The public copy makes the factory table "Dimensions for Floor System" (page 110) readable, but the hosting and reproduction rights are not established; no PDF is kept |
| Forum attachments containing dimensioned factory plates | Same protected document, republished by a third party |
| PDF aggregators with no identifiable publisher | Unverifiable provenance |

A rejected source can remain useful as a hint that a document exists. It never
becomes a catalog reference.

## Batch 1 findings

- No dimensioned factory drawing is legally and freely accessible. Exploded
  views document assembly and the bill of materials, not geometry.
- Usable dimensional data will come from direct measurement, supplemented by a
  purchased body shell reference (`SRC-CARGEOMETRY-993-BODY`).
- Part numbers are freely accessible, but redistributing them is not: they
  serve as working identifiers, not as published content.
- Two major forums refuse automated access; consulting them stays manual and
  every value taken from them must be re-measured.
- The community corpus frequently copies the same uncited origin; the rule
  "two copies do not make two confirmations" applies directly.
- The public mirror of the Porsche technical booklet `1st Edition, Status 8 1995`
  confirms that a floor pan check table exists: A/P21 440 ± 2 mm,
  B/P3 670 ± 0.5 mm, C/P5 770 ± 2 mm, D/P6 204 ± 2 mm, E/P18 1,330 ± 1 mm,
  F/P19 1,236 ± 1 mm, G/P12 278 ± 1 mm, H/P20 1,018 ± 1 mm, I/P13 935 ± 1.5 mm,
  K/P14 973 ± 1.5 mm and L/P22 640 ± 1 mm. The document states that dimensions
  are taken from the center of holes or screw points and that dimensions in
  parentheses are horizontal. These values are a lead for buying or consulting
  an authorized copy, not project measurements nor redistributable geometry.

## Batch 2 — 3D models and digital twins

Searched in English and German on August 28, 2026, across 3D marketplaces, scan
shops, digitization services and the technical press.

### The finding

**No freely reusable, verified digital twin of the 993 was found.** Commercial
body scans exist, but they are exterior-only, purchase-only, self-declared and
without a public metrology report. What exists falls into four categories:

| Category | Example | Level | What it is worth |
|---|---|---|---|
| Synthetic visual mesh | game models, 3D stock libraries, RWB Sketchfab | D | Silhouette, never an interface |
| Raw unscaled scan | `SRC-SKETCHFAB-993-GT2-RAW-SCAN` | E | Shape, not measurement |
| Commercial component scan | `SRC-BREMAR-3D-SCAN-STORE` | D | No 993 component |
| Commercial body scan | `SRC-WOLFE-993-TURBO-EXTERIOR-SCAN`, `SRC-SKETCHFAB-993-BARN-FIND-SCAN` | D | Exterior declared at 1.76–2 mm, with no verified dimensions and no redistribution license |

The only complete 993 body scan found with a declared open license remains the
raw GT2 scan, under CC BY 4.0. It was obtained by videogrammetry from 115 frames
taken from a YouTube video: no scale, no stated accuracy, and a rights chain
that is not watertight since it derives from images owned by a third party. By
contrast, the archive `SRC-RENN3DPARTS-993-OPEN-FILES` lists nine part files
under licenses declared per record (CC-BY, CC-BY-SA, CC-BY-NC, CC-BY-NC-SA or
public domain). These part meshes are neither a vehicle scan nor evidence of
interface accuracy; the primary license and the units must be confirmed before
redistribution. The
[supplementary German-language search](research/phase-1-recherche-allemande.md)
listed other community assets with declared licenses, to be confirmed on their
original publications. None of these assets is dimensionally qualified. The two
commercial body scans therefore remain leads for purchase and comparison, not
free substitutes.

### What exists, but out of reach

Porsche Classic already does exactly this work, in-house
(`SRC-PORSCHE-CLASSIC-3D-PRINTING`): SLM for steel, SLS for polymers, and "a 3D
scan of the component is enough as a basis to start production". Eight parts
produced, about twenty under study, checked by pressure testing, tomography and
fit checks on the vehicle.

It is both a validation of the approach and the bar to clear. The manufacturer
does not publish this data.

### The lead that would have scaled, and is closed

`SRC-CAR-CLOUDS-POINT-CLOUDS` sells laser point clouds of complete vehicles at
195 USD. A full-car scan would give the mounting environment of dozens of parts
at once, where a part measurement serves only one: it was the best answer to the
scale problem.

Catalog queried in full on August 28, 2026 — 906 products, five Porsches:

| Model | Price |
|---|---|
| Porsche 911 Cabriolet (996) 2001 | 195 USD |
| Porsche 911 2015 (991) | 195 USD |
| Porsche Cayenne 2019 and 2020 | 195 USD |
| Porsche Macan 2019 | 195 USD |

**No 993, and nothing air-cooled.** The closest is a 996: next generation,
entirely different body shell. It is not a substitute.

The deliverable is an E57 point cloud, interior included. The lead would only
reopen through a dedicated digitization order, at an entirely different price
level — or through another provider, yet to be identified.

## Batch 5 — German-language search, 993 measurements and scans

Consulted on August 29 and 30, 2026. The results are recorded in the source
registry; no forum image, protected attachment, raw digitization or third-party
CAD file is copied into the repository.

### Community measurements

| Record | Result | Level | Decision |
|---|---|---|---|
| `SRC-PFF-993-RS-LETTERING-MEASUREMENT` | Carrera RS script: 28.5 cm from each side, 6 cm from the lower edge, 33 cm long, 3 cm high | C | Lead to re-measure, no geometry published |
| `SRC-PFF-993-CABRIO-ROOF-BUSHING-MEASUREMENT` | Convertible top bushing: outer Ø 12 mm, inner Ø 10 mm, depth 9 mm, with flange | C | Lead to re-measure on a removed part; no interchangeability claim |
| `SRC-PFF-993-SPEAKER-DIAMETERS` | Speakers reported at 165 mm front and 130 mm rear on a 1997 Cabrio; depth unknown | C | Context for an audio bracket; also measure depth, opening and fasteners |
| `SRC-PFF-993-FRONT-SPEAKER-MEASUREMENT` | Another German thread reports 13 cm at the front without Sound-Paket, and a substantial modification to go to 16 cm | C | Contradicts the 165 mm reported on a Cabrio; separate audio variant, nominal diameter and opening by direct measurement |
| `SRC-PFF-993-SUNROOF-REVERSE-ENGINEERING` | Reconstruction of 993 sunroof parts in reinforced polymer | not rated | Interesting project to contact; no dimension or CAD published |
| `SRC-PFF-993-RS-SPRING-DATA` | RS spring wire diameters and rates reported by the forum | C | Documented, but excluded from manufacturing decisions: safety-critical suspension |
| `SRC-PFF-993-STABILIZER-BAR-DIAMETER` | Rear diameter declared at 18 mm on a 1995 C2 Tiptronic, within an 18–21 mm range | C | Direct measurement mandatory; safety-critical suspension, no manufacturing |
| `SRC-PFF-993-DISTRIBUTOR-BEARING-DIMENSIONS` | 964/993 distributor bearings declared at about Ø32 mm outer, Ø12.45 mm inner and 10 mm high | C | Community measurement with no instrument, repeats, variant or datum; identify and measure the removed part before any replacement |
| `SRC-PFF-993-BRAKE-LIGHT-SWITCH-TRAVEL` | Declared brake light switch travel: 6–16 mm, measured at the middle of the pedal rubber on a 993 Tiptronic | C | Safety adjustment with no instrument, repeats or year; check against workshop documentation and on the vehicle, no manufacturing or modification |
| `SRC-ELFERSZENE-993-VALVE-SPRING-INSTALLATION-LENGTH` | German procedure and declared installed lengths for 993 valve springs: intake 36.7 + 0.3 mm / exhaust 35.7 + 0.3 mm, or 37.2 + 0.3 mm / 35.8 + 0.3 mm for M64/20 RS | C | Page blocked, values taken from the index with no independent validation; highly loaded valvetrain, no reproduction or release without engineering review and fatigue validation |

These values are member claims, with no instrument, repeats, measurement datum
or independent validation. They serve to prepare a direct measurement, not to
mark a part "accurate", "fitted" or "tested".

### German providers and manufacturers

| Record | What is demonstrated | What is missing |
|---|---|---|
| `SRC-DENK3D-993-SWITCH-PANEL-REPAIR` | Printed PETG CF kit for broken tabs on 964/993 switch panels; references 96455207104 and 96455213501 | No scan, CAD, dimensions or license; the complete panel is not sold |
| `SRC-BESPOKE-ELEMENTAL-993-CARBON-SWITCH-PANELS` | Manufacturer showing 993/964 carbon Schalterblenden; a variant skinned over the original part and a molded autoclave variant | B claimed | No drawing, scan, dimension, tolerance or report; request a sample and distinguish the skinned version from the replacement part |
| `SRC-PARTWORKS-993-INTERIOR-REPRODUCTIONS` | 993 catalog: sun visor clips (18/25 mm), two Hella lamps (133 × 30 mm, 89 × 33 × 28 mm) and 964/993 odometer display (27 × 62 mm) | Declared product dimensions, with no measurement protocol or reusable file; check the variant and the interface on a sample |
| `SRC-FEBOE-964-993-ALTERNATOR-BELT-DIMENSIONS` | German FEBÖ listing: 964/993 belt, Porsche ref. 999 192 338 50, advertised as 10 × 775 mm, for alternator/fan | Product claim with no profile, tolerances, reference length, pulleys or independent measurement; maintenance data only, no reconstruction or release without verification |
| `SRC-TECHSCAN3D-GERMANY-LIDAR-CAD-SERVICE` | German provider advertising scans of classic vehicles, PTX/BTX/XYZ and E57 LiDAR clouds, CSV/DXF/XML measurements and STEP/IGES CAD | No 993 project, public file, uncertainty report or reuse license; request a contracted scan with datums, scale, raw data and explicit rights |
| `SRC-PARTWORKS-993-VALVE-STEM-SEAL-DIMENSIONS` | German partworks/Elring listing: 993 valve stem seal advertised at 10.4 mm high, Ø14.2 mm outer, Ø10.8 mm inner and 8 mm stem | Product dimensions with no profile, tolerances, material, evidence of OEM equivalence or independent measurement; engine sealing, no reproduction or release without characterization and validation |
| `SRC-FVD-993-LOWER-CONSOLE-COVER-DIMENSIONS` | German FVD listing: 993 lower console cover ref. 99363207110 advertised at 110 × 80 × 40 mm, 0.06 kg, without lamps and with two clips per cover | C | Contradiction between the title (Coupé without M425/M650) and the compatibility table; commercial envelope with no datums, cutouts, clips, tolerances, CAD or independent measurement |
| `SRC-CLASSICPARTS-993-AIR-FUNNEL-DIMENSIONS` | German Classic Parts listing: set of six intake funnels compatible with the 993 3.6–3.8, advertised at 40 × 34 mm and 0.9 kg, ref. AT83144 / PM-O180-3 | C | Commercial dimensions with no drawing, mounting dimensions, tolerances, protocol or clear distinction between single part and set; manufacturer listed as JP Group A/S, sample to be measured before any reproduction |
| `SRC-FVD-993-HOT-AIR-CONNECTING-PIECE-DIMENSIONS` | German FVD listing: 993 hot air connector ref. 99321134601, advertised at 0.18 kg for Cabrio, Coupé and Targa bodies | C | Commercial weight with no diameters, thicknesses, radii, tolerances or protocol; order a sample and cross-check with the Rennlist workshop lead |
| `SRC-FVD-993-BITURBO-REAR-SPOILER-DIMENSIONS` | German FVD listing: 993 Bi-Turbo GFK rear spoiler advertised at 145 × 63 × 27 cm and 6.7 kg | C | Aftermarket envelope with no holes, datums, tolerances or aerodynamic validation; benchmark only, no reproduction or modification without variant check and validation |
| `SRC-DESIGN911-993-INSTRUMENT-80MM` | Clock blanking plug listed for the 1994–1998 993, designed for an 80 mm diameter instrument | Nominal instrument diameter, not the OEM cutout or interface; drawing, tolerance and independent measurement absent |
| `SRC-PARTWORKS-993-ODOMETER-GEAR` | E15 gear advertised at Ø 6.90 mm and 15 teeth, with a 17-K mating gear variant and an EU/US distinction | Product data from a manufacturer, with no protocol, drawing or CAD; advertised as injection molded, not 3D printed |
| `SRC-WOLFCARHIFI-993-SCAN-CAD-ADAPTERS` | 993 products advertised as coming from scan/CAD/printing, 130, 4×6 and 165 mm adapters | Complete interfaces, files and test report not published |
| `SRC-WOLFCARHIFI-993-REAR-100MM-SCAN` | Rear adapter advertised for a 100 mm speaker, designed from 3D scans of the 993 rear shelf and printed in high-temperature plastic | File, drawing, coordinates and report not published; 100 mm refers to the speaker, not the Porsche interface |
| `SRC-KLASSIKERAUTORADIO-993-REAR-SPEAKER-DIMENSIONS` | German manufacturer: 993 replacement rear speaker advertised at 90 × 150 mm, 50 mm depth and Ø80 mm magnet | Dimensions of the replacement product, not the OEM opening or hole spacing; no CAD, tolerance or independent measurement; buy a sample |
| `SRC-SONORITY-993-M490-SPEAKER-DIMENSIONS` | German supplier: M490-compatible system with woofer 130/116.5/58.5 mm, midrange 90/73/37 mm and tweeter, 48 mm cutout/22 mm depth | Speaker dimensions, not Porsche brackets; no interface, independent measurement or tolerance; useful for framing an audio campaign |
| `SRC-AIRAX-993-WIND-DEFLECTOR-DIMENSIONS` | German AIRAX documentation: 964/993 wind deflector, envelope 33 × 33 × 97, mass 3.00 kg and materials of the frame, cover and mesh | Overall dimensions with no anchor points, tolerance, section or CAD; mounting and visibility to be checked on a cabriolet |
| `SRC-WS-AUTOTEILE-993-FRONT-PLATE-HOLDER-DIMENSIONS` | German listing for the 993 701 105 00 front plate holder: width 439 mm, height 80 mm, declared incompatible with the standard EU plate | No hole spacing, hole, thickness, radius, datum or independent check; buy a copy before any template |
| `SRC-FSH-993-INSTRUMENT-RINGS` | German manufacturer: set of five aluminum rings for 911/964/993 instruments, clip-on mounting and advertised mass of about 0.06 kg | No diameter, width, thickness, depth, tolerance or CAD; buy a sample before reconstruction |
| `SRC-TECHART-993-INSTRUMENT-RINGS-MANUAL` | German TECHART instructions for the 964/993 rings: reference 093.460.106.009, cleaning, 5–6 bonding points and adhesive tape of 3 mm maximum | Mounting instructions with no dimensions or CAD; useful for preparing removal and locating the contact zone, not for validating a reproduction |
| `SRC-CULTS-993-WHEEL-CENTER-CAP-CAD` | German commercial model offering four STEP/STL files for a center cap associated with reference 993 361 303 11 | Dimensions, measurement, scan and license not verified; wheel part subject to measurement and engineering review |
| `SRC-PARTWORKS-993-C4-CENTER-TUBE-MEASUREMENT` | German manufacturer: refurbishment of the 993 C4 central tube with straightness check, bearing positioning and inspection of functional surfaces | No numerical result, tolerance, report or CAD; highly loaded drivetrain component, contact lead only |
| `SRC-ELEVEN-993-DOOR-WINDOW-FRAME-MOUNTING-PLATE` | German seller: small window frame mounting plate advertised as a genuine Porsche part, diagram item 10, compatible with 993 Coupé 1995–1998 | No Porsche reference, dimension, thickness, hole, tolerance or independent measurement; buy and identify the part before any reconstruction |
| `SRC-TECHART-993-FENDER-AIR-DUCT-MANUAL` | German TECHART instructions: fender cutting template, Ø2.5 mm pilot holes, cutting, TIG welding and anti-corrosion treatment for a 993 air duct | Template, coordinates, radii, tolerances and CAD absent; aftermarket body modification, to be checked before any reproduction |
| `SRC-ELEVEN-ENGINEERING-OLDTIMER-RE` | Professional scan → parametric CAD reconstruction workflow; contractual rights spelled out | No public 993 case; declared ±0.1 mm tolerance, not audited here |
| `SRC-ZESAD-993-TURBO-SCAN-TO-CAD` | Scan and STL-to-STEP reconstruction service for a 993 Turbo application | No public file; flywheel = loaded part, out of catalog without engineering |
| `SRC-GOTECH-CLASSIC-PARTS-RE` | Weissach provider: laser scanning of parts and their mounting situation, 3D data preparation for manufacturing | No public 993 case, metrology report, tolerance or CAD license; to be approached for a small non-critical interior part |
| `SRC-OPTI3D-GERMANY-SCAN-CAD-RE` | German provider in Troisdorf: Zeiss/Artec/Scantech scanners, mobile scanning, point cloud to solid CAD model and reproduction of classic parts | No public 993 case, report, uncertainty or deliverable license; request a contracted campaign on a non-critical part |
| `SRC-FORMAG-GERMANY-MOBILE-LASER-SCAN` | German provider: mobile laser scanner, accuracy advertised down to 0.1 mm, meshing and scan-to-CAD, on-site service possible in Germany | No public 993 case; commercial performance to be confirmed by report, datums, hidden surfaces and rights; indicative rate 1,190 EUR excl. VAT for about 7 h |
| `SRC-Q-TECH-RODING-CT-SCAN-CAD` | German provider: ZEISS CT up to Ø275 × 360 mm or Ø615 × 870 mm, CT/scan to STEP conversion and extraction of interior/exterior regions | No public 993 case; parameters and accreditation declared by the provider, to be confirmed by report, datums, uncertainty and a rights contract |
| `SRC-MOUMAMOTION-GERMANY-3D-SCAN-CAD-SERVICE` | German provider in Offenbach: non-contact scanning advertised at 0.05 mm, CAD reconstruction with tolerances and FDM/SLA manufacturing of oldtimer parts; original part accepted by mail | No public 993 case, CT or LiDAR; declared accuracy with no report or repeats; request datums, hidden surfaces, editable format and rights |
| `SRC-PFF-993-CDR21-LOGO-MEASUREMENT` | Two members of a German forum measure the Porsche logo of a Becker CDR-21/2238 radio at 33 mm and 32.5 mm, with a photograph | C | Community measurement with no established instrument, logo variant, tolerance or 993 vehicle; reference for direct measurement of a removed radio, not a console interface |
| `SRC-PFF-993-CABRIO-LOCKING-MOTOR-MEASUREMENT-LEAD` | German diagram asking for the A/B dimensions of the convertible top locking motor of a 1996 993 Cabriolet | D | No numerical answer, tolerance or protocol; contact lead only, retention mechanism subject to mechanical validation |
| `SRC-MAKO-GERMANY-POINTCLOUD-NATIVE-CAD` | German provider in Straelen: conversion of point clouds or scans into native CAD, with build history and cloud/CAD check advertised | No 993 case, report or public file; sample behind a form, and 0.05 mm accuracy advertised for the equipment, not for a 993 part |
| `SRC-KLEINANZEIGEN-993-CABRIO-REAR-SPEAKER-MEASUREMENT` | German classified ad for a rear speaker kit for the 993 Cabriolet: 100 mm basket, installation depth about 46 mm and diagonal hole spacing about 115 mm | C | Approximate dimensions of a non-original replacement, with no datum, instrument, tolerance or OEM interface; compare on a sample before any adaptation |
| `SRC-PFF-993-HEADLAMP-REFLECTOR-RIVET-HOLES` | German thread: headlamp reflector holes reported at about 3 mm, with reassembly possible using 5 mm M3 screws | C | Community dimension with no drawing, instrument or tolerance; headlamp variant and optical alignment to be checked on a removed part |

### Body scans and manufacturer evidence

| Record | Access and scope | Level |
|---|---|---|
| `SRC-SHINING3D-993-SCAN-CASE` | German case study documenting the actual scan of a 1995 993 with 8.6 m of tracking and 206.7 m³ of measuring volume; no data delivered. The 0.02 mm is an advertised characteristic of the equipment, not the result of the 993 scan | B claimed |
| `SRC-WOLFE-993-TURBO-EXTERIOR-SCAN` | Commercial OBJ of a 993 Turbo exterior, advertised accuracy 1.76 mm; roofline reported as worse | D claimed |
| `SRC-SKETCHFAB-993-BARN-FIND-SCAN` | Commercial exterior Carrera scan advertised at 2 mm; purchase and license terms to be checked | D claimed |
| `SRC-PORSCHE-CT-WEISSACH` | Porsche documents its CT tomography capability, but publishes no 993 scan or usable dataset | A, no 993 data |

**Batch 5 conclusion:** no freely downloadable 993 CT, LiDAR or laser scan data
with verified rights and accuracy was found. The best next acquisition is a
direct measurement of a small non-critical part, with variant, instrument,
repeats, reference photos and documented reuse permission. Commercial body
scans can help with the silhouette or with preparing a measurement campaign,
but must not on their own supply manufacturing interfaces.

## Batch 6 — Second pass: forums, marketplaces and scan providers

Supplementary search on August 29 and 30, 2026, with German queries and hobbyist
threads devoted to designing, printing and fitting 993 parts. Rennlist pages
could not be re-read automatically; indexed results are kept as leads, not as
reusable files.

### Community CAD and fitting

| Record | Result | Level | Decision |
|---|---|---|---|
| `SRC-RENNLIST-993-REAR-SPEAKER-MOUNTS` | Fusion 360 bracket printed on a CR-10 for rear speakers; OEM grille kept; PLA fit reported as "quite good" on a Pioneer | C | Ask the author for the STL and the rights; check each speaker on a removed part |
| `SRC-RENNLIST-993-REAR-SPEAKER-FRAMES-STEP` | Fusion 360 STEP files passed between hobbyists, then frames refined by measurement and printing for Infiniti Kappa speakers with OEM grilles | C | File, protocol, audio variants and license not public; contact the author and re-measure the interface |
| `SRC-RENNLIST-993-HIFI-SPEAKER-ADAPTER-DIMENSIONS` | Door adapter plate dimensioned at about 18 × 9¼ inches, with hole positions and cutouts; 4 × 6 rear speaker fitted under the OEM grille | C | Dimensions of a personal installation, not of the OEM part; no instrument, CAD or license; re-measure per audio variant |
| `SRC-GRABCAD-964-993-TWEETER-GRILL-BRACKET` | CAD bracket for screwing back a 964/993 door tweeter grille, OEM reference 91155567300 mentioned; original tweeter clips excluded | D | GrabCAD page blocked; file, dimensions, editable format and license to be obtained from the author before any use |
| `SRC-THINGIVERSE-993-REAR-SPEAKER-SHIM` | STL indexed as a 993 rear speaker shim onto which the original grille clips | D | Primary source and license not verified; no dimension or independent measurement; obtain legally and compare on a part |
| `SRC-CULTS-964-993-CONSOLE-REPAIR-STL` | Two free STLs for 964/993 console repair, with published file bboxes and an identified author | D | License field empty; download and redistribution on hold, bboxes not equivalent to interface dimensions |
| `SRC-CULTS-993-DOOR-POCKET-REINFORCEMENT` | Reinforcement for the non-Hifi 993 door pocket: two STLs and bboxes advertised at 75.184 × 12.7 × 73.660 mm | D | Cults listing blocked to direct access; license, file and fit to be confirmed, bbox not equivalent to an OEM dimension |
| `SRC-RENNLIST-993-SEAT-RAIL-BUSHING-CAD` | Owners' thread reporting a replacement seat rail part and an archive `993 seat rail bushing v3.zip` | C | Download and license not verified; seat rail tied to occupant restraint and positioning, no release without engineering review |
| `SRC-RENNLIST-993-DOOR-POCKET-REINFORCEMENT` | Putty impression and several test prints for a door pocket reinforcement; fit deviations and warping documented | C | Very good method and test-fit lead, but no reusable dimension or CAD recovered |
| `SRC-RENNLIST-993-DOOR-POCKET-DIMENSION-LEAD` | Partial dimensions declared at about 50 mm (standard) and 35 mm (HiFi), with mention of a CAD drawing of the reinforcement | C | Uninstrumented discussion values; critical dimension of the standard model, file and rights to be obtained, then re-measure |
| `SRC-RENNLIST-993-SWITCH-REPAIR-CAD` | Attempted reconstruction of a plastic switch component; four pin dimensions proposed for SolidWorks modeling | C | The project appears abandoned; no final dimension or CAD accessible |
| `SRC-RENNLIST-993-HVAC-BUTTONS-CAD` | Replacement buttons for the climate control unit designed by a hobbyist for the 964, 993 compatibility claimed, printed via Shapeways | C | File, dimensions, 993 test and license not verified; contact the author before any reuse |
| `SRC-PFF-993-REAR-SPOILER-HOLE-SPACING` | Community measurement of about 79 mm on the hinge and 62 mm on the spoiler during a Turbo installation | C | Variant and reference marks not established; zone subject to aerodynamic loads, no manufacturing or drilling without verification and review |
| `SRC-SHAPEWAYS-993-SUN-VISOR-GOPRO-CLIP` | Shapeways article: 3D-printed right-hand 993 sun visor clip, integrated GoPro mount and direct fit claimed; deliberately tight fit | B claimed | File, dimensions, material, author and license not verified; track down the sample before any reuse |
| `SRC-RENNLIST-993-SPLIT-GRILL-CAD` | Paper templates, printed prototypes and measurement of the engine lid curvature; final model split at around 360 mm, 2.4 mm shell | C | Good development protocol, but file and rights absent; confirm the material and the fit |
| `SRC-RENNLIST-993-DOOR-SPEAKER-POD` | 993 Targa door pod with inner Ø 73–74 mm, Ø 80 mm insert circle and a large recess of about 6.5 inches | C | Values from a Focal K2 installation; re-measure per speaker and obtain the file |
| `SRC-RENNLIST-993-WINDSHIELD-TEMPLATES` | Three printable templates for glass installation depth; 3D files linked by the author, about 5 mm thick and minimum bed of 7 × 3 inches | C | Reconstruction from tracings, check claimed within 1 mm, but page, files and license not verified; RS glass difference to be confirmed |
| `SRC-RENNLIST-993-BUMPERETTE-DELETE-CAD` | Bumperette delete inserts modeled, tested, then offered via Shapeways in several materials | C | The file and its rights are not public; the marketplace link is incomplete |
| `SRC-THANGS-993-UPPER-CONSOLE-TABS` | Commercial STL advertised at 68 × 6 × 29 mm for the 964/993 upper console tabs | D | Purchase and license to be checked; the bbox and "perfect fit" are seller claims |
| `SRC-THANGS-993-LOWER-CONSOLE-TABS` | Commercial STL advertised at 87 × 12 × 31 mm for the 964/993 lower console tabs | D | Lead adjacent to the control panel, not evidence of the switch blank geometry |
| `SRC-CULTS-993-DOOR-SCAN` | Commercial STL of a G-body door with 993 handle adaptation and Targa frame, file dimensions advertised | D | Modified panel, not an OEM door; purchase, license and comparison with the original mandatory |
| `SRC-CGTRADER-993-DASHBOARD-SCALE-MODEL` | Dashboard model advertised in STL/OBJ/DXF/FBX/glTF, but explicitly drawn for a 1/8 scale model and imperfect | E | CAD false positive; millimeter units shown, but scale and accuracy incompatible with 993 manufacturing geometry |
| `SRC-RENN3DPARTS-993-OPEN-FILES` | Community archive of nine 993 records with STLs, photos, bboxes and per-record licenses: CC-BY, CC-BY-NC, CC-BY-SA, CC-BY-NC-SA or public domain depending on the author | D | The files remain meshes with no independent measurement; confirm the primary source, the units and the rights before redistribution; no file copied into the repository |
| `SRC-THINGIVERSE-993-POLLEN-TABS` | Primary Thingiverse model `thing:2152823` by LimeyBoy, with replacement and reinforcement variants of the pollen filter tabs | C | Modern page, files and license not machine-readable; secondary bbox of about 30.700 × 18 × 10.800 mm to be checked |
| `SRC-PELICAN-993-FAN-SHROUD-DELETE-CAD-LEAD` | Request from a Germany-based user for a CAD/STL file of a 964/993 fan shroud delete cover | C | No file, dimension or license on the page; follow up with the author and clarify the cooling role before use |
| `SRC-RENNLIST-993-ALTERNATOR-INSULATOR-PHOTOGRAMMETRY` | Hobbyist attempt: about 100 photos to reconstruct a broken 993 alternator insulator; model judged too irregular and incomplete | C | No file or dimension; the lesson favors direct measurement and CAD reconstruction, not uncontrolled photogrammetry |
| `SRC-PFF-993-CARRERA-4-LETTERING-POSITION` | German measurements of the position and width of the Carrera/Carrera 4 scripts on two 993 cars | C | Community measurement with no instrument or repeats; useful for visual restoration, not for manufacturing a part or generalizing to the 4S |
| `SRC-RENNLIST-993-DASHBOARD-LIGHTING-DIMENSIONS` | Dashboard opening estimated at about 19 × 31 mm, or switch housing face at about 17 × 28 mm | C | Owner-declared values; no instrument, datum or repeats; lead to re-measure for the console, with no evidence of fit |
| `SRC-PFF-993-INSTRUMENT-INNER-RING-LEAD` | German thread looking for dimensions or a source for the thin chrome inner rings of the 993 instruments | C | No dimension or CAD in the thread; obtain a removed ring and record its diameters, width, thickness and depth |
| `SRC-PFF-993-OPTION490-SPEAKER-MEASUREMENT-LEAD` | Recent German thread: request for M490 speaker dimensions; installation reports for Pioneer, Option AIR-130 and Ampire CP460 in the original locations | C | No dimension table, instrument, depth or repeats; contact the owners and measure per audio variant |
| `SRC-RENNLIST-993-RS-HOT-AIR-BYPASS-TUBE-CAD-LEAD` | Hobbyist thread: shortening an RS hot air duct by about 2 inches, reuse of an OEM sleeve and proposal for a CAD/printed reconstruction around ref. 99321134601 | C | Approximate value with no instrument or file; measure the ends, check flow/temperature and obtain the author's permission before any reuse |
| `SRC-CULTS-993-SEAT-HINGE-COVER-CAD` | Commercial STL of a front seat hinge cover plate advertised for 993/964/968/944/928/924, author FIBERcraftENGINEERING, design 2192556 | D | Detail page inaccessible; dimensions, fit, source file and redistribution license not verified; buy legally, measure on the exact seat and do not extrapolate to the seat mountings or seat safety |
| `SRC-HUMFWORKS-993-PARTS` | Manufacturer: late 993/964 phone clip, dashboard blanking plugs in three sizes and 964/993 wiper plug with mounting details | C | No drawing, scan, CAD, dimension, tolerance or independent check; buy a sample and ask for the rights before any measurement or reuse |
| `SRC-VAGBOARD-993-LOCK-COVER-FIT` | German-language forum: Porsche lock cover ref. 993 537 613 00 01C, light modification of the lugs and reported fit in VW locks | C | No drawing, scan, dimension, instrument, repeats or license; obtain a sample and check the geometry and interchangeability separately |
| `SRC-FVD-993-EXHAUST-TIPS-DIMENSIONS` | German manufacturer: oval stainless exhaust tips for the narrow-body 993 C2/C4/RS, envelope advertised at 120 × 85 mm | C | Commercial envelope with no interface dimensions, spacing, thickness, tolerance or independent measurement; hot, vibrating zone to be characterized on a sample |
| `SRC-ASTROLLCAGES-993-LASER-SCANNED-CAGE` | Manufacturer: 993 cage advertised as designed from a 3D laser scan, 40 mm E355 steel and designed to FIA Appendix J | D | No cloud, CAD, resolution, report or reuse right; safety structure not to be reproduced without dedicated engineering and validation |

These threads confirm real demand for small interior interfaces, but also show
that the workshop prototype is a separate step from the nominal geometry:
several versions were printed before an acceptable fit was reached. No
third-party file may enter the repository without an explicit license, an
identified author and a comparison with the original part.

### German measurement with an internal contradiction

`SRC-PFF-993-AC-BELT-DIMENSIONS` reports, within a single exchange, a 13 × 1085
A/C belt that does not fit, a 13 × 1100 that reportedly fits, and Porsche
reference 999 192 363 50 given as 12.5 × 1085 for the 993 versus 13 × 1085 for
the 964. A deflection of about 15 mm is also mentioned.

This source is useful for detecting a reference or variant mix-up, not for
publishing a dimension: the contradiction must be resolved by the part, the
variant and official documentation before any decision.

### Body shell dimensions and chassis measurement request

| Record | Result | Level | Decision |
|---|---|---|---|
| `SRC-RENNLIST-993-BODY-DIMENSIONS-PDF` | Several indexed attachments: "body dimensions small" (1.06 MB), "body measurement" (773.6 kB) and "temp body structure dimensions" (1.0 MB); diagrams and points in millimeters advertised | C | Files and provenance not verified, 403 access; obtain legally, then compare with official documentation or a direct measurement |
| `SRC-PFF-993-BODY-DIMENSIONS` | Exterior dimensions reported by variant: Carrera 1,735 mm wide, S/Turbo 1,795 mm, GT2 1,855 mm, lengths 4,245 mm | C | Envelope reference; the measuring points and the variants must be confirmed |
| `SRC-ASTRA-993-TYPE-APPROVAL-DIMENSIONS` | Official Swiss Typenschein in German for a 993 Carrera coupé: 4,245 mm long, 2,272 mm wheelbase, 1,735 mm wide and 1,300 mm high, 1,285 mm with sport chassis | A claimed | Type-approval reference for the vehicle envelope; redistribution rights to be confirmed, and no interface dimension or manufacturing tolerance |
| `SRC-PFF-993-REAR-SUBFRAME-MEASUREMENT-REQUEST` | Explicit list of distances to measure on the rear subframe, but no numerical answer on the page | D | Follow up with an owner who has the vehicle on a lift; do not treat the request as a drawing |
| `SRC-RENNLIST-993-RIDE-HEIGHT-MEASUREMENTS` | Underbody reference points and RoW Sport values of 144 +/- 10 mm front, 127 +/- 10 mm rear, with deviation limits | C | Community reference marks and values to be confirmed; useful for setting up a measurement campaign, not part geometry nor a releasable setting |

The Rennlist PDF is a potentially important lead for reference points, but its
rights status and technical origin are not established. The PFF dimensions are
useful for spotting a variant error, not for reconstructing a surface. The rear
subframe also belongs to a suspension-related zone: it stays outside the
manufacturing scope without engineering review.

### CT, laser and scan-to-CAD providers

| Record | Documented capability | Current limit |
|---|---|---|
| `SRC-FREEFORM-GMBH-CT-LASER-RE` | German provider: CT of objects up to 300 × 300 × 400 mm, NanoCT advertised at 1 µm or less, measurement reports, scan-to-CAD; line laser scanner on a CMM for parts up to 1.6 m | Declared commercial capabilities, no public 993 scan; the laser is not vehicle LiDAR |
| `SRC-A-CONCEPTS-SCAN-FEM-SERVICE` | Mobile scanning, CAD preparation and FEM; German reference mentioning a 993 Turbo engine in a 917 project | Confidential project, no 993 geometry published and no contractual delivery accuracy |
| `SRC-OTTO-MODELS-993-LASER-SCAN` | Account of a laser scan of a 993 Carrera to prepare an Otto scale model | No scale, point cloud, accuracy or reuse rights |
| `SRC-FABSPEED-993-LASER-SCAN-EXHAUST` | Manufacturer claiming to have laser-scanned the 993 OEM engine trays, mufflers and catalytic converters before the CAD design of an X-pipe | No point cloud, CAD, tolerance or test report published |
| `SRC-SCHIMMEL-993-SCAN-SERVICE` | Provider listing the Porsche 911 (993) among its laser scanning campaigns of vehicles, panels and interiors | No public 993 deliverable; instrument, accuracy and license to be defined by quote |
| `SRC-SCHONER-993-GT2-LIDAR` | Technical page now re-read directly: claim of a high-fidelity LiDAR scan and advertised access to blueprints/CAD of a 993 GT2 EVO II | Heavily modified electric project; no public file, scale, report or reuse right confirmed |
| `SRC-KUKUK-CLASSIC-CAR-3D-SCAN` | German office: point cloud, 3D model, dimensioning, mobile scanning and 3D-Röntgen advertised for bodies and spare parts | No public 993 dataset, report, CT/scan output or license; 0.01 mm accuracy advertised for the equipment, not for a 993 |
| `SRC-CMA-MOBILE-3D-VEHICLE-METROLOGY` | German mobile or lab metrology: point cloud, mesh and reverse engineering to STEP/IGES/CATIA/SOLIDWORKS/NX/Creo, with PDF report; ISO 17025 systems advertised | No public 993 dataset; 0.010–0.012 mm advertised for the equipment, to be confirmed by report and quote |
| `SRC-ASEC-AUTOMOTIVE-SCAN-RE` | German provider: mobile ATOS/TRITOP optical scanning, industrial CT for hidden geometry, measurements, reports and reverse engineering to STL/OBJ/PLY/CAD | No public 993 dataset; ask for the method, fixtures, uncertainties, error analysis, datums and reuse rights |
| `SRC-PCM-SCAN-TRACEABLE-METROLOGY` | German provider: AT960 laser tracker + AS1 scanner, GD&T inspection and reconstruction to E57/PLY/STL/OBJ/STEP/IGES; system uncertainty advertised at ±15 µm + 6 µm/m per ISO 10360-10 | No public 993 dataset; advertised system value, not a result on a 993; datums, repeats, hidden surfaces and license to be contracted |
| `SRC-3D-OLDTIMER-GERMANY-RE` | German manufacturer advertising scan-CAD-print, fit checks in the assembly and cycle testing; Porsche 924/911 example | No 993 case or public CAD; fuel line bracket example out of scope without review |
| `SRC-LMS-993-GT2-EVO-WHOLE-CAR-SCAN` | Video documenting the complete 3D scan of a modified 993 GT2 EVO to prepare a conversion | No cloud, mesh, CAD, scale, accuracy or reuse right; contact lead, not OEM geometry |
| `SRC-ED24-GERMANY-SCAN-RE` | German provider: part scanning, STL/OBJ, CAD/STEP reconstruction and advertised accuracy of 0.1 mm | Public example outside the 993; declared accuracy, no 993 report or deliverable license |
| `SRC-3DPADELT-GERMANY-CT-LASER-RE` | German provider: optical/laser scanning, photogrammetry, laser tracker and CT; E57/LAS/LAZ clouds, mesh and STEP/IGES/DXF CAD | No public 993 case; accuracy depends on the object, the volume and the method; no 993 deliverable or right verified |
| `SRC-3D-DRUCK-SERVICE-FRANKFURT-RE` | German provider: in-house scanning and reverse engineering, digital archiving, oldtimer reproduction, print volumes up to 800 × 800 × 1,000 mm; CT rate advertised from €99 | No public 993 case, CT/LiDAR not identified and performance declared without protocol; request a traceable quote and the deliverable rights |
| `SRC-PROLASERTEC-GERMANY-3D-SCAN-CAD` | German provider: fringe projection, point cloud, mesh and STL/STEP/DXF options; parts up to 300 × 300 × 300 mm, rate advertised from €69 | No public 993 case or report; 0.04 mm advertised for the equipment, to be confirmed by quote, report and CAD rights |
| `SRC-JOCHAM-OLDTIMER-SCAN-RE` | German provider: oldtimer scanning, STEP/IGES CAD and reconstruction for molding; accuracy advertised at 0.2 mm on freeform surfaces and 0.05 mm on ruled surfaces | No public 993 case; declared commercial values, to be confirmed by report and contract |
| `SRC-PROSCAN3D-GERMANY-SCAN-RE` | German service: raw STL ±0.10 mm, processed STL ±0.05 mm and STEP CAD ±0.05 mm advertised; exclusive rights option | No public 993 case; accuracy depends on the part and the process, deliverable and rights to be contracted |
| `SRC-SCANIT3D-GERMANY-SCAN-METROLOGY` | German provider: scanning from 3 to 30,000 mm, Creaform scanners, CAD reverse engineering and inspection reports | No public 993 case; performance advertised per system, not a result on a 993 part |
| `SRC-LASER3DSCAN-GERMANY-RE` | German provider: laser scanning 5 mm–4 m, STL/OBJ/PLY mesh, parametric STEP/IGES CAD and client archiving; indicative prices from €70 excl. VAT / €350 excl. VAT | No public 993 case; 0.02 mm is a declared best case, the page states a practical tolerance of about ±0.03 to ±0.1 mm and excludes hidden internal geometry |
| `SRC-RICHTSATZ-MIETEN-993-CELETTE` | German rental company listing the Celette set `564.330`, "911 Carrera Typ 964 / Zusatz 993" | No published pin plan, coordinate or certificate; mounting and direct measurement lead to be contracted |
| `SRC-KFZ-GUTACHTER-BERLIN-993-3D-BODY-MEASUREMENT` | German office showing a 993 Targa reference and advertising 3D body measurement | No public cloud, report, manufacturer reference mark, uncertainty or 993 value; accident appraisal to be distinguished from nominal CAD |
| `SRC-TZR-PAUTER-993-CONNECTING-ROD-DIMENSIONS` | German manufacturer listing: 993/993 Turbo connecting rod with advertised dimensions, tolerances, mass, material and inspections | Product data with no CAD drawing or independent measurement; highly loaded part, reproduction prohibited without engineering review and fatigue validation |
| `SRC-PARTWORKS-993-BRAKE-DISC-DIMENSIONS` | German catalog: 993 Turbo front disc advertised at 322 × 32 × 72 mm, and RS/WTL/Turbo and Carrera rear discs advertised at 322 × 28 × 68 mm and 299 × 24 × 65 mm respectively; 103 mm centering and 130 mm bolt circle | C | Commercial dimensions with no drawing or independent measurement; safety-critical brakes, no manufacturing or release without engineering review and approved validation |

### New German and community leads

| Record | Result | Level | Decision |
|---|---|---|---|
| `SRC-ROADSTER-FASHION-993-HEADLAMP-HOOK` | Repair hook printed in aluminum or stainless steel for the 993 headlamp retaining spring | B claimed | No dimension, CAD, tolerance or bonding qualification; request a sample and check the headlamp aim |
| `SRC-LT3D-993-HEATER-KNOB` | 3D-printed 993/964/944/968 heater knob, reference 94465320500 | B claimed | Compatibility, exact material and tolerance not published; lead for a direct measurement of an interior part |
| `SRC-DTW-993-SMARTPHONE-HOLDER` | Smartphone holder replacing the ashtray, in carbon-reinforced plastic, for the 993 | B claimed | Commercial product with no file or dimensioned interface; benchmark and contact only |
| `SRC-FVD-993-SMARTPHONE-HOLDER-DIMENSIONS` | German listing of the DTW holder: declared envelope 160 × 100 × 70 mm and mass 0.32 kg | C | Product envelope, not interface dimensions nor independent measurement; no CAD or tolerance published |
| `SRC-FVD-993-DOOR-HANDLE-DIMENSIONS` | German listing of a set of aluminum handles for the 993: declared envelope 108 × 45 × 27 mm and mass 0.18 kg | C | Seller's product dimensions, with no datums, tolerance, CAD or independent measurement; obtain a sample before comparing with the OEM part |
| `SRC-FVD-993-RADIO-DASHBOARD-COVER-DIMENSIONS` | Aftermarket radio cover with no switch opening for the 964/993: declared envelope 187 × 58 × 28 mm, mass 0.13 kg | C | Dimensions probably of the product envelope, not the interface; buy a sample and measure before comparing with the switch blank |
| `SRC-PORSCHE-CLASSIC-PCCM-993-DIMENSIONS` | Official Porsche page: 993-compatible 1-DIN PCCM unit, envelope dimensions 187.5 × 58 × 170 mm, reference 91164559000 | A | Dimension of a device housing, not the console cavity or mounting; no interface drawing or CAD; check reference only |
| `SRC-FVD-993-HOOD-EMBLEM-DIMENSIONS` | 993-compatible hood emblem/bracket set: declared size 67 × 51 mm and a warning about the bracket fit | C | Commercial claim with no drawing or tolerance; useful for visual finish only, to be checked on a sample |
| `SRC-FVD-993-ENGINE-INSULATION-COVER-DIMENSIONS` | Aftermarket GFK cover for the edge of the 993 engine sound insulation mat: declared envelope 840 × 100 × 50 mm, mass 0.24 kg, five press studs | C | Product envelope with no clips, holes, radii, tolerance or thermal characterization; obtain a sample before any reconstruction |
| `SRC-FVD-993-INLET-VALVE-DIMENSIONS` | German FVD listing: 993 C2/C4 and Turbo intake valve advertised with an 8 mm stem, 49 mm head and 120 g mass; envelope 50 × 110 × 50 mm | C | Commercial claim with no functional length, material, treatment, tolerances, drawing or independent measurement; highly loaded valvetrain, no reproduction or release without engineering review and fatigue validation |
| `SRC-PARTWORKS-993-EXHAUST-VALVE-DIMENSIONS` | German partworks catalog: Carrera exhaust valve advertised at 109 × 42.5 × 8 mm and Turbo valve at 108.9 × 43.5 × 8 mm | C | Commercial claim with no tolerances, material, treatment, groove, inspection, drawing or independent measurement; highly loaded valvetrain, no reproduction or release without engineering review and fatigue validation |
| `SRC-PFF-993-WHEEL-EMBLEM-DIMENSIONS` | German thread: wheel cap emblem associated with a 993 reported at 35 × 46 mm | C | Community claim with no instrument, orientation, repeats or cap fit; decorative template to be checked on a sample, with no wheel or fastening geometry inferred |
| `SRC-PFF-993-FRONT-BRAKE-CALIPER-PISTON-DIAMETERS` | German thread: front caliper pistons of the standard 993 and BiTurbo reported at 44 and 36 mm | C | Uninstrumented answer, with no position distinction or tolerance; safety-critical brakes, documentary lead only and no manufacturing or release without review and approved validation |
| `SRC-PORSCHE-993-DME-REFERENCE-SENSOR-GAP` | Porsche technical document in German: speed/reference sensor–flywheel ring gear gap set to 1.0 ± 0.2 mm | A | Service adjustment dimension, with no part drawing or complete datums; copyrighted document, to be used for checking and not for reconstructing an interface without verification |
| `SRC-FVD-993-DOOR-TRIM-PANEL-DIMENSIONS` | 993 left door panel: declared product dimensions 105 × 44 × 2 cm and mass 1.6 kg, with many variants listed | C | Commercial envelope with no cutouts, datums, tolerances or CAD; order a sample and record the OEM interface before reconstruction |
| `SRC-CURBS-993-DOOR-PANEL-SPEAKER-CUTOUT-DIMENSIONS` | German manufacturer: declared cutouts of 154 mm for the main speaker and 68 mm for the tweeter on RS panels compatible with 993/993 Turbo/GT | C | Aftermarket/RS configuration dimensions, not the OEM opening; buy and measure a panel before use |
| `SRC-TUERPAPPEN-993-DOOR-PANEL-3MM` | German manufacturer: 993 panel bases advertised in 3 mm board, configurable cutouts and preparation for 16 cm speakers | C | Thickness and configuration of an aftermarket panel, with no interface dimensions or CAD; order a sample and record the holes before reconstruction |
| `SRC-JEHNERT-993-DOORBOARD-TECHNICAL-DATA` | German Jehnert brochure for 993 doorboards: 200 mm nominal speaker, 26 mm tweeter and slight enlargement of the inner sheet metal | B claimed | Aftermarket component dimensions, not OEM openings or hole spacing; copyrighted brochure and no redistributable CAD |
| `SRC-CARPASSION-993-DOOR-SPEAKER-ADAPTATION` | 964/993 forum report: going from a 13 cm to a 16 cm speaker and four 2.5 mm adapter holes | C | Adaptation described on a 964, transfer to the 993 to be confirmed; no datum, depth, repeats or CAD file |
| `SRC-CK-CABRIO-993-STYLE-CONVERTIBLE-MEASUREMENTS` | German manufacturer: radius difference of 34 mm advertised between 964/G-model and 993 architectures, with details of the overhang and the top seal | B claimed | Measurements of an aftermarket adaptation, not of an OEM top; useful for separating variants, to be checked on the vehicle and the pattern |
| `SRC-PARTWORKS-993-SWITCH-BLANK-OEM` | German listing of an OEM Porsche Schalterblende, refs 9936135230001C / 993.613.523.00, fitment 993 1994–1998, several variants | B | Page with no dimension, scan, CAD or tolerance, currently unavailable; obtain a copy before measuring |
| `SRC-PFF-993-TURBO-SEAT-CLIP-MEASUREMENT` | German thread: 1.5 mm steel wire and S-clip of about 10 mm for the 993 Turbo seatback cushion | C | Approximate values, with no instrument or drawing; seat part to be checked before any reproduction |
| `SRC-993C2-993-SEAT-MOUNTING-DIMENSIONS` | German blog post: seat track 408 mm, St37 plates of 5 × 30 mm, M8 × 20 and a 12 mm hole 40 mm from the end | C | 996-on-993 C2 adaptation, not an OEM drawing; seat mounting zone subject to specific review and validation |
| `SRC-PFF-993-CR21-RADIO-COVER-LEAD` | German thread about a missing cover for a CR-21 radio; members suggest a plastic cutout or a 3D print | C | No dimension, reference, CAD or file; contact lead only |
| `SRC-PFF-993-PORSCHE-WHEEL-CERTIFICATE` | German Porsche PDF relayed by PFF: wheel and ET offset combinations from 16 to 18 inches, by variant | B claimed | Copyrighted safety reference; no wheel manufacturing or release without dedicated verification |
| `SRC-PFF-993-FRONT-LID-SHEET-THICKNESS` | German thread: front lid sheet thickness estimated at about 0.6 mm and factory paint mentioned at 100–120 µm | C | No instrument or protocol; comparison lead on a sample, not a material or composite panel specification |
| `SRC-SPORTWAGENDOKTOR-993-CLIMATE-FAN-MOUNT` | Repair case of a 993 climate system where the fan bracket of a Porsche unit is reported as 3D printed | B claimed | No file, dimension, material or right; manufacturing precedent, not reusable geometry |
| `SRC-3DGO-993-964-CUP-HOLDER` | Indexed 993/964 community model with a declared Public Domain license; a secondary archive also gives a fitting photo and a bbox | D | Primary Printables license and units not verified; do not redistribute before confirmation |
| `SRC-ARMYTRIX-993-UNDERBODY-SCAN` | Manufacturer advertising a 3D scan of the 993 underbody for exhaust prototyping | C claimed | No scan, CAD, resolution, alloy or report; contact lead, exhaust subject to high thermal and vibration loads |
| `SRC-NIEDERHOF-993-POLYCARBONATE-MEASUREMENT` | 993/GT2 glazing made to original, template or CAD; advertised process: measurement, two-axis bending, annealing at 175 °C and surface treatment | B claimed | No geometry or tolerance published; useful for requesting a template or a measurement campaign, with separate regulatory validation |
| `SRC-RENNLIST-993-JACKING-POINT-MEASUREMENT` | A community record reports about 235–240 mm and 275 ± 5 mm between jacking marks on a C2 | C | Single record with ambiguous reference marks; confirm C2/C4 with datums, repeats and photos, with no use for a suspension part |
| `SRC-RENNLIST-993-JACKING-POINT-DISCREPANCY` | Carrera 4 thread: diagram reported at 1,245 mm, alternative calculation at 1,195 mm and a reply of 52 inches between front/rear points | C | Contradictory values and undefined reference marks; check on the vehicle with a datum and repeats, with no use for a structural part |
| `SRC-THINGIVERSE-993-PHONE-MOUNT` | 993/964 phone mount; a secondary archive confirms an STL declared CC-BY, 82 mm gauge ring and bbox 136.013 × 91.999 × 35.520 mm | D | Primary source, license and units to be confirmed; no claim of fit or accuracy |
| `SRC-CELERITECH-KALMAR-993-PHOTOGRAMMETRY` | Exhaust of a 993-based car captured by photogrammetry/3D scan, reconstructed in CAD and laser-checked | B claimed | Modified vehicle, proprietary data and no accuracy published; method reference, not OEM geometry |
| `SRC-PFF-993-TARGA-ANTENNA-HOLE-MEASUREMENT` | Antenna base hole reported at almost 19 mm on a car that was probably already modified; original estimated at 16 mm, with an anti-rotation tab | C | Separate the modification from the OEM dimension; re-measure on an unmodified body shell before any CAD |
| `SRC-PFF-993-PASSENGER-FOOTWELL-COVER-DIMENSIONS` | Phone bracket cover identified by reference 964 552 133 00; plastic part estimated at about 100 × 80 mm | C | Approximation with no thickness or clips; obtain a copy and measure before any reconstruction |
| `SRC-FSH-993-DASHBOARD-TRIM-DIMENSIONS` | 964/993 aftermarket trim: radio hole spacing advertised at 130 mm, cutout about 95 × 42 mm and optional Ø55 mm ring | C | Dimensions of the Singer Style product, not the OEM; airbag adaptation and interfaces to be checked on a sample |
| `SRC-TECHART-993-REAR-SPOILER-MOUNTING-MANUAL` | German TECHART instructions: Carrera/Turbo distinction, mounting kit 093.100.850.009 for the Carrera, fastening points and brake light wiring | A | Manufacturer instructions with no dimensioned coordinates; spoiler subject to aerodynamic loads, no manufacturing geometry or modification without validation |
| `SRC-TECHART-993-REAR-SPOILER-I-DRILLING-MANUAL` | German TECHART instructions: drilling template for the 993 spoiler I, 10 mm hole and 1.3 Nm torque for the brake light fastening | A | Accessory instructions, with no OEM hole spacing or coordinates; aerodynamic zone and moving lid, no modification without validation |
| `SRC-PORSCHE-993-SPOILER-TEILEGUTACHTEN` | German Porsche/TÜV dossier: approved 993 Aerokit combinations, references and mounting requirements for Carrera/RS | A | Official document with no CAD coordinates; restricted reproduction rights and no spoiler modification without variant check and validation |
| `SRC-PORSCHE-993-AIR-FILTER-TEILEGUTACHTEN` | German Porsche/TÜV dossier: perforated 993 air filter housing, ref. 993.110.030.06 and type/model variants | A | Configuration reference with no dimensions or geometry; copyrighted document, no reconstruction from the text alone |
| `SRC-PFF-993-OVERALL-WIDTH-MIRRORS` | German community measurement: overall width of a 993 with mirrors reported at about 183.2 cm | C | Reference marks, mirror state, instrument and repeats not established; check on the vehicle, without confusing it with the type-approved body width |
| `SRC-OLDTIMER-ERSATZTEILE24-993-SWITCH-RING-DIMENSIONS` | German listing: 911/964/993 switch ring advertised at Ø30.5 mm outer, 10.5 mm depth, Ø23 mm front and Ø28 mm rear | C | Declared dimensions of a commercial reproduction, with no drawing or independent measurement of the OEM opening; acquire a sample before comparison |
| `SRC-FVD-993-CARBON-SWITCH-PANEL-DIMENSIONS` | German listing: 964/993 carbon Schalterblende advertised at 124 × 75 × 47 mm, 0.02 kg | C | Envelope of a carbon-skinned commercial product, with no interface dimensions or OEM drawing; measure a sample before reconstruction |
| `SRC-FVD-993-FRONT-IMPACT-TUBE-DIMENSIONS` | German FVD listing: 993 aluminum front impact tube advertised at 139 × 100 × 53 mm and about 0.14 kg | C | Commercial dimensions with no drawing or independent measurement; crash protection element, no substitution without engineering review and dedicated validation |
| `SRC-KFZ-KAUERT-993-REAR-CONTROL-ARM-DIMENSIONS` | German listing: reconditioned 993 rear control arm advertised at 380 mm long and 340 mm between centers | C | Commercial dimensions with no datums, tolerances or method; suspension, no substitution without engineering review and dedicated validation |
| `SRC-FVD-993-LIGHT-SWITCH-SYMBOL-CAP-DIMENSIONS` | German listing: 964/993 switch symbol cap advertised at 25 × 25 × 5 mm, 0.02 kg, clipped onto the knob | C | Commercial envelope with no datum, tolerance, drawing or independent measurement; obtain a sample before comparing with the OEM part |
| `SRC-RENNLIST-993-CONSOLE-SWITCH-HOLE-DIMENSIONS` | Community record: console opening of a 1997 993 approx. 17.0 × 27.9 mm and cover approx. 16.2 × 27.4 mm | C | Single measurement with no instrument, tolerance or repeats; page blocked, re-measure on the exact variant before CAD |
| `SRC-TECHART-993-BKS-CUTTING-TEMPLATE` | German TECHART template for 993 BKS: cutting outline, front edge reference mark and printed 100 mm scale | A | The target product, datums, coordinates and tolerances are not stated; printing at full size mandatory, copyrighted document and no redistributable geometry |
| `SRC-RENNLIST-993-3D-PRINTED-DIY-BITS` | Hobbyist thread on printed 993 parts: speaker frames, windshield templates, seat bushings and cup holder | D | Page blocked, files and licenses not verified; links to Thingiverse/Printables to be checked individually, no mesh replaces an OEM measurement |
| `SRC-FVD-993-A-PILLAR-FAIRING-DIMENSIONS` | German FVD listing: 993 rain gutter deflectors advertised at 550 × 80 × 50 mm and 0.29 kg | C | Envelope of an aftermarket GFK product, with no drawing, datums or tolerances; aerodynamic modification to be treated as a benchmark, not as OEM geometry |
| `SRC-CLASSICPARTS-993-WINDOW-SWITCH-DIMENSIONS` | German listing: 964/993 window switch advertised at 35 × 35 × 60 mm and 0.02 kg | C | Detail page expired at access time; check whether the dimensions refer to the part or the packaging, with no drawing, tolerance or independent measurement |
| `SRC-PARTWORKS-993-THROTTLE-LINKAGE-BUSHING-DIMENSIONS` | German catalog: 911/964/993 throttle linkage bushing advertised at ID 8.15 mm, OD 12.15 mm and 8 mm high | C | Declared commercial dimensions, with no datums, tolerances, material, CAD or independent measurement; acquire a sample and check the linkage before any reconstruction |
| `SRC-PFF-993-ALARM-MODULE-MEASUREMENTS-TOOL` | German owner: Excel table of values measured on the 993 alarm/central locking (ZV) unit and a printed opening tool, STL offered privately | C | Attachment, protocol, dimensions and rights not verified; contact the author before any acquisition, without turning the electrical measurement into geometry |
| `SRC-PFF-993-INSTRUMENT-GLASS-THICKNESS` | German thread: 993 instrument glass thickness reported at about 3.8 mm | C | Single measurement with no instrument, zone, tolerance or repeats; obtain a removed glass and re-measure before any reproduction |
| `SRC-PFF-993-CASSETTE-CONSOLE-3D-PRINT` | German owner reporting a printed storage console after removing the Fischer C-Box from a 993 Cabriolet | C | No file, dimension or test published; contact the author and re-measure the console interfaces before any CAD |
| `SRC-PORSCHE-ORIGINALE-993-PRODUCT-DIMENSIONS` | German Porsche Classic catalog: insulation mat 1,000 × 500 × 2.3 mm and bushing 12 × 14 × 15 mm for 993 references | A claimed | Manufacturer listing dimensions, not an interface drawing nor an independent measurement; copyrighted PDF, keep the reference and URL only |
| `SRC-ELFERLISTE-993-STEERING-WHEEL-DIAMETERS` | German thread: standard steering wheel reported at 380 mm, Momo D36 measured at 360 mm and Prototipo at 350 mm | C | Community measurements with no instrument, exact reference, tolerance or repeats; steering/airbag, no manufacturing without engineering review |
| `SRC-THINGIVERSE-993-RS-MOMO-HORN-RING` | Indexed Thingiverse file for a 993 RS Momo wheel: 52 mm hole, Ø 59 mm outer and 3 mm protrusion advertised | D | License and independent measurement not verified; steering-related element, no release without engineering review |
| `SRC-PARTWORKS-993-WHEEL-CENTER-CAP-DIMENSIONS` | German partworks listing: Porsche 993 center cap ref. 9933613030761M advertised in plastic, Ø 76 mm outer, Ø 60 mm inner and 46 mm high | C | Commercial dimensions with no drawing, datums, tolerances, method or independent measurement; acquire and measure a sample before any reconstruction, with no conclusion about the wheel or its fastening |
| `SRC-FVD-993-GT2-STEERING-WHEEL-DIMENSIONS` | German FVD listing: GT2 steering wheel for the 993 advertised at Ø350 mm, Ø30 mm grip, 70 mm dish and 1.157 kg mass | C | Commercial claim with no drawing, hole spacing, tolerance or test; steering/airbag part advertised without TÜV, no reproduction or release without engineering review and regulatory validation |
| `SRC-NETZWERK-9ELF-964-993-BUMPER-BRACKET-DIMENSIONS` | German manufacturer: 964/993 bumper brackets advertised with a 10 mm base plate, 5 mm tube wall and 35 mm tube diameter | C | Commercial dimensions with no drawing, datums, tolerances or calculation; crash-related part, no reproduction or substitution without engineering review and dedicated validation |
| `SRC-PFF-993-SUNROOF-DEFLECTOR-REPAIR-LEAD` | German PFF thread: reference 911 564 127 00 for the sunroof deflector retractor and a successful replacement report | D | Hobbyist lead with no dimension, instrument, CAD, scan or license; obtain a removed part and measure before any reconstruction |
| `SRC-BMB-GERMANY-CT-RE` | German laboratory BMB: three published CT configurations, from 7 µm to 0.2 mm, parts up to 3,500 × 2,000 mm and 200 kg, surface reconstruction and STL advertised | B | Service capabilities, not a 993 case nor open data; ask for uncertainty, datums, format and rights before acquisition |
| `SRC-HACHTEL-BASIC-CT-SCAN` | German Basic Scan CT offer for small parts: advertised volume Ø180 × 180 mm, voxel output, optional STL, €99 | C | No cleanup, segmentation, voxel resolution, uncertainty or reuse license; lead for a polymer cover, to be supplemented by controlled metrology |
| `SRC-FRAUNHOFER-ROBOCT-LARGE-PARTS` | Fraunhofer IIS: robotic RoboCT for large automotive parts, including doors, tailgates and side structures, with regions of interest and microtomography | B | Research/service lead with no 993 case, file, report or published rights; request a protocol and a contractual deliverable |
| `SRC-VISION-METRIC-CT-DIGITIZATION` | German provider: ZEISS METROTOM, 165 × 140 mm volume, 65.3 µm voxel or 32.6 µm at high resolution, STL and analyses advertised | B | Declared capability for small parts, with no 993 case, uncertainty, repeats or data license; request a sample and a report |

These results add contacts and a few small-part candidates, but none yet
constitutes an instrumented measurement or reusable geometry with established
rights. Above all, the German search confirms the value of a direct campaign on
a removed interior part.

These providers offer an acquisition route, not an open corpus. The brief to be
sent must require the variant and part number, reference marks and scales, the
metrology report, the output format, the tolerances, the treatment of hidden
surfaces and an explicit license for the delivered CAD. For a hollow part or one
with internal channels, CT is the relevant method; for a body or a large
exterior interface, a laser scan or a registered photogrammetry must be
supplemented by dimensional references. No public, calibrated and reusable 993
LiDAR was found in this pass. The Schöner site is an apparent exception — a
LiDAR claim explicitly found — but it remains a lead with no usable data or
verified rights, on an electrified, non-OEM GT2 EVO II body.

## Batch 3 — Original masses, through German-language search

`SRC-FEDERLEICHTE-ELFER-993-WEIGHTS` provides what no English-language source had
given: the masses of the original 993 parts, against the lightweight versions,
material by material, over three pages — exterior, interior, technical.

### What this project can use directly

Small trim parts, non-critical, replaceable like for like:

| Part | Original | Lightweight | Saving |
|---|---:|---:|---:|
| Door trim strips | 550 g | 170 g | 380 g |
| Lightweight dashboard | 2,100 g | 950 g | 1,150 g |
| Dashboard top | — | 290 g | — |
| Air ducts | — | 35 g | — |
| Heater cover | — | 10 g | — |

These are exactly the shapes the selector brings up — `cover strip`, `cover`,
`insert` — and exactly the domain where polymer printing is the right process.

### What the big numbers hide

The biggest savings in these tables are **not** replacements:

| Line | Displayed saving | What it really is |
|---|---:|---|
| Ventilation assembly | 11.4 kg | Removal of the heater, not a replacement |
| Racing seat | 12.5 kg | Affects occupant restraint |
| Lightweight steering wheel | 1.9 kg | Removal of the airbag |
| Doors | 26 kg each | Loss of the side-impact bars and the glass |
| Roof | 19.5 kg | Structural welded panel |
| Wheels, ball joints | 1.5 to 3.3 kg | Class presumed critical by `SAFETY.md` |

A mass table does not say what one is allowed to remove. Classify before
quantifying, never the reverse.

## Batch 4 — JavaScript-rendered pages

Several sources were classified as unusable on August 28 when they were only
**client-side rendered**: the page responded, but its content existed only
after the JavaScript ran. That is not a refusal, it is a rendering problem —
and the distinction changes everything, because a refusal is respected while a
rendering problem is solved.

Check of the `robots.txt` files on August 29, 2026:

| Source | What its robots.txt says | Verdict |
|---|---|---|
| `porsche.com` (Classic catalog) | `User-agent: *`, disallows only `/api/`, `/search/`, `/login/` and some archives. **No named agent.** | **Allowed** |
| `wheel-size.com` | Allows `/size/`, disallows only `/admin/`, `/api/`, `/data/` and filter combinations | **Allowed** |
| `newsroom.porsche.com` | `allow: /` | Allowed, and already readable |
| `pcss-tsi.porsche.com` | The `robots.txt` itself returns 403 | Closed host, out of reach |
| `rosepassion.com` | `ClaudeBot` and `Claude-Web` under `Disallow: /` | **Refused**, see ADR 0003 |

The first two lines are the finding: **the official Porsche parts catalog and
the wheel data are allowed**, and their content went unread solely for lack of
a rendering engine.

### Test run on August 29, 2026, and its result

The hypothesis was that a server-side browser would remove the obstacle. It was
tested, on a Cloudflare account, via Browser Run and its Kitesurf engine.

**The engine works**: the wheel-size page was indeed rendered, 115,293
characters extracted where a plain request returned almost nothing.

**And the hypothesis is refuted on both targets.**

| Target | Rendering result |
|---|---|
| `wheel-size.com` | The rendered page shows `Bolt Pattern (PCD): -`, `Thread Size: -`, `Wheel Tightening Torque: -`. These values **are not published**; they were not hidden |
| `porsche.com` catalog | 722 characters, metadata only, **identical with Kitesurf and with Chromium**. The body is served to no headless browser |

The lesson goes beyond these two pages: an empty field on a page can mean
"rendered later" or "never published", and only an actual render tells them
apart. Here, it was the second answer in both cases.

Browser Run also changes **nothing** about the last two lines of the previous
table: a host that returns 403 stays closed, and a site that refuses named
agents keeps refusing them from any infrastructure.

## Remaining Phase 1 work

- [x] 3D models under a verifiable license — part files listed per record; the
      GT2 scan still has an imperfect rights chain, and no freely reusable 993
      body scan was found. See batches 2 and 5.
- [x] Classification by variant, year and availability — every record carries
      its coverage, variants and access status; ambiguous cases stay flagged in
      the notes rather than merged.
- [x] Missing or hard-to-obtain parts — first case documented by a source: the
      Turbo engine carrier `993 115 021 53` has no replacement alternative, the
      tubular carrier on the specialist market being explicitly non-Turbo. The
      three polymer candidates of phase 2, for their part, remain chosen on
      engineering criteria and not on documented scarcity.
- [x] Cross-assessment of provenance, license, accuracy, reuse — the 294
      records state the known rights, the evidence level and the usage limits;
      no unverified data is promoted to catalog geometry.

Status: twenty documented candidates, the phase exit threshold is reached in
number; the registry now holds 294 valid source records. The Renn 3D Parts
archive adds nine leads to public STL files, but their licenses stay attached to
each record and their bboxes do not replace a measurement. The Porsche Fanatics
project data and the manual data increase technical coverage, while the new
German scans and sources increase lead coverage,
but they turn no candidate into a releasable part. Sources without automated
access count as listed candidates, not as exploited data. Two examples,
`SRC-TEILE-COM-993-ENGINE-CARRIER` and
`SRC-RENNLINE-TUBULAR-ENGINE-CARRIER`, refuse automated access: they count as
listed candidates, not as exploited sources.
