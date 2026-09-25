# 993 headlamp spring hook, AlSi10Mg — F0 twin

## Decision

The hook is a good first metal additive candidate: a small repair series, hollow
geometry, very low mass and a commercial precedent printed in aluminum or
stainless. Unlike a standard bolt, additive manufacturing can make sense for
restoring a function that has become hard to source.

The F0 is, however, not a copy of the commercial or Porsche part. No public
dimension of the hook or of its interface with the headlamp has been found. The
`16 × 8 × 15 mm` CAD is therefore an independent hypothesis meant to exercise
the software chain. It must not be printed for fitting, bonded, or installed.

References:
[Roadster-Fashion commercial hook](https://shop.roadster-fashion.de/de/reparaturteil-federhaken-am-scheinwerfer.html) and
[official EOS M 290 / AlSi10Mg / 30 µm route](https://www.eos.info/metal-solutions/data-sheets/aluminium/pds-eos-aluminium-alsi10mg-eos-m-290-30um).

## Material and process chosen for the screening

The candidate route is `EOS Aluminium AlSi10Mg`, material set
`AlSi10Mg_FlexM291 2.01`, EOS M 290, `30 µm` layers, as-built condition. The EOS
sheet publishes in particular a minimum density of `2.67 g/cm³`, a vertical
coupon yield strength of `233 MPa`, a minimum ultimate strength of `461 MPa`, a
vertical conductivity of `100 W/(m·K)` and an indicative minimum wall of
`0.4 mm`.

These values are coupon properties, not part allowables. Temperature-dependent
strength, the as-built surface, notches, the powder batch and the real
orientation must be qualified.

## Results run

| Domain | Execution | Useful result | Authority |
|---|---|---|---|
| Analytical equations | bending, shear, von Mises, deflection, mean bond, expansion | mass `2.352 g`; von Mises `15.348 MPa`; free growth `0.0352 mm` | synthetic regression |
| LPBF geometry | 4,000 probes and section of every layer | `425` layers; orientation `roll_y_45`; proxy supports `3.06 mm³`; no trapped powder at `0.25 mm` | screening, not EOSPRINT |
| CalculiX | six C3D10 runs, cold and hot, three meshes | fine p95 `10.786 MPa` cold and `141.898 MPa` hot; p95 variation fine/previous `0.47 %` and `2.84 %` | synthetic load case |
| OpenUSD | STEP conversion with `usd-convert-cad 0.2.0` | binary Z-up asset in millimeters | exchange compliance |
| NVIDIA validation | `nvidia_usd_validate 1.21.0` | asset and rigid scene with no failing rule | USD schema/quality |
| Rigid bodies | `ovstage 0.1.1.355824` + `ovphysx 0.5.11` CPU | witness settled from `22` to `17 mm` in `240` steps | software integration only |
| PhysicsNeMo | not run | six uncorrelated cases are insufficient to train a surrogate | blocked |
| OVRTX | not run for this F0 | RTX GPU not needed before real geometry | blocked |

The CalculiX hot local maximum is `303.467 MPa`, above the room-temperature
coupon yield strength. It sits near the rigid thermal clamp and does not
converge like the p95: it is a signal of a singularity or of an unfavorable
design to investigate, never a proof of failure or of integrity.

## What blocks printing

- scan or metrology of the broken hook, the seat and the spring;
- force, direction, travel, contact and number of cycles of the spring;
- temperature, radiation and vibration spectrum measured in the headlamp;
- adhesive, preparation, gap, shear and peel when hot;
- hot material card and heat treatment of the chosen EOS route;
- supports, orientation and supplier machine file;
- first article, CT/NDT, metrology, retention test, beam aim and a signed
  engineering review.

The evidence and its SHA-256 digests are gathered in
[`twins/993-headlamp-spring-hook-alsi10mg-f0/evidence/`](../../twins/993-headlamp-spring-hook-alsi10mg-f0/evidence/).

<!-- print-screen:begin -->

## LPBF print simulation

The STEP was tessellated, then sliced over its full height at `30 µm`, on the EOS M 290 route of the candidate material. Orientation chosen by the automatic rule: `roll_y_45`.

| quantity | value |
|---|---:|
| layers | 425 |
| build height | 12.73 mm |
| layers with an unsupported region | 1 |
| support proxy | 3.06 mm³ |
| local thickness p01 | 1.000 mm |
| trapped powder at 1.00 mm | 0.00 mm³ |

![LPBF print simulation](../../parts/993-elec-headlamp-spring-hook-f0-0001/evidence/lpbf-f0/993-elec-headlamp-spring-hook-f0-0001-lpbf-geometry-screen.png)

This screening is neither an EOSPRINT project, nor a distortion calculation, nor a recoater check. **Printing remains prohibited.**

<!-- print-screen:end -->
