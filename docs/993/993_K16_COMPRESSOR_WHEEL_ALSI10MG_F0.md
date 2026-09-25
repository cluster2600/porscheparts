# 993 K16 compressor wheel — AlSi10Mg LPBF F0 concept

A supplier listing for the right-hand K16 `53169886735` declares for the wheel
`53241232006` an inducer of `40.6 mm`, an exducer of `60.5 mm` and `6 + 6`
blades. It gives no profile, no height, no hub, no bore, no tolerance and no
material. PorscheFanatics places the two turbochargers in the 993 intake chain
and lists upgrade wheels, but no additively manufactured K16 wheel.

The F0 therefore keeps only the two diameters and the blade count. Its `3 mm`
disc, its `18 mm` height, its `6 mm` bore, its hub and its straight `1.2 mm`
blades are independent assumptions.

## Why study additive

Twelve blades, their fillets and the hub can be produced and iterated without
foundry tooling. LPBF is, however, only relevant if an optimized geometry or
internal features bring a gain that five-axis machining does not. Roughness,
defects, distortion and HCF strength may on the contrary make LPBF inferior.

The mandatory comparison remains:

1. cast and qualified aluminum wheel;
2. wheel cut on five axes from a billet;
3. AlSi10Mg LPBF wheel, machined, balanced and qualified in overspeed/burst.

## Geometry obtained

The re-read STEP contains a valid BREP solid of `60.5 × 60.5 × 18 mm`, six main
blades, six splitters and a through bore. Its volume is `12,248.31 mm³` and its
theoretical mass `32.70 g`. A solid envelope cylinder would weigh `138.16 g`,
i.e. a theoretical stock ratio of `4.22`. This cylinder is neither an
industrial stock size nor an economic proof.

## Synthetic aerodynamic point

At `330 K`, tip Mach `0.9` gives `327.75 m/s` and a derived speed of
`103,464 rpm`. For one bank of a `3.6 l` engine at `5,750 rpm`, volumetric
efficiency `0.95`, the geometric flow is `0.08194 m³/s`. With an assumed
inducer hub of `12 mm`, the axial velocity is `69.35 m/s`, Mach `0.190`,
Reynolds `281,588` and the flow coefficient `0.212`.

At pressure ratio `1.8` and synthetic efficiency `0.72`, the calculated outlet
temperature is `413.8 K`, the work `84.23 kJ/kg`, the power per bank
`13.11 kW` and the torque `1.21 N·m`. This point is not a K16 map and deals
with neither surge, nor choke, nor incidence, nor real efficiency.

## Mechanical screening — F0 rejected

The idealized rotating disc reaches `119.4 MPa`, then `171.9 MPa` at `1.2×`
overspeed. The straight main blade reaches `271.5 MPa` at the nominal point and
`390.9 MPa` at overspeed. Against the EOS room-temperature comparison value of
`245 MPa`, the ratio is only `0.627`: **the F0 topology fails** and must not go
on to detailed CFD/FEA without resizing.

The combined elastic and thermal growth is `0.147 mm`, whereas the actual
clearance is unknown. The fully constrained thermal bound is `220.5 MPa`. Ten
mg·mm of imbalance already produce `1.17 N`. The approximate rotational energy
is `878 J` and the count reaches `620.8 million` revolutions in `100 h`. None of
these results proves strength, balance or containment.

## Software reproduction

```bash
docker run --rm --platform linux/amd64 -v "$PWD:/work" -w /work \
  ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57 \
  python parts/993-eng-k16-compressor-wheel-alsi10mg-f0-0001/source/compressor_wheel.py \
  --out parts/993-eng-k16-compressor-wheel-alsi10mg-f0-0001/derived/compressor_wheel_alsi10mg_f0.step \
  --report parts/993-eng-k16-compressor-wheel-alsi10mg-f0-0001/evidence/engineering-screen.json
```

## Next gates

1. Scan/CT the right-hand and left-hand wheels, then measure profiles, hub,
   bore, nut, shaft, backplate, diffuser, housing, clearances and balancing
   datums.
2. Obtain compressor maps, speeds, pressure/temperature, accelerations,
   surge/choke, imbalance and duty cycle.
3. Rebuild the blades with aerodynamic surfaces, fillets, machining
   allowances, tolerances and real interfaces.
4. Run converged rotating CFD, then FSI/centrifugal-thermal FEA, contact,
   rotordynamics, Campbell, HCF and probabilistic burst.
5. Qualify AlSi10Mg, orientation, supports, distortion, heat treatment, HIP,
   blade finishing, CT, metrology, balancing and spin proof.
6. Test on a contained spin rig, then turbo on the bench, then engine, under
   review by a turbomachinery specialist.

PhysicsNeMo awaits correlated CFD-structure-rotordynamics cases with train,
holdout and out-of-distribution sets. SimReady awaits the measured assembly.
This F0 STEP is authorized neither for manufacturing, nor for rotation, nor for
turbo or engine use.

<!-- print-screen:begin -->

## LPBF print simulation

The STEP was tessellated, then sliced over its full height at `30 µm`, on the EOS M 290 route of the candidate material. Orientation chosen by the automatic rule: `roll_y_45`.

| quantity | value |
|---|---:|
| layers | 1,745 |
| build height | 52.33 mm |
| layers with an unsupported region | 6 |
| support proxy | 0.16 mm³ |
| local thickness p01 | 0.270 mm |
| trapped powder at 1.00 mm | 0.00 mm³ |

![LPBF print simulation](../../parts/993-eng-k16-compressor-wheel-alsi10mg-f0-0001/evidence/lpbf-f0/993-eng-k16-compressor-wheel-alsi10mg-f0-0001-lpbf-geometry-screen.png)

This screening is neither an EOSPRINT project, nor a distortion calculation, nor a recoater check. **Printing remains prohibited.**

<!-- print-screen:end -->
