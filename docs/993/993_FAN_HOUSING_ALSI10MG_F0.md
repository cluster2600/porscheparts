# 993 engine fixed fan housing — AlSi10Mg F0

This candidate targets the **stationary** part of the cooling system, never the
rotating impeller. PorscheFanatics points out that the housing distributes air
to the whole engine: its fit and its sealing are functional.

FVD publishes the reference `993 106 667 03`, a product envelope of
`300 × 300 × 170 mm` and `1.9 kg`. Centre Porsche Roissy publishes `1.86 kg` and
also links `993 106 667 01`. A reseller describes the part as aluminum, without
grade, process or certificate. These elements are enough to bound an F0, not to
rebuild a fittable part.

## Geometry and additive value

The build123d master keeps the published envelope, then uses entirely synthetic
interfaces: throat `252 mm`, shell `3 mm`, flange `4 mm`, annular support
`90/70 mm`, six spokes `81 × 12 × 12 mm` and six `6.6 mm` holes.

The re-read STEP contains one valid BREP solid, without impeller, and an open
air path. Its volume is `668,006.23 mm³`, that is `1,783.58 g` in AlSi10Mg.
Being close to the commercial `1.86–1.90 kg` is not a validation: several very
different geometries can have the same mass.

A solid rectangular billet would weigh `40.851 kg`, `22.90` times the F0. AM can
therefore make its case for a low-volume restoration, by consolidating shell,
flange, support and spokes. A qualified aluminum/magnesium casting nonetheless
remains the reference to beat on cost, fatigue, surface finish and rate.

## Flow screening

With the synthetic case `Q = 1.25 m³/s`, the annular section is:

`A = π(D² - d²)/4 = 0.043514 m²`, then `v = Q/A = 28.73 m/s`.

For `ρ = 1.05 kg/m³` and `K = 0.8`, the lumped model gives:

`Δp = Kρv²/2 = 346.58 Pa`, then `P = ΔpQ = 433.23 W`.

The screen passes under an arbitrary limit of `500 Pa`, ratio `1.443`. It is
neither a fan curve nor the flow distribution to the cylinders.

## Structure, modal and thermal

A synthetic radial load of `2 kN` is spread equally over six spokes. The beam
model gives `I = bt³/12 = 1,728 mm⁴`, `93.75 MPa` and `0.488 mm` at the tip. The
ratio to `245 MPa` is `2.61`: the static screen passes narrowly on the maximum
deflection of `0.50 mm`.

The first mode of the simplified cantilevered spoke is `1,512.8 Hz`. A
synthetic excitation at eleven blades and `6,000 rpm` is `1,100 Hz`; separation
`37.5 %`, above the `20 %` target. This screen does not replace a modal model of
the assembled housing.

At `150 °C` from `20 °C`, the throat grows freely by `0.688 mm`. Fully
restrained, `σ = EαΔT` reaches `191.1 MPa`; the ratio `245/191.1 = 1.282` is
below `1.5`: **thermal failure**. The overall F0 therefore fails, deliberately.

## Reproduction

```bash
docker run --rm --platform linux/amd64 -v "$PWD:/work" -w /work \
  ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57 \
  python parts/993-eng-fan-housing-alsi10mg-f0-0001/source/fan_housing.py \
  --out parts/993-eng-fan-housing-alsi10mg-f0-0001/derived/fan_housing_alsi10mg_f0.step \
  --report parts/993-eng-fan-housing-alsi10mg-f0-0001/evidence/engineering-screen.json
```

## Next gates

1. Scan the assembled housing, impeller, hub, alternator, sheet metal and seals.
2. Measure bore, concentricity, datums, blade clearances and thermal tolerances.
3. Instrument flow, pressure, leakage, temperatures, speed, vibration and belt
   load.
4. Rebuild the ducts and run CFD/CHT with a measured fan curve.
5. Run assembled FEA, modal/harmonic, fatigue and blade containment.
6. Compare casting, machined fabrication and LPBF with complete cost/quality.
7. Qualify orientation, supports, T6, HIP, machining, CT, FPI and endurance.

PhysicsNeMo stays deferred until correlated CFD/CHT/structure/modal sets exist,
with separate training, validation, holdout and out-of-distribution splits.
The F0 is prohibited from manufacture, rotation, installation and start-up.

<!-- print-screen:begin -->

## LPBF print simulation

The simulation was run and **failed closed**: none of the candidate orientations fits the EOS M 290 envelope (250 x 250 x 325 mm). No result is therefore published for this part, and no image is made up in its place.

<!-- print-screen:end -->
