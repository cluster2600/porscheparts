# Porsche air-cooled engine fans: OEM identity, variants and evidence audit

Research date: 3 October 2026. Scope: early 911, 930, 964, 993 and historical 935 racing applications. Principal target: **993 Turbo, engine M64.60, impeller 964.106.015.22**. This report concerns identity and evidence; it does not establish a production-ready rotor.

## Findings that change the model

1. **The target is distinct from Carrera and RS.** The official 993 PET lists Turbo impellers .01521/.01522, Carrera .01531 and RS .01540. A generic “964/993 fan” model is inadequately specified. [Porsche PET 993](https://files.porsche.com/f/332100/db8e7dba1c/kat017-d-911-98-katalog.pdf#page=78)
2. **The hub conflict is substantially narrowed by factory evidence.** Porsche ORIGINALE lists .05131 for 964/993 excluding RS. The 964 PET explicitly includes both Turbo engine types in the .05130/.05131 hub application. That supports OEM Turbo use, while leaving the aftermarket alternator interface unresolved. [ORIGINALE 05, PDF 7](https://a.storyblok.com/f/332100/d50d3473a6/originale-05-ww.pdf#page=7), [964 PET, PDF 95](https://files.porsche.com/f/332100/b26b3c7233/kat013-d-911-94-katalog.pdf#page=95)
3. **No primary source found proves 935/993 Turbo rotor equivalence.** A commercial “935” scan, replica flat-fan assembly, or cross-reference list cannot establish that equivalence. Retain it as an unproven hypothesis.
4. **245 mm is not yet a verified working diameter for this target.** FVD lists a 24.5 × 24.5 × 8.7 cm commercial envelope and 0.9 kg. It gives neither dimensional datums nor tolerances. These fields support an envelope claim, not an inspected blade-tip diameter or rotor-only mass. [FVD .01522](https://www.fvd.net/en-us/shop/engine-cooling-fan-alternator-impeller-965-993-turbo-993-gt2-96410601522~p252068)
5. **Airflow tables must retain model and engine speed.** They are isolated manufacturer operating points, not pressure-flow curves. Repeated forum compilations mix speeds and contain contradictory diameters.

## Evidence convention

- `manufacturer_catalog`: factory part identity/application in the cited edition
- `manufacturer_spec`: factory-published technical value, not a new measurement
- `manufacturer_history`: Porsche retrospective; valuable for architecture, weaker than the applicable period technical drawing for dimensions
- `supplier/dealer_claim`: commercial listing, even when the item is described as genuine
- `secondary_transcription`: copied technical data with original page not available
- `visual_observation_candidate`: image-based feature interpretation, requiring corroboration
- `unknown/unproven`: intentionally empty parameter

Nothing in this pass was physically measured. A replacement relationship does not prove identical geometry, identical material, original production fitment, or reverse interchangeability. All PDF page numbers below are **1-based**. PET also has a plate-local page counter; include both to avoid off-by-one errors.

## 1. Catalog hierarchy and terminology

The current official [Porsche Classic catalog index](https://www.porsche.com/germany/accessoriesandservice/classic/originalpartscatalogue/) supplies separate early-911, G-series, 964 and 993 PDFs. The inspected service-catalog snapshots are dated 24 July 2017. They are not necessarily as-built period catalogs and may incorporate replacement parts. A number's first three digits alone do not determine the car where it is used.

The 993 PET's introduction explicitly warns that illustrations are non-binding. Thus an exploded drawing is good evidence of component separation and assembly relationships, but is not a scale drawing.

Keep these entities separate in the digital twin:

| Entity | German | English/French usage | Modeling implication |
|---|---|---|---|
| Main rotating engine fan | Laufrad | impeller, fan wheel; turbine/hélice | Rotor alone or supplied rotor-and-hub must be distinguished |
| Fixed surrounding housing | Gebläsegehäuse | fan/blower housing; carter de soufflante | Includes its own flow passage and stationary features |
| Bearing hub | Radnabe/Laufradnabe | impeller hub; moyeu de turbine | Separate bearing/interface component |
| Rear extension/cone | Nabenverlängerung | hub extension | Not the main housing |
| Small rear fan | Gebläserad | auxiliary alternator fan | Separate rotor on alternator shaft |
| Split sheave | Keilriemenscheibenhälfte | pulley half; demi-poulie | Shims influence belt position/tension |
| Racing right-angle drive | fan drive | drive/renvoi d'angle | A drive scan is not a blade scan |

## 2. 993 target and adjacent variants

Primary locator: [Kat017, plate 105-00](https://files.porsche.com/f/332100/db8e7dba1c/kat017-d-911-98-katalog.pdf#page=77), diagram PDF 77; rows PDF 78–79. Core identities:

| Component | Turbo M64.60 | Carrera / RS distinctions |
|---|---|---|
| Impeller | 96410601521; 96410601522 | Carrera 96410601531; RS M64.20 96410601540 |
| Housing | 99310666750 | 99310666701; 99310666703 |
| Strap | 99310625150 | 99310601700 through 1995; 99310601701 from 1996 |
| Fan pulley | 99310650950 inner; 99310651050 outer | 96410651102 |
| Alternator pulley | 99310626800; 99310626801 | Engine-specific Carrera variants |
| Common hub | 96410605130; 96410605131 | RS 99310605180 |
| Rear extension | 93060304101 | Distinct from housing |
| Auxiliary fan | 92860304501 | Distinct from main impeller |

The Turbo fan-belt row is 99919234350, 9.5 × 760 mm, position 13. Position 14 lists Turbo 99919237350, 9.5 × 753 mm (technical information 7/97), and 99919237250, 9.5 × 757 mm. Read the relevant technical information before selecting between these alternator-drive belts. Do not treat all listed belts as interchangeable.

The Carrera .01531 and RS .01540 rows explicitly say they include position 25. The Turbo row does not give that same inclusion annotation. Therefore a commercial impeller package's hub content should be checked, even where a hub is valid for the application.

### ORIGINALE 05 verification

The small Porsche parts brochure's **PDF 7 / footer 201905P83** directly identifies .01522 for 964 Turbo 3.6 (1993–94) and 993 Turbo (1995–98); .01531 for 964/993 Carrera; and .05131 for both generations except RS. It illustrates the two rotor families separately. PDF 37 / footer 201905P113 repeats the 993 fitments. The English full filestore URL returned 404, but the Storyblok-hosted copy was downloaded and visually inspected. German, Italian and Spanish search-index copies corroborate the part labels; translated copies remain the same source, not independent tests. [Verified English copy](https://a.storyblok.com/f/332100/d50d3473a6/originale-05-ww.pdf#page=7)

### Replacement evidence, with limits

- .01521 → .01522 is explicitly reported by [Design911](https://www.design911.co.uk/p/alternator-fan---impeller-porsche-964tt---993tt/)
- A dealership-network catalog additionally lists 93010601500, 96410601320 and 96410601520 as replaced by .01522. This is a useful service-replacement lead, not a verified chronological design history. [Replacement list](https://porsche.oempartsonline.com/oem-parts/porsche-fan-blade-96410601522)
- 99310666750 → 99310666752 is reported by the same catalog network. Record the original housing and replacement housing separately. [Housing replacement](https://porsche.oempartsonline.com/oem-parts/porsche-fan-shroud-99310666752)
- Patrick Motorsports explicitly excludes Turbo for .01531, includes its hub, and says it replaces .01502. [Carrera listing](https://patrickmotorsports.com/products/eng96410601531)
- Centre Service Porsche Poitiers lists .01502, .01530 and .05100 among alternatives for .01531, but does not establish their sequence. Its listed 0.948 kg is a commercial mass for Carrera, not a Turbo mass. [French dealer page](https://www.boutiqueporschepoitiers.fr/produit/96410601531-turbine-de-refroidissement-moteur-porsche/)

## 3. 964 factory distinctions

[Kat013 plate 105-00, PDF 94–95](https://files.porsche.com/f/332100/b26b3c7233/kat013-d-911-94-katalog.pdf#page=94) identifies these families:

- Carrera M64.01: .01502 through 1992; Carrera M64.01/02: .01531
- RS M64.03: .01575 through 1992, .01540 from 1993
- Turbo 3.3 M30.69: 93010601500
- Turbo 3.6 M64.50: 96410601521 and 96410601522
- Carrera housing: 96410666702/.03; Turbo housing: 93010600608
- Turbo pulley: 93010612402; pulley halves 93010650900/.01 and 93010651000/.01
- Turbo belt at position 13A: 99919234550, 9.5 × 785 mm
- Hubs .05130/.05131 explicitly apply to M30.69 and M64.01/02/50; RS has 99310605180

This factory hub application is more probative than a reseller's broad exclusion or title. It does not resolve an altered shaft, spacer stack, bearing fit or PMB 240 A assembly.

## 4. Early 911 / 930 service-part chronology

These are selected core rows, not an assertion that every year/market had one universal fan. Exact engine restrictions and blank obsolete rows matter.

| Catalog and locator | Selected identities and restrictions |
|---|---|
| [1965–69 Kat073 PDF105–106](https://files.porsche.com/f/332100/f4448d92ea/kat073-d-911-69-katalog.pdf#page=105) | Rotor 90110601003; housing 90110610103 for early restriction, 90110601100 after engine split; pulley 90160342101; belt 99919217650/5A, 9.5 × 710 |
| [1970–73 Kat074 PDF104–105](https://files.porsche.com/f/332100/0862752924/kat074-d-911-73-katalog.pdf#page=104) | Rotor 90110601003; housing 90110601100; pulley 90160342101; extension 91110603300 |
| [1974–77 Kat092 PDF68–69](https://files.porsche.com/f/332100/185c901bfe/kat092-d-911-77-katalog.pdf#page=68) | Rotors 90110601003 and 91110602800 assigned by engine code; housing 91110600800 for listed 911/911S/Carrera3.0; 9.5 × 710 and 9.5 × 725 belt applications differ |
| [1975–77 Turbo Kat093 PDF54](https://files.porsche.com/f/332100/b93eb5fdf0/kat093-d-911-77-katalog.pdf#page=54) | Housing 91110600800; rotors 93010601200/.01; pulley 93010620902; belt 99919209750, 9.5 × 725 from 1976 |
| [1978–83 Kat002 PDF95](https://files.porsche.com/f/332100/11e2e74cae/kat002-d-911-83-katalog.pdf#page=95) | Early SC rotor 93010601101/housing 93010600500; transition at engine 6399201→6399202 and 6393868→6393869; later housing 93010600600 and rotor 93010601200/.01; .01200/.01 also listed for Turbo |
| [1984–86 Kat007 PDF81](https://files.porsche.com/f/332100/a9d1b7c9ce/kat007-d-911-86-katalog.pdf#page=81) | Rotor 93010601200/.01; Carrera housing 93010600607, Turbo 93010600606; pulley 93010620902; extension 91110605501 |
| [1987–89 Kat012 PDF81](https://files.porsche.com/f/332100/c6c38b1d99/kat012-d-911-89-katalog.pdf#page=81) | Same selected rotor/pulley/extension family; Carrera housing .00607 versus Turbo .00606; belts .17650/.1765A and .3135A appear separately |

The 226/245 mm and 5/11-blade historical story is widely reproduced, but the inspected PET text does not provide those dimensions or blade counts. Do not upgrade that story to a measured CAD dataset. The separate technical manual evidence below is stronger for drive ratios and stated air delivery.

## 5. Verified factory technical values

| Application | Fan/crank speed | Air delivery | Engine speed | Primary locator |
|---|---:|---:|---:|---|
| 1972 911 T | approx 1.3 | approx 1230 L/s | 5800 rpm | [1971 workshop manual PDF12](https://pca-chicago.org/wp-content/uploads/2024/02/911ServiceManual-1971.pdf#page=12) |
| 1972 911 E/S | approx 1.3 | approx 1380 L/s | 6500 rpm | Same page |
| 1976 / 1977 911 S | 1.8 | 1265 L/s | 6000 rpm | [Factory engine manual PDF44/46](https://data.club911.net/divers/32tech/moteur.pdf#page=44) |
| 1978 911 SC | approx 1.8 | 1380 L/s | 6000 rpm | Same compilation PDF48 |
| 1980 / 1981 911 SC | approx 1.68 | 1500 L/s | 6000 rpm | Same compilation PDF50/52 |
| 964 Carrera | 1.6 | 1010 L/s | Not specified in the cited table | [P10-L printed28 / PDF32](https://data.club911.net/divers/964tech/964doc.pdf#page=32) |

P10-L printed22/PDF26 additionally specifies **12 rotor blades, 17 housing guide vanes and magnesium housing** for the 964 Carrera. It explains a separate auxiliary fan on the alternator shaft. Tiptronic's **2.23→2.68** change concerns alternator speed; it is not a change of fan ratio. Housing material must not be silently applied to the Turbo impeller. [Porsche training manual](https://data.club911.net/divers/964tech/964doc.pdf#page=26)

For 993 Turbo, [Elferclassic's German transcription](https://www.elferclassic.de/technik/techdaten/993-turbo-95-98-techdat.php) gives 1:1.8 and 1210 L/s **at 5750 engine rpm** for 1997–98. The live host returned 502, while search-index text exposed the table. Several forums instead attach 6100 rpm. The original applicable factory specification booklet remains required before using this as a trusted validation point.

No pressure-rise, installed system resistance, air density, temperature, fan power curve, uncertainty, or test-rig definition was found with these points. Comparisons at different speed and resistance are not fan-efficiency comparisons.

## 6. 935: architecture and naming hazards

**A complete flat-fan assembly is not the same object as a 993 Turbo impeller.** Period racing variants, subsequent customer developments, and modern replicas must be registered separately. Avoid a single `935_fan` entity that merges them.

Porsche's retrospective explicitly confirms that the **935/78 Moby Dick** combines air-cooled cylinders with water-cooled four-valve heads. Consequently its cooling duties differ materially from an all-air-cooled road engine. This alone prevents direct airflow equivalence assumptions. [Porsche Heritage Moments](https://newsroom.porsche.com/en/2026/history/porsche-heritage-moments-935-norbert-singer-timo-bernhard-42018.html)

A second trap is **engine type versus vehicle type**. Porsche's Group C press kit, PDF19–21, describes a **956 engine designated Type 935/76** and a nine-blade carbon-laminate fan in its engine discussion. It does not identify the fan of the 1976 vehicle commonly called 935/76. The same document distinguishes later 956/962 water-cooling evolutions. [Official Group C document](https://newsroom.porsche.com/dam/jcr:c4c877c6-2d0f-4f71-a7ba-8f6d97fdb490/40%20Jahre%20Gruppe%20C.pdf#page=19)

### Commercial evidence that must remain commercial

- Design911 sells **93510610300R/1**, a flat-fan inlet funnel with rotor, describing a GRP funnel and aluminum blades. Its generic related-number list includes 93010601200/.01. It does not establish factory 935 revision provenance, nor cross-reference .01522. The suffix and replica context must be preserved. [Product](https://www.design911.co.uk/p/fan-housing-with-fan-blades-porsche-935/)
- Jim Torres Racing describes an aluminum reproduction intended to interchange with factory flat-fan components. That is first-party evidence of its reproduction design claim, not a material certificate for every period Porsche unit. [Reproduction maker](https://jimtorresracing.com/for-sale/reproduction-flat-fan)
- Wolfe Classics lists **935 Fan**, **Fan Housing**, **Air Guide**, and **Fan Drive** as separate scan products. A drive scan does not deliver blade geometry. Neither a product title nor a thumbnail proves the donor year, OEM part, dimensional uncertainty, completeness, coordinate system, or redistribution licence. No purchase was made in this pass. [Scan inventory](https://www.wolfeclassics.com/shop)
- AASE lists 935/78 and 935/79 operating instructions/parts catalogs, which are promising next primary sources. Their contents were not available in the inspected listings. No purchase or outreach was made. [Literature inventory](https://www.aasesales.com/collections/race-cars)

**Unresolved:** exact period rotor, gearbox, funnel and hub numbers for 935/76, /77, Baby, Moby Dick, customer /78-/79 and Kremer variants; rotor diameters, direction, ratios, material grades and mass for each. These are not safely transferable between variants.

## 7. Conflicts and rejected shortcuts

1. **Diameter:** 245 mm commercial envelope versus 279.4 mm forum table. Neither supplies target-specific inspection. Preserve source values as claims and leave authoritative blade-tip diameter empty.
2. **Airflow speed:** 5750 versus 6100 engine rpm for the commonly repeated 1210 L/s Turbo figure.
3. **Hub:** factory application supports Turbo .05131; a reseller exclusion is weaker. Aftermarket 240 A compatibility remains a different question.
4. **Catalog images:** PET's common schematic may illustrate Carrera while sharing a callout with Turbo. Do not count blades on the generic plate to identify Turbo.
5. **Material:** a magnesium housing statement does not establish a magnesium rotor, and a modern aluminum replica does not establish the original alloy.
6. **Cast versus service number:** raised casting identifiers may differ from orderable assembly numbers; record both from the actual specimen, never silently replace one with the other.
7. **Circular sourcing:** the existing porschefanatics project is search-indexed and reproduces its earlier 245 mm inference and reconstructed features. It was excluded as independent evidence. Repetition through search results cannot validate the existing model.
8. **Rotation:** “clockwise” without a specified observer is ambiguous. No unambiguous target-specific factory direction statement was established here; leave it unknown pending an authenticated view/drawing or safe specimen observation.

## 8. Next evidence needed, in priority order

1. Obtain the exact .01522 specimen identification, manufacturing/casting marks, donor engine and whether its bearing hub is included.
2. Measure blade-tip diameter, full axial envelope, hub interfaces, bore/bearing fits, bolt-circle and index, cup depth, openings, ribs, thickness distribution, radial/axial runout and clearance to the matching housing. Record instruments and uncertainty.
3. Obtain the original 993 Turbo technical specification page and technical information **7/97**; resolve the belt/pulley revision before freezing drive speed or interfaces.
4. Acquire or inspect the applicable original 935 parts/operating catalog for the particular donor being compared. Ask a scan supplier for donor identification, included components, dimensional accuracy and permitted public derivatives before relying on its mesh.
5. Obtain material identification, alloy/heat-treatment data, balancing requirement and fatigue/overspeed evidence for the intended manufacturing route. Catalog identity does not qualify an additively manufactured replacement.

## Search coverage and reproducibility

Searched German (`Laufrad`, `Gebläsegehäuse`, `Lüfterrad`, `Kühlgebläse`, `Übersetzung`, `Ersatzteilkatalog`), English (impeller, fan, flat fan, factory manuals, parts catalogs), French (turbine, hélice, moyeu, ventilateur, diamètre, catalogue de pièces), Italian (girante, ventola, ricambi) and a Japanese part-number/cooling-fan query. English/German yielded the usable factory documents; French dealer evidence helped terminology and commercial mass. Italian/Spanish ORIGINALE editions corroborated labels. Japanese results largely concerned oil-cooler fans or general repair, not target rotor geometry. Scale-model instructions, hobby meshes, generic parts SEO and unsourced forum numerics were not used as manufacturing geometry.

Outputs accompanying this report:
- `sources.json`: 32 source records, source class, language, exact locator and caveats
- `oem_parameters.csv`: 114 application, parameter and replacement-claim rows
- `oem_research.json`: combined machine-readable version

The downloaded PDFs, extracted texts, page images and checksum file are **private research working copies**, not licensed public GitHub assets. Publish original analysis, short factual records and source links; do not automatically commit full manuals, commercial scans or manufacturer illustrations.
