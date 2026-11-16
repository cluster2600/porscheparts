# Published data for the 935 head twin: valve train, fatigue, port flow

Search of 16 November 2026. **Nothing here is a measurement of the scanned head,
a design value or an admitted input.** These are published values of other
heads and of test coupons, each with its source and how it was read. The
machine-readable record is [findings.json](findings.json); the twin's
[register](../../../twins/935-cylinder-head-cad-twin/params/prepared-work.json) says what each part still lacks.

## What the search gave

| Part | Found | Still missing |
|---|---|---|
| Valve train | valve sizes, lifts, timing and cam lobe dimensions of the production 930 Turbo, and the valve angles of the 964 Turbo 3.3, from two homologation forms | the cam of the 934 or 935, every spring figure, every mass |
| Fatigue | three room-temperature sets with their points or fit, two sets after ageing at 177 °C, three single strengths at 200 and 350 °C from abstracts | an S-N curve at the head's temperature with its points |
| Port flow | the port openings of the production head, the definition of the flow coefficient, two validated computations on other heads (6% and 8% from the bench) | any flow sheet of these heads |

## How it was read

Three search agents read public pages and documents. A host that refused
automated readers was left alone; they are listed at the end. Each value
carries a flag:

- **read in source**: the value was read in the document itself.
- **read off a graph**: the value was read off a figure, about two digits.
- **abstract only**: only the abstract could be opened.
- **seller declaration**: the maker's or seller's own statement.

The column *second reading* says whether the value was read again in the
saved copy before it was written here. That second reading restored two
failures missing from the first transcription of the Roveda table. The
copies stay outside Git; their SHA-256 is in the record.

## Valve train

The two forms describe production engines: the 930 Turbo 3.0 (form 3076) and
the 964 Turbo 3.3 (form B-298). Neither is the 934, the 935 or the scanned head.

| Quantity | Value | Unit | Source, field | Flag | Second reading |
|---|---|---|---|---|---|
| inlet valve, outside diameter | 49 | mm | [fia-3076](https://historicdb.fia.com/sites/default/files/car_attachment/1601075701/homologation_form_number_3076_group_3.pdf), item 161, page 10 | read in source | re-read |
| inlet valve, largest lift | 9.7 | mm | [fia-3076](https://historicdb.fia.com/sites/default/files/car_attachment/1601075701/homologation_form_number_3076_group_3.pdf), item 162 | read in source | re-read |
| exhaust valve, outside diameter | 41.5 | mm | [fia-3076](https://historicdb.fia.com/sites/default/files/car_attachment/1601075701/homologation_form_number_3076_group_3.pdf), item 171 | read in source | re-read |
| exhaust valve, largest lift | 8.9 | mm | [fia-3076](https://historicdb.fia.com/sites/default/files/car_attachment/1601075701/homologation_form_number_3076_group_3.pdf), item 172 | read in source | re-read |
| springs per valve | 2 | coil springs | [fia-3076](https://historicdb.fia.com/sites/default/files/car_attachment/1601075701/homologation_form_number_3076_group_3.pdf), items 163, 164, 173, 174 | read in source | re-read |
| clearance at which the timing is stated ('theoretical timing clearance') | 0.1 | mm | [fia-3076](https://historicdb.fia.com/sites/default/files/car_attachment/1601075701/homologation_form_number_3076_group_3.pdf), items 165, 175 | read in source | re-read |
| inlet opens / closes | 3 / 37 | degrees after top dead centre / after bottom dead centre | [fia-3076](https://historicdb.fia.com/sites/default/files/car_attachment/1601075701/homologation_form_number_3076_group_3.pdf), items 166, 167 | read in source | re-read |
| exhaust opens / closes | 29 / 3 | degrees before bottom dead centre / before top dead centre | [fia-3076](https://historicdb.fia.com/sites/default/files/car_attachment/1601075701/homologation_form_number_3076_group_3.pdf), item 176 and the item after it, numbered 167 a second time on the form | read in source | re-read |
| inlet cam lobe S / T / U | 22.25 / 15.75 / 31.5 | mm, each ± 0.2 | [fia-3076](https://historicdb.fia.com/sites/default/files/car_attachment/1601075701/homologation_form_number_3076_group_3.pdf), item 205, page 11 | read in source | re-read |
| exhaust cam lobe S / T / U | 21.73 / 15.75 / 31.5 | mm, each ± 0.2 | [fia-3076](https://historicdb.fia.com/sites/default/files/car_attachment/1601075701/homologation_form_number_3076_group_3.pdf), item 205, page 11 | read in source | re-read |
| smallest diameter of the inlet pipe | 1.259 | in | [fia-3076](https://historicdb.fia.com/sites/default/files/car_attachment/1601075701/homologation_form_number_3076_group_3.pdf), item 192, page 11 | read in source | re-read |
| bore x stroke, compression ratio | 95 / 70.4 / 6.5 | mm, mm, to 1 | [fia-3076](https://historicdb.fia.com/sites/default/files/car_attachment/1601075701/homologation_form_number_3076_group_3.pdf), items 65, 67, 139 | read in source | not re-read |
| camshafts, drive, valve operation | 2 overhead camshafts, chain, rocker arms, 4 bearings per shaft |  | [fisa-b-298](https://historicdb.fia.com/sites/default/files/car_attachment/1479168902/homologation_form_number_298_group_b.pdf), item 325, page 8 | read in source | re-read |
| inlet / exhaust valve, largest diameter | 49 / 41.5 | mm | [fisa-b-298](https://historicdb.fia.com/sites/default/files/car_attachment/1479168902/homologation_form_number_298_group_b.pdf), items 327 d, 328 e, page 8 | read in source | re-read |
| valve stem in the guide, inlet and exhaust | 9 | mm, ± 0.2 | [fisa-b-298](https://historicdb.fia.com/sites/default/files/car_attachment/1479168902/homologation_form_number_298_group_b.pdf), items 327 e, 328 f | read in source | re-read |
| valve length, inlet / exhaust | 110.1 / 108.4 | mm, each ± 1.5 | [fisa-b-298](https://historicdb.fia.com/sites/default/files/car_attachment/1479168902/homologation_form_number_298_group_b.pdf), items 327 f, 328 g | read in source | re-read |
| angle between valve and vertical, inlet / exhaust | 25.5 / 30.25 | degrees (25°30′ and 30°15′ on the form) | [fisa-b-298](https://historicdb.fia.com/sites/default/files/car_attachment/1479168902/homologation_form_number_298_group_b.pdf), items 321 e, 321 f, page 5 | read in source | re-read |
| aftermarket cam: valve lift, advertised duration, duration at 0.050 in, lobe centre, lash | 0.445 / 290 / 268 / 103 / 0.004 | in, degrees, degrees, degrees, in | [webcam-233](https://webcamshafts.com/pages_vehicles/automobile/porsche_install_data/tc_000452_000591.html), timing card | seller declaration | not re-read |

Computed here from the form's figures, not published:

- cam lift, inlet / exhaust (S − T): 6.5 / 5.98 mm.
- base circle check, U − 2 T: 0 / 0 mm.
- rocker ratio implied, valve lift over cam lift, inlet / exhaust: 1.492 / 1.488 to 1 (arithmetic on the form's figures, not a published ratio; the form's tolerance of ± 0.2 mm on S and T moves it by about ± 0.09).
- opening period between the stated events, inlet / exhaust: 214 / 206 crank degrees (short for a period taken at the seat: what the 0.10 mm clearance means for the stated events is not explained on the form).

### The valve angles against the scan

| Quantity | Form B-298 | Scan fit | Difference |
|---|---|---|---|
| angle between the two valves | 55.75 | 55.763 | +0.013 degrees |
| valve_y_minus to the deck normal, against the inlet angle | 25.5 | 25.886 | +0.386 degrees |
| valve_y_plus to the deck normal, against the exhaust angle | 30.25 | 29.893 | -0.357 degrees |
| guide bore of valve_y_minus, against the stem diameter | 9 | 8.51 | -0.49 mm |

The angle between the two fitted axes equals the sum of the two published
angles within 0.02°. Each axis is about 0.4° from its published angle, in
opposite directions; the twin already found 0.42° between its two ways of
building a valve axis. The fitted guide bore is half a millimetre smaller than
the production stem, so this head does not take the production 9 mm valve;
the maker's catalogue lists 8 mm stems ([dossier](../935-faithful-replica-20261028/README.md)).

The form describes another head. The agreement does not calibrate the scan
and does not identify the inlet. It is one more indication that
`valve_y_minus` is the inlet, beside its larger seat; H09 stays open until a
specification or a marked photograph of the specimen says so.

**Not found:** a cam card of the 934 or 935; how the rocker ratio varies through the lift; the mass of a valve, retainer, keeper or rocker; spring installed height, seat load, open load, rate or coil-bind height in a page that could be opened; a stated engine speed limit of the 935 (8000 rpm appears only as the speed of peak power); valve sizes of the 934, the 935 or this maker's head beyond its catalogue ranges; seat and guide dimensions.

**Contradictions:** one article states a rocker ratio of 1.47; the form's lobe and lift figures imply about 1.49; a club forum post gives other timing for the 1974 engine (opening 20 and 50 degrees early) with no clearance stated; the form's events are at 0.10 mm.

**Leads that were not opened:** a parts seller's page with a racing spring kit's heights, loads and rate (the host answered 'too many requests' three times); the maker's and two tuners' pages on billet turbo heads (hosts refuse automated readers).

## Fatigue of printed AlSi10Mg

None of this is admitted as material data: the repository admits no fatigue
data ([tool guide](../../AGENT_TOOL_GUIDE.md)), and admitting any of it is a
decision this note does not take.

| Set | Condition | Loading | Result | Flag | Second reading |
|---|---|---|---|---|---|
| [roveda-2024](https://elib.dlr.de/207898/), Table 4 | as built, 265 °C / 1 h, 300 °C / 2 h; polished; vertical | axial, R = 0.1, 30 Hz, run-out 1e7, temperature not stated | 20 points below | read in source | re-read |
| [kramer-2025](https://publikationen.bibliothek.kit.edu/1000184850) | machined; vertical; heat treatment not found | rotating bending, R = −1, 50 Hz, run-out 1e7 | 60 MPa amplitude at 1e7; fit 507.7 · N^−0.14 | read in source | re-read |
| machine maker's sheet ([catalogue](../../../catalog/manufacturing/processes/eos-m290-alsi10mg-30um.json)) | turned; no heat treatment | fully reversed, temperature not stated | 110 MPa at 2e7 | read in source | not re-read |
| [nabil-2022](https://utw10945.utweb.utexas.edu/sites/default/files/2022/Effect%20of%20Thermal%20Aging%20in%20the%20Fatigue%20Life%20of%20Hot.pdf), Table 3 | hot isostatic pressing, aged at 177 °C, then machined | axial, R = 0.1, 50 Hz, room temperature | mean life at 124 MPa: 1.31 / 1.23 million cycles unaged (XY / Z), 0.02 / 0.01 million after 1000 h | read in source | re-read |
| [barrera-2025](https://utw10945.utweb.utexas.edu/sites/default/files/2025/38%20Study%20of%20Fatigue%20Endurance%20on%20Artificially%20Aged.pdf) | stress relief at 285 °C, or pressing and T6; aged at 177 °C; machined | axial, R = 0.1, 50 Hz, room temperature, run-out 5e6 | stress relieved at 124 MPa: 20 of 24 ran out at every ageing time; pressed and T6 at 145 MPa: all ran out to 100 h, mean 61,364 to 182,952 cycles at 1000 h | read in source | conditions only |
| [di-egidio-2023](https://doi.org/10.3390/met13020263) | T5 and rapid T6; polished | rotating bending, fully reversed | T5: 92 MPa at room temperature, 78 MPa at 200 °C; rapid T6: 108 and 92 MPa | abstract only | re-read |
| [bahl-2026](https://impact.ornl.gov/en/publications/strain-rate-hardening-enhances-fatigue-resistance-of-alsi10mg-all/) | not in the abstract | 350 °C, 20 Hz | 30 MPa at 1e7 | abstract only | re-read |
| [natesan-2020](https://doi.org/10.3390/ma13051202), Table 6 | **cast** A356 + 0.5% Cu, T7, from cylinder heads | strain controlled, strain ratio −1 | σf′ 421 / 346 / 231 MPa and b −0.096 / −0.087 / −0.073 at 150 / 200 / 250 °C | read in source | re-read |

The Roveda points (stress **range** in MPa against cycles to failure; the
amplitude is half the range):

| As built | 265 °C for 1 h | 300 °C for 2 h |
|---|---|---|
| 200 / 43,700 | 210 / 3,874 | 180 / 6,637 |
| 180 / 67,316 | 200 / 10,281 | 170 / 26,039 |
| 160 / 120,482 | 180 / 76,004 | 160 / 137,131 |
| 140 / 706,175 | 160 / 193,641 | 140 / 396,002 |
| 130 / 1,532,958 | 140 / 327,412 | 120 / 1,589,833 |
| 130 / run-out at 10,000,000 | 130 / 1,174,921 | 110 / 5,336,296 |
|  | 120 / run-out at 10,000,000 | 100 / run-out at 10,000,000 |

In the two ageing sets the stress level is not defined as a maximum or an
amplitude. The 200 °C and 350 °C values are single strengths from abstracts:
their run-out counts, stress ratios and specimens could not be read.

**Not found:** a stress-controlled S-N curve at 100 to 300 °C with its points, in a document that could be opened: the two values at 200 °C and the one at 350 °C are single strengths from abstracts; a test that combines a long soak with testing at temperature: the 177 °C ageing sets were tested at room temperature; as-built surfaces at temperature, thermo-mechanical fatigue, or the effect of mean stress at temperature; a review with a table of points that could be opened; a public database of 1,610 S-N sets exists (doi 10.1038/s41597-023-02150-x) and was not opened.

**Contradictions:** fully reversed strength of machined coupons: 110 MPa at 2e7 cycles on the machine maker's sheet, 60 MPa at 1e7 in the Kramer set; T6: reported to help in three papers and to reduce life in a fourth, as quoted by a review; stress relief: no gain in the Roveda set, where the run-out range falls from 130 to 120 to 100 MPa; surface: one group finds ground and as-built surfaces alike, another finds machining clearly better; exposure: 'no variation' after 17 h at 200 °C, against lives falling by a factor of 60 or more after 1000 h at 177 °C.

**Leads that were not opened:** four often-cited room-temperature sets (2012 to 2017) sit behind paywalls or refusing repositories; their numbers are not written here; a dissertation with strain-life data up to 200 °C is under embargo until 2027.

## Port flow

No flow sheet of a 930, 934 or 935 head could be opened. What was read:

| Quantity | Value | Unit | Source, field | Flag | Second reading |
|---|---|---|---|---|---|
| inlet opening of the head at the manifold face, height x width | 41.5 / 32.6 | mm, −2% / +4% | [fisa-b-298](https://historicdb.fia.com/sites/default/files/car_attachment/1479168902/homologation_form_number_298_group_b.pdf), drawing I, page 9; chamfer 1.2 x 45° | read in source | re-read |
| opening of the inlet manifold at the head, height x width | 38.5 / 33 | mm, −2% / +4% | [fisa-b-298](https://historicdb.fia.com/sites/default/files/car_attachment/1479168902/homologation_form_number_298_group_b.pdf), drawing II, page 9 | read in source | re-read |
| exhaust manifold outlet, inside | 67 / 39 | mm | [fisa-b-298](https://historicdb.fia.com/sites/default/files/car_attachment/1479168902/homologation_form_number_298_group_b.pdf), item 328 c, page 8 | read in source | re-read |
| smallest diameter of the inlet pipe, 930 Turbo 3.0 | 1.259 | in | [fia-3076](https://historicdb.fia.com/sites/default/files/car_attachment/1601075701/homologation_form_number_3076_group_3.pdf), item 192 | read in source | re-read |

References for comparing a computed flow with a bench:

- definition of the flow coefficient: mass flow = nominal valve area · C · sqrt(2 · density · pressure drop), with the nominal area (π/4) D² of the valve ([naca-tn-1366](https://ntrs.nasa.gov/api/citations/19930082003/downloads/19930082003.pdf), page 4 and appendix A; read in source, re-read; D is the smallest contact diameter of valve and seat (not re-read); test at a pressure drop of 10 in. of alcohol).
- cycle-mean flow coefficient 0.445 at a lift of a quarter of the valve diameter, for two valve sizes ([naca-tn-1366](https://ntrs.nasa.gov/api/citations/19930082003/downloads/19930082003.pdf), figure captions; read in source, re-read).
- peak flow coefficient about 0.68 at lift / diameter 0.25 and about 0.60 at 0.198 ([naca-tn-1366](https://ntrs.nasa.gov/api/citations/19930082003/downloads/19930082003.pdf), Fig. 23; read off a graph, not re-read).
- computed against measured, helical diesel port, 523,000 cells: the global discharge coefficient is about 6% under the measurement ([encit-2008](https://abcm.org.br/app/webroot/anais/encit/2008/artigos/6_4861.pdf), Tables 1 and 3, conclusions; read in source, re-read).
- computed against measured, four-valve petrol head, 99,500 cells at 5.0 kPa: largest discrepancy 8% ([scientia-2014](https://scientiairanica.sharif.edu/article_3494_20cc6d2898623cf0a9841882fb1a5674.pdf), sections 3 and 4; read in source, re-read).
- bench practice: test pressures of 10, 25 or 28 in. of water are all in use; one practitioner chose 28 in. after finding little change of the port balance below 26 in. ([yunick](https://www.performancetrends.com/PDFs/Smokey%20Yunick%20Airflow%20Testing.pdf), whole note; read in source, not re-read).
- Computed here: factor between flows at two test pressures, if flow goes as the square root of the pressure drop: 10 to 28, 25 to 28, 10 to 25 in. of water: 1.673 / 1.058 / 1.581 (follows from the orifice equation above; a bench maker's note warns that it is not exact at high velocity).

**Not found:** a flow sheet of a 930, 934 or 935 head, of a 3.0 to 3.3 litre 911 head or of this maker's head, in a page that could be opened; valve and port diameters of the 935; a flow coefficient against lift / diameter, or a validated steady computation, for a two-valve hemispherical air-cooled head: the nearest are a flat two-valve research head of 1947 and four-valve or diesel ports; the inlet radius and the bore adapter of a bench fixture, with dimensions.

**Contradictions:** the coefficients of different papers are not interchangeable: seat area, valve-head area, curtain area and bore area are all in use as the reference area; no single 'standard' test pressure: 10, 25 and 28 in. of water each appear as the usual one.

**Leads that were not opened:** forum threads that quote flow figures for 911 heads at 25 in. of water, on two hosts that refuse automated readers; search excerpts only, their numbers are not written here; a flow-bench maker's manual with the fixture rules (behind a robot wall).

## Hosts that refused automated readers

They were left alone ([decision 0003](../../decisions/0003-no-vendor-harvesting.md)). A person can open them by hand.

- valve-train: forums.pelicanparts.com, rennlist.com, lnengineering.com, fvd.net, 911uk.com, carpokes.com, gt2i.com, design911.co.uk, sierramadrecollection.com.
- fatigue: mdpi.com (full texts), sciencedirect.com, link.springer.com, nottingham-repository.worktribe.com, iris.polito.it, cris.unibo.it, hal.science (full texts), publica.fraunhofer.de, elib.uni-stuttgart.de, preprints.org, apps.dtic.mil.
- port-flow: rennlist.com, forums.pelicanparts.com, lnengineering.com, fvd.net, lindseyracing.com, eng-tips.com, manualshive.com, matec-conferences.org, core.ac.uk (full texts).

## Sources

- **fia-3076**: [FIA / ONS homologation form no. 3076, Porsche Turbo, Group 3, valid from 1 January 1977, 28 pages](https://historicdb.fia.com/sites/default/files/car_attachment/1601075701/homologation_form_number_3076_group_3.pdf). The production 930 Turbo 3.0 engine, not the 934, the 935 or the scanned head.
- **fisa-b-298**: [FISA / ONS Group B homologation form B-298, Porsche 911 Turbo 2 (3299 cm3), valid from 1 April 1993, 54 pages; pages 1 to 9 read](https://historicdb.fia.com/sites/default/files/car_attachment/1479168902/homologation_form_number_298_group_b.pdf). The production 964 Turbo 3.3 engine, not the scanned head.
- **webcam-233**: [Web Cam timing card, Porsche 911 SOHC 12v, grind 233](https://webcamshafts.com/pages_vehicles/automobile/porsche_install_data/tc_000452_000591.html). An aftermarket camshaft for 911 engines in general.
- **roveda-2024**: [Roveda, Serrano-Munoz, Haubrich, Requena, Madia: Investigation on the fatigue strength of AlSi10Mg fabricated by PBF-LB/M and subjected to low temperature heat treatments. Materials & Design 244 (2024) 113170](https://elib.dlr.de/207898/).
- **kramer-2025**: [Kramer, Wexel, Purwitasari, Jarwitz, Schulze, Zanger: Impact of different pore types on the tensile and fatigue properties of AlSi10Mg parts produced by laser powder bed fusion. Progress in Additive Manufacturing (2025)](https://publikationen.bibliothek.kit.edu/1000184850).
- **nabil-2022**: [Nabil, Arrieta, Wicker, Benedict, Medina: Effect of Thermal Aging in the Fatigue Life of Hot Isostatic Pressed AlSi10Mg Fabricated by Laser Powder Bed Fusion. Solid Freeform Fabrication Symposium 2022](https://utw10945.utweb.utexas.edu/sites/default/files/2022/Effect%20of%20Thermal%20Aging%20in%20the%20Fatigue%20Life%20of%20Hot.pdf).
- **barrera-2025**: [Barrera, Medina, Arrieta, Marquez: Study of Fatigue Endurance on Artificially Aged Additive Manufactured AlSi10Mg After Stress Relieved and Hot Isostatic Pressed + T6. Solid Freeform Fabrication Symposium 2025, pp. 529-545](https://utw10945.utweb.utexas.edu/sites/default/files/2025/38%20Study%20of%20Fatigue%20Endurance%20on%20Artificially%20Aged.pdf).
- **di-egidio-2023**: [Di Egidio, Ceschini, Morri, Zanni: Room- and High-Temperature Fatigue Strength of the T5 and Rapid T6 Heat-Treated AlSi10Mg Alloy Produced by Laser-Based Powder Bed Fusion. Metals 13 (2023) 263](https://doi.org/10.3390/met13020263). The abstract only, in an open index record; the publisher refused the full text.
- **bahl-2026**: [Bahl, Richter, Torbet, Rakhmonov, Su, Plotkowski, Pollock, Shyam: Strain-rate hardening enhances fatigue resistance of AlSi10Mg alloy at 350 °C. Acta Materialia 305 (2026) 121866](https://impact.ornl.gov/en/publications/strain-rate-hardening-enhances-fatigue-resistance-of-alsi10mg-all/). The abstract only, on the laboratory's publication page.
- **natesan-2020**: [Natesan, Eriksson, Ahlström, Persson: Effect of Temperature on Deformation and Fatigue Behaviour of A356-T7 Cast Aluminium Alloys Used in High Specific Power IC Engine Cylinder Heads. Materials 13 (2020) 1202](https://doi.org/10.3390/ma13051202). The open-access full text in Europe PMC.
- **naca-tn-1366**: [Livengood and Eppes: Effect of changing manifold pressure, exhaust pressure and valve timing on the air capacity and output of a four-stroke engine operated with inlet valves of various diameters and lifts. NACA Technical Note 1366, December 1947](https://ntrs.nasa.gov/api/citations/19930082003/downloads/19930082003.pdf). A single-cylinder CFR research engine with a flat two-valve head, not a hemispherical chamber.
- **encit-2008**: [Comparisons between steady state analyses of a high swirl-generating helical intake port. Proceedings of ENCIT 2008, paper 6-4861](https://abcm.org.br/app/webroot/anais/encit/2008/artigos/6_4861.pdf). A helical diesel inlet port.
- **scientia-2014**: [Mohammadebrahim et al.: Investigation into the effect of intake port geometric parameters and blockage on flow coefficient and in-cylinder flow. Scientia Iranica B 21(2) (2014) 438-448](https://scientiairanica.sharif.edu/article_3494_20cc6d2898623cf0a9841882fb1a5674.pdf). A four-valve petrol head.
- **yunick**: [Smokey Yunick: Airflow Testing (note distributed by a flow-bench software maker)](https://www.performancetrends.com/PDFs/Smokey%20Yunick%20Airflow%20Testing.pdf).
