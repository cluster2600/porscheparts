# 993 engine cooling impeller — AlSi10Mg F0

This rotating part is the direct continuation of the fixed F0 housing.
PorscheFanatics identifies the Porsche impeller `964 106 015 31` for 964/993.
FVD publishes a product envelope of `300 × 300 × 150 mm` and `0.94 kg`; the
Centre Service Porsche Poitiers publishes `0.948 kg`. Partworks states
aluminum, without grade or process.

## F0 geometry and integration

The build123d master is independent: diameter `280 mm`, depth `30 mm`, annular
hub `80/30 mm`, twelve straight blades swept by `10°` and a `3 mm` peripheral
ring. The re-read STEP contains one valid BREP solid of `370,931.41 mm³`, that
is `990.39 g` in AlSi10Mg.

The mass sits at `+5.36 %` of FVD's `940 g`, but this scalar comparison
validates neither shape nor balance. A `280 × 280 × 30 mm` billet would weigh
`6.280 kg`, `6.34` times the F0: AM has a real geometric and material benefit.

The first assembly test is deliberately strict: the previous F0 housing has a
synthetic `252 mm` throat, facing this `280 mm` impeller:

`c_radial = (252 - 280)/2 = -14 mm`

The assembly is therefore **incompatible**. No synthetic dimension is silently
adjusted; a measurement or an architecture decision is required.

## Overspeed and energy

The regression case uses `10,000 rpm`, then `12,000 rpm` at `1.20×`. The tip
speed at overspeed is `175.93 m/s`, Mach `0.467` at `80 °C`.

The thin-ring screen `σθ = ρv²` gives `82.64 MPa`, room-temperature ratio
`245/82.64 = 2.965`. Each synthetic blade weighs `38.13 g`; the direct model
`F = mω²r` gives `5.33 kN` and `38.06 MPa` at the root, ratio `6.44`. Both
screens pass, but ignore notch, bending, torsion, LPBF defects and HCF.

The analytical polar inertia is `0.00831 kg·m²`; the overspeed energy is
`6.56 kJ`. It is a hazard indicator, not a proof of containment.

## Modal, flow and thermal

The first mode of the simplified cantilevered blade is `556.5 Hz`; the
twelve-blade passing frequency is `2,000 Hz`, separation `72.2 %`. Passing this
screen does not replace a Campbell diagram of the alternator/housing assembly.

The flow `1.01 m³/s` and pressure rise `800 Pa` are synthetic targets: area
`0.05655 m²`, mean velocity `17.86 m/s`, air power `808 W` and ideal torque
`0.772 Nm`. Without blade angle/shape and a measured curve, no cooling
performance is computed.

At `150 °C` from `20 °C`, the diameter grows freely by `0.764 mm`. Fully
restrained, `σ = EαΔT = 191.1 MPa`; ratio `1.282`, hence **failure**. With the
housing incompatibility, the overall result stays red.

## Reproduction

```bash
docker run --rm --platform linux/amd64 -v "$PWD:/work" -w /work \
  ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57 \
  python parts/993-eng-cooling-impeller-alsi10mg-f0-0001/source/cooling_impeller.py \
  --out parts/993-eng-cooling-impeller-alsi10mg-f0-0001/derived/cooling_impeller_alsi10mg_f0.step \
  --report parts/993-eng-cooling-impeller-alsi10mg-f0-0001/evidence/engineering-screen.json
```

## Next gates

1. Measure the impeller, housing, hub, shaft, alternator, pulley and shim
   assembly.
2. Reconcile diameter, depth, tip clearance and thermal growth.
3. Scan the blades and measure speed, flow, pressure, temperature and noise.
4. Run rotating CFD and CHT with correlated rig curves.
5. Run centrifugal/thermal FEA, Campbell, HCF and blade loss.
6. Qualify LPBF, T6/HIP, machining, CT/FPI and two-plane balancing.
7. Pass contained overspeed, vibration, flow then engine-cell endurance.

PhysicsNeMo stays deferred until correlated rotating CFD,
structure/modal/HCF and rig series exist. The F0 is prohibited from
manufacture, rotation, installation and start-up.

<!-- print-screen:begin -->

## LPBF print simulation

The simulation was run and **failed closed**: none of the candidate orientations fits the EOS M 290 envelope (250 x 250 x 325 mm). No result is therefore published for this part, and no image is made up in its place.

<!-- print-screen:end -->
