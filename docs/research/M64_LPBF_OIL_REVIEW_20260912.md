# M64 cylinder head: LPBF process and oil cooling

The literature available as of September 12, 2026 supports a progressive qualification through coupons and cylinder head sectors. It does not demonstrate that a printed, turbocharged, four-valve M64 cylinder head cooled only by air/oil will withstand 700 hp. The repository's reference remains **700 PS at the crankshaft, i.e. 514.85 kW**; 700 mechanical hp would correspond to about 522 kW. Engine speed, fuel, duty cycle and the heat actually transferred to each cylinder head remain to be defined.

## Engine references and scope

Swindon documents an air-cooled four-valve M64 kit that uses the original valvetrain drive and lubrication. This industrial existence establishes the plausibility of the architecture, without providing any public validation of an LPBF cylinder head at 700 PS turbo. Singer announces 710 HP SAE net and four valves for its DLS Turbo Road, but **with water-cooled cylinder heads**, and air-cooled cylinders.[^10][^11] No historical claim about the impossibility of four valves in the 1960s is retained, for lack of a verified primary source.

## Process simulation

AdditiveFOAM is suited to heat transport and local melt-pool flow, with a volumetric source, latent heat and the Marangoni effect. Its 2025 article explicitly places this model between detailed melt-pool resolution and part-scale computation.[^1] Knapp et al. show on the IN625 of the NIST benchmark that a calibrated simplified thermal model can reproduce certain outputs as well as a model with flow.[^2] This result justifies an economical calibration; it does not prove that flow or vaporization are negligible for the M64 alloy and recipe.

The F58 runs must remain distinct:

| Receipt and date | Physics and window | Limiter / absorbed laser |
|---|---|---:|
| [Corrected coupon of September 8, 2026](../reports/M64_F58_CORRECTED_COUPON_20260908.md) | Coupled flow; stopped at 109.55 µs out of 120 µs | 8.406 % |
| [q10 quadrature of September 12, 2026](../reports/M64_QUADRATURE_EXECUTION_20260912.md) | Thermal only; 40 µs completed | 9.8133 % |
| [q20 quadrature of September 12, 2026](../reports/M64_QUADRATURE_EXECUTION_20260912.md) | Thermal only; 40 µs completed | 8.8675 % |

All of them hit the 3,300 K numerical cap. The q10/q20 runs compare only the quadrature over the same window; they neither complete nor replace the coupled coupon of September 8. These percentages, over different physics and durations, do not describe an improvement trend. An excellent accounting closure that includes this artificial sink does not constitute a physical validation. The priority remains: distinct powder/solid properties, measured absorption and laser profile, justified thermal conditions, then metallographic sections of tracks and multilayer coupons. The Kumar et al. (2026) preprint covers precisely evaporation, vapor recoil, laser reflections and powder-thickness variation; its announced agreement with NIST deserves a targeted reproduction, without automatically replacing the existing solver.[^9]

For the full cylinder head, a thermomechanical build model is required: layer activation, supports, clamping, temperature-dependent plasticity, cooling, heat treatment, plate removal and machining. The documentary orientations diverge over time: [the September 8 note](../reports/M64_MULTIPHYSICS_EXECUTION.md) retains MOOSE as a candidate, while [the September 12 plan](../reports/M64_JOBS_234_20260912.md) gives priority to Adamantine after process qualification. The MOOSE/MALAMUTE DED examples do not qualify LPBF; the Adamantine 1.0 version released in 2024 limits its mechanics to serial CPU and requires conforming hexahedral meshes.[^4][^12] The proposal is a **single thermomechanical benchmark**, comparing the existing chain with Adamantine on the same coupon, with the same laws, loads, unclamping sequence and distortion measurements. The choice will depend on this deviation from the measurements, on meshing feasibility and on computational cost; no mandatory integration of both families is proposed.

ExaCA v2 improves the treatment of remelting and the prediction of texture. ExaConstit then computes the homogenized mechanical response of polycrystals.[^3][^13] Adding them is justified only if EBSD measurements and tests in several orientations make it possible to calibrate and check these models. A simulated grain color gives neither a hot fatigue curve nor a cylinder head service life.

## Printed oil circuits

A defensible starting architecture combines retained external fins with oil galleries that are accessible, short and directed toward the thermally critical zones. Parallel branches limit the path length, but require control of the flow split; very long serpentines increase the difficulty of cleaning and the hydraulic sensitivity. This choice remains an engineering proposal to be compared with cooling without additional galleries.

Sizing must couple extracted heat and hydraulic cost:

\[
\dot Q_{oil}=\dot m\,c_p(T)\,(T_{out}-T_{in}),\qquad
\Delta p=\left(f\frac{L}{D_h}+\sum K\right)\frac{\rho U^2}{2},\qquad
P_{pump}=\frac{\Delta p\,\dot V}{\eta}.
\]

These relations do not allow the 514.85 mechanical kW to be equated with the heat to be extracted. The air/oil/exhaust split must be measured or computed, the actual viscosity of cold and hot oil used, and the flow still available for lubrication checked, together with return and de-aeration.

Favero et al. combine hydraulic tests, surface characterization and tomography of LPBF CuCrZr channels according to their orientation.[^5] The transferable consequence is methodological: use the measured printed cross-section and calibrate the equivalent roughness on the pressure drop. The material, the fluid and the experimental correlations must not be transferred directly to engine oil. A single Ra value and a nominal CAD geometry are insufficient to qualify each gallery.

Depowdering must precede any treatment likely to fix the residues. Plan access, rotations, evacuation and witness specimens reproducing the worst branch; check by repeated weighing, filtering of the rinses and inspection/CT according to their sensitivity. Du et al. achieve depowdering by combining vortex and compressed air, but on a **SiC binder-jetted** heat exchanger, not metal LPBF: their protocol defines no guaranteed minimum diameter for this cylinder head.[^6]

Juárez et al. study deposits from an aerated turbine oil at wall temperatures up to 236 °C; temperature and oxygen change their onset.[^8] **236 °C is not an allowable limit for engine oil.** The test loop must use the selected oil, with representative wall temperature, flow rate, residence time, aeration and hot shutdowns. Measure deposit mass, pressure-drop drift, change in heat transfer and released particles, including after restart.

## Proposed criteria for the next batches

These criteria organize the tests; the manufacturing and service limits must be approved before they are run.

| Batch | Expected evidence and acceptance condition |
|---|---|
| Numerical coupon | Full window; no active cap; explicit mass/energy balance; spatial and temporal refinement. Proposed initial targets: energy residual below 1 %, variation of useful outputs below 5 %, separate from experimental correlation. |
| LPBF coupon | Traceable powder lot, machine, parameters, orientation and treatments; measured melt pool; porosity and defects by size/location; model/measurement comparison with declared uncertainties and validation on coupons not used for calibration. |
| Gallery sector | CT of passages and thicknesses, measured cleanliness, cold/hot flow–pressure curves, heat exchange and split between branches; limits set by the pump budget and metal/oil temperature. |
| Mechanical sector | Distortion after cutting/machining, sealing under design pressure, durability of seats/guides and thermal cycles; thresholds drawn from the clearances, clamping loads and loads actually defined. |

Van der Rest et al. show that roughness and near-surface defects govern the fatigue of AlSi10Mg; their tests are at room temperature, in cyclic tension R = 0.1.[^7] The final process must therefore be tested hot, after aging, with representative internal surfaces: tension, fatigue, thermomechanical cycles and creep/relaxation when hold times justify it. Polished specimens or a high mean density do not qualify the bridges between seats and galleries. The final step remains an instrumented engine dyno with post-test inspection.

## Sources and reading level

Sources consulted on **September 12, 2026**, publications retained up to that date. "Full" means the complete document was read; "sections" a targeted consultation of the full text; "abstract" excludes any claim of a complete reading.

[^1]: J. Coleman et al., [AdditiveFOAM: A Continuum Multiphysics Code for Additive Manufacturing](https://www.theoj.org/joss-papers/joss.07770/10.21105.joss.07770.pdf), JOSS, **May 23, 2025**. Peer-reviewed software article; **full, 4 pages**. [ORNL code](https://github.com/ORNL/AdditiveFOAM).
[^2]: G. L. Knapp et al., [Calibrating uncertain parameters in melt pool simulations of additive manufacturing](https://doi.org/10.1016/j.commatsci.2022.111904), Computational Materials Science 218, **February 5, 2023**. Peer-reviewed; **ORNL abstract and publisher excerpts of method/conclusion**, not full.
[^3]: M. Rolchigo et al., [ExaCA v2.0](https://doi.org/10.1016/j.commatsci.2025.113734), Computational Materials Science 251, **March 2025**. Peer-reviewed; **ORNL abstract and beginning of the author manuscript**, not full. [OSTI manuscript](https://www.osti.gov/servlets/purl/2538332).
[^4]: B. Turcksin and S. DeWitt, [Adamantine 1.0: A Thermomechanical Simulator for Additive Manufacturing](https://www.theoj.org/joss-papers/joss.07017/10.21105.joss.07017.pdf), JOSS, **October 17, 2024**. Peer-reviewed software article; **full, 5 pages**. [Code](https://github.com/adamantine-sim/adamantine).
[^5]: G. Favero et al., [Effect of the building orientation on additively manufactured copper alloy: Hydraulic performance of different surface roughness channels](https://doi.org/10.1016/j.ijft.2024.100790), International Journal of Thermofluids 23, **August 5, 2024**. Peer-reviewed; **publisher abstract and indexed excerpts of the institutional manuscript**, direct PDF inaccessible.
[^6]: W. Du, W. Yu, D. M. France and D. Singh, [Depowdering of an additively manufactured heat exchanger with narrow and turning channels](https://doi.org/10.1016/j.addlet.2024.100202), Additive Manufacturing Letters 9, **April 2024**. Peer-reviewed; **abstract and indexed experimental sections**, not full. SiC/binder jetting.
[^7]: C. van der Rest et al., [Influence of roughness and subsurface porosity on the fatigue life of AlSi10Mg produced by Laser Powder Bed Fusion](https://doi.org/10.1016/j.msea.2025.148885), Materials Science and Engineering A 944, **online July 28, 2025**, November 2025 volume. Peer-reviewed; **introduction, 2.4 and conclusions sections of the UCLouvain PDF**.
[^8]: R. Juárez, B. Creighton and E. L. Petersen, [Temperature Dependence of Aerated Turbine Lubricating Oil Degradation From a Lab-Scale Test Rig](https://doi.org/10.1115/1.4066787), ASME Journal of Engineering for Gas Turbines and Power 147(7), **online January 20, 2025**, July 2025 issue. Journal article; **publisher abstract deposited in Crossref**, PDF inaccessible.
[^9]: B. Kumar et al., [Laser Powder Bed Fusion Melt Pool Dynamics for Different Geometric Variations and Powder Layer Heights: High-Fidelity Multiphysics Modeling vs 2025 NIST Experiments](https://arxiv.org/abs/2604.07359v1), **v1 submitted on March 29, 2026 at 02:53:32 UTC**, according to the re-checked arXiv history. The identifier belongs to the 2026-04 series; the public announcement date is not established here. **Preprint**, peer review not established; **abstract only**.
[^10]: Swindon Powertrain, [M64 24V Cylinder Head Kit Product Sheet](https://swindonpowertrain.com/wp-content/uploads/2025/10/M64-24V-Cylinder-Head-Kit-Product-Sheet-0923.pdf), sheet referenced "0923", hosted under 2025/10. Manufacturer source; **descriptive section of the PDF**. Exact revision date not established.
[^11]: Singer Vehicle Design, [DLS Turbo Services — Road](https://singervehicledesign.com/singer-in-the-world/featured-restoration-3/), undated page. Manufacturer source; **Engine section**, transcribed on September 12, 2026.
[^12]: Idaho National Laboratory, [MALAMUTE System Design Description](https://malamute.inl.gov/sqa/malamute_sdd.html) and [overview](https://malamute.inl.gov/), official documentation; **process and architecture sections**. The home page indicates a documentation build of September 11, 2026. No M64 run established.
[^13]: LLNL, [ExaConstit](https://github.com/LLNL/ExaConstit), official code and README, **applications, constitutive and input-data sections**, transcribed on September 12, 2026; software documentation, not a material test.

## 2 October supplement: the owner's perforated-fin paper

Sroka, Sufe and Kejela, [Improving heat transfer in an air-cooled engine by
redesigning the fins](https://www.combustion-engines.eu/pdf-195440-116096?filename=Improvingheattransfer.pdf),
*Combustion Engines* 201(2), 2025, pp. 14–21, DOI 10.19206/CE-195440,
CC BY 4.0. Full eight-page text read; Figure 2 and tabulated results checked.
Private PDF SHA-256: `3ed12edd838cc6ffae5c1057ba7d5107628b4913fbe4157b5f778a167816b337`.

The study concerns a single cylinder, not a turbo four-valve head. Figure 2
shows imposed 350 °C and convection at 35 W/(m² K). Table 4 reports a
temperature span of 69 K without perforations and 71.8 K with circular holes;
mass changes from 0.960 to 0.926 kg. These yield **+4.06% temperature span**
and **−3.54% mass**, not independent proof of +4% heat flow in watts.

Reproduction checks expose unresolved input consistency:

- Table 1's 50 mm bore and 70 mm stroke imply **137.445 cm³**, not the
  stated 250 cm³.
- For 96 through-holes, 2.5 mm thickness and 2,700 kg/m³ density, equal
  40 mm² openings remove about **25.9 g** in either shape, unlike the
  differing reported mass reductions. Placement/intersections need recovery.
- No mesh-convergence study or experimental correlation is established here.

This is a useful hypothesis source, not an M64 validation or an LPBF alloy
qualification. Its dimensions, convection coefficient and material properties
are not imported into the head's physical boundary conditions.

### Project-derived experiment, not a result of the paper

Preserve the scanned outer envelope, mating regions and load paths. Do not
drill the current CAD until fin and protected-region labels are established.
Compare these candidates with identical loads, material state, oil routing and
ambient conditions:

| Candidate | Controlled change | Mandatory comparison |
|---|---|---|
| A | Original unperforated fins | Reference mass, temperatures and fan demand |
| B | Rounded through-holes restricted to labelled fins | Same removed volume and protected fin roots |
| C | Rounded slots, without exterior-envelope change | Same porosity and minimum ligament as B |

Hole size follows local fin width, thickness and ligament constraints; no
7.14 mm default is transferred from the paper. Screen several hole positions
before increasing porosity. Reject any connection to a port, oil gallery,
seat, guide, plug boss or structural interface.

Use existing OpenFOAM CHT for the coupled solid/air calculation. Compare first
at equal air mass flow, then at the same fan curve or shaft-power budget:
perforations can change pressure losses and bypass useful fin passages.
Record integrated heat rejection, mass/energy residuals, pressure loss, peak
seat-bridge temperature, gradients and mass. At fixed heat input, prefer
thermal resistance `(T_hotspot - T_air_in)/Q_in`, not a larger arbitrary
maximum-minus-minimum temperature span. Cross-check a simple fin coupon with
an analytical conduction/convection model before running the complete head.

Run three systematically refined grids and explicit numerical-uncertainty
estimates; require any improvement to exceed those uncertainties. Then test
hot thermomechanical fatigue and fin-root vibration, followed by the existing
LPBF support/removal, minimum-wall and distortion checks. No gain is accepted
if it sacrifices a required structural or manufacturing margin. PhysicsNeMo
may rank designs only after independent solver results supply training and
held-out validation; it does not certify a geometry from this paper.

**Status:** comparison defined, no perforated-head CAD or CFD result produced.
The current curve/volume reconciliation remains the immediate numerical gate.
