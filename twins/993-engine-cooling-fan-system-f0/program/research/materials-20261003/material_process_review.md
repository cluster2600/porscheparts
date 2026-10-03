# Material and LPBF evidence for the 993 Turbo cooling-impeller study

Research snapshot: 3 October 2026 UTC. This is an engineering evidence pack for candidate modeling, not a manufacturing selection, part qualification, or permission to install or spin a rotor. Nothing was fabricated or tested in this research pass.

## Decision summary

1. Keep AlSi10Mg as the inherited exploratory scenario, with ZRapid iSLM420DN explicitly marked unconfirmed as the production route. A public machine envelope plus a research recipe does not establish properties of the final impeller.
2. Compare three real AM aluminum alternatives without mixing their property cards: EOS AlF357 for a similar-density ductile alternative; Scalmalloy for higher ambient-temperature strength; Al 2139 AM where measured metal temperature makes hot strength important. Ti 6Al 4V is only a high-strength, higher-density comparator, not a preferred replacement.
3. Separate as-built, stress-relieved, T6-like, HIP and hot-rolled material. They are different constitutive states. A rotor whose supports are removed after stress relief cannot retain an as-built tensile card by default.
4. The important unresolved inputs are temperature- and state-dependent elasticity/plasticity, route-specific fatigue and defect evidence, and print-model calibration. The machine-readable files preserve missing values as null. No complete qualified FEA/LPBF material card has been established.
5. The original rotor alloy remains unverified for the exact target part. A Porsche statement about a magnesium housing does not identify its impeller alloy. The cast-aluminum EPS rotor is a separate aftermarket benchmark, with an unspecified alloy grade/temper.

## 1. How to use the evidence

`material_evidence.json` and `.csv` contain 143 property records, with source, page/section, units, condition, orientation, uncertainty and admissibility. `source_manifest.csv` identifies the original sources. `process_simulation_inputs.json`, `process_parameters.csv` and `simulation_requirements.csv` distinguish inherited settings, vendor capabilities, assumptions, and missing calibration data.

All records have `admissible_for_release=false`. This does not mean that the measured coupon properties are false. It means they do not by themselves validate this rotor, geometry, service spectrum, final surface or manufacturing route. Published means are not statistical design allowables. A density lower bound is not a conservative maximum for centrifugal loading; a mean porosity percentage is not the maximum critical flaw.

The property matrix is a reference corpus. Do not automatically merge every non-null value into one solver card. A solver scenario must identify one alloy, feedstock, machine/parameter revision, build orientation, thermal history and surface state. Other routes are separately labeled sensitivities.

## 2. Comparative material assessment

### AlSi10Mg: inherited baseline, usable public process evidence

The current EOS M290/30 µm sheet reports these **turned coupon** values, ordered Z / XY:

| State | 0.2% yield, MPa | UTS, MPa | Elongation, % |
|---|---:|---:|---:|
| As manufactured | 233 / 270 | 466 / 461 | 6.3 / 10.2 |
| EOS T6 | 250 / 260 | 310 / 320 | 11 / 11 |
| SR 270 °C, 90 min | 200, orientation unspecified | 310, orientation unspecified | 9 |

Reported density is ≥2670 kg/m³; average defect percentage is 0.04%. Conductivity, Z / XY, is 100 / 110 W/(m K) as manufactured, 165 / 155 after EOS T6, and 160 / 165 after SR. The sheet does not explicitly state the conductivity test temperature. CTE is reported over 25–100, 25–200 and 25–300 °C intervals: 20, 22 and 27  × 10⁻⁶/K. Current E, ν, cp, full plastic curves and service-temperature allowables are absent. [EOS current process sheet](https://www.eos.info/metal-solutions/data-sheets/aluminium/pds-eos-aluminium-alsi10mg-eos-m-290-30um)

The 2022 PDF supplies useful provenance: M290, FlexM291 2.01, 30 µm, 35 °C platform; EOS T6 means 530 °C/30 min, water quench, then 165 °C/6 h and air cooling. It warns of porosity growth during heat treatment and of aging/overaging when thermal exposure increases. Its as-built values differ slightly from the current sheet, so do not silently combine versions. [EOS January 2022, pp.5–8](https://www.eos.info/03_system-related-assets/material-related-contents/metal-materials-and-examples/metal-material-datasheet/aluminium/material_datasheet_eos_aluminium-alsi10mg_en_web.pdf#page=5)

Historical E and cp values are preserved only as archival evidence. The 2014 sheet's E values span 60–75 GPa across orientation/state, with ±10 GPa as stated; cp is 890–920 J/(kg K), ±50. Its thermal footnote points to EOSINT M270, while the front-page scope discusses M280/M290 Speed 1.0. These are not modern ZRapid temperature-dependent data. [EOS-authored 2014 sheet, pp.1,4–5, hosted mirror](https://printform.com/wp-content/uploads/2018/09/EOS_Aluminium_AlSi10Mg_en.pdf)

**Implication:** reasonable development baseline, but neither the EOS ambient card nor archival constants establish the iSLM420DN final-state properties. A broad published spread is a sensitivity family, not a guaranteed bound on the target part.

### AlF357: similar density, more ductile AM Al-Si option

EOS M290/30 µm AlF357 has density 2670 kg/m³ (one reported density sample). Z / XY yield is 250 / 255 MPa as built and 265 / 270 MPa after its T6-like cycle; corresponding UTS is 400 / 365 and 330 / 340 MPa. Post-treatment elongation is 11.5% in both orientations. Conductivity is 140 W/(m K) as built and 150 after treatment, with test temperature unstated. The process reports 0.03% average defects over 20 samples. Its heat cycle is 540 °C/30 min, water quench, then 165 °C/6 h. [EOS AlF357 process sheet](https://www.eos.info/metal-solutions/data-sheets/aluminium/pds-eos-aluminium-alf357-eos-m-290-30um)

**Implication:** a useful comparative AM material, not a cast-A357 substitution rule. The public sheet does not supply E(T), ν, cp(T), CTE, fatigue curves or a rotor-relevant hot-strength database. This evidence cannot justify a ZRapid recipe or hot FEA card without additional qualification.

### Scalmalloy: strong ambient candidate with important temperature caveats

The 3D Systems DMP Flex/Factory 350 Config B sheet describes SR at 325 °C/4 h followed by air cooling. At 30 µm, yield is 490 ±10 MPa XY and ±15 MPa Z; UTS is 520 ±10/±15 MPa. The uncertainty notation is vendor mean and 95% tolerance interval at 95% confidence. The theoretical density is 2670 kg/m³, adopted from APWORKS; this is not a full-rotor density measurement. At 20 °C, conductivity 95–100 W/(m K) is **calculated from electrical resistivity**, not directly thermally measured. CTE over 20–100 °C is 23.5 × 10⁻⁶/K. [3D Systems sheet, pp.1–2 and footnotes](https://de.3dsystems.com/sites/default/files/2022-02/3d-systems-certified-scalmalloy(a)-datasheet-usen-2022-02-23-a-print.pdf)

A separate primary experiment used vertical Concept Laser M2 GEN2 specimens with HIP at 325 °C/100 MPa/4 h and furnace cooling. Its yield values at 21 / 100 / 200 °C were 466 / 384 / 156 MPa; corresponding E values reported in the analysis were 80 / 75 / 61 GPa. The paper's ν=0.34 is explicitly an assumption, not a measurement. Its fatigue tests are fully reversed strain-controlled machined coupons; temperature effects depend on strain amplitude and initiating defects. These data are evidence against temperature-independent selection, not a replacement for the DMP350 material card. [Khan et al., sections 2,4.2 and Fig.8](https://onlinelibrary.wiley.com/doi/10.1111/ffe.14549)

**Implication:** shortlist only after establishing rotor-metal temperatures, final heat treatment and a supplier-supported process. The APWORKS product page's 480 MPa yield/520 MPa tensile headline is broader than a complete route-qualified dataset. [APWORKS](https://www.apworks.de/scalmalloy)

### Al 2139 AM: compare when hot strength matters

EOS's modified AM alloy is distinct from wrought 2139. Its M290/60 µm T4 coupons report Z / XY yield 460 / 460 MPa, UTS 520 / 540 MPa and elongation 4 / 6%; density ≥2840 kg/m³. The M290 recipe has a 175 °C platform; the M400-4/50 µm variant uses 195 °C and different properties. T4 is 490 °C/45 min, water quench and three days natural aging. The vendor's elevated-temperature yield graph was visually reviewed; an exact numeric curve, confidence bound and exposure history were not supplied. No E, ν, cp, k, CTE or fatigue curves are extracted from this sheet. [EOS Al 2139 AM, pp.5–7 and 9–11](https://www.eos.info/03_system-related-assets/material-related-contents/metal-materials-and-examples/metal-material-datasheet/aluminium/material_datasheet_eos_aluminium_al2139-am_02-23_en.pdf#page=5)

**Implication:** justified hot-service comparator, not a recommendation to substitute an unspecified high-strength aluminum. Request numerical hot constitutive data and fatigue evidence, including thermal exposure duration and quench distortion.

### Ti 6Al 4V: limited comparator

EOS M290/30 µm material after 800 °C/2 h in argon has density ≥4400 kg/m³, yield 965 /945 MPa and UTS1075 /1055 MPa in Z /XY at room temperature. E, ν, thermal data and fatigue are absent from the selected sheet. [EOS Ti 64](https://www.eos.info/metal-solutions/data-sheets/titanium/pds-eos-titanium-ti64-eos-m-290-30um)

**Implication:** higher tensile strength must be weighed against substantially higher density. At fixed geometry/rpm, mass, polar inertia and centrifugal loading rise with density. Do not infer overall benefit from UTS alone. Hub fit, thermal growth, modes and the full rotor must be redesigned/rechecked. No wrought, ELI or electron-beam Ti 64 data are imported.

## 3. Constitutive and fatigue admissibility

### Temperature and thermal history

As a concrete different-route example, Lehmhus et al. used M290 parts built at 200 °C and stress-relieved at 350 °C/2 h. Vertical, as-built-surface coupons at room temperature /125 /250 °C gave yield 165.94 /154.98 /132.95 MPa, UTS280.20 /249.68 /162.82 MPa, and E71.86 /70.41 /55.74 GPa. Their sample counts and SDs are retained in the matrix. These data demonstrate condition dependence and must not be used as universal knockdowns on the EOS35 °C recipe. [Primary study, section 2 and Table A2](https://pmc.ncbi.nlm.nih.gov/articles/PMC9612077/)

Required practices:

- Identify whether E is tensile, dynamic or a homogenized tensor. Elastic isotropy does not establish plastic isotropy. A primary AlSi10Mg RUS study observed nearly isotropic elasticity alongside process-dependent plastic behavior; its detailed tensor/route should be checked before adoption. [Scientific Reports 2021](https://www.nature.com/articles/s41598-021-85047-2)
- Do not construct a hardening law from YS, UTS and elongation alone. Obtain stress–strain curves, valid true-stress conversion range, post-necking calibration if needed, orientation and test rate. Retain uncertainty.
- Distinguish test temperature from prior aging exposure. A hot tensile result after a short soak does not prove long-duration stability or creep resistance.
- Confirm whether CTE is interval/secant or instantaneous/tangent, and its stress-free/reference temperature. For a documented mean coefficient, use the appropriate reference-to-temperature expansion; do not insert interval averages as pointwise tangent data.
- Keep cast or wrought benchmarks separate. Their identical nominal chemistry does not imply LPBF microstructure, defect morphology or allowables.

### Fatigue

EOS's 110 MPa number is a finite-life point at 20 million cycles, fully reversed R=−1, on turned specimens without heat treatment. It is not an endurance limit, an as-printed blade allowable, or a validated positive-mean-stress rotor life. No Miner, Goodman, Gerber, notch or surface correction is silently chosen.

A2026 primary AlSi10Mg study's indexed abstract reports a route where machining/polishing changed 10⁷-cycle strength from 43 to 66 MPa and emphasizes critical defects and surface notches. These numbers are not imported as rotor allowables because the full testing conditions were not recovered here. [Study DOI10.1016/j.rineng.2026.112570](https://www.sciencedirect.com/science/article/pii/S2590123026035863)

A2023 Scalmalloy paper's 400 MPa number is an **intrinsic prediction from a Kitagawa diagram**, not a general printed-component fatigue limit. Do not use it as a blade S–N point. [Study DOI10.1016/j.ijfatigue.2023.107592](https://www.sciencedirect.com/science/article/pii/S0142112323000932)

For the impeller, obtain S–N or strain-life data at relevant R ratios, temperatures, surface/downskin condition, root notch and build direction. Preserve runouts, scatter, cycles versus reversals, residual stress, and initiation-defect size/location. Require a defect-detection and acceptance plan consistent with the fatigue model. Mean porosity and tensile pass/fail alone cannot close this gap.

## 4. Inherited ZRapid scenario: what is and is not established

The local lead reports this existing scenario: iSLM420DN, AlSi10Mg,500 W,1300 mm/s,0.10 mm hatch,0.04 mm layers,0.08 mm spot and 303.15 K platform. One active laser, absorptivity 0.35 with 0.25/0.45 sensitivities, and 8 s recoating are project assumptions. The detailed source recipe was not independently recovered in this research pass.

The cited paper is about **hot rolling after SLM**, including 40% thickness reduction. Its rolled material properties do not apply to an unrolled impeller; its as-built control and exact experimental recipe must be identified separately. [Article](https://www.sciencedirect.com/science/article/pii/S2352492826011013)

The official iSLM420DN page lists two 500 W lasers,420×420 mm nominal XY and 500 mm Z including substrate; beam diameter capability is 0.06–0.20 mm at 1/e². This establishes an envelope, not the actual laser assignment, build recipe or material qualification. Supports, exclusion regions, plate thickness and orientation still consume usable space. [ZRapid specifications](https://www.zrapid.com/en/slm420dn.html)

The public material link failed to fetch. Secondary sellers' unspecified mechanical-property tables were not promoted into a validated ZRapid card. 

## 5. Print simulation: calibrated result versus illustrative calculation

### Label the simulation level

1. **Geometric buildability check:** watertight/manifold CAD, unsupported surfaces, access, powder removal, build envelope and machining allowance. It cannot predict residual stress, lack of fusion or fatigue life.
2. **Uncalibrated process sensitivity:** explicit assumptions can compare trends, but distortion/stress magnitudes remain provisional. Absorptivity variation is not a statistical uncertainty interval.
3. **Calibrated inherent-strain model:** useful for macroscopic distortion if its effective strain is fitted and validated for the same machine, recipe, material and simulation formulation. It does not independently resolve melt-pool defects.
4. **Calibrated thermal–mechanical model:** requires phase-/temperature-dependent thermal and mechanical data, actual build schedule, boundary conditions and validation. More mesh detail does not replace missing data.

Ansys distinguishes isotropic SSF, anisotropic directional factors, scan-pattern factors and thermal–structural TSSF. Its guide requires recalibration when machine, material/supplier, process or model/mesh assumptions change. Calibration coupons should use the intended production parameters, followed by appropriate distortion measurements. [Ansys Calibration Guide 2025 R2, printed pp.1–3,8–12](https://ansyshelp.ansys.com/public/Views/Secured/corp/v252/en/pdf/LPBF_Calibration_Guide.pdf), [current calibration modes](https://ansyshelp.ansys.com/public/Views/Secured/corp/v261/en/add_lpbf_cal/add_lpbf_cal_intro.html)

### Required input package

The structured requirements file itemizes 14 groups. The most consequential are:

- Traceable powder lot, chemistry/interstitials, PSD and reuse history
- E(T), ν(T), density/reference state, orientation-dependent plastic response and annealing/reset behavior
- Powder/solid/liquid thermal properties or enthalpy, latent heat, solidus/liquidus, thermal expansion reference and contact conductance
- Actual contours, up/downskin, remelts, hatch order/rotation, laser assignment/overlap, dwells, recoating and jump time
- Measured power-at-bed, spot convention/profile and calibrated effective absorption
- Plate material/thickness/clamping, support geometry/stiffness/conduction and spatial preheat
- Gas/O₂/flow, convection, emissivity and powder packing/conductivity
- Cutoff order, support removal, heat treatment, quench, HIP, machining and surface treatment

Temperature-dependent thermal properties and scan information are required by the solver's thermal-strain formulation; a part-only input otherwise implies an assumed scan pattern. [Ansys Users Guide, section 6.2–6.3, printed p.108](https://ansyshelp.ansys.com/public/Views/Secured/corp/v251/en/pdf/Additive_Print_and_Science_Users_Guide.pdf)

Powder and dense-solid measurements are different experimental problems. A dense-solid room-temperature conductivity is not a powder-bed model. [NIST thermal-property methods](https://www.nist.gov/publications/thermal-property-measurement-methods-and-analysis-am-solids-and-powders)

### Calibration and validation sequence

Engineering recommendation, not a claim that tests have run:

1. Freeze the proposed manufacturing route and record its revision. Keep production selection pending until the supplier accepts it.
2. Build calibration specimens representative of scan axes, plate positions and support strategy. Measure their geometry before and after release without conflating heat-treatment changes.
3. Fit only the parameters supported by those measurements. Document instrument uncertainty, repeatability, objective function and residual errors.
4. Predict a withheld geometry and a thin curved blade/root-representative feature. Validate after relevant cutoff and thermal-processing stages. This is independent validation; refitting the same cantilever is insufficient.
5. Perform mesh/time-step/layer-lumping and support-model sensitivity. Check temperatures, distortion and residual stress against the observation each model claims to predict.
6. Only then consider geometric compensation. Confirm that compensation preserves blade section, hub datums, minimum stock and balance-correction space after final processing.

## 6. Rotor release gates that coupon comparisons cannot satisfy

A printable STL or STEP is an intermediate deliverable. Before any operating rotor claim:

- Verify the exact hub/shaft/pulley topology, material and torque-transfer path; apply fit, preload, belt and bearing loads appropriately
- Use actual fan speed, maximum continuous duty, start/stop cycles and a justified overspeed case; engine rpm is not automatically fan rpm
- Combine centrifugal stress and deformation with mean and unsteady aerodynamic loading; evaluate blade/root stresses and interface loads
- Evaluate thermal gradients, differential hub/housing growth, manufacturing/runout tolerances, bending and vibration together in hot clearance
- Check prestressed modes and excitation crossings over operating speed, including blade-pass and engine/drive orders
- Assess fatigue and defect tolerance for final surface condition; include stress concentrations, residual stress, corrosion/galvanic effects and credible foreign-object damage
- Inspect final parts, machine critical datums, verify balance of the defined assembled rotor and document correction limits
- Have qualified engineers define a guarded/contained spin and overspeed proof program, acceptance criteria and service inspection plan

No universal safety factor, balance grade, overspeed percentage or proof speed is chosen here. Those require the actual assembly, service requirements, applicable standards and competent engineering responsibility.

## 7. Benchmark provenance and immediate next decisions

The Porsche 964 training page specifies a magnesium **housing** for the Carrera arrangement. It cannot identify a 993 Turbo rotor grade. [Porsche training, PDFp.26](https://data.club911.net/divers/964tech/964doc.pdf#page=26)

EPS 93010601200EPS is a 245 mm 11-blade cast-aluminum rotor with a drop-forged steel hub. Its supplier page does not identify alloy/temper or provide rotor-level fatigue/overspeed evidence. It is not a direct AM material card or a confirmed 993 Turbo drop-in. [EPS product](https://www.epsauto.com/products/alternator-updated-aluminum-fan)

The next actionable decisions are to confirm the intended machine/supplier and post-processing route, establish the rotor metal-temperature/speed envelope, and obtain route-matched constitutive/fatigue/calibration data. Geometry and explicitly provisional sensitivity calculations can progress while these gaps remain visible. A validated print simulation and operating-rotor release cannot be claimed yet.
