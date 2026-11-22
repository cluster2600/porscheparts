# 935 head twin: identity of the specimen and a check of the scale

Search of 22 November 2026, for issues #692 and #693. **Nothing here is a
measurement of the scanned head.** Published values are declared hypotheses
with their sources. The records are the twin's
[specimen-identity.json](../../twins/935-cylinder-head-cad-twin/params/specimen-identity.json)
and [scale-check.json](../../twins/935-cylinder-head-cad-twin/params/scale-check.json);
the assumed identity is H16 and H17 in the
[hypotheses register](../../twins/935-cylinder-head-cad-twin/hypotheses.json).

## Why

The owner decided on 2026-11-22 that what the two issues wait for is researched
online and that the twin works on declared assumptions, to be reviewed by
Wolfe Classics, the seller of the scan. Nobody was contacted. This search builds
on the [faithful-replica dossier of 2026-10-28](935-faithful-replica-20261028/README.md),
which recorded the seller's private statement (Xtreme, cast then machined) and
the maker's four catalogue programs, and on the
[published-data search of 2026-11-16](935-head-published-data-20261116/README.md),
which read the 930 Turbo and 964 Turbo homologation forms. Neither was redone.

## Result in short

- **Assumed identity (H16, H17):** a new Xtreme Cylinder Heads casting, cast
  then machined, for a Porsche 935; two valves, two plugs, four head studs,
  8 mm stems and M12 × 1.25 plugs; the maker's 2.0–2.9 litre program, for the
  2.85 L 935 engine, bore at most 92.8 mm. Status: assumed by owner decision
  2026-11-22, not confirmed. The 3.0–3.5 litre program stays open.
- **Scale:** the 1 mm unit holds within the primary check, the plug thread
  bore against M12 × 1.25: s from 0.934 to 1.053. The chamber shoulder agrees
  to within 0.9% but rests on H17, so it is not counted. The guide bore reads
  0.49 to 0.56 mm larger than an 8 mm guide (s 0.935 to 0.942), unexplained.
- **No published figure describes this specimen.** The only published
  statement about it is the listing: "Made specifically for a 935 racecar but
  can fit other 70s or 80s models of 911".

## How the pages were read

Each host's `robots.txt` was read before any page. Pages were saved privately
on 2026-11-22 under `work/935-cad-twin/agents-20261122/692-693/pages` (outside
Git), turned into text, and every quote in the identity record was matched
again against that saved text by a script before it was written; values from
the homologation forms, the 993 manual record and Wikipedia were re-read in
their saved copies by hand. Hosts that refused automated readers or answered
with a bot check were left alone ([decision 0003](../decisions/0003-no-vendor-harvesting.md)).
Search tools drop table rows and merge lines: the bore of the 935 came back
from the search summaries as "92.8" with several bores beside it, and only the
saved pages showed which page says which, and that two of them contradict
themselves.

## Queries

| Query | What it gave |
|---|---|
| Porsche 935 engine 2857 cc bore 92.8 mm stroke 70.4 twin ignition | enthusiast spec pages with 92.0, 92.4 and 92.8 mm bores; Wikipedia |
| "92.8" bore Porsche 935 2857 "70.4" technical data newsroom OR museum | the same pages; no Porsche page with a bore |
| Porsche 935 "Bohrung" "92,8" Hub "70,4" 2857 | MAHLE Motorsports catalogue pages; no Porsche page with a bore |
| Porsche 935 1976 Doppelzündung Zylinderköpfe luftgekühlt newsroom | Porsche Heritage Moments pages, no ignition data |
| Porsche 935 engine type 930/72 ... twin-plug ignition air-cooled heads 2.85 | Supercar Nostalgia (twin plug ignition), forum posts |
| Porsche 911 cylinder head stud spacing mm crankcase head studs pattern dimension | forum posts and a service bulletin on stud height; no published spacing |
| Porsche 911 930 cylinder head stud "M10" Dilavar head nut torque 32 Nm | forum posts and retailers |
| ARP 204-4206 Porsche 911 930 air-cooled head stud kit thread size M10 x 1.5 | retailer pages naming M10 × 1.5; none could be opened |
| Porsche 935 twin plug cylinder head 12mm spark plugs second plug 911 racing heads | auction and forum pages; no published plug thread for a 935 head |
| spark plug thread sizes M12x1.25 M14x1.25 ISO 28741 thread diameter pitch table | The Engineering ToolBox table of ISO 28741 |
| Creaform HandySCAN 700 technical specifications accuracy | reviews and the maker's pages; not used (below) |

Pages were also read directly, without a search: the Wolfe Classics sitemap,
listing, services, gallery and related 935 scan listings; every page of the
Xtreme Cylinder Heads sitemap except the contact form; Wikipedia's Porsche 935, Spark plug and ISO
metric screw thread articles by their raw wikitext; the Porsche Newsroom
turbo press kit; the FIA historic database form 645.

## Sources kept

| Source | Kept for | Applies to |
|---|---|---|
| [Wolfe Classics listing](https://www.wolfeclassics.com/shop/p/p-car-billet-cylinder-head-scan) | the only published statement about the specimen | same head |
| [Wolfe Classics services](https://www.wolfeclassics.com/services) | the two scanners the seller names | the seller's equipment |
| [repository dossier](935-faithful-replica-20261028/README.md) | the seller's private statement: Xtreme, cast then machined | same head (private) |
| [Xtreme programs](https://www.xtremecylinderheads.com/programs), [2.0–2.9 L](https://www.xtremecylinderheads.com/castings-1), [3.0–3.5 L](https://www.xtremecylinderheads.com/castings-2), [3.6–4.0 L NA](https://www.xtremecylinderheads.com/castings-3), [3.6–4.0 L turbo](https://www.xtremecylinderheads.com/castings-4) | process, programs, 8 mm stems, 12 or 14 mm plugs, valve and chamber ranges | same family |
| [Xtreme shop](https://www.xtremecylinderheads.com/ourshop) | the maker engraves its logo on its castings | same family |
| [Porsche Newsroom turbo press kit](https://newsroom.porsche.com/en/press-kits/50-years-porsche-turbo/Porsche-and-turbo-technology-in-motorsport--from-pioneer-to-world-champion.html) | the 935 of 1976: 2.85 litres | same engine family (H17) |
| [Wikipedia: Porsche 935](https://en.wikipedia.org/w/index.php?title=Porsche_935&oldid=1385579704) | the 1.4 turbo factor and the 4.0 L class; capacities 2.8 to 3.3 L; optional 3.0 L customer engine | same engine family |
| [Supercars.net 935/76](https://www.supercars.net/blog/1976-porsche-93576/) | bore 92.8, stroke 70.4, 2856 cm³; dual ignition | same engine family |
| [Supercar Nostalgia 935/76](https://supercarnostalgia.com/blog/porsche-935-76) | bore 92.4, stroke 70.4, 2856 cm³; twin plug ignition | same engine family |
| [Ultimatecarpage 1976 935](https://www.ultimatecarpage.com/spec/423/Porsche-935.html) | Type 930/72, bore 92.0, stroke 70.4, 2,808 cm³ | same engine family |
| [FIA form 3076](https://historicdb.fia.com/sites/default/files/car_attachment/1601075701/homologation_form_number_3076_group_3.pdf) | one plug per cylinder, chamber 89.6 cm³ (930 Turbo 3.0) | other head |
| [FISA form B-298](https://historicdb.fia.com/sites/default/files/car_attachment/1479168902/homologation_form_number_298_group_b.pdf) | valve angles 25° 30′ and 30° 15′, 9 mm stem (964 Turbo 3.3) | other head |
| [993 manual record](../../catalog/manual/993-workshop-manual-measurements.json) | guide bore 8.00 to 8.015 mm, plug thread M 14 × 1.25 | other head |
| [The Engineering ToolBox: ISO 28741](https://www.engineeringtoolbox.com/spark-plugs-iso-metric-threads-d_2032.html) | M12 × 1.25 and M14 × 1.25 major and minor diameters | a standard |
| [Wikipedia: ISO metric screw thread](https://en.wikipedia.org/w/index.php?title=ISO_metric_screw_thread&oldid=1381962783) | minor and pitch diameters from the major diameter and pitch | a standard |

The bores disagree, and two of the three pages contradict themselves:
Supercars.net gives 2856 cm³ and 92.8 mm in its table and "the 2808cc flat-6"
in its text; Supercar Nostalgia gives 2856 cm³ and a 92.4 mm bore, which with
the 70.4 mm stroke make 2832 cm³. Porsche's 2.85 litres and the class limit,
4000 / 1.4 = 2857.1 cm³, both point to 92.8 mm with that stroke; that is
arithmetic on published figures, not a published bore of this head.

## Sources rejected, and why

| Source | Why |
|---|---|
| FIA form 645 (Porsche Turbo, Group 4) | an image-only PDF; an OCR pass at 300 dpi gave unreadable items. It describes the 930 Turbo 3.0 for Group 4 (bore 95 mm legible), not this head. OCR images deleted |
| Stuttcars 935/76 specification page | the saved page carried no specification text |
| Summit Racing ARP 204-4206 page | bot check; left alone |
| Rudy's Diesel ARP head stud kit page | answered 429; left alone |
| pelicanparts, rennlist, design911, lnengineering forum and shop pages | refuse automated readers (2026-11-16 note); forum figures are not admitted |
| Retro Sport 935 head set (930 104 048 01) | refuses automated readers (403); kept only as recorded in the 2026-10-28 dossier |
| Wolfe Classics 935 K4 engine, body and stripped-car scan listings | real 935 cars scanned by the seller; no page links the head to any of them |
| Porsche Heritage Moments 935 pages | no engine data beyond the variants |
| MAHLE Motorsports Porsche catalogue pages | kit tables with a chamber volume beside each kit (68 cm³ for 2.7 to 2.9 L kits, 90 cm³ for 3.0 L and over) whose column is not labelled in the text layer; a lead that the maker's two programs follow the production head families, not used as a value |
| Creaform and Shining 3D scanner specifications | the scanner of this scan is not stated, and a scanner's specification is not the accuracy of a scan |

## Discriminating features and what they say

| Feature (twin record) | Fitted | Says |
|---|---|---|
| plug bores per chamber ([feature-fits](../../twins/935-cylinder-head-cad-twin/params/feature-fits.json)) | 2 | twin plug, as the 935; not a production 930 head (one plug) |
| plug thread bore ([reference sheet](../../twins/935-cylinder-head-cad-twin/params/reference-sheet.json)) | 11.40 mm, confirmed | a 12 mm plug under the 1 mm unit; not the 993's M14 |
| chamber shoulder ([frame](../../twins/935-cylinder-head-cad-twin/params/frame.json)) | 92.80 mm | the 2.85 L 935 bore, if the chamber edge is the bore |
| register recess | 113.88 mm | nothing: no published register diameter found |
| stud passages | 4, square of 85.6 to 85.8 mm | nothing: no published stud pattern found |
| valve axes | 25.89° and 29.89° | the 911 two-valve geometry; no scale, no program |
| guide bore | 8.51 mm, not confirmed | not the production 9 mm stem; 0.5 mm over the maker's 8 mm |
| seats and throats | exhaust-side seat 43.0 mm at mid-band | weakly toward the 3.0–3.5 L program, if valve_y_plus is the exhaust |
| chamber volume | not computed | would separate 68–73 from 86–90 cm³ |

## What stays unresolved

- The program and the bore: no published statement, and the chamber volume is
  not computed (it needs declared valve faces; the private occupancy grid's
  descriptor was not found on 2026-11-22).
- The engine type number, a part number or casting mark, the material batch,
  the scanner and its export unit.
- The guide bore: half a millimetre over an 8 mm guide, unexplained.
- No published register diameter, stud pattern or stud thread of any
  candidate could be opened.

The eleven questions for the reviewer are in the identity record. The scale
stays the owner's instruction until a contributed measurement (decision
[0019](../decisions/0019-accept-contributed-measurements.md)) or the seller's
statement of the scanner's unit arrives.
