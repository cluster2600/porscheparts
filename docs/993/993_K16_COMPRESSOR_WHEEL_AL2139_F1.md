# K16 compressor wheel — Al2139 AM F1 iteration

The AlSi10Mg F0 did its job: it failed. At tip Mach `0.9` and `1.2×`
overspeed, its straight main blade reached `390.9 MPa` against a
room-temperature comparison value of `245 MPa`, i.e. a ratio of `0.627`.

The F1 keeps exactly the only geometric facts published for the right-hand K16
wheel `53241232006`: inducer `40.6 mm`, exducer `60.5 mm`, six main blades and
six splitters. The change concerns the candidate material and the thickness
distribution, not a supposed OEM reconstruction.

## Engineering change

The main blade goes from a uniform `1.2 mm` to a linear law `3.0 → 0.8 mm`.
The splitter goes to `2.4 → 0.8 mm`. The locked CAD approximates each law with
four overlapping radial segments; the force calculation uses the exact
continuous integral of the thickness.

AlSi10Mg is replaced as candidate by EOS Aluminium Al2139 AM on the M 290,
`60 µm`, heat treated. For this route EOS publishes TRL `3`, a minimum wall of
`0.4 mm`, an average density of at least `2.84 g/cm³`, `0.2–0.3 %` average
defects, Rp0.2 `460 MPa`, vertical Rm `520 MPa` and vertical elongation `4 %`
at room temperature. These values are not rotor allowables.

## CAD result

The re-read STEP contains a valid BREP solid of `60.5 × 60.5 × 18 mm`, twelve
blades and a through bore. Its volume is `13,554.48 mm³` and its theoretical
mass `38.49 g`. An Al2139 envelope cylinder would weigh `146.96 g`, i.e. a
theoretical ratio of `3.82`. This is neither an industrial stock size nor a
cost calculation.

## Tapered blade calculation

For a linear thickness `t(r)`, the blade volume uses:

`V = h × L × (t_racine + t_pointe) / 2`

The centrifugal force uses the exact first radial moment:

`F = ρ × h × ω² × ∫ r × t(r) dr`

Then the root stress is screened by:

`σ = Kt × F / (t_racine × h)` and `σ_survitesse = σ × 1.2²`.

(`racine` = root, `pointe` = tip, `survitesse` = overspeed.)

The F1 main blade weighs analytically `1.380 g`, with a mean radius of
`16.382 mm`. It produces `2.654 kN`, `160.84 MPa` nominal and `231.61 MPa` at
overspeed. The splitter reaches `200.10 MPa` at overspeed.

The governing Al2139/stress ratio is therefore `1.986`, against `0.627` for the
F0, i.e. `40.75 %` less stress despite the higher density. The disc gives a
ratio of `2.516` and the fully constrained thermal bound `1.905`. All three
exceed the regression threshold of `1.5`.

**This only means that the F1 passes three room-temperature equations.** The
`460 MPa` limit comes from T4 specimens, the modulus and expansion remain
provisional, and no hot HCF is available. There is still no aerodynamic
profile, no K16 map and no complete rotor.

## Aerothermal point unchanged

The synthetic point remains `103,464 rpm`, `0.08194 m³/s` per bank, axial Mach
`0.190`, pressure ratio `1.8`, efficiency `0.72`, outlet `413.8 K` and power
`13.11 kW`. It serves only to compare F0 and F1 on the same basis.

Centrifugal plus thermal growth is `0.159 mm`, whereas the actual clearance is
unknown. The approximate rotational energy rises to `1,034 J`; ten mg·mm of
imbalance produce `1.17 N`. These values reinforce the requirement for a
contained spin rig and prove no strength.

## Reproduction

```bash
docker run --rm --platform linux/amd64 -v "$PWD:/work" -w /work \
  ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57 \
  python parts/993-eng-k16-compressor-wheel-al2139-f1-0001/source/compressor_wheel_f1.py \
  --out parts/993-eng-k16-compressor-wheel-al2139-f1-0001/derived/compressor_wheel_al2139_f1.step \
  --report parts/993-eng-k16-compressor-wheel-al2139-f1-0001/evidence/engineering-screen.json
```

## Next gates

1. Measure/CT the K16 wheel and the whole shaft-nut-backplate-housing assembly.
2. Build real blade surfaces from metrology and inverse aerodynamic design.
3. Obtain the map, speeds, temperatures, clearances, imbalance and duty cycle.
4. Run converged rotating CFD, FSI, centrifugal-thermal FEA, rotordynamics,
   Campbell, HCF and probabilistic burst analysis.
5. Qualify Al2139, orientation, supports, heat treatment, defects, finish,
   machining, CT and balancing.
6. Pass contained spin proof, overspeed and burst tests before any turbo bench.

PhysicsNeMo awaits correlated CFD-structure-rotordynamics series with train,
holdout and out-of-distribution sets. The F1 is authorized neither for
manufacturing, nor for rotation, nor for turbo or engine use.

<!-- print-screen:begin -->

## LPBF print simulation

The STEP was tessellated, then sliced over its full height at `60 µm`, on the EOS M 290 route of the candidate material. Orientation chosen by the automatic rule: `roll_y_45`.

| quantity | value |
|---|---:|
| layers | 873 |
| build height | 52.33 mm |
| layers with an unsupported region | 21 |
| support proxy | 22.17 mm³ |
| local thickness p01 | 0.183 mm |
| trapped powder at 1.00 mm | 0.00 mm³ |

![LPBF print simulation](../../parts/993-eng-k16-compressor-wheel-al2139-f1-0001/evidence/lpbf-f0/993-eng-k16-compressor-wheel-al2139-f1-0001-lpbf-geometry-screen.png)

This screening is neither an EOSPRINT project, nor a distortion calculation, nor a recoater check. **Printing remains prohibited.**

<!-- print-screen:end -->
