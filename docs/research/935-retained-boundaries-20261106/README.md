# Complete retained-boundary provenance and native review

This increment makes every remaining boundary of the retained 935 source
reference traceable. Its **98,874 directed boundary edges** comprise **97,872**
edges already open in the original acquisition, **276** edges exposed by removal
of quarantined source facets and the **726** previously verified local-cut
segments. Independent full-mesh reconstruction accounts for all of them; no
unexplained acquired-surface loss is accepted.

There are **968 oriented boundary walks** after separating local surface vertex
fans at unchanged coordinates. The private review delivery contains all of them:
**965 closed native wires and three independent-edge references** for walks
that revisit a coordinate. A 968-object FreeCAD document is saved, closed,
reopened, freshly exported and independently inspected against the actual
source edges. **No curve is filled; no face or solid is created.** This prepares
traceable repair/review work, not a complete head or manufacturing release.

[Aggregate receipts](results.json) bind the four executed sources, two reused
helpers, source inputs, whole-boundary proofs, actual terminal results and saved
native geometry. The private capsule `935-retained-boundaries-20261106-001` is
frozen read-only and rehashed: **1,990 payload files / 64,839,592 bytes**, manifest
`729e2e98997bee3b8b2a14069ddbd1cb12b160c1837e518b35cb6c49c03c6465`.
Coordinates, edge/face/curve IDs, the complete review queue, BREP and native
documents remain outside Git and external AI/CAD services.

## Exact input and scope

The input is the already verified
[retained reference after local cuts](../935-source-transition-cuts-20261106/README.md),
with **2,401,740 triangles**. Its mapped NPZ has SHA-256
`ebd1978f2b2ebef87e7aeb6be2571350c8c4edad9e078f996b9cb723b2d8e31b`.
Original scan contract
`4623d5d3b73fe3d03ca988a47543a8dd1be7834d3040e6f7efd1e1e95c766486`
and decoded arrays
`dd94c37117a1f1277a4f2b7f0bf0023e0d1858991b943f766cf447db319a101a`
remain unchanged. The original source admission/atlas plan is
`f26389c910ded839b94de910f495c0110a0fd103fc860af2b4a07e25139d5026`.

One source unit remains one owner-assumed nominal millimetre; this is not
measured physical calibration. The prior 0.75 nominal-mm stock planes and five
provisional geometric domains are inherited unchanged. Their anatomical
identity, functional interfaces and physical datums remain unaccepted.

The original raw scope still contains **99,876 open edges / 928 boundary
curves**, before quarantine and local separation. The retained 968 walks have a
different scope and fan convention. Their difference is not a count of new
physical holes. Original quarantine records stay in the unchanged acquisition;
this increment does not restore, discard further, repair or close any surface.

## Exhaustive edge origins and surface vertex fans

[The auditor](source/audit_retained_boundaries.py) enumerates every retained
edge and its owning triangle. For a boundary joining original nodes, it rejoins
the exact original edge and raw source-face uses. A one-use original edge is
labelled acquisition-origin. An additional raw use is allowed only when every
other source facet is explicitly quarantined. An unexplained missing
nonquarantine surface causes refusal. Boundaries between constructed nodes must
match the exact previously verified five-region section graph.

Global source vertex IDs alone can join two surfaces that touch only at a
point. For each boundary vertex, the auditor therefore computes separate local
face fans through shared two-use surface edges. Each resulting boundary fan
must have exactly one incoming and one outgoing edge. Complete directed walks
then cover every boundary edge once. There are **98,825 indexed boundary
vertices** and **98,874 boundary fan visits**; these extra visits do not move or
invent coordinates. The original source topology remains recorded separately.

[The independent checker](source/check_retained_boundaries.py) repeats a full
structured-pair edge census rather than the auditor's packed edge codes. It
builds each local face-link graph with dictionaries/BFS rather than sparse
connected components, checks the complete fan-partition bijection and every
directed walk, and independently queries original-facet incidence. The original
raw 928 curves, retained edge origins and links to the 83-chart source atlas are
also rejoined. Independent descriptor checks cover centroids, perimeter,
plane-normal length, reported plane residuals and repeated coordinate visits;
numerical affine rank and bounds diagonal remain producer review descriptors,
not independently certified cap-admission inputs. A closed indexed walk that jumps
between separate point-contact fans is refused.

| Review provenance family | Boundary walks |
|---|---:|
| Acquisition-origin edges only | 898 |
| Quarantine-exposed edges only | 59 |
| Mixed acquisition/quarantine edges | 6 |
| Previously declared local cut | 5 |
| Total | 968 |

These are provenance classes, not accepted physical roles. An acquisition
boundary can represent interrupted coverage, a passage, separate hardware or
another unresolved condition. A quarantine-only contour is a traceable source
repair target, not automatic permission for a cap.

## Review geometry and native objects

The private CSV/JSON queue contains each ordered walk, origin counts, raw
acquisition-curve IDs, original source-atlas chart indices, perimeter and fitted
contour-plane descriptors. Eight contours have numerical affine rank two and
960 have rank three. Rank or a least-squares residual does not identify a
machined plane, physical tolerance or functional opening. Collinear/point-like
contours cannot define a plane. Mutual curve intersections and full geometric
simplicity have not been exhaustively certified.

Three walks (private indices 0429, 0856 and 0920) revisit a source coordinate.
[Native construction/readback](source/native_boundary_review.py) represents
these as **independent directed edges**, retaining the contact and fan evidence
without pretending to create a simple native wire. The other 965 walks become
closed three-dimensional native wires. A nonplanar boundary is never converted
into a planar face. All 98,874 original/constructed directed source segments are
represented exactly once in the intended topology.

Separate native preflight controls preserve a nonplanar wire without a face,
preserve a self-contact walk as independent edges, refuse a reversed source
walk, and refuse an original coordinate moved by `1e-9` nominal mm even though
that is below the looser constructed-node guard. Original coordinates require
**zero readback error**; only the previously constructed cut nodes use the
unchanged `1e-8` nominal-mm arithmetic guard. This is not physical metrology.

[The FreeCAD author/exporter](source/create_boundary_document.py) creates
`retained-boundary-review.FCStd` with 968 individually indexed reference
objects. Each includes source hashes, edge-origin counts, original atlas-chart
links, raw acquisition-curve links, representation, an unreviewed physical role
and false closure/manufacturing flags. Review notes remain empty. These fields
provide a place for evidence-backed review; they do not authorise closing a
port or printing a part.

The **9,633,339-byte** document is saved, closed, reopened, then a fresh process
exports every actual stored shape. Independent inspection rechecks all 968
exports: **98,874 edges, 98,927 native vertex objects, 965 wires, zero faces and
zero solids**. The extra native vertices come from the three deliberately
independent edge sets. Original-coordinate error is zero; maximum constructed
cut-node error is `5.154374172525247e-13` nominal mm, below the unchanged arithmetic
guard. No proximity sewing, tolerance sweep or source-coordinate adjustment is
performed. Native validity is not physical or manufacturing qualification.

## Execution and replay

The existing isolated Python 3.12.13/OCP 7.9.3.1 runtime remains unchanged under
software manifest
`d7879b23d83988901358bee60ecfbd3e3372c975051aa4ac1ef328614b4648f7`.
NumPy/SciPy perform the whole-surface audit; FreeCAD 1.1.4 runs in the existing
local-only outbound sandbox. No dependency installation or new paid resource
is needed. The original $35/$30/$5 budget/reserve remains unchanged; no current
provider credit or invoice is inferred from the earlier historical snapshots.

| Phase | Verified outcome |
|---|---|
| B0 | Current retained-surface proof and exact acquisition/fragment/role/atlas inputs admitted |
| B1 | Complete 98,874-edge source attribution and 968 fan-aware walks |
| B2 | Independent full edge census, local fan links, raw origins, descriptors and chart links |
| B3 | Actual native controls, all source curves, saved FreeCAD shapes and separate source readback |
| B4 | English executed sources, hashes, aggregate receipts and synthetic verification published |

All concrete ledgers precede their executions. The reused
[bounded controller](../935-source-cut-admission-20261106/source/run_local_delivery.py)
records actual exits, sampled RSS and child reaping with a 600-second shared
wall limit per ledger, 4-GiB child RSS and 4-GiB disk floor. Source audit takes
4.219 seconds; independent whole-source inspection 12.061 seconds (sampled peak
2,006,864 KiB RSS). Native construction takes 2.125 seconds and independent
readback 3.163 seconds. Native document creation/reopening takes 10.791 seconds,
fresh export 5.101 seconds and actual-saved-shape reinspection 3.789 seconds.
These are local terminal observations, not cloud/GPU speedup claims. Every
owned child is reaped.

Replay needs the hash-bound private acquisition, retained reference, fragment
maps, source roles, atlas and admitted-region inputs. Use new private output
directories; public summaries cannot recreate private geometry:

```sh
python -B source/audit_retained_boundaries.py --job PRIVATE/source-job.json --output NEW_AUDIT
python -B source/check_retained_boundaries.py --job PRIVATE/source-job.json --built NEW_AUDIT --output NEW_PROOF
python -B source/native_boundary_review.py --job PRIVATE/native-job.json --mode build --output NEW_NATIVE
python -B source/native_boundary_review.py --job PRIVATE/native-job.json --mode check --built NEW_NATIVE --output NEW_NATIVE_CHECK
python -m unittest discover -s tests -p test_935_retained_boundary_origins.py -v
```

Execute native controls before construction and the separate private sandboxed
document/export/readback ledgers before accepting native delivery. Synthetic
tests cover shared square/point-contact topology, fan merging, missing edges,
walks crossing between fans, false closure authority, original versus quarantine
provenance, unexplained source loss and degenerate plane descriptors. They need
no private scan or OCCT runtime. A ninth test binds public receipts to executed
source hashes, the complete saved boundary set and false release flags.
Repository CI is separate from engineering acceptance.

## Next reconstruction and release boundary

The 59 quarantine-only contours and six mixed contours now have exact source
facets and admitted neighbour-chart links for a separate repair-admission
study. Any inferred patch must retain its source mask and assumptions and pass
deviation, topology/intersection and independent checks before further use.
The 898 acquisition-only contours require physical-role/coverage review; a
functional passage must not be sealed merely because its boundary is closed.

This remains the acquired-reference STEP/FreeCAD branch in the
[engineering architecture](../../architecture/README.md) and
[scan workflow](../../architecture/scan-repair-workflow.md). PicoGK remains the
new-engine-geometry route; Qwen/CADAM remain auxiliary proposal tools, and Gmsh,
OpenFOAM, CalculiX and Adamantine retain their defined roles. No new engine
volume is admitted by a boundary review document. The inherited hypothetical
domain still fails 996 native Gmsh minSICN cells.

Complete faithful head-solid reconstruction, accepted specimen identity,
metrology/interfaces/component roles, missing and hidden surfaces, admissible
meshes and correlated engine loads/physics, material/machine/powder/support/
toolpath qualification, physical build/inspection, professional review and
engine validation remain open. G0–G5 stay false and the full goal remains
active. No supplier message, physical print, merge or manufacturing release is
performed by this increment.
