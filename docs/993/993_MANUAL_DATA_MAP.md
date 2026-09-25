# Technical map of the 993 manual

This document links the structured data of the Porsche Fanatics project to the
reverse-engineering catalogue. We have neither a vehicle nor a donor part. The
numbers below are therefore specifications published in the workshop manual,
not measurements taken by this project and not CAD dimensions.

## Access and provenance

- [993 procedure index](https://porschefanatics.com/993/manual/): 235
  repair-number and page entries.
- [Technical data](https://porschefanatics.com/993/technical-data/): 111
  values extracted from the technical data sheets.
- [Tightening torques](https://porschefanatics.com/993/torques/): 195 rows
  spread across the tables of each repair group.
- Reference source of the catalogue: `SRC-PORSCHE-WORKSHOP-MANUAL-993`.
- Bridge to the public index and its extractions:
  `SRC-PORSCHEFANATICS-993-MANUAL-DATA`.
- [Exhaustive register of quantitative values](../../catalog/manual/993-workshop-manual-measurements.json):
  2,496 records, of which 2,190 occurrences come from the OCR'd procedures.

The PDF file consulted locally is not added to the repository. The Porsche
Fanatics project keeps its extractions to allow search and traceability, but
they do not replace the authorized copy of the manual. The public pages also
state that the procedures, warnings and exploded views must be read in the
manual.

## Where to look for part information

| Family | Manual area | Use for the catalogue |
|---|---|---|
| Engine and valve train | groups 10–15, notably p. 15, 98, 108, 121, 137, 152–157, 177 | specifications, clearances, wear limits and inspection methods |
| Manual transmission | group 3, p. 253–258 | G50 variants, ratios, capacities and mounting torques |
| Carrera 4 transmission | group 3, p. 354 onward | G64 identification and procedure specific to all-wheel drive |
| Chassis and steering | groups 4–5 | procedures and torques; no manufacturing geometry on its own |
| Brakes | group 46, p. 725–728 | variant data and service limits; never an authorization to manufacture |
| Body and interior | groups 51–68 | identification, removal and installation; generally no dimensioned drawings |
| Heating and air conditioning | group 87 | procedures and identification of subassemblies |
| Electrical | groups 90–97 | identification and procedures, without extrapolating connector geometry |

## Useful values already checked in the PDF

### Vehicle and powertrain — Carrera 993

PDF page 15, "Technical data" sheet:

| Item | Printed value | Variant / remark |
|---|---:|---|
| Cylinders | 6 | Carrera 993 |
| Bore | 100 mm | M64/05 manual and M64/06 Tiptronic |
| Stroke | 76.4 mm | same sheet |
| Actual displacement | 3,600 cm³ | same sheet |
| Compression ratio | 11.3:1 | same sheet |
| EEC power | 200 kW / 272 HP at 6,100 rpm | sheet declaration, not a project measurement |
| EEC torque | 330 Nm at 5,000 rpm | sheet declaration |
| Manual transmission weight | 232 kg | dry, ready to install, per the sheet heading |
| Tiptronic weight | 224 kg | same context |

PDF page 19, dimensions at DIN weight:

| Item | ROW | USA |
|---|---:|---:|
| Length | 4,245 mm | 4,260 mm |
| Width | 1,735 mm | 1,735 mm |
| Height | 1,300 mm | 1,315 mm |
| Wheelbase | 2,272 mm | 2,272 mm |
| Front track | 1,405 mm | 1,405 mm |
| Rear track | 1,444 mm | 1,444 mm |
| Ground clearance | 110 mm | 120 mm |
| Sport chassis — height | 1,285 mm | to be confirmed per variant |
| DIN curb weight | 1,370 kg | — |
| 70/156/EEC weight | 1,445 kg | — |
| Maximum permissible weight | 1,710 kg | 1,690 kg |
| Maximum front / rear axle load | 720 / 1,065 kg | Carrera table |

Length, height, ground clearance and maximum weight must therefore not be
merged into a generic "993" record.

### Engine internals and wear parts

These values are inspection limits from the manual. They are useful to define
a future metrology campaign or to check a model, but on their own they do not
define a printable part.

| Subject | Value | PDF page |
|---|---|---:|
| Crankshaft, main bearing diameter d1, standard | 59.971–59.990 mm | 98 |
| Crankshaft, connecting rod journal diameter d2, standard | 54.971–54.990 mm | 98 |
| Crankshaft, main bearing diameter d3, standard | 30.980–30.993 mm | 98 |
| Repair d1 / d2 / d3 | −0.25 or −0.50 mm depending on the column | 98 |
| Crankshaft flange d4 | 89.780–90.000 mm | 98 |
| Crankshaft flange wear | 89.580 mm | 98 |
| Timing gear fit d5 | 42.002–42.013 mm | 98 |
| Bearing diameter d6 / wear limit | 29.960–29.993 / 29.670 mm | 98 |
| Case bearing bore 1–8, standard | 65.000–65.019 mm | 98 |
| Case bearing bore 1–8, oversize | 65.250–65.269 mm | 98 |
| Intermediate shaft circumferential clearance, new | 0.035–0.084 mm | 137 |
| Wear limit of the circumferential clearance | 0.10 mm | 137 |
| Cylinder-piston installation clearance | 0.02–0.03 mm | 108 |

Piston/cylinder tolerance groups, page 108:

| Group | Cylinder Ø | Piston Ø |
|---:|---:|---:|
| 0 | 100.000–100.007 mm | 99.970–99.980 mm |
| 1 | 100.007–100.014 mm | 99.977–99.987 mm |
| 2 | 100.014–100.021 mm | 99.984–99.994 mm |
| 3 | 100.021–100.028 mm | 99.991–100.001 mm |

Guides and valves:

| Subject | Value | PDF page |
|---|---|---:|
| Guide inner bore after machining | 8.00–8.015 mm | 153 |
| Guide installation interference | 0.06–0.08 mm | 153 |
| Standard guide, stated outer diameter | 13.060 mm | 154 |
| First repair-size guide, stated outer diameter | 13.260 mm | 154 |
| Permissible guide rocking clearance, intake/exhaust | 0.80 / 0.80 mm | 152 |
| Intake valve, head a | 49 ± 0.1 mm | 155 |
| Intake valve, stem b | 7.970 − 0.012 mm | 155 |
| Intake valve, length c | 110.1 ± 0.1 mm | 155 |
| Exhaust valve, head a | 42.5 ± 0.1 mm | 155 |
| Exhaust valve, stems b1 / b2 | 7.950 − 0.012 / 7.970 − 0.012 mm | 155 |
| Exhaust valve, length c | 109 ± 0.1 mm | 155 |
| Intake / exhaust seat angle | 45° / 45° | 155 |
| Intake spring installed length M64/05–08 | 36.7 + 0.3 mm | 157 |
| Exhaust spring installed length M64/05–08 | 35.7 + 0.3 mm | 157 |
| Intake spring installed length M64/20 RS | 37.2 + 0.3 mm | 157 |
| Exhaust spring installed length M64/20 RS | 35.8 + 0.3 mm | 157 |

For the RS valves, the same page gives in parentheses the heads 51.5 mm
(intake) and 43.5 mm (exhaust), as well as the stem diameter variants. The RS
variant must be kept instead of replacing the Carrera value.

### Valve timing and alternator/fan belt

PDF page 177: the distance between the intermediate shaft face and the rear
sprocket is 98.07 mm for cylinders 1–3; the distance to the front sprocket is
43.27 mm for cylinders 4–6. The permissible camshaft sprocket position
deviation is ±0.25 mm. The printed example with A = 35.5 mm gives
133.57 ± 0.25 mm and 78.77 ± 0.25 mm.

PDF page 121:

- used belt: 15–23 graduations cold, 20–28 at operating temperature;
- new belt: 23–35 graduations cold, then 28–40 after about 15 minutes
  at idle or a 10-mile test drive;
- stated tool: Porsche 9574; shims 0.5 and 0.7 mm, the latter being
  identified by a 2 mm hole.

These graduations are specific to the instrument and are not millimeters.

### Manual transmission and associated torques

Pages 253–257 identify the G50/20 and G50/21 families for the Carrera and
G50/31, G50/32 and G50/33 for the Carrera RS. The printed final drive ratios
are 3.444 for both tables; the public Porsche Fanatics sheet shows the ratio
detail per family.

PDF page 258, examples to check against the repair group and the actual
transmission before any work: oil plugs M22×1.5 at 30 Nm, M8 nuts at 23 Nm,
M6 clamping plate at 10 Nm, M18×1.5 reversing light switch at 35 Nm and
M14×1.5 breather at 35 Nm. The complete table, which also includes the shaft
nuts, stays in the public index rather than being copied here.

### Brakes: data kept, manufacturing blocked

Pages 725–726 describe the Carrera 4; pages 727–728, the Carrera 4S
(Turbo-Look). Printed examples:

| Variant | Front/rear discs | New thickness front/rear | Wear limit front/rear |
|---|---|---|---|
| Carrera 4 | 304 / 299 mm | 32 / 24 mm | 30.0 / 22.0 mm |
| Carrera 4S Turbo-Look | 322 / 322 mm | 32 / 28 mm | 30.0 / 26.0 mm |

The Carrera 4 also carries the caliper piston diameters 2×44 + 2×36 mm at the
front and 2×30 + 2×28 mm at the rear; the Carrera 4S repeats these diameters
in the checked sheet. The printed runout limits are 0.05 mm for the disc,
0.04 mm for the hub and 0.09 mm for the installed disc.

These are service data for a safety component. They are not used to design a
caliper, a disc, a shim, a wheel carrier or any braking part in this project.
Any future part in this area requires professional review, calculations,
testing and documented regulatory validation.

## What these data allow now

1. Identify families and variants before requesting CAD or a donor part.
2. Define measurement plans: for example piston/cylinder, valve guide, timing
   gear and console elements.
3. Check a future scan or an acquired part against published values, without
   declaring the interface "fitted" before a direct measurement.
4. Prioritize non-critical interior parts, notably the 964/993 console tab
   listed by `SRC-PRINTABLES-964-993-CONSOLE-SWITCH-TAB`.

The register `catalog/measurements/MEAS-MANUAL-993-ALL.json` now contains the
2,496 indexed documentary specifications. They are not physical measurements
by the project: no part, no vehicle and no instrument was used. Instrumented
part sessions will stay separate and can be added once the raw readings are
available.
