# German-source Mezger turbo and materials supplement

Reviewed on 3 October 2026. This supplement adds 108 attributed records and 27
source records to the [earlier materials review](../mezger-turbo-materials-20261003/README.md).
Twenty-five sources are German, one Porsche sheet is bilingual German/English,
and one English MAMBATEK product was discovered through German queries. Twenty-four
sources support factual records; three journal landing pages supply bibliography
only because their full articles were not acquired. Translated Porsche articles
are the same publisher's evidence, not independent corroboration.

The project application remains the 993 Turbo M64/60, original K16 housings to be
converted to hybrids, with a target above 550 metric horsepower at the crankshaft.
This research supplies component and documentary data; no compressor match,
manufacturing drawing or achieved engine output is established by this increment.

The [factual register](../../../catalog/reference/mezger-german-sources-20261003/facts.json)
preserves exact applications, component names, units, document locators and
qualifications. The [source crosswalk](../../../catalog/reference/mezger-german-sources-20261003/source-crosswalk.json)
records language, edition, public URL and captured-response SHA-256. The
[training increment](../../../training/mezger-german-sources-20261003/README.md)
is separate from both frozen earlier packs.

## Precise aftermarket K16 wheel data

The [MAMBATEK 015-2218-2 supplier page](https://www.mambatek.com/en/products/heavy-duty-porsche-993-k16-67356736-twin-turbo-cw-tw-repair-kit-2p)
names M64.60 and K16 donors 5316-970/988-6735 and -6736. Its English page was found
through German search terms. These are supplier declarations for one aftermarket
kit, not measurements or material certificates for the original Porsche wheels.

| Component | Published declaration | Register |
|---|---|---|
| Compressor | 2618 aluminium billet; 6+6 blades | MEZGER-DE-T002, T004 |
| Compressor diameters | 40.5 mm inducer, 60.5 mm exducer, 64.18 mm extended-tip outside diameter | MEZGER-DE-T003 |
| Turbine | Inconel 713C; nine blades | MEZGER-DE-T005, T007 |
| Turbine diameters | 49 mm exducer, 55 mm inducer | MEZGER-DE-T006 |
| Thrust bearing | Three oil holes | MEZGER-DE-T008 |
| Balancing | Individually balanced wheels; assembled CHRA balancing recommended by supplier | MEZGER-DE-T009 |

The listing's “94–07” vehicle-year range is inconsistent with the 993 generation.
It must not become a production-date or fitment assertion. No compressor map,
efficiency contours, surge/choke limits, certified shaft-speed limit or verified
550 PS engine result is supplied.

German [TTE24](https://www.tte24.net/product_info.php?products_id=1430) describes
high-strength aluminium and a 49.5 mm machined compressor-housing inlet. This is a
housing datum; the earlier TTE manufacturer wheel-inlet figure uses a different
datum. Neither wording establishes an alloy grade or manufacturing tolerance.
German [TurboZentrum process information](https://www.turbozentrum.de/OST-Details-Stage2)
describes compressor wheels milled from forged aluminium and five-axis housing
machining. Its separate 993 Stage 2 offer uses a K24-family donor, and its
advertised 750 PS output is based on customer feedback. It does not validate a
K16 hybrid for the project target.

## RR350 chemistry and processing, with grade scope

The [German Rheinfelden safety sheet](https://rheinfelden-alloys.eu/wp-content/uploads/2015/08/Alufont-60_RR350_AlCu5NiCoSbZr_DE_V2.pdf)
identifies RR350, Alufont-60 and AlCu5NiCoSbZr as supplier names. The actual
[2015 processing basis data](https://rheinfelden-alloys.eu/wp-content/uploads/2016/01/Verarbeitungsbasisdaten_RHEINFELDEN-ALLOYS_2015_DE.pdf),
PDF p.2, supplies composition ranges and maxima. These qualify a general grade;
they do not certify the chemistry of an Xtreme casting or identify an original
Porsche M64/60 head alloy.

| Element | Published mass percentage |
|---|---:|
| Cu | 4.5–5.2 |
| Ni | 1.3–1.7 |
| Co | 0.10–0.40 |
| Ti | 0.15–0.30 |
| Mn | 0.1–0.3 |
| Si | maximum 0.20 |
| Fe | maximum 0.30 |
| Mg | maximum 0.10 |
| Zn | maximum 0.10 |
| Zr & Sb | source prints a joint 0.10–0.30 entry; individual or combined interpretation is unresolved |

The same document's p.4 lists a generic T7 cycle: solution treatment at
535–545 °C for 10–15 h, water quench at 80 °C, then ageing at 210–220 °C for
12–16 h. T7 is the overaged condition. The AlCu solution-treatment guidance has
a wall-thickness applicability threshold of 8 mm. That is a process-table
qualification, not a measured Porsche or Xtreme wall thickness. The document
does not establish a particular component's casting route, actual heat cycle,
porosity, fatigue performance or accepted service load.

The [German Alufont product information](https://rheinfelden-alloys.eu/legierungen/alufont/)
also gives sand-cast T7 strength, elongation and hardness. The register preserves
the published ranges and parenthetical values; it does not convert them into
guaranteed material allowables for a cylinder-head design.

## 2618A and cylinder-surface definitions

The [German Smiths 2618A sheet](https://www.smithshp.com/de/assets/pdf/aluminium/hochleistungsaluminium/2618a-aluminium-deutsch.pdf)
provides Cu 1.8–2.7%, Mg 1.2–1.8%, Ni 0.8–1.4% and Fe 0.9–1.4% by mass,
plus maximum limits for other elements. Its T6 bar/section mechanical minima
depend on stock dimensions. For stock up to 10 mm the sheet lists 320 MPa proof
stress and 400 MPa tensile strength; above 10 mm through 100 mm it lists 340 MPa
and 420 MPa respectively. These are stock-product data. A supplier naming
“2618” for a wheel or piston does not establish Smiths 2618A chemistry, this
stock condition or these mechanical minima for that finished part.

The [German Motorservice aluminium-block overhaul guide](https://www.ms-motorservice.com/MediaAssets/51703_ks_50003804-01_web.pdf),
first edition August 2006, distinguishes several surface technologies:

| Quantity | Published general-process value | Scope |
|---|---|---|
| Nickel–SiC coating thickness | Average 10–50 µm | p.26, section 2.4.5; measurement stage is not defined as finished post-honing |
| SiC volume fraction in that coating | 7–10% | Same historical generic process |
| ALUSIL alloy example | AlSi17Cu4Mg, nominal 17% silicon by mass | p.22; not a 993 Turbo Nikasil cylinder identification |
| Primary silicon-crystal size | 20–70 µm | Bulk hypereutectic ALUSIL crystals, distinct from coating SiC particles |
| Local aluminium recession | 0.3–0.7 µm | MAHLE silicon-exposure machining example; not a coating or cylinder wall |

The recession definition comes from [MAHLE's German 2021 cylinder-machining guide](https://www.mahle-aftermarket.com/media/homepage/facelift/media-center/workshop/honbroschur_2021/de_mahle_honbroschur_2021_ansicht_final.pdf).
The earlier LN NSC figure of 101.6–127 µm per side explicitly describes its
finished post-honing process. It remains a separate supplier/process statement;
these ranges must not be averaged or used as competing measurements of an
original M64/60 cylinder.

[Motorservice SI 1199](https://www.ms-motorservice.com/MediaAssets/alusil-buchsenrohlinge-fuer-die-reparatur-von-aluminium-motorbloecken_56963.pdf)
also warns that its ALUSIL repair blanks require a compatible piston running
surface. Its warning about uncoated pistons used with nickel-plated bores is
retained with the exact repair-product scope, rather than turned into a complete
Porsche piston interchangeability specification.

## Magnesium and factory manufacturing evidence

The [German Porsche Classic crankcase article](https://newsroom.porsche.com/de/2023/produkte/porsche-classic-neue-magnesium-kurbelgehaeuse-fuer-fruehe-porsche-911-31497.html)
describes new replacement magnesium cases for 1968–1976 early 911 engines of
2.0, 2.2, 2.4 and 2.7 litres. It gives sand casting, five-axis CNC machining,
more than 50 tools and more than 1,300 control dimensions. An example 3–4 mm
material removal concerns machining allowance, not finished wall thickness.
It describes multi-week dynamometer validation of a Carrera RS 2.7 prototype.
None of these statements identifies the 993 Turbo's crankcase as magnesium.

The same article explains that reproduction machining data for unspecified
larger-displacement 1990s aluminium crankcases benefited from the Porsche 962
Group C engine reproduction project. It does not name a precise M64/60 casting
grade, revision or machining drawing. Its early magnesium production route must
not be transferred to those aluminium cases by analogy.

## Racing and later engines

German factory texts sharpen the comparison without transferring their hardware
to the 993 Turbo:

| Exact application | Additional documented precision |
|---|---|
| 959 road cutaway engine | Block explicitly cast from aluminium alloy; exact grade remains unspecified |
| 935/78 | Air-cooled cylinders and water-cooled heads, four valves per cylinder |
| Initial 1995 993 GT2 racing version | 3.6 L and 450 PS |
| Final GT2 Evo development stages | 3.8 L and up to 515 kW / 700 PS |
| 1993 Turbo S Le Mans GT | 3.16 L biturbo, 353 kW / 480 PS with restrictors |
| 1996 GT1 competition engine | 3.2 L, fully water-cooled, 441 kW / 600 PS; distinct from the earlier GT1-98 museum example |
| 1994 Dauer 962 Le Mans GT | 3.0 L and 500 kW / 680 PS with restrictors |

Sources are the [German motorsport press kit](https://newsroom.porsche.com/de/pressemappen/50-Jahre-Porsche-Turbo-36122/Die-Anf%C3%A4nge-und-die-Turbo-Technologie-im-Motorsport.html),
[935 engineering retrospective](https://newsroom.porsche.com/de/2026/historie/porsche-heritage-moments-935-norbert-singer-timo-bernhard-42017.html)
and [959 cutaway article](https://newsroom.porsche.com/de/historie/porsche-geschichte-959-iaa-schnittmodell-12381.html).
The 935 Baby's approximately 5,000 rpm response transition is a reported driving
impression, not a rated engine-speed or turbo-speed limit.

The German RUF TRIBUTE page describes a new 3.6 L engine with aluminium block
and heads, four camshafts and three-valve heads. It is separately scoped; it
does not establish historic CTR2 or M64/60 internals. The retrospectively labelled
“overboost” torque entries for 964/993 in Porsche Klassik are recorded as
unresolved attribution. They are not proof of overboost hardware on those cars.

## Documentary gaps and training hand-off

Exact original M64/60 alloy grades, component heat states and wall/crown
thicknesses remain unestablished. The [gap register](../../../catalog/reference/mezger-german-sources-20261003/research-gaps.json)
records unsuccessful routes without inventing missing values. The public
German abstracts identify especially relevant engineering papers:

- Beer, Held, Kerkau and Rehr, *Der neue Motor des Porsche 911 Turbo*, MTZ 61,
  pp.730–743, November 2000, [DOI 10.1007/BF03227310](https://doi.org/10.1007/BF03227310).
- Schmitt and colleagues, *Der neue Porsche 911 Turbo*, ATZ 102, part 1,
  pp.914–923, November 2000, [DOI 10.1007/BF03224321](https://doi.org/10.1007/BF03224321);
  part 2, pp.1058–1068, December 2000,
  [DOI 10.1007/BF03224336](https://doi.org/10.1007/BF03224336).

Only abstracts and bibliographic metadata were reviewed. Their unread full
texts create no technical training targets. A cited 1993 Carrera engine article
is a further documentary lead, with Carrera scope retained.

Training uses authored English records and grounded extraction conversations.
Both earlier packs' source, source-family and exact-claim partitions constrain
the new data, including German retailer mirrors of previously held-out products.
Common alloy concepts can recur across distinct products; this is not a test of
independent engineering reasoning. No new training run or weights are produced.
Raw manuals, supplier PDFs, scans and website passages are not redistributed.
Check receipts and any environment limitation appear in [validation.json](validation.json).
