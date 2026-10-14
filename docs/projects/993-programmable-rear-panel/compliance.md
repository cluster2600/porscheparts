# Compliance and origin — decision gates

Preliminary research consulted on **September 27, 2026**; legal and technical
qualification of the product **not obtained**. Official references in
[sources.md](sources.md). The project may be stopped or limited to the
demonstrator if no acceptable route is confirmed. CE, road approval and Swiss
origin answer different questions.

## Start with the original part

Porsche describes a rear panel with a red reflective logo [S20]. That establishes
neither the regulatory class of each area nor the equipment of each market. The
manufacturer of a kit for the 993 documents a reflector/rear-fog-lamp housing
assembly and the rear fog lamps [S21]; this is evidence of functions present on
some configurations, **not evidence of road approval of the kit conversion**.
Do not transfer this architecture to every 993.

Before designing, record on the exact reference: active functions, bulbs,
wiring, reflective surfaces, E/e markings and categories, links with the adjacent
lamps. Determine where the mandatory retro-reflectors are and whether the panel
is one of them. Confirm separately the presence of a fog lamp, a reversing lamp
or any other function: **do not presume that the center panel carries the
reversing lamp or that it is purely decorative**. The actual part and its variant
dossier must decide. Photograph the markings without publishing the VIN/plate.

Changing the lens, tint, source or geometry can invalidate an approved function.
Copying an existing marking is excluded; physically keeping an approved component
does not guarantee the compliance of its integration. Even removable and switched
off, a screen can alter reflection, functions, color, visibility and safety.

## Switzerland, EU and Germany

| Area | Basis / verified facts or status | Work to obtain |
|---|---|---|
| Switzerland, vehicle | OETV RS 741.41 (Swiss ordinance on the technical requirements for road vehicles) [S22]; FEDRO (OFROU) publishes the identification of lamps/retro-reflectors [S23] | Consolidated version and applicable articles to be reviewed; requirements according to first registration, market and variant; approval/modification with the cantonal service, with competent expert assessment |
| Germany | StVZO §49a [S24] covers the permitted lighting installations and expressly includes variable/dynamic external optical displays, self-illuminated or backlit; §19 deals with the consequences of modifications on the authorization [S25] | Written opinion before full-width design; component/installation approval route, §22a/§21 where applicable, without presuming that an individual approval will admit animated text |
| UN / EU, vehicle | Examine UN R48 (installation), R148 (signaling), R150 (retro-reflection), R10 (EMC), as well as the relevant historical regulations R38/R3/R7/R23 according to functions and transitional rights | The laboratory must select the series of amendments, photometry/color/angles and markings; no automatic equivalence between old vehicle and new component |
| EU radio | RED 2014/53/UE [S26]: safety, EMC, spectrum and radio product file | Laboratory: EN 300 328, EN 301 489 and safety/exposure according to the applicable versions; EU declaration, marking, instructions and traceability. A pre-qualified module is not sufficient on its own |
| Swiss radio | OFCOM: essential requirements, assessment, documentation, declaration and information/marking [S27] | Confirm OIT (Swiss ordinance on telecommunications installations)/rules in force and recognition of the EU file, instructions for the target markets |
| Cybersecurity / product | Scope of the RED delegated regulation 2022/30 and subsequent texts, CRA, RoHS/WEEE (DEEE), general safety, packaging/EPR (REP) obligations to be examined according to product and date | Do not assert that BLE without cloud automatically exempts from the requirements; relay phone and data processing to be qualified. Legal analysis and application dates remain open |
| Bluetooth | Bluetooth SIG requires qualification before sale/distribution [S28] | Choose the route, current fees, name of the marketing entity and trademark rights; qualification separate from CE |

**Two distinct uses:** coupon on the bench / exhibition on closed private
grounds, and an installation intended for the road. A private car park open to
the public is not presumed to be outside road law. A private demonstration does
not exempt from electrical safety, site authorization, glare control, or the
obligations that apply to placing on the market. The "off while driving"
interlock is a possible risk reduction, **not an approval route in itself**.
No unvalidated speed signal is invented; in particular, no CAN bus is presumed
on the 993.

## Questions for the competent body

After agreement, send the regulatory RFQ from [rfqs.md](rfqs.md), with:
reference/variant, photos of the markings, a diagram of the functions kept/removed,
optical concept, planned matrix and power, failure modes and power supply.
Obtain in writing the functions to preserve, applicable texts/series,
acceptability even with the screen off, tests, samples, cost/lead time and the
CH/DE/EU route. TÜV is not a universal label that bypasses these questions. DTC
is a Swiss lead; TÜV Rheinland Berlin publishes a specific competence in lighting
[S18–S19]. Check the mandate/accreditation for the tests actually ordered.

## "Made in Switzerland" goal

According to the IPI (Swiss Federal Institute of Intellectual Property)
[S29–S30], an industrial product must notably reach **60% of the eligible cost
price in Switzerland**, carry out in Switzerland the activity that gives it its
essential characteristics, and perform a physical manufacturing step there.
Final assembly alone does not automatically establish any of these conditions.

The [swissness.csv](swissness.csv) register and the calculation in
[budget.md](budget.md) are an analysis model, **not an attestation**. Include
eligible production and R&D costs according to a documented allocation; break
down imported components, local processing and labor. Examine quality control,
certification and amortization separately with the IPI rules. Packaging,
post-production distribution and after-sales service are excluded from this
calculation; they stay in the economic budget. Do not automatically exclude
imported LEDs on the grounds that they are not manufactured in Switzerland: any
exception requires its basis.

Private evidence file per batch: bill of materials and origin, itemized invoices,
manufacturing site, hours actually worked, R&D amortization base, stable
accounting method, description of the essential operation and review report.
Recalculate on any change of supplier or volume; keep anonymized references that
can be published. A total cost of 250 CHF does not mean that 150 CHF are eligible as Swiss.

"Made in Switzerland" / "Swiss Made" is an indication of origin; a private label
(for example a Swiss Label trademark license) adds its own regulations and
rights, without replacing the law. No Swiss cross, label or Swiss claim appears
on the mockup, the advertising or the packaging. The internal wording is
**Swiss origin goal, to be demonstrated**.
