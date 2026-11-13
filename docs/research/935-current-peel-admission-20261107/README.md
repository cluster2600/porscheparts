# Exact peel continuation on the current 935 calculation mesh

Four independently checked batches remove **2,440** severely conditioned sliver
cells. The full native shape census improves from **996 to 868** nonpositive
indicators, but the absolute quality gate still fails and no head field solve
is admitted.

This increment continues the latest
[kernel-cavity candidate](../935-kernel-cavity-20261105/README.md), rather than
repeating the historical OpenFOAM case. It applies the previously verified
microscopic surface-peel operation after a fresh complete source audit.
[Results](results.json) bind each batch, its independent checks and the final
candidate. A reduction in bad cells does not complete solver admission.

The domain remains a declared hypothetical bare head. The original scan,
the open acquired-surface reconstruction and the
[supported printing assembly](../935-single-volume-20261107/README.md) remain
separate and unchanged. This is a numerical calculation-surface correction;
its checker 3MF is not a replacement printing master or a metal machine job.
The original faithful-CAD, functional-simulation and metal-build objective
remains open.

## Source admission and unchanged operation

The actual parent mesh is
`d618763474f2eeb7bf680ce18f6f2efce22795e538263b7dfc639ffb68be62c5`.
Its whole-volume signs, opposite internal-face pairing, complete source
boundary, exact conditioning census and Gmsh readback were inspected before
this continuation. It contains 15,251 cells with edge-Jacobian Frobenius
condition at least 1e12 and 996 nonpositive native `minSICN` indicators. Its
absolute quality gate fails. This admits diagnostic correction, not head fields.

The frozen [peel operator](../935-condition-directed-20261105/source/audit_surface_peels_v2.py)
is reused unchanged. The new wrapper independently binds the current source
identities and joins every severe cell to all 8,218,458 surface triangles by
literal node IDs. It protects every cap-incident vertex and the mapped original
marked curves. Tag zero is inherited envelope skin, not acquired-scan identity;
cap tags describe assumed construction closures, not measured interfaces.

An admitted cell has exactly two skin boundary faces. Its old boundary diagonal
must be unmarked and incident to that cell only. The alternate diagonal must
be absent from the whole boundary and have a complete simple-cycle cell link.
The frozen exact geometric predicate requires a strictly convex projected
quadrilateral, consistent normals, nonworsening triangle quality and the same
fixed displacement limit, `512 * 2^-52 * maximum_extent`. Vertex-disjoint
packing is deterministic. No threshold, coordinate, cap, marked curve or
physical hypothesis is tuned to increase the accepted count.

Deleting the thin positive tetrahedron replaces its two boundary triangles by
its other two faces. The represented calculation boundary and material volume
change; exact preservation of the old surface is not claimed. Every stored
coordinate remains. The complete local graph correspondence is composed with
the predecessor's inherited bound, always below the existing 0.01 nominal-mm
study limit. This is not a measured manufacturing tolerance.

## Independent verification and complete checks

The constructor exports proposals only. A separate wrapper reuses the frozen
[Fraction verifier](../935-condition-directed-20261105/source/verify_surface_peels.py),
independently recomputing every local graph/volume proof, complete global edge
incidence, simple cycle, cap and curve restriction. It checks disjoint patches,
exports only after those proofs, and rereads every coordinate bit, retained
cell tuple and surface row. These are distinct arithmetic implementations of
the same contract, not independent physical observations.

Each resulting surface receives the unchanged full native validator: all edges,
vertex manifoldness, connected components, shell orientation, every intersection
pair and exact 3MF coordinate/index readback. The complete volume inspector
checks every cell with outward determinant intervals and exact Fraction
fallbacks, every opposite internal face and the complete oriented boundary.
It does not upgrade the inherited exhaustive tetrahedron-pair intersection
status. Every condition count is then freshly recomputed and compared against
an independent exact deletion prediction from the full predecessor census.
Gmsh export/re-import checks every actual node label, coordinate, tetrahedron
and boundary row before its complete native metric census.

Each positive source audit is followed by separate Fraction verification,
complete native surface and volume checks, a fresh whole condition census and
actual Gmsh export/re-import. The accepted progression is:

| Stage | Removed in batch | Remaining tetrahedra | Condition at least 1e12 | Nonpositive native minSICN |
| --- | ---: | ---: | ---: | ---: |
| Immutable kernel parent | — | 12,967,669 | 15,251 | 996 |
| First batch | 2,217 | 12,965,452 | 13,034 | 875 |
| Second batch | 204 | 12,965,248 | 12,830 | 868 |
| Third batch | 18 | 12,965,230 | 12,812 | 868 |
| Fourth batch | 1 | 12,965,229 | 12,811 | 868 |

The global minimum mean ratio remains 1.291009351665788e-11 and the worst
edge-Jacobian Frobenius condition remains approximately 8.452019e15. Native
Jacobian determinants and volumes stay positive, while 868 native shape
indicators remain nonpositive. These distinct metrics are retained together;
the shape rejection is not called a measured physical inversion.

A final complete audit of all 12,811 remaining severe cells finds **zero**
eligible peels: 11,625 would worsen the local triangle-quality minimum, 211
violate cap constraints and 975 lack exactly two boundary faces. This is a
fixed point of this unchanged operation, not proof that no other reconstruction
or meshing method can work. No empty candidate or identical native rerun is
created. Further work must audit those source restrictions before choosing a
different admitted correction.

The new cumulative checker independently composes every deletion back to the
one immutable kernel parent. It compares every coordinate bit and retained
tetrahedron tuple, verifies that every changed boundary row belongs to an
independently certified patch, checks actual MSH/3MF and report/source hashes,
and recomputes the complete removed volume using exact parent-coordinate
determinants. The exact result agrees with the sum of all four certificates.
Literal two-generation ancestry and invalid-index controls exercise its mapping;
the two portable unit tests include duplicate, signed-range, dtype, shape and
large-unsigned refusals.

The actual literal controls precede the head in both arithmetic paths. A
forged proposal repeats a real source-cell ID and recomputes its declared file
hashes; the verifier rejects it at uniqueness checking, before mesh export.
This demonstrates that checksum consistency alone cannot admit a proposal.
Every published source patch is independently replayed with the system `patch`
utility. Its bytes must equal the executed source, and every loop/comprehension
AST must remain identical to the frozen original. The patches adapt source
identities, complete denominators and predecessor report schemas; the numerical
operators, classifiers, controls and quality thresholds remain unchanged.

## Execution, resources and replay

Requirement `R935-CURRENT-PEEL-1` links the current source audit to independently
checked numerical correction in application service `A-CAE` on `T-MAC`. This
follows the [scan workflow](../../architecture/scan-repair-workflow.md) and
[local-compute decision](../../decisions/0012-local-compute-gpu-last.md).
Qwen/CADAM assistance and PicoGK/STEP, Gmsh, OpenFOAM, CalculiX and Adamantine
retain their documented roles. No imported model output grants acceptance.

Use new private output directories and the frozen input manifests. The wrappers
take `--job PRIVATE_JOB --output NEW_DIRECTORY`; jobs bind all geometry,
predecessor reports and frozen helper hashes. The input capsules are private;
their hashes and scalar outcomes are public. Source patches apply to the exact
original scripts named in their headers. The private derivation receipts and
patch-replay controls bind the original and executed hashes. Never edit a frozen
source or replay into an existing evidence directory.

Existing Mac Python 3.12.13 / NumPy 2.5.4 runtimes are reused. Gmsh 4.12.1 is
provided by the existing native head runtime, with the existing isolated
scientific site explicitly on `PYTHONPATH`. A successful module probe records
the actual Gmsh module and binary hashes before head execution. No package is
installed or upgraded. Early preparation refusals are retained: an attempted
copy of an already frozen helper, a runtime without Gmsh and a Gmsh-only runtime
without NumPy. Each stops before any native head child; the corrected plans
reuse hash-identical sources and the documented separated runtimes. A second
native launch also refuses a reused output directory before head calculations.
Its nonzero status is retained even though a historical report exists there.
The corrected plan uses a fresh owned directory and checks its current mesh
and input-report binding; the cumulative checker verifies that binding again.

The existing bounded controllers retain exact command lines, logs, input hashes,
terminal states and owned-child reaping. Admission/verification use 600 seconds
and 4 GiB sampled child RSS; global checks use 600 seconds per ledger and 12 GiB
sampled direct-child RSS, with a 4 GiB disk floor. Outputs remain private.
New paid compute is **$0**. The original $35 total / $30 compute / $5 reserve
is unchanged; the prior conservative allocation remains $15.6788427751. No
new Vast resource or supplier message is created by this increment.

A read-only refresh of the existing supplier correspondence supplies no new
measurements, units, hidden-passage or material/process specification. The
existing [cast-and-machined identification](../wolfe-classics-935-billet-cylinder-head-scan.md)
is reconfirmed. The supplier request remains unsent.

Physical scale calibration, exact variant/interfaces, hidden passages, alloy,
operating data, process/exposure recipe, powder removal, machining, inspection
and professional engine validation remain unresolved. The acquired-surface
closure lane also remains open. This correction cannot qualify a functional
metal head or replace those requirements with a software success flag.
