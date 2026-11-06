# Traceable local cuts through the original 935 source surface

This increment constructs the transitions left unresolved by the previous
[five-region source admission](../935-source-cut-admission-20261106/README.md).
All **726** crossing source triangles are partitioned into **2,178** derived
triangles. Independent exact-rational checks prove that the two opposite halves
tile each original triangle, preserve its winding and area, remain inside it,
and share the same original-edge intersection nodes. No cap or hidden surface
is added. Component identity and the stock planes remain hypotheses.

The usable outputs are six open OBJ/NPZ references (retained surface plus five
provisional outward domains), ten native STEP transition patches and a saved
FreeCAD transition-review document. All actual stored shapes and all actual
OBJ bytes have independent readback. These advance faithful surface separation;
they are not a complete bare-head solid, parametric engine master or print job.

[Aggregate receipts](results.json) bind the five executed sources, two reused
controllers/macros, input hashes, source/fragment accounting, actual process
terminal results and native registration. Private capsule
`935-source-transition-cuts-20261106-001` is frozen read-only and rehashed:
**93 payload files / 179,382,124 bytes**, manifest
`c466b1dfe74befa86f207d05fd33734506d383515933fe5bf7356614316cad9b`.
Geometry, original IDs, native documents and detailed connection/job inputs
remain outside Git and external AI/CAD services.

## Admission and retained assumptions

The original OBJ remains unchanged under SHA-256
`4623d5d3b73fe3d03ca988a47543a8dd1be7834d3040e6f7efd1e1e95c766486`.
Decoded source arrays retain SHA-256
`dd94c37117a1f1277a4f2b7f0bf0023e0d1858991b943f766cf447db319a101a`;
the complete admission plan is
`f26389c910ded839b94de910f495c0110a0fd103fc860af2b4a07e25139d5026`.
The preceding independent five-region report is
`5a56d4b838ad27b21c3193144f4454fd0fbdbf60d9b04b2c569eec3b2a73de01`,
and its original-face role partition is
`270e59a9e597b9d817ed52952af7afa97ef12406f7ea012905f886688fa76ed3`.

Only those five previously admitted simple, disjoint source-section domains are
processed. Their **0.75 nominal-mm stock** and three source-fit plane hypotheses
are unchanged; no plane, classifier or cut threshold is tuned. One OBJ unit is
one owner-assumed nominal millimetre. Physical calibration, accepted anatomical
separation and manufacturing tolerance remain unverified. The 204 quarantined
source records remain untouched in the original acquisition; they are not
silently deleted or filled in a manufacturing master.

## Both-half construction and independent proof

[The constructor](source/build_transition_cuts.py) identifies generated nodes by
original source-edge ID and plane index. An edge/plane intersection is an exact
fraction of the stored binary source coordinates and coefficients. Both halves
reuse that same node before one rounding to float64. Original nodes retain
their exact stored coordinates. Sutherland–Hodgman traversal retains source
winding; the clipped triangle or quadrilateral is triangulated without an
additional interior point.

[The separate checker](source/check_transition_cuts.py) reconstructs all node
origins directly from the original acquisition with a different rational
formula. It independently derives each half-polygon boundary, checks directed
edge-chain cancellation, exact projected area and three-dimensional planarity,
original-triangle barycentric inclusion, correct halfspace and winding. Each
convex half has one or two triangles, its full expected boundary and exact area;
duplicate, reversed, omitted or overlapping same-count substitutions fail.
The two halves together reproduce the original source triangle in ideal
rational arithmetic.

There are **725 original transition nodes** and **726 constructed source-edge
nodes**. Exact ideal intersections are distinguished from once-rounded stored
coordinates. Maximum once-rounding displacement is
`2.89780573984756e-14` nominal mm. Stored fragments retain nonzero edges and
correct orientation; their minimum stored edge is approximately
`0.0003526949700244301` nominal mm. These are numerical diagnostics, not scanner
accuracy or a manufacturing tolerance. The predeclared constructed-endpoint
arithmetic guard remains `1e-8` nominal mm.

| Provisional region | Original crossing triangles | Retained-side fragments | Outward-side fragments |
|---|---:|---:|---:|
| 1 | 171 | 256 | 257 |
| 2 | 139 | 206 | 211 |
| 3 | 143 | 212 | 217 |
| 4 | 133 | 204 | 195 |
| 5 | 140 | 210 | 210 |
| Total | 726 | 1,088 | 1,090 |

All 726 expected section segments occur once on each side with opposite
directions. Unresolved protrusions and all other original surfaces retain their
previous roles. No anatomical interpretation is granted by this proof.

## Complete surface assembly and actual OBJ readback

[The assembler and separate check mode](source/assemble_source_reference.py)
construct a retained open surface of **2,401,740** triangles: 2,400,652 unchanged
original triangles plus 1,088 retained transition fragments. The five outward
references contain **65,548** triangles: 64,458 unchanged original facets plus
1,090 outward fragments. Across all six references, **2,467,288** triangles equal
the 2,465,836 admitted originals with 726 replaced by their 2,178 fragments.
The 204 original quarantine records remain separately accounted for.

NPZ records bind each original face or independently proved fragment index and
global original/generated node identity. Inspection checks complete coverage
against immutable inputs, then parses every actual OBJ vertex and ordered face.
Original-coordinate readback is exact; constructed OBJ coordinates equal their
independently checked once-rounded intersections. All 726 cut interfaces are
one-use mesh boundaries with the opposite partner direction.

Whole-source edge reconciliation prevents mistaking the cuts for additional
missing acquisition data:

- Separate-mesh edge sum **3,751,731** equals admitted original edges 3,748,827,
  plus 726 subdivided source edges, 726 quadrilateral triangulation diagonals,
  726 new section segments and 726 extra separate-mesh interface uses.
- Separate-mesh boundary sum **101,598** equals admitted original open edges
  100,146 plus twice the 726 section segments.
- The retained reference has **98,874** boundary edges, including its 726 cut
  segments. Other original gaps remain. The complete raw scan's earlier 99,876
  open edges is a different scope, before the 204-record quarantine.

No global hole fill, proximity welding, smoothing or inferred passage is part
of this assembly. Its OBJ/NPZ references are not advertised as printable volumes.

## Native references, actual saved shapes and registration

[Native transition construction/readback](source/native_transition_reference.py)
uses the frozen STEP source builder and independent topology reader. Ten
patches represent both halves of each of the five transition strips. Every
expected derived triangle, straight edge, adjacency, vertex fan and shell is
checked against the bound fragment graph. Original nodes must have **zero**
readback error. Only constructed nodes use the `1e-8` arithmetic guard.
Actual native support planes are also inspected against their vertices.

Separate native preflight processes exercise a literal triangle partition with
nontrivial fractional endpoints. Two actual negative native files must fail:
an acquired original vertex moved by `1e-9` (below the constructed-node guard),
and the same facets with deliberately unsewn edges. Counts or a common loose
coordinate threshold cannot pass those controls.

The reused [FreeCAD document macro](../935-source-cut-admission-20261106/source/create_region_document.py)
saves, closes and reopens ten distinct reference objects with identity
placements, source hashes and false anatomical/manufacturing flags. A fresh
process exports the actual stored shapes; another independently reinspects all
2,178 fragment faces. Actual saved original-node error is zero, maximum
constructed-node readback error is `1.2582760069203449e-11` nominal mm, and
maximum actual support-plane residual is `1.1915561577076594e-11` nominal mm.
The 609,302-byte document contains transition references, not the full head.

[A further actual-native registration check](source/check_native_registration.py)
matches all **726** cut nodes in the saved inside and outside patches and the
previous verified source-section BREP wires. Inside/outside stored coordinates
coincide exactly for every paired node. Maximum difference from a prior section
wire is `1.2259893980790496e-11` nominal mm, below the unchanged arithmetic guard.
Native patches remain separate unsewn references; this is not a sewing,
physical tolerance or global solid-closure claim.

## Execution and reproducibility

The frozen isolated Python 3.12.13/OCP 7.9.3.1 runtime is reused unchanged; its
software manifest is
`d7879b23d83988901358bee60ecfbd3e3372c975051aa4ac1ef328614b4648f7`.
The existing local-only outbound sandbox confines FreeCAD 1.1.4. All phase
ledgers bind concrete input hashes, commands, expected reports and checks before
execution. The reused [bounded controller](../935-source-cut-admission-20261106/source/run_local_delivery.py)
records actual exits, sampled child RSS, deadlines and child reaping, with a
600-second shared wall limit per ledger, 4-GiB child RSS and 4-GiB disk floor.

| Phase | Actual outcome |
|---|---|
| T0 input admission | Existing five source-supported simple/disjoint domains and immutable source hashes verified |
| T1 construction | Literal controls followed by 726 both-half source partitions |
| T2 independent proof | All parent triangles, areas, origins, winding and 726 interfaces verified |
| T3 complete reference | Six actual OBJ/NPZ references inspected and whole-source seams reconciled |
| T4 native delivery | Controls, ten STEP patches, saved FreeCAD shapes and all 726 registrations verified |
| T5 publication | Executed sources, hashes, aggregate receipts and synthetic checks published; repository CI is separate from physical qualification |

Whole-reference construction takes 10.784 seconds, and separate readback/seam
inspection 19.769 seconds (sampled peak 1,499,200 KiB RSS). Native patch build
takes 1.488 seconds and readback 2.128 seconds; native document creation/reopening
2.341 seconds, actual saved-shape export 0.840 seconds, reinspection 1.898 seconds
and registration 1.274 seconds. These are local terminal observations, not a
GPU/cloud speedup comparison. All owned children are reaped.

Replay requires the original private arrays, admitted-region NPZs, role map,
planes and exact hash-bound jobs, plus the frozen builder/reader. Public
summaries do not reconstruct private geometry. Use new private outputs:

```sh
python -B source/build_transition_cuts.py --job PRIVATE/source-job.json --output NEW_FRAGMENTS
python -B source/check_transition_cuts.py --job PRIVATE/source-job.json --built NEW_FRAGMENTS --output NEW_PROOF
python -B source/assemble_source_reference.py --job PRIVATE/source-job.json --fragments NEW_FRAGMENTS/private-transition-fragments.npz --proof NEW_PROOF/report.json --mode build --output NEW_REFERENCES
python -B source/native_transition_reference.py --job PRIVATE/native-job.json --mode build --output NEW_NATIVE
python -B source/native_transition_reference.py --job PRIVATE/native-job.json --mode check --built NEW_NATIVE --output NEW_NATIVE_CHECK
python -m unittest discover -s tests -p test_935_source_transition_cuts.py -v
```

Run the separate assembly check mode and the private sandboxed document/export/
registration ledgers before accepting outputs. Preserve every executed source
version and rejected case. The public tests use synthetic tetrahedron/literal
data and adversarial endpoint, origin, parent, halfspace, duplicate-facet and
actual OBJ/NPZ substitutions. A ninth test binds the public receipts to executed
source hashes, complete accounting, native controls and the false release flags.
They need no private scan or OCCT installation.

## Engineering boundary and next work

This is the existing STEP/FreeCAD acquired-reference branch of the
[engineering architecture](../../architecture/README.md) and
[scan reconstruction workflow](../../architecture/scan-repair-workflow.md).
PicoGK remains authoritative for new engine geometry; these source subdivisions
introduce no missing material, designed cap or passage. Qwen/CADAM remain
auxiliary proposal tools. Gmsh, OpenFOAM, CalculiX and Adamantine keep their
defined meshing, flow/thermal, mechanical and manufacturing roles.

No paid resource or supplier message is created for this increment. The owner
permits the scan on Vast, while this small transition workload uses local
compute. The original $35 total / $30 compute / $5 closeout reserve is unchanged;
the preceding $22.01 observed credit and $15.34 conservative allocations are
historical snapshots, not a fresh balance or invoice.

The retained reference still has unresolved source gaps and component identity.
No admissible closed engine volume follows from these local cuts. The existing
hypothetical domain still has 996 native Gmsh minSICN failures and does not admit
a new engine-field solve. Accepted specimen interfaces/metrology, hidden and
missing surfaces, faithful bare-head solid reconstruction, correlated engine
loads/physics, material/machine/powder/support/toolpath qualification, physical
build/inspection, professional review and engine validation remain open.
G0–G5 stay false and the full faithful-head goal remains active.
