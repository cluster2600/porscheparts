# Deeper M64/60 dimensional evidence

Reviewed on 24 October 2026. This supplement adds 49 records, of which 40 are
retained and nine remain excluded. It links 20 canonical sources, including
17 new source records. The retained set includes one quarantined supplier-angle
anomaly and one documentary applicability record. No physical part was measured.

The [factual register](../../../catalog/reference/m64-dimensions-deep-20261024/facts.json)
and [CSV export](../../../catalog/reference/m64-dimensions-deep-20261024/facts.csv)
preserve product identity, source edition, datum, conditions, tolerance and
qualifications. The [crosswalk](../../../catalog/reference/m64-dimensions-deep-20261024/source-crosswalk.json)
distinguishes original PDFs/HTML, public photographs, web-reader responses and
frozen source-record JSON used only for historical comparisons.

## Standard-replacement piston and cylinder

The [MAHLE 2025 piston/cylinder catalogue](https://www.mahle-aftermarket.com/media/homepage/facelift/media-center/product-catalogs/mahle_piston_cylinders_assemblies_2025.pdf)
explicitly lists M64.60 in entry 51, PDF p.1334 / printed p.1332. It identifies
piston 5043600 / production number 100P46, pin 23 × 54, cylinder 503WR4400 and
assembly 5043690. This supplies a specific standard-replacement application;
it does not certify identity with every original Porsche production revision.

| Product and maker datum | Published nominal value |
|---|---:|
| Piston KH, compression height | 31.80 mm |
| Piston ÜH, dome height | 9.50 mm |
| Piston AA, distance between bosses | 21.80 mm |
| Piston F, top-land width | 6.10 mm |
| Piston GL, total length | 63.30 mm |
| Pin outside diameter × total length | 23 × 54 mm |
| Cylinder A, register diameter | 107.00 mm |
| Cylinder C, collar diameter | 115.00 mm |
| Cylinder H, maker's collar-height datum | 77.27 mm |
| Cylinder L, total height | 114.50 mm |

The actually inspected legends are PDF p.37 / printed 35 for pistons and
PDF p.42 / printed 40 for cylinders. H runs from the upper sealing face to the
illustrated lower shoulder where the register begins. It is not collar material
thickness. F is the top-land dimension; ÜH is dome height. Neither establishes
piston crown-wall thickness. The schematic does not provide a wall map,
manufacturing tolerances or a complete surface model.

Compression height 31.8 and total cylinder height 114.5 appeared previously for
different aftermarket products. The new evidence establishes the named
standard-replacement SKUs and their datum definitions; those repeated numerical
values are not claimed as newly discovered numbers. The larger register and
collar dimensions likewise do not establish an installed housing fit or measured
original cylinder-wall thickness.

## Exhaust-valve evidence and an explicit old discrepancy

The [SM VM18 maker catalogue](https://media.sm-original-germany.com/wp-content/uploads/2026/09/VM18.pdf)
lists M64.60/M64.60R/M64.60RS under entry63, PDF p.1649 / printed1617.
Its OE cross-reference, PDF p.2488 / printed2456, maps 993.105.419.52 to
SM 864452-6. The named replacement product is declared as:

| Quantity | Published nominal value |
|---|---:|
| Valve-head diameter | 42.50 mm |
| Nominal stem diameter | 8.00 mm |
| Overall length | 108.90 mm |

The frozen earlier ENGINE-D126 record contained a 43.5 mm retail declaration
attributed to SM/partworks. That older record did not establish identity with
SM 864452-6. New record M64-DEEP-V001 explicitly retains both declarations,
their separate source IDs and the frozen comparison-file hash. It does not
overwrite the old pack or choose a universal as-built Porsche diameter.

The same VM18 row literally prints 25° in a column whose legend identifies
valve-seat angle. That entry is retained only as an uncertainty example,
pending independent corroboration. It is not used as a Porsche seat-machining
specification or confused with the valve-axis angle.

For inlet valves, SM 854429-6 declares 49.1 mm while the earlier FVD 99310540902EQ1
listing declares 49 mm. The precise products remain separate; rounding is only
an unverified possible explanation. Additional Schrick oversize valves and
SI993-family guides retain their aftermarket/Carrera comparison scope.
Their nominal stem/bore sizes do not establish running clearances or Turbo fit.

## A model-specific factory checking procedure

A [public reproduction of the factory dial-gauge procedure](https://workshop-manuals.com/porsche/911_turbo_awd/f6-3600cc_3.6l_sohc_twin_turbo/engine_cooling_and_exhaust/engine/camshaft_lifters_and_push_rods/camshaft_engine/component_information/adjustments/camshaft_timing_adjustment_using_locking_devices/page_654/)
explicitly identifies an early-production engine-number window. The register
keeps that restriction by its precise page locator rather than copying serial
strings into the repository. It does not apply the procedure to all M64/60s.

The readable procedure supplies a 1.01 ± 0.04 mm inlet-valve lift at overlap TDC,
temporary 0.10 mm mechanical inlet lash and approximately 10 mm dial-indicator
preload. It describes temporary adjustable rockers and auxiliary mechanical
chain tensioning. These are checking conditions, not peak valve lift or a full
cam profile. The source's unconventional event-angle text remains excluded
pending actual image inspection; no angle convention is repaired by guessing.

The reproduction's model heading is insufficient on its own: some other pages
under that heading contain Carrera or later four-valve material. Only internally
identified procedures are retained. A dated Porsche bulletin adds an explicit
Turbo/Turbo S documentary applicability link for a lifter-measurement chapter;
this alone does not validate every older Carrera numerical limit for the Turbo.

Exact Turbo repair literature is now distinguished from introductory literature:
WKD 483220 is the Turbo repair guide and WKD 483221 its addendum; German
Service Information Technik WKD 409410 and English WKD 409421 are introductory
documents. Full unread books create no technical targets. Acquisition routes and
inspection limitations are recorded in the gap register.

## Precisely labelled historical comparisons

The [official 959 PET](https://files.porsche.com/f/332100/ba5c0db064/kat010-e-959-88-katalog.pdf)
adds 959.50 road-engine replacement-part dimensions, including 0.25 mm valve-seat
oversizes and 0.5 / 1.0 / 1.5 mm spring-seat washer options. Repair increments are not
absolute counterbore diameters. Some seal sizes repeat known numbers but supply
a new 959-specific application; no 993 interchangeability is inferred.

Actual public photographs of Porsche customer935 operating instructions supply
two separate factory baselines:

| Customer instruction document | Engine type | Bore | Stroke | Printed displacement |
|---|---|---:|---:|---:|
| Model 1978 | 930/78 | 95 mm | 70.4 mm | 2994 cm³ |
| Model 1979 | 930/79 | 97 mm | 70.4 mm | 3121.45 cm³ |

The customer 1978 document is not the works 3.2 L water-head 935/78 Moby Dick.
The published displacement values are preserved as declarations, rather than
replaced with calculations. The crosswalk identifies the actual photographed
pages and hashes, and makes clear that complete manuals were not acquired.

The historical [MAHLE 2022 guide](https://www.epartrade.com/uploads/contents/d5e1e74b-6411-11e8-be4b-560001755c9c/2021/11/2022-porsche-ap-guide-.pdf)
also records a separate PP102-012 aftermarket configuration: 4032 alloy, 437 g
listed mass, 9.7 cm³ crown volume and 8.1 calculated compression ratio.
It is a different exact identifier/edition from PP102-012N in the earlier
2024 register. Missing clearance-column units remain unresolved; no conversion
or manufacturing clearance is accepted from those unlabeled fields.

Protomotive's own 993 K16/K24 outlet fabrication flange declares a 0.5 inch
stock thickness, with the exact 12.7 mm unit conversion labelled as such. It
does not provide a complete bolt pattern or establish original housing/flange
thickness. Those interfaces remain acquisition gaps.

## Data preparation and acceptance boundary

Requirement REQ-M64-DEEP-20261024 adds attributable dimensional inputs and
preserves conflicting historical product declarations. It supports B-VERIFY in
the [engineering architecture](../../architecture/README.md), follows the
[capture protocol](../../CAPTURE_PROTOCOL.md) and existing
[ADR0012](../../decisions/0012-local-compute-gpu-last.md). No part geometry,
manufacturing approval or release evidence is created by this increment.

The [separate training pack](../../../training/m64-dimensions-deep-20261024/README.md)
contains 40 authored CPT passages and 40 supplied-record extraction examples.
All are train under the conservative publisher-family policy; no new validation
or test sample is claimed. Four earlier packs and their holdouts remain frozen.
Full measurement and discrepancy metadata appear in targets and provenance.
This is data preparation, not a new training run or reasoning benchmark.

See [independent review](review.json), [validation receipts](validation.json)
and [remaining gaps](../../../catalog/reference/m64-dimensions-deep-20261024/research-gaps.json).
Original wall thicknesses, complete port coordinates and exact K16 patterns are
still missing. Raw manuals, rendered images, seller photos and web-reader
responses remain outside the repository.
