# Measured conductivity for a separate AlSi10Mg study

Temperature-dependent conductivity data are available for a separate LPBF
AlSi10Mg recipe. They support a future conditional conduction study; no head
material is selected and no head solve follows from this lookup.

Willkomm et al., *Design and manufacturing of a cylinder head by laser powder
bed fusion*, IOP Conference Series: Materials Science and Engineering 1097
(2021) 012021, [DOI](https://doi.org/10.1088/1757-899X/1097/1/012021),
reports the following laser-flash results in Table 2, printed page 6.
Conductivities are in W/(m·K); ± values are reported standard deviations.

| Temperature (°C) | Build direction Z | Transverse XY |
| ---: | ---: | ---: |
| 23 | 162.9 ± 7.2 | 154.6 ± 7.7 |
| 150 | 163.6 ± 6.3 | 154.4 ± 2.1 |
| 200 | 165.4 ± 6.1 | 154.9 ± 2.9 |
| 250 | 160.5 ± 3.5 | 152.2 ± 1.2 |

The reported treatment heats to 240 °C over one hour, holds six hours,
oven-cools to 100 °C, then air-cools. Coupon machine, scan recipe, layer
thickness and plate preheat remain unspecified. The component's later
X-Line/200 °C manufacturing description does not identify those coupons.
This recipe stays separate from the [seven manufacturer entries](ENGINEERING_MATERIALS.md).

The [source register and visual confirmation](derived/engineering/material-conductivity-literature/README.md)
retain the table and treatment provenance. The official publisher PDF was
downloaded and both relevant pages were rendered and viewed. Its SHA-256 is
`bc666124ffe955239fad3a627bae45e445de4b30e818e57917a02876ed8ff607`.
The institutional URL was readable through the web parser but its direct
fetch returned HTML; its PDF byte identity remains unestablished. No PDF or
page image is redistributed. The article is CC BY 3.0.
The [independent publication review](derived/engineering/material-conductivity-literature-peer-review.json)
checks both source records, the table, treatment, units and stated limits.

Piecewise-linear interpolation in each column over **23–250 °C** is a proposed
numerical assumption. It is not a published continuous law. Refuse
extrapolation; convert kelvin with T°C = TK − 273.15 and conductivity to
W/(mm·K) by dividing by 1,000 for the mm-based solver. Two directional scalar
sensitivity cases can remain separate. A tensor additionally needs an explicit
build-axis frame and assumptions of transverse isotropy and zero cross terms.
Measurement scatter is not a design allowable.

Steady conduction needs neither density nor heat capacity. Table 2 also
contains heat-capacity measurements, preserved in the visual receipt, but no
transient material law is selected here. Matched E(T), Poisson ratio, expansion,
stress-free state, plasticity, fatigue and creep remain open. The 250 °C test
point establishes no service-temperature limit. An accepted mesh, mapped
loads and cooling boundaries are still required before a head calculation.
