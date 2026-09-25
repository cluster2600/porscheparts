# Phase 2 — 993 CAD and 3D files found in the communities

Date consulted: August 29, 2026. Queries run in German, English and French
around `993 CAD`, `CAO`, `STEP`, `STL`, `3D scan`, `SolidWorks`, `FreeCAD`,
`Rennlist`, `PFF`, `GrabCAD`, `Thingiverse` and `Printables`.

## Conclusion

Owners have indeed worked on functional 3D files for the 993. The public corpus
covers mostly small parts, accessories, shop jigs and visual meshes. No
complete, parametric, metrological CAD assembly of the car was found.

The four new leads most useful to the twin are:

1. three CAD jigs for windshield setting depth, derived from physical jigs and
   then redrawn in SolidWorks;
2. a scan of a complete Carrera advertised at full scale with 2 mm accuracy.
3. a second scan, this time of a 1996 Turbo, sold as OBJ and advertised at
   1.76 mm exterior accuracy;
4. an industrial case study covering the metrological scan and reverse
   engineering of a 1995 993 Coupé at Juliá Automobile.

The jigs can document a body shell–glazing interface; the two commercial scans
can provide body envelopes; the case study identifies a holder of professional
data. None may be presented as certified geometry before the files, the scale,
the variant and the rights have been checked.

## Second wave of research

The search was extended to GitHub and GitLab repositories, Carpokes, Pelican
Parts, PFF, Cults, Thingiverse, 3D Warehouse, scanning service providers and
restoration shops. To date, no identifiable public Git repository contains a
993 assembly or part under an explicit name in STEP, FreeCAD, OpenSCAD or STL.
The results that are actually usable are scattered across forums and
marketplaces.

| New source | Geometry or information | Value for the twin | Status and safeguard |
|---|---|---|---|
| Wolfe Classics | OBJ exterior scan of a 1996 Turbo, advertised accuracy 1.76 mm | second complete envelope, useful for cross-comparison | purchase required; roofline flagged as weak; license and metrology to be requested |
| SHINING 3D / Juliá Automobile | scan and reverse engineering of a 1995 Coupé | identified holder of professional body shell and body geometry | private files; 0.02 mm describes the scanner, not the uncertainty of the complete model |
| Cults / formfactorperformance | wheel center cap `993361303.11` in STEP and STL | first small part found in an editable CAD format | private license, no evidence of retention or fit |
| Cults / ITMonkey | left/right reinforcements for the non-HiFi door pocket in STL | local geometry with a declared envelope and a clear function | paid, private use, no interface dimension published |
| Carpokes | repair insert for the 944/964/993 climate control knob | specialist community and an old thread with feedback | file URL and license to be recorded in an authenticated session |
| PFF / 1.AVM | 993 sunroof components rebuilt in reinforced polymer | evidence that functional CAD exists in Germany | no public file, dimension or reference; contact to be established |
| Denk3D | repair kits for the 964/993 switch-panel clips | two families of candidate small interior interfaces | commercial product, closed CAD; measure a real part |
| Thingiverse / LimeyBoy | Momo RS horn ring: 52 mm inside, 59 mm outside, 3 mm protrusion | small geometry bounded by three declared dimensions | exact license and electrical operation to be checked |
| Pelican Parts / gmorat | bumperette delete inserts, several iterations | reveals the real variability of the bumper cutout | no file; design parametrically and measure each car |

This wave therefore mainly adds two holders of complete scans, six families of
small parts and one important design constraint. It does not change the
central conclusion: no public file yet constitutes an assembled, reusable,
metric digital twin.

## Ranked results

| Priority | Item | Advertised format or process | Evidence available | Current limit |
|---|---|---|---|---|
| high | windshield setting jigs | SolidWorks, then 3 printable files, top/bottom/side | design thread, scale corrections, Printables link and usage feedback | license, master files, dimensions and uncertainty to be checked |
| high | complete scan of a "barn find" Carrera | scan mesh, 1.6 M triangles | full size and 2 mm accuracy declared by the seller | paid, variant and calibration report missing, redistribution prohibited |
| high | exterior scan of a 1996 Turbo | OBJ, 1.76 mm exterior accuracy declared | service provider's listing and roof defect explicitly flagged | paid, process, deviation map and license not published |
| high | Juliá Automobile reverse engineering | metrological scanning system and professional CAD | German case study, car and model year identified | private data; instrument accuracy differs from overall uncertainty |
| medium | wheel center cap `993361303.11` | STEP and STL | OEM reference and master formats declared | private license, no evidence of fit or retention |
| medium | non-HiFi door pocket reinforcements | two STL, left/right | published envelope and documented function | paid, private license, tolerances and test missing |
| medium | rear seat adjustment bushing | STL in a ZIP archive | author and a user describe fabrication and fitting | license, dimensions, material, mass and variant unknown |
| medium | split rear grille bar | Thingiverse STL, community CAD | design log, finishing and fitting photos | custom part, not an OEM reproduction; exact license to be reconfirmed |
| medium | speaker frames, cup holders, phone mount, bleed tab | STL on Thingiverse/Printables or Renn3D archive | files and a few fitting photos | scale, material, mass, license and fit still incomplete depending on the part |
| low | CGTrader/GrabCAD/3DModels.org bodies | Blender, FBX, OBJ, STL or STEP conversion | detailed visuals, sometimes advertised overall dimensions | render or miniature geometry, no local metrology demonstrated |
| low | GT2 scan by videogrammetry | Sketchfab mesh, CC BY | free mesh and described provenance | no scale or accuracy, third-party video frames |

## Particularly useful threads

- [Rennlist index of 993 3D parts](https://rennlist.com/forums/993-forum/1451330-thread-of-993-3d-printed-diy-bits.html):
  speakers, windshield jigs, cup holders, console and seat bushings;
- [development of the windshield jigs](https://rennlist.com/forums/993-forum/1401664-windshield-replacement-diy.html):
  three CAD files to set the glazing depth;
- [history of digitizing the jigs](https://rennlist.com/forums/993-forum/937323-f-s-993-windshield-back-glass-templates-5.html):
  move from a physical tracing to SolidWorks and resolution of scale problems;
- [seat rail bushing](https://rennlist.com/forums/993-forum/958995-993-passenger-and-driver-side-seat-rail-replacement-alternative-2.html):
  STL attached to the forum and usage feedback;
- [split grille bar](https://rennlist.com/forums/993-forum/1189086-993-custom-split-grill-3.html):
  Thingiverse file `4349486` and fitting log;
- [request for chassis and suspension plans](https://rennlist.com/forums/993-forum/1285117-993-chassis-and-suspension-blueprints-3d-models.html):
  the public reply provides a PDF of body shell dimensions, not a 3D model.
- [exterior scan of a 1996 993 Turbo](https://www.wolfeclassics.com/shop/p/1996-porsche-911-turbo-3d-scan):
  OBJ advertised at 1.76 mm, with a known limit at the roof;
- [German SHINING 3D / Juliá Automobile case study](https://www.shining3d.com/de/juli%C3%A1-automobile-shining-3d-when-passion-meets-3d-scanning-technology-classic-porsche-rebor):
  professional scan of a 1995 993 Coupé for reconstruction;
- [Carpokes CAD library](https://www.carpokes.com/viewforum.php?f=20):
  thread dedicated to a repair insert for the 993/964/944 climate control knob;
- [German reconstruction of sunroof parts](https://www.pff.de/thread/2821329-3d-druck-mit-kohlefaser-cnc-fraesen-und-drehen-ersatzteile-besser-als-original/):
  photographic comparison between original parts and reproductions;
- [CAD development of bumperette inserts](https://forums.pelicanparts.com/porsche-964-993-technical-forum/905860-bumperette-delete-modification-ive-been-working.html):
  documents the cutout variations between cars.

Searches on PFF and the FreeCAD and Autodesk forums produced no shareable,
better-documented 993 CAD file. The GrabCAD results found concern mostly RWB
bodies, miniatures or render meshes.

## Next qualification action

1. ask Wolfe Classics and 21 Design for a sample, the reference frame, the
   scaling method, a deviation map and their license terms;
2. contact Juliá Automobile to find out whether sections, interfaces or
   targeted measurements can be shared without disclosing their complete model;
3. open the Carpokes and Thingiverse pages in an authenticated session to
   record license, author, formats and checksums;
4. ask the jig authors for the SolidWorks master file or a STEP, the reference
   dimensions and the body shell variant tested;
5. import into the repository only a file whose license actually allows
   redistribution; otherwise keep the URL, metadata and local digest without
   the mesh.
