# Porsche 935 engine and cooling system evidence synthesis

Research date: 3 October 2026 UTC

## Conclusion

The research establishes useful variant identities, cooling topologies, nominal engine ratings and several reproduction-component descriptions. It does **not** establish a buildable factory 935 fan assembly or a calibrated whole-engine cooling model. In particular, original fan geometry, complete crank-to-fan ratio, view-defined rotation, bearing/preload and seal specifications, pressure–flow–power maps, and engine heat-rejection data remain unresolved.

The most consequential findings are:

- Factory 935/78 Moby Dick has water-cooled four-valve heads and air-cooled cylinders. It needs its own thermal and fan configuration
- Kremer K3's air-to-air change concerns **charge-air intercooling**. It is not proof of water-cooled cylinder heads
- The proposed 11,000 rpm / 3,500 cfm / 15 hp replica was abandoned. Those values are not completed test results
- EB's reported 1.5 hp at 4,000 fan rpm and 32 hp at 12,000 fan rpm concern a replica test installation, without a published calibration or complete curve
- Current 1.50 kg and 1.60 kg product masses describe funnel-and-wheel sets, not bare rotors. A machined 7075 rotor and a cast-aluminium rotor are different reproduction products
- The nine-blade carbon-fibre fan in Porsche's Group C publication cannot be assigned to the 1976 Group 5 car merely because its later engine is called Type 935/76

These conclusions and their source chains are recorded in [the parameter ledger](ENGINE_FAN_PARAMETER_LEDGER.json). No record is automatically admitted to a simulation, and no physical validation is claimed.

## Scope and evidence accounting

This synthesis read all four deliverables in each of **40 explicit language lanes**: German, English, French, Italian, Spanish, Dutch, Portuguese, Swedish, Danish, Norwegian, Finnish, Polish, Czech, Slovak, Hungarian, Romanian, Bulgarian, Greek, Croatian, Slovenian, Estonian, Latvian, Lithuanian, Irish, Maltese, Icelandic, Ukrainian, Russian, Belarusian, Serbian, Bosnian, Macedonian, Albanian, Turkish, Catalan, Basque, Galician, Welsh, Luxembourgish and Romansh.

The 160 lane files contain **535 source/access records and 418 claim records**. Those counts include rejected candidates, wrong-model controls, bibliographic leads and coverage observations. They are not counts of engineering sources or independent measurements. Earlier searches concentrated on the fan system; later searches and the separate engine supplement added engine operating and thermal context. Depth is therefore uneven across the expanded scope.

The [source-family register](SOURCE_FAMILIES.json) consolidates repeated URLs and identified publication chains. Translations of a Porsche release, repeated Design911 product pages and localized Highmotor articles do not provide independent corroboration. Different manufacturer articles are useful consistency checks but still have common organizational provenance. FSH, StuttGear and Design911 descriptions may share a supply chain; manufacturing independence was not established. The register's remaining URL families must not be interpreted as independently verified authors or experiments.

No additional web searches were made for this synthesis. It audits the recorded reads and findings, rather than claiming a fresh retrieval of every linked page. The [QA summary](QA_SUMMARY.json) records input hashes, schema checks, source references, publication restrictions and lane-level limitations. Original heterogeneous schemas and files were preserved. Three engine-supplement files were also reviewed; their seven source/lead records are separately listed and may overlap the lane sources.

## Factory engine branches

### 1976 factory 935

Porsche reports nominal displacement **2.85 L**, a **single turbocharger**, and **434 kW / 590 PS**. This is a manufacturer historical baseline, not a complete engine setup or dyno point. The reviewed passage supplies no rated rpm, boost reference, torque curve or fan gearing. It must not be populated with the later Group C Type 935/76 specifications. Ledger P001–P003. [Porsche turbo motorsport history](https://newsroom.porsche.com/en/press-kits/50-years-porsche-turbo/Porsche-and-turbo-technology-in-motorsport--from-pioneer-to-world-champion.html)

### 1977 factory 935/77

Porsche distinguishes **two smaller turbochargers** and **463 kW / 630 PS**. A separate manufacturer museum article gives **2,857 cm³** for the displayed 935/77. These sources identify a works development branch; they do not prove every 1977 customer car or subsequent rebuild had identical hardware. Ledger P004–P005 and P011. [Porsche turbo history](https://newsroom.porsche.com/en/press-kits/50-years-porsche-turbo/Porsche-and-turbo-technology-in-motorsport--from-pioneer-to-world-champion.html), [Engines in Concert](https://newsroom.porsche.com/en/history/engines-in-concert-10874.html)

### 1977 Baby

The manufacturer baseline is **1.4 L** and **279 kW / 380 PS**. Keep this small-engine sprint branch separate. A Czech Porsche newsletter also describes an air-cooled turbo six but does not supply its fan specification or a numerical thermal limit. The indexed publisher lead for 71 × 60 mm, 1,425 cm³ and associated operating figures was not fully read and remains a document lead. Ledger P006–P007. [Porsche turbo history](https://newsroom.porsche.com/en/press-kits/50-years-porsche-turbo/Porsche-and-turbo-technology-in-motorsport--from-pioneer-to-world-champion.html), [Porsche News Spring 2010, PDF page 9](https://porsche.cz/ufiles/o-porsche/porsche%20news/PorscheNews012010.pdf#page=9)

### 1978 factory 935/78 Moby Dick

The museum specification gives **3,211 cm³**. Porsche separates a maximum headline rating of **621 kW / 845 PS** from the **552 kW / 750 hp-label** Le Mans setting. The English labels do not establish a separate mechanical-horsepower measurement; the paired kW values and German/Polish metric labels must remain visible. No common rpm/boost/test condition was recovered for these two regimes. Ledger P008–P014. [Porsche Museum specification](https://newsroom.porsche.com/en/press-kits/Porsche-Museum/Porsche-935-78-%E2%80%9EMoby-Dick%E2%80%9C.html), [Porsche Goodwood account](https://newsroom.porsche.com/en/history/porsche-goodwood-festival-of-speed-england-935-moby-dick-962-804-911-carrera-rsr-turbo-2708-indycar-jubilee-70-years-racecar-15851.html)

Water-cooled four-valve heads coexist with air-cooled cylinders. A March 1978 Autosprint development report supplies period evidence of lateral head-cooling radiators and front oil radiators. That observation concerns a development car, not a final plumbing diagram. Its isolated five-speed caption is quarantined. [Porsche 2020 interview](https://christophorus.porsche.com/it/2020/394/frank-steffen-walliser-935-moby-dick-hockenheimring.html), [Autosprint printed pages 36–37](https://v8blog1978.wordpress.com/wp-content/uploads/2016/03/as-78-11-14p.pdf)

An upright/vertical fan is described in secondary cutaway coverage; a tertiary 210 mm versus 226 mm diameter comparison and one-third flow claim lead to unread book pages. Neither is admitted as measured factory geometry. The Dutch article prints **1,700 L/min** for 1977 and **500 L/min** for Moby Dick. Those suspect units remain literal: 0.02833 and 0.008333 m³/s by arithmetic only. They must not be silently changed to L/s or used to build a fan curve. Ledger P016–P018. [AutoWeek cutaway article](https://www.autoweek.nl/autonieuws/artikel/doorzaag-zaterdag-porsche-935-moby-dick/), [German tertiary bibliography trail](https://de.wikipedia.org/wiki/Porsche_935)

### 1978 customer cars

An Autosprint Mugello report about Gelo, Kremer and Konrad customer entries gives an approximate **3,500–8,000 engine-rpm range**, **700 CV**, and **1.4 atmospheres** of reported boost. It does not identify gauge versus absolute pressure, a measured power curve or fan speed. Its intercooler placement and revised turbo lubrication concern those customer cars, not automatically factory Moby Dick or the fan gearbox. Ledger P019–P020. [Autosprint printed page 28](https://v8blog1978.wordpress.com/wp-content/uploads/2016/03/as-78-12-19p.pdf)

## Kremer engines and cooling

### K3 architecture and individual cars

Kremer's published Ludwig account supports **air-to-air charge cooling**. Team-manager Achim Stroth places the exchanger above the gearbox and ahead of the engine. Their testimony is valuable for layout, but supplies no intercooler map, cylinder-air allocation or fan operating point. Ledger P021–P025. [Kremer Magazine 01, page 11](https://www.kremer-racing.com/assets/uploads/dateien/media/kremer-newspaper-no1.pdf#page=11), [Stroth account](https://automedia.revsinstitute.org/porsche-935-k3)

Ludwig recalls a 20-degree intake-temperature reduction and 30–40 PS benefit; Uwe Sauer recalls 30 degrees. These unconditioned recollections must remain separate, without averaging or converting them into cylinder-temperature reductions. The associated belt-repair story names injection-pump/alternator belts, not a demonstrated fan-drive failure. [Ludwig interview](https://www.netzwerkeins.com/2020/04/11/klaus-ludwig-im-interview-wiedersehen-mit-dem-teufel-ueber-die-ruhmreiche-aera-des-wunderautos-aus-koeln-bilderstoeckchen/), [Sauer interview](https://www.auto-motor-und-sport.de/oldtimer/kremer-porsche-935-k3-im-fahrbericht-jaegermeister-mit-riesenfluegel/)

Two useful specimen records must not be blended:

| Identified car or state | Source-reported engine information | Restriction |
|---|---|---|
| Bruce Meyer's 1979 Le Mans-winning K3 | 3.0 L, six-cylinder, twin turbo; owner says air-cooled and approximately 800 KM | Rounded owner/manufacturer account, without rpm, boost or as-raced build sheet |
| Wera K3 chassis 0090003, restored state | Engine 930/80; nominal 3.2 L twin turbo; 760 horsepower; vehicle gearbox 930/60 | An intervening 962-engine installation makes photograph date essential; horsepower standard and operating conditions absent |

Ledger P026–P031. [Porsche Bruce Meyer interview](https://christophorus.porsche.com/pl/2023/407/garage-bruce-meyer.html), [Wera chassis history](https://www.wera.de/ru/ispytaite-wera/tool-rebels/chast-istorii-gonok/)

Other documented identities include rebuilt K2 chassis 007 00016, K3a/80 chassis 000 00011, photographed K3/81 chassis 01 00020, and reconstruction 009 00016 completed in 2010. Installation observations are useful but do not authenticate original rotor metallurgy or metrology. The dimensioned miniature portion of Rob de Bie's page is not full-size evidence. [K3/81 photographs and scope](https://www.robdebie.nl/models/kremer-k3.htm), [reconstructed K3 seller listing](https://www.elferspot.com/nl/auto/porsche-935-1979-4267504/)

### K4 must retain its own record

The Canepa seller account for **K4-01 restored to 1983 IMSA specification** reports **3,162 cm³**, twin turbo, **700 hp at 7,500 rpm** and **536 ft/lbs at 6,100 rpm**. It lists aluminium block/head, dry-sump lubrication, dual ignition and selected internal-component brands. These are seller assertions, not factory metallurgy or fan-oil data. Intercooler changes and in-door ducts are reported for the car's history; the separate “over 800 hp” raised-boost account does not define the 700 hp operating point. Ledger P032–P037. [Canepa K4-01 listing](https://www.jamesedition.com/cars/porsche/935/1981-porsche-935-k4-for-sale-1136993)

Interpreting ft/lbs as customary torque lb-ft gives **about 726.72 N·m**. The Greek derivative's 74.1 kgf·m gives about 726.67 N·m. Likewise, 700 mechanical hp would be about 709.71 PS, plausibly explaining its 710-horsepower text. This is conditional unit arithmetic, not independent corroboration or proof of the unspecified power standard. [Greek linked report](https://www.drive.gr/posts/classic-news/porsche-935-k4-toy-1981-gia-285-ekat)

Gunnar's identified K4 installation supports the broad horizontal-fan drive architecture, but no K4-only rotor drawing or ratio was recovered. [Gunnar Racing explanation](https://www.gunnarracing.com/team/lola/stage4.htm)

## The complete horizontal fan system

### Architecture supported and specification missing

The restorer account describes a crank-driven belt, horizontal input shaft and a 90-degree gearbox under the fan, with a vertical output shaft. A member's illustrated account identifies a rubber-cushioned coupling and the mounting location. This describes the mechanism without establishing gear form, tooth counts, bearing arrangement, preload or oil requirements. Ledger P038. [Gunnar Racing](https://www.gunnarracing.com/team/lola/stage4.htm), [PCA BahnStormer December 2009, printed page 5](https://rsp.pca.org/BahnStormer/Bahn_2009_12web.pdf)

The whole-system boundary includes intake/ignition/injection packaging, alternator and belt alignment, oil-cooler relocation, inlet funnel, stator, shroud/baffles, leakage paths, fin resistance and exit pressure. An engine rpm cannot determine fan rpm without the complete drive ratio. A vehicle transmission code or ratio is not the fan-drive ratio.

### Measured claims versus proposals

| Evidence | Reported quantities | Treatment |
|---|---|---|
| EB replica rig account, 2015 | 1.5 hp at 4,000 fan rpm; 32 hp at 12,000 fan rpm, approximately 8,000 engine rpm | Builder-reported isolated points; no calibration, uncertainty, full curve or pressure/flow map |
| Paul/alfa11 proposal, 2003 | Up to 11,000 fan rpm at 7,500 engine rpm; 3,500 cfm / alternate 1,600 L/s; 15 hp | Project abandoned April 2005; promised comparison not completed |
| Steve Weiner's operated 935s | Approximately 30+ hp | Named recollection with no identified variant, speed or test method |

Ledger P039–P045. [EB report](https://ferdinandmagazine.com/porsche-flat-fan-kit), [proposal and abandonment thread](https://forums.pelicanparts.com/porsche-911-technical-forum/114459-where-find-type-935-flat-fan-2.html), [Weiner discussion](https://forums.pelicanparts.com/porsche-911-technical-forum/520886-flat-fans-revisited.html)

The inferred EB fan/crank ratio is approximately 1.5, not a demonstrated bevel-gear ratio. The proposal's 3,500 cfm converts to about 1.652 m³/s, versus its separate rounded 1.600 m³/s statement. Neither is a pressure-conditioned measurement. Do not average the three power claims, fit a universal curve through them, or infer gearbox losses from total drive demand.

### Reproduction parts and materials

| Identified product | What its own source reports | What remains unproved |
|---|---|---|
| Torres reproduction | CNC 7075 aluminium rotor; cast-aluminium drive housings; oil-feed fittings; fiberglass housing options | Temper, coating specification, geometry, bearing/seal stack, oil flow/pressure, burst rating and OEM revision equivalence |
| FSH 230d | Cast-aluminium wheel, GFK funnel, approximately 1.50 kg item mass | Bare rotor mass, original alloy and period allocation |
| FSH 230 | Separate GFK shroud set, approximately 1.50 kg | Supplied-content overlap; do not add automatically to 230d |
| StuttGear TK 230d | GRP funnel and cast-aluminium wheel, 1.60 kg item mass | Original rotor mass or an independent factory measurement |
| Design911 93510610300R/1 | Honey-coloured GRP housing and aluminium blades | Authentic OEM supersessions or interchange from listed related numbers |
| EB 0701403 / 0701505 | Guibo supplier ID; titanium crank pulley Grade 5 and 0.34 kg guidance mass | Coupling stiffness, pulley pitch diameter and drive ratio |
| Spezialmotorer | Replica applications and up to 32 separate spares | Complete BOM, drawing set or exact shared fitment across 934/935/IMSA 962 |

Ledger P046–P059. [Torres information sheet via supplier retailer](https://www.aasesales.com/products/noloc-j128-24000r-110746), [FSH 230d](https://www.f-s-h.com/Einlauftrichter-mit-Luefterrad-935), [FSH 230](https://www.f-s-h.com/Motorverblechung-935), [StuttGear TK 230d](https://www.stuttgear.com/Inlet-funnel-with-fan-wheel-for-Porsche-935), [Design911](https://www.design911.co.uk/p/fan-housing-with-fan-blades-porsche-935/), [EB pulley](https://eb-motorsport.com/shop/rsr-turbo-to-935-crank-shaft-pulley-titanium/), [Spezialmotorer](https://www.spezialmotorer.com/produkter/numquam)

Torres' 60–90 minute run-in at 2,000–8,500 rpm does not name the shaft represented by rpm and is not a certified maximum-speed or burst test. The Nomad/Lola owner's 7 kg arrangement uses a bespoke drive and standard 911 fan, so it supplies neither original 935 mass nor a lubrication prescription. [Torres discussion](https://forums.pelicanparts.com/porsche-911-used-parts-sale-wanted/905416-flat-fan-assemblies.html), [Nomad/Lola owner account](https://www.ddk-online.com/phpBB2/viewtopic.php?start=30&t=69167)

## Separate Group C engine Type 935/76

Porsche's Group C press kit explicitly assigns **Type 935/76** to the 956 engine: **2,649 cm³**, **92.3 × 66 mm**, two KKK K26 turbochargers, a reported **1.2 bar** pressure without an explicit gauge/absolute reference in the cited sentence, **620 PS at 8,200 rpm**, and **630 N·m at 5,400 rpm**. Its later cooling discussion describes bank-specific water circuits and a nine-blade carbon-fibre-laminate impeller. Ledger P063–P071. [Porsche Group C press kit, printed pages 18–20](https://newsroom.porsche.com/dam/jcr:a6f33b52-c47d-47b4-98c1-7e963661f587/40%2520Years%2520Group%2520C.pdf)

These are valuable data for a separately identified Group C configuration. They do not close the original Group 5 935 fan gaps. The same boundary applies to air-cooled single-turbo 962 IMSA versus other 962 C configurations: shared marketing fitment is not shared thermal duty.

## Other exclusions and unresolved contradictions

- **Modern 2018/2019 935:** Type 991.2/GT2 RS-derived data, including 3,800 cm³, belong to a different vehicle. Transmission oil-cooling bullets must not be read as historic fan lubrication
- **Walter Wolf road K3:** the seller describes a 1984 air-cooled twin-KKK road car with a 740 hp/PS label but no displacement or rated rpm. Secondary 2.85 L and 3.2 L claims remain unresolved; neither defines a racing K3
- **FABCAR 935/84, engine 690025:** seller wording about a composite flat-fan setup does not resolve rotor versus shroud material or prove original Kremer/factory hardware
- **934 power-saving anecdotes:** 14 CV or approximately 15 ch “gained” is not fan power absorbed, and the claimed baseline/method is missing
- **917, 959, road 911/964/993, VW conversions, scale models and game data:** no numerical substitution is permitted simply because the fan or model name resembles 935
- **Butzi 1976 table:** 588 N·m at 7,900 rpm implies about 486.44 kW, inconsistent with 447 kW if the same condition is intended
- **Butzi Moby Dick table:** 634 kW at 8,200 rpm needs about 738.32 N·m at that point; a stated 691 N·m peak cannot support that same condition. The 634 kW also conflicts with the manufacturer baseline
- **Turbo catalogue leads:** 5327 988 7004 / 935.123.008.00 and 5326 988 7010 / 930.123.015.00 are candidate catalogue associations. Matching catalogue rows may share upstream data. A separate September 1973 “935” row is quarantined; no universal historical fitment or compressor map follows

These checks are documented in the ledger and original source references. [Modern Porsche technical description](https://newsroom.porsche.com/en_US/motorsport/us-media-guide/race-cars/porsche-935-2019.html), [Wolf seller](https://www.mechatronik.de/en/sales/current-stock/porsche-935-kremer-k3-le-mans-en/), [Butzi 1976 table](https://www.butzi.cz/porsche/modely/76_935_coupe.html), [Butzi Moby Dick table](https://www.butzi.cz/porsche/modely/78_935-78_coupe_moby_dick.html), [TurboDave catalogue](https://turbodave.hu/turbo_porsche.html)

## Requirements for a defensible model

The following are engineering requirements, not claims recovered from historical sources. Start with one chassis, engine build date, engine serial/type and installed fan revision. Preserve every assumption and its uncertainty.

| Model purpose | Required inputs and validation |
|---|---|
| Fan aerodynamics | Measured rotor/stator/shroud geometry; clearances; rotation datum; fan rpm; inlet density and total conditions; outlet restriction; simultaneous flow, pressure and shaft-power tests |
| Installed engine cooling | Cylinder/head fin geometry, bank distribution, shroud leakage and vehicle-dependent inlet/exit pressures; measured air-resistance curve and metal temperatures |
| Coupled thermal model | Separate cylinder, head, oil, charge-air and applicable water-circuit loads; measured temperatures/flows, heat split and transient duty |
| Drive mechanics | Effective pulley and gear ratios, shaft speed/torque, belt tension/slip, bearing layout/preload, coupling stiffness, inertia and mechanical loss |
| Stress and durability | Material/temper or laminate definition, temperature-dependent properties, manufacturing tolerances, balance, vibration, fatigue and independently reviewed overspeed qualification |
| Whole-engine boundary | Matched torque/power/rpm/boost operating maps, fuel/ignition settings, turbo and intercooler maps, oil state and race-duration conditions |

For steady shaft rotation, power and torque obey P = T × 2πn/60 in consistent SI units. This is a consistency check, not a way to invent an engine curve from separate maxima. Likewise, engine brake power does not determine cooling heat rejection: fuel energy, exhaust, oil, heads/cylinders and other losses require a measured or validated heat balance. Turbo boost is not the cooling fan's pressure rise.

A full spare-parts catalogue is especially useful for mechanical identity and service details, but a first aerodynamic model principally needs traceable geometry, operating conditions and performance validation. Any speculative exploratory model must be labelled as such and kept separate from the evidence ledger. Missing values remain null, not zero.

## Highest-value next evidence

No owner, supplier, club or author was contacted during this synthesis. The next useful documents or measurements are:

1. **Correct factory catalogue and operating-instruction editions:** cooling and lubrication plates with adjacent part tables for the chosen year/customer/works configuration. A photographed cover reading “model 1978” does not prove Moby Dick contents
2. **Barth/Dobronz operating-instruction reproduction:** the inspected contents place 935 instructions at pages 256–267. These actual pages remain unread. The Moby Dick fan lead separately points to Barth/Büsing page 252; do not treat a citation as a read document
3. **Known-provenance assembly metrology:** part markings, dated installation, rotor and housing geometry, separate masses/inertia, pulley dimensions, tooth counts and view-defined rotation; no uncalibrated photographic scaling
4. **Mechanical service records:** bearing IDs/fits/preload, seal stack, gear backlash and lubrication feed/drain parameters for that actual unit
5. **Calibrated rig and installed-engine tests:** synchronized fan/engine rpm, torque, static/total pressures, airflow, air density, oil/coolant state and cylinder/head temperatures across representative duty points, with repeatability and uncertainty
6. **Identified engine dyno/cooling records:** the Nicholson McLaren K3 case study reports a rebuild and bench testing but publishes no numerical map or precise chassis identity; it is a useful evidence-location lead, not public calibration data

[Catalogue cover lead](https://www.magicsix.de/93578bta.php), [DNB contents](https://d-nb.info/1011312859/04), [period catalogue listing](https://www.pcarmarket.com/auction/marketplace-original-1970s-porsche-934935-spare-parts-catalog), [Nicholson McLaren case study](https://nicholsonmclaren.com/motorsport/case-studies/porsche-935/)

A recently photographed Typ 935 lubrication plate, **1/6/1, printed page 32**, lacks a visible edition and adjacent part-number table. It should be completed with those pages before drawing a fan-oil conclusion. [Public catalogue-fragment post](https://forums.pelicanparts.com/12706822-post1.html)

## Access limits and negative findings

This is a bounded public-source search, not “all European languages” or “every forum on Earth.” Source language was checked from text rather than country domain. English on a Swedish or Irish site was not counted as native-language evidence; localized versions were not treated as independent engineering reports.

The sparse-language lanes are meaningful negative coverage. Irish, Maltese, Macedonian, Albanian, Basque, Welsh, Luxembourgish and Romansh provide no qualifying technical claim set; several other lanes retain only quarantined secondary leads. For example, Welsh-language National Library searches returned no matches, while the genuine Romansh RTR racing article concerned a 1974 RSR rather than a 935. Those outcomes do not prove the absence of unindexed print, audio, private or physical holdings.

Forum reading was selective and documented. English Pelican/DDK/PCGB discussions yielded the most detailed replica information. Public threads were also actually inspected in Spanish, Dutch, Italian, Swedish, Estonian and several other lanes. Some public pages recovered after extraction failures, so they must not be described as login-gated. Conversely, member-only forums, CAPTCHA/security challenges, robots restrictions and certificate warnings remained access limits; no bypass is claimed.

Native search itself can be incomplete: Avtomobilizem returned zero for a term visibly present in inspected posts. A search result or zero-hit page is evidence of that search, not proof about the entire site. Heterogeneous query logs are preserved without a falsely precise global query total.

## Publication and reuse

Only the four synthesis deliverables are designated as the public synthesis package. They contain original analysis, short bibliographic identifiers, factual specifications and links. Third-party PDFs, DOC files, photographs, screenshots and raw page caches are research materials and must not be copied into the repository.

Five original lane files contain local/cache references: de/REPORT.md, de/sources.json, en/search-log.json, it/REPORT.md and it/sources.json. Public per-lane export should also remove or paraphrase quote/excerpt fields across languages. No explicit JSON quote field individually exceeded 25 words in the scan, but that does not establish aggregate per-source compliance when fragments or translations repeat. The synthesis copies none of those excerpt fields.

The QA manifest preserves hashes of the original 160 lane files. This research package does not claim that a GitHub upload, numerical simulation, component manufacture, service procedure or physical test has been completed.
