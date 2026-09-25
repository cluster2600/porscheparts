# 993 engine oil filter console — AlSi10Mg F0

This twentieth candidate is an engine console with two integrated oil
galleries. The benefit of additive manufacturing is specific: creating two
non-collinear paths, the filter base and the ports in a single body, without
cross-drilling plugs. A casting or 6061-T6 machining with plugs nevertheless
remains a competing solution to compare.

PorscheFanatics identifies `993 107 057 00` and `993 107 057 01` as consoles at
position 44 of group `101-10`, then the engine filter `993 107 203 03` and its
MAHLE equivalent `OC 229` at position 48. OEMVWShop declares `0.78 kg` for the
console `...01`, without a protocol. The OC 229 data sheet gives
`Ø76 × 101 mm`, `M20×1.5`; distributor data add `Ø72/62 mm`, `20 Nm` and
`333 g`. These values define the mating component, not the console.

## F0 geometry

The build123d master is entirely independent: `130 × 90 × 20 mm` body, `Ø82 mm`
filter base, unthreaded `Ø20 mm` boss, four synthetic holes and two `Ø16 mm`
ports. Two inclined, offset galleries connect the ports to an annular inlet and
to a central `Ø12 mm` outlet.

The STEP re-read in the locked CAD image contains a valid BREP solid of
`144 × 90 × 50 mm`, two galleries, four functional openings and no closed
powder volume. Its volume is `314,735.40 mm³` and its theoretical AlSi10Mg mass
`840.34 g`. The envelope box would weigh `1,730.16 g`, i.e. a stock/F0 ratio
of `2.06`.

The F0 mass is `1.073 ×` the commercial `780 g`, but this proximity validates
nothing: neither the weighing boundary, nor the surface, nor the OEM material
is known.

## Hot/cold hydraulics

The regression scenario imposes `30 L/min`, oil at `850 kg/m³`, an effective
roughness of `0.05 mm` and three segments `16/12/16 mm`. It uses:

`v = Q/A`, `Re = ρvd/μ`

`f = 64/Re` when laminar, otherwise the Haaland approximation,

`Δp = Σ[(fL/d + K)ρv²/2]`

The OCR occurrence from the manual indicates about `6.5 bar` at `5,000 rpm`
and `90 °C`, without visual verification. The regression threshold is
arbitrarily set at 5 %, i.e. `32.5 kPa`.

- hot, `μ = 0.012 Pa·s`: `28.82 kPa`, ratio `1.128` — **passes**;
- cold, `μ = 0.25 Pa·s`: `44.65 kPa`, ratio `0.728` — **fails**.

The calculation omits the filter medium, the bypass valve, the real local
losses, the fittings and the engine circuit. It therefore does not predict the
vehicle's oil pressure.

## Pressure, filter and thermal

At a synthetic proof pressure of `12 bar`, the membrane screen
`σ = pd/(2t)` with `d = 16 mm` and `t = 4 mm` gives `2.4 MPa`, i.e. a
room-temperature ratio to the limit of `102.08`.

The published filter torque is handled by `F = T/(Kd)` with `K = 0.20`, hence
`5,000 N`. On a synthetic `Ø72/62` ring, the mean pressure is `4.751 MPa`. An
assumed `12 mm` engagement gives `22.97 MPa` von Mises on the simplified thread
and a ratio of `10.67`. Both screens pass, but validate neither the real
thread nor the seal.

At `150 °C` from `20 °C`, the free growth over `144 mm` is `0.393 mm`. Fully
constrained, `σ = EαΔT` reaches `191.1 MPa`, i.e. a ratio of `1.282` against
the `1.5` threshold — **fail**.

## F0 decision

The consolidation of the galleries justifies the LPBF study, but the cold
hydraulic screen and the thermal screen fail. The process stays undecided
between casting, CNC 6061-T6 with qualified plugs and LPBF AlSi10Mg. Internal
cleanliness is a major gate: absence of trapped powder does not mean validated
depowdering or engine cleanliness.

## Reproduction

```bash
docker run --rm --platform linux/amd64 -v "$PWD:/work" -w /work \
  ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57 \
  python parts/993-eng-oil-filter-console-alsi10mg-f0-0001/source/oil_filter_console.py \
  --out parts/993-eng-oil-filter-console-alsi10mg-f0-0001/derived/oil_filter_console_alsi10mg_f0.step \
  --report parts/993-eng-oil-filter-console-alsi10mg-f0-0001/evidence/engineering-screen.json
```

## Next gates

1. Scan the console, case, filter, seals, sensors and lines.
2. Visually check the exact pressures and conditions in the manual.
3. Measure flow, viscosity, pulsed pressure, temperatures and contamination.
4. Rebuild the galleries and interfaces on measured datums and tolerances.
5. Run CFD/CHT, cavitation, pulsed pressure, contact, modal and fatigue.
6. Compare casting, CNC+plugs and LPBF on cost, mass, leakage and cleanliness.
7. Qualify orientation, T6/HIP, machining, CT, FPI, proof test, leak and flushing.
8. Pass a hot/cold hydraulic bench, then engine endurance and dyno.

PhysicsNeMo stays deferred until correlated CFD/CHT/structure/leak series exist,
split into training, validation, holdout and out-of-distribution. The F0 is
prohibited from manufacturing, oil circulation, installation and engine use.

<!-- print-screen:begin -->

## LPBF print simulation

The STEP was tessellated, then sliced over its full height at `30 µm`, on the EOS M 290 route of the candidate material. Orientation chosen by the automatic rule: `roll_y_45`.

| quantity | value |
|---|---:|
| layers | 3,960 |
| build height | 118.79 mm |
| layers with an unsupported region | 624 |
| support proxy | 5,546.77 mm³ |
| local thickness p01 | 0.914 mm |
| trapped powder at 1.00 mm | 0.00 mm³ |

![LPBF print simulation](../../parts/993-eng-oil-filter-console-alsi10mg-f0-0001/evidence/lpbf-f0/993-eng-oil-filter-console-alsi10mg-f0-0001-lpbf-geometry-screen.png)

This screening is neither an EOSPRINT project, nor a distortion calculation, nor a recoater check. **Printing remains prohibited.**

<!-- print-screen:end -->
