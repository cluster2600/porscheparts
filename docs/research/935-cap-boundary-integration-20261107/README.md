# 935: integrate the refined cap and trace a conforming local volume trial

The refined construction cap is now integrated into a separately versioned
complete head boundary. The whole 8,234,708-triangle surface passes topology,
complete intersection and actual 3MF readback checks. All original point bits,
all retained oriented faces, construction tags and 702,209 mapped required
edges are preserved. This is a **hypothesis study surface**, not faithful
editable CAD, specimen metrology or a qualified functional metal part.

A traceable local cavity was then prepared and meshed. Its actual tetrahedral
trial is positive and conforms to the prescribed boundary, but fails both
independent shape and native metric gates. **It is refused for head-volume
integration.** The existing full volume and supported printing master remain
unchanged; their previous quality failures are not upgraded.

This continues the [checked cap refinement](../935-cap-graph-admission-20261107/README.md)
and [previous complete volume](../935-global-quality-continuation-20261107/README.md).
The [phase ledger](phase-ledger.json) keeps the original CAD, physics, process
and physical-validation objective open. Unprepared later phases are explicit.

## Complete boundary admission

Only 275 traced original cap triangles are replaced by the already checked
16,525 triangles. The 8,125 added points come byte-exactly from that private
cap proposal. Every original full-boundary coordinate remains in its original
array position; every other oriented triangle and construction tag is copied
literally. An independent implementation reconstructs these joins and scans
every candidate facet for every mapped required edge. Each required edge has
exactly two surface uses.

| Whole-boundary check | Result |
|---|---:|
| Vertices / triangles | 4,114,444 / 8,234,708 |
| Replaced old cap faces / added cap points | 275 / 8,125 |
| Open / nonmanifold / inconsistently oriented edges | 0 / 0 / 0 |
| Zero-area triangles / complete intersection pairs | 0 / 0 |
| Vertex manifold / one connected material body | passed / passed |
| Actual 3MF coordinate and index readback | exact |

The unchanged whole-surface checker, including its literal predicate and shell
controls, runs over the entire new surface. The actual head-study 3MF SHA-256 is
`de0749d0f03075aec97cf5a291813ce233a00eecc5b80df3ac36c14b388e28e2`.
It has neither supports nor a machine/material/exposure profile. It does not
replace the earlier supported printing-study assembly.

The complete correspondence is the identity outside this cap and the preceding
independently checked cap graph correspondence inside it. Its composed bound is
**0.00964321537478613 nominal mm relative to the frozen hypothesis**. It is not
an acquired-scan accuracy or physical calibration result. The cap is still an
assumed construction plane with unaccepted physical datum, as documented in
the [cap source admission](../935-cap-graph-admission-20261107/README.md).

## Upstream cavity admission before meshing

The first region contains every original tetrahedron incident to any of the
277 original cap contour vertices: 808 cells. Its boundary has two pinched
edges, so it is refused before native tetrahedralization. Complete parent-edge
incidence adds exactly two cells. The resulting 810-cell region has correctly
paired edges and no intersections, but two pinched vertices.

Native libigl and the existing independent corner-graph fan implementation
agree on those vertices. Their complete parent stars add 15 cells. The final
825-cell region passes closure, orientation, vertex manifoldness, complete
intersections, one-material-body classification and actual 3MF readback. These
are monotone source-topology closures, not alternative mesh parameter trials.

Separate audit adapters independently recover the exact selected cell IDs:
they reconstruct the original pinched edges, rescan every parent cell for
their incidence, reconstruct the vertex fans, and rescan every parent cell for
those stars. All subsequent quality, source and exact volume computations are
byte-identical to the original audit implementation, apart from report schema.
Both zero-context patches replay to the executed source bytes.

Every one of the final 158 internal-interface faces is rejoined against all
12,952,857 actual parent cells: exactly one selected and one retained exterior
cell use it, with opposite orientation. All other cavity outer faces are
literal parent head faces or the checked refined cap. No numerical interface
is described as a measured mechanical attachment or physical passage.

| Final cavity boundary family | Faces | Faces forcing tet q below 0.01 |
|---|---:|---:|
| Unchanged internal numerical interface | 158 | 0 |
| Unchanged hypothesis head surface | 451 | 0 |
| Refined construction cap | 16,525 | 0 |

The exact fixed-face bound is necessary, not a promise of a successful mesh.
Seven unchanged outer/interface faces remain below the separate q_face=0.01
surface warning. The exact signed cap-volume change is approximately
**6.487893151589341e-13 nominal mm³**. Independently summing old and new oriented
cavity boundaries gives exactly this same rational difference. This is not a
new full-volume partition proof.

## One native trial and independent refusal

The existing pinned Gmsh 4.12.1 recipe and optimization-disabled wrapper run
unchanged: algorithm 10, one thread, 2.0 nominal mm fixed background size,
no optimization, no boundary coarsening. The same actual path first meshes a
cube. Independent source/facet checks and exact rational determinant summation
prove its unit volume and positive cells. The options are witnessed at the
actual `generate(3)` call. No parameter sweep or paid compute is used.

The local trial produces 8,570 nodes and 19,232 tetrahedra. The native log has
no refusal, error or warning, including no `Meshing process terminated` message.
The separate interval/exact checker proves all cell signs positive, all source
points and prescribed boundary faces retained, all interior faces oppositely
paired and all nodes used. Two cell signs require exact rational fallback.
Actual MSH 4.1 binary export/re-import then joins every node label, coordinate,
tetrahedron and boundary triangle. These checks do not override failed quality.

| Local quality check | Original 825-cell region | Refused trial |
|---|---:|---:|
| Tetrahedra | 825 | 19,232 |
| Exact mean ratio below 0.01 | 173 | 2,612 |
| Frobenius condition at least 1e12 | 24 | 620 |
| Nonpositive native minSICN | 3 | 211 |

Original condition/native flags are traced subsets of the preceding complete
parent census. The trial is freshly classified over every cell. Every one of
its 19,232 mean-ratio cubes is evaluated exactly; every severe condition value
is exact. Native adverse values are retained, not clamped or dismissed as
rounding. Positive exact determinants are not reported as native shape success.
Cell conditioning is not a PDE condition number or a physical error estimate.
The independent every-cell metric controls exercise 960 classifications on
120 dyadic/threshold fixtures before the actual case.

Of the 620 severely conditioned trial cells, 584 have all four vertices
incident to the refined cap; the corresponding count is 205 of the 211 native
shape-refused cells. These are source-membership counts, not an exact
coplanarity or physical-anatomy claim. The trial adds only one interior volume
point. Its 2.0 nominal mm background size is approximately 24.47 times the
median refined-cap edge length (0.081735 nominal mm). These observations guide
the next proposal; they do not prove that sizing or coordinate conditioning is
the cause, or that either change will pass.

## Reproduction, evidence and remaining work

New source entry points take `--job PRIVATE_JOB.json --output NEW_DIRECTORY`:

- [Boundary construction](source/assemble_boundary.py) and
  [independent complete join](source/check_boundary_join.py).
- [Original cavity audit](source/audit_cap_cavity.py),
  [edge-star closure](source/close_cavity_edges.py),
  [vertex-star closure](source/close_cavity_vertices.py) and
  [complete remesh metric attribution](source/audit_remesh_metrics.py).
- [Edge-closed audit adapter](source/edge-closed-cavity-audit.diff) and
  [vertex-closed audit adapter](source/vertex-closed-cavity-audit.diff), applied
  to the original cavity audit with no numerical-kernel changes.

Existing meshing, interval/exact, condition, native export/readback, whole-surface
and vertex-fan helpers are reused without modification. All source, runtime,
actual inputs, commands and output identities are bound in the private plans.
[results.json](results.json) publishes curated scalar outcomes, source hashes,
terminal ledgers and the frozen private manifest. Proprietary geometry,
selectors, exact cell values, binary meshes and raw logs remain private.
Public command paths use `REPOSITORY`, `PRIVATE_CAPSULE` and `PRIVATE_ARTIFACTS`
placeholders; the private plans bind their actual paths and hashes.

Three portable tests cover source joins and tampering, full feature incidence,
and paired cavity faces versus duplicate orientation. Native/predicate/fan/cube
and metric controls also run through their actual runtime paths. The first
cube preparation guard used exact equality on a floating aggregate and stopped
before the local case. Its replacement checks the exact determinant sum, which
is exactly one; the original native cube did not need rerunning.

Local `make check` passed: 5,863 main tests, 421 skipped, including the three
new portable tests. All 16 numerical controller ledgers are terminal and their
owned children reaped. The 150-payload-file private capsule (462,302,504 bytes)
is frozen, with every payload rehashed after read-only permissions were applied.
Its manifest identity is published in [results.json](results.json).

Next, test a separately declared proposal generator with numerical coordinate
conditioning and boundary-aware sizing. It must restore **all prescribed world
boundary coordinate bits** and undergo independent world-coordinate volume,
quality, topology and native checks before any accepted integration. This is
not yet implemented or prepared. No rejected local tetrahedron enters the
current full volume; its 439 severe-condition and 83 native shape-refused cells
remain the current counts. No head field solve or functional metal release is
claimed. Specimen metrology, faithful editable CAD, hidden passages, correlated
loads, qualified alloy/machine/process, physical inspection and professional
engine validation remain open.

All work uses existing Mac runtimes, with bounded 600-second controllers and
4 GiB or 12 GiB sampled-child RSS limits. No new Vast resource or supplier
message is created: **$0 new paid compute**. The original $35 total, $30 compute
ceiling and $5 closure reserve remain unchanged. The earlier conservative
$15.67884277510534 allocation is not an invoice. Original scan, supported
printing master and existing full volume were rehashed unchanged.
