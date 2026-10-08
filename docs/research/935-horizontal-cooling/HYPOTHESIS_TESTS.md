# Hypothesis tests — horizontal 935 system

Campaign run on October 7, 2026 on Kali2/ext4, without Vast. It complements
the [27 initial kinematic scenarios](HYPOTHESES.md) with **160 reduced-system
scenarios** and **nine CalculiX runs** on an ideal ring.
The six groups of the [existing calculator](../../../twins/935-horizontal-cooling-system-f0/source/build_system_twin.py)
are run: speeds, kinematics, inertia/imbalance, air network, transmission
budget and thermal. No scan, former proxy geometry or
assumed mounting interface is used as reference geometry.

## Chosen parameters and how to replace them

All the following physical parameters are campaign assumptions.
Zero uncertainties describe fixed points, not a measured precision.

| Domain | Assumptions | Required confrontation |
|---|---|---|
| Reduced rotor | Ring Ø 275 mm, bore Ø 40 mm, thickness 4 mm; nine equivalent blade masses of 6 cm³ each, at a radius of 100 mm. | Volume and inertia of the calibrated reconstruction; measured mass and balancing. The point masses ignore the blades' own inertia. |
| Speeds | 3,000, 6,000, 8,500, 11,000 rpm; total ratio 1 and zero slip. | Simultaneous engine/rotor speeds. 11,000 rpm is an exploration point, not an authorized speed. |
| Braking | Constant deceleration to zero in 0.1 or 1 second. | Tachometer trace, inertias of the whole transmission, behavior of the coupling and the belt. |
| Transmission | Steady-state efficiency 95%, pulley pitch radius 50 mm, gear pitch diameter 40 mm, solid shaft Ø 16 mm. | Measurements of the disassembled mechanism and definition of the gear teeth, shafts, bearings and losses. |
| Air | Curve chosen at 6,000 rpm: `(Q,Δp,η)` = `(0,1200,0.4)`, `(0.6,1050,0.65)`, `(1.2,650,0.55)`, `(1.8,0,0.2)`; units m³/s, Pa, 1, decimal point notation. | Accepted CFD curves, then bench, at the same total-pressure stations. No Porsche curve is claimed. |
| Network | Six equal branches of 15,000 Pa·s²/m⁶, one leak of 50,000, common resistance of 100; two global multipliers: 0.5 and 2. | Passage geometry and loss measurements. The six branches are fictitious zones, not the six identified cylinders. |
| Thermal | Air: 1.15 kg/m³, 1,005 J/(kg·K), inlet at 25 °C. Each zone: 3 kW, UA = 150 W/K, capacity 8 kJ/K, initially 100 °C; 60 s time step. | Engine loads, thermal resistances and temperature measurements. No exchange with the oil and no gradient in the rotor is simulated. |

The existing cards cover AlSi10Mg, AlF357, Ti‑6Al‑4V, WE43, 316L,
17‑4PH, IN718, CoCr MP1, M300 and CuCrZr. Density and modulus are taken
as comparison values, with their sources and digests in the
outputs. Isotropy and ν = 0.33 are assumed for all metals.
**No yield strength, safety margin, fatigue life or allowable
speed is calculated.** The WE43 data remain unqualified surrogates
for the printed part. The [EOS Ti64 data sheet](https://www.eos.info/metal-solutions/data-sheets/all-processes-and-materials?id=eos-titanium-ti64)
shows why machine, orientation and treatment must accompany a
material property; the cards do not constitute a production dossier.

## Independent centrifugal check

The witness is **the ring only**, without the nine blade masses. Its
radial edges are free. The half-thickness is modeled in CAX8, with
axial symmetry at the mid-plane, and three meshes of 16, 32, 64 radial
elements, each with two elements through the half-thickness. The nine runs
are fresh solves for AlSi10Mg, WE43 and Ti64 at 8,500 rpm.

The CAX8 conventions (`x` radial, `y` axial) and the `CENTRIF = ω²` load
follow the documentation by the author of CalculiX, [axisymmetric elements](https://web.mit.edu/calculix_v2.7/CalculiX/ccx_2.7/doc/ccx/node51.html)
and [centrifugal load](https://web.mit.edu/calculix_v2.7/CalculiX/ccx_2.7/doc/ccx/node148.html).
The input deck uses mm, N, s, tonne; the system calculations use SI.
The density in g/cm³ is multiplied by 10⁻⁹ for the CalculiX deck.

The constant-thickness plane solution satisfies:

\[
\sigma_r=\frac{3+\nu}{8}\rho\omega^2
\left(a^2+b^2-r^2-\frac{a^2b^2}{r^2}\right),\qquad
\sigma_\theta=\frac{3+\nu}{8}\rho\omega^2
\left(a^2+b^2+\frac{a^2b^2}{r^2}-\frac{1+3\nu}{3+\nu}r^2\right).
\]

The independent software check verifies zero radial tractions at
both edges and the equilibrium `dσr/dr + (σr−σθ)/r + ρω²r = 0`.
The [NASA method for rotating disks](https://ntrs.nasa.gov/api/citations/19960021252/downloads/19960021252.pdf)
documents this equilibrium and the plane-stress assumptions; it
distinguishes the disk loads, the blade loads and the thermal effects.
The latter are excluded from our witness.

| Hypothetical material | Analytical von Mises peak of the ring | CalculiX, fine mesh | Maximum analytical radial displacement |
|---|---:|---:|---:|
| WE43 | 22.92 MPa | 22.56 MPa | 0.01608 mm |
| AlSi10Mg | 33.44 MPa | 32.92 MPa | 0.01478 mm |
| Ti64 | 55.10 MPa | 54.25 MPa | 0.01550 mm |

The final stress deviation is 1.54%; the variation between the two
fine meshes is 1.55%. The displacement deviation is below 0.004%.
The witness thresholds are: analytical deviation below 2% in stress
and 1% in displacement, variation between the two fine meshes below 5%.
All three materials meet these criteria. The first 8/16/32-element run
still reached a 3.04% peak deviation; it is kept separately and
motivated the refinement. The peak at the integration points converges toward the
free-edge peak; no nodal stress extrapolation is used.
This check does not qualify the blade roots or the rotor mounting.

## Transmission loads: first useful result

At 8,500 rpm, with the network at multiplier 2 and a stop in 0.1 s:

| Reduced rotor material | Assumed mass | Rotational energy | Inertial braking torque, absolute value | Torque envelope including air load |
|---|---:|---:|---:|---:|
| WE43 | 0.524 kg | 2.02 kJ | 45.36 N·m | 49.56 N·m |
| AlSi10Mg | 0.765 kg | 2.95 kJ | 66.19 N·m | 70.38 N·m |
| Ti64 | 1.261 kg | 4.85 kJ | 109.07 N·m | 113.26 N·m |

The inertial torque is divided by ten when the stop takes one second.
The envelope is the **sum of the absolute values** of the inertial and aerodynamic torques;
it is not their signed sum during braking. It serves to prepare the
load cases, without simulating the elasticity, backlash or shocks of the mechanism.
For the AlSi10Mg scenario, it gives 3.52 kN of tangential force on
the assumed Ø 40 mm gear and 87.51 MPa of torsional shear stress in
the assumed Ø 16 mm solid shaft. No shaft material or allowable is
assigned. The steady-state rotor torque in this same scenario is 4.19 N·m.
The sizing will therefore have to cover the transients of the whole drive train.

The flow of the **fictitious network** in this scenario is 1.349 m³/s, of which 1.236
in the cooled zones and 0.113 in the leak. The power at the rotor
shaft is 3.732 kW and that at the angle-drive input 3.928 kW. One fictitious zone
reaches 72.81 °C after 60 s, with a steady-state limit of 51.96 °C.
These are consequences of the chosen curve and loads, with no predictive
value for the specimen. Changing the metal alone here keeps the air
curve and the thermal zones: blade deformations are not coupled.

## Reproduction and checks

From the repository root, on Linux with CalculiX already installed:

```sh
OMP_NUM_THREADS=1 PYTHONNOUSERSITE=1 python3 twins/935-horizontal-cooling-system-f0/source/run_hypothesis_tests.py --ccx --output work/935-hypothesis-tests-new
python3 -m unittest discover -s tests -p test_935_hypothesis_tests.py -v
```

Without `--ccx`, the 160 reduced scenarios are run alone. Use a
new private destination. Each case keeps its inputs and outputs;
the CalculiX decks, logs, results, source digests and manifest are
saved. The flow, pressure, power and braking-work balances
have relative residuals below 5×10⁻¹⁶ in the final campaign.
The witness and system checks are recorded in `results.json`.
The thresholds are numerical checks, without physical validation of the twin.

The final campaign uses Python 3.14.7 and CalculiX 2.23. At commit
`7e8c5c4c`, `make check` passes on Kali2/ext4: 3,559 tests discovered,
181 skipped for optional dependencies, then all the complementary
checks. The 6,778 source files compared match the
local digests. The [CI of the same commit](https://github.com/cluster2600/porscheparts/actions/runs/37690829623)
also passes.

To reproduce the general check, use `umask 022` and
`PYTHONNOUSERSITE=1 OMP_NUM_THREADS=1 make check`. Two environment failures
are kept: group-writable fixtures under `umask 002`,
then incomplete OCP bindings in the user directory. The safety guards
and installed dependencies were not modified; the accepted check uses
the isolated system environment already used for the campaign.

The three attempts, exact sources, decks, results, logs and plots
are in the [verified private delivery](https://github.com/cluster2600/porscheparts-935-private/releases/tag/hypothesis-load-tests-20261007).
The archive keeps 742 files verified by SHA-256, with no scan.
