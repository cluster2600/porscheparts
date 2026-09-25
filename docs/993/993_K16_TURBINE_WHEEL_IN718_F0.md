# K16 turbine wheel — IN718 F0 concept

This sixteenth distinct metal part of the program is the first model of the
hot K16 rotor. The additive benefit is real for a complex spare part produced
in low volume: twelve blades can be iterated without recreating foundry
tooling. That does not automatically make LPBF preferable. A qualified cast
nickel wheel remains the industrial reference to beat.

The F0 result is a **rejection**, which is useful: the model passes the
centrifugal disc check but fails at the blade root, at the thermal gradient and
at the selected temperature envelope. Nothing in this dossier authorizes
manufacturing or rotation.

## Facts and assumptions

TurboMaster links the right-hand K16 `5316-988-6735` of the 993 Turbo to the
wheel/shaft `5316-120-5000`. The Invasion supplier listing declares `54.96 mm`
at the inducer, `48.97 mm` at the exducer and twelve blades. A Kinugawa
replacement wheel for the same reference announces `49/55 mm`, a tip height of
`9.4 mm` and an `8.42 mm` shaft.

These are the only geometric facts used. The `20 mm` axial envelope, the disc,
the hub and the straight `2.4 → 0.8 mm` blades are the project's own
assumptions. Each continuous taper is represented in CAD by four steps. The
complete shaft, its joint, the profiles, the twist, the fillets, the
clearances and the balancing corrections are absent.

PorscheFanatics confirms the 993 twin-turbo context and the interest in hot-side
upgrades, but catalogues no additive wheel and no reusable K16 geometry.

## Candidate material

The screening uses EOS NickelAlloy IN718 API on the M 290, `40 µm` layer, after
heat treatment. EOS publishes TRL `9`, a typical minimum wall of
`0.3–0.4 mm`, a density of `8.15 g/cm³`, `0.03 %` average defects and, at room
temperature in the vertical direction, Rp0.2 `865 MPa`, Rm `1,236 MPa`,
elongation `28 %`.

These results are coupons tied to the API process. They give no HCF, no LCF,
no creep, no crack growth and no burst allowable for this rotor. EOS presents
IN718 generically for uses up to `700 °C`. The BorgWarner catalogue gives a T3
context of `950 °C` continuous for the upgrade line, but T3 is a gas
temperature, not a measured K16 metal temperature. The `250 °C` exceedance is
therefore a stop signal, not proof of melting.

## Computable CAD

The STEP re-read in the locked image contains a valid BREP solid of
`54.96 × 54.96 × 20.00 mm`, twelve blades and a shaft interface marker of
`8.42 mm`. The volume is `17,076.46 mm³` and the theoretical IN718 mass
`139.17 g`. An envelope cylinder would weigh `386.70 g`, i.e. a stock-to-part
ratio of `2.779`. The complete shaft is not modeled.

## Rotation and overspeed

Lacking a K16 speed trace, the rotor only shares the regression point of the
F1 compressor: compressor tip Mach `0.9`, giving `103,464 rpm`. The turbine tip
then reaches `297.74 m/s`.

For a blade of linear thickness `t(r)`:

`V = h × L × (t_racine + t_pointe) / 2`

`F = ρ × V × ω² × r_moyen`

`σ_racine = Kt × F / (t_racine × h)`

(`racine` = root, `pointe` = tip, `moyen` = mean.)

With `Kt = 2.5` and the `1.2×` overspeed, the stress reaches `701.50 MPa`. The
room-temperature Rp0.2/stress ratio is `1.233`, below the regression threshold
of `1.5`: **fail**.

The rotating disc is screened by
`σ = (3 + ν) / 8 × ρ × ω² × r²`. At overspeed it reaches `427.85 MPa`, i.e. a
room-temperature ratio of `2.022`: this screen alone passes.

## Thermal

The fully constrained bound uses
`σ_th = E × α × ΔT / (1 − ν)` with a synthetic `350 K` gradient. It gives
`1,528.17 MPa`, hence a room-temperature ratio of `0.566`: **fail**. The
modulus and Poisson's ratio are provisional; applying a room-temperature limit
to this hot case does not constitute a life calculation.

Extrapolating the EOS coefficient at `700 °C` up to the `950 °C` gas context,
the free radial growth would be `0.396 mm`. The actual clearance is not known
and the metal temperature cannot be equated with T3. The value only serves to
show that thermal–housing coupling is indispensable.

## Single-point power balance

The same compressor point requires `13.11 kW`. With an assumed mechanical
efficiency of `0.95`, the turbine must deliver `13.81 kW`, i.e. `1.274 N·m`.
For a synthetic AFR of `12`, a turbine efficiency of `0.70` and an outlet at
`110 kPa`, the ideal-gas balance requires an expansion ratio of `1.419`.

This result is neither a turbine map nor proof of flow. It ignores the
volute, the real blading, pulsations, the wastegate, leaks and bearing losses.

The approximate rotational energy of the F0 solid is `3.08 kJ`. An imbalance
of `10 mg·mm` produces `1.17 N`. In `100 h`, the model accumulates
`620.8 million` revolutions and `7.45 billion` blade passes. Without hot
HCF/LCF curves, the life calculation stays explicitly not computable.

## Reproduction

```bash
docker run --rm --platform linux/amd64 -v "$PWD:/work" -w /work \
  ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57 \
  python parts/993-eng-k16-turbine-wheel-in718-f0-0001/source/turbine_wheel.py \
  --out parts/993-eng-k16-turbine-wheel-in718-f0-0001/derived/turbine_wheel_in718_f0.step \
  --report parts/993-eng-k16-turbine-wheel-in718-f0-0001/evidence/engineering-screen.json
```

## Next gates

1. CT-scan the wheel `5316-120-5000`, the shaft and the joint.
2. Rebuild the measured profiles, fillets, hub surfaces and interfaces.
3. Measure speed, T3, metal temperature, pressures, flow, wastegate and cycle.
4. Compare qualified casting, machining and LPBF with a real wheel-shaft route.
5. Run converged rotating CFD, CHT, FSI, centrifugal-thermal FEA, Campbell,
   rotordynamics, creep, HCF/LCF and probabilistic burst.
6. Qualify powder, parameters, orientation, supports, heat treatment, HIP,
   machining, polishing, joint, CT, FPI, metallurgy and balancing.
7. Pass contained spin proof, overspeed and burst tests before any turbo bench.

PhysicsNeMo stays deferred: correlated CFD/CHT/structural series with training,
validation, holdout and out-of-distribution sets are needed first. The F0 is
prohibited from manufacturing, rotation, turbo and engine use.

<!-- print-screen:begin -->

## LPBF print simulation

The STEP was tessellated, then sliced over its full height at `40 µm`, on the EOS M 290 route of the candidate material. Orientation chosen by the automatic rule: `roll_y_45`.

| quantity | value |
|---|---:|
| layers | 1,183 |
| build height | 47.32 mm |
| layers with an unsupported region | 10 |
| support proxy | 59.60 mm³ |
| local thickness p01 | 0.133 mm |
| trapped powder at 1.00 mm | 0.00 mm³ |

![LPBF print simulation](../../parts/993-eng-k16-turbine-wheel-in718-f0-0001/evidence/lpbf-f0/993-eng-k16-turbine-wheel-in718-f0-0001-lpbf-geometry-screen.png)

This screening is neither an EOSPRINT project, nor a distortion calculation, nor a recoater check. **Printing remains prohibited.**

<!-- print-screen:end -->
