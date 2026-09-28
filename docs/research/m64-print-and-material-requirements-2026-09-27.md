# Manufacturing-Requirements Report: '3D Printable Part' for the M64/60 Digital Twin

## 1. Service Conditions From Repository Evidence

**Charge-air temperature post-intercooler**
- **50 °C** (assumed value for simulation envelope, no measured Porsche data). Range estimated: **38–59 °C** using intercooler effectiveness 0.60–0.75 with compressor efficiency 0.65–0.75, gamma 1.4, and T1 20 °C.
- Status: derived from synthetic 0D mass-flow model, **not a sensor measurement**.
- Evidence: `docs/TURBO_AIRFLOW_SIMULATION_DATA.md`, section "First calculated mass-flow envelope".
- **For intake-duct and intercooler end-tank candidates: use 50–60 °C as design condition; mark unknown beyond that range.**

**Engine-bay air temperatures**
- Repository explicitly states: **unknown**. Documentation cites fan flow 1,210 l/s at 5,750 rpm as *engine cooling*, not intake flow, and forbids replacing ambient with that figure.
- No published ambient, underhood soak, or hot-soak temperature in `docs/993/`, `catalog/parts/`, or the simulation data file.
- Cooling-fan-system dossier (fan housing + impeller F0) tests a synthetic 252 mm housing against 280 mm impeller; clearance failure at −14 mm is geometric, not thermal.
- **Mark engine-bay ambient and hot-soak unknown; cite only the cooling flow, not a temperature.**

**Exhaust-gas temperatures (hot side)**
- **900 K = 627 °C** in the exhaust-manifold F0 screening (synthetic case: 3.6 L, 5,750 rpm, VE 0.95, 900 K gas, 50 kPa gauge).
- Turbine-wheel IN718 screening cites a **synthetic 427 °C** service condition that blocks the Ti-6Al-4V route against its 400 °C creep ceiling.
- Status: **screening boundary conditions, not measured T3 or turbine-inlet data**; repository states "Measure pulsed pressures and temperatures, lambda, ignition, flow, vibration spectrum, turbine map and duty cycles" as a next gate.
- **For exhaust-side candidates (manifold, turbine wheel, heat shield, oil return line, exhaust tip): use 900 K or 427 °C as screening limits; mark real T3 unknown.**

**Piston-temperature envelope**
- CalculiX thermomechanical screening (mesh 2.5 mm): **Hot Tmax 187.04 °C** on the CP1 piston-gallery F0 concept.
- Material card: Constellium AHeAD CP1 publishes qualitative stability toward **250–300 °C**; no qualified hot allowables for LPBF piston service.
- **Mark piston crown, ring-land, and gallery temperatures unknown beyond the synthetic CalculiX result.**

**Oil-side temperatures**
- Turbo oil return line dossier cites **120 °C** for hydraulic screening (2 L/min, oil density 850 kg/m³, viscosity 0.015 Pa·s).
- Status: synthetic fluid temperature, not a measured oil-sump or turbo-bearing temperature.
- **Use 120 °C as a screening oil temperature; mark real oil circuit unknown.**

**Summary table (service conditions by part family)**

| Component family | Gas/air/oil condition | Source | Status |
|---|---|---|---|
| Cold-side intake duct, intercooler end tank | Post-intercooler charge air **50–60 °C** | TURBO_AIRFLOW_SIMULATION_DATA.md mass-flow model | Derived assumption; no sensor |
| Engine-bay mounted parts (fan housing, valve cover, bracket) | Ambient / hot-soak | No repo source | **Unknown** |
| Exhaust manifold (IN625 LPBF candidate) | Exhaust gas **900 K (627 °C)** | 993_EXHAUST_MANIFOLD_IN625_F0.md screening | Synthetic; not measured T3 |
| Turbine wheel (IN718 candidate) | Turbine service **427 °C** | am-validation-policy.json Ti-6242 screen | Synthetic blocking value |
| Piston (CP1 gallery F0) | Hot CalculiX p95 **187 °C**, max temp; material stability **250–300 °C** claimed | 993_PISTON_CP1_COOLING_GALLERY_F0.md | FEA result; no hot allowable |
| Turbo oil return line (IN625) | Oil **120 °C** | 993_TURBO_OIL_RETURN_LINE_IN625_F0.md | Synthetic hydraulic point |

---

## 2. Candidate Processes Mapped to Service Conditions

### 2.1 Metallic LPBF (repository screens AlSi10Mg, Ti64, IN625, IN718)

All values from EOS M 290 datasheets indexed in `catalog/sources/` and mirrored in `catalog/manufacturing/processes/`.

#### AlSi10Mg (EOS M 290, 30 µm, TRL 9)
- **Process card**: `catalog/manufacturing/processes/eos-m290-alsi10mg-30um.json`
  - Source: https://www.eos.info/metal-solutions/data-sheets/aluminium/pds-eos-aluminium-alsi10mg-eos-m-290-30um
  - Min. wall thickness: **0.4 mm**
  - Coupon properties (heat-treated): vertical Rp0.2 **233 MPa**, horizontal Rp0.2 **270 MPa**, min. Rm **461 MPa**
  - Fatigue strength (fully reversed, 2×10⁷ cycles): **110 MPa**
  - Thermal conductivity: vertical **100 W/(m·K)**, horizontal **110 W/(m·K)**
  - CTE (25–100 °C): **20×10⁻⁶/K**; (25–200 °C): **22×10⁻⁶/K**; (25–300 °C): **27×10⁻⁶/K**
- **Service-temperature limit**: no published hot yield or creep ceiling in the EOS card. Constellium AHeAD CP1 (comparable high-strength Al for AM) claims qualitative stability toward **250–300 °C** (piston dossier). Treat **200 °C** as a conservative screening ceiling for AlSi10Mg strength retention; mark exact limit unknown.
- **Tolerance class**: EOS M 290 with 30 µm layer achieves **ISO 2768-mK** to **±0.1–0.2 mm** on machined features; as-built surfaces require allowance.
- **Surface roughness**: after shot peening **Ra 5–9 µm** (Ti64 card cites same range; AlSi10Mg card does not publish a roughness value explicitly, but LPBF aluminum as-built is typically **Ra 10–20 µm** horizontal, **Ra 15–30 µm** vertical).

#### Ti-6Al-4V Grade 5 (EOS M 290, 30 µm, TRL 9)
- **Process card**: `catalog/manufacturing/processes/eos-m290-ti64-30um.json`
  - Source: https://3dformtech.fi/wp-content/uploads/2019/11/Ti-Ti64_9011-0014_9011-0039_M290_Material_data_sheet_11-17_en-1.pdf
  - Min. wall thickness: **0.3–0.4 mm**
  - Heat treatment: **800 °C for 2 h under argon**
  - Coupon properties (HT): horizontal Rp0.2 **945 MPa**, Rm **1055 MPa**, elongation **13 %**; vertical Rp0.2 **965 MPa**, Rm **1075 MPa**, elongation **14 %**
  - Surface roughness after shot peening: **Ra 5–9 µm**
- **Service-temperature limit**: **400 °C** creep-limited ceiling (repository card cites "literature commonly gives 350–400 °C for Ti-6Al-4V due to early beta-phase creep"). Not a supplier guarantee or part allowable.
- **Tolerance class**: comparable to AlSi10Mg; **ISO 2768-mK** to **±0.1–0.2 mm** machined.
- **Surface roughness**: as-built **Ra 10–20 µm**; after peening **Ra 5–9 µm**.

#### IN625 / UNS N06625 (EOS M 290, 40 µm, stress-relieved 870 °C × 1 h)
- **Process card**: `catalog/manufacturing/processes/eos-m290-in625-40um.json`
  - Source: https://www.eos.info/05-datasheet-images/Assets_MDS_Metal/EOS_NickelAlloy_IN625/Material_DataSheet_EOS_NickelAlloy_IN625_en.pdf
  - Min. wall thickness: **not explicitly published in the card**; LPBF nickel superalloys typically achieve **0.3–0.5 mm**
  - Stress relief: **870 °C for 1 h, rapid cooling**
  - Coupon properties (as-manufactured): vertical Rp0.2 **630 MPa**, Rm **870 MPa**, elongation **48 %**; horizontal Rp0.2 **720 MPa**, Rm **980 MPa**, elongation **33 %**
  - Elevated-temperature tensile (heat treated, tested per ISO 6892-1): stress-rupture at **131 MPa / 816 °C** for **231 h** (vertical), **132 h** (horizontal)
  - Surface roughness: **Ra 1–5 µm** (both horizontal and vertical; datasheet section "Surface Roughness")
- **Service-temperature limit**: **816 °C** (stress-rupture test point in EOS card). For sustained static load with safety factor, screen at **650–700 °C** and mark fatigue/oxidation unknown.
- **Tolerance class**: **ISO 2768-mK** to **±0.15–0.25 mm** machined; 40 µm layer slightly less precise than 30 µm AlSi10Mg/Ti64.
- **Surface roughness**: as-built (per EOS card) **Ra 1–5 µm**. (Note: unusual for LPBF; typical LPBF nickel is Ra 10–20 µm. The EOS card may report after-peening or include a finishing assumption; mark this as datasheet-claimed.)

#### IN718 API (EOS M 290, 40 µm, API 6ACRA heat treatment)
- **Source**: https://www.eos.info/metal-solutions/data-sheets/nickel-alloys/pds-eos-nickelalloy-in718-api-eos-m-290-40um (directly fetched)
  - Min. wall thickness: **Typical 0.3–0.4 mm**
  - Heat treatment: solution **1060 °C ± 10 °C, 120 min**, forced Ar quench 130 °C/min (1060–300 °C); aging **815 °C ± 5 °C, 360 min**, forced Ar cool ~25 °C/min (815–300 °C)
  - Coupon properties (HT, room temperature per EN ISO 6892-1): vertical Rp0.2 **865 MPa**, Rm **1236 MPa**, elongation **28 %**; horizontal Rp0.2 **882 MPa**, Rm **1267 MPa**, elongation **26 %**
  - Density: **8.15 g/cm³**; average defect **0.03 %**
  - CTE (25–700 °C): **15.5×10⁻⁶/K**
- **Service-temperature limit**: EOS describes IN718 as **suitable up to 700 °C** (repository card note). API 6ACRA qualification covers oil/gas drilling equipment; aerospace turbine practice commonly uses IN718 to **650 °C** with creep and LCF qualification. Mark **650–700 °C** as the screening envelope; exact allowable unknown without hot coupon data.
- **Tolerance class**: **ISO 2768-mK** to **±0.15–0.25 mm** machined (same 40 µm process family as IN625).
- **Surface roughness**: EOS page does not publish a numeric Ra value for IN718; assume LPBF-typical **Ra 10–20 µm** as-built, **Ra 5–10 µm** after peening/machining; mark unknown from datasheet.

### 2.2 Polymer Powder-Bed Fusion (SLS/MJF) for cold-side ducting (PA12, PA11)

No EOS polymer datasheet is indexed in `catalog/sources/`; web sources below are public manufacturer pages.

#### PA12 (polyamide 12, SLS)
- **Typical SLS PA12 heat-deflection temperature (HDT @ 1.8 MPa)**: **~70–80 °C**
- **Continuous use temperature**: **~80–90 °C**
- **Min. wall**: **0.8–1.0 mm** (EOS, Formnext, and typical industrial SLS guidelines)
- **Tolerance class**: **±0.2–0.3 mm** (EOS FORMIGA P 110, Boschrexroth, typical SLS capability)
- **Surface roughness**: **Ra 10–15 µm** as-built (unfilled PA12)
- Source examples: EOS PA 12 materials page; BASF Forward AM Ultrafuse PA12; Farsoon EOSINT P series documentation.
- **Verdict for post-intercooler charge-air duct**: marginal. If the true post-IC temperature is **50–60 °C**, PA12 has a small thermal margin; if real IAT reaches **70–80 °C** in hot soak or traffic, PA12 exceeds HDT and creeps. **Not recommended for permanent charge-air service without verified IAT < 60 °C sustained.**

#### PA11 (polyamide 11, bio-based, SLS)
- **HDT @ 1.8 MPa**: **~60–70 °C**
- **Continuous use**: **~70–80 °C**
- Marginally lower temperature limit than PA12; even less suitable for charge-air ducts.

#### PEI 1041 / ULTEM (polyetherimide, SLS or FDM)
- **HDT @ 1.8 MPa**: **~170–175 °C**
- **Continuous use temperature**: **~170 °C** (Sabic ULTEM 1010/1040 datasheets; BASF Forward AM ULTEM AM dataset)
- **Min. wall**: **1.0–1.5 mm** (SLS); **0.8–1.0 mm** (FDM Stratasys/MARKFORGED)
- **Tolerance**: **±0.2–0.5 mm** (SLS); **±0.1–0.3 mm** (FDM with support removal)
- **Surface roughness**: **Ra 8–12 µm** (SLS); **Ra 10–20 µm** (FDM)
- **Verdict for cold-side intake or coolant-side shroud**: service-credible for temperatures up to ~150 °C. For charge-air at **50–60 °C**, PEI is over-specified; for engine-bay shrouds or brackets, it handles hot soak but is expensive and may be mechanically over-designed.

#### GF/CF-filled nylons (PA6-GF, PA12-CF, high-temperature nylons PA6T, PA9T)
- **PA6-GF (30 % glass-filled)**: HDT **~210–220 °C**; continuous use **~120–140 °C**
- **High-temperature nylons (PPA, PA6T/6I)**: HDT **~250–280 °C**; continuous use **~140–150 °C**
- These are service-credible for engine-bay ambient and hot soak. Not currently screened in the repository.

### 2.3 Explicit exclusion: PETG and PLA

**PETG:**
- HDT @ 1.8 MPa: **~65–75 °C**
- Continuous use: **~60–70 °C**
- **Not service-credible** for charge-air ducting at 50–60 °C sustained with hot-soak margin, or for any engine-bay application. Creep under bolt preload and thermal aging make it unsuitable.

**PLA:**
- HDT @ 1.8 MPa: **~55–65 °C** (unfilled); heat-treated or blended variants reach ~80–100 °C but lose ductility
- Continuous use: **~50–60 °C**
- **Not service-credible** for any underhood application. Brittle, low Tg (~60 °C), poor creep resistance, poor UV and hydrolytic stability.

---

## 3. Missing Print-Release Gate: Geometric And Process Constraints

The repository `am-validation-policy.json` defines 11 release stages but **does not define a numerical design-for-manufacture (DfM) gate** for wall thickness, tolerance, surface, insert strategy, or powder removal. The policy blocks release at stage 04 (material-machine-process card) and stage 07 (recoater and support removal) for every tracked part because:

- No signed EOSPRINT project (orientation, supports, powder evacuation routes).
- No machined-interface allowance specification.
- No part-level dimensional allowables contract.

### 3.1 Minimum wall and feature size by process (proposed gate)

| Process | Min. wall (self-supporting) | Min. wall (with support) | Min. hole (vertical) | Min. hole (horizontal) | Min. edge/fillet |
|---|---|---|---|---|---|
| **AlSi10Mg LPBF (EOS M 290, 30 µm)** | **0.4 mm** (EOS-published) | **0.3 mm** | **1.0 mm** | **0.8 mm** | **R 0.3 mm** |
| **Ti64 LPBF (EOS M 290, 30 µm)** | **0.3–0.4 mm** (EOS-published range) | **0.3 mm** | **1.0 mm** | **0.8 mm** | **R 0.3 mm** |
| **IN625 LPBF (EOS M 290, 40 µm)** | **0.5 mm** (inferred from nickel AM practice; not published) | **0.4 mm** | **1.2 mm** | **1.0 mm** | **R 0.4 mm** |
| **IN718 LPBF (EOS M 290, 40 µm)** | **0.3–0.4 mm** (EOS-published typical) | **0.3 mm** | **1.2 mm** | **1.0 mm** | **R 0.4 mm** |
| **PA12 SLS (EOS FORMIGA P 110)** | **1.0 mm** (EOS guideline) | **0.8 mm** | **1.5 mm** | **1.0 mm** | **R 0.5 mm** |
| **PEI 1041 SLS** | **1.5 mm** | **1.0 mm** | **2.0 mm** | **1.5 mm** | **R 0.5 mm** |

**Rationale**: minimum walls derive from EOS M 290 published cards for AlSi10Mg and Ti64; IN625/IN718 use 0.3–0.4 mm where published or a conservative 0.5 mm for 40 µm nickel. Polymer values follow typical EOS FORMIGA and BASF/Stratasys guidelines.

### 3.2 Achievable tolerance class

**LPBF metals (EOS M 290 family, all materials)**:
- **As-built (no machining)**: **ISO 2768-cL** to **±0.3–0.5 mm** (depends on orientation, support shrinkage, residual stress).
- **With post-machining on critical interfaces**: **ISO 2768-mK** to **±0.1–0.2 mm** (requires design allowance and fixturing plan).
- **Layer-step effect**: horizontal (XY) features can achieve **±0.05–0.1 mm** on a single layer; vertical (Z) features have **±0.15–0.3 mm** due to staircase effect and distortion.

**PA12 SLS**:
- **As-built**: **±0.2–0.3 mm** (EOS FORMIGA P 110; shrinkage ~15–20 % green-to-sinter but compensated in software).
- **With reaming/drilling**: **±0.1 mm** on small holes.

**PEI SLS/FDM**:
- **±0.2–0.5 mm** (SLS); **±0.1–0.3 mm** (FDM, depending on part orientation and support removal).

**Citation**: dimensional accuracy for EOS M 290 is discussed in EOS application notes and the ASTM F3318-18 specification for LPBF AlSi10Mg (indexed in repository as `src-astm-f3318-18.json` but not fetched). Polymer tolerances from EOS FORMIGA and Farsoon guidelines.

### 3.3 Surface roughness effect on duct airflow

**LPBF aluminum (AlSi10Mg) as-built**: **Ra 10–20 µm** (conservative assumption for un-peened, un-machined internal duct).

**Effect on flow**: the repository exhaust-manifold F0 screening calculates **391.78 Pa** loss with **K = 0.2** junction loss but explicitly states "roughness...are absent." For a cold-side intercooler duct or intake runner:

- Smooth machined aluminum or cast: **Ra 1.6–3.2 µm**, Darcy friction factor **f ≈ 0.015–0.02** (fully rough turbulent).
- LPBF as-built: **Ra 10–20 µm**, **f ≈ 0.03–0.05** (transition to fully rough flow at high Reynolds).
- **Penalty**: for a 34 mm-diameter, 200 mm-long runner at **90 m/s** (manifold screening velocity), the wall shear stress and pressure drop can be **2–3× higher** for rough LPBF versus smooth machined.

**For intake-duct candidates**: if the F0 assumes smooth walls, the real LPBF or SLS as-built roughness **increases pressure loss by 30–100 Pa** over a 0.5 m duct run. **Mandatory post-processing**: abrasive-flow machining, electro-chemical polishing, or coated liner if ΔP < 100 Pa is a hard constraint.

### 3.4 Fastener-insert strategy

Repository does not specify threaded-insert or bonded-anchor strategy for any tracked part. **Proposed gate requirement**:

1. **LPBF metal parts**: integral cast-in threaded bosses (machined after build) or helical threaded inserts (Heli-Coil, Keensert) bonded with high-temp epoxy (Upol, 3M DP460, ~150 °C service) or press-fit interference.
2. **PA12/PEI polymer parts**: ultrasonic-set inserts (Heinrich Knebel US-SEAL), heat-set brass inserts, or through-bolt with backing plate. Avoid self-tapping screws into SLS PA12 (low pullout strength).
3. **Torque allowables**: not in repository; contract with supplier and validate by proof test.

### 3.5 Powder-removal volumes for LPBF (closed internal volumes)

Repository exhaust-manifold F0 requires **three open runners converging into one open collector** for depowdering. No closed volume.

Repository piston-gallery F0 has a **closed-ring gallery** with **two temporary radial ports** that must be plugged and CT-verified after powder evacuation.

**Gate requirement**: 
- **Any LPBF part with an enclosed internal volume must have at least one powder-exit hole ≥ 3× the nominal powder PSD D₉₀ (EOS IN625 powder sieves at 63 µm; exit ≥ 2 mm for safety margin).**
- **The depowder path must be verified by CT or borescope after build and before heat treatment.**
- **Open inlets/outlets are acceptable (manifold, oil return line); sealed volumes require proof of evacuation.**

---

## 4. Per-Candidate Material/Process Table (Condensed)

| Part ID (abbrev.) | Service Condition | Proposed Material | Process | Material Limit | Screening Margin | Key Unknowns | Citations |
|---|---|---|---|---|---|---|---|
| **993-ENG-EXH-MANIFOLD-IN625-F0** | Exhaust gas **627 °C** (900 K screening) | IN625 | LPBF EOS M 290, 40 µm | **816 °C** (stress-rupture) | **1.30×** temperature (816/627) | Real T3, pulsation, creep life, fatigue, oxidation, full-build distortion | EOS IN625 card; repo manifold F0 |
| **993-ENG-K16-TURBINE-WHEEL-IN718-F0** | Turbine service **427 °C** (synthetic) | IN718 API | LPBF EOS M 290, 40 µm | **650–700 °C** (EOS claims; API 6ACRA scope) | **1.52–1.64×** temp at 427 °C screening | Hot HCF, overspeed, creep life, rotor balancing, real turbine map | EOS IN718 PDS; am-validation-policy |
| **993-ENG-TURBO-HEAT-SHIELD-IN625-F0** | Radiant/exhaust-side hot gas (temperature unknown, likely 400–600 °C) | IN625 | LPBF or sheet metal | Same as manifold: **816 °C** | Unknown without measured temperature | Radiant flux, contact temp, vibration, attachment design | Repo part JSON; EOS IN625 card |
| **993-ENG-TURBO-OIL-RETURN-LINE-IN625-F0** | Oil **120 °C** (synthetic hydraulic) | IN625 | LPBF | **816 °C** | **6.8×** | Real oil temp, backflow dynamics, vibration, mounting, leak life | Repo oil-line F0; EOS IN625 card |
| **993-ENG-FAN-HOUSING-ALSI10MG-F0** | Engine-bay ambient/hot-soak (unknown) | AlSi10Mg | LPBF or casting | **200 °C** (conservative screen) | Unknown without bay temp | Real bay temp, impeller-tip clearance, overspeed, containment, fatigue | Repo fan-system F0; EOS AlSi10Mg card |
| **993-ENG-COOLING-IMPELLER-ALSI10MG-F0** | Same as housing (engine-bay air) | AlSi10Mg | LPBF or CNC | **200 °C** | Unknown | Rotational speed, centrifugal stress, balance, blade fatigue, containment | Repo fan-system F0; EOS AlSi10Mg card |
| **993-ENG-INTERCOOLER-END-TANK-ALSI10MG-F0** | Charge air **50–60 °C** (post-intercooler) | AlSi10Mg | LPBF | **200 °C** | **3.3–4.0×** temp; pressure ΔP | Burst pressure, thermal cycling, braze/weld to core, vibration, real IAT | TURBO_AIRFLOW doc; EOS AlSi10Mg card |
| **993-ENG-THREE-RUNNER-INTAKE-ALSI10MG-F0** | Intake charge **50–60 °C** | AlSi10Mg | LPBF | **200 °C** | **3.3–4.0×** temp | Powder removal from 34 mm runners, real IAT, pressure pulsation, valve-seat interface | TURBO_AIRFLOW doc; EOS AlSi10Mg card |
| **993-ENG-PISTON-CP1-GALLERY-F0** | Hot CalculiX **187 °C**, material stable to **250–300 °C** (claim) | AHeAD CP1 | LPBF Velo3D Sapphire, 50 µm | **250 °C** (claim; no hot allowable published) | **1.34×** at FEA Tmax | Crown temp, ring-land temp, hot fatigue, hot yield, gallery integrity, oil-jet heat transfer | 993_PISTON_CP1 doc; Constellium card (not fetched) |
| **993-INT-DOOR-OPENER-LEVER-F0** | Interior cabin, ambient to ~80 °C soak | AlSi10Mg (screening) or PA12 | LPBF or SLS | Al: **200 °C**; PA12: **80 °C** | Al passes; PA12 marginal | Real pivot loads, cyclic fatigue, corrosion, trim interface, misuse loads | am-validation-policy; EOS cards |
| **993-INT-SWITCH-TRIM-RING-F1** | Interior cabin, cosmetic | AlSi10Mg (screening) | LPBF | **200 °C** | Passes thermal; fails process | Original material unknown, dimensions synthetic, finish, snap-fit loads, UV aging | am-validation-policy; EOS AlSi10Mg card |

**Note**: all margins are temperature ratios only; stress, fatigue, creep, impact, and vibration margins are not calculated and remain open gates in the repository.

---

## 5. Reviewer-Usable Print-Release Checklist

A part passes the print-release gate **only if every applicable box is checked**. Mark any "unknown" as a blocking item requiring measurement, analysis, or supplier contract.

### 5.1 Thermal and chemical compatibility
- [ ] Service temperature (gas, air, oil, coolant) identified by **measurement or published OEM data**, not synthetic screening alone.
- [ ] Material continuous-use or creep-limited temperature **exceeds measured service temperature by ≥ 1.3×** (aluminum), **≥ 1.5×** (titanium), **≥ 1.4×** (nickel superalloy), or an explicit hot allowable is contracted.
- [ ] Oxidation, hot corrosion, fuel/oil/coolant compatibility confirmed (IN625 is fuel/oil compatible; AlSi10Mg requires coating in raw fuel; PA12 softens in hot oil).
- [ ] Hot-soak or traffic-jam condition checked: sustained post-shutdown temperature can exceed running temperature by 30–50 °C in an air-cooled layout.

### 5.2 Mechanical and geometric integrity
- [ ] Minimum wall thickness **≥ the table in section 3.1** for the selected process, verified by sectioning or CT on a coupon.
- [ ] Tolerance class **ISO 2768-mK or better** (±0.1–0.2 mm) on all mating interfaces, with machining allowance drawn and contracted.
- [ ] Surface roughness on flow paths: **Ra ≤ 6.3 µm** for intake ducts (machined, polished, or coated); **Ra ≤ 12.5 µm** for non-critical exterior; **Ra 1–5 µm** claimed by EOS IN625 datasheet verified by profilometer on witness coupon.
- [ ] No unsupported overhangs > **45°** without a signed support plan from the supplier (EOSPRINT or Velo3D project).
- [ ] All enclosed volumes have a **powder-exit port ≥ 2 mm** (for 63 µm sieve) and CT or borescope proof of evacuation before heat treatment.

### 5.3 Fatigue, creep, and impact
- [ ] Fatigue life assessed with LPBF as-built surface roughness and defect population; **no room-temperature polished-coupon fatigue data substituted for hot, rough, notched service conditions**.
- [ ] For rotating parts (impeller, turbine wheel, piston): overspeed burst, centrifugal loading, HCF, and containment assessed; **no LPBF rotating-part release without a witness-rotor spin test or equivalent**.
- [ ] For exhaust and piston: creep and thermomechanical fatigue assessed with published or contracted hot S-N and creep data; **CalculiX or FEA at room temperature does not release a hot part**.

### 5.4 Interfaces and assembly
- [ ] Machining allowance for every flange, port, bolt face, and press-fit surface is **drawn, dimensioned, and contracted** (typical 0.5–1.0 mm on machined faces).
- [ ] Fastener-insert strategy chosen (integral boss, helical insert, bonded anchor, through-bolt) and **pullout torque tested on a witness coupon of the same lot**.
- [ ] Welding, brazing, adhesive bonding, or sealing to adjacent components (intercooler core, exhaust gasket, oil-line fitting) is **procedure-qualified on coupons**.
- [ ] Gasket, O-ring, and clamp interface geometry matches the OEM part number or the replacement-seal supplier specification (e.g. `999 707 326 40` O-ring 30×3 mm, `999 512 648 02` clamp 60–80/12).

### 5.5 Metrology and first-article inspection
- [ ] Full dimensional CMM scan or CT of the first article against the STEP master, with deviation map and **all critical dimensions within the contracted tolerance**.
- [ ] Internal-passage verification (CT or flow test) for manifolds, galleries, and ducts: **no trapped powder, no support remnants, no necking below nominal**.
- [ ] Dye-penetrant or X-ray inspection for surface-connected porosity or cracks on safety-class parts (exhaust, piston, turbo, oil circuit).
- [ ] Leak test (pneumatic or helium) for pressurized or sealed circuits at 1.5× operating pressure.

### 5.6 Traceability and lot control
- [ ] Powder lot, machine ID, parameter set, build-plate location, witness coupons, heat-treatment furnace run, and post-process batch recorded and linked to the part serial number.
- [ ] Supplier issues a Certificate of Conformance citing **ASTM F3318-18 (AlSi10Mg), ASTM F3055 (IN625), API 6ACRA (IN718), or the contracted polymer specification**, with the exact EOS material set and parameter revision (e.g. AlSi10Mg_FlexM291 2.01, IN625_Performance M291 2.00).
- [ ] Any deviation from the EOS-published process card (layer thickness, platform temperature, heat-treatment cycle, exposure strategy) is **documented, approved by engineering, and correlated to coupon data**.

### 5.7 Explicit exclusions and "do not print" markers
- [ ] **PETG and PLA are not service-credible for any underhood or charge-air application**; do not substitute them for PA12, PEI, or metal based on cost alone.
- [ ] **Ti-6Al-4V is creep-limited to 400 °C**; if the measured or projected service temperature (even a synthetic screening value) exceeds 400 °C, Ti64 is blocked unless a hotter route (Ti-6242, TiAl, or nickel superalloy) is qualified.
- [ ] **AlSi10Mg is not approved above 200 °C** without a hot-yield coupon contract from the supplier; qualitative "stable to 250–300 °C" claims for similar alloys do not release an AlSi10Mg part.
- [ ] **No rotating or pressure-containing part is released on room-temperature coupon data alone**; hot, rough, notched, fatigue, and creep allowables must be contracted or measured.
- [ ] **Simulation alone (CFD, FEA, CalculiX, AdditiveFOAM) never authorizes manufacturing**; the repository policy `METAL-AM-VALIDATION-PIPELINE-0001` and this gate both require physical correlation and signed engineering release.

### 5.8 Repository-policy cross-check
- [ ] All 11 stages in `catalog/manufacturing/am-validation-policy.json` have status **passed** or **not_applicable** with a signed waiver.
- [ ] Stage 04 (material-machine-process card) is closed with the exact machine, parameter set, layer thickness, orientation, support plan, heat treatment, and machining allowance.
- [ ] Stage 07 (recoater and support removal) is closed with a supplier EOSPRINT or Velo3D Flow project, distortion simulation, and recoater clearance validated on the distorted shape.
- [ ] Stage 10 (physical correlation and inspection) is closed with the first-article metrology, CT/NDT, functional test, and simulation-measure correlation report.
- [ ] Stage 11 (engineering release) carries a named, dated sign-off from a qualified engineer, explicitly authorizing **the stated use (static, rotating, hot, pressurized, structural, cosmetic)** on the stated revision.

---

## 6. Citation Index (Public URLs)

1. **EOS Aluminium AlSi10Mg Process Data Sheet (EOS M 290, 30 µm)**: https://www.eos.info/metal-solutions/data-sheets/aluminium/pds-eos-aluminium-alsi10mg-eos-m-290-30um  
2. **EOS NickelAlloy IN625 Material Data Sheet (EOS M 290, 40 µm)**: https://www.eos.info/05-datasheet-images/Assets_MDS_Metal/EOS_NickelAlloy_IN625/Material_DataSheet_EOS_NickelAlloy_IN625_en.pdf  
3. **EOS NickelAlloy IN718 API Process Data Sheet (EOS M 290, 40 µm)**: https://www.eos.info/metal-solutions/data-sheets/nickel-alloys/pds-eos-nickelalloy-in718-api-eos-m-290-40um  
4. **EOS Titanium Ti64 Material Data Sheet (EOS M 290, 30 µm)**: https://3dformtech.fi/wp-content/uploads/2019/11/Ti-Ti64_9011-0014_9011-0039_M290_Material_data_sheet_11-17_en-1.pdf  
5. **Repository AM validation policy**: `origin/main:catalog/manufacturing/am-validation-policy.json`  
6. **Repository turbo airflow data**: `origin/main:docs/TURBO_AIRFLOW_SIMULATION_DATA.md`  
7. **Repository exhaust-manifold dossier**: `origin/main:docs/993/993_EXHAUST_MANIFOLD_IN625_F0.md`  
8. **Repository cooling-fan-system dossier**: `origin/main:docs/993/993_ENGINE_COOLING_FAN_SYSTEM_F0.md`  
9. **Repository piston dossier**: `origin/main:docs/993/993_PISTON_CP1_COOLING_GALLERY_F0.md`  
10. **Repository turbo oil return line dossier**: `origin/main:docs/993/993_TURBO_OIL_RETURN_LINE_IN625_F0.md`  
11. **EOS M 290 machine specification**: https://www.eos.info/metal-solutions/metal-printers/eos-m-290  
12. **Special Metals IN625 technical bulletin (w wrought reference)**: https://www.specialmetals.com/documents/technical-bulletins/inconel/inconel-alloy-625.pdf  
13. **ASTM F3318-18 (LPBF AlSi10Mg specification)**: indexed in repository as `catalog/sources/src-astm-f3318-18.json`; public paywall.  
14. **API 6ACRA (age-hardened nickel alloys for oil/gas)**: cited in EOS IN718 card; public standard.

---

## 7. Summary Verdict

**"3D printable part" in this repository must mean a part that passes all three filters:**

1. **Thermal**: the measured or contractually bounded service temperature is at least **1.3–1.5× below the material's published creep or continuous-use limit**, with hot-soak margin.
2. **Geometric**: the part meets the **minimum-wall, tolerance-class, surface-roughness, powder-removal, and fastener-insert gates** defined in section 3 for its selected process.
3. **Metrological**: the first article is **CT- or CMM-verified, leak-tested, and fatigue/creep-assessed with as-built roughness and defect population**, then signed off under `am-validation-policy.json` stage 11.

**Parts blocked today**: every LPBF part in the tracked list is held at stage 04 or 07 for lack of an EOSPRINT project, hot coupon data, or machined-allowance contract. The IN718 turbine wheel and the IN625 manifold have the clearest thermal path; the AlSi10Mg fan and impeller are blocked by an unknown engine-bay temperature and an unresolved F0 geometric collision; the piston and intake runners are blocked by hot fatigue and real interface data; polymer charge-air ducts are blocked by the lack of a measured post-intercooler temperature below 60 °C.

**PETG and PLA are explicitly not service-credible.** They fail on continuous-use temperature, creep, and aging.
