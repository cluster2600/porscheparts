# 993 Turbo airflow calculation data

Collection status as of August 30, 2026. This document prepares a simulation of
the 993 Turbo air circuit. It declares neither an exact K16 geometry, nor a
measured performance, nor a manufacturable part.

## Conclusion of the collection

The dossier is sufficient to launch an exploratory study of engine mass flow
and of the pressure losses of a cold-side duct. It is not sufficient to
faithfully simulate the K16 wheel, calculate its speed, predict efficiency or
design a replacement wheel.

The main gap remains the same after the German-language search and the
Porsche Fanatics consultation: no usable public K16 compressor/turbine map, no
blade profile, no internal clearance, no efficiency curve and no intercooler
pressure-loss measurement were found.

## Evidence hierarchy

| Level | Source | What it allows us to claim | What it does not allow us to claim |
| --- | --- | --- | --- |
| A | [Porsche Christophorus](https://newsroom.porsche.com/christophorus/fr/2020/394/turbo-engines.html) | Parallel twin-turbo architecture, 3,600 cm3, 0.8 bar, 408 PS, 540 Nm | K16 map, CAD, materials, losses |
| A | [Porsche Austria PET, plate 107-45](https://www.porsche.at/media/Kwc_Basic_DownloadTag_Component/4740-45397-124814-downloadTag/default/f5000535/1729608718/kat017-d-911-98-katalog.pdf) | Part numbers, quantities, seals, clamps and interfaces to look for | Flow dimensions, tolerances, thicknesses, CAD |
| B | [BorgWarner Performance Catalog](https://www.borgwarner.com/docs/default-source/iam/boosting-technologies/bw_turbo-performance-catalog.pdf) | K16-6735 + K16-6736 pairing, catalogue power and commercial limits | Allowable limit of an additive part, aero map |
| C | [FVD](https://www.fvd.net/de/shop/turbolader-k16-rechts-993-serie-99312301452-993123014dx~p239094), [Invasion Auto Products](https://www.invasionautoproducts.com/94pocark16tu.html), [TurboMaster](https://www.turbomaster.com/eng/turbo/borgwarner/5316-988-6735/) | Part numbers, dimensions and diameters declared by vendors | Independent measurement, wheel profile, tolerance |
| C | [elferclassic](https://www.elferclassic.de/technik/techdaten/993-turbo-95-98-techdat.php) | Engine operating points and reference speed | Actual intake mass flow and boost curve |
| derived | Calculations in this document | Mass-flow envelopes with explicit assumptions | Measured Porsche data |

The detailed records are in `catalog/sources/`. The mass and envelope values
retained are in `catalog/reference/993-declared-part-data.json` with status
`declared`.

## System identification

### Turbochargers

- Porsche describes two small turbochargers in parallel, each feeding one
  cylinder bank, with two air-to-air intercoolers.
- The BorgWarner catalogue identifies the original pair as **K16-6735 +
  K16-6736** for the 911 Turbo 993 3.6. It states 408 hp stock and a commercial
  limit of 500 hp for the stock turbo. The upgrade line lists the K24
  5324 988 7003/7004 and 555 hp.
- The public documentation found identifies the **KKK / BorgWarner /
  3K-Schwitzer** family. Garrett is not confirmed by the sources consulted; the
  turbo must not be renamed Garrett without an identification plate or a
  primary source.
- A supplier record identifies the right-hand K16 as BorgWarner
  `5316-988-6735`, Porsche `993 123 014 51/52`, CHRA `5316-710-0520` and model
  `K16-2467GGA/8.88`. The left/right attribution of the `6736` remains to be
  confirmed on a part.

### Subassembly bill of materials collected

The TurboMaster page for the `5316-988-6735` provides catalogue identifiers
for the CHRA and the subassemblies:

| Subassembly | Public part number |
| --- | --- |
| CHRA | `5316-710-0520` |
| Bearing housing | `5316-151-0002` |
| Back plate | `5314-151-5702` |
| Heat shield | `5316-165-2000` |
| Thrust collar | `5314-127-0400` |
| Spacer | `5314-127-0500` |
| Compressor housing | `5324-101-5320` |
| Turbine housing | `5316-100-9050` |
| Turbine wheel | `5316-120-5000` |
| Compressor wheel | `5324-123-2006` |
| Actuator | `5825-110-4006` |
| Declared turbine A/R | `8.00` |

Invasion Auto Products declares for the right-hand K16:

| Item | Declared value | Limitation |
| --- | ---: | --- |
| Turbine wheel, inducer | 54.96 mm | Supplier diameter, profile unknown |
| Turbine wheel, exducer | 48.97 mm | Supplier diameter, profile unknown |
| Turbine wheel, trim | 6.45 | Supplier convention to be confirmed |
| Turbine wheel | 12 blades | Profile, thickness and angle unknown |
| Compressor wheel, inducer | 40.6 mm | Supplier diameter, profile unknown |
| Compressor wheel, exducer | 60.5 mm | Supplier diameter, profile unknown |
| Compressor wheel | 6 + 6 blades, billet | Material and profile not documented |
| Compressor housing, alpha angle | 307.5 deg | Supplier reference only |
| Turbine housing, beta angle | 70 deg | Supplier reference only |
| Wastegate | 0.50 bar | Declared setting, not a control law |
| Rod lift | 4.20 mm | Measurement/protocol not provided |

These numbers do not define a parametric wheel: a wheel requires the complete
surfaces, the local angles, the thicknesses, the hub, the radii, the clearances
and the manufacturing law.

## Air circuit and OEM interfaces

The path to model first is:

```text
filter / HFM mass airflow sensor -> bank split
    -> left K16  -> hose -> left intercooler  ->
                                                  merge -> throttle
    -> right K16 -> hose -> right intercooler ->      -> plastic manifold
```

The Porsche PET for plate 107-45 confirms the following part numbers for the
charge circuit:

- intercooler: `993 110 330 53`;
- air ducts: `993 110 340 53` and `993 110 340 54`;
- brackets: `993 110 110 50` and `993 110 110 52`;
- temperature sensor: `993 606 114 00`;
- left hose: `993 110 633 56`;
- right hose: `993 110 632 56`;
- O-rings: `30 x 3 mm`, part number `999 707 326 40`;
- clamps: `60-80/12`, part number `999 512 648 02`, and `40-60/9`, part number
  `999 512 647 02`;
- rubber mounts: `930 113 430 00`; bushings `993 110 111 50`;
- screws and washers to be identified before any interface CAD.

The PET is the best bill-of-materials evidence, but it does not give the inside
diameter, the bend radius, the thickness, the core section or the complete
center distances. The dimensions below therefore remain product envelopes and
packaging bounds.

## Available dimensions and masses

| Object | Dimensions / mass | Status for the twin |
| --- | --- | --- |
| Complete left K16, FVD | `280 x 190 x 210 mm`, `5.76 kg` | Supplier declaration, envelope only |
| Complete right K16, FVD | `280 x 190 x 210 mm`, `5.60 kg` | Supplier declaration, envelope only |
| FVD right pressure hose | `430 x 70 x 90 mm`, `0.42 kg` | Aftermarket replacement |
| FVD left pressure hose | `430 x 70 x 115 mm`, `0.42 kg` | Aftermarket replacement |
| FVD reinforced hose kit | stated fitting `43/57 mm x 410 mm`; envelope `440 x 160 x 100 mm`, `1.08 kg` | Connection bound, test pressure not provided |
| FVD air duct `993 110 340 54` | `600 x 280 x 50 mm`, `0.9 kg` | FVD development, not OEM geometry |
| FVD reinforced bracket | `255 x 80 x 23 mm`, `0.2 kg` | Aftermarket upgrade, not structural qualification |
| AKS DASIS core `177020T` for `993 110 330 53` | core `260 x 270 x 60 mm`, `7.06 kg` | Aftermarket core, not complete assembly |
| TA Technix module `05PO002` | two core modules `260 x 260 x 100 mm`; stated fittings 66 mm outside / 68 mm inside; max width 860 mm, max height 240 mm, center distance 690 mm | Aftermarket, heterogeneous data not to be combined without a drawing |
| FVD Motorsport intercooler `FVD110330` | `870 x 410 x 190 mm`, `10.1 kg` | Upgrade with installation modifications |
| FVD left heat shield | `160 x 110 x 105 mm`, `0.23 kg` | Product envelope, fasteners unknown |
| FVD sensor `993 606 114 00` | `75 x 35 x 20 mm`, `0.02 kg` | Product envelope, electrical curve absent |

The mass of a replacement, a kit or a core must never be added up as OEM mass.
The source references and the qualification are kept in the JSON register.

## German-language forums

The forums were searched separately from manufacturer sources. They are useful
for finding configurations, recurring failures and data to request from an
owner, but their posts are not metrological measurements by default.

| Forum | Useful information | Modeling decision |
| --- | --- | --- |
| [PFF, 408/430/450 PS](https://www.pff.de/thread/2651537-993-biturbo-408-430-450-ps-unterschiede/) | Reports indicating K16 on 408/430 and K24 on 450/WLS II, with ECU/cooling modifications | Variant cross-check only; does not replace the turbo plate or the VIN |
| [Carpassion, displayed pressure](https://www.carpassion.com/forum/thema/26748-ladedruckanzeige/) | The instrument cluster reportedly caps at 0.8 bar; modified cars are reported at 1.3-1.4 bar; hoses and clamps can cause problems | The cap is treated as a display limit; modified pressures are excluded from the stock case |
| [Motor-Talk, 993 Turbo compilation](https://www.motor-talk.de/forum/993-turbo-fragen-zum-kauf-t1226876.html) | Leads on WLS, K16/K24, supposed limits of the intercooler and the mass airflow sensor | Purchase/inspection leads, not boundary conditions |

The most useful common signal is circuit maintenance: check hose seating,
clamps, fittings and leaks before interpreting a low pressure. The forums,
however, provide no internal section, no fitting profile, no K16 map and no
reproducible HFM mass flow. Pressure and power values from modified vehicles
must not be injected into the stock twin.

## Tuners and turbo manufacturers

Tuners sometimes publish more detail than forums, but these are proprietary
configurations and performance promises. Their value for the twin is to show
which variables were actually modified and which information must be
requested.

| Tuner | Published configuration | Useful data | Limitation |
| --- | --- | --- | --- |
| [FVD](https://www.fvd.net/fr/shop/turbocompr-sport-k16-24-g-pour-993-fvd123013~p262679) | K16/24 hybrid | Stated compressor inducer 47.5 mm, CNC housing, modified backing plate, reinforced turbine and bearing, balancing, oil/DME adapters | 555 hp is a kit target; no map or complete profile |
| [Cargraphic](https://www.cargraphic.de/en/your-vehicle/for-porsche/for-911/for-993/for-turbo-turbo-s-36l/engine-upgrade-kits-porsche-993-turbo-s-36l/power-kit-2-for-porsche-993-turbo-36l/lkp93t300s2/) | Special K16/24 + ECU + exhaust + oil | 475 PS / 632 Nm stated, tests claimed on an RS-Tuning dyno | Dyno sheet, boost, IAT and mass flow absent |
| [TTP](https://t-t-p.de/motortuning-porsche/) | K16 450 PS, modified K16 500 PS, K24 550 PS | Integrated water-to-air intercooler, oil cooling, programmable ECU, levels 450/580, 500/620 and 550/640 | Tuning figures, with no map or dyno protocol |
| [Elferwelt](https://www.elferwelt.de/leistungen/porsche-993-turbo-gt2/) | K16/8055011W, 520-540 PS kit | Lightened rotating assembly, clearance optimization, static/dynamic balancing, matched injectors, DME CC460/OTP | The mention `80er CNC Druckseite` is not a defined dimension |
| [TTH](https://www.turbo-technik-hamburg.de/shop/porsche/911/993/436/porsche-911-993-gt2-wls-i-ii-turbo-s-3-6-t-k24-750ps) | K24 with hot-side housing 10 | Extended Tip, CNC housing, reworked turbine, reinforced bearings/capsules, balancing stated down to 0.05 g | K24 offer up to 750 PS with adapted engine and software; not stock K16 |
| [9ff](https://www.9ff.com/en/pages/993-konfigurator) | F64 twin turbo 550 with 2x K24-24.80 | 550 hp / 700 Nm, water intercooler, large ducting, injectors, reinforced pump and case | Complete conversion; no map or wheel geometry |

Two lessons are directly useful:

1. K16/24 hybrids seek the compromise between low-rpm response and high-rpm
   flow. They must not be used as the geometry of the original K16.
2. At high power levels, tuners simultaneously modify turbo, intercooler, fuel,
   ECU, exhaust and bottom end. It is therefore impossible to attribute a flow
   or temperature gain to the turbo alone.

Tuner pages do not publish the data we need for an aero model: compressor and
turbine maps with corrected flow, pressure ratios and efficiency islands, shaft
speed, T1/T3, pressure losses, clearances and blade profiles. A technical
request addressed to them must demand these values, the test conditions, the
uncertainty and permission to use the data.

## Public dyno data

The search found a few dyno points, but no complete calibration dossier. The
register [`dyno-reference.json`](../simulation/993-turbo-dyno/dyno-reference.json)
keeps the published values and their context:

| Case | Reported data | Use retained |
| --- | --- | --- |
| RUF Turbo R on K16 base | Torque in lb-ft from 2,000 to 6,000 rpm; stated peaks 506 hp at 5,500 and 460 hp at 6,000 | Incomplete anchor curve; torque/power consistency check |
| RS-Tuning/UMW comparison | K24RS at 522 PS DIN versus K16 Stage 3 at 471 hp on the same engine | Level comparison, with no usable curve points |
| Powerhaus K24 | 500 whp and 525 lb-ft at 5,000 rpm, about 1 bar reported | Chassis anchor point; power at the wheels, not the crankshaft |
| Rebuilt K16 / Turbo S DME | 324 whp at 6,000 rpm and 329 lb-ft at 4,600 rpm, three pulls reported | Modified chassis anchor, with no crankshaft conversion |
| Cargraphic K16/24 | 475 PS at 6,090 rpm and 632 Nm at 4,550 rpm | Manufacturer target, dyno sheet absent |
| AP Car Design K26 | 610 PS and 920 Nm at 4,200 rpm on a complete conversion | Contextual bound outside K16/K24 |

The script `scripts/model_turbo_dyno_0d.py` derives for each point the power
from torque, the BMEP and a per-turbo mass-flow envelope. It also compares the
published power/torque values at the same speed and flags discrepancies. The
output is in `simulation/993-turbo-dyno/derived-dyno-curves.json` and stays at
status `reference_only`: it fabricates neither a compressor map nor a CFD
calibration.

## Available engine conditions

| Parameter | Value | Nature |
| --- | ---: | --- |
| Cylinders | 6 | Cross-checked secondary technical data |
| Displacement | 3,600 cm3 | Porsche / technical source |
| Bore x stroke | `100 x 76.4 mm` | Secondary technical compilation |
| Compression ratio | `8.0:1` | Secondary technical compilation |
| Power | `408 PS` at `5,750 rpm` | Porsche |
| Torque | `540 Nm` at `4,500 rpm` | Porsche |
| Rev limiter | `6,720 +/- 20 rpm` | Secondary technical compilation |
| Maximum public boost | `0.8 bar` | Porsche; pressure and measurement location to be specified |
| Load measurement | HFM / mass airflow sensor | Functional identification, calibration absent |
| Fan | `1,210 l/s` at 5,750 rpm | Engine cooling, **not intake flow** |

The cooling fan flow is explicitly excluded as a turbo inlet condition. It
concerns the engine cooling air.

## First calculated mass-flow envelope

This section is a reproducible derivation, not a measurement. Assumptions of
the first sweep:

- four-stroke engine of `0.0036 m3`;
- ambient and compressor inlet pressure: `1.013 bar abs`;
- manifold pressure: `0.8 bar` of boost, i.e. `1.813 bar abs`;
- post-intercooler temperature: `50 degrees C`;
- volumetric efficiency swept: `0.85` to `1.00`;
- equal split between the two banks;
- ideal gas, `R = 287.05 J/(kg K)`;
- no leakage and steady state.

The formula is:

```text
Vdot = Vd * N / (2 * 60)
rho = p / (R * T)
mdot_total = rho * Vdot * VE
mdot_banc = mdot_total / 2
```

With these assumptions, `rho = 1.9545 kg/m3`. The values obtained are:

| Speed | Engine volumetric flow | Total mass flow, VE 0.85-1.00 | Mass flow per K16, kg/s | Mass flow per K16, lb/min |
| ---: | ---: | ---: | ---: | ---: |
| 4,500 rpm | `0.1350 m3/s` | `0.224-0.264 kg/s` | `0.112-0.132` | `14.8-17.5` |
| 5,750 rpm | `0.1725 m3/s` | `0.287-0.337 kg/s` | `0.143-0.169` | `19.0-22.3` |
| 6,720 rpm | `0.2016 m3/s` | `0.335-0.394 kg/s` | `0.168-0.197` | `22.2-26.1` |

Mass flow is conserved through the circuit, but volumetric flow and density
change before and after the compressor. The 50/50 split is a starting
assumption: left and right lengths, losses, wastegates and efficiencies can
make it wrong.

For a first estimate of the pressure ratio:

- with no loss between compressor and manifold: `PR = 1.813 / 1.013 = 1.79`;
- with a provisional loss of `0.05-0.20 bar` in the charge circuit: `PR`
  becomes about `1.84-1.99`.

The `0.05-0.20 bar` loss is a sensitivity range, not a Porsche measurement.
With `T1 = 20 degrees C`, an assumed compressor efficiency of `0.65-0.75` and
`gamma = 1.4`, the calculated compressor outlet temperature is about
`91-117 degrees C`. With an assumed intercooler effectiveness of `0.60-0.75`,
the post-intercooler temperature would be about `38-59 degrees C`. These
numbers must not replace a sensor before/after the intercooler.

## Relation to the current OpenFOAM case

The case
`simulation/993-k16-cold-side-baseline/` is a regression harness:

- equivalent rectangular diffuser `50 -> 68 mm` over `90 mm`;
- imposed density `1.2 kg/m3`;
- imposed velocity `40 m/s`;
- derived mass flow `0.09425 kg/s`;
- no wheel, CHRA, wastegate, real intercooler or K16 geometry.

This mass flow is deliberately synthetic and sits below the per-K16 envelope
calculated under the assumptions above. It must not be replaced silently: it
serves to verify the OpenFOAM chain and the relative comparisons. The next
physical case will have to impose a justified per-bank mass flow and a geometry
whose sections are known.

Three sensitivity variants are now materialized in
`simulation/993-turbo-variants/`: `K16-OEM`, `K16-24-HYBRID` and
`K24-REFERENCE`. They use the same derived mass flow of `0.156 kg/s` per turbo,
at constant density, so as to compare only synthetic cold envelopes. Inlet
velocities change with the section. The manifest attaches the FVD, Cargraphic,
TTP, TTH, Elferwelt and 9ff sources, but the tuners' power targets remain
declarations outside the solver. The files can be regenerated with
`make turbo-variants` and are checked by `make turbo-variants-check`.

## What is missing before a calibrated CFD

### Geometry

- licensed scan or CAD of the right and left turbo;
- flange drawings, axes, center distances and common datums;
- inside diameters and radii of the OEM hoses;
- geometry of the intercooler housings, fins, core density and dead volumes;
- throttle, manifold, plenum and intake sections;
- complete profiles of the wheels and diffusers.

### Operation

- boost/speed curve and pressure before/after each intercooler;
- HFM mass flow and its calibration;
- ambient temperature, post-compressor and post-intercooler temperature;
- compressor/turbine efficiency and shaft speed;
- turbine inlet pressure, T3 temperature, back pressure;
- wastegate opening law and transient behavior;
- surge/choke limits and fatigue data.

### Validation

The minimum test bench will have to measure simultaneously mass flow, pressure
and temperature before/after each K16 and each intercooler. The points must be
repeated, the instruments and uncertainties recorded, then compared with the 0D
network and the 3D CFD. A photo, a PET exploded view or a vendor sheet does not
replace this bench.

## Simulation strategy

1. **0D/1D network**: sweep speed, VE, boost, temperature, efficiency and
   pressure loss. The [BorgWarner MatchBot](https://www.borgwarner.com/aftermarket/boosting-technologies/performance-turbochargers/matchbot)
   serves as a reference for the input/output variables, but does not provide
   the missing K16 map.
2. **Cold-side CFD**: first calculate a duct, an elbow, a fitting or an
   intercooler whose geometry is accessible and licensed. Compare pressure
   loss, velocity uniformity and separation.
3. **Thermal**: add the intercooler and its surroundings with measured or
   explicitly swept temperatures/coefficients.
4. **Complete K16**: only after obtaining a map or test points and an
   authorized wheel geometry. A simulation without a map will produce an image
   or an extrapolation, not a credible prediction.
5. **Manufacturing**: the turbo, the wheel, the shaft, the CHRA and the hot-side
   housing remain blocked by the catalogue safety class. The first object must
   remain a cold duct or adapter, non-rotating and non-structural.

## Recorded sources

- `SRC-PORSCHE-CHRISTOPHORUS-993-TURBO-DATA`
- `SRC-PORSCHE-AUSTRIA-993-107-45-PET`
- `SRC-PORSCHEFANATICS-993-TURBO-PET`
- `SRC-BORGWARNER-993-K16-PERFORMANCE-CATALOG`
- `SRC-BORGWARNER-MATCHBOT-993-INPUTS-OUTPUTS`
- `SRC-TURBOMAP-COMPRESSOR-MAP-METHODOLOGY`
- `SRC-TURBOMASTER-993-K16-6735-PARTS`
- `SRC-INVASIONAUTOPRODUCTS-993-K16-INTERNAL-DATA`
- `SRC-FVD-993-K16-OEM-DIMENSIONS`
- `SRC-ELFERCLASSIC-993-TURBO-TECHNICAL-DATA`
- `SRC-WS-AUTOTEILE-993-MAF-IDENTIFICATION`
- `SRC-PFF-993-BITURBO-VARIANT-FORUM`
- `SRC-CARPASSION-993-TURBO-BOOST-HOSE-FORUM`
- `SRC-MOTOR-TALK-993-TURBO-FORUM-TECHNICAL-LEADS`
- `SRC-FVD-993-K16-24-SPORT-TURBO-DATA`
- `SRC-CARGRAPHIC-993-K16-24-POWERKIT-DATA`
- `SRC-CARGRAPHIC-993-MOTORSPORT-INTERCOOLER-DATA`
- `SRC-TTP-993-TURBO-TUNING-STAGES`
- `SRC-ELFERWELT-993-K16-8055011W-KIT`
- `SRC-TTH-993-K24-750-TURBO-PROCESSING`
- `SRC-9FF-993-F64-K24-550-DATA`
- `SRC-RENNLIST-993-RUF-TURBO-R-ENGINE-DYNO`
- `SRC-RENNLIST-993-K16-K24-COMPARATIVE-ENGINE-DYNO`
- `SRC-RENNLIST-993-POWERHAUS-K24-DYNO`
- `SRC-RENNLIST-993-K16-CHASSIS-DYNO`
- `SRC-AP-CAR-DESIGN-993-K26-DYNO-REPORT`
- FVD, AKS DASIS and TA Technix sources for the adjacent parts.
