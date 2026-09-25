# M64: conductive materials, hot strength and missing data

This targeted review supplements the [existing material campaign](../reports/M64_700CH_MATERIAL_COOLING_LPBF.md). It does not make a final alloy selection. Sources were consulted up to **September 12, 2026**; scientific publication, supplier data sheet and unread lead are kept distinct.

## Decision for the first comparisons

Keep **AlSi10Mg as the process baseline**, **CP1 as the heat-spreading candidate**, **HT1 as the hot-strength candidate**. A20X remains an alternative whose test conditions and conductivity must be completed. This work hierarchy does not name the winning material. The [documentary points in the repository](../../twins/m64-cylinder-head/targets/700ps-material-process-candidates.json) remain observations attached to a process and a condition, not design allowables.

Pauzon et al. study CP1, Al–1Fe–1Zr, made by LPBF, directly. They link precipitation to mechanical behavior after aging and report **330 MPa yield strength and 27 MS/m electrical conductivity**, after 400 °C for four hours. These are results of their protocol; **400 °C is the heat treatment, not the service temperature under load**. Electrical conductivity does not become a thermal card without a justified relation and calibration.[^1]

The Constellium data sheet gives **182–189 W/(m·K)** depending on the treatment time at 400 °C; the measurement temperature of that column is not specified. Its room-temperature tensile table therefore does not guarantee 300 MPa of strength in a valve bridge at 200–300 °C. The [existing campaign](../reports/M64_700CH_MATERIAL_COOLING_LPBF.md) keeps the hot points and their different treatment separate.[^2]

The EOS **M290, AlSi10Mg, 30 µm** data sheet gives a conductivity of 100/110 W/(m·K) as-built vertical/horizontal, 165/155 after T6 and 160/165 after stress relief. It identifies a reproducible baseline, but does not allow these values to be carried over to another machine, a rough internal surface or another thermal history. The page does not provide a complete k(T) curve here. Its mention of a minimum printable wall is not an allowable structural thickness for a cylinder head.[^3]

The gain of CP1 over AlSi10Mg therefore depends strongly on **the condition compared**. Setting aged CP1 against as-built AlSi10Mg would produce a misleading ranking if the AlSi10Mg component were to be heat treated. The data currently available do not yet allow a complete comparison at identical service temperature and lifetime.

## Why conductivity alone is not enough

In a simplified thermal path:

\[
R_{cond}=\frac{L}{kA},\qquad
R_{conv}=\frac{1}{\eta_f h A_f},\qquad
\dot Q=\frac{\Delta T}{R_{cond}+R_{contact}+R_{conv}}.
\]

This network is a first-order cross-check, not a replacement for three-dimensional CHT. Doubling k does not necessarily double the heat extracted: the seat–cylinder head contact, the flow between fins, the shrouds and the oil cooler can dominate. A gallery locally increases heat transfer but also removes load-bearing material; a very thin fin can become ineffective and hard to manufacture.

The final decision must compare, on the same geometry and the same loads, the temperature of the exhaust/spark plug bridges, the gradient near the seats, the deformation of the bores, clamping relaxation, thermomechanical fatigue, mass and auxiliary power. **The material that conducts heat best is not automatically the one that gives the best cylinder head.**

The A20X brochure distinguishes room-temperature treatments from the hot table. For the latter, the missing parameters prevent attributing a T7 condition by mere editorial proximity. Its figures remain useful for requesting comparable tests, not for filling in a fatigue card.[^4] The 2618 and INCONEL 718 comparisons are already sourced in the campaign: the first is a conventional benchmark, the second a mass/conduction comparison and a possible candidate for some components, not a proposal for a complete body.

## What recent publications change

Mani et al. characterize the phases of Al–1Fe–1Zr in three dimensions by nanotomography and fluorescence. The reported resolution reaches 57 nm for one of the techniques. This study helps understand the intermetallic networks and the Fe/Zr distribution; **it is not a new hot fatigue campaign on CP1**. Its open data can support a later microstructure study, without delaying the first macroscopic computation on measured properties.[^5]

Nagalingam et al. compare single- and multi-laser LPBF AlSi10Mg. Their tests combine positions on the build plate, layer thickness and gas flow. An optimized multi-laser strategy can match the fatigue performance of the baseline; a reduced gas flow increases detrimental defects. The fatigue specimens are machined and then ground, at a strain amplitude of 0.5%. The practical application is to plan witness coupons in the overlap zones and downstream of the gas, and surfaces representative of the galleries. These results do not provide a thermomechanical fatigue law for a cylinder head.[^6]

A publication of **March 11, 2026**, *Computational design of ultra-high thermal conductivity, crack-free aluminum alloys for additive manufacturing*, is an alloy design lead. The notice and identity were found, but access to the PDF was refused. **No quantified gain or material choice is inferred from it**; its detailed analysis belongs to the delegated missions, with this access level explicitly flagged.[^7]

## Material test package to prepare

For each selected alloy–machine–powder–orientation–treatment combination:

1. **Heat transport:** k(T), Cp(T), density and thermal expansion; distinguish measured, computed and assumed conductivity. Check anisotropy and aging effects.
2. **Hot mechanics:** E(T), stress–strain curves, relaxation/creep at the relevant hold times; room-temperature tests after exposure kept separate from tests performed directly at temperature.
3. **Durability:** LCF/HCF and thermomechanical fatigue with temperatures and phases matching the computed scenarios; representative machined and internal surfaces, characterized defects, scatter and sample counts retained.
4. **Assembly:** interference fit/relaxation of seats and guides, sealing, differential expansion; insert materials and lubrication explicitly defined.
5. **Process:** coupons built with the real recipe, laser position and overlaps; metrology after heat treatment, cutting, machining and cleaning. The calibration and validation sets must be distinct.

The final temperatures, durations and specimen counts will follow from the loads and an approved qualification plan. No supplier table replaces these tests. There is not yet any material assigned and qualified for engine manufacturing.

## Sources and reading

[^1]: C. Pauzon et al., [Direct ageing of LPBF Al-1Fe-1Zr for high conductivity and mechanical performance](https://doi.org/10.1016/j.actamat.2023.119199), *Acta Materialia* 258, 119199, **October 1, 2023**. Article evaluated; abstract and the publisher's method/results/conclusion excerpts consulted, not the full text.
[^2]: Constellium, [Aheadd CP1 — Product Sheet](https://assets.foleon.com/eu-central-1/de-uploads-7e3kk3/41170/product_sheet_aheadd_cp1_nov_2021docx.e81a7d073ebf.pdf), **November 2021**, 2 pages. Supplier data sheet, not an article; document reread, values attached to their condition in the existing register.
[^3]: EOS, [AlSi10Mg, EOS M290, 30 µm](https://www.eos.info/metal-solutions/data-sheets/aluminium/pds-eos-aluminium-alsi10mg-eos-m-290-30um); [materials portal tables](https://www.eos.info/metal-solutions/data-sheets/all-processes-and-materials?id=eos-aluminium-alsi10mg). Process data sheet consulted on September 12, 2026. The portal's status date is not a scientific publication date.
[^4]: ECKART, [Metal Powders for Additive Manufacturing, A20X, pp. 4–5](https://www.eckart.net/en/download/document/view/id/519). Supplier brochure, A20X section consulted; missing conditions kept in the [register](../../twins/m64-cylinder-head/documentary-material-points-20260907.json).
[^5]: D. Mani et al., [Nanoscale 3D characterization of an Al-1Fe-1Zr alloy for additive manufacturing](https://doi.org/10.1016/j.matchar.2025.115109), *Materials Characterization* 225, 115109, online **May 2, 2025**. Article evaluated; methods, results and conclusions of the [institutional PDF](https://publications.rwth-aachen.de/record/1012561/files/1012561.pdf?version=1) consulted, data not reproduced.
[^6]: A. P. Nagalingam et al., [Impact of Multiple-Laser Processing on the Low-Cycle Fatigue Behaviour of Laser-Powder Bed Fused AlSi10Mg Alloy](https://doi.org/10.3390/met15070807), *Metals* 15(7), 807, **July 18, 2025**. Article evaluated; abstract and methods sections 2–3 of the [institutional PDF](https://eprints.whiterose.ac.uk/id/eprint/230301/1/metals-15-00807.pdf) consulted; not an exhaustive reading of the 22-page article.
[^7]: Y. He et al., [Computational design of ultra-high thermal conductivity, crack-free aluminum alloys for additive manufacturing](https://doi.org/10.1080/17452759.2026.2638103), *Virtual and Physical Prototyping* 21(1), e2638103, **March 11, 2026**. **Notice only; PDF inaccessible.** Bibliographic lead, excluded from the selection evidence.
