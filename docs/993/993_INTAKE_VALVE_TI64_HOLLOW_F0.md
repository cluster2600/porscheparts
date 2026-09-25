# 993 hollow intake valve — Ti64 LPBF F0 concept

For the reference `99310540902`, FVD publishes a `49 mm` head, an `8 mm` stem,
a mass of `120 g` and a commercial package size of `50 × 110 × 50 mm`. The
sheet provides no functional length, profile, seat, groove, material or
tolerance. PorscheFanatics identifies titanium valves in the Swindon
four-valve kit, without establishing the grade or the compatibility with the
two-valve M64 cylinder head.

The F0 therefore uses only the published diameters. Its `109 mm` length, its
`3 mm` flat head, its conical transition, its cavity, its `5 mm` axial bore and
its four `1.2 mm` ribs are independent hypotheses.

## Why study additive

The LPBF interest is not to reproduce a solid valve, better obtained by forging
and machining. It is to make a hollow head and stem in a single body, with
internal ribs distributed according to the loads. The bore stays open at the
tip to attempt depowdering; its closure, inspection and retention are not
defined. The mandatory comparison remains:

1. solid forged and machined titanium valve;
2. conventional or friction-welded hollow valve;
3. hollow LPBF Ti-6Al-4V body with qualified closure.

## Geometry obtained

The re-read STEP contains one valid BREP solid of `49 × 49 × 109 mm`. Its volume
is `12,545.86 mm³` and its theoretical mass `55.45 g` at `4.42 g/cm³`. A solid
shape sharing exactly the same synthetic exterior would weigh `72.38 g`: the
hollow removes `23.38 %`. The `64.55 g` difference against the published
`120 g` is not an OEM saving, because the commercial sheet and the F0 do not
define the same geometry.

## Mathematical screenings

The regression case takes `6,720 rpm`, `12 mm` of lift over `240°` of
crankshaft, a `520 N + 40 N/mm` spring, a `0.20 MPa` differential, `+400 K` and
`100 h`. A simple harmonic law gives an event duration of `5.95 ms`, a maximum
velocity of `6.33 m/s` and an acceleration of `6,685 m/s²`. With the CAD mass,
the inertia is `371 N` and the axial screening force, spring and pressure
included, `1.75 kN`.

The annular stem section gives `57.1 MPa` in nominal tension/compression and
Euler `20.5 kN`. The idealized circular head plate gives `6.23 MPa` and
`0.0037 mm`. These room-temperature margins cover neither the seat, nor the
guide, nor the keepers, nor impact, nor LPBF defects.

The first cantilevered-beam mode is only `190.8 Hz`, i.e. `3.41` times the
event frequency of `56 Hz`: this result calls for a modal analysis of the
complete system and does not constitute an acceptable frequency separation.
Over `100 h`, the count reaches `20.16 million` events without predicting a
life.

Free expansion is `0.392 mm`. The fully restrained bound is `396 MPa`, while the
1D axial conduction is only `1.37 W` with the Ti64 comparison properties.
Temperatures must therefore be measured and the seat-guide thermal contacts
resolved before any conclusion.

## Software reproduction

```bash
docker run --rm --platform linux/amd64 -v "$PWD:/work" -w /work \
  ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57 \
  python parts/993-eng-intake-valve-ti64-hollow-f0-0001/source/intake_valve.py \
  --out parts/993-eng-intake-valve-ti64-hollow-f0-0001/derived/intake_valve_ti64_hollow_f0.step \
  --report parts/993-eng-intake-valve-ti64-hollow-f0-0001/evidence/engineering-screen.json
```

## Next gates

1. Measure a removed valve, its seat, guide, keepers, retainer, spring, cam,
   rocker and piston-to-valve clearances.
2. Instrument lift law, pressure, temperature, impact, float, bounce,
   lubrication and duty cycle.
3. Rebuild the interfaces with tolerances, surface finish, coatings, hardness,
   allowances and real closure.
4. Solve multibody then contact/modal/thermal/HCF-LCF FEA with convergence,
   defects and oriented hot Ti64 properties.
5. Qualify orientation, supports, depowdering, heat treatment, HIP, machining,
   alpha case, CT, cleanliness, closure and balancing.
6. Hot-test the full-scale valve, then a motored cylinder head and an engine on
   the dyno under professional review.

PhysicsNeMo waits for correlated multibody-thermal-structure series with
training, holdout and out-of-distribution splits. SimReady waits for the
measured assembly. This F0 STEP is authorized neither for manufacture, nor for
fitting, nor for an engine.

<!-- print-screen:begin -->

## LPBF print simulation

The STEP was tessellated, then sliced over its full height at `30 µm`, on the EOS M 290 route of the candidate material. Orientation chosen by the automatic rule: `roll_y_45`.

| quantity | value |
|---|---:|
| layers | 3,241 |
| build height | 97.23 mm |
| layers with an unsupported region | 254 |
| support proxy | 1,002.61 mm³ |
| local thickness p01 | 1.200 mm |
| trapped powder at 1.00 mm | 0.00 mm³ |

![LPBF print simulation](../../parts/993-eng-intake-valve-ti64-hollow-f0-0001/evidence/lpbf-f0/993-eng-intake-valve-ti64-hollow-f0-0001-lpbf-geometry-screen.png)

This screening is neither an EOSPRINT project, nor a distortion calculation, nor a recoater check. **Printing remains prohibited.**

<!-- print-screen:end -->
