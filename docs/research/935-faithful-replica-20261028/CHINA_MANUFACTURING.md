# Chinese manufacturing candidates and required data

Research date: 28 October 2026. No supplier has accepted the part, quoted the work
or supplied a complete process dataset. No message or scan has been sent. Capabilities
below are supplier declarations, not qualification of this cylinder head.

| Candidate | Public evidence | Missing for this part | Assessment |
|---|---|---|---|
| Falcontech, Wuxi | Simulation, powder, SLM, HIP, machining and testing; process development with Farsoon | Selected machine/alloy, hot-property curves, actual parameters, coupons, CT criteria and data-sharing terms | First enquiry candidate; not selected for manufacture |
| Farsoon, Changsha | Adjustable laser/path/layer/temperature parameters and process logging; AlSi10Mg datasheet | Accessible machine settings do not guarantee delivery of data to a customer or properties of a batch; calibration and curves absent | Potential process partner; distinguish equipment maker from service provider |
| BLT, Xi'an | Model assessment, printing, post-processing, machining and testing; AlSi10Mg/AlSi7Mg catalogue | Same material/process/calibration package required; no identified RR350 head qualification | Alternative to compare on data completeness |

## Primary sources

- [Falcontech capabilities and validation approach](https://falcontech.com.cn/en).
- [Falcontech–Farsoon collaboration](https://www.farsoon-gl.com/alcggs/falcontech-a-journey-from-material-engineering-to-large-scale-metal-additive-manufacturing/): historical development work, not a current data-sharing commitment.
- [Farsoon software and parameters](https://www.farsoon-gl.com/software/).
- [Farsoon AlSi10Mg](https://www.farsoon-gl.com/jhwcl/fs-alsi10mg/): declared density 2.65 g/cm³; heat-treated tensile strength ≥300 MPa, yield strength ≥180 MPa and elongation ≥7%. Temperature curves, orientation and exact treatment needed for our analyses are not provided on that page.
- [BLT engine solutions](https://www.xa-blt.com/%E5%8F%91%E5%8A%A8%E6%9C%BA/).
- [BLT powders and tests](https://www.xa-blt.com/products/powders/).
- [Xtreme programmes](https://www.xtremecylinderheads.com/programs): current families advertised as RR350 lost-wax castings with HIP. The scanned specimen's alloy is still unknown; no automatic equivalence to AlSi10Mg is admitted.

## Required data matrix

| Package | Traceable information required | Current admission |
|---|---|---|
| Material identity | Alloy, powder chemistry/lot/reuse, particle distribution, exact treatments | Not received |
| Thermal properties | Density, conductivity, heat capacity and expansion against temperature; solidus/liquidus and latent heat for process modelling | Not received |
| Mechanical properties | E, ν, temperature-dependent plasticity, XY/Z anisotropy, fatigue, creep and ageing in the intended duty envelope | Not received |
| Machine | Model/configuration, calibration, laser/spot, layers, preheat, atmosphere, plate and fixtures | Not received |
| Build definition | Orientation, supports, machining stock, power/speed/hatch, scan order, layer timing and usable exports | Not received |
| Adamantine calibration | Coupons, temperature histories, distortion before/after release, calibrated heat-source model and uncertainties | Not received |
| Finished part | Depowdering, machining, treatment/HIP, CT/NDT, roughness, dimensional checks, leak tests and acceptance criteria | Not received |
| Engine operation | Donor loads and reference flow/thermal/mechanical measurements | Required from owner/engine manufacturer; an AM vendor cannot replace them |

Generic published properties may support explicitly hypothetical sensitivity studies.
They are not admitted as properties of this specimen. Missing values remain missing;
a language-model response cannot fill them authoritatively.

## Ready-to-review enquiry — not sent

Proposed business recipients from official sites:
`info@falcontech.com.cn`; `sales.global@xa-blt.com`.

**Subject: Technical feasibility and simulation-data request — faithful aluminium engine cylinder-head replica**

We are assessing a geometrically faithful replica of an existing aluminium
engine cylinder head. We have an external scan, but physical scale, hidden
geometry, original alloy and operating loads are not yet fully established.
The manufacturer's catalogue mentions cast RR350 with HIP; this is not a
confirmed identification of our specimen. Please do not assume AlSi10Mg is
an equivalent replacement.

Before transferring geometry or placing an order, please confirm:

1. Whether you can support a one-off engineering prototype, its expected
   manufacturing route, and the evidence needed to select a suitable alloy.
2. Whether you can provide temperature-dependent thermal and mechanical data,
   XY/Z properties, heat-treatment details, fatigue/creep data where applicable,
   test methods, uncertainties and powder-lot traceability.
3. Whether the actual machine configuration, build orientation, supports,
   scan strategy, laser settings, layer timing, preheat and boundary conditions
   can be supplied in an agreed format for independent process simulation.
4. Whether calibration coupons, measured distortion and thermal histories can
   be supplied, including the removal of supports and release from the plate.
5. Your proposed machining, cleaning, heat treatment/HIP, CT/NDT, dimensional
   inspection and leak-test route, with proposed acceptance criteria.
6. Which data are public, available under NDA, unavailable or require paid
   testing; please separate existing evidence from proposed development.

Our intended simulation tools include Gmsh, OpenFOAM, CalculiX and Adamantine.
We need traceable process data rather than a claim that a generic material
datasheet validates this component. Please identify your technical contact,
data-sharing conditions, indicative engineering lead time and cost categories.

This is a feasibility enquiry, not a manufacturing order. No geometry is attached.
