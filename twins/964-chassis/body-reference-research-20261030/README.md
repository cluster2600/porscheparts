# 964/993 body-reference research — 30 October 2026

**Four official Celette setup PDFs were recovered from public links in the
current store, including the 964 base set and the 993 complement.** This
corrects the earlier assessment that the relevant documentation was only
available behind the old site's login. It does not establish that an entire
body-coordinate database is publicly downloadable.

The practical result is a better fixture/version map, a German illustrated
tunnel reference, and a specific lead for additional height tables. **No new
body-point XYZ coordinates were accepted into the interface contract.**

The [manifest](manifest.json) records URLs, byte counts, SHA-256 hashes and
reviewed pages. Source PDFs and photographs remain in ignored local storage
under `work/964-deep-web-research-20261030/`; they are not redistributed in Git.
This directory is a retrieval cache, not a durable private evidence release.
The research is targeted, not an exhaustive census of internet content.

## Newly acquired first-party fixture documents

All eight pages below were rendered and visually inspected. The printed sheet
identifier matters more than a reseller's abbreviated description.

| Set | Public document | PDF page → printed sheet | Printed date | Contribution |
|---|---|---|---|---|
| 564.300 | [Celette PDF](https://store.celette.com/media/image/document/f4/dd/f4dd0eb688de7b88162cce08b703951d47a7159b.pdf) | 1 → 425-D-4B; 2 → 425-D-4A | 7 October 1988 | Historical Carrera 4 4WD arrangements; not a C2 setup by assumption |
| 564.310 | [Celette PDF](https://store.celette.com/media/image/document/11/e2/11e20ee54a70d5f703302e6186f62263756f0952.pdf) | 1 → 425-D-4E; 2 → 425-D-4F | 9 July 1990 | Earlier C2/C4 arrangements; preserve separately from the later set |
| 564.320 | [Celette PDF](https://store.celette.com/media/image/document/2d/48/2d488671e56e55dfd4536a98782213ef7f511bea.pdf) | 1 → 425-D-4H; 2 → 425-D-4J | 30 January 1997 | C2/C4 fixtures, model-year alternatives and setup details |
| 564.307 | [Celette PDF](https://store.celette.com/media/image/document/64/a5/64a5ca2ec35175f471860df12342aa8a562c5a4a.pdf) | 1 → 425-D-4K; 2 → 425-D-4L | 9 July 1993 | Explicit 993 complement to 564.320 |

For 564.320, page 1 distinguishes the arrangement through model 1990 from
the model 1991 arrangement in figure 5. Page 2 distinguishes C4 figure 11
from C2 figure 12: fittings 31/32 use spacer 33 or 34 respectively. These are
**Celette item numbers**, not Porsche manual P31/P32 or our point register.
The scan donor remains user-reported C2 with unknown model year and gearbox.
Neither this sheet nor the earlier Porsche P14 width fork identifies that donor.

For 564.307, the manufacturer explicitly specifies the base-set relationship.
The different rear arrangements demonstrate why a 993 interface survey cannot
be replaced by a blanket claim that the 964 shell is interchangeable. The
fixture bill of materials is not a complete monocoque attachment inventory.

These are setup drawings: they associate dedicated fittings, MZ towers,
traverses and numbered bench positions. They also contain tool settings.
They do **not** enumerate chassis-point X/Y/Z coordinates in our vehicle frame.
Reconstructing coordinates from them would additionally require the bench
datum/grid definition, actual fitting contact geometry, offsets and uncertainty,
plus correspondence to the vehicle features. A tower designation such as MZ 080
must not be imported as a chassis Z coordinate.

### What the German and Swiss rental catalogues add

- [Carbesa's bilingual catalogue](https://www.carbesa.ch/fileadmin/user_upload/Carbesa/Services/Mietwerkzeuge_Preisliste.pdf),
  dated 2 December 2020, pages 40–41: 564.320 and the 564.307 complement;
  sheet references 425.D4H, 425.D4G and 425.D4K. **425.D4G is a further
  document target**, not one of the pages recovered above. This historical
  catalogue does not establish current stock or a current rental quote.
- [Richtsatz-Express](https://www.richtsatz-express.de/index.php/versteckte-kategorieliste/category/1639-porsche):
  lists the older 564.300/8/9 combination for 964 and adds 564.307 for 993.
  This is a fixture-family lead, not permission to combine arbitrary revisions.
- [Tkaczyk](https://richtsatz-mieten.de/richtsaetze/porsche/): still lists
  564.330 for the 964/993 description. The official 564.307 relationship is
  now established; the meaning of this different rental designation remains
  open in [CTR-0017](../../../catalog/registers/contradictions.json).

## Forums: follow attachments, then compare with the existing manual

| Thread | Observation | Treatment |
|---|---|---|
| [Pelican: 964 front chassis and suspension differences](https://forums.pelicanparts.com/porsche-964-993-technical-forum/1134144-964-front-chassis-suspension-differences.html) | Three original image files retrieved from the manual post, including the cover and dimension plates | The floor-control/table and early assembly plate duplicate material already held. The early P14 span is not the MY91+ span. No additional height table recovered |
| [Pelican: 2012 fixture-set listing](https://forums.pelicanparts.com/porsche-911-used-parts-sale-wanted/703702-celette-964-fixture-set-mz-tower-system.html) | Owner describes 564.320 plus 564.307, while expressing uncertainty about year coverage | Useful discovery lead, superseded by the manufacturer PDFs for the set relationship; not donor applicability evidence |
| [Pelican: 2024 fixture search](https://forums.pelicanparts.com/porsche-964-993-technical-forum/1171854-964-993-celette-fixtures.html) | Names the same two references | Confirms a research lead, not dimensions or current availability |
| [Pelican: 2005 discussion](https://forums.pelicanparts.com/porsche-911-used-parts-sale-wanted/221562-fs-73-911-sunroof-clip.html) | Historical Celette North America 564.307 PDF link | Tested: HTTP 200 returned HTML, not a PDF. Replaced by the working current-store link |
| [Rennlist: 993 blueprints](https://rennlist.com/forums/993-forum/1285117-993-chassis-and-suspension-blueprints-3d-models.html) and [earlier thread](https://rennlist.com/forums/993-forum/765037-993-blueprint-with-dimensions.html) | Indexed attachments include a small body-dimensions PDF | Attachment contents not recovered this pass; retain the existing access limitation, not a claim that the file is unavailable everywhere |
| [Rennlist: 993 jacking points](https://rennlist.com/forums/993-forum/1191329-jacking-point-dimensions-993-carerra-4-a.html) | Discussion mixes point definitions and diagonal/longitudinal interpretations | Already registered; no forum number promoted to a measured body datum |

The photographed Porsche plates are not independent measurements of another
body. Search results for early 911 floor drawings, wheel alignment and outer
vehicle dimensions were kept separate from the required 964/993 body datums.
Our own PorscheFanatics pages are not independent corroboration.

## Tunnel: a useful German manufacturer reference

[CAE article 10064 installation manual](https://cae-racing.de/mediafiles/Sonstiges/Porsche/EBA_PORSCHE%20964-V3.pdf)
covers a manual-shifter retrofit for 964 C2 and 993. Page 2 shows the rear
tunnel reinforcement around the shift-rod passage and describes access through
the lower tunnel cover. This helps identify features that must be represented
and surveyed, beyond the visible lower skin of the underbody scan.

It also describes cutting that reinforcement for its own racing retrofit.
That proposed modification is **not factory geometry**, a monocoque design
instruction or a strength result. The manual provides neither a datum-based
mounting pattern nor a swept linkage envelope. Its five/six-speed instructions
do not identify the project's unknown gearbox, and they do not establish C4
propeller-shaft space. Keep those configurations separate.

## Stronger coordinate leads, still to acquire and authenticate

**CarGeometry is more specific than a generic scan-service lead.** The
[964 archive listing](https://cargeometry.org/porsche/105-porsche-911-carrera-964-1989-1994-body-dimensions.html)
contains 24 public image URLs, including the vehicle photograph, familiar
Porsche manual pages, and additional plan/side drawings with numeric tables.
Public preview images 03, 09 and 20 (the filenames' suffixes) show height/point
tables distinct from the already-held Porsche assembly plate. Body styles
are mixed; some previews explicitly concern Cabriolet.

The directly linked larger previews were also retrieved. They remain too
limited for reliable complete transcription and identification of every datum.
The archive is advertised at USD 20; no purchase was made. Original publisher,
revision, unit conventions, point identities and reuse rights remain to be
established. **Do not infer a full coordinate set from the previews.** The
[separate 993 listing](https://cargeometry.org/porsche/109-porsche-911-carrera-coupe-993-19941998-body-dimensions.html)
remains a separate acquisition target already in the source registry.

Other specialist routes were checked:

| Route | What the public source establishes | Missing for this project |
|---|---|---|
| [Car-O-Data](https://car-o-liner.com/en-us/product/car-o-data/) | Manufacturer describes upper/lower points, setup data and an annual subscription | Exact 964 C2 and 993 entries, revision, point definitions and exportable nominal values not obtained |
| [Blackhawk catalogue](https://blackhawkcollision.com/wp-content/uploads/2020/10/Blackhawk-catalogue-2020-EN.pdf) | SHARK measuring-system/database route | No specific 964/993 sheet recovered; generic equipment capabilities do not prove a model's coverage |
| [Car Bench](https://www.carbench.it/en/) | Current manufacturer site and reserved area | No public 964/993 coordinate sheet recovered; older indexed Porsche page did not open |
| [Spanesi](https://spanesi.com/automotive-measuring-systems/) | Manufacturer measuring-system route | No public nominal 964/993 data export recovered |

These are access/coverage observations for this pass, not evidence that the
providers lack the data. A search snippet, equipment approval or workshop
marketing page is not the actual model-specific measurement report.

## What this changes in the next engineering step

1. **Use the recovered 564.320 C2 and 564.307 sheets for a correspondence
   review.** Identify the physical feature touched by each relevant fitting,
   retain the Porsche point ID and Celette item ID in separate fields, and
   document the interpretation. Do not fill missing coordinates from drawing
   pixels or bench-station numbers.
2. **Prioritize the additional coordinate tables.** Obtain a legible sample
   with its original publisher, model/body style, date, datum definition and
   units before purchasing a compilation or requesting a database export.
   For Celette, target 425.D4G and the dimensional definition/calibration of
   the contact tooling; the setup PDFs alone are not that definition.
3. **Extract a new, traceable documentary dataset when acquired.** Two
   independent readings, explicit units, point/side/feature identity, original
   uncertainty and checks against the already-held Porsche spans are required.
   Keep documentary nominal coordinates distinct from surveyed donor points.
4. **Use CAE's photo to guide the tunnel feature inventory.** The reinforcement,
   shift passage, lower cover, service access and moving linkage need explicit
   interfaces. Preserve unknown transmission-specific clearances.

This research narrows the missing inputs. It neither replaces the already-held
marble measurements nor establishes complete interior geometry, laminate
properties, structural performance, manufacturing readiness or homologation.
The [interface survey](../interface-measurement-plan.md) remains the acceptance
path for the actual donor and its separate 993/C4 compatibility checks.
