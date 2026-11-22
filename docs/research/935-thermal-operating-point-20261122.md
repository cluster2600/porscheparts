# A published operating point for the 935 head's thermal model

Search of 22 November 2026, for issue #702. **Nothing here is a measurement
of the scanned head or of a 935 engine.** Each value is a published value of
another engine, with its source, how it was read and how far it is from this
head. The values used by the correlation are declared as hypothesis H16 in
the twin's [register](../../twins/935-cylinder-head-cad-twin/hypotheses.json);
the correlation rule is in the
[contract](../../twins/935-cylinder-head-cad-twin/params/thermal-correlation-contract.json),
committed before any solve.

## What was looked for

A head temperature with its sensor position at one stated operating point
(speed, load, boost, cooling-air state) for the Porsche 930, 934 or 935, or
any air-cooled 911 head; and, for the same point, the cooling-air flow, the
oil temperature and the share of heat taken by air and oil. The earlier
passes ([literature](../../twins/935-cylinder-head-cad-twin/params/thermal-literature-bounds.json),
[valve train, fatigue, port flow](935-head-published-data-20261116/README.md))
had found none.

## Verdict

No head temperature of a 911, 930, 934 or 935 engine at a stated operating
point could be opened. The pages that hold 911 readings, mostly forum threads,
refuse automated readers, and the factory and engineering papers that would
hold them are behind paywalls. The closest complete published data with a
sensor position are NACA's measurements on air-cooled aircraft cylinders:
power, speed, manifold pressure, cooling-air state and the temperature under
the rear spark plug, public domain. The correlation uses one NACA table
through hypothesis H16, and says how far it is from this head.

## Values used

Every value below was read in the downloaded report, then read a second time
in a page image rendered from the same file (the OCR text of these scans
drops and mangles table cells). The files stay outside Git; their SHA-256 is
in the contract.

| Source | Value | Where | Sensor position | Second reading |
|---|---|---|---|---|
| [NACA MR E5G09](https://ntrs.nasa.gov/api/citations/19930093593/downloads/19930093593.pdf) (Werner, Blackman, White, July 1945) | normal rated power: 2600 rpm, 42.7 in. Hg abs., 1100 bhp (nominal), automatic rich, cowl flaps 1/4 to 1/3 open; manufacturer's head limit 450 °F; predicted maximum 440 °F | Table I, p. 21 | "Rear-spark-plug-gasket temperatures T12" (footnote a) | re-read |
| same | military power: 2800 rpm, 50.8 in. Hg abs., 1350 bhp, automatic rich, cowl flaps 1/3 open; limit 500 °F; predicted maximum 456 °F | Table I | T12 | re-read |
| same | take-off: 2800 rpm, 52.0 in. Hg abs., 1350 bhp, automatic rich, cowl flaps 1/4 to 1/3 open; limit 500 °F; predicted maximum 543 °F | Table I | T12 | re-read |
| same | "Calculations for take-off power and normal landing approach based on sea-level pressure altitude and cooling-air and carburetor-air temperatures of 100° F. Other operating conditions based on pressure altitude of 7000 feet and cooling-air and carburetor-air temperatures of 60° F." | Table I, footnote e | | re-read |
| same | "an R-1830-94 engine mounted in the left inboard nacelle of a B-24D airplane"; "normal rated power of 1100 brake horsepower at 2600 rpm and a take-off power of 1350 brake horsepower at 2800 rpm" | p. 2 | | read once |
| same | "The rear-spark-plug-gasket thermocouple T12 and the cylinder rear-hold-down-flange thermocouple T14 were used to determine temperature limits in accordance with the manufacturer's specifications." | p. 3 | the head analysis itself used 14 thermocouples embedded 30% of the metal thickness into the rear spark-plug bosses | read once |
| [NACA Report 612](https://ntrs.nasa.gov/api/citations/19930091688/downloads/19930091688.pdf) (Pinkel, 1938) | equation (19), Pratt & Whitney 1340-H head: the gas-side term goes as the indicated horsepower to the power 0.64 (0.68 for the 1535 head) | p. 14 | average of 22 head thermocouples | re-read |
| [NACA Report 645](https://ntrs.nasa.gov/api/citations/19930091720/downloads/19930091720.pdf) (Schey, Pinkel, Ellerbrock, 1938) | "It is the practice at present to use the temperature of the rear spark-plug gasket as the index of the cooling of a cylinder." | p. 19 | rear spark-plug gasket | re-read |
| same | "In a multicylinder engine, variations of as much as 50° F. occur between the maximum temperatures of the various cylinders." | p. 19 | | re-read |
| same | the rear spark-plug gasket temperature "may at times give incorrect indications of the cooling of a cylinder" | p. 19 | | re-read |
| [Porsche newsroom, turbo motorsport press kit](https://newsroom.porsche.com/en/press-kits/50-years-porsche-turbo/Porsche-and-turbo-technology-in-motorsport--from-pioneer-to-world-champion.html) | "the 935 was launched in 1976 with a 2.85-litre single-turbo engine and 434 kW (590 PS)" | | | read once; the same figure is in the [935 cooling research](../../twins/935-horizontal-cooling-system/research/CONSOLIDATED_REPORT.md) |

All three NACA records carry the NTRS determination "GOV_PUBLIC_USE_PERMITTED";
`ntrs.nasa.gov/robots.txt` allows every agent. The Porsche press text is quoted
in a few words only. All pages were accessed on 2026-11-22.

Conversions made here, not published: 440 °F = 226.7 °C, 456 °F = 235.6 °C,
543 °F = 283.9 °C, 450 °F = 232.2 °C, 500 °F = 260.0 °C, 60 °F = 15.6 °C,
100 °F = 37.8 °C, 50 °F of difference = 27.8 K.

## How far this is from the 935 head

Computed here from the figures above:

| | R-1830-94, normal rated | Porsche 935, 1976 |
|---|---|---|
| cylinders, displacement | 14, 1830 cubic inches by designation (30.0 l), 2.14 l per cylinder | 6, 2.85 l, 0.475 l per cylinder |
| power per cylinder | 78.6 bhp, 58.6 kW | 72.3 kW |
| power per litre | 27.4 kW/l | 152 kW/l, about 5.6 times as much |
| cooling | ram air through a cowling with flaps, in flight | an engine-driven fan in a shroud |
| temperature quoted | predicted maximum of 14 cylinders, from NACA's cooling correlation of one measured flight | none published |

The two heads share the type, an air-cooled finned aluminium head with two
valves and two spark plugs, and nothing else. A 2.85-litre six with the 70.4 mm
stroke of the 930 Turbo (FIA form 3076, in the earlier search) needs a bore of
92.8 mm, which is the twin's fitted chamber shoulder (92.80 mm): arithmetic, not
evidence of the specimen's engine.

## 911-family values that were opened, and why none is an operating point

| Source | What it gives | Why it is not used as the operating point |
|---|---|---|
| 993 workshop manual, [OCR extraction in this repository](../../catalog/manual/993-workshop-manual-measurements.json) (unreviewed) | "Cylinder head temperature > 80 °C (> 176 °F)" (PDF p. 1269) and "the cylinder head temperature is > 95° C." (p. 1234), as conditions of the DME diagnosis | thresholds of a diagnosis at the factory sensor, no load or speed |
| [Wikipedia, Porsche PFM 3200](https://en.wikipedia.org/wiki/Porsche_PFM_3200) | the 911-based aircraft engine; N03 "162 kW (217 hp) at 5300 rpm" | gives no temperature |
| [Aircraft Engine Historical Society, Porsche](http://www.enginehistory.org/Piston/HOAE/Porsche.html) | "US TC = E23NE (8/30/85); LBA TC = 4602" for the PFM 3200 N03 | the type certificate data sheet and the operator's manual, which should state a head-temperature limit and its sensor position, could not be found as files |
| [SAE 850895 abstract](https://saemobilus.sae.org/papers/porsche-aircraft-engine-p-f-m-3200-850895) (Bott, Dorsch, 1985) | "The engine is cooled by an engine-driven fan which functions proportionally to power output." | the full paper is paywalled |

## Leads that were not opened

Numbers seen only in search excerpts are not written here.

- Hans Mezger, "The development of the Porsche Type 917 car", Proc. IMechE 186
  (1972): a copy on a forum host returned HTTP 403. A search excerpt says it
  compares engine temperatures and blower power with earlier racing engines.
- Hans Mezger, SAE 780718, "Turbocharging engines for racing and passenger
  cars" (1978): paywalled. The most likely published source of 934 and 935
  head temperatures.
- Bott and Dorsch, SAE 850895: paywalled.
- FAA type certificate data sheet E23NE and LBA type certificate 4602 of the
  PFM 3200: not found as openable files. EASA revoked the LBA certificates in
  2008 (search excerpt of an EASA notice, not opened).
- Owner readings at the factory head-temperature sensor of the 964 and 993 (on
  cylinder 3, by the sellers' product names), and a limit at the rear plug
  flange of a boosted 911: forum threads on hosts that refuse automated
  readers.
- A thermal-imager study of an air-cooled motorcycle head (Tang et al., 2017):
  the publisher returned HTTP 403.

Hosts that refused or failed, left alone ([decision 0003](../decisions/0003-no-vendor-harvesting.md)):
rennlist.com, forums.pelicanparts.com, forums.linkecu.com (403),
mooneyspace.com (403), hagerty.com (403), journals.sagepub.com (403),
acurazine.com (403), kfz-tech.de (429, too many requests), stuttcars.com
(members only past the introduction), seqair.com (certificate for another
host), porscheplanes.com (no address), porscheaviation.com (redirects to an
unrelated shop).

## What would replace H16

In order of value, each through a registered source or a contributor
([decision 0019](../decisions/0019-accept-contributed-measurements.md)):

1. a head temperature of a 930, 934 or 935 at a logged speed, boost and
   cooling-air state, with the sensor position on the head;
2. the PFM 3200 type certificate data sheet or operator's manual: a 911 head
   with a certified head-temperature limit at a stated position and power;
3. a logged reading of the 964 or 993 factory head sensor at a stated speed and
   load, with the sensor's position on cylinder 3;
4. Mezger's SAE 780718 or IMechE 1972 paper.
