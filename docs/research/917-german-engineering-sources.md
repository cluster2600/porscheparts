# German engineering sources — Porsche 917 engine

## Scope

This note lists only German-language pages consulted on September 1, 2026. It
separates published facts, reconstruction hypotheses and data still missing. No
text, drawing, photograph, PDF or mesh from these publishers is copied into the
repository.

Evidence levels used: **A** = Porsche publication or manufacturer data;
**B** = identified specialist or engineer; **C** = uncorroborated secondary
technical source; **D** = lead to verify. A published value is not, for all
that, a manufacturing dimension.

## Claims matrix

| Paraphrased claim | Variant | Value / unit | Source | Level | Rights | Authorized use in the twin | Contradictions or caveat |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Declared engine architecture | 917/30 | 180° V, 12 cylinders, turbo, 5,374 cm³ | [Porsche Museum](https://newsroom.porsche.com/de/pressemappen/Porsche-Museum/Porsche-917-30-Spyder.html) | A | Porsche copyright, reference only | USD tree, BOM and functional envelope | "180° V" is not enough to prove boxer kinematics; keep the published topology |
| First production displacement | 917, 1969 | 4,494 cm³; bore 85 mm; stroke 66 mm; 580 PS | [auto motor und sport](https://www.auto-motor-und-sport.de/oldtimer/porsche-917-motor-kraftwerk-ohne-gleichen/), displacement and power corroborated by [Porsche](https://newsroom.porsche.com/de/2019/unternehmen/porsche-917-50-jahre-goodwood-members-meeting-2019-17461.html) | B for the dimensions, A for displacement/power | Copyright, reference only | Scale check of the cylinders and stroke parameter | Do not mix with the 5-liter or with the 917/30 |
| Naturally aspirated evolution | 917 5-liter | 4,999 cm³; 86.8 × 70.4 mm; compression 10.5:1; 630 PS at 8,300 min⁻¹ | [auto motor und sport](https://www.auto-motor-und-sport.de/oldtimer/porsche-917-motor-kraftwerk-ohne-gleichen/) | B | Copyright, reference only | Piston and stroke parameters and first load case | Secondary data; chamber details remain unknown |
| Can-Am evolution | 917/30, 1973 | 5,374 cm³; 90 × 70.4 mm; compression 6.5:1; 1,100 PS at 7,800 min⁻¹; 112 mkg at 6,400 min⁻¹, i.e. about 1,098 N·m | [auto motor und sport](https://www.auto-motor-und-sport.de/oldtimer/porsche-917-motor-kraftwerk-ohne-gleichen/) | B | Copyright, reference only | Piston/stroke parameters and mechanical load | Power depends on boost and tuning; the conversion to N·m is computed, not quoted |
| Race power and record version | 917/30 | 1,100 PS at 7,800 min⁻¹; 1975 record version with intercoolers: 1,230 PS | [Porsche, "Am Limit"](https://newsroom.porsche.com/de/motorsport/porsche-919-hybrid-evo-917-30-canam-spyder-timo-bernhard-mark-donohue-rennwagen-16319.html) | A | Porsche copyright, reference only | Separate the 1973 and 1975 load profiles | Other Porsche pages state 1,200 PS or "more than 1,200 PS"; do not merge the tunings |
| Cylinder head studs | 917 engine presented for 1970 | 48 pieces; length 149.5 mm; shank Ø 9 mm; mass 65 g each | [Porsche Christophorus](https://christophorus.porsche.com/de/2019/390/le-mans-1970-hans-mezger-17024.html) | A | Porsche copyright, reference only | Best public scale check; case–cylinder–cylinder head interface and BOM mass | Verify physically before extending to the 917/30 |
| Stud material and insulation | 917 | Dilavar steel alloy; insulating sleeve of glass fiber and resin | [Porsche Christophorus](https://christophorus.porsche.com/de/2019/390/le-mans-1970-hans-mezger-17024.html) | A | Porsche copyright, reference only | Thermomechanical model and relative expansions | Exact grade, properties and process not published |
| Case, cylinders and connecting rods | 917 | Sand-cast magnesium case; individual Nikasil-coated cylinders; titanium connecting rods | [auto motor und sport, interview with Hans Mezger](https://www.auto-motor-und-sport.de/oldtimer/porsche-917-motor-kraftwerk-ohne-gleichen/) | B | Copyright, reference only | Provisional material assignments, mass and thermal | Alloys, treatments and geometries not published; no material may be released for manufacturing on this source alone |
| Valvetrain and ignition | Type 912 / 917 | Two camshafts per bank; two inclined valves and two spark plugs per cylinder; central gear drive | [auto motor und sport](https://www.auto-motor-und-sport.de/oldtimer/porsche-917-motor-kraftwerk-ohne-gleichen/) | B | Copyright, reference only | Kinematics of the camshafts, valves, gears and ignition | The four-valve Type 922 is a distinct concept and must not replace the historical configuration |
| Crankshaft and power take-off | 917 | Eight plain bearings; central power take-off | [auto motor und sport](https://www.auto-motor-und-sport.de/oldtimer/porsche-917-motor-kraftwerk-ohne-gleichen/) | B | Copyright, reference only | Breakdown of the crankshaft, the case halves and the transmission | Lengths, diameters and offsets remain unknown |
| Declared firing order | 917 | 1-9-5-12-3-8-6-10-2-7-4-11 | [auto motor und sport](https://www.auto-motor-und-sport.de/oldtimer/porsche-917-motor-kraftwerk-ohne-gleichen/) | B | Quoted technical fact; protected article | Animation, cylinder excitation and acoustics | The numbering convention must be confirmed by an original drawing |
| Lubrication | 917 | Dry sump; one pressure pump and six scavenge pumps; announced capacity 24 l | [auto motor und sport](https://www.auto-motor-und-sport.de/oldtimer/porsche-917-motor-kraftwerk-ohne-gleichen/) | B | Copyright, reference only | Functional oil schematic, thermal and BOM | The 55 l tank published for a 917 KH corresponds to a distinct component/vehicle variant |
| Air cooling | 917 | Announced fan flow rate: 3,100 l/s | [auto motor und sport](https://www.auto-motor-und-sport.de/oldtimer/porsche-917-motor-kraftwerk-ohne-gleichen/) | B | Copyright, reference only | First volumetric boundary condition for a sensitivity study | Pressure–flow curve, speed, leakage and per-cylinder distribution missing |
| Candidate cylinder spacing and valve diameters | Type 912 | Cylinder spacing 118 mm; intake Ø 47.5 mm; exhaust Ø 40.5 mm | [Kfz-tech](https://www.kfz-tech.de/Buchprojekte/Porsche/917Teil2.htm) | C | Copyright, reference only | Scale-check and cylinder head reconstruction hypotheses | No primary corroboration found: do not lock the CAD on these values |
| Candidate valve timing | Type 912 | Intake: opens 104° before TDC, closes 104° after BDC; exhaust: opens 105° before BDC, closes 75° after TDC | [Kfz-tech](https://www.kfz-tech.de/Buchprojekte/Porsche/917Teil2.htm) | C | Copyright, reference only | First parametric valve animation | Convention and checking clearance not published; unfit for a definitive collision validation |
| Mechanical injection | 917 | Bosch system; pressure published by the secondary source: 17.5 bar | [auto motor und sport](https://www.auto-motor-und-sport.de/oldtimer/porsche-917-motor-kraftwerk-ohne-gleichen/) and [Kfz-tech](https://www.kfz-tech.de/Buchprojekte/Porsche/917Teil2.htm) for the pressure | B for the architecture, C for the pressure | Copyright, reference only | Fuel BOM and initial 1D model | Pump cam, flow rates and speed/load law unknown |
| Historical forced induction | 917/10 and 917/30 | Two turbochargers with a bypass valve; supplier historically attributed to Eberspächer | [Porsche, "Turbo-Vision"](https://newsroom.porsche.com/de/2024/historie/porsche-turbotechnologie-motorenbau-vision-christophorus-411-36722.html) for the architecture; [Classic Driver](https://www.classicdriver.com/de/article/porsche-sound-nacht-m%C3%A4nner-motoren-manierismen) for Eberspächer | A for the architecture, B for the supplier | Copyright, reference only | Turbo bill of materials, manifolds and boost control | No credible German evidence found for KKK/K26; model and maps of the Eberspächer turbo unknown |
| Published boost pressure | 917/30 | 1.3 bar | [auto motor und sport](https://www.auto-motor-und-sport.de/oldtimer/porsche-917-motor-kraftwerk-ohne-gleichen/) | B | Copyright, reference only | Exploratory test point only | Absolute or gauge pressure not specified: do not use it as a definitive boundary condition |
| Transient response and documented failure | 1971–1972 turbo prototypes | About one second before power builds; test of October 27, 1971 stopped by valves left hanging open | [Porsche, "Mission 917"](https://christophorus.porsche.com/de/2021/401/weissach-917.html) | A | Porsche copyright, reference only | Qualitative spool target and FMEA scenario | Historical account, not an instrumented curve |
| Boost control by the driver | 917/30 | Boost raised at the start then reduced for engine life and fuel consumption | [Porsche, "Am Limit"](https://newsroom.porsche.com/de/motorsport/porsche-919-hybrid-evo-917-30-canam-spyder-timo-bernhard-mark-donohue-rennwagen-16319.html) | A | Porsche copyright, reference only | Mission controller in Omniverse | Control positions and associated pressures unknown |
| Contemporary validation of a recreated engine | Functional 917 replica | EGT and cylinder head temperature per cylinder; fast automatic shutdown; mapping of fuel demand on the dyno | [Herrmann Motorenentwicklung](https://herrmann-motorenentwicklung.de/porsche-917-eine-ikone-des-motorsports-auf-unserem-pruefstand/) | B | Copyright, reference only; collaboration required | Instrumentation architecture, dyno and correlation plan | No numerical measurement series is published |
| Porsche reconstruction method | 917-001 | Disassembly, 3D scan, surface reconstruction and comparison with the construction drawings before tooling is made | [Porsche Museum](https://newsroom.porsche.com/de/2019/historie/porsche-917-001-rueckbau-restaurierung-museum-17524.html) | A | Porsche copyright, reference only | Justifies the chain scan → surfaces → original dimensions → check | The page mainly concerns the body; it validates a method, not the engine dimensions |
| Porsche additive validation reference | Modern 911 GT2 RS piston | LMF/LPBF in aluminum alloy; mass reduced by 10 %; closed cooling channel; 200 h engine test | [Porsche Newsroom](https://newsroom.porsche.com/de/2020/technik/porsche-kooperation-mahle-trumpf-kolben-3d-drucker-leistung-effizienz-911-gt2-rs-21461.html) | A | Porsche copyright, reference only | Qualification model for a future printed part | Demonstrates neither the manufacturability nor the safety of a 917 piston |

## Contradictions to keep as variants

- Depending on the Porsche page, the 917/30's power appears as 1,100 PS,
  1,200 PS, more than 1,200 PS or 1,230 PS. The model must therefore separate at
  least the 1973 race tuning and the 1975 record tuning with intercoolers.
- The 24 l of oil published for the engine and the 55 l tank described on a
  917 KH are not two interchangeable measurements.
- The KKK designation found in later sources must not be applied to the
  historical 917/30 without evidence. The German sources retained point to
  Eberspächer, but give neither a part reference nor a turbo map.
- Titanium exhaust valves are not established by a primary German source. The
  titanium connecting rods are better documented, but their grade and treatment
  remain unknown.
- A 1,600 hp concept engine must remain a non-historical variant, separate from
  the documented 917/30.

## Data still missing

The public sources consulted do not provide:

- the dimensioned engine envelope and the joint planes;
- the crankshaft length, the main/crankpin journal diameters and their offsets;
- the connecting rod center distance, the pin dimensions and the fastener
  details;
- the complete cylinder head fastening pattern, beyond the number and outer
  dimension of the studs;
- the chambers, ports, fins and wall thicknesses;
- the exact alloys, metallurgical tempers and heat treatments;
- the reference and compressor/turbine maps of the Eberspächer unit;
- the gallery diameters, clearances, flow rates and pump curves;
- a complete Porsche bill of materials with part numbers.

These fields must remain `unknown` or `provisional`. They can be completed only
with authorized Porsche drawings, calibrated metrology/CT of a legally
accessible engine, or a documented collaboration with an engine builder. The
[Porsche Archiv](https://pnr-prd2-pub2.newsroom.porsche.com/de/pressemappen/Porsche-Museum/Archiv-und-Sammlung.html)
is the lawful route to favor for historical drawings.

## Reuse

The [Porsche Newsroom terms](https://newsroom.porsche.com/de/bilder-media/videos/porsche-newsroom-nutzungshinweise.html)
reserve texts, images, videos and other media for regulated uses. The other
publishers consulted display no open license for their content. The repository
therefore keeps only provenance records and paraphrased facts; no media,
drawing or model from these pages may be redistributed.
