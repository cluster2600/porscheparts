# 962 head: sourced material-point comparison

The [calculated report](derived/engineering/material-comparison.json) uses the
seven recipes in [materials.json](engineering/materials.json) and the four
retained [geometric metal volumes](derived/family/delivery-report.json).
It performs mass and yield-retention arithmetic only. No material, service
temperature, process recipe or head strength is qualified or selected.

## HT1: keep the two treatments separate

The [Constellium HT1 sheet](https://assets.foleon.com/eu-central-1/de-uploads-7e3kk3/41170/aheadd_ht1_fact_sheet_230620.ccac52e244fb.pdf),
page 1, reports vertical specimens from EOS M290/60 µm builds. The actual
temperature/time schedules for treatments #1 and #2 are not supplied.
Retention is `100 × yield(T) / yield(25 °C)` within the same treatment:

| Manufacturer treatment | Yield at 25 °C | Yield at 200 °C | Retained at 200 °C | Yield at 250 °C | Retained at 250 °C |
| --- | ---: | ---: | ---: | ---: | ---: |
| #1 | 425 MPa | 238 MPa | 56.00% | 188 MPa | 44.24% |
| #2 | 285 MPa | 270 MPa | 94.74% | 216 MPa | 75.79% |

Treatment #1 leads at 25 °C; treatment #2 leads at the two published hot
points. A room-temperature yield ranking therefore cannot select a head
material. These are manufacturer coupon points, without interpolation,
extrapolation, a constitutive law, design allowables or fatigue life.
Neither hot test point is a selected cylinder-head service temperature.

## Conditional mass of the study body

The [EOS CuCrZr sheet](https://www.eos.info/var/assets/05-datasheet-images/Assets_MDS_Metal/EOS_CopperAlloy_CuCrZr/Material_DataSheet_EOS%20_Copper_CuCrZr_en.pdf?v=11),
pages 5–7, gives a minimum density of 8,840 kg/m³ for the retained
M400-1/80 µm entries. Multiplying each fixed study volume by that density gives:

| Head bore | Geometric metal volume | Conditional minimum CuCrZr body mass |
| --- | ---: | ---: |
| 95 mm | 915.458 cm³ | 8.093 kg |
| 98 mm | 911.704 cm³ | 8.059 kg |
| 100 mm | 908.921 cm³ | 8.035 kg |
| 102 mm | 905.982 cm³ | 8.009 kg |

The same density entry produces the same mass arithmetic for all four
CuCrZr treatment/orientation rows. This is a conditional lower bound at
fixed geometric volume, not a measured mass or a bound that accounts for
geometry uncertainty. It covers only the modeled body, without an installed
assembly, supports, machining changes, seats, guides or fasteners.
The retained CP1 and HT1 sources provide no density in the input register;
their mass outputs remain `null`.

## Data still needed

The EOS tensile table does not specify an exact numeric test temperature;
the comparison leaves it `null` and does not relabel it as 25 °C. Its
conductivity-optimized and tensile-optimized treatments and horizontal/vertical
specimens remain separate. The published 88% and 76% IACS values are electrical
conductivity, not thermal-conductivity inputs.

The [CP1 sheet](https://assets.foleon.com/eu-central-1/de-uploads-7e3kk3/41170/product_sheet_aheadd_cp1_nov_2021docx.e81a7d073ebf.pdf)
provides a single conductivity value of 187 W/(m·K), with no explicit temperature
in that column. It supplies no k(T) curve. No elastic, plastic, thermal,
fatigue or creep law is fabricated from these points.

The next comparison needs process-specific k(T), E(T), Poisson ratio,
expansion, heat capacity, plasticity, fatigue/TMF, creep/relaxation and their
scatter, plus exact powder/machine/orientation/treatment identity. It also
needs pressure and thermal histories, accepted CHT/structural meshes,
contacts/preloads, seat/guide retention, corrosion and independent correlation.
The [input contract](engineering/input-contract.json) retains those open gates.
Compare candidates on the same geometry and conditions before attributing a
result to material choice.

## Reproduction and checks

The stdlib [calculator](source/compare_materials.py) reuses the engineering
validator, checks delivery volumes against the bound inspection reports and
records SHA-256 digests of inputs, geometry records, calculator and validator.
It refuses to overwrite an existing report. No mesh generation or physics
solver is invoked.

```sh
python3 twins/962-cylinder-head-f0/source/compare_materials.py \
  --check twins/962-cylinder-head-f0/derived/engineering/material-comparison.json
python3 twins/962-cylinder-head-f0/source/compare_materials.py \
  --output work/962-engineering/new-material-comparison.json
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests \
  -p 'test_962_material_comparison.py' -v
```

Six targeted tests pass: treatment-specific references, missing temperature
and density, rejection of incomplete HT1 points, bound-input drift, actual
geometry linkage and refusal to overwrite. These checks establish arithmetic
and provenance, not a material-selection or manufacturing decision.
