# Reinforced carrier: current numerical checkpoint

The **d64a7faf** native master has an adaptive volume of **288,415.83655452315 mm³** and a dense reference mass of **1.274797998 kg**. The four smooth rib additions use **6.96 g**, leaving **25.20 g** below the **1.30 kg** limit.

See the [actual CAD surface comparison](../../media/carrier-rib-actual-surfaces-20261018/README.md), [reinforcement construction drawing](../../media/carrier-rib-C2-20261018/README.md) and [nominal interface sheet](../../media/carrier-nominal-interfaces-20261018/README.md).

The [editable handover](../../../parts/993-eng-carrier-0001/source/design-20261016/stock-rib-C2-candidate-20261018/README.md) contains the actual BREP, STEP and STL, construction sources, parameters and tested local reconstruction commands. Both original BREP byte identities were reproduced in a fresh run. The [copy review](handover-copy-root-review.json) verifies all 65 copied payloads and the final 66-file path set.

## Geometry and mesh

The current native body is one valid solid. Its fresh 597,720-triangle STL passes whole topology and intersection checks; the sampled two-way distances are **0.015438140 / 0.047388128 mm**, below the retained **0.06 mm** screen. All eight complete protected-interface probe rosters and the original assembly predicate pass.

The [STEP review](STEP-root-review.json) records two valid, empty strict native differences in all dimensions. The STEP adaptive relative volume difference is **5.980736573 × 10⁻⁹**, below **10⁻⁸**. The [volume-mesh review](mesh-root-review.json) records **159,612 nodes and 85,767 C3D10 tetrahedra**, minimum sampled Jacobian **0.008331803**, exact same-operator CAD import volume agreement, and all six actual bore-node rosters. Native BREP remains the master.

## Two actual mechanical cases

Both cases use **Fz = −4,000 N**, **My = 850 N·m**, **E = 107,000 MPa** and **ν = 0.31**. K1000 applies **1,000 N/mm total per eye and axis**, distributed over that eye's nodes.

| Case | Previous stock peak | Current rib peak | Peak reduction | Current maximum displacement | Relative energy error |
| --- | ---: | ---: | ---: | ---: | ---: |
| Rigid eyes | 621.141462 MPa | 600.659493 MPa | 3.30% | 2.709626 mm | 1.70 × 10⁻⁹ |
| K1000 eyes | 1,633.128570 MPa | 1,548.151984 MPa | 5.20% | 16.478757 mm | 1.56 × 10⁻⁸ |

Both independent energy checks pass the original **10⁻⁴** limit. The [complete mechanical review](mechanics-root-review.json) retains every global maximum, the corresponding element and integration point, current CAD identity, tool return codes and cleanup checks. The full [rigid](rigid-energy-audit.json) and [spring](spring-energy-audit.json) energy reports are exact copies of the executed records.

The [complete stress-distribution image](../../media/carrier-stress-distribution-20261018/README.md) plots all **686,136 integration-point rows** across the two cases, with a common scale and every global maximum retained.

The current peaks moved away from the former rib hotspot:

| Case | Element / integration point | Undeformed peak coordinates (mm) | Measured corner-edge maximum | Proposed local size |
| --- | --- | --- | ---: | ---: |
| Rigid | 35,381 / 2 | (264.015209, 21.485040, −11.310000) | 2.768883 mm | 1.384442 mm |
| K1000 | 81,008 / 3 | (83.308756, −15.653915, 13.526061) | 1.906371 mm | 0.953186 mm |

These are initial mesh results. Stress convergence and adequate strength are still open. The size proposal halves each measured corner-edge maximum. Earlier stock Figure 33 shows the preceding geometry's fields.

## Current junction observations and refinement

The [actual section image](../../media/carrier-current-thin-junction-20261018/README.md) shows the current spring-case peak inside a thin wedge between the arm arch and a window wall. Its nearest-face native normal chord is **0.317968484 mm**, from current face 120 to face 164. A reverse chord at a different nearby point is **0.300345471 mm**. The adjacent rib observation is **2.188382396 mm**. These are separate local measurements, not a global minimum thickness or an established stress singularity.

The [observation review](hotspots-root-review.json) closes both actual five-probe native runs. Their [complete compact summary](hotspots-observed-summary.json) retains every reported nearest-face and edge observation, qualified chord and null count. Both complete face/edge distance rosters remain in the original records.

The first [local refinement](local-refinement-refusal-root-review.json) measured **2.360754878 / 1.351859995 mm**, above the unchanged **1.384441618 / 0.953185689 mm** targets. It also changed the end1 bore coordinates: **2,145 of 2,274** nodes had no unique match within the original **10⁻¹⁰ mm** bound. That mesh was refused and was not solved.

A subsequent [frozen-bore attempt](frozen-bore-refusal-root-review.json) recovered all six original T6 bore meshes from the complete current T10 boundary. No fixed bore edge conflicted with the two local targets. Native 1D generation completed, but a curve-parameter ambiguity stopped installation before any protected curve was cleared or injected. Its refusal remains unchanged.

The [independent parameter observer](curve-parameter-observer-root-review.json) then checked all 18 protected curves. The `getClosestPoint` parameter guards failed; the separate `getParametrization` → `getValue` route passed the original domain, uniqueness and **10⁻¹⁰ mm** roundtrip guards on every curve, with maximum error **2.8422 × 10⁻¹⁴ mm**. The [next attempt](raw-preservation-gap-root-review.json) completed installation and native volume generation but refused repeated node-tag enumeration before its mesh writer ran. Its unavailable final arrays remain unknown.

The [raw-preserving refinement](frozen-bore-T6-refinement-refusal-root-review.json) saves the complete mesh before verification. All six original bore coordinate bijections and full T6 connectivity proofs now pass, with zero coordinate mismatch. Repeated rows combine only when the same native tag has identical binary64 XYZ; all raw rows and multiplicities remain retained. The mesh has **161,547 nodes / 86,820 T10 elements**, positive sampled Jacobians and exact same-operator CAD import agreement.

This refinement still refuses the original volume-error nonregression guard: **−0.000242000454338** versus the coarse **−0.000232811681518**. Its measured local maxima are **1.559827077 / 1.015801710 mm**, above the unchanged **1.384441618 / 0.953185689 mm** targets. No refined mechanical case was solved. The original coordinate, connectivity, volume and actual edge-size gates remain in force.

The [saved-boundary volume study](boundary-volume-attribution-root-review.json) independently recomputes both complete encoded corner meshes with dyadic integer arithmetic. The exact corner-boundary change is **−2.650187600 mm³**; the original Gmsh T10 volume observations differ by **−2.650187600 mm³**, with a separate operator-delta residual of **4.27 × 10⁻¹¹ mm³**. The changed saved boundary accounts for this volume difference beyond summation roundoff. Exact corner-polytope arithmetic remains distinct from the full quadratic T10 operator and does not qualify the rejected mesh.

Every edge-to-midside association was checked. All stored binary64 midpoint expressions match; most are not exact rational midpoints, with maximum rational deviation **2.8422 × 10⁻¹⁴ mm**. Complete unchanged-face cancellation and all unmatched boundary contributions are retained. Only the latest mesh has captured native face identities; the coarse mesh's native face IDs remain unknown. The next method reuses the existing adaptive discrete refinement of the admitted coarse mesh, retaining original coordinates, protected facets and all numerical gates.

## R1 junction trial — separate candidate

A [new seven-edge junction trial](R1-junction-trial-root-review.json) produced native BREP **240109ca**, one valid solid with **243 faces** and no degenerate edges. A single declared **1 mm** fillet follows the complete actual reentrant contour; all seven source-profile, finite normal and material-side checks precede the native build.

The strict **d64 minus trial** native difference is valid and empty in all dimensions. The reverse difference is one valid positive solid, with **36.049512 mm³** measured volume. The separate whole-body adaptive volume difference is **36.055640 mm³**; these two observations are retained separately. The trial mass is **1.274957364 kg**, leaving **25.04 g** below the ceiling, and the original overall bounds pass.

The [fresh body inspection](R1-body-volume-root-review.json) confirms one valid Solid and one shell, **243 faces / 738 edges / 488 vertices**, and zero degenerate edges. It observes all three original volume overloads on the same native Solid. F/F/F and T/F/F each return **288,451.89106919506 mm³**; the separate adaptive result is **288,451.89219496236 mm³**, exactly matching the construction trial's binary64 observation.

All [four actual tool-column Commons](R1-four-tool-columns-root-review.json) completed and returned valid, entirely empty results in all dimensions. They use the original **12.5 mm radius**, centres **(±50, ±20) mm** and **Z = 4–44 mm**. Each operation imports the candidate afresh and preserves its raw result before evaluating the predicates.

The [fresh surface generation](R1-surface-generation-root-review.json) produced a **651,012-triangle** STL, SHA-256 **88c405af…**, with the original Gmsh recipe. The [whole-native and sampled forward audit](R1-forward-surface-root-review.json) passes its original **0.06 mm** screen: maximum **0.021524182 mm** across **3,072 STL probes**. It retains **8,430 trimmed CAD sample points** for the separate inverse check. Full topology/intersections, inverse distance and protected-interface audits remain subsequent stages. The [actual before/after image and X50 foot section](../../media/carrier-R1-actual-surfaces-20261018/README.md) show the new rounded junction with English labels. STEP exchange and mechanics also follow this candidate. The d64 mechanical results and existing section/stress images remain attached to d64; they do not establish the new trial's stress response.

## Evidence scope

[Provenance](provenance.json) maps every copied record to its actual source and hash. This compact folder contains the complete records listed there. Full native fields, owner collections, solver binaries and runtime maps remain at the retained local paths recorded in those reports; this folder does not claim a self-contained solver replay.

Process preparation must follow the selected geometry. The seven-region, 1,034-layer native-envelope experiments still refer to the preceding stock body; they are not transferred to d64. The [repaired stock source-2 report](../carrier-source2-repair-20261018/README.md) records an actual RC0 seal under a separate V3 finite-distance contract. All 22 affected final faces remain explicitly unknown; old strict-12 acceptance, continuous coverage and process-anchor admission remain false. Supports, full layer vectors and a machine job remain subsequent stages.
