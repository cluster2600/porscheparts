# Porsche 911 / 935 cooling fans: aftermarket and supplier evidence

Research snapshot: 3 October 2026 UTC. This is supplier research for a digital twin, not a fitment sign-off or authorization to manufacture, install, or run a fan. No vendor was contacted and no purchase was made.

## Main findings

1. The available market is more diverse than an OEM-magnesium-versus-billet choice: EPS sells a cast-aluminum 11-blade rotor with a forged steel hub; INDEX sells CFRP rotors and housings; Carpoint lists magnesium RSR components alongside a separate cast-aluminum housing; LN Engineering and Rennline sell billet housings. None of the reviewed retail pages supplied a complete pressure-flow-power map or a traceable burst/fatigue qualification report.
2. The strongest immediately usable geometric evidence is a Carpoint installation sheet, with explicit spacer dimensions and some alternator/fan dimensions. Its datums and exact fan part associations are incomplete. It is a useful constraint source, not a substitute for measurement of the target assembly.
3. At least three actual supplier families offer complete 935-style systems: Jim Torres Racing, Spezialmotorer and Bailey Cars. FSH/TK/Design911 inlet-and-rotor products are partial assemblies and must not be counted as complete drive conversions.
4. EB Motorsport's 2015 development report contains two quantitative absorbed-power points. Their original test setup and rotor must remain attached to those numbers. Gunther Werks' current greater-than-twofold air-volume claim has no published operating point.
5. Alternator choice changes drive requirements. Classic Retrofit recommends a serpentine belt and tensioner for its 964/993 240 A unit, and its 175 A unit for conventional double-pulley or RS single-pulley arrangements. Neither is selected here.

## Evidence rules

- Manufacturer catalog facts establish what is claimed for that product, not independent measurement or certified compatibility.
- A retailer's copied product description is not another experiment. `lineage_group` in the source manifest identifies obvious shared evidence.
- Prices are page observations on the access date, exclude unlisted charges, and are not quotations. Parsed stock labels can be contradictory. No inventory was confirmed with a seller.
- Nominal diameter, supplied blank diameter, housing diameter, and actual blade-tip diameter are separate parameters. Likewise, package dimensions and shipping weights are not part geometry.
- Unless expressly identified, speed limits, balance grades, alloy temper, layup, clearances, blade profiles, hub bolt-circle datums, fatigue life and airflow boundary conditions remain unknown.

## 1. Vertical axial fan replacements

### EPS: 93010601200EPS

The maker identifies an 11-blade, 245 mm cast-aluminum rotor and a drop-forged steel hub with gold zinc plating. Its design page describes a pitch between the earlier 911 and 964 designs, marketed for 1974-89 cars. No numeric pitch or test curve accompanies the cooling and longevity claims. Crucially, this is not evidence of a fully forged rotor. [EPS product](https://www.epsauto.com/products/alternator-updated-aluminum-fan), [design description](https://www.epsauto.com/alternator-aluminum-fan)

Design911's version, 93010601200/1, adds a nominal 3.25-inch pulley and says cars with the 226 mm fan need housing 93010600600/1, crank pulley 93010202804 and belt 99919217650 as well. The retailer's year labels are internally broad; preserve the hardware dependencies instead of treating the title as universal drop-in fitment. Its prose is substantially the EPS marketing lineage, not independent validation. [Retailer compatibility](https://www.design911.co.uk/porsche/911-1965-1989/alternator-generator-fan-impellor/)

Maker price observed: USD 489. Mass, blade sections, allowable speed and balance tolerance were not recovered.

### INDEX / PORCO ROSSO: genuinely different composite variants

| Product | Catalog identifier | Supplier facts | Important unknowns |
|---|---|---|---|
| Classic 911 rotor | PR-MA030 | 911/930 through 1989 with 245 mm fan; 12 blades; approximately 430 g; A7075 machined, hard-anodized hub | Tip clearance, detailed blade geometry, laminate/resin, overspeed and balance results |
| 964/993 rotor | PR-MA010 | Approximately 400 g; single-pulley compatibility claimed; hub bearing excluded | Blade count and diameter not specified in recovered text; Carrera/Turbo scope unresolved |
| Classic housing | PR-MA040 | CFRP; 245 mm classic-911 family; shop mass approximately 1,360 g | Assembly boundary, stiffness, alternator clamping/load path |
| 964/993 housing | PR-MA020 | CFRP; shop mass approximately 1,475 g | Presentation page says 1,400 g; scope and claimed percentage saving unresolved |

The classic rotor's 12 blades are an intentional aftermarket design change. The maker mentions CFD as design support, but no mesh, turbulence treatment, rotational speed, system impedance or measured validation is public in the reviewed pages. Do not silently treat it as a replica of the 11-blade Turbo rotor. [Classic rotor shop](https://ec.index-id.jp/products/detail/4), [design page](https://index-id.jp/products/cfrp-cooling-fan-for-porsche-classic-911/)

PR-MA010's approximately 50% mass reduction does not establish which complete OEM assembly was weighed. For the housing, both pages claim a 74% reduction without defining the baseline, while disagreeing on mass. Retain those claims separately; do not compute an OEM mass from them. [964/993 rotor](https://ec.index-id.jp/products/detail/6), [housing shop](https://ec.index-id.jp/products/detail/5), [housing presentation](https://index-id.jp/products/cfrp-fan-housing-for-porsche-964-993/)

Observed pre-Japan-tax prices: PR-MA030 JPY 251,000; PR-MA010 JPY 210,000; PR-MA040 JPY 358,000; PR-MA020 JPY 360,000. Made-to-order descriptions have inconsistent two-, three-, and two-to-four-week estimates. Treat availability as made-to-order, not a delivery promise. [Classic housing shop](https://ec.index-id.jp/products/detail/29), [fitment page](https://index-id.jp/products/cfrp-fan-housing-for-porsche-classic-911/)

### partworks: 3765, an oversize rotor that needs finishing

The maker/supplier lists 11 blades, aluminum and 250 mm supplied outside diameter, cross-referencing 90110601003 / 90110601002 for 1965-77 2.0/2.2/2.4/2.7 and 914-6 applications. The page explicitly requires regrinding for 245 mm or 225 mm housings. This is not a contradictory 245 mm nominal fan measurement; it is a machining-stage distinction. No final clearance or post-machining balance acceptance is supplied. Direct product-page observation was EUR 309.98 including 19% VAT and unavailable; earlier indexed category snippets showed EUR 297.03, so the direct page takes precedence for this snapshot. [partworks 3765](https://partworks.de/Fan-wheel-for-PORSCHE-911-2-0-2-2-2-4-2-7-914-6-90110601003)

## 2. Housings and small-diameter racing systems

### Billet housings: do not transfer the material to the fan

- LN Engineering 930-106-006-07-LN is a one-piece CNC billet 6061 housing for 245 mm classic-911 applications. The page specifies a 21 mm spacer for its 114 mm alternator class, and 10 mm for its 123 mm class; thin optional shims are also listed. Price: USD 1,325. Its 10 lb and 15 x 15 x 10 inch commercial fields are not accepted as a measured housing mass or envelope. Direct page fetch returned 403; the indexed manufacturer content was readable. [LN catalog](https://lnengineering.com/ln-engineering-billet-fan-housing-ring-for-1965-89-porsche-911-930-106-006-07-ln/)
- Rennline M57 uses two machined aluminum billets, supports the 245 mm assembly, and includes 10 mm and 21 mm spacers. Price: USD 1,194. The recovered maker page does not identify alloy grade or temper; do not import 6061-T6 from an aggregator. [Rennline M57](https://www.rennline.com/billet-fan-shroud-sku-m57/)
- EPS/Vertex lists separate aluminum housings 93010600600EPS for 1974-83 and 93010600607EPS for 1984-89, both at USD 789 in the category block. These are catalog families, not proof that every alternator/fan combination in those years fits. [Vertex catalog](https://www.vertexauto.com/engine-cooling-c-7529.aspx)

### Carpoint: keep magnesium and aluminum variants separate

| Item | Stated material | Nominal diameter | Stated mass |
|---|---|---:|---:|
| COL11.1.140 RSR / 906 / 914-GT housing-and-fan set | Magnesium | 225 mm | Housing 1,365 g; fan 885 g |
| COL11.1.128 RSR / 906 housing | Cast aluminum | 225 mm | 1,850 g |
| COL11.1.128F rotor | Magnesium | 225 mm | Not specified on isolated-rotor page |

The same 90110610300 / 90110610300R reference family appears across these products; this does not make their material or mass identical. [Set](https://www.carpoint.de/en/porsche-spareparts/motorsport-parts/fan-housing-with-fan-wheel-for-porsche-rsr-906-914-gt_2201_3207), [aluminum housing](https://www.carpoint.de/en/porsche-spareparts/motorsport-parts/fan-housing-alternator-906-911-rsr-90110610300r_1015_1946), [rotor](https://www.carpoint.de/en/porsche-spareparts/motorsport-parts/fan-wheel-225mm-for-porsche-rsr-906-914-gt-fan-housing_2744_3802)

Carpoint links an undated, one-page German dimension sheet. It was downloaded and visually checked. Two differently numbered download links return byte-identical files (SHA-256 f4661b319c97f6e4fdf07f261e45da4a28ce4743641008914d0baf2da4e1e9ea), not two independent sources. It lists:

- Alternator heights: 35/55 A 82 mm; 70 A 92 mm; 90 A 104 mm
- Ring depths: 55 A 5 mm; 70 A 14 mm; 90 A 27 mm; a 55 A / C2-fan adapter case 19 mm
- Normal fan-to-ring protrusion 2 mm; this is not radial blade-tip clearance
- Spacer: outside diameter 146 mm, inside diameter 123.5 mm, thickness 12 mm, six 6.5 mm holes spaced 60 degrees apart; no bolt-circle diameter
- Blade diameters: 11-blade 244.5 mm; 12-blade 254 mm, with no exact part numbers

The document does not define the measurement datums. Its alternator heights must not be reconciled with LN's 114/123 mm length classes by arithmetic alone. It also discusses machining a mismatched alternator/ring combination, without enough context to constitute a complete machining instruction. [Carpoint sheet, page 1](https://cdn02.plentymarkets.com/ee5vntdimm3u/propertyItems/10578/Datenblatt.pdf)

TRE's small-fan housing is cast aluminum and requires its matching strap and race-version engine shroud. The page's 250 mm fan wording conflicts with its small-diameter/1978-79 SC context and with Carpoint/Mittelmotor's 225 mm family. Record the conflict; do not turn 250 mm into a CAD constraint. [TRE](https://tremotorsports.com/engine/rsr-small-fan-housing)

Mittelmotor explicitly offers a service to reduce the 245 mm wheel for a 225 mm ST/RSR ring, SKU 8,70005 neu. The page does not publish resultant airflow or mechanical validation. [Machining service](https://www.mittelmotor.de/racing/de/1-0-rennsport/68535/3676/1-01-motorteile/2-8-70005-neu-detail)

## 3. Horizontal / flat-fan systems

### Full systems currently represented by actual suppliers

Jim Torres Racing describes a cast-aluminum 935 reproduction whose components interchange with factory parts. It includes the oil distribution tree, long banjo, feed line and fittings, but excludes the alternator and engine-specific belt. Its account of two prior magnesium assembly fractures is useful firsthand experience, not a controlled material comparison or a quantified failure rate. No public dimensional drawing, speed rating or flow curve was recovered. [Torres](https://jimtorresracing.com/for-sale/reproduction-flat-fan)

Spezialmotorer describes vintage/modern replica systems originally intended for 934, 935 and IMSA 962 replacement use, with adaptability claimed for 930 3.0/3.2/3.3 cases and 3.6 engines. The catalog says up to 32 separate fan-system parts are available. Neither broad 3.6 fitment nor the phrase replica establishes stock 993 Turbo intercooler clearance. [System description](https://www.spezialmotorer.com/produkter/numquam), [parts catalog](https://www.spezialmotorer.com/products)

Bailey Cars' indexed maker page describes a mechanically driven kit for 930/964 engines. Direct opening returned a verification interstitial; the indexed text establishes an offering but not a fully verified present specification. Historic third-party claims about 10,500 rpm, carbon/Kevlar construction or 600 hp capacity were not promoted into current design parameters. [Bailey flat fan](https://baileycars.co.za/page.html)

### Inlet + rotor is not a complete conversion

FSH 230d is a first-version 935 GRP inlet and cast-aluminum rotor reproduction. Approximate listed set mass is 1.50 kg; price EUR 5,890 including 19% VAT. The seller flags race-use status and possible fitting adjustments. Stuttgear lists TK 230d, attributed to TK GFK-Technik, at 1.60 kg and EUR 5,240. Both carry GTIN 4251967365589: treat them as a likely shared product lineage, with unresolved 100 g mass discrepancy, not independently corroborated designs. [FSH](https://www.f-s-h.com/Inlet-funnel-with-fan-wheel-for-Porsche-935), [TK/Stuttgear](https://www.stuttgear.com/Inlet-funnel-with-fan-wheel-for-Porsche-935)

Design911 93510610300R/1 likewise describes a GRP inlet and aluminum blades. Its cross-reference list also includes 93010601200/01; that retailer relationship must not be read as dimensional interchangeability between an axial 911 rotor and a flat-fan assembly. [Design911 935 component](https://www.design911.co.uk/p/fan-housing-with-fan-blades-porsche-935/)

### Quantitative test evidence: EB Motorsport, 2015

John Glynn's firsthand interview with Mark Bates reports testing on an electrically driven static long block, after reverse-engineering an original 935 drive. A bought-in carbon rotor was used while EB's own tooling remained in development. Reported absorbed-power points are 1.5 hp at 4,000 fan rpm and 32 hp at 12,000 fan rpm; the latter is described as approximately 8,000 engine rpm. The report mentions airflow/diverter work but gives no numerical flow or pressure data. [Interview, testing sections](https://ferdinandmagazine.com/porsche-flat-fan-kit)

Interpretation: these two points may be retained as sparse manufacturer-reported benchmarks for that rig. They are not an OEM 935 map, a continuous 12,000 rpm limit, or a claim about the project fan. The article's exponential wording is qualitative; two measurements do not identify a governing law. Mechanical versus metric horsepower, electrical-to-shaft correction, inlet density, restrictions, instruments, uncertainty and repeatability are not disclosed. Do not fit an efficiency curve from them.

### Modern integrated program: Gunther Werks

The current Turbo and F-26 maker pages identify flat-fan cooling on bespoke 4.0-liter twin-turbo 993-derived builds. Both claim more than twice the air volume and more even six-cylinder cooling compared with a standard vertical fan. They provide neither comparator identity nor fan rpm, pressure, air density, power consumption or temperature distribution measurements. The Turbo's 7,500 rpm figure is engine redline, not fan rating. No standalone fan SKU or retrofit availability was verified. [Turbo](https://guntherwerks.com/programs/turbo/), [F-26](https://guntherwerks.com/programs/f26/)

## 4. Drive topology and alternator integration

Rothsport RS-079 is a billet-aluminum single-belt conversion hub, paired with its RS-164 fan pulley for 964/993. Its RS-155 is a classic 1976-89 fan pulley; a 126 mm RS-140 crank pulley is suggested, but the fan pulley pitch diameter is absent, so no ratio should be calculated. Parsed pages show both sold-out and add-to-cart text; inventory is unresolved. [RS-079](https://rothsport.com/products/964-993-rs-single-belt-conversion-hub), [RS-164](https://rothsport.com/products/fan-pulley-89-98-964-993), [RS-155](https://rothsport.com/products/fan-pulley-76-89-911)

Patrick Motorsports ENG 993 106 051 80 PMS / PMP36FANHUB is a 6061-T6 billet-aluminum solid hub, referencing the M64.20 RS arrangement. It supports original or stud hardware, and the maker says it can retain the factory crank pulley while eliminating one belt. This is a change in kinematic coupling, not merely lighter hardware. Turbo-specific compatibility remains unresolved here. [PMS solid hub](https://patrickmotorsports.com/collections/patrick-motorsports-parts-kits/products/eng99310605180pms)

Classic Retrofit's 964/993 product pages distinguish 175 A and 240 A mechanical-drive suitability as described above. They claim custom casings for the fan housings and Denso six-phase hairpin internals. Electrical current is not fan-shaft power: a twin needs electrical load, efficiency and ratio assumptions as separate inputs. The 240 A price was GBP 895 plus VAT with a listed 7-10-day dispatch estimate. [175 A](https://www.classicretrofit.com/en-us/products/porsche-964-993-high-output-175a-alternator-1989-1995), [240 A](https://www.classicretrofit.com/products/porsche-964-993-240a-high-output-alternator)

The maker's 993 installation note says an initial spacer compensates for an inset bearing; other spacers match the original pulley-stack height. It specifically retains the rear cone because the cone also spreads alternator-nut load. No spacer dimensions are given, and the post does not explicitly identify which current rating is pictured. [993 installation note](https://classic-retrofit.com/forum/index.php?/topic/2521-993-alternator-install/)

A different official 175 A manual describes classic 1965-89 installation. It reports 150 A continuous testing with a single pulley, recommends polyrib at the full 175 A level, and gives a 1.8 alternator/engine ratio example. That short alternator needs 10 mm spacing in 1974-83 housings and 21 mm in 1984-89 housings. Do not copy those dimensions into the distinct 964/993 assembly. [Classic-911 175 A manual, Performance and Fitment](https://classic-retrofit.com/forum/index.php?/topic/1204-175a-upgraded-alternator-installation-manual/)

## 5. Failure caveats, material routes and exclusions

- A Japanese 993 owner reports dry-carbon fan/housing contact and blade-tip fiber deterioration on 21 August 2025. The recovered post does not securely identify a brand. This is an inspection/failure-mode lead, not grounds to attribute a defect to INDEX or to all composites. [CARTUNE report](https://cartune.co.jp/notes/cHKYBihaUO)
- A fan described as balanced is missing a residual-unbalance limit, balance speed, correction method and assembled-hub definition. It cannot supply a rotor-dynamics acceptance criterion.
- For cast, billet, forged-hub or composite candidates, request evidence for the complete rotating assembly and interfaces, including thermal fit, hub torque transfer, fatigue, clearance under load, foreign-object damage, corrosion/galvanic details, inspection and overspeed containment. These are engineering validation requirements, not proven supplier deficiencies.
- Searches for additively manufactured Porsche cooling rotors did not recover a qualified, operational retail fan with dimensional and test evidence. Scale-model STL files, stationary heater ducts and research on printed cylinder blocks are different categories. Sarah Chapman's June 2023 thesis is a useful engine heat-transfer lead, not proof of a service-ready printed rotor. [Author-uploaded thesis](https://www.researchgate.net/publication/372237377_Heat_transfer_optimization_of_a_3D_printed_air-cooled_aftermarket_Porsche_engine)
- FLAT4 EG-290 is explicitly designed around VW cases of 1,300 cc and above. Its Porsche-style label and 65 A alternator must not make it a 911-compatible product. [Japanese supplier page](https://shopping.flat4.co.jp/products/detail/94)
- PorscheFanatics' 993 Turbo fan project and catalog were excluded as independent evidence because they may be derivative of the project being researched. In particular, that site's 240 A selection and inferred 245 mm diameter are not adopted as user instructions or verified OEM dimensions. [Project page](https://porschefanatics.com/projects/993-turbo-fan/)

## 6. Suggested digital-twin structure

These are research integration recommendations, not hardware choices:

1. Separate variant records for early 11-blade axial, 225/226 mm small-fan, later 245 mm axial, Carrera 964/993, Turbo 964/993, and horizontal 934/935-style systems. Supplier fitment tables must not collapse them.
2. Separate rotor, hub, bearing, fan pulley, alternator pulley, alternator body, housing, rear cone, intake funnel, stator/diverters, engine shroud and drive gear/coupling objects.
3. Store every dimensional claim with source, component boundary, datum, nominal/as-supplied/measured status and uncertainty. Missing tolerances remain null. Preserve contradictory claims as separate records.
4. Keep marketing performance in an evidence layer. Do not insert greater-than-twofold airflow or hybrid-pitch improvements as solver boundary conditions.
5. Use EB's two points only as a named historical test dataset, with unknown pressure/flow. A validation-ready map needs flow and pressure across resistance settings, shaft torque/power, rpm, density, inlet/outlet configuration and calibrated uncertainties.
6. Before target geometry is frozen, resolve alternator dimensions, bearing location, hub/pulley kinematics, cone mounting, belt plane, hot clearances and compatible shroud. A rendering that visually fits is not sufficient.

## Research coverage and limits

English, German, French, Italian and Japanese query passes were attempted. Useful unique supplier evidence was strongest in English/German and the Japanese INDEX/FLAT4 ecosystem. French/Italian results mainly returned localized supplier pages or unrelated water-cooled radiator fans; direct language links on the Design911 935 page failed in this tool. The [French EPS listing](https://www.design911.com/fr/p/porsche-911-alternator-fan---impeller-93010601200/) and [Italian partworks listing](https://partworks.de/Ventola-per-PORSCHE-911-2-0-2-2-2-4-2-7-914-6-90110601003) were recovered through search. They repeat the same product lineages. No novel French/Italian manufacturer test curve was recovered. Supplier statements hosted on official support forums were included as manufacturer instructions; general forum archaeology remained outside this lane.

Historical D-Zug, Promotive and Bailey discussions were discovery leads, not current inventory or validated specifications. Generic electric radiator, oil-cooler, HVAC and decklid fans were excluded from the main rotor catalog.

## Delivered files

- `aftermarket_catalog.json`: 28 product/variant records and 44 source records
- `aftermarket_products.csv`: flat product table
- `aftermarket_parameters.json` and `.csv`: 85 quantitative claims, with units, qualifiers and source IDs
- `aftermarket_source_manifest.csv`: source type, lineage, access date and page/section locator
- `aftermarket_search_log.json`: representative multilingual coverage and negative results
- `carpoint_10578.pdf`, `carpoint_10584.pdf`, `carpoint_10578.png`: internal evidence copies only; do not automatically republish third-party files in the public repository

All source copies and linked images retain their original rights. Publish original summaries, factual parameter records and source URLs; check licensing before redistributing a supplier PDF, photograph or detailed drawing.
