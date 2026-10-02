# Recent fan-shape research and experiment priorities

Research checked on 2026-09-29. This is a targeted selection, not an exhaustive
systematic review. Published findings concern other machines and are not
performance predictions or manufacturing approval for the Porsche rotor.

## Most useful recent papers

| Publication | Evidence read | Relevance and limitation |
|---|---|---|
| **2026-06-01 — A causality-guided and interpretable sweep–lean optimization framework of axial fan blades for aerodynamic enhancement**, *Energy* 352, 140913. [DOI](https://doi.org/10.1016/j.energy.2026.140913) | Publisher abstract and highlights; full numerical setup not available in this review. | Treat sweep and lean as separate design variables. Do not attribute causality or transfer an optimum from a surrogate without controlled CFD and independent cases. |
| **2026-05-12 — Laser powder bed fusion enabled modular fan blade design for efficient acoustic optimization**, Schultheiß et al., *Progress in Additive Manufacturing*. [Full text](https://link.springer.com/article/10.1007/s40964-026-01661-4) | Full article; physical LPBF manufacture and fan-bench comparison. | Particularly relevant to printed blades: representative interface coupons, support orientation, finishing and balancing matter. Its modular leading edge retained approximately the reference aerodynamic/acoustic performance; it did not demonstrate increased flow from serrations. Its AlSi10Mg/SLM 280HL tolerances and process cannot qualify ZRapid or this rotor. Use coupon methodology, not a bolt-on leading edge on the Porsche prototype. |
| **April 2026 issue — Effects of Blade Solidity and Aspect Ratio on a 0.5 Hub-to-Tip Ratio Tube-Axial Fan**, *Journal of Turbomachinery* 148, 041008. [Author-deposited paper](https://www.research.unipd.it/retrieve/941f9487-4e1c-4815-a87f-5750b870d613/turbo-25-1207.pdf) | Full author-deposited paper; experimental family of 18 printed prototypes. Issue date is not asserted to be its first online publication date. | Separate chord/solidity from blade aspect ratio and tip clearance. This supports controlled chord experiments and later blade-count studies. Our annulus and alternator differ; wider blades cannot be presumed to produce more useful flow. |
| **2026-02-25 — Effects of Hub Geometry on the Aerodynamic and Acoustic Performance of Axial Flow Fans**, Zhang et al., *Applied Sciences* 16, 2227. [Publisher](https://www.mdpi.com/2076-3417/16/5/2227) | Full publisher text; RANS/LES/acoustic predictions, with physical validation identified as future work. | Hub contour changes can improve a low-flow operating region while degrading high-flow operation. Include the real alternator/cup and downstream components before optimising root flow. Do not shrink the cup or assign a favourable hub cone that interferes with the PMB assembly. |
| **2026-01-25 — Multi-objective optimization design of axial flow fan rotor blades and guide vanes based on coordinated radial twist**, Xie et al., *Proceedings IMechE Part C*. [Publisher](https://journals.sagepub.com/doi/10.1177/09544062251415485) | Publisher abstract/metadata. Reported improvements are optimisation-study results; experimental confirmation was not established from the accessible evidence. | Study rotor twist together with stationary flow guidance. NURBS spanwise distributions suggest a later nonlinear twist experiment. Do not copy reported percentages or the authors' optimisation algorithm as proof of benefit. |
| **2026-01-08 — Design and Assessment of Forward-Inclined Blades for a 0.5 Hub-to-Tip Ratio Tube-Axial Fan**, Masi, Danieli and Rech, *Energies* 19, 327. [Publisher](https://www.mdpi.com/1996-1073/19/2/327), [author manuscript](https://www.research.unipd.it/retrieve/73c2f7a9-6248-4814-bc8e-8fc04423368a/2026%20-%20Masi%2CDanieli%2CRech%20-%20Design%20and%20Assessment%20of%20Forward-Inclined%20Blades.pdf) | Publisher summary and author-deposited text; CFD and experimental assessment. | Forward inclination is tied to the actual meridional flow and clearance, rather than decorative curvature. Compare both sweep signs at fixed chord, twist and clearance. |

## Very recent but less directly transferable

- **September 2026 issue:** [Impact of wire mesh casing treatment on compressor rotating instability and stall patterns](https://doi.org/10.1016/j.ast.2026.112685), *Aerospace Science and Technology* 176, 112685. Publisher abstract describes an experimental low-speed compressor study. It motivates checking stability and tip leakage across a pressure–flow curve; it does not justify adding a wire mesh to the Porsche housing.
- **2026-08-31:** [Aerodynamic and Aeroacoustic Effects of Axial Clearance in a Wall-Penetrating Blade Ring Ducted Fan for Unmanned eVTOL Propulsion](https://www.mdpi.com/2226-4310/13/9/786), *Aerospace* 13, 786. The prototype demonstrates architecture operability, not validation of the predicted 5,000 rpm aerodynamic/acoustic results. Its rotating ring would fundamentally change our assembly and loading; retain only the lesson to control and measure leakage paths.

A search also found DOI `10.1016/j.flowmeasinst.2026.103605`, assigned to a
January 2027 issue. Its first-online date was not established here, so it is
not presented as a confirmed publication available by this review date.
Its bionic configurations are explicitly not experimentally validated.

## How the papers change this project

1. **Operating point first.** Compare pressure–flow curves, torque and power at
   matched RPM; a free-discharge flow increase is insufficient. Keep noise,
   off-design stability and blade stress as separate objectives.
2. **Controlled geometry first.** The current 16-case plan changes pitch,
   spanwise twist, camber, sweep and tip chord around E, mostly one variable at
   a time. It holds the nominal diameter, blade count and mounting geometry.
   Rays through the annulus measure projected blockage, never airflow.
3. **Actual assembly matters.** The PMB housing, support vanes, rear cone and
   engine resistance cannot be omitted from an installed-performance claim.
   Clearance experiments remain numerical sensitivity studies until tolerances,
   thermal growth, bearing play and centrifugal deflection are bounded.
4. **Then more complex shapes.** Nonlinear twist, independent lean, edge
   undulations and serrations are later candidates. They add mesh and
   manufacturing demands and may reduce noise without improving flow.
5. **PhysicsNeMo needs trustworthy data.** Use its mesh/field audits now.
   Train a surrogate only after accepted CFD cases span the parameters and
   held-out validation exists. Do not train on rejected or unconverged results.
6. **Manufacturing experiments must preserve provenance.** For every valid
   geometry and material/process combination report mass from volume and
   density, layer height, sampled wall thickness, support estimate and what
   thermal/mechanical simulation actually ran. Physical tolerances, fatigue,
   porosity, polymer interlayer strength and balancing require real tests.

## Current numerical gate

The first stricter E mesh eliminates the reported concave face angles but
still fails the extended check because of concave cells. The solver is now
stopped on that failure. There is no new accepted CFD result or demonstrated
increase in airflow from this campaign at this stage.
