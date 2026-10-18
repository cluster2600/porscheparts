# Reinforced carrier: current numerical checkpoint

Latest design work: [reinforcing the window root](#reinforcing-the-window-root--new-24af-design-trial). The **24af** design trial now has closed native construction, sampled surface/topology checks, complete protected-interface comparison and a native reference section. Its volume mesh, STEP exchange and mechanics remain pending; the completed d64 study and separate R1 mechanical results retain their own identities below.

The **d64a7faf** native master has an adaptive volume of **288,415.83655452315 mm³** and a dense reference mass of **1.274797998 kg**. The four smooth rib additions use **6.96 g**, leaving **25.20 g** below the **1.30 kg** limit.

See the [actual CAD surface comparison](../../media/carrier-rib-actual-surfaces-20261018/README.md), [reinforcement construction drawing](../../media/carrier-rib-C2-20261018/README.md) and [nominal interface sheet](../../media/carrier-nominal-interfaces-20261018/README.md).

The [editable handover](../../../parts/993-eng-carrier-0001/source/design-20261016/stock-rib-C2-candidate-20261018/README.md) contains the actual BREP, STEP and STL, construction sources, parameters and tested local reconstruction commands. Both original BREP byte identities were reproduced in a fresh run. The [copy review](handover-copy-root-review.json) verifies all 65 copied payloads and the final 66-file path set.

## Geometry and mesh

The current native body is one valid solid. Its fresh 597,720-triangle STL passes whole topology and intersection checks; the sampled two-way distances are **0.015438140 / 0.047388128 mm**, below the retained **0.06 mm** screen. All eight complete protected-interface probe rosters and the original assembly predicate pass.

The [STEP review](STEP-root-review.json) records two valid, empty strict native differences in all dimensions. The STEP adaptive relative volume difference is **5.980736573 × 10⁻⁹**, below **10⁻⁸**. The [volume-mesh review](mesh-root-review.json) records **159,612 nodes and 85,767 C3D10 tetrahedra**, minimum sampled Jacobian **0.008331803**, exact same-operator CAD import volume agreement, and all six actual bore-node rosters. Native BREP remains the master.

## Two coarse mechanical cases

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

Every edge-to-midside association was checked. All stored binary64 midpoint expressions match; most are not exact rational midpoints, with maximum rational deviation **2.8422 × 10⁻¹⁴ mm**. Complete unchanged-face cancellation and all unmatched boundary contributions are retained. Only this native refinement has captured native face identities; the coarse mesh's native face IDs remain unknown.

A separate adaptive discrete refinement of the admitted coarse mesh completed three passes, producing **161,826 nodes / 87,256 T10 elements**. All original node IDs, NPZ coordinate bytes, serialized NODE lines, six bore rosters, protected corner facets and protected midside IDs remain unchanged. Its original comparison against generated coarse metadata refused a volume difference of about **3 × 10⁻¹⁰ mm³** before the final edge-size test; that refusal remains unchanged.

The [saved-mesh diagnostic](same-operator-H2-root-review.json) applies the same retained Gmsh operator and element order to both serialized INPs. Both observed volumes are exactly **288,348.6899786381 mm³**, binary64 hex **41119972c289c296**, with exact observed difference **0**. It also independently recomputes both complete original edge-size measurements: **1.384441617742 / 0.953185688956 mm**, at most the original **1.384441617746 / 0.953185688957 mm** targets. This distinct, zero-tolerance serialized-reference contract passes. It does not rewrite the earlier generated-metadata result.

### Actual mechanical cases on the saved refinement

The [two refined cases](refined-mechanics-root-review.json) use the same d64 CAD, loads, material assumptions, original coordinates and protected mesh entities. All serialized force, moment, rigid-support and spring-stiffness cards were checked before solving. Both actual solvers completed and passed the unchanged independent energy test.

| Case | Coarse peak | Refined peak | Refined/coarse peak ratio | Refined maximum displacement | Relative energy error |
| --- | ---: | ---: | ---: | ---: | ---: |
| Rigid eyes | 600.659493 MPa | 925.772793 MPa | 1.541261 | 2.710864 mm | 6.02 × 10⁻⁹ |
| K1000 eyes | 1,548.151984 MPa | 2,740.902001 MPa | 1.770435 | 16.482678 mm | 8.57 × 10⁻⁹ |

Both global peaks occur at **element 85,784 / integration point 2**, undeformed coordinates **(83.421659, −15.366811, 13.685695) mm**, with a measured corner-edge maximum of **0.701533164 mm**. Every global maximum and tie remains retained. Maximum displacements change by only **0.0457% / 0.0238%**, while the peaks increase by **54.13% / 77.04%**. This demonstrates strong local stress sensitivity to refinement; it supplies no converged stress or adequate-strength conclusion. The complete [rigid](refined-rigid-energy-audit.json) and [spring](refined-spring-energy-audit.json) energy records and all 64 output identities are retained. The R1 geometric correction is evaluated separately below.

The [actual coarse/refined field image](../../media/carrier-d64-coarse-refined-20261018/README.md) compares all four completed d64 cases with a common camera, common field scales and true deformation ×1. It retains all integration-point rows and every global maximum; it does not establish convergence or transfer d64 results to R1.

## R1 junction trial — separate candidate

A [new seven-edge junction trial](R1-junction-trial-root-review.json) produced native BREP **240109ca**, one valid solid with **243 faces** and no degenerate edges. A single declared **1 mm** fillet follows the complete actual reentrant contour; all seven source-profile, finite normal and material-side checks precede the native build.

The strict **d64 minus trial** native difference is valid and empty in all dimensions. The reverse difference is one valid positive solid, with **36.049512 mm³** measured volume. The separate whole-body adaptive volume difference is **36.055640 mm³**; these two observations are retained separately. The trial mass is **1.274957364 kg**, leaving **25.04 g** below the ceiling, and the original overall bounds pass.

The [fresh body inspection](R1-body-volume-root-review.json) confirms one valid Solid and one shell, **243 faces / 738 edges / 488 vertices**, and zero degenerate edges. It observes all three original volume overloads on the same native Solid. F/F/F and T/F/F each return **288,451.89106919506 mm³**; the separate adaptive result is **288,451.89219496236 mm³**, exactly matching the construction trial's binary64 observation.

All [four actual tool-column Commons](R1-four-tool-columns-root-review.json) completed and returned valid, entirely empty results in all dimensions. They use the original **12.5 mm radius**, centres **(±50, ±20) mm** and **Z = 4–44 mm**. Each operation imports the candidate afresh and preserves its raw result before evaluating the predicates.

The [fresh surface generation](R1-surface-generation-root-review.json) produced a **651,012-triangle** STL, SHA-256 **88c405af…**, with the original Gmsh recipe. The [whole-native and sampled forward audit](R1-forward-surface-root-review.json) measures **0.021524182 mm** across **3,072 STL probes**. The [complete joint surface audit](R1-joint-surface-root-review.json) measures **0.047388128 mm** from all **8,430 trimmed CAD sample points** to the STL. Both sampled directions pass the unchanged **0.06 mm** screen. All triangles participate in topology and intersection checks: one positive-volume component, zero open/nonmanifold/orientation edges, zero degenerate or needle triangles, and zero self-intersection pairs. Relative mesh volume error is **2.7481 × 10⁻⁵**, below **0.002**; maximum bounds error is **1.052 × 10⁻⁷ mm**, below **0.06 mm**. These sampled distances remain distinct from a continuous fidelity bound.

The [complete protected comparison](R1-protected-root-review.json) passes all original study-interface checks for this actual R1 BREP and STL. All **eight complete 3,264-point rosters** contain zero hits, with **1,632 saved chunk hashes** and no random fallback. The whole original assembly predicate passes. The central-pad and all six end-interface symmetric-difference volume observations are zero, as is the whole-pair mesh intersection volume. These retain the original ROI volume predicates and finite-probe scope; the strict native Cut and tool Commons remain separate records.

The [actual before/after image and X50 foot section](../../media/carrier-R1-actual-surfaces-20261018/README.md) show the new rounded junction with English labels. Its footer records the pending audit status at image creation; subsequent audits are linked above.

The [actual default STEP exchange](R1-STEP-refusal-root-review.json) returns RC1. Its adaptive relative volume difference is **7.190185336 × 10⁻⁹**, within the original **10⁻⁸** guard, and the writer settings are restored. Both fresh strict native differences nevertheless return **invalid, nonempty compounds**, each with one Solid and zero signed solid volume. Their complete raw results are retained. The forward difference has **243 faces / 741 edges / 490 vertices**; the reverse has **243 / 742 / 490**. This does not establish physical erosion or addition, and the exchange is not accepted. Native BREP remains the trial's master.

The independent [fresh native-BREP mesh](R1-mesh-root-review.json) completes with **166,361 nodes / 89,689 C3D10 elements**. All sampled Jacobians are finite and positive, with minimum **0.008331803**. Gmsh observes **288,451.8910691951 mm³**, compared with the corresponding native F/F/F value **288,451.89106919506 mm³**; the relative difference **2.22 × 10⁻¹⁶** passes the unchanged import guard. The distinct mesh volume is **288,388.7266472701 mm³**, relative error **−0.000218981221484** against the adaptive native volume. All six complete actual node rosters are checked: **528** per central bore and **2,274** per end eye. Their comparison with the earlier EF7 reference does not claim identical rosters. The mesh uses the native BREP directly and has no STEP dependency.

The [two actual R1 geometry observations](R1-reference-geometry-root-review.json) query this new body at the two closed d64 reference peaks and their four corner probes. Every probe retains all **243 face / 738 edge distances**, native D2 properties, normal-line hits and unresolved qualifiers. The [complete local summary](R1-reference-geometry-observations.md) and [machine-readable observations](R1-reference-geometry-summary.json) include every retained nearest support and qualified chord. At the refined d64 reference point, a qualified R1 local normal chord measures **0.230562407 mm** between fresh R1 faces 62 and 60; corner 0 measures **0.018991912 mm** between those supports. A locally thin region therefore remains at these probes. These are separate local geometric measurements, with no global minimum-thickness or R1 stress conclusion. The summary's pending-ROOT sentence records its creation time; the linked ROOT review subsequently closes both actual jobs.

### Actual R1 coarse mechanical cases

The [two completed R1 cases](R1-mechanics-root-review.json) use this fresh **166,361-node / 89,689-T10** mesh and the original **Fz = −4,000 N**, **My = 850 N·m**, **E = 107,000 MPa**, **ν = 0.31** and K1000 total-per-eye-and-axis contract. Whole serialized coordinates, load resultants and support cards were checked before solving. Both actual solvers returned RC0; their containers were removed and fresh absence checks passed.

| Case | Global integration-point peak | Maximum displacement | Relative energy error |
| --- | ---: | ---: | ---: |
| Rigid eyes | 735.976996 MPa | 2.707886 mm | 1.74 × 10⁻⁹ |
| K1000 eyes | 2,095.883175 MPa | 16.423858 mm | 1.32 × 10⁻⁸ |

The complete [rigid](R1-rigid-energy-audit.json) and [spring](R1-spring-energy-audit.json) energy audits pass the unchanged **10⁻⁴** criterion. The ROOT review verifies all **62 output files**, actual native plans, solver identity, every global maximum and all current input identities.

Both sole maxima occur at **element 83,728 / integration point 1**, undeformed coordinates **(83.397174, −15.380329, 13.889129) mm**. Its measured maximum corner edge is **0.939982012 mm**, giving the proposed original H/2 target **0.469991006 mm**. Both roles identify the same measured site. This point is distinct from the older d64 reference locations used for the preceding R1 geometric observations; its actual native observations and section are recorded below.

R1 and d64 use different CAD and independently generated coarse meshes, so changes in their maxima include geometry and discretisation effects. R1 stress convergence and adequate strength remain open. The d64 field images retain their original identities. The separate R1 refinement and its original refusal are recorded below.

### Actual R1 peak geometry and saved refinement

The [fresh own-peak observation](R1-own-peak-geometry-root-review.json) queries the actual R1 body at its own common peak and all four corner probes. Every probe retains all **243 face / 738 edge distances**. The [complete observations](R1-own-peak-geometry-observations.md) and [machine-readable summary](R1-own-peak-geometry-summary.json) preserve all **10 qualified chords and 32 unresolved nearest-support rows**.

At the integration point, the nearest B-spline support has a qualified **0.085913084 mm** normal chord to a planar support. A reciprocal support chord is **0.067453672 mm**. Their fresh shared edge has native C0 continuity, lies **0.092581044 mm** from the peak and has a reported outward-normal angle of **137.055729°**. These are local support/normal observations near an edge, not a global minimum wall thickness, material-side classification or established stress singularity. The summary's pending-ROOT sentence is its frozen creation-time status; the linked review closes the actual job.

The [separate exact section](R1-own-peak-section-root-review.json) retains the complete native BREP intersection and all **41 curves / 1,833 sampled positions** at **X = 83.39717404347466 mm**. It uses the original **0.001 mm** drawing deflection. Maximum observed plane residual is **4.2633 × 10⁻¹⁴ mm**, below the section's native edge tolerance. Raw native curves are saved before sampling, and complete sampled data before their checks. A normal chord in three dimensions is distinct from this plane section; a YZ projection must be labelled as such. The [actual native section image](../../media/carrier-R1-own-peak-section-20261018/README.md) retains the whole outline and uses the actual peak-element bounds for the detail, with projected endpoints and 3D lengths labelled.

The [R1 discrete refinement](R1-discrete-volume-refusal-root-review.json) actually completed **four passes**, saving **167,765 nodes / 90,628 T10 elements**. All original NPZ coordinate bytes, serialized NODE lines, node IDs, six complete bore rosters, protected corner facets and their edge-to-midside associations remain unchanged. The original generated-volume nonregression gate then refuses **288,388.7266472696 mm³**, compared with the generated reference **288,388.7266472701 mm³**. Its relative errors are **−0.00021898122148578114 / −0.00021898122148422683**. Within that original refused stage, the final full H/2 measurement is not reached and no refined mechanical case is started.

The complete refusal remains unchanged. The [distinct saved-mesh diagnostic](R1-saved-operator-H2-root-review.json) subsequently reads both saved INPs with the same Gmsh operator. Its [complete volume comparison](R1-saved-operator-volume-comparison.json) observes **288,388.7266472696 mm³** for each serialized mesh, with **zero exact binary64 difference**. Both complete original region-edge measurements ([rigid](R1-saved-H2-measurement-0.json), [spring](R1-saved-H2-measurement-1.json)) return **0.4699910057556872 mm**, below the unchanged **0.4699910057558742 mm** H/2 target. This separate diagnostic retains the original coordinates, NODE lexemes, six complete bore rosters and protected facets/midsides. It does not replace the original generated-reference comparison or adopt a new master.

### Actual R1 mechanics on the saved refinement

The [two completed refined R1 cases](R1-refined-mechanics-root-review.json) use the saved **167,765-node / 90,628-T10** mesh. Whole serialized coordinates, all loads and support cards were checked again. Material, load and K1000 definitions are unchanged from the coarse R1 cases.

| Case | Coarse peak | Refined peak | Refined/coarse peak | Refined maximum displacement | Relative energy error |
| --- | ---: | ---: | ---: | ---: | ---: |
| Rigid eyes | 735.976996 MPa | 842.642887 MPa | 1.144931 | 2.708498 mm | 5.13 × 10⁻⁹ |
| K1000 eyes | 2,095.883175 MPa | 2,435.105337 MPa | 1.161852 | 16.427288 mm | 5.85 × 10⁻¹⁰ |

Both complete [rigid](R1-refined-rigid-energy-audit.json) and [spring](R1-refined-spring-energy-audit.json) energy audits pass the original **10⁻⁴** limit. The ROOT review verifies all **64 output files**, native resources, solver identity and cleanup. Complete [rigid](R1-refined-rigid-assessment.json) and [spring](R1-refined-spring-assessment.json) assessments retain every global maximum and same-R1 coarse comparison.

Both sole global peaks occur at **element 89,936 / integration point 2**, undeformed coordinates **(83.42304294902544, −15.452886912386544, 13.911696709557964) mm**. Its measured maximum corner edge is **0.385433557 mm**. Peak stresses rise **14.49% / 16.19%** while maximum displacements change **0.0226% / 0.0209%**. This remaining mesh sensitivity supplies no converged-stress or adequate-strength conclusion. No peak is excluded. These are two context cases, not the complete declared ten load cases under both support conditions.

## Reinforcing the window root — new 24af design trial

The editable change moves only the first main-window corner A along its original AB edge: **+1.5 mm in scaled X and +0.110294118 mm in Y**, mirrored across X. B and C stay fixed. Both targeted window branches change; the other **ten window branches** and four rib rails remain unchanged. The [effective override](corner-slide-effective-trial.json) is authoritative; copied nominal construction plans remain historical snapshots.

The [actual construction review](corner-slide-construction-root-review.json) closes native BREP **24af0584** as one valid solid. The [strict original-baseline difference](corner-slide-baseline-minus-candidate.json) and [strict d64 difference](corner-slide-d64-minus-candidate.json) are valid and empty in all dimensions. The new design deliberately omits the separate R1 fillet; the [R1-minus-candidate result](corner-slide-R1-minus-candidate.json) retains that nonempty difference rather than claiming R1 containment. All [four tool-column predicates](corner-slide-four-tool-predicates.json) pass with zero positive solid intersection; any boundary contact must lie on the recorded exact pad support.

The [fresh native-body review](corner-slide-body-root-review.json) records **one Solid / one shell, 236 faces / 725 edges / 482 vertices**, with zero degenerate edges. The [three same-Solid volume observations](corner-slide-three-volume-observations.json) keep **288,685.9375234367 mm³** F/F/F separate from **288,685.89908443496 mm³** adaptive volume. The [actual local measurements](corner-slide-local-measurements.json) give nominal mass **1.2759916739532025 kg** at **4,420 kg/m³**, leaving **24.01 g** below **1.30 kg**; bounds pass. This is **1.194 g** above d64.

The [dedicated surface generation](corner-slide-surface-generation-root-review.json) produces the fresh **598,372-triangle** STL, SHA-256 **b4026f66…**. The [actual before/after illustration](../../media/carrier-corner-slide-actual-surfaces-20261018/README.md) shows this complete STL beside d64, with common camera, scale and a shared prior-R1 reference X plane. All tessellated section segments are computed before the display crop; full profile counts and coordinate hashes are retained. It contains no new mechanical field or sampled native section. The [forward review](corner-slide-forward-root-review.json) and [joint surface review](corner-slide-joint-root-review.json) now pass the original sampled two-way distance, whole topology and intersection gates for this STL and native master. The mesh has **299,144 vertices**, one positive connected component, and zero boundary, nonmanifold, inconsistent-orientation, degenerate or needle elements; no self-intersection pairs are reported. The [full joint audit](corner-slide-joint-audit.json) retains **3,072 STL samples / 8,159 trimmed CAD samples**, maximum distances **0.014916915793648703 / 0.047388128068578256 mm**, below **0.06 mm**. Its relative surface-mesh volume error is **1.810974999 × 10⁻⁵**, below **0.002**. These sampled distances are not a continuous surface-distance bound.

The [complete protected-interface review](corner-slide-protected-root-review.json) also passes for this 24af BREP and its fresh STL. All **eight × 3,264** original boolean probe rows are false, across **1,632** recorded chunks with zero random fallback. The original study assembly predicate passes: central-pad, six end-interface and whole-pair overlap differences are zero. The [full inspection](corner-slide-protected-inspection.json), [probe/chunk record](corner-slide-protected-contains-chunks.json) and complete owner/assessment records retain the nominal comparison and original **1.20 kg** flag as false alongside the authorized **1.30 kg** mass check as true. These are model-interface checks, not physical fitment or manufacturing approval.

Volume meshing, mechanical cases and STEP exchange remain pending for this design. Its eventual mechanical study must cover all **ten declared load cases under both support conditions**. Earlier d64/R1 results do not complete those stages.

The [new native observation](corner-slide-prior-R1-reference-root-review.json) queries 24af at the **prior R1 coarse reference** (83.39717404347466, −15.380328571289892, 13.889129384939432) mm and its four retained corner probes. This is not a stress peak calculated for 24af. At the reference point, fresh 24af support directions give three local normal chords: **5.959720525 mm (120→169)**, **2.188732128 mm (163→169)** and **2.188715195 mm (169→163)**. These distinct directions are not a global thickness or strength measurement, and their face indices belong only to this query body. The [complete assessment](corner-slide-prior-R1-reference-assessment.json) and ROOT review retain all **ten qualified chords / thirty unresolved nearest-support rows**, complete five-probe distances and raw ray hits.


The [native section review](corner-slide-native-section-root-review.json) closes a separate serial native section of 24af at that same **prior-R1 reference X = 83.39717404347466 mm**. The [raw section BREP](corner-slide-prior-R1-reference-section.brep) was saved before sampling. The [section descriptor](corner-slide-prior-R1-reference-section.json) and [complete parameters and XYZ](corner-slide-prior-R1-reference-section-data.json) retain all **32 curves / 821 drawing samples** under the original **0.001 mm** deflection sampler. Maximum section-plane residual is **1.4211 × 10⁻¹⁴ mm**, within the observed **5 × 10⁻⁶ mm** native edge tolerance. This is actual native section geometry; the earlier surface illustration retains only complete tessellated profile counts and hashes. Neither the reference plane nor its local normal chords is a new 24af mechanical result or global thickness measurement.

## Evidence scope

[Provenance](provenance.json) maps every copied record to its actual source and hash. This compact folder contains the complete records listed there. The new 24af surface, protected-interface and section ROOT, owner and assessment records are copied here in full, together with the raw section and complete sampled coordinates. Full native solver fields, remaining owner collections, solver binaries, surface sample arrays and runtime/source dependencies remain at the retained local paths recorded in those reports; this folder does not claim a self-contained replay.

Process preparation must follow the selected geometry. The seven-region, 1,034-layer native-envelope experiments still refer to the preceding stock body; they are not transferred to d64. The [repaired stock source-2 report](../carrier-source2-repair-20261018/README.md) records an actual RC0 seal under a separate V3 finite-distance contract. All 22 affected final faces remain explicitly unknown; old strict-12 acceptance, continuous coverage and process-anchor admission remain false. Supports, full layer vectors and a machine job remain subsequent stages.
