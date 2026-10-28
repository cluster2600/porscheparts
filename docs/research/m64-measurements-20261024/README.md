# Additional M64/60 dimensions and inspection references

Reviewed on 24 October 2026. The register contains 107 records: 89 accepted
supplier/documentary records and 18 excluded FIA leads. Twenty source records
are linked, including 17 new canonical entries. No physical component was
measured. The accepted data comprise 80 nominal records, seven clearance
records, one explicitly derived comparison and one documentary-conflict record.
Three accepted records teach uncertainty rather than selecting a disputed value.

The [JSON register](../../../catalog/reference/m64-measurements-20261024/facts.json)
and [CSV export](../../../catalog/reference/m64-measurements-20261024/facts.csv)
retain each component, exact application, units, datum, conditions, tolerance
definition and variant basis. Source editions, representations and hashes are in
the [crosswalk](../../../catalog/reference/m64-measurements-20261024/source-crosswalk.json).
These are additional documented specifications, not a manufacturing drawing or
a complete dimensional survey of the 993 Turbo.

## Crankshaft and bearing interfaces

The [Glyco CATGY2201 catalogue](https://www.drivparts.com/content/dam/marketing/emea/fmmp/ecat/Glyco-Combined-Digital-Catalogue-CATGY2201.pdf),
PDF p.832 / printed p.802, entry 26, explicitly lists M64.60, M64.60R and the
supplier's M64.60RS application. Its English legend is PDF p.9 / printed VII;
the German legend is PDF p.11 / printed IX. The older Federal-Mogul edition is
the same manufacturer family, not an independent physical inspection.

| Interface or product quantity | Published value | Meaning |
|---|---|---|
| Big-end crankpin diameter | 54.971–54.990 mm | STD supplier journal interval |
| Big-end bearing housing diameter | 58.000–58.019 mm | Supplier housing interval |
| Big-end shell width | maximum 14.800 mm | Maximum bearing width, not journal length |
| Big-end shell wall | maximum 1.499 mm | Maximum standard shell thickness |
| Big-end oil clearance | 0.020–0.075 mm | Catalogue oil clearance; radial/diametral convention not inferred |
| Main journal diameter | 59.971–59.990 mm | STD supplier journal interval |
| Main-bearing housing diameter | 65.000–65.019 mm | Supplier housing interval |
| Main shell width, bearing 1 | maximum 27.890 mm | Bearing width |
| Main shell width, bearings 2–7 | maximum 17.000 mm | Bearing width |
| Main shell wall | maximum 2.500 mm | Standard shell thickness |
| Main oil clearance | 0.020–0.073 mm | Catalogue oil clearance |
| Crank-web distance | 28.000–28.052 mm | The labelled web spacing; not crankshaft endfloat |

Records M64-MEAS-B001 through B012 preserve the supplier's dimensions and
definitions. Remaining B records distinguish component-SKU data and an explicitly
derived 964/993 width comparison. These catalogue limits are not Porsche wear
limits, a machining authorization or load-capacity evidence for a modified engine.

## Pistons, pins, rings and seals

The Goetze 2019–2021 catalogue explicitly associates set 08-326200-00 with
M64.60/M64.60R. Its nominal axial ring heights are 1.750 / 1.750 / 2.000 mm for
top, second and oil rings at 100 mm STD bore. Those are axial heights, not ring
radial depth or end gaps. The [source crosswalk](../../../catalog/reference/m64-measurements-20261024/source-crosswalk.json)
links the exact manufacturer PDF and row locator.

The historical Wössner 2013/2014 catalogue supplies a separate aftermarket
configuration. These historical part suffixes and dimensions must not be
silently combined with a current catalogue revision.

| Exact historical Wössner application | Published declaration |
|---|---|
| K9018DA / K9018D200 | Compression height 31.6 mm; signed dome volume +12.12 cm³ |
| WP094 pin listed for those kits | 23 mm outside diameter, 13 mm inside-diameter entry, 61 mm length, 126 g |
| K9018DA / 1000XTY ring set | 1.5 / 1.2 / 2.5 mm axial stack |
| K9018D200 / 1020XSK ring set | 1.2 / 1.5 / 2.5 mm axial stack |
| K9018DA piston | Published nominal mass 462 g |
| K9018D200 piston | Published nominal mass 453 g |

The pin table's CT construction and incomplete bore profile do not establish a
constant cylindrical bore or a uniform wall thickness. No original Porsche
piston-crown thickness was established. LN PS104-015N geometry is retained as
an expressly labelled 4.1 L naturally aspirated comparison, not a Turbo kit.

MAHLE's already registered Porsche assembly guide adds generic minimum
piston-to-valve recommendations: 0.080 inch intake, 0.100 inch exhaust, and
0.050 inch radial clearance. These are supplier assembly recommendations, not
original M64/60 wear limits or proof of clearance with a chosen camshaft.

The [Victor Reinz September 2016 catalogue](https://www.victorreinz.com/img_cpm/002/Katalog%20komplett%2016/Printkatalog%20Reinz%20PKW%20PORSCHE.pdf),
PDF p.8, includes M64.60 in its 993 model row. It gives seal 81-21392-30 as
30 × 50 × 10 mm and seal 81-20004-30 as 90 × 110 × 12 mm. The register preserves
those dimensional sequences without inventing lip interference or housing fits.
Ring 71-29154-00 is listed with a 106 mm diameter designation and 1 mm thickness.
The precise diameter datum and compressed/uncompressed state are not specified;
these values do not describe a head wall or cylinder bore.

## Turbo shaft and bearing data

The captured Melett catalogue identifies replacement shaft/wheel 1301-016-436,
cross-referenced to 5316-120-2113 and 5316-120-5000. The existing TurboMaster
993 K16-6735 parts chain provides a conditional application link.

| Supplier dimension | Published value | Qualification |
|---|---|---|
| Melett turbine inducer / exducer | 55.0 / 49.1 mm | Replacement-product declarations |
| Melett turbine tip width | 6.7 mm | Labelled diagram datum |
| Melett shaft outside diameter | 8.5 mm | One printed decimal; no tolerance supplied |
| Turbo International 8-D-0910 bearing OD | 12.99–13.00 mm | K14/K16/K24 replacement family |
| Same bearing width / oil holes | 9.58 mm / four | Nominal supplier table |
| Generic K16 service-chart journal | 8.458–8.468 mm | Family-level reference, not exact 993 qualification |
| Generic K16 ring grooves | 1.49–1.54 mm | Chart dimensions, not ring width |
| Generic K16 axial-play maximum | 0.100 mm | Chart limit; its complete inspection protocol is not supplied |

No precision equivalence is asserted between a rounded 8.5 mm catalogue entry
and a different source's journal interval. They do not establish the same
measurement datum or an original wheel's complete geometry.

Two turbo conflicts remain explicit: the TI bearing ID is 8.50–8.51 mm in its
dedicated table but 8.49–8.51 mm in its service-kit table; TurboMaster prints
13.091 mm in both minimum and maximum bore columns. Neither conflict becomes
a selected machining acceptance band. No new compressor map, certified shaft
speed, complete wheel surface or modified-engine power result was obtained.

## Cylinder-head and valve-train comparisons

Schrick supplies dimensioned retainer and spring products. One outer-spring
entry specifies 202 N at 34.0 mm and 630 N at 21.0 mm: these are force-at-length
points, not free lengths. Exact product numbers and the 993 Carrera comparison
scope remain in the register.

Dougherty's GT 2 Turbo profile lists theoretical valve lifts of 0.485 / 0.470
inch under its zero-lash and theoretical-rocker-ratio conditions. The named
aftermarket profile is not an authenticated Porsche factory grind. Complete
lift-versus-angle laws and a fully specified angular/threshold convention are
not supplied.

The Carrera intake-stem entry differs between two factory documents: workshop
7.970 −0.012 mm versus technical booklet 7.920 −0.012 mm. Both actual local
page images were inspected. Record M64-MEAS-H016 preserves the conflict rather
than selecting a value or transferring it to the Turbo.

## FIA inspection boundary

The readable primary text of [FIA GT2-003](https://historicdb.fia.com/sites/default/files/car_attachment/1601074501/homologation_form_number_3_group_gt2.pdf),
PDF p.4, article 321e, supports a 25°30′ intake-valve-axis angle relative to
vertical for the homologated 993 GT2. It does not establish a production
tolerance, full axis coordinates or road-M64/60 applicability.

Actual source PDF bytes and viewable page images were unavailable for these FIA
documents in this environment. The exhaust-angle OCR and 18 image-only or
ambiguous comparison rows remain excluded with null values. Their source hashes
identify reader text or availability receipts, not original PDF bytes. Excluded
rows create no training targets. The excluded-lead register is useful for a
future authorized document inspection, not numerical reuse.

## Repository and training hand-off

Requirement REQ-M64-MEASUREMENTS-20261024 is to add attributable dimensional
inputs while retaining their measurement definitions. It supports architecture
element B-VERIFY in the [engineering architecture](../../architecture/README.md),
uses the [capture protocol](../../CAPTURE_PROTOCOL.md), and retains the existing
[ADR 0012](../../decisions/0012-local-compute-gpu-last.md). This increment changes
research data only; existing part records, CAD and release gates remain authoritative.

The [training increment](../../../training/m64-measurements-20261024/README.md)
contains 89 authored CPT passages and 89 supplied-record extraction conversations.
All are in train under the conservative source-family policy; no new validation
or test sample is claimed. Three frozen earlier packs constrain source, family
and exact-claim assignments. Measurement metadata is present in both targets and
provenance. These extraction examples are not a benchmark of independent
engineering reasoning. No new model training or weights are produced.

[Independent data-review results](review.json) record the inspection scope.
[Validation receipts](validation.json) distinguish targeted data checks from the
global repository check. The [gap register](../../../catalog/reference/m64-measurements-20261024/research-gaps.json)
lists missing original walls, datums and tolerances. Raw manuals, supplier PDFs,
reader extractions and images are not redistributed.
