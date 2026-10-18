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

A subsequent [frozen-bore attempt](frozen-bore-refusal-root-review.json) recovered all six original T6 bore meshes from the complete current T10 boundary. No fixed bore edge conflicted with the two local targets. Native 1D generation completed, but a curve-parameter ambiguity stopped installation before any protected curve was cleared or injected. No volume mesh or FEA followed. The original coordinate, complete connectivity, volume and actual edge-size gates remain unchanged while this mapping is corrected.

## Evidence scope

[Provenance](provenance.json) maps every copied record to its actual source and hash. This compact folder contains the complete records listed there. Full native fields, owner collections, solver binaries and runtime maps remain at the retained local paths recorded in those reports; this folder does not claim a self-contained solver replay.

Process preparation must follow the selected geometry. The seven-region, 1,034-layer native-envelope experiments still refer to the preceding stock body; they are not transferred to d64. The [repaired stock source-2 report](../carrier-source2-repair-20261018/README.md) records an actual RC0 seal under a separate V3 finite-distance contract. All 22 affected final faces remain explicitly unknown; old strict-12 acceptance, continuous coverage and process-anchor admission remain false. Supports, full layer vectors and a machine job remain subsequent stages.
