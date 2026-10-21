<a id="dimensionnement--mezger-4-l-biturbo-1-000-ch-moteur-sp95"></a>

# Sizing study: Mezger 4 L twin-turbo, 1,000 metric horsepower, SP95

English translation of the [retained French study](MEZGER_4L_SP95.md).
The original is preserved byte-for-byte because its SHA-256 is pinned in
[the historical delivery receipt](derived/flow4l/delivery-report.json).
This companion adds no calculation or qualification; the current
[bionic-family scope](BIONIC_FAMILY.md) remains separate from this earlier target.

The requested target in this study is a six-cylinder Mezger **4 L, twin-turbo,
four valves and two ignition points per cylinder, on SP95**, for bench and
track use. The calculations below determine conditional requirements; they
do not demonstrate that 1,000 metric horsepower is achievable on SP95 with
the donor.

The [calculator](source/mezger_sp95_budget.py) and [complete report](derived/mezger-sp95-budget.json)
retain assumptions, units, sensitivities, digests of the Python sources and
geometric check, and unknowns. No result is an engine-tuning instruction.

<a id="hypothèses-et-équations"></a>

## Assumptions and equations

| Input | Central-scenario value | Status |
|---|---:|---|
| Crankshaft power | 1,000 PS = 735.499 kW | Owner request, metric horsepower |
| Bore × stroke | 102 × 81.6 mm | 4 L study assumption, not a donor measurement |
| Calculated displacement | 4,000.660 cm³ | Six cylinders, four-stroke |
| Speed at target power | 7,000 rpm | Assumption, sweep 6,500–8,000 |
| Brake efficiency on lower heating value | 30% | Assumption, sweep 26–34% |
| Lambda | 0.82 | Assumption, sweep 0.78–0.86 |
| Fuel lower heating value / stoichiometric AFR / density | 42.5 MJ/kg / 14.4 / 745 kg/m³ | Calculation surrogate; SP95 batch uncharacterized |
| Volumetric efficiency | 100% at manifold density | Assumption, sweep 90–110% |
| Manifold air | 50 °C | Assumption, sweep 40–60 °C |
| Atmosphere / filter loss / charge-system loss | 1.01325 bar / 0.02 bar / 0.10 bar | Constant assumptions |
| Compressor isentropic efficiency / inlet temperature | 72% / 25 °C | Assumptions; map unselected |
| Heat to water from heads only | 12% of chemical power | Assumption, sweep 8–16% |
| Water: cp / density / temperature rise | 4,180 J/(kg·K) / 965 kg/m³ / 15 K | Water only, constant properties; mixture unselected |

SP95 here specifies **RON 95**. Ethanol content remains unknown: E5/E10 labels
are distinct from octane rating, and SP95 may be E10 depending on the market.
The JSON's three fuel-property triplets are illustrative sensitivities,
without a batch certificate or exact E5/E10 correspondence. See the primary
[Department for Transport explanation](https://www.gov.uk/guidance/e10-petrol-explained).

With P in W, Vd in m³ and n in rpm:

```text
Vd = 6 × π/4 × bore² × stroke
Torque = P / (2πn/60)
BMEP = 4π × torque / Vd                         [Pa, four-stroke engine]
Mean piston speed = 2 × stroke × n/60           [m/s]
Chemical power = P / brake efficiency
Fuel flow = chemical power / lower heating value [kg/s]
Air flow = fuel flow × AFR_stoich × lambda
p_manifold = air flow × R_air × T_manifold / (VE × Vd × n/120)
PR_compressor = (p_manifold + downstream loss) / (p_atmosphere − filter loss)
T_outlet = T_inlet × [1 + (PR^((γ−1)/γ) − 1)/η_compressor]
Q_charge_air_exchangers = air flow × cp_air × (T_outlet − T_manifold)
Q_head_water = fraction to heads × chemical power
Water flow = Q_head_water / (cp_water × ΔT_water) [kg/s]
Equivalent diameter = √(4 × volumetric flow / (π × selected velocity))
```

Efficiency is **brake** efficiency, which already incorporates engine losses
in its overall balance. New auxiliary consumption must be defined to retain
a consistent net target. Sweeps vary one input at a time: mixture, efficiency,
volumetric efficiency and knock are coupled in the actual engine.
Enrichment therefore does not guarantee the same power with less air, as an
isolated reading of the equation at fixed efficiency might suggest.

<a id="couple-et-contraintes-mécaniques"></a>

## Torque and mechanical constraints

Each row imposes **1,000 metric horsepower at that speed**: this is neither
a predicted torque curve nor a maximum-speed selection.

| Speed, rpm | Torque, N·m | BMEP, bar | Mean piston speed, m/s | Required manifold boost, bar |
|---:|---:|---:|---:|---:|
| 6,500 | 1,080.5 | 33.94 | 17.68 | 1.90 |
| 7,000 | 1,003.4 | 31.52 | 19.04 | 1.69 |
| 7,500 | 936.5 | 29.42 | 20.40 | 1.51 |
| 8,000 | 877.9 | 27.58 | 21.76 | 1.36 |

BMEP is **not** peak combustion pressure. To prepare future load cases,
purely hypothetical peaks of 140, 180 and 220 bar correspond, at a 102 mm
bore, to **114.4 / 147.1 / 179.8 kN** gas force.
These are neither predicted pressures nor allowable loads. Clamping, bearing
surfaces, inertia loads, fatigue and block/valvetrain strength remain to be
established on the exact variant.

The required total clearance volume per cylinder is Vc = (Vd/6)/(CR−1):

| Explored compression ratio | Total clearance volume, cm³ |
|---:|---:|
| 8.0:1 | 95.25 |
| 8.5:1 | 88.90 |
| 9.0:1 | 83.35 |
| 9.5:1 | 78.44 |

This volume includes the chamber, gasket, deck clearance and piston effect.
Do not copy it into the head cavity alone. None of these compression ratios
is selected or validated on SP95.

<a id="air-turbos-et-carburant"></a>

## Air, turbos and fuel

Central scenario: **207.7 kg/h**, or **278.8 L/h of fuel**, and **0.681 kg/s
of air** in total. Each turbo must therefore supply approximately
**0.341 kg/s, or 45.1 lb/min actual flow**, at a compressor pressure ratio of
**2.83**. This flow is not corrected to a supplier map's reference conditions.
The two turbos share flow equally here; this distribution remains to be checked.

Manifold pressure is **2.707 bar absolute**, or **1.694 bar gauge**.
The air model with γ=1.4 and cp=1,005 J/(kg·K) gives **168 °C** at the
compressor outlets and **80.9 kW** to reject in the air exchangers to obtain
50 °C in the manifold. These are steady-state requirements, not exchanger
dimensions. Selection requires efficiency, surge, choke, speed and turbine
backpressure maps over the entire engine range. Pressures must be absolute
when calculating PR; see [Garrett, reading maps and calculating pressure ratio](https://www.garrettmotion.com/wp-content/uploads/2018/05/Garrett-Performance-Products-Catalog.pdf).

| Assumed efficiency | Specific fuel consumption, g/kWh | Fuel, L/h | Air, kg/s | Calculated boost, bar |
|---:|---:|---:|---:|---:|
| 26% | 325.8 | 321.6 | 0.786 | 2.11 |
| 30% | 282.4 | 278.8 | 0.681 | 1.69 |
| 34% | 249.1 | 246.0 | 0.601 | 1.38 |

With **six port injectors**, an assumed 80% duty cycle and 3 bar injector
differential pressure, the central requirement is **968 cm³/min per injector**
for the assumed fuel. A 25% flow reserve gives **348 L/h pump flow at about
4.69 bar above tank pressure** if the regulator maintains 3 bar above the
manifold. Line losses are additional; a zero-pressure flow rating is
insufficient. Injector data must use the same fluid and differential pressure,
including dead times and injection window. This calculation selects neither
injectors nor a pump.

**SP95 point: no “safe” boost follows from RON alone.** Charge temperature,
chamber, bore, plug positions, compression ratio and ignition change the knock
limit, as [Garrett explains](https://www.garrettmotion.com/knowledge-center-category/oem/advanced/).
The requested twin ignition remains a proposal to characterize in combustion:
no power, ignition-advance or knock-resistance benefit is credited.
The engine must be able to reduce load if the measured limit requires it;
1,000 metric horsepower remains a target to check on the bench with actual fuel.

<a id="eau--conséquence-directe-pour-la-culasse-picogk"></a>

## Water: direct consequence for the PicoGK head

At the central point, the heads reject **294.2 kW**, or **49.0 kW per head**.
At ΔT=15 K this requires **291.7 L/min** for all six, **145.9 L/min per bank**
and **48.6 L/min per head**, with six balanced parallel branches.
Cylinders, oil and turbos are not included in this water load. Their share
remains within the balance's unassigned 1,422 kW; it cannot be added
arbitrarily to the head radiator.

| Fuel-energy fraction to heads | Total heat, kW | Water at ΔT=15 K, L/min | Per head, L/min | Equivalent inner Ø at 3 m/s, mm |
|---:|---:|---:|---:|---:|
| 8% | 196.1 | 194.5 | 32.4 | 15.14 |
| 12% | 294.2 | 291.7 | 48.6 | 18.55 |
| 16% | 392.3 | 389.0 | 64.8 | 21.41 |

The combined range of thermal sweeps alone, at 30% efficiency, gives
**24.3–97.2 L/min per head** and **13.1–26.2 mm** equivalent diameter for
3 m/s (fractions 8–16%, ΔT=10–20 K). This is neither a statistical interval
nor a guaranteed envelope. Antifreeze mixture and temperature-dependent
properties will change these values. [IAPWS reference formulations](https://iapws.org/technical-guidance/release/LiquidWater)
can later replace the water constants; they were not evaluated in this
simplified calculation.

The existing bionic study's ports have a section of about **75.842 mm²**,
according to the [geometric check](derived/architecture-report.json).
Their mean velocity would be **10.69 m/s** at the central point.
The corresponding dynamic pressure is **0.551 bar**; it is not the circuit's
pressure loss. Section changes, bends, channels and roughness require
hydraulic/CFD calculation before selecting a pump.

For the next geometry variant, reserve at this calculation point both an
inlet **and** an outlet section equivalent to **18.55 mm inner diameter**,
and about **32.12 mm** for each bank manifold, if 3 m/s is retained as an
exploratory target. Connections, internal branches and their distribution
must accommodate this flow; this diameter alone does not size the network.
This calculation modifies no previously attested STL/VDB files.

The studied part remains four-valve/twin-ignition. The two existing 7 mm
wells are reservations, not spark-plug threads or qualified interfaces.
The [Performance Developments photographs](https://performancedevelopments.com/porsche-962c-race-engine-part-3/)
show construction modified by that engine builder with separated liners;
they provide neither a Mezger donor's interfaces nor its water galleries.
Axis dimensions, seats, valvetrain, inserts and the volumes required for twin
ignition remain to be measured/defined.

<a id="matériau-et-peltier"></a>

## Material and Peltier

Conduction alone gives ΔT = surface heat flux × thickness / conductivity.
At **3 MW/m²** and **4.5 mm**, hypothetical conductivities of
100 / 160 / 220 / 320 W/(m·K) give **135 / 84.4 / 61.4 / 42.2 K** temperature
differences across the metal. This includes neither convection nor interface
resistance; actual heat flux is unmeasured.

High conductivity alone therefore does not select the head material.
The supplier itself distinguishes [conductivity-oriented Aheadd CP1 from temperature/strength-oriented HT1](https://www.constellium.com/products/aluminium-powders/).
The sweep values are assigned to neither alloy. Conductivity as a function
of T, thermal fatigue, creep, expansion, seat/guide retention and the LPBF
process must be documented before choosing aluminum or copper alloy.
No material is qualified here.

The Peltier balance reuses the existing calculator without inventing a module
efficiency. Absorbing the heads' **294.2 kW** with COP=1 would require
**294.2 kW electrical power at the modules**, **326.9 kW at the bus** with
90% conversion, and **621.1 kW rejected to ambient**, including the converter.
At 48 V this is **6,810 A**, before pumps and fans. Even at COP=2 the bus
would require 163.4 kW. Primary cooling retained for subsequent sizing is
therefore a water/radiator loop; any Peltier remains limited to a separate
auxiliary study. Engine-driven supply would increase engine requirements
and require recalculation of the net balance.

<a id="chaîne-doutils-et-vérification"></a>

## Toolchain and verification

This stage provides sizing conditions to pass to the
[repository's documented toolchain](../../docs/TOOLCHAIN.md).
It does not turn a 0D balance into a cylinder-head simulation.

| Stage | Result or dependency |
|---|---|
| Sources and metrology | Sources cited; exact donor, interfaces and fuel batch unknown |
| Python calculation | Power, air, fuel, water, section and sensitivity budget actually executed |
| Local Qwen | Actual r3 execution; invalid response rejected, no equation integrated |
| PicoGK / ShapeKernel / LatticeLibrary / VDB | Existing geometry preserved; new flow requirements above |
| Gmsh / OpenFOAM / CalculiX | Not run in this stage; conformal metal/water interface and loads to establish |
| USD / render | No new geometry or render produced by this calculation |
| LPBF / correlation / bench | Process, coupons, metrology, combustion measurements and professional review required |

Reproduce from the repository root with Python 3.12, as in CI:

```sh
python3 twins/962-cylinder-head-f0/source/mezger_sp95_budget.py
python3 -m unittest discover -s tests -p 'test_962_mezger_sp95_budget.py' -v
```

The Qwen response and receipt are retained in [this run's archive](derived/qwen-assistance/mezger-sp95-r3/review.json).
The response violates the no-code request, uses `lambda` as a Python variable
and degrades the rpm → rad/s factor from 60 to 6. It is truncated at 768 tokens
and was not executed. The review is therefore rejected; it provides no
additional validation.

The six tests independently check the energy balance, power/BMEP relation,
air/water/section continuity, sensitivities, invalid-input rejection, Qwen-run
digests and consistency of the stored report. All qualification flags remain
false; allowable boost on SP95 remains `null`.
