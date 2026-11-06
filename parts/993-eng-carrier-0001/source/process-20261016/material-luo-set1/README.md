# RT mechanical sensitivity — Luo public data, process set 1

This batch contains four individual measured curves, their pre-necking conversions and the derived plasticity tables. The first curve to use for the agreed diagnostic is `flat-set-1-plastic.inp`, chosen independently of the carrier's response. The other three specimens bound the observed scatter of this single set; four tests do not define an allowable stress.

Original data: Luo, Yin, Simpson, Beese, [Data in Brief 46 (2023) 108911](https://doi.org/10.1016/j.dib.2023.108911), [Zenodo 6587905, version 10-16-2023](https://zenodo.org/records/6587905), licence **CC BY 4.0**. Attribution, licence link and transformations are kept in `DATA_LICENSE.json`. The original archives are not added to the repository.

Process: ProX DMP 320, LaserForm Ti Gr23 (A) Ti6Al4V ELI powder, 275 W / 800 mm/s, 60 µm layer, 82 µm hatch, tension along the Z build axis. Treatment: stress relief 670 °C 5 h then furnace cooling under argon 12 h. This batch is a room-temperature sensitivity for this material and this condition; it does not identify the real law of the carrier's Grade 5. Poisson's ratio is not provided by this source: any value used remains a separate assumption.

| Specimen | Published E (MPa) | Published Rp0.2 (MPa) | Plastic points | Model εp range | Initial → final σtrue (MPa) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Flat1 | 106000 | 946 | 248 | 0–0.046980426 | 956.878–1073.556 |
| Flat2 | 110000 | 942 | 255 | 0–0.046609583 | 952.630–1082.480 |
| Round1 | 118787 | 927 | 277 | 0–0.049013623 | 936.794–1082.219 |
| Round2 | 110000 | 956 | 191 | 0–0.047629591 | 966.909–1094.936 |

For homogeneous pre-necking strain: σtrue = σeng(1 + eeng), εtrue = ln(1 + eeng), εplast,raw = εtrue − σtrue/Epublished. The model takes the measured Rp0.2 as the initial yield and shifts its plastic origin to that point. This convention removes about 0.24–0.26 % of plastic strain already present at the proof point; it is not a measurement of the proportional limit. The CSVs keep the raw conversion, without this translation and without smoothing, so that this decision can be revisited.

Stress noise is treated by PAVA isotonic regression on all points retained after this threshold and before the maximum engineering stress. Maximum adjustment 0.611 MPa for the four tests, 0.431 MPa for Flat1. No hardening point is reconstructed from the Rp/Rm pair alone. The table is intended for an isotropic J2 sensitivity model; it includes no damage or fracture law. A solver may extrapolate beyond the last entry: reject the interpretation of the diagnostic if its maximum PEEQ exceeds the corresponding range above.

Reproduction from the three pinned public downloads, with Python and the dependencies in `../materials/requirements.txt`:

```sh
python3 ../materials/fetch_luo_sources.py /path/to/new/source-data
python3 ../materials/extract_luo_rt.py /path/to/new/source-data /path/to/new/derived-data
```

The SHA256s, process data, conventions, number of points and smoothing deviation are in `provenance.json`. The portable extractor exactly reproduced the eight numerical CSV/INP files of this batch.
