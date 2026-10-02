# 993 Turbo engine research and K16 hybrid data

Research and owner-requested integration dated 2 October 2026. The engine is
the air/oil-cooled 3.6-litre M64/60 of the Porsche 993 Turbo. The owner's target
is **more than 550 metric horsepower at the crankshaft, with power as the
priority**, using the original K16 turbochargers as hybrid donors.

The [normalized catalog](../../../catalog/reference/993-turbo-research-20261002/)
keeps factory specifications, aftermarket declarations, secondary reports,
calculated examples and missing evidence distinct. The
[training package](../../../training/993-turbo-20261002/README.md) provides
reproducible plain-text CPT and native-message SFT exports with provenance and
separate training, validation and test partitions. It prepares data; no model
training, adapter replacement or measured model improvement is claimed.

## Findings that affect the project

The stock reference is 300 kW / 408 metric hp at 5,750 rpm, 540 Nm at 4,500 rpm,
100 × 76.4 mm bore/stroke, 3,600 cm³ displacement, 8.0:1 compression and two
parallel K16 turbochargers. Published boost is 0.8 bar gauge, not a compressor
pressure ratio. BorgWarner identifies the pair as K16-6735 and K16-6736.

Two supplier pages describe original-core 993 K16 hybrid products at a declared
650 PS capacity. These are suitable proposals to investigate for the target;
their published capacity is neither a complete turbo map nor a power or
durability qualification for a particular M64/60 engine.

| Product | Published configuration | Evidence limit |
| --- | --- | --- |
| [TTE650 5050](https://tteglobal.com/porsche/911/993-turbo/490/tte650-5050-porsche-993-upgrade-turbochargers) | Original K16/8 hot housings and clipped original K16 turbines; billet 6+6 compressor, 50 mm inlet; turbine outlet stated as 50 mm | 650 PS capability claim; no public compressor/turbine map or complete 993 operating-point set |
| [TTH K16-650](https://www.turbo-technik-hamburg.de/shop/porsche/911/993/435/porsche-911-993-turbo-k16-650ps) | Customer-supplied Porsche/BorgWarner K16 with hot housing 8; milled Extended Tip compressor, CNC contour, trimmed turbine and reinforced bearings/actuators | Up to 650 PS with appropriate engine components and software; wheel diameters and maps not published |
| [FVD K16/24](https://www.fvd.net/fr/shop/turbocompr-sport-k16-24-g-pour-993-fvd123013~p262679) | 47.5 mm compressor-wheel inlet, housing/backplate work, turbine trimming and reinforced thrust bearing | 555 hp in the supplier's published units, conditional on its supporting components and calibration |

The consulted 750–800 PS products use K24 donors. TTE750 explicitly excludes
K16 donors for that product. This is a product-specific restriction, not proof
that every conceivable K16 development has the same limit. Hot-housing labels
8/10 must not be silently converted into ordinary dimensionless A/R values.

## Actual map leads

- [SJM KKK 2467 GGA/GGB](https://www.sjmautotechnik.com/parts_products/turbo/k16.htm)
  is a genuine historical compressor-map scan with efficiency and corrected
  speed/flow data. It is published for 5316-988-6717, an Audi upgrade reference.
  The compressor designation overlaps the 993 family, but exact wheel, diffuser
  and housing equivalence with 6735/6736 has not been established. Printed
  reference conditions are 981 mbar and 293 K. The highest plotted speed is not
  automatically a certified rotor limit.
- [Turbomap's database](https://www.turbomap.ch/Home/TCDatabase) offers measured
  numerical compressor and turbine SAE datasets for a Porsche 996 K16-2467G,
  M96/70, 309 kW. The catalog was read; the quoted datasets were not acquired.
  This is a different engine/application, with exact turbo identity still to
  obtain before comparing it with the 993.
- [Garrett G25-550](https://www.garrettmotion.com/racing-and-performance/performance-catalog/turbo/g-series-g25-550/),
  GT2860RS and BorgWarner EFR6258/6758 provide manufacturer comparison maps.
  A map measured in their original housing cannot be assigned to a K16 hybrid
  merely because its wheel diameter is similar.
- [Garrett Turbo Tech 103](https://www.garrettmotion.com/wp-content/uploads/2019/10/GAM_Turbo-Tech-103_Expert-1.pdf)
  explains compressor maps, absolute pressures and system losses.

No map explicitly qualified for the exact stock 993 K16-6735/6736 assembly was
confirmed in the consulted sources. That statement describes this research's
result; it does not establish that such data do not exist.

RUF Turbo R/CTR2 specifications and forum-transcribed engine curves are kept as
configuration-specific comparison evidence. Engine power/torque alone cannot
identify a unique compressor or turbine map. Some transcribed torque/power
points are internally inconsistent. RUF UK's printed 405 kW / “550 bhp” also
mixes power units. Singer's 3.8-litre engines and Gunther Werks' 4.0-litre engine
change the matching problem and do not supply stock K16 evidence.

## Reports and data

The original French research reports are retained as session deliverables.
They have been regenerated for public export to remove the private project
source link and the duplicated raw Carrera OCR appendix. New documentation
and normalized record prose are in English. The current catalog and training
manifests govern machine consumption; the reports describe the research stage.

| Export | Contents |
| --- | --- |
| [Engine PDF](exports/fr/Porsche_993_Turbo_dossier.pdf) / [DOCX](exports/fr/Porsche_993_Turbo_dossier.docx) | Architecture, materials, cooling, speeds, references, audit and missing data |
| [Engine workbook](exports/fr/Porsche_993_Turbo_registre.xlsx) / [JSON](exports/fr/registre_recherche.json) | 164 source-tagged facts, calculations, 15 audit findings and 19 missing-data families |
| [Turbo PDF](exports/fr/Porsche_993_cartographies_et_hybrides.pdf) | Map leads, hybrid comparison, reverse-engineering protocol and supplier data request |
| [Turbo workbook](exports/fr/Porsche_993_cartographies_et_hybrides.xlsx) / [JSON](exports/fr/registre_cartographies.json) | 40 documentary references, secondary curve points, editable matching example and provenance |
| [Calculated demand plot](exports/fr/demande_calculee_par_turbo.png) | Assumed engine airflow and pressure-ratio demand; no turbo map overlaid |
| [Publication manifest](publication-manifest.json) | SHA-256 and size of every retained report/data export |

The 20 matching points assume 3.6 L, equal flow sharing, 90% volumetric
efficiency, 50 °C manifold air, 20 °C inlet air, 1 bar ambient and fixed inlet/
outlet losses. They are calculated examples, not measured operating points,
validated boost settings or predicted power. Change the correction references
to match the selected compressor map.

The existing [Carrera manual registry](../../../catalog/manual/993-workshop-manual-measurements.json)
remains separate. Its 2,496 entries include 2,190 OCR occurrence records; they
are not newly inspected M64/60 data and are not duplicated as raw text in this
publication or used as Turbo training truth.

## Evidence and publication boundaries

Source links and original factual summaries are published. Raw supplier pages,
commercial map images, proprietary manuals, raw scans, private source data,
vehicle identifiers and consultation scratch paths are omitted. Third-party
sources retain their own rights; accessible content is not automatically
redistributable. The repository's license applies to original authored reports
and training examples, not to an upstream manual or map.

OEM alloy grades, exact K16 operating speeds and the absolute Turbo fan ratio
remain unresolved. FVD's 100,000 rpm VSR condition and TTE's generic balancing
text are not 993 operating limits. Hybrid qualification needs the exact
wheel/housing combination, turbine flow, maximum rotor speed, temperature
limits, balance report and instrumented engine results including back-pressure.
This integration releases no physical part or engineering design.

The [validation receipt](validation.json) records the dataset checks, the
environment-specific permission-test recovery and the existing Docker audit
that could not complete because the execution environment ran out of disk space.
