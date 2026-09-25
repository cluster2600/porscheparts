# CP1 — targeted supplement: one elevated-temperature point and expansion coefficients

Search of September 7, 2026, independent of the previous transcription. No solver
parameter modified, no curve interpolated, no material qualification.

## 1. A genuine tensile point at 200 °C

The **Constellium / C-TEC, Formnext 2021, slide 9** presentation explicitly
distinguishes the **1 h at 400 °C** treatment from the **200 °C** test. Stated
process: EOS M290, 60 µm layers, vertical specimen.

| Test temperature | Yield strength YS | Tensile strength UTS | Elongation |
|---|---:|---:|---:|
| 200 °C | **126 MPa** | **149 MPa** | **17.0 %** |

The same page gives an expansion of **25.19 × 10⁻⁶ K⁻¹ over 20–200 °C**,
but does not tie this coefficient to a specific treatment condition. The table
and its headers were checked visually in the rendered PDF. The public
document carries a confidentiality marking: no PDF or image is added
to the repository, only these facts and their provenance.

Primary source: [Shahani and Chehab, Constellium, Formnext 2021, p. 9](https://assets.foleon.com/eu-central-1/de-uploads-7e3kk3/41170/2021-11-8_constellium_aheadd_formnext_final.a0a8c4307e76.pdf).

Missing information remains missing: tensile standard, YS proof
offset, strain rate, hold at test temperature, sample count, scatter and
surface condition. **126 MPa is not automatically Rp0.2, an allowable stress,
or the value for the 4 h treatment.**

## 2. A more recent manufacturer data sheet with three temperature ranges

The process data sheet **EOS Aluminium Constellium CP1 / M290 / 60 µm**, shown
as of **04.09.2026**, identifies the parameter set `AlCP1_060_M291`, level **TRL 3**,
125 °C build plate and argon. It publishes:

| Temperature range | Published expansion coefficient |
|---|---:|
| 25–100 °C | **19 × 10⁻⁶ K⁻¹** |
| 25–200 °C | **21 × 10⁻⁶ K⁻¹** |
| 25–300 °C | **22 × 10⁻⁶ K⁻¹** |

The tensile properties on this data sheet remain **at room temperature**.
The expansion section does not state its heat-treatment condition, orientation,
standard or uncertainties. The primary HTML page was archived and hashed
privately; its PDF generation link returned HTTP 500.

Primary source: [EOS, CP1 M290 / 60 µm data sheet](https://www.eos.info/metal-solutions/data-sheets/aluminium/pds-eos-aluminium-constellium-cp1-eos-m-290-60um).

## Consequences for future M64 computations

The documentary gap is reduced, not resolved: CP1 now has in our
transcription **one tensile point explicitly at elevated temperature** and **four
range coefficients**. They do not form a complete material law.

- The expansion values describe ranges, not instantaneous values
  of α(T) at their bounds. Do not inject their three numbers as
  a differential curve into a solver.
- The 2021 and EOS values must not be merged: unstated conditions,
  different ranges and noticeably different values.
- No new verified **k(T)** or **Cp(T)** law was found in the
  selected documents. An electrical conductivity is not substituted for a
  thermal measurement; aging is not treated as an elevated-temperature test.
- The additional elevated-temperature properties and the cyclic data needed
  for the mechanical model remain missing. The 200 °C point justifies no
  extrapolation to the hot spot of the future turbo cylinder head.

The Nikon `MDS_Aheadd CP1_2024-11.2_EN` and Velo3D (February 16, 2024) data sheets
were also read: they detail recipes and room-temperature tests,
but add no elevated-temperature law to this supplement.
[Nikon](https://nikon-slm-solutions.com/wp-content/uploads/2024/11/mds5144.pdf),
[Velo3D](https://velo3d.com/wp-content/uploads/2025/04/Velo3D-Material-Datasheet-Aluminum-CP1.pdf).

Machine-readable transcription, conditions and unknowns:
[cp1-hot-points-supplement-20260907.json](../../twins/m64-cylinder-head/cp1-hot-points-supplement-20260907.json).
