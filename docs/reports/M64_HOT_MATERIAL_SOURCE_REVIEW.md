# M64 — material data re-read from the manufacturer PDFs

September 7, 2026. The PDF skill required a **visual** check of the
tables and notes: ECKART PDF pages 4–5, Constellium pages 1–2. The four
pages were rendered locally; neither the PDFs nor proprietary renders are
added to the repository. Digests, locators and figures:
`twins/m64-cylinder-head/documentary-material-points-20260907.json`.

## A20X points as a function of temperature

| Test T (°C) | Tensile strength (MPa) | Published yield strength (MPa) | Elongation (%) |
| ---: | ---: | ---: | ---: |
| 20 | 511 | 445 | 11 |
| 100 | 423 | 375 | 10 |
| 150 | 369 | 354 | 20 |
| 200 | 331 | 311 | 15 |
| 250 | 224 | 215 | 12 |

Source: [ECKART, PDF page 5, lower table](https://www.eckart.net/en/download/document/view/id/519).
This table does not directly state treatment, orientation, sample count,
hold time or hot test method. **It is not automatically
labeled T7.** The upper table gives E = 74/77/79 GPa at room
temperature for as-built/stress-relieved/T7-treated, respectively. Stress relief
is 300 °C, 2 h, on the build plate; the T7 recipe is proprietary.

Anomaly kept: 445 MPa at 20 °C in the lower table, against a
390–440 MPa range in the upper T7 column. Do not merge these data sets
nor correct the figure without clarification from the manufacturer. The labels do not
specify the Rp0.2 offset; the transcription keeps "yield strength".

## CP1: treatment at 400 °C, but tensile test at 25 °C

| Treatment at 400 °C | Tensile at 25 °C (MPa) | Published yield at 25 °C (MPa) | Elongation (%) | Published k (W/m·K) |
| ---: | ---: | ---: | ---: | ---: |
| 1 h | 340 | 321 | 14.2 | 182 |
| 4 h | 342 | 323 | 12.8 | 187 |
| 7 h | 332 | 313 | 16.8 | 189 |

Source: [Constellium CP1, November 2021, page 2](https://assets.foleon.com/eu-central-1/de-uploads-7e3kk3/41170/product_sheet_aheadd_cp1_nov_2021docx.e81a7d073ebf.pdf).
The vertical orientation and the 25 °C apply to the tensile test. **The measurement
temperature of k is not stated in its adjacent header**: it remains
null in the transcription. The three rows vary the treatment duration,
not the operating temperature. No hot tensile point is
provided. The announced stability at 250–300 °C for several thousand hours
constitutes neither a k(T) curve nor a hot allowable strength.

## Data still needed to simulate the part

| Property | A20X, pages examined | CP1, pages examined |
| --- | --- | --- |
| Yield/ultimate as a function of T | 5 published points, incomplete conditions | No hot point |
| Modulus E(T) | Only room-temperature E by condition | Not published |
| Conductivity k(T) | Not published | 3 values by treatment, not by T |
| Heat capacity Cp(T) | Not published | Not published |
| Expansion α(T), Poisson's ratio | Not published | Not published |
| Full plasticity, creep, relaxation, fatigue/TMF | No usable laws in these pages | No usable laws in these pages |

This transcription improves the documentary starting points but does not provide
a complete constitutive map. It does not choose a winning material,
interpolates no curve and assigns no allowable to the M64 cylinder head.
The loads, the exact process and the temperature range must be
defined before comparing the mechanical and thermal margins.
