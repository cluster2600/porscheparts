<a id="culasse-à-eau--données-matière-avant-cht-et-fatigue"></a>

# Water-cooled head: material data before CHT and fatigue

**No alloy or process recipe is qualified for our head.** The study compares
CP1 and CuCrZr; selection depends on heat transfer **and** the hot strength
of the seat/guide/stud assembly. High conductivity does not replace these checks.

<a id="vérification-des-sources-le-12-octobre-2026"></a>

## Sources checked on October 12, 2026

The [current Constellium page](https://www.constellium.com/products/aluminium-powders/)
positions CP1 (Al–Zr–Fe, AA8A61.50) for conductivity and HT1
(Al–Mn–Ni–Cu–Zr, AA8A81.50) for temperature capability and strength.
This distinction motivates a comparison if CP1 fails at temperature; the page
provides no allowables for our head. The CP1 value of 187 W/m·K in the
[initial dossier](README.md#matière--conductivité-et-tenue-à-chaud) remains a
room-temperature measurement, not a k(T) law.

The [EOS CuCrZr data sheet](https://www.eos.info/var/assets/05-datasheet-images/Assets_MDS_Metal/EOS_CopperAlloy_CuCrZr/Material_DataSheet_EOS%20_Copper_CuCrZr_en.pdf?v=11),
PDF pages 5–7, separates two treatments for M400-1, 80 µm layers.
The downloaded PDF has the same digest as the initial reference:
`274737eccc264b900ce8136bb5c3d786bea05378bccf2dd15dda70e53273f6c3`.

| EOS M400-1 recipe | Published treatment | Published vertical Rp0.2 | Published electrical conductivity |
|---|---|---:|---:|
| Favoring conductivity | 550 °C, 3 h, inert atmosphere | 230 MPa | 88% IACS |
| Favoring tensile strength | 490 °C, 1 h, inert atmosphere | 495 MPa | 76% IACS |

These coupon results are not hot-fatigue limits. Do not assign 495 MPa and
88% IACS to the same recipe. IACS measures electrical conductivity: the data
sheet provides no thermal-conductivity curve for CHT. Pages 9–10 describe a
different M290 1 kW system; do not mix its data with the M400-1 data.

The process minimum wall stated on page 5 does not become a head thickness
that withstands combustion. The 340 W/m·K conductivity cited in the initial
research summary does not qualify our supplier's recipe either.

<a id="données-à-acquérir-sur-le-procédé-retenu"></a>

## Data to acquire for the selected process

| Function | Required data, still absent | Comparison condition |
|---|---|---|
| CHT | k(T), heat capacity, density, channel surface finish | Same batch/process, orientation and treatment; thermal domain defined by calculation then bench testing |
| Thermal stress | Expansion, modulus and plasticity as functions of T | Same metallurgical state and thermal history as the part |
| Lifetime | Thermomechanical fatigue, relaxation/creep, scatter and defects | Identified engine temperature/pressure cycle, not only cold tensile strength |
| Seats and guides | Hot interference fit and contact pressure, expansion of both materials | Exact supplier parts, tolerances and retention tests after cycling |
| Water and oil | Corrosion, fluid compatibility, sealing and porosity | Actual fluid and selected temperatures; aging and circuit cleaning |
| LPBF channels | Roughness, depowdering, residues, dimensional drift and CT defects | Coupons reproducing the future design's orientation, sections and junctions |

Do not set a metal service temperature from coolant temperature alone.
Local temperatures are CHT outputs to correlate on the bench. For CuCrZr
inserts in CP1, add thermal contact resistance, assembly, differential
expansion and galvanic corrosion; no multimaterial benefit is established.

<a id="comparaison-à-réaliser"></a>

## Comparison to perform

Compare CP1 and CuCrZr on the **same geometry and under the same conditions**
using laws specific to each recipe. Keep flow, pressure loss, local
temperatures, mass and stress/fatigue as separate results.
Then assess channel optimization at comparable flow or pumping power;
do not confuse a material benefit with a hydraulic benefit.

Coupons and tests must be defined and approved with the engine builder and
manufacturer before execution. This sheet authorizes no printing parameter,
proof pressure, service life or thickness reduction.
