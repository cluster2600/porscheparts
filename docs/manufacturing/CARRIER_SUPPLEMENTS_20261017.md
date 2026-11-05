# Supplements to the calculation and its reproduction

[English results supplement](CARRIER_SUPPLEMENTS_20261017_EN.md) · [English workflow guide](PART_WORKFLOW_EN.md)

[Guide 7](../../scripts/build_carrier_workshop_guide_v7.py) adds to guide 6
the **32-state** mechanical cycle. It first checks the historical 16-state
attachment and keeps the six support admissions of guide 6. It then attaches
the results to the same mesh and the same load deck, checks the solver and
audit receipts, then recomputes the comparison of the JSON states.

The thresholds remain ENER = 0.001 and Piola = 0.0001. The historical 16-state
ENER refusal remains visible. The law is the published Grade 23 ELI reference;
the computed residual has no defined acceptance threshold. The
[evidence capsule](../../parts/993-eng-carrier-0001/source/design-20261016/constitutive-refinement-20261017/README.md)
and its 44 files are copied with their manifest into the run directory.

On a new execution whose seven regions and process have been admitted:

```sh
python scripts/build_carrier_workshop_guide_v7.py /chemin/du/passage
```

The module reruns neither the solver nor the audit of the DAT files. Its
attachment was replayed on exact copies of the current model's inputs. The
packaging of the complete guide still waits for the results of the seven
regions.

[Runner 3](../../scripts/run_part_workflow_v3.py) keeps the contract of
runner 2 and accepts a declared budget of 1 to 86,400 seconds **per step**.
Steps remain sequential; this ceiling is not a total duration.
Existing recipes keep their budgets. The next recipe must explicitly declare
the budgets needed for long generations. Clean-up on overrun remains that of
runner 2; the diagnostics supervisor is a separate mechanism.

The targeted tests cover the runner's identities and outputs, the budget
bounds and the refusals of the mechanical supplement: modified data,
incomplete schedule, altered thresholds, solver or audit errors and copies
modified after rendering. The [gallery](../../parts/993-eng-carrier-0001/source/progress-figures-20261016/index.html)
keeps the images of the model and the calculations.

The [local recipe for region 008](../../manufacturing/workflows/993-carrier-source008-v7-001.json)
reruns only its V7 generation from the preserved inputs, with a budget of
57,600 seconds and captures of each completed section. Its 47 digests and its
runtime identity were checked before launch. It remains distinct from the
complete recipe: its execution is in progress, and no result for the seven
regions is inferred from the illustrated local replay alone.

The [software restoration capsule](../../parts/993-eng-carrier-0001/source/software-archive-restoration-20261017/README.md)
keeps the three real CalculiX, PyMesh and CGAL b4e8 experiments, the executed
callers, the small native results and a verifier with no native runtime. It
states the dependencies already installed and distinguishes the experimental
archive from the stable CGAL 6.1.3 procedure.

The [covered-point encoding capsule](../../parts/993-eng-carrier-0001/source/process-point-encoding-20261017/README.md)
keeps the real check of the **17,384 events** of the large zone 000 over the
1,034 heights: all have a non-zero encoded witness from the same group.
The helper and its thirteen tests can be used without an AM runtime; a
verifier rereads the compressed evidence and recomputes rounding cells and
rational inclusions. The original geometry remains intact. Integration into
the slicer and recomputation of contacts and graphs remain separate from this
check; this capsule grants no global admission.

The [plate for the imposed shrinkage calculation on the whole part](../../parts/993-eng-carrier-0001/source/progress-figures-20261016/wholepart-release-20261017/README.md)
keeps the four native displacement fields, their double-precision reading and
the analytical checks. The former gradient threshold of 10⁻⁷ remains
unchanged. The uniform case gives an error of 1.24×10⁻¹⁴; the quadratic field
and the provisional clamping give 58.090 µm after release.
This mechanical sensitivity study does not replace process simulation.
The PNG was reread; the three formats were reproduced from a separate copy.
The [complete native case capsule](../../parts/993-eng-carrier-0001/source/design-20261016/wholepart-native64-20261017/README.md)
keeps the inputs, the four states, the exact sources and the real receipts.
Its commands restore the compressed files and replay their analysis with
Python and NumPy, without rerunning the solver.

The [local refinement plate](../../parts/993-eng-carrier-0001/source/progress-figures-20261016/local-refinement-20261017/README.md)
compares the real edges before and after in two fixed zones. The resulting
mesh contains **160,964 nodes and 86,544 T10 elements**; the 3,218 protected
facets and the support sets are preserved. The
[capsule of the two elastic calculations](../../parts/993-eng-carrier-0001/source/design-20261016/local-refinement-20261017/README.md)
provides the mesh, the solver inputs, the complete fields and the restoration
and reanalysis commands. Both energy balances pass their unchanged threshold
of 10⁻⁴; reanalysis from another directory reproduces the four complete
reports byte for byte.

The computed peaks reach **1,108 MPa on rigid supports and 3,337 MPa under
K1000**, increases of 79.4 % and 99.1 % relative to the EF7 mesh.
They migrate to the cover–rib junction. This result guides the correction of
the shape; it does not constitute stress convergence. The mesh drawings and
the mechanical results remain attached to the same reference STEP, distinct
from any new fillet geometry.

The [comparative section of fillet R1](../../parts/993-eng-carrier-0001/source/progress-figures-20261016/native-fillet-20261017/README.md)
shows the blend built in the native BREP, at the same coordinates before and
after. Its extracted CAD points and the three exports are preserved; the
standalone replay reproduces their drawing. The prototype keeps its refused
STEP exchange check and does not inherit the mechanical calculations of the
previous geometry.

The [new remeshing plate](../../parts/993-eng-carrier-0001/source/progress-figures-20261016/surface-remesh-20261017/README.md)
compares the two complete STLs of the same C1 BREP. Gmsh 4.15.2 produces
**638,174 triangles**, with **zero needles** at the unchanged criterion of
0.001. The
[libigl check, actually closed](../../parts/993-eng-carrier-0001/source/progress-figures-20261016/surface-remesh-audit-20261017.json)
confirms zero open edges, non-manifold elements, orientation inconsistencies,
degenerates or intersections, one positive component, and bores and supports
preserved within their tolerances. The 3,072 STL→BREP probes and the 8,621
BREP→STL points give maxima of **0.018234 and 0.047388 mm**, below the
0.06 mm threshold. These distances remain sampled. The
[standalone replay of the drawing](../../parts/993-eng-carrier-0001/source/progress-figures-20261016/surface-remesh-root-publication-20261017.json)
reproduces the PNG, SVG and PDF byte for byte; the real receipts are preserved.

The C1 BREP master also passes the strict native material-conservation Cut.
Its new global calculation mesh comprises **166,794 nodes and 89,788 T10
elements**, with a minimum Jacobian of **0.00828553** and no non-positive
element. The six nodal groups are measured on this mesh; their lists differ
from the former EF7. The import check now compares volumes computed by the
same integration, at the unchanged threshold of 10⁻⁸; the adaptive volume
remains the reference for the mass and the FE volume.
The CAD mass remains close to **1.26237 kg**, below the ceiling of **1.30 kg**.
The [two C1 calculations, actually closed](../../parts/993-eng-carrier-0001/source/design-20261016/native-C1-20261017/README.md)
keep the loads Fz = −4,000 N and My = +850,000 N·mm. The rigid case gives
**2.794104 mm / 907.278068 MPa**, the K1000 case **18.171491 mm /
2,663.075178 MPa**. K1000 means 1,000 N/mm in total per eye and per axis,
distributed over the nodes of each eye. Both energy audits pass the
unchanged threshold of 10⁻⁴, with relative errors of **3.59 × 10⁻⁹** and
**3.15 × 10⁻⁹**. All peaks are preserved; the common maximum is element
84037, IP1, near [82.136315; −14.388848; 12.860258] mm.

The capsule keeps the editable BREP, the surfaces, the meshes and the raw
outputs in three archives of under 100 MB each. Its replay from `/` restores
**186 original files** and reproduces the four complete energy and peak
reports byte for byte. The
[publication receipt](../../parts/993-eng-carrier-0001/source/design-20261016/native-C1-root-publication-20261017.json)
links the real calculation returns, the preserved files and this replay.
The stresses and refinement of the former CAD are not transferred.
Current update (English): the same-master C1 h/2 test is now closed, with
VM = 996.758 / 2996.496 MPa, U = 2.794566 / 18.174421 mm and passing unchanged
1e-4 energy audits; stress convergence remains open. The
[durable H2 capsule and actual four-report byte-identical replay](../../parts/993-eng-carrier-0001/source/design-20261016/native-C1-h2-20261017/ACTUAL_REPRODUCTION.md)
preserve the complete cases and the earlier refusal separately.

[Plate 24 of the C1 stresses and displacements](../../parts/993-eng-carrier-0001/source/progress-figures-20261016/C1-fields-20261017/README.md) shows these two closed cases with all boundary facets, the global maxima separated, a common stress scale and a deformed shape at ×1. The PNG, SVG and PDF were reproduced byte for byte from the C1 archives and a small mirror of sources and evidence; the dependencies and the real closure receipts are preserved. This drawing claims no new mechanical analysis and no stress convergence.
