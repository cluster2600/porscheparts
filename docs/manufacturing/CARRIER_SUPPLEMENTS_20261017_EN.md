# Carrier results and reproduction notes — 17 October 2026

## Latest revision checkpoint — complete seven-edge law (07b354)

The newest candidate master is native BREP **`07b354e3716b…`**, with CAD mass
**1.262364410 kg** at 4,420 kg/m³, below the 1.30 kg design target. The complete
seven-edge radius function passed its retained exact native-law check, and the
[strict baseline-retention check](../../work/carrier-process-20261017/bounded-webs-C1-functional-law-geometry-gates-preparation-001/root-terminal-review-001.json)
returned an empty difference in every topological dimension. The separate
[addition and mass closeout](../../work/carrier-process-20261017/bounded-webs-C1-functional-law-addition-preparation-001/root-terminal-review-001.json)
records positive added material. This closes the revision's native geometry
retention and added-material checks.

The fresh surface is STL **`8d0b09b705e1…`**, with **637,850 triangles**. Its
[joint surface closeout](../../work/carrier-process-20261017/bounded-webs-C1-functional-law-libigl-preparation-001/root-terminal-review-001.json)
records one connected component and zero boundary/non-manifold edges,
inconsistent orientation edges, degenerate triangles, needles and
self-intersection pairs. The **3,072 STL→BREP probes** have maximum distance
**0.01900753 mm**; the **8,716 CAD→STL samples** give **0.04738813 mm**. Both are
below the unchanged 0.06 mm sampled-distance limit. Sampling does not establish
a continuous global distance bound.

The [actual geometry view](../../parts/993-eng-carrier-0001/source/progress-figures-20261016/C1-functional-law-candidate-20261017/README.md)
shows the complete retained STL and a source-datum junction crop. Its actual
PNG and rasterized PDF page were reviewed for legible English labels and no
observed clipping. The close-up is a display projection, not a wall-thickness
or stress measurement.

The [actual seven-edge law figure](../../parts/993-eng-carrier-0001/source/progress-figures-20261016/C1-seven-edge-radius-law-20261017/README.md)
shows the retained radius coefficients and exact proof references. It is a
scalar law plot, not a rendering of the surface or a mechanical result.

The [complete protected-interface and tool-access comparison](../../work/carrier-process-20261017/bounded-webs-C1-functional-law-protected-chunks-preparation-002/root-terminal-review-001.json)
now passes for this master under retained study-interface dimensions. The
complete ordered probe results and native CAD/assembly checks were retained.

The [fresh T10 mesh closeout](../../work/carrier-process-20261017/bounded-webs-C1-functional-law-BREP-mesh-preparation-001/root-terminal-review-001.json)
records **166,263 nodes and 89,485 C3D10 elements**, straight midsides and zero
nonpositive sampled Jacobians; the minimum sampled Jacobian is
**0.0003884557712**. The six current node groups were measured anew: 528 nodes
in each of the four bolt groups, and 2,274 in each end group. Their node tags
and exact coordinate rosters are not assumed identical to an older mesh.
The imported OCC volume is 285,603.0822514583 mm3, matching the like-for-like
nonadaptive native reference at the unchanged relative 1e-8 guard. Separately,
the mesh volume is 285,525.5303865585 mm3, with relative error
-0.0002705762106 against the adaptive native material-volume reference. These
operators remain separate; the import check does not prove absolute CAD identity.

The [two closed linear-static cases](../../work/carrier-process-20261017/bounded-webs-C1-functional-law-static-preparation-001/root-solver-terminal-review-001.json)
use this same 07b354 master and coarse T10 mesh: Fz = −4,000 N,
My = +850,000 N·mm, E = 107,000 MPa and ν = 0.31.

| Current coarse case | Global IP von Mises maximum | All-node displacement maximum | Relative energy-closure error |
| --- | ---: | ---: | ---: |
| Rigid ends | 690.251 MPa | 2.794908 mm | 8.2870e-9 |
| K1000 ends | 1,898.691 MPa | 18.181958 mm | 1.2120e-8 |

Both independent energy closures pass the unchanged 1e-4 tolerance; all global
integration-point peak ties are retained. K1000 means 1,000 N/mm **total per eye
and axis**, distributed over 2,274 nodes at each end (13,644 SPRING1 elements).
These are coarse-mesh results; stress convergence has not been established.
Earlier a42 C1 and terminal-taper stresses and H2 studies are separate histories
and are not transferred to this master. The “Current C1” section below remains
the **a42 C1 checkpoint**, followed by its historical evidence.

[English workflow guide](PART_WORKFLOW_EN.md) · [French supplement](CARRIER_SUPPLEMENTS_20261017.md) · [Figure gallery](../../parts/993-eng-carrier-0001/source/progress-figures-20261016/index.html)

This page separates the current C1 results, retained historical studies and
unfinished support/delivery stages. File names and evidence identifiers retain
their original spelling. The archive READMEs and figures linked below remain
unchanged historical records.

## Current C1 geometry and mechanical results

The editable master is native BREP **`a42e6942…`**, with CAD mass
**1.262369675 kg ≤ 1.30 kg** at 4,420 kg/m³. Its strict native old-minus-new
material check is empty. Candidate STEP exchanges remain refused; BREP is
not relabelled as a successful STEP export.

The dedicated Gmsh 4.15.2 surface contains **638,174 triangles**. The independent
[libigl report](../../parts/993-eng-carrier-0001/source/progress-figures-20261016/surface-remesh-audit-20261017.json)
records zero open/non-manifold edges, orientation inconsistencies, degenerate
triangles, needles or self-intersections, and one positive component. The needle
criterion remains 0.001. The 3,072 STL→BREP probes and 8,621 BREP→STL points give
**0.018234 and 0.047388 mm**, below 0.06 mm. These are sampled distances, not a
continuous global BREP-distance bound. [Figure 23](../../parts/993-eng-carrier-0001/source/progress-figures-20261016/surface-remesh-20261017/README.md)
retains both full surfaces and the actual replay evidence.

The coarse C1 volume mesh contains **166,794 nodes and 89,788 T10 elements**,
minimum Jacobian **0.00828553**, with no non-positive elements. Its six nodal
rosters were measured on this mesh and differ from the earlier EF7 rosters.
Import volume is checked against the same native integration operator at the
unchanged relative threshold of 10⁻⁸. The separate adaptive native volume
remains the mass and FE-volume reference.

Both coarse C1 cases and both qualified local-H2 cases have genuinely closed
with solver return code 0 and passing independent energy audits:

| Mesh and case | Maximum displacement, mm | Global IP von Mises, MPa | Relative energy error |
| --- | ---: | ---: | ---: |
| Coarse C1, rigid | 2.794104095 | 907.278068 | 3.593452869 × 10⁻⁹ |
| Coarse C1, K1000 | 18.171491077 | 2,663.075178 | 3.151176986 × 10⁻⁹ |
| Local H2 C1, rigid | 2.794565820 | **996.757555** | **8.555242736 × 10⁻⁹** |
| Local H2 C1, K1000 | 18.174421153 | **2,996.496111** | **2.509120423 × 10⁻⁸** |

The energy threshold remains **10⁻⁴**. Every case retains Fz = −4,000 N,
My = +850,000 N·mm, E = 107,000 MPa and ν = 0.31. K1000 means **1,000 N/mm in
total per eye and per axis**, distributed over each eye's nodes. The H2 decks
were compared to the actual coarse C1 CLOAD, fixed-set and spring-stiffness
cards and nodal rosters, rather than relying only on parameter labels.

All global maxima are retained. The coarse cases share element **84037/IP1**.
The H2 peak moves to **90371/IP2**, at undeformed reference coordinates
**[82.162332198, −14.460778140, 12.883191321] mm**. The rigid and K1000 stress
peaks increase by about **9.86% and 12.52%**; displacement changes by only
about 0.016%. The energy checks pass, but these two meshes do **not establish
stress convergence** or an allowable-stress decision.

The [actual H2 root closeout](../../work/carrier-process-20261017/bounded-webs-C1-qualified-h2-static-preparation-001/root-terminal-review-001.json)
(SHA-256 `a988350ed8ac84008b35c893ad24dba377756bfa211d400aee7be9ea85e5afe1`)
joins the two solver returns, full outputs, independent audits, all peaks and
owned-container cleanup. Its [durable copy](../../parts/993-eng-carrier-0001/source/design-20261016/native-C1-h2-20261017/evidence/root-review/native-FEA-root-review.json)
is now retained in the separate H2 capsule; the coarse-C1 capsule is unchanged.

The existing H2 mesh had first been refused by its original float-volume
non-regression guard. That refusal remains unchanged. A separate closed
[qualification](../../work/carrier-process-20261017/bounded-webs-C1-existing-mesh-qualification-preparation-001/root-terminal-review-001.json)
verified the same serialized binary64 volume operator on both meshes, all
three refinement passes, protected faces/nodes and the original local size
measurements. It does not rewrite the original verdict. The two fixed target
values are **0.4668954269534402 mm**, derived from half the original peak
TET's maximum corner-edge length; they are not a global mesh-size label.

## Which files and pictures reproduce which results

The [native C1 capsule](../../parts/993-eng-carrier-0001/source/design-20261016/native-C1-20261017/README.md)
contains the editable BREP, dedicated surface, coarse C1 mesh and both complete
coarse cases, including CAD parents, INP, DAT/FRD/NPZ and full reports. Its three
archives are each below 100 MB and restore **186 original members**. The retained
analysis replay reproduced all four complete coarse energy/peak reports without
running CAD, Gmsh or CCX. Its [publication receipt](../../parts/993-eng-carrier-0001/source/design-20261016/native-C1-root-publication-20261017.json)
links the actual returns and byte-identical replay. The newer H2 cases are
separate evidence; they are not claimed to be members of those coarse archives.

The [durable C1 H2 capsule and actual reproduction](../../parts/993-eng-carrier-0001/source/design-20261016/native-C1-h2-20261017/ACTUAL_REPRODUCTION.md)
add three new ZIPs, each below 100 MB, and depend on the 186 existing C1 members.
The combined restoration contains 420 original files. Actual owned verification
and analysis replay both closed RC0; all four complete energy/peak reports were
reproduced byte-identically, with every original and all 500 runtime files
unchanged. The [root replay closeout](../../parts/993-eng-carrier-0001/source/design-20261016/native-C1-h2-20261017/evidence/root-review/root-replay-terminal-review-001.json)
and complete inventory preserve the result without a new CCX, CAD or mesher run.
The original H2 volume refusal and subsequent distinct qualification remain
separate records; no stress-convergence or manufacturing claim is added.

[Figure 24](../../parts/993-eng-carrier-0001/source/progress-figures-20261016/C1-fields-20261017/README.md)
shows the **coarse C1** stress/displacement fields. It uses every boundary facet,
a common stress scale, all global peaks and deformation at **×1**. The facet
colour is the maximum of the four IP values in its adjacent element; global
peaks remain separate markers/tables. Facets use the linear corners of T10
faces, not curved quadratic-face interpolation. The dependent drawing replay
restores the C1 archives and adds a small 44-file mirror; all three output
formats are byte-identical. It requires the documented C1 capsule and installed
211 + 8 runtime authority; no large NPZ/INP/ZIP/runtime is duplicated.

The [native fillet section, figure 22](../../parts/993-eng-carrier-0001/source/progress-figures-20261016/native-fillet-20261017/README.md)
uses actual section edges from the old STEP and the new BREP. Its three-dimensional
R1 blend is not a hand-drawn circular arc. The drawing replay operates on the
retained extracted points; the parent CAD models are linked by hash.

The next mechanical step must use the same CAD, loads and mounts and address
the migrating local peak. A picture, a small energy residual or a change of
support stiffness is not substituted for a stress-convergence study.

## Historical mechanical studies retained separately

The earlier local refinement belongs to the **previous STEP geometry**, not C1.
Its [mesh figure](../../parts/993-eng-carrier-0001/source/progress-figures-20261016/local-refinement-20261017/README.md)
and [two-case capsule](../../parts/993-eng-carrier-0001/source/design-20261016/local-refinement-20261017/README.md)
retain 160,964 nodes, 86,544 T10 elements and 3,218 protected facets. Its stress
peaks of about **1,108 / 3,337 MPa** rose by 79.4% / 99.1% and migrated. Those
results motivated the geometric investigation; they are not convergence data
transferred to the changed C1 master.

The [16-to-32-state constitutive study](../../parts/993-eng-carrier-0001/source/design-20261016/constitutive-refinement-20261017/README.md)
also retains its original mesh, material law, loads and supports. Only the two
static increment lines change from `0.125` to `0.0625`; final amplitude and step
duration remain unchanged:

| Check over all states | 16 states | 32 states | Unchanged threshold |
| --- | ---: | ---: | ---: |
| Maximum relative ENER | 0.001585140971 | 0.000731617082 | 0.001 |
| Maximum relative Piola | 0.000005637878 | 0.000087742489 | 0.0001 |
| Maximum residual displacement, mm | 0.09925853846 | 0.09908998769 | Not defined |

The Piola maximum **increases**, while remaining below its threshold. The
historical 16-state ENER refusal is preserved. The 32-state audits pass, with
positive deformation determinants and plastic strain inside the law's measured
domain. This is increment refinement, not demonstrated mesh convergence. Its
Grade 23 ELI law comes from the published Flat1/Z specimen by Qixiang Luo,
Lu Yin, Timothy W. Simpson and Allison M. Beese, stress-relieved at 670 °C for
5 h; provenance and CC-BY-4.0 data licence are included. This coupon law and a
future Ti64 machine/process variant are not interchangeable labels.

The [whole-part prescribed-shrinkage study](../../parts/993-eng-carrier-0001/source/design-20261016/wholepart-native64-20261017/README.md)
retains four native double-precision displacement states and analytic checks.
Its uniform gradient error is 1.24 × 10⁻¹⁴ under the unchanged 10⁻⁷ threshold;
the quadratic/provisional-fixture case gives 58.090 µm after release. This is a
prescribed-strain sensitivity calculation, not a calibrated LPBF build model.

## Support, slicing and guide status

The [v7 guide builder](../../scripts/build_carrier_workshop_guide_v7.py) adds the
32-state result to guide 6. It first verifies the historical 16-state binding,
then the same discrete mesh/deck, solver/audit receipts and full JSON comparison.
It keeps the six support gates. For a **new run whose seven regions and process
have all been admitted**, the retained command is:

```sh
python scripts/build_carrier_workshop_guide_v7.py /chemin/du/passage
```

This command does not run CCX or audit DAT files. The builder's binding has been
tested; complete guide packaging still needs the complete admitted regional
results and whole-trajectory audits. The existing seven-region/1,034-layer
package is not declared final PASS here.

The [v3 runner](../../scripts/run_part_workflow_v3.py) accepts 1–86,400 seconds
**per stage**, with sequential stages and the retained cleanup contract. The
[local region-008 recipe](../../manufacturing/workflows/993-carrier-source008-v7-001.json)
identifies a separate V7 generation with a **57,600 s** budget and progress
captures. Its 47 input identities and runtime were checked at launch. That
recipe does not establish a result for all seven regions.

The [covered-point capsule](../../parts/993-eng-carrier-0001/source/process-point-encoding-20261017/README.md)
retains the exact checks of **17,384 events over 1,034 heights** in original
region 000: each collapsed encoded point has a nonzero encoded witness of the
same owner. The 13 helper tests and proof verifier retain exact rounding cells
and rational coverage. This result leaves the original geometry unchanged;
section integration, contacts and exposure graphs require their own complete
checks. It is not a seven-region admission.

The [software-restoration capsule](../../parts/993-eng-carrier-0001/source/software-archive-restoration-20261017/README.md)
records actual small CalculiX, PyMesh and experimental CGAL b4e8 restorations
from local archives, with the pre-existing dependencies explicitly listed.
It does not claim a fully offline stable-CGAL-6.1.3 installation from those
three archives alone.

The remaining handover combines admitted support geometry, audited part/support
vectors and a consistent revision manifest. A printer-specific machine build
file and final Ti64 process variant remain to be selected; generic output is
not presented as an already loaded EP-M650/BLT-S600 job. See the
[retained machine options](../../parts/993-eng-carrier-0001/source/process-20261016/machine-options.json)
for the recorded candidate volumes and source links.


## The local C1 junction in an oblique section

[Figure 25](../../parts/993-eng-carrier-0001/source/progress-figures-20261016/index.html#C1-junction-section)
shows the actual before/after CAD profiles in the plane of the coarse 84037/IP1
normal ray and Z. Its short chord is a local junction observation; the later H2
peak is not plotted. The [sampled-point replay and complete evidence](../../parts/993-eng-carrier-0001/source/progress-figures-20261016/C1-junction-section-20261017/README.md)
retain the distinct native producer and presentation sources, the refused STEP
exchange, and three byte-identical exports without another CAD or FEA run.

## Terminal-taper diagnostic revision

The new native BREP `dde710a2…` is a separate diagnostic revision. Its measured
mass is **1.262364740 kg**, leaving **37.635 g** below the 1.30 kg ceiling at
4,420 kg/m³. The strict baseline-minus-candidate Boolean is empty. A separate
candidate-minus-baseline Boolean and the adaptive CAD volumes retain their own
results: the added solid integrates to 34.420893 mm³, while the difference of
the two whole-solid integrals is 34.414293 mm³. These values are not forced to
match. The [mass and material closeout](../../work/carrier-process-20261017/bounded-webs-C1-terminal-taper-addition-preparation-001/root-terminal-review-001.json)
retains the actual measurements.

Gmsh generated a new surface from this BREP, with **637,836 triangles** and STL
identity `7ef349d6…`. The independent native import measures one valid solid,
one shell, 247 faces, 748 edges, 494 vertices and **zero degenerated edges**.
Those counts concern the whole candidate; the added-material residue has its
own topology. The [forward screen closeout](../../work/carrier-process-20261017/bounded-webs-C1-terminal-taper-native-screen-preparation-001/root-terminal-review-001.json)
retains 3,072 STL-to-BREP samples, a maximum distance of **0.018234 mm** under
the unchanged 0.06 mm criterion, and 8,638 native CAD points for the separate
inverse check. A finite sample does not establish a continuous distance bound.

The kernel completed the native build, but its resulting variable-radius law
differs from the requested transition law. The original post-build refusal
remains RC1. This revision is therefore not substituted for the current C1
master. Its inverse-distance/topology, protected-interface, STEP-exchange and
mechanical results must be obtained for its own identities; the older C1/H2
results above are not results for this taper.

## Exact native coverage: first comparison completed

The CGAL 6.1.3/GMP rational polygon-set implementation has completed five
analytical comparisons and the first actual fallback triangle from a captured
support band. All six native return codes are zero and their exact remaining
areas and coverage decisions match the original Python Fraction calculation.
The analytical cases include a shared edge, an uncovered hole, a positive
2⁻⁸⁰-scale slit and a point contact. The real case retains its original triangle
index 3 and all 708 selected primitives in their original order.

The [native comparison closeout](../../work/carrier-process-20261017/native-band-union-benchmark-preparation-002/root-native-terminal-review-001.json)
binds the compiled binary, input transports, complete outputs, original
reference certificates, libraries and runtime identities. Both owned scopes
were checked inactive/absent after execution. This establishes the first
bounded native comparison; a complete band, the historical step/cell
certificates and the final regional support gates remain separate checks.

## Terminal-taper surface, mounting and volume-mesh results

The independent libigl audit of this revision's surface is complete: one
closed, positively oriented component, **637,836 triangles**, and zero boundary,
nonmanifold, orientation, degenerate, needle or self-intersection defects.
Its **8,638 CAD-to-STL samples** have a maximum distance of **0.047388 mm**, below
the unchanged 0.06 mm criterion. The [joint surface closeout](../../work/carrier-process-20261017/bounded-webs-C1-terminal-taper-libigl-preparation-001/root-terminal-review-001.json)
retains the actual input identities and complete audit. These finite samples
remain distinct from a continuous distance bound.

The complete mounting comparator also passes on the new BREP and new STL.
Central-pad and end-interface symmetric differences, tool-column and secondary
gauge intersections, and the whole-pair Manifold intersection are zero. All
**eight complete 3,264-point containment rosters** return zero hits. Ordered
16-point execution chunks bound temporary work; all 1,632 chunk hashes and
eight whole Boolean rosters are retained. The random ambiguity fallback was
never requested and its binding was restored. The [mounting closeout](../../work/carrier-process-20261017/bounded-webs-C1-terminal-taper-protected-chunks-preparation-001/root-terminal-review-001.json)
records an actual **2,566,619,136-byte peak RSS**, not a hard memory ceiling.
It preserves the historical 1.20 kg flag as false and separately passes the
current 1.30 kg ceiling. The comparator uses the retained F0 study interfaces.

The new volume mesh contains **166,403 nodes and 89,536 quadratic T10 elements**.
All sampled Jacobians are positive; the minimum is **0.007956871**. Its volume
differs from the adaptive native reference by **−0.023078%**. Six mounting
rosters were measured afresh, with **528 / 528 / 528 / 528 / 2,274 / 2,278 nodes**;
old roster identities are not assumed. The [T10 closeout](../../work/carrier-process-20261017/bounded-webs-C1-terminal-taper-BREP-mesh-preparation-001/root-terminal-review-001.json)
also joins the unchanged 10⁻⁸ import-volume criterion to the same nonadaptive
native operator. The rigid and elastic cases below use these new identities.
No old C1/H2 stress result is transferred.

[Figure 26 and its complete evidence capsule](../../parts/993-eng-carrier-0001/source/progress-figures-20261016/C1-terminal-taper-profile-20261017/README.md)
provide English PNG, SVG and PDF comparisons of the actual profiles. This
drawing reuses the closed original profiles and newly extracts only the taper;
the orange ray belongs to original C1. The original radius-law refusal remains
recorded independently of the successful surface, mounting and mesh checks.

## Exact native coverage: complete captured band

The same tested CGAL 6.1.3/GMP binary has completed the entire captured band:
**4,613 triangles and 4,611 ordered primitives**. All triangles are covered;
the sum of exact rational residual areas is **0/1**. The retained transport
derives from the original geometry without changing its triangulation or
coordinates. All **4,615 ordered output rows** are preserved and checked.
The actual native run took **126.359 s**, with **47,374,336 bytes peak RSS**.
The [whole-band closeout](../../work/carrier-process-20261017/native-band-union-full-band-preparation-001/root-terminal-review-001.json)
binds the unchanged binary, complete inputs, outputs, libraries and scoped
cleanup evidence.

This is a new exact polygon-set certificate authority. It does not fabricate
the historical Fraction step/cell certificate or silently replace its verifier.
The separate original Fraction-based one-SKIN trial reached its internal
14,300 s deadline without returning a band certificate or regional commit;
that incomplete result remains recorded. No speed ratio or regional support
admission is inferred from these different completed scopes. Integration must
retain reconstruction, contacts, components and all original regional gates.

The explicit new policy has also completed a full captured planar unit:
genuine reconstructed material, reconstruction record, two complete contacts
and whole-unit admission all pass. Its [unit closeout](../../work/carrier-process-20261017/cgal-captured-unit-policy-diagnostic-preparation-001/root-terminal-review-001.json)
retains the original captured native input and the new outputs. This extends
the band result to that captured unit; fresh native generation, 3D remapping
and regional assembly remain separate stages.

## Terminal-taper: two new mechanical cases

Both linear static cases now use the new **89,536-element T10 mesh** and its
actual mounting rosters. Material stiffness remains E = 107,000 MPa, ν = 0.31;
the combined nominal load remains Fz = −4,000 N and My = +850,000 Nmm. The
elastic model assigns **1,000 N/mm total per eye and per axis**, divided among
that eye's 2,274 or 2,278 nodes.

| Result | Rigid eyes | Elastic eyes, K1000 |
| --- | ---: | ---: |
| Maximum displacement, mm | 2.794015 | 18.170201 |
| Maximum integration-point von Mises stress, MPa | 697.312504 | 1,977.809951 |
| Independent relative energy closure error | 4.35144 × 10⁻⁹ | 1.98886 × 10⁻⁹ |
| Unchanged energy criterion | 10⁻⁴ | 10⁻⁴ |
| Global peak element / integration point | 84327 / 1 | 54403 / 3 |

The [complete two-case closeout](../../work/carrier-process-20261017/bounded-webs-C1-terminal-taper-static-preparation-001/root-solver-terminal-review-001.json)
retains both full results, independent energy audits and every global maximum.
The rigid peak lies at approximately **(−82.1363, −14.3888, 12.8603) mm**; the
elastic peak lies at **(82.0534, −14.6036, 12.5321) mm**. Neither was excluded
because of its location. Both owned solver runs exited zero and their containers
were removed and independently checked absent.

The original coarse C1 cases gave 907.278068 / 2,663.075178 MPa. The new values
are lower on regenerated meshes under the retained loads and support models.
These comparisons do not establish stress convergence or a material allowable.
The common refinement targets both new peak locations using half of each peak
element's measured maximum corner-edge length: **0.466895399 mm** for the rigid
peak and **0.758431424 mm** for the elastic peak. Four completed refinement
passes retained every original node, coordinate lexeme, mounting roster and
protected boundary facet. The resulting mesh contains **168,675 nodes and
91,040 T10 elements**, with positive sampled Jacobians.

The unchanged volume non-regression test refused this run: the refined mesh
volume is **285,536.9707756387 mm³**, versus **285,536.9707756392 mm³** in the
parent's metadata. The [refinement closeout](../../work/carrier-process-20261017/bounded-webs-terminal-taper-discrete-refinement-preparation-001/root-terminal-review-001.json)
preserves the refusal and all four complete pass records. Independent edge
measurement was not reached, and no refined mechanical case has run. Comparing
both serialized meshes with the same volume operator is the next diagnostic.
The original radius-law refusal also remains recorded.

## Terminal-taper: default STEP exchange result

One default STEP export and readback completed with all ten captured reader /
writer settings unchanged; the two writer settings were restored in `finally`.
The adaptive relative volume difference was **1.31549 × 10⁻⁹**, passing the
unchanged 10⁻⁸ criterion. The nonadaptive and adaptive volume operators remain
separate records.

Both fresh, serial, non-destructive differences at fuzzy zero completed, but
neither was topologically empty. The strict STEP roundtrip therefore remains
**refused**. Its [complete exchange closeout](../../work/carrier-process-20261017/bounded-webs-C1-terminal-taper-STEP-preparation-001/root-terminal-review-001.json)
preserves both raw BREP residues and all dimensional summaries. These Boolean
outputs are not interpreted as material erosion. The native BREP and its
separately checked STL remain the geometry references; the STEP does not
replace that master.

## Complete seven-edge functional-law revision

The new native candidate `07b354e3716b…` retains the requested radius function
over all seven source edges. The isolated rebuilt-stock control reproduced
`NCollection_Sequence::First`; the patched control completed and saved one valid
Solid. The [complete native observation](../../work/carrier-process-20261017/bounded-webs-C1-full-contour-native-observer-preparation-001/root-terminal-review-001.json)
retains both outcomes and the exact rational restrictions of every native knot
span. The [English law figure](../../work/carrier-seven-edge-law-figure-preparation-002/render-001/carrier-seven-edge-radius-law.png)
shows the progressive first edge and the constant 1 mm radius on the remaining
six edges. Its sampled curves illustrate the separate full-function proof.

The new candidate has its own [strict baseline-retention check](../../work/carrier-process-20261017/bounded-webs-C1-functional-law-geometry-gates-preparation-001/root-terminal-review-001.json)
and [positive-addition, mass and bounds check](../../work/carrier-process-20261017/bounded-webs-C1-functional-law-addition-preparation-001/root-terminal-review-001.json):

| Actual CAD result | Value |
| --- | --- |
| Calculated mass at 4,420 kg/m³ | **1.262364410 kg** |
| Margin below the 1.30 kg limit | **37.636 g** |
| Candidate volume, adaptive operator | 285,602.8077120175 mm³ |
| Added-material Cut integral | 34.34037865930564 mm³ |
| Adaptive candidate-minus-baseline volume difference | 34.33973232074641 mm³ |

The two volume differences use distinct operators and retain their distinct
values. The original bounds gate passes with its unchanged 10⁻⁶ mm guard.
The [fresh surface export](../../work/carrier-process-20261017/bounded-webs-C1-functional-law-surface-preparation-001/root-terminal-review-001.json)
contains **637,850 triangles**, STL `8d0b09b705e1…`. At this export checkpoint,
its two-way surface, protected-interface and mechanical checks are pending.
Earlier terminal-taper fields remain results of their own geometry revision.
