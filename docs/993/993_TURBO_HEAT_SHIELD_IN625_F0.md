# 993 left turbo heat shield — IN625 F0 concept

The PorscheFanatics catalogue confirms `993 123 113 51` in turbo group
`202-16`. FVD publishes for this part an envelope of **160 × 110 × 105 mm**, a
mass of **0.23 kg** and a 993 Turbo/GT2 application. No surface, thickness,
fastener, tolerance, temperature or material is published.

The model keeps only this envelope. Its open trapezoidal vault, its nominal
`0.8 mm` wall, its three bosses and their bores are an independent topology.
The volume stays fully open, hence no trapped powder.

## AM benefit and sheet-metal competition

LPBF IN625 would allow a conformal shell with integrated bosses and local
stiffeners, useful for a small series and a complex thermal geometry. But
stamped or assembled sheet metal remains the reference process to beat.

The F0 weighs theoretically `325.58 g`, i.e. `41.6 %` more than the `230 g`
published by FVD. Since the material of the commercial product is unknown,
this result is not a validation by mass; above all, it prevents declaring AM
the winner without further optimization and cost comparison.

## Screenings run

The report recalculates:

- polygonal volume and mass `rho V`;
- bending of a local strip by `I=b t³/12`, `M=F L/4`, `sigma=M c/I` and
  `delta=F L³/(48 E I)` under a synthetic `50 N`;
- mean bearing pressure of the three bosses;
- free expansion `alpha L delta_T`;
- fully constrained bound `E alpha delta_T`;
- radiation `epsilon sigma A (T1⁴-T2⁴)` with hypothetical temperatures,
  emissivity and view factor;
- areal conductive resistance `t/k` and thermal capacity `m c_p`;
- single OCCT BREP, analytical volume and STEP re-read.

The shell gives `175.78 MPa` in nominal bending, `0.646 mm` of deflection and
`0.783 mm` of free expansion. The fully constrained bound reaches
`997.74 MPa`, above the `640 MPa` room-temperature comparison value: the
fasteners will have to allow expansion. This is not a vehicle prediction.

## Next gates

1. Scan the part and record hot/cold surfaces, fasteners and clearances.
2. Measure temperatures, fluxes, emissivity, airflow and the limit of the
   protected components.
3. Define vibration, preloads and thermal cycles.
4. Compare sheet metal and LPBF on mass, cost, distortion, finish and endurance.
5. Run nonlinear shell, modal, conjugate heat transfer, oxidation, creep and
   thermal fatigue with a qualified IN625 map.
6. Inspect, then test on a thermal and vibration bench before the vehicle.

PhysicsNeMo will wait for a set of correlated CAE cases or tests. The SimReady
step is deferred until measured interfaces and qualified hot properties exist;
the F0 STEP is not a manufacturable part for installation.

<!-- print-screen:begin -->

## LPBF print simulation

The STEP was tessellated, then sliced over its full height at `40 µm`, on the EOS M 290 route of the candidate material. Orientation chosen by the automatic rule: `build_x`.

| quantity | value |
|---|---:|
| layers | 4,000 |
| build height | 160.00 mm |
| layers with an unsupported region | 177 |
| support proxy | 6,092.64 mm³ |
| local thickness p01 | 0.800 mm |
| trapped powder at 1.00 mm | 0.00 mm³ |

![LPBF print simulation](../../parts/993-eng-turbo-heat-shield-in625-f0-0001/evidence/lpbf-f0/993-eng-turbo-heat-shield-in625-f0-0001-lpbf-geometry-screen.png)

This screening is neither an EOSPRINT project, nor a distortion calculation, nor a recoater check. **Printing remains prohibited.**

<!-- print-screen:end -->
