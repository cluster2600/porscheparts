# Manufacturing qualification review — horizontal fan R0 / V5

**Review package, 2026-10-04. Manufacturing acceptance and service qualification are both open.**
This package prepares an engineering/manufacturer review. No workshop has accepted the part, no build has been ordered, and no physical specimen has been inspected. Numerical study results cannot close the physical acceptance gates below.

## Configuration supplied for review

The source geometry is an original analytical reconstruction informed by an unscaled private scan. The nominal 275 mm diameter, nine blades, interfaces, clearances and material are study assumptions. The scanned object's identity as a 935 part, its units, and equivalence to a 993 fan are unresolved. These configurations represent a horizontal cooling arrangement; they are not a released substitute for a measured 993 assembly.

| Configuration | Editable rotor | STEP SHA-256 | Difference from R0 |
| --- | --- | --- | --- |
| R0 | [R0-rotor.step](R0-rotor.step) | `d765efe71feab39bb03558d03ace47d98cd98cf3b14a6e5fc47b87a3647bc9fd` | Reference analytical geometry |
| V5 | [V5-rotor.step](V5-rotor.step) | `3697df79b2a8470643bae331bedbf80ac982dfd323473d5a1dc530481c351700` | Carrier web thickness multiplied by 1.3; volume +12.76% |

[Parameters](parameters/), [geometry receipts](results/geometry/), [engineering calculations](ENGINEERING.md) and [artifact manifest](manifest.json) identify the versions. Raw scans remain private and are excluded from this review package. Supplier transfer of CAD requires a separately authorized destination and scope.

## Material and manufacturing scenario

**Candidate route for review:** laser powder bed fusion of AlSi10Mg, followed by approved thermal treatment, support removal, machining and inspection. Review target identified by the project coordinator: **BLT (Xi’an Bright Laser Technologies), Xi’an**. No contact, CAD transmission, workshop acceptance, machine allocation or manufacturing authorization has occurred. Alloy, final condition and actual machine remain decisions for engineering/workshop review. EOS M 290 remains a published envelope/material reference for the existing screening, not the selected production route.

The EOS public sheet describes a 250 × 250 × 325 mm envelope, with usable space dependent on the platform and application. This is an envelope reference, not an acceptance of the nested rotor. The flat 275 mm rotor exceeds the 250 mm plane. A diagonal edge orientation (`Rx 90°`, then `Rz 45°`, column-vector convention) merits review; the existing R0 tessellation fits the envelope with a hypothetical 10 mm allowance on each side. Actual supports, platform, recoater clearance, machining stock and workshop exclusions must be included in the final nesting. [EOS M 290 system sheet](https://www.eos.info/metal-solutions/metal-printers/data-sheets/sds-eos-m-290).

The material/process reference describes a 30 µm AlSi10Mg route and distinguishes as-manufactured, stress-relieved and T6 conditions. Heat treatment changes properties and can affect porosity. Its coupon results are not rotor allowables. The final alloy specification, condition and approved treatment sequence must be selected together with the engineer and workshop. [EOS AlSi10Mg process sheet](https://www.eos.info/metal-solutions/data-sheets/aluminium/pds-eos-aluminium-alsi10mg-eos-m-290-30um).

The numerical support-release scenario deliberately retains generic isotropic elasticity (`E = 70 GPa`, `ν = 0.33`) from the previous mechanical study. It is **not** a qualified AlSi10Mg material card, thermal history, temperature-dependent plasticity model or calibrated machine-specific inherent strain. An explicitly assumed contraction field tests geometry sensitivity only.

BLT reports an AlSi10Mg stator-frame example made on an S400 with six lasers and 30 µm layers. That commercial example establishes a capability lead, not a qualified recipe for this fan. [BLT case, 2026-04-17](https://www.xa-blt.com/en/news/blt-showcased-evtol-aircraft-motor-stator-frame-at-tct-asia-2026/). The current S400 page lists 450 × 300 × 400 mm excluding substrate thickness, and two through eight 500 W lasers; the coordinator also found a 2025 brochure reporting 400 × 300 × 400 mm. Confirm the exact serial/configuration and usable envelope rather than combining versions. [BLT S400](https://www.xa-blt.com/en/product/blt-s400/). The 275 mm rotor nominally fits either width/depth with the assumed 10 mm margin, but this is not approved nesting.

The coordinator’s primary-source audit identifies heat treatment/HIP, cutting, finishing/machining and high-energy CT capabilities. This execution environment could not retrieve the Chinese page; these are coordinator-supplied capability claims to verify during review, not independently demonstrated rotor inspection performance. [BLT technical capabilities, 2022](https://www.xa-blt.com/news/铂力特2022年技术成果答卷提交中/). Request CT scanner, complete-part coverage, achievable resolution and flaw detectability at blade roots/web/hub. A quality-system certificate or a powder-scope certification does not qualify this rotor.

## Comparative numerical manufacturing study

R0 and V5 reuse their independently checked C3D10 rotor meshes at 4.5 mm and 3.6 mm target sizes. Both use the same elastic card, prescribed field, orientation and support selection rule. A rigid-column bound fixes the lowest surface node in each projected support raster cell. This is a mechanical attachment proxy; it contains no printable support solids, support stiffness calibration or heat conduction.

Two static states are solved: attached to the proxy supports, then all supports released with six independent gauge constraints to remove rigid motion. The pre-existing analytic single-tetrahedron benchmark is rerun on the actual native solver. Its exact released solution is uniform contraction with zero stress.

| Sensitivity | Same input for R0 and V5 | Purpose |
| --- | --- | --- |
| Reference | Diagonal edge build, 5 mm support raster, assumed amplitude 0.001 | Conditional shape response |
| Half amplitude | 0.0005, otherwise identical | Verify expected linear scaling; not a calibrated strain estimate |
| Zero amplitude | 0, otherwise identical | Detect artificial deformation/stress or parser errors |
| Orientation | Flat rotor, build normal +Z, same amplitude/raster (legacy case ID `upright`) | Compare mechanical sensitivity; flat non-fit control for the EOS reference envelope; potentially fits the BLT reference envelopes |
| Supports | Diagonal edge, 10 mm raster | Sensitivity to idealized attachment density |
| Mesh | Diagonal edge, target 3.6 mm | Check global displacement sensitivity; point-restraint stress singularities remain |

The field is `ε* = −a(0.5 + 0.5s²)(I − 0.7nnᵀ)`, with normalized height `s` and build normal `n`. This formula is an analyst-defined scenario, not a measured process property. No melting, deposition activation, scan path, thermal gradient, recoater collision, distortion compensation, pore formation or microstructure is simulated. Stress peaks at fixed support points are not acceptable physical build-stress predictions. No strain magnitude or displacement threshold in this study is a manufacturing acceptance limit.

The comparative results, source decks/field hashes, attached/released displacement, release increment, rigid-motion-removed deformation, zero/scaling controls and plots are linked in [ENGINEERING.md](ENGINEERING.md) and the [12-case comparison](results/lpbf/manufacturing-comparison.json). The absence of process calibration is an explicit limitation of every result. Released displacement maxima in the diagonal-edge reference are 0.096015 mm (R0) and 0.096054 mm (V5); the support-release increment is 0.196200 / 0.180054 mm. These are scenario outputs, not predicted physical build distortion. The zero-strain and amplitude-scaling controls pass. Since the prescribed strain does not depend on support-induced thermal/plastic history, changing support density changes the release increment but not the final elastic equilibrium. The fine-grid proxy selects 521 attachment nodes versus 518, so this is combined mesh/support sampling sensitivity, not complete process-model convergence.

## Inputs and decisions required from the workshop

1. **Production configuration:** approved rotor revision and change control, true interface drawing, dimensional scale, load-bearing features, machining datums, permitted support contact zones, stock allowances, and inspection drawing. The hypothesized bore is not a measured fit. Establish datum A/B/C and tolerance values from the mating shaft/drive/shroud before functional manufacture.
2. **Feedstock:** alloy and final condition, powder supplier/batch certificate, chemical composition, particle-size distribution, storage, drying/handling and reuse history, sieving/mixing records, contamination controls and build powder traceability.
3. **Qualified equipment/recipe:** machine model/serial and qualification status, software/build file revision, layer thickness, laser calibration, hatch/contour/downskin parameters, scan sequence, atmosphere/oxygen controls, platform material/preheat/flatness, gas flow, recoater type and calibrated clearance. Values must come from the route owner; no synthetic recipe is supplied here.
4. **Supports and process model:** exact support CAD, contact teeth and removal access, plate stiffness/thermal properties, support conduction/compliance, cut sequence, stress relief before cutting if selected, and calibrated distortion model. Calibration specimens and an independent holdout build should match material, recipe, orientation, supports and post-processing.
5. **Post-processing:** documented depowdering, support removal, approved stress relief or T6 sequence and furnace records, distortion checks before/after release and treatment, machining sequence and workholding, deburring/polishing without reducing critical thickness, final cleaning and traceability. HIP is **not automatically prescribed**: the engineer/workshop must justify it against defect type, fatigue requirement, surface-connected flaws, dimensional change and the selected alloy/thermal route; validate its effects with representative evidence.
6. **Representative coupons:** select geometry/location/orientation with the engineer to represent blade roots, webs, supported/downskin surfaces and thermal mass. Obtain composition, density/porosity/metallography and tensile data in relevant directions and condition. Fatigue specimens must reflect service stress ratio, temperature, surface/notch condition and defects; polished generic coupons do not qualify rough blade roots.

The proposed production dossier follows the need for controlled AM operations described by [ISO/ASTM 52920:2023](https://www.iso.org/standard/76911.html). System capability artifacts may inform calibration using [ISO/ASTM 52902:2023](https://www.iso.org/standard/79683.html). The official [ASTM F3318-18 abstract](https://store.astm.org/f3318-18.html) concerns finished AlSi10Mg PBF parts. These public abstracts establish scope only; this package does not claim conformance to unread paid clauses. Applicable editions, actual requirements and contractual acceptance values must be reviewed by competent parties.

## Inspection and acceptance evidence

| Stage / characteristic | Proposed evidence | Acceptance values / owner | Current state |
| --- | --- | --- | --- |
| Geometry and interfaces | Controlled drawing, CAD revision/hash, independently measured reference and mating parts | Engineer approves scale, datums, GD&T, fits and stock | Missing physical definition |
| Powder / build | Batch certificates, powder history, machine/recipe qualification, signed build record and deviations | Workshop QA and engineer agree applicable material specification | Missing workshop data |
| Attached / released shape | Optical/CMM measurements in documented datums before/after cutting; compare calibrated predictions | Engineer approves machining stock and distortion limits | Numerical scenario only |
| Final dimensions | Calibrated CMM/optical measurement of bore, mating faces, runout, concentricity, tip envelope, blade pitch/profile and root thickness | Drawing limits and measurement uncertainty to be approved | No manufactured specimen |
| Internal defects | CT or qualified alternative, coverage of roots/web/hub, voxel/detection capability, artifacts and dimensional uncertainty documented; representative reference defects/coupons | Engineer defines defect types, sizes, spatial limits and method capability | No NDT data |
| Surface integrity | Qualified visual/penetrant examination as appropriate; roughness/topography at blade roots and downskin; document removed support scars | Engineer/NDT specialist sets method and defect/finish limits | No NDT/finish data |
| Material / thermal state | Furnace records, coupon properties, metallography and agreed condition verification | Route-qualified property requirements, sampling and lot acceptance | Generic elastic card only |
| Repeatability | Agreed sample size and builds, deviation handling, independent coupon/model validation | Workshop QA + engineer approve qualification plan | Not assessed physically |
| Manufacturing acceptance | Complete inspection dossier, deviations dispositioned, signatures and traceable serial/build ID | Design authority and manufacturer | **Open** |

CT capability is not established by owning a CT scanner: flaw detectability and coverage must suit this actual rotor. The scope of [ASTM E3166-20e1](https://www.astm.org/e3166-20e01.html) addresses NDE of metal AM parts after build; its aerospace context is a methodological reference here, not an assertion that this automotive rotor meets aerospace requirements. Numerical watertightness and positive Jacobians do not establish absence of physical pores, lack of fusion or cracks.

## Separate service qualification of a rotating engine part

Manufacturing acceptance means a controlled part satisfies its agreed drawing, material and inspection requirements. Service qualification additionally requires a documented professional engineering review and approved validation plan for this highly loaded engine rotor.

The plan must establish actual attachment/preload, drive ratio and speed envelope, thermal conditions, installed airflow/pressure requirements, fatigue duty and defects, bearing/contact behavior, modal/excitation separation, balance correction zones and permitted mass removal. Review rotating prestress/gyroscopic response and converged blade-root stresses with route-specific allowables. Current fixed-bore elastic results and isolated steady airflow do not establish safe RPM or fatigue life.

Select rigid/flexible rotor behavior before defining balance acceptance. The scope of [ISO 21940-11:2016](https://www.iso.org/standard/54074.html) covers rigid rotor balancing, correction planes and residual unbalance; its [2022 amendment](https://www.iso.org/standard/78116.html) must also be considered. No balance grade, correction-plane tolerance or residual-unbalance value is invented here.

An instrumented rotation/overspeed test, if approved later, belongs to a competent workshop under an agreed containment, mounting, instrumentation, stop-criteria and post-test inspection protocol. The responsible engineer must set speed, duration, cycles, acceptance criteria and safety arrangements. No physical spin, vehicle installation or manufacturing order is authorized by this document.

## What can be closed now and what cannot

- **Numerical evidence available now:** valid analytical BRep/STEP, checked C3D10 meshes, conditional rotation/modal response, isolated CFD at its declared pressure point, geometry orientation/envelope screening, assumed elastic support-release response and its zero/scaling/mesh controls, hash-linked reports and actual-field USD/plots.
- **Workshop data required:** selected machine/material/condition, qualified recipe, exact supports/plate/release and treatment route, calibrated material/process model, capability/inspection methods, production and machining drawings with approved limits.
- **Physical evidence required:** measured original/interfaces, calibration and holdout specimens, recorded build, dimensional/surface/internal inspection, route-specific material/fatigue evidence, balance and approved rotor tests, signed manufacturing and service acceptance.

The immediate review decision is which geometry/material/route to investigate and which data/acceptance criteria to freeze. A successful numerical scenario cannot change the current acceptance state to “fabrication validated.”
