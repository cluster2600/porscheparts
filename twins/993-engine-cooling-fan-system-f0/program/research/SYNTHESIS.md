# Research synthesis and open decisions

[Research home](README.md) · [Index with sources and locators](source-index.json) · [Validation plan](../VALIDATION_PLAN.md)

This synthesis summarizes the four delivered lanes. IDs refer to the original
records in the index; their caveats and access levels take precedence over
abbreviated wording. No target blade drawing, fit, safe speed, complete Turbo
performance curve or project-impeller LPBF qualification has been established.

## Identity and speeds

| Question | Documentary finding | Consequence |
|---|---|---|
| Which 993 impeller? | PET993, plate 105-00, PDF pages 77–79: Carrera `96410601531`, RS M64.20 `.40`, Turbo M64.60 `.21/.22`. ORIG05 repeats these families. | Distinguish the Carrera reconstruction from the Turbo reference; identify the physical specimen. |
| Hub `96410605131` | ORIG05 and PET964 document applications, including Turbo M30.69/M64.50. | Catalog applicability does not provide aftermarket-hub interface dimensions. |
| Is “935” identical to 993? | PORSCHE935 / GEO-S008 distinguish several 935 variants; the 935/78 combines water-cooled heads and air-cooled cylinders. | Horizontal and vertical cooling fan assemblies are not interchangeable by name. Equivalence is unproven. |
| 964 training | P10L: 12 impeller blades, 17 stator vanes, impeller drive ratio 1.6. Tiptronic alternator ratios 2.23 → 2.68 are separate. | Always identify the shaft associated with a speed. |
| Carrera airflow | P10L: 1,010 L/s without a speed in the table. GEO-S002: 1,010 L/s at 6,000 crankshaft rpm for Carrera, ratio about 1.6. | 9,600 impeller rpm is a conditional no-slip conversion; this point is not a Turbo curve. |
| Turbo airflow | ELFER993T / GEO-S005: 1,210 L/s at 5,750 crankshaft rpm; FORUMDIA and copies: 6,100 rpm. Ratio 1.8 is reported by secondary sources. | Open conflict; accepted target airflow remains unknown. |

FVD22 lists 24.5 × 24.5 × 8.7 cm and 0.9 kg as commercial product data. These
are not a toleranced blade-tip diameter and a metrological impeller-only mass.
The existing model's 245 mm remains an assumption. Specimen identity and
physical interfaces require verification.

## Product distinctions to preserve

| Sources | Finding or distinction | Caveat |
|---|---|---|
| AF01–AF03 EPS | Advertised cast-aluminum impeller, 11 blades / 245 mm; forged-steel hub. | “Forged” does not describe the entire impeller. |
| AF13, AF44 partworks | 250 mm blank to machine to 245 or 225 mm for the installation. | Blank and finished diameters are different states. |
| AF06–AF10 INDEX | Classic PRMA030: 12 blades, 245 mm, about 430 g, A7075 hub. PRMA010 964/993: about 400 g, other dimensions unknown. Fan housing 1,400 / 1,475 g on different pages. | Variants and conflicting masses retained; the “74%” baseline is unresolved. |
| AF04–AF05 | LN specifies a 6061 fan housing; the exact Rennline grade is not established. | Do not transfer fan housing material to the impeller or invent T6. |
| AF14–AF17 Carpoint | RSR 225 mm: magnesium fan housing 1,365 g, impeller 885 g; separate aluminum fan housing 1,850 g. Sheet: 244.5 mm / 11 blades and 254 mm / 12 blades. | Sheet applications, datums and tolerances require identification. |
| AF17 | 2 mm axial impeller/fan housing projection; different alternator heights and ring depths. | 2 mm is not radial clearance. Six holes at 60° do not establish their pitch-circle diameter. |
| AF20–AF26 | Torres, Spezialmotorer and Bailey describe complete flat-fan systems; FSH/TK/Design911 supply inlet and impeller subassemblies. | Subassembly and complete conversion are distinct. Shared FSH/TK GTIN, 1,500 / 1,600 g: lineage and conflict retained. |
| AF27 EB Motorsport | Bench-test interview: 1.5 hp at 4,000 and 32 hp at 12,000 impeller rpm. | Protocol, hp definition, pressure, airflow and uncertainty unknown; not a qualified curve or safe-speed limit. |
| AF28–AF29 Gunther Werks | Advertised air volume more than doubled. | Comparator and operating point absent; 7,500 engine rpm is not an impeller limit. |
| AF34–AF37 Classic Retrofit | 175 A: conventional/double-belt or RS drive; 240 A: serpentine belt and tensioner recommended. | **The user has selected no alternator.** Interfaces need measurement; early-911 spacers do not automatically transfer. |

Within this search scope, no supplier provides a complete pressure–flow–power
map with a protocol, qualified target-impeller fatigue data or a qualified
operational AM impeller. Listings are neither quotations nor geometry-reuse rights.

## Forums and lineage

The [multilingual report](corpus/forums/multilingual_forum_research.md) and
[access gaps](corpus/forums/coverage_and_gaps.md) distinguish accounts, reported
measurements and copied tables. Repeated Bill Verburg tables, including
F01/F03/F04/F07, do not become independent confirmations. The nine
[reported bench points](corpus/forums/reported_bench_series.csv) retain their
unknown speed axis. Accounts of rubbing, cracks and belts inform inspection;
they establish no nominal clearance, balance grade or target-impeller service life.

## Measurements and calculations to prepare

The [104-parameter contract](corpus/geometry/parameter-contract.json) retains
unknowns as `null`, units and acceptance gates. The
[measurement checklist](corpus/geometry/measurement-checklist.md) defines the
functional frame: A = bore axis, B = mounting plane, C = indexed feature.
At least two independent physical lengths, preferably three, must establish
scale. Global PCA and automatic ICP prove neither this axis nor relative
registration of the scan's rear portion.

GEO-S001 / SAE 920789 provides a primary Porsche abstract on cooling and
pressure differences. Full text and a usable curve remain unverified; lawful
acquisition is still needed. GEO-S024 identifies a secondary thesis reporting
about 0.317 m³/s at 5,000 crankshaft rpm, without experimental validation of our
impeller.

GEO-S009 / GEO-S010 identify **FAN-01**, an independent axial-fan benchmark
licensed CC BY 4.0: 495 mm impeller, 248 mm hub, 2.5 mm tip clearance, nine
NACA4510 blades, 1,486 rpm, 1.4 m³/s design flow, 150 Pa target, and reported
measurement of 126.5 Pa / efficiency 0.53. It is an option for checking a CFD
workflow against published measurements, not Porsche geometry. No benchmark
archive download or benchmark calculation is claimed as executed here.

GEO-S011, EOS AlSi10Mg/M290/30 µm sheet: typical data, vertical 230 MPa /
horizontal 270 MPa yield strength, fatigue 110 MPa at 20 million cycles,
R = -1, turned specimens and the condition defined in the sheet. These are
neither blade allowables nor ZRapid qualification. Project LPBF calculations
retain their own process card and limits.

ISO/AMCA GEO-S012–GEO-S017 describe testing, system effects and balancing;
no project certification is claimed. Similarity laws remain conditional on
matching geometry, density and flow regime. A ratio of 1.8 / 1.6 does not
establish an actual engine-cooling improvement.

Physical validation depends on specimen identity and metrology, selected
interfaces, the engine system and documented material/process. The research
is available and checked; these engineering conditions remain open.
