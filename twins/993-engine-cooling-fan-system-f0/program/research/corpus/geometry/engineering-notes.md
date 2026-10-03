# Porsche cooling-fan geometry and validation research

Research date: 2026-10-03. Scope: 911/935 engine cooling rotors, with particular attention to the 993 Turbo. This is an evidence and measurement plan, not a released fan design or an assertion of interchangeability.

## Findings that change the engineering plan

1. **There is no validated 935-to-993 geometric equivalence in the sources inspected.** A model labelled “935 fan” does not establish its year, factory/customer-racing variant, casting, actual diameter, drive, hub, or suitability for the 993 Turbo. Porsche confirms that the 935/78 had water-cooled heads and air-cooled cylinders, a materially different cooling duty from earlier fully air-cooled cars. [Porsche, 935/78 technical history](https://newsroom.porsche.com/en/2026/history/porsche-heritage-moments-935-norbert-singer-timo-bernhard-42018.html)
2. **993 Carrera data must not be relabelled as Turbo data.** A factory workshop-manual facsimile states approximately 1:1.60 crankshaft-to-fan and 1010 L/s at 6000 crankshaft rpm, on the 993 Carrera technical-data page. That implies approximately 9600 fan rpm, ignoring slip. Test pressure, air density and uncertainty are not supplied on that page. [Manual, PDF page 17, zero-based page 16](https://manualplace.com/lib/porsche-993-workshop-manuals-sample.pdf)
3. **The repeated Turbo flow figure has an unresolved speed conflict.** A secondary transcription for M64/60, MY1997–98 gives 1210 L/s at 5750 engine rpm and a 1:1.8 ratio. Forum tables give 1210 L/s at 6100 engine rpm. Neither is a full fan map. The transcription contains an unrelated obvious unit error (100 mm paired with 3.49 inches), so it cannot substitute for the original technical-data page. Preserve both reported operating points and leave the accepted Turbo value unset. [Transcription](https://www.elferclassic.de/technik/techdaten/993-turbo-95-98-techdat.php), [forum example](https://forums.pelicanparts.com/911-engine-rebuilding-forum/728120-5-blade-fan.html)
4. **A valuable Porsche-authored engineering paper exists, but its full fan curve was not verified here.** SAE 920789, Manfred Hochkönig and Rauser Michael, Porsche AG, *Cooling System Layout for High Performance Cars*, 1992, DOI 10.4271/920789. The public abstract describes pressure-difference-based development for air- and liquid-cooled systems. A forum says the paper contains a 964 pressure/flow/efficiency/surge map. Obtain the paper legitimately before digitizing or citing that figure as verified data. [Publisher](https://saemobilus.sae.org/papers/cooling-system-layout-high-performance-cars-920789), [lead only](https://shoptalkforums.com/viewtopic.php?t=59175)
5. **A genuine open benchmark can validate the numerical workflow without pretending to be Porsche geometry.** EAA FAN-01 v5 supplies rotor CAD, performance, LDA, unsteady pressure and acoustic datasets. Its Zenodo page explicitly displays CC BY 4.0; the licence was verified in the cloud browser, not inferred from Zenodo defaults. Keep it in a separate benchmark namespace. [Dataset, version DOI](https://zenodo.org/records/20037409)

## Evidence classes and admission rules

Use distinct fields for source authority, method and verification state. A factory value can be approximate; a careful physical measurement can describe a worn or incorrect part; a vendor can accurately describe its own replacement while not describing the factory rotor.

- **Manufacturer primary:** original Porsche manual/drawing; manufacturer test or material sheet. Record document revision, page and applicability. A facsimile hosted elsewhere remains factory-authored content, but host authenticity and republication rights are separate questions
- **Measured primary:** raw or traceable measurements on an identified specimen, including calibration and uncertainty
- **Research primary:** original experiment or numerical benchmark, not a secondary summary of it
- **Vendor assertion:** listing or commercial specification; useful for locating a candidate, not a manufacturing tolerance
- **Forum/secondary lead:** traceable quotation, user experiment or transcription; preserve author/date/context and do not promote repetition to corroboration
- **Derived:** calculation with named inputs and assumptions, kept distinct from an observed value
- **Unavailable:** no inspected source establishes the quantity. Use null, never zero or a silent guessed default

Do not use a single global confidence score. A source may have high confidence for a part number but low confidence for blade geometry or airflow. A numeric value needs variant, configuration, units, datum, test conditions, uncertainty or explicit “not stated,” and its permitted use.

## Quantitative information available now

### Porsche-family evidence

| Specimen/application | Quantity | Reported value | Conditions / caveats | Use |
|---|---|---:|---|---|
| 993 Carrera manual page | Fan/engine speed ratio | approx. 1.60 | Factory-authored facsimile; Carrera | Context only for Turbo |
| Same | Air delivery | 1010 L/s | 6000 crank rpm; pressure/density unspecified | Single historical point, not a fan curve |
| Same, calculated | Fan speed | approx. 9600 rpm | 6000 × 1.60; slip ignored | Derived context |
| 993 Turbo, secondary table | Fan/engine speed ratio | 1.8 | M64/60 MY1997–98; OEM page unverified | Candidate input requiring confirmation |
| Same | Air delivery | 1210 L/s | 5750 engine rpm | Conflicts with forum speed |
| 993 Turbo, forum table | Air delivery | 1210 L/s | 6100 engine rpm | Unverified lead |
| Early 911 T factory manual | Air delivery | approx. 1230 L/s | 5800 rpm as stated in table | Historical comparison only |
| Early 911 E/S factory manual | Air delivery | approx. 1380 L/s | 6500 rpm as stated in table | Historical comparison only |
| Early 911 T/E/S factory manual | Crank/fan ratio | approx. 1:1.3 | Table context must accompany use | Not a 993 specification |
| Early 930 Turbo factory manual section | Air delivery | 1560 L/s | 6000 crank rpm, ratio approx. 1:1.67 | Section is early 930; host title “1989” is not model applicability |

Early-manual sources: [911 technical table](https://pca-chicago.org/wp-content/uploads/2024/02/911ServiceManual-1971.pdf), [930 manual, hosted page 14; engines in preceding section include 930/50–54](https://www.manualslib.com/manual/392505/Porsche-911-Turbo-1989.html). These points do not establish relative fan efficiency: shaft power and matching system resistance are absent.

### Explicitly licensed generic benchmark

The original FAN-01 research describes 495 mm rotor diameter, 248 mm hub, 2.5 mm tip clearance, nine NACA 4510-profile blades, zero skew, 1486 rpm, and a 1.4 m³/s design operating flow. The intended total-to-static pressure was 150 Pa; the measured rise at the design point was 126.5 Pa and efficiency 53%. Do not mistake the design target for measured pressure. It is a much larger, slower rotor than the Porsche candidates. [Original authors’ benchmark description](https://arxiv.org/html/2211.12014v1)

Version v5 files useful for a minimal reproducible CFD validation package: cad_model.zip (6.5 MB), characteristic.zip (34.8 kB), LA_Case4_AxialFan_measurements.pdf (2.2 MB), lda_data.zip (748.4 kB). The record also includes much larger microphone datasets. File checksums and licence provenance are in evidence.json. No benchmark archive was downloaded, executed or republished in this research pass. [Versioned file index](https://zenodo.org/records/20037409)

## Scan identity, scale and registration

The parent reports a purchased file named `Fan0.5mm back not lined up with center.obj`, with 624492 vertices, 1240465 faces and 8611 open edges. These are **reported diagnostics**, not an independent inspection in this lane. Neither “0.5mm” nor vertex count establishes physical units, accuracy, sample spacing, or dimensional tolerance. The wording flags possible registration trouble; it does not prove which portion is wrong.

### Minimum evidence to establish scale

Obtain at least two independent, well-separated physical lengths on the actual scanned specimen, ideally one large radial and one axial dimension. A third scale check is strongly recommended. Prefer a calibrated ring diameter or a known clean machined bore, hub register diameter, and a face-to-face distance. Record instrument, calibration, uncertainty, temperature, measurement direction, and exact mesh-feature correspondence.

Fit one uniform scale to the raw file, then inspect independent residuals. A unit candidate such as metres versus millimetres is only a hypothesis until checked. Different radial and axial scale factors can hide scan distortion; never apply them silently. Do not force this scan to 245 mm because a 993 replacement listing uses that nominal number.

### Functional coordinate system

- Datum A: rotation axis fitted to a verified machined bore, shaft seat or register, using multiple axial sections and fit residuals
- Datum B: mounting/abutment plane, independently fitted; record its perpendicularity to A rather than forcing it flat without reporting the change
- Datum C: keyway, indexed hole or another non-axisymmetric reference; defines the angular zero and prevents ambiguous blade-phase alignment
- Origin: A intersecting B
- +Z: explicitly selected along the intended through-flow direction; verify the sign with the real assembly
- +X: ray from A toward C; +Y completes a right-handed frame
- Rotation: record clockwise/counter-clockwise **with the viewing direction**, plus signed angular velocity in that frame

A global principal-component axis is a useful diagnostic, not the preferred functional datum. Missing geometry, nonuniform point density, cup openings and misregistered backs can bias it. Do not align the back to the front solely by centroid or unconstrained whole-surface ICP.

### Registration and topology workflow to perform later

1. Preserve the raw asset, provenance, licence and content hash
2. Identify disconnected components and front/back acquisition surfaces; distinguish holes caused by missing data from intentional openings
3. Establish scale and A/B/C before fitting blade stations
4. If separate passes exist, register using common reliable features with one rigid transform per pass; quantify overlap residuals and withheld-feature error
5. Store the homogeneous transform, fitted features, residual statistics and any rejected points
6. Generate a cleaned derivative. Record every fill, smoothing, remesh and inferred surface with a mask; do not alter the raw file
7. Compare each blade independently before deciding whether a mean/periodic blade is appropriate
8. Check watertightness, self-intersections, face orientation and minimum-feature preservation separately from dimensional fidelity

“Watertight” is a meshing property. It does not prove correct thickness, alignment, units, balance, strength, or aerodynamic fidelity.

### Vendor provenance questions

Ask the seller for specimen year/model, original part/casting number, maker, blade count, physical outer diameter, shaft/bore dimensions, measurement units, scanner and calibration, nominal point spacing versus accuracy, preprocessing history, and original unregistered passes. Ask whether the purchased part is a factory piece, replica, repair or modified rotor, and what the filename means.

The Wolfe Classics related air-guide listing is titled 935 but describes a 934 guide, and offers separate top/bottom scans after purchase. That is an identity lead, not proof that the rotor scan is wrong. [Listing](https://www.wolfeclassics.com/shop/p/porsche-935-air-guide-3d-scan) A fan-drive scan is also listed, but its exterior cannot reveal hidden gear geometry, heat treatment or bearing ratings. [Drive listing](https://www.wolfeclassics.com/shop/p/porsche-935-fan-drive-3d-scan)

## What must be measured before any 993 installation claim

See measurement-checklist.md for acquisition detail. The gate is a complete interface stack for **both** the scanned rotor and an identified target 993 Turbo assembly:

- Rotor swept diameter and axial envelope, hub/cup profile, blade handedness and count
- Central bore/register and bearing seats, fits, shoulders, key/spline or bolt pattern, fasteners and retaining method
- Mounting-face location relative to blade leading/trailing edges, axial runout and radial runout
- Fan housing inner contour, eccentricity, mounting and downstream stator/support geometry
- Cold clearances and hot/rotating tolerance stack, including deformation and bearing/shaft motion
- Pulley effective pitch diameters, belt section, belt path, fan versus alternator speeds, slip and tension/load limits
- Target alternator’s exact manufacturer/model/revision, shaft and front/rear interfaces, cooling paths, mass and bearing loads
- Rear cone, impeller, holes, ribs, stators and shroud branches that influence blockage and distribution

Matching rotor outer diameter and blade number are insufficient. Matching a rotor in free air is also insufficient when the housing, obstruction, inlet distortion and engine pressure loss differ.

## Parametric representation

parameter-contract.json defines a reusable record shape and parameter dictionary. The goal is to preserve measured geometry, support controlled changes and expose unknowns.

Represent blade geometry at explicit radial stations. At each station store leading/trailing-edge points, chord, signed stagger, camber/thickness functions, leading-edge radius, trailing-edge thickness, and their source/uncertainty. Use a documented cylindrical-section unwrapping convention. Define stagger relative to the local tangential direction; an angle to the axial direction is a different parameter. Store axial sweep, tangential skew and stacking reference separately. Do not call every curved outline “pitch.”

Retain each blade and angular position in the measurement layer. A periodic idealization is a distinct derivative with residual maps. Root fillets and thickness minima are structural inputs; do not erase them with an airfoil fit. Porsche airfoil coordinates and spanwise twist were not found in the inspected primary sources. NACA 4510 belongs to FAN-01, not to Porsche.

Represent hub, cup, shaft and housing with axial profiles plus explicitly indexed openings, ribs, holes and machined interface surfaces. Keep rotating and stationary parts separate. Parameter coupling should prevent blade changes from accidentally changing the bearing fit or pulley offset.

## CFD plan and validation boundaries

### First build a measured baseline

Specify the complete configuration: inlet bellmouth/grille/intercooler or other obstruction, rotor, housing, alternator/supports/rear cone, downstream shroud, engine-fin resistance and outlet environment. Record inlet temperature, pressure, humidity/density and turbulence; do not substitute ambient for measured engine-bay inlet air without saying so.

Test pressure rise, flow and torque across a throttled operating range at several measured fan speeds. Define whether pressure is total-to-total, total-to-static or static-to-static, the exact pressure stations, and whether power is rotor shaft, drive shaft or electrical. Meter alternator loading separately from fan aerodynamic power. Map pressure and flow distribution into the cylinder/head branches, not only total volume flow.

Use a steady rotating-frame model for initial screening if appropriate, followed by unsteady sliding-mesh validation where blade/stator interaction, distorted inflow or unstable operation matters. Document turbulence/wall treatment, roughness, tip-gap resolution, domain extent, mesh/time-step studies, mass conservation and torque convergence. A converged residual alone is not experimental validation. FAN-01 can test the solver workflow, but the Porsche assembly still needs its own validation points.

ISO 5801:2017 covers standardized fan performance tests and uncertainty/conversion rules; its 2025 amendment should be considered. ISO/TR 16219:2024 specifically warns that actual installation effects depend on exact fan/disturbance geometry. These are useful method references, not a claim that a Porsche fan is certified to them. [ISO 5801](https://www.iso.org/standard/56517.html), [system effects](https://www.iso.org/standard/87617.html)

### Derived checks, never substituted measurements

For the same geometrically similar fan/housing at comparable Reynolds/Mach regimes, classical incompressible similarity gives Q proportional to nD³, pressure rise proportional to density·n²D², and impeller power proportional to density·n³D⁵. Changing only ratio 1.60 to 1.80 would imply 12.5% more speed, approximately 26.6% more pressure and 42.4% more impeller power at corresponding points. These are conditional calculations, **not** predicted 993 Turbo gains or measured data. Different blades or a different system can invalidate the comparison. [AMCA fan laws](https://www.amca.org/assets/resources/public/resources/ansi-amca-99-25-standards-handbook.pdf), [AMCA conversion equations](https://www.amca.org/assets/resources/public/pdf/Publications/amca-211-22-%28rev.-01-23%29.pdf)

Calculate tip speed from verified diameter and rotor speed; evaluate local relative Mach number using axial/tangential inflow, not tip circumferential speed alone. Track blade-passing frequency and relevant shaft/engine excitation orders for structural/acoustic work. A generic low-Mach benchmark does not establish incompressibility for a fast Porsche rotor.

### Cylinder heat-transfer research, distinct from fan validation

Sarah Chapman's 2023 Macquarie thesis is available as an author-uploaded manuscript. Section 4.1.1.1.1 reports 0.317 m³/s at 5000 crank rpm from PR Technology via Symons (2021), then imposes a uniform inlet. Raw test conditions/uncertainty are missing. Section 5.1 says actual Porsche-engine experimental validation was not completed. It is a thermal-method lead, not a Turbo fan curve. No institutional copy was found in targeted searches. [Manuscript](https://www.researchgate.net/publication/372237377_Heat_transfer_optimization_of_a_3D_printed_air-cooled_aftermarket_Porsche_engine)

Useful primary validation literature for the downstream cooling system:

- Thornhill and May, SAE 1999-01-3307: electrically heated finned cylinders tested over 12–50 m/s. Useful for heat-transfer-method checks, not Porsche rotor geometry. [Publisher](https://saemobilus.sae.org/papers/experimental-investigation-cooling-finned-metal-cylinders-a-free-air-stream-1999-01-3307)
- Thornhill et al., SAE 2003-32-0034: finned-cylinder tests over 2–20 m/s and variation of fin pitch/length. [Publisher](https://saemobilus.sae.org/papers/experimental-investigation-free-air-cooling-air-cooled-cylinders-2003-32-0034), [Queen's Belfast record](https://pure.qub.ac.uk/en/publications/experimental-investigation-into-the-free-air-cooling-of-air-coole/)
- Thornhill et al., SAE 2006-32-0039: circumferential heat-transfer distribution, 100 mm external cylinder diameter and 10–50 mm fins. [Publisher](https://saemobilus.sae.org/papers/experimental-investigation-temperature-heat-transfer-distribution-around-air-cooled-cylinders-2006-32-0039)
- Yoshida et al., JSME 49(3), 869–875 (2006): experiments show that adding tightly spaced fins can fail to improve cooling at low velocity. This supports measuring the coupled fin-channel resistance and temperature field rather than maximizing surface area alone. [J-STAGE, DOI 10.1299/jsmeb.49.869](https://www.jstage.jst.go.jp/article/jsmeb/49/3/49_3_869/_article)

These experiments are not interchangeable with the installed 993 shroud/fin system. Original geometries, loads, boundary conditions and uncertainty must accompany any validation reuse.

## FEA, balance and LPBF release requirements

Do not optimize on airflow alone. The rotor must survive combined centrifugal, aerodynamic, thermal, joint and vibration loads with the manufactured surface and defect state.

Required analyses include centrifugal prestress, thermal gradients and growth, blade/root/hub stress, contact/retention and fit stresses, rotor-shaft-bearing dynamics, prestressed modes and a speed-dependent Campbell diagram, fatigue under mission cycles and mean stress, and sensitivity to defect/roughness/tolerance extremes. Include belt/gear loads and the real support stiffness. A fixed bore in FEA can conceal the real joint or shaft failure mode.

The exact original Porsche alloy/condition, residual-unbalance acceptance, modal frequencies, fatigue allowables and burst/overspeed acceptance were not found in inspected primary sources. Do not invent a G grade, safety factor or overspeed multiplier. Agree them with the responsible rotor engineer and test facility before hardware release. ISO 21940-11 addresses rigid-rotor balancing; flexible behavior belongs to a different method. ISO 14694 is a fan balance/vibration reference, not proof of automotive applicability. [Rotor balancing](https://www.iso.org/standard/54074.html), [fan balance/vibration](https://www.iso.org/standard/37371.html)

An LPBF alloy name alone is not a material card. Record machine, parameter-set revision, powder chemistry/lot/reuse, build orientation, layer size, support strategy, heat treatment, stress relief, HIP if qualified, machining, surface finish, inspection and coupons. Avoid enclosed powder traps. Printability minimum wall thickness is not a fatigue-safe blade thickness.

One primary candidate-material reference is EOS AlSi10Mg. For the EOS M 290 / 30 µm process, the sheet reports ≥2.67 g/cm³ density, typical as-manufactured vertical/horizontal yield strengths 230/270 MPa, and a 110 MPa fatigue figure on turned, fully reversed specimens at 20 million cycles without heat treatment. These are process- and specimen-specific values, not blade allowables. The sheet explicitly ties fatigue to surface/geometry and does not assert an aluminium endurance limit. [EOS, PDF pages 5–9](https://eos.info/05-datasheet-images/Assets_MDS_Metal/EOS_Aluminium_AlSi10Mg/Material_Datasheet_EOS_Aluminium_AlSi10Mg_EN.pdf)

Release gates should require traceable geometry inspection, qualified material/process evidence, NDT appropriate to the critical defects, final balance in the actual assembly condition, guarded remote spin testing at an agreed test envelope, aerodynamic verification and hot engine-system validation. No safe operating speed or printable design is established by this report.

## Publication and licence boundary

The research package contains original synthesis, small factual extracts, source links and measurement fields. It contains no vendor meshes, copied manual pages, patent plates or SAE figures. Buying a scan does not by itself establish permission to redistribute it or a derived mesh in a public GitHub repository. Capture the actual licence and permitted derivative/redistribution scope before committing geometry. Preserve source-specific licences separately from the repository’s own licence.

FAN-01 is explicitly CC BY 4.0 in the inspected v5 record. If copied later, retain creator attribution, DOI/version, licence and a description of changes; inspect archive-internal notices too. Public access alone is not an open licence for any other asset.

## Remaining source-acquisition priorities

1. Original 993 Turbo technical-data/Service Information page covering M64/60 fan ratio and airflow, including revision and test conditions
2. Lawful full text of SAE 920789; verify actual figure model, axis units, pressure definition, speed, efficiency definition, surge annotation and possible data-reuse permission
3. Original 934/935 parts/service documentation or an identified original specimen with measurements; no image-derived dimensions without calibration
4. Seller clarification and calibrated dimensions for the purchased scan; exact meaning of the unaligned-back filename
5. Target 993 Turbo housing, hub, pulley and selected alternator interface drawings; dimensions from unrelated 997 or 175 A units do not fill these gaps
6. Bench pressure–flow–torque map and cylinder-distribution measurements of the exact baseline assembly
7. Qualified printed-material fatigue/defect data matching the chosen process and blade finish, plus a professional spin/balance validation plan

## Search coverage and negative findings

Public searches included English/German/French/Italian/Japanese terms for 911/993/935 fan, blower, cooling, geometry, dimensions, CAD, scan, pressure and engineering papers. No inspected source supplied an openly licensed, dimensionally validated Porsche 935 or 993 Turbo rotor CAD model, spanwise section coordinates, complete fan map, or factory FEA/material/balance release specification. This is a bounded search result, not proof that none exists.

Patent results inspected or screened included US2980194A (older air-cooled boxer architecture), US4677941A (electrical cooling-fan control), US4889382A (rear spoiler/intake ducting), EP0531792A2 (electric reluctance-motor fan), and DE102010036660B4 (secondary-air mechanism). They are not 935/993 rotor manufacturing drawings and were not used to infer blade dimensions. [Older boxer patent](https://patents.google.com/patent/US2980194A/en), [electrical fan patent](https://patents.google.com/patent/US4677941A/en), [blower patent](https://patents.google.com/patent/EP0531792A2/en)

A contemporary porschefanatics project page appeared in search and explicitly describes unvalidated reconstruction assumptions. It was excluded as independent corroboration because it may represent the same project context, and its geometry is not a primary measurement. Likewise, scale-model assembly drawings, game/visualization CAD and fan-art meshes were not accepted as engineering data.
