# 993/993 Turbo connecting rod — Ti64 F0 topology concept

TZR/PAUTER publishes for its 993/993 Turbo connecting rod a center distance of
`127.00 mm`, a pin of `23.01 mm`, a big-end bore of `58.01 ± 0.003 mm`, widths
of `18.75 mm` and `19.58 mm`, and a steel mass of `535 g`. The sheet announces a
titanium option on request with a `33 %` saving per rod, without publishing the
alloy, the process or the absolute mass. PorscheFanatics corroborates titanium
rods as a 993 engine candidate, but brings no dimension.

The F0 keeps only these published dimensions. The outer diameters `78/40 mm`,
the two open flanges `10 × 14 mm`, the visual cap split of `0.4 mm` and two
`8.4 mm` passages are the project's own hypotheses. Bolts, threads, bearing
shells, small-end bushing, oil channel, qualified fillets, clearances and mass
distribution are absent.

## Why study additive

An open LPBF topology can be reshaped from load fields, with material
concentrated in the mechanical paths and no closed powder pocket. It must,
however, be compared to a forged/machined 4340 steel rod and to a conventional
titanium rod. The study by Cecchel et al. on an optimized Ti-6Al-4V connecting
rod made by SLM includes FEA and full-scale fatigue, but reports lower endurance
than the conventional reference: a fine topology and a static margin therefore
do not constitute a fatigue validation.

The OCCT BREP and its STEP re-read are valid with two solids, body and cap. The
F0 envelope is `186.0 × 84.0 × 19.58 mm`, the volume `77,154.68 mm³` and the
theoretical mass `341.02 g` at `4.42 g/cm³`. This mass is `17.43 g`, about
`4.9 %`, under the theoretical target of `358.45 g` obtained by applying the
`33 %` to the `535 g`. It validates neither the PAUTER titanium offer, nor the
balancing, nor the strength of the F0.

## Screenings run

The regression case takes the documented bore of `100 mm`, the stroke of
`76.4 mm` and `6,720 rpm`, then adds synthetic hypotheses: cylinder pressure
`12 MPa`, piston/pin assembly `600 g`, a third of the rod mass in translation,
concentration factor `1.5` and a `100 h` cycle.

With the CAD mass, the equations give `94.25 kN` of gas force, `17.56 kN` of
inertia and a compression bound of `111.81 kN`. The two idealized flanges lead
to `598.98 MPa` of local compressive stress and an EOS room-temperature
limit/stress ratio of `1.64`. The Euler/load ratio is `5.47`. The projected
pressures are `102.80 MPa` at the big end and `248.17 MPa` at the small end, the
`100 h` cycle represents `40.32 million` revolutions and the free expansion over
`+100 K` is `0.114 mm`.

These numbers are reproducible mathematical checks, not an FEA nor a life
prediction. They ignore in particular contact, bolt preload, oil film,
out-of-plane bending, LPBF defects, surface finish, temperature and multiaxial
fatigue.

## Next gates

1. Measure or scan a connecting rod, its cap, bolts, bearing shells, pin and
   crankshaft/piston interfaces; record mass and end-to-end balance.
2. Freeze the M64 variant, cylinder pressure envelope, moving masses,
   overspeed, knock, temperature, spectrum and service duration.
3. Rebuild joint faces, bores, fillets, lubrication, preload, friction,
   clearances and tolerances from the measurements.
4. Compare steel, conventional titanium and LPBF Ti64 by multibody then
   converged nonlinear 3D FEA of contact, buckling, modal and fatigue.
5. Optimize the topology with keep-outs, orientations, machining allowances and
   manufacturing constraints, then qualify powder, heat treatment, HIP, CT,
   roughness, dye penetrant and coupons.
6. Carry out full-scale static and fatigue proof with the chosen bolts and
   bearings, then correlate on rig and dyno under engine engineering review.

PhysicsNeMo stays deferred until a correlated FEA/fatigue set with training,
holdout and out-of-distribution splits is available. SimReady waits for the
measured interfaces of the assembly. This F0 STEP is authorized neither for
manufacture, nor for fitting, nor for engine start-up.

<!-- print-screen:begin -->

## LPBF print simulation

The simulation was run and **failed closed**: the STEP master is not a single body; slicing refuses a surface in several pieces. No result is therefore published for this part, and no image is made up in its place.

<!-- print-screen:end -->
