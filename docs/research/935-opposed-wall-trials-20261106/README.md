# Acquired opposed-skin wall trials — November 6, 2026

The original-scan reconstruction gains **216 exploratory walls / 432 inferred
triangles**. Complete parent geometry, source-facet prefix and every
earlier provenance channel survive actual full OBJ/NPZ readback. The resulting
2,405,669-triangle surface passes whole native intersections, indexed duplicates,
degeneracy, edge incidence/winding and every used vertex fan. It remains open:
**95,949 boundary edges / 1,463 walks**, with ten anatomically unaccepted
components. It is not a faithful complete head, functional solid or printing job.

The [scalar results](results.json) bind the actual sources, immutable parent
helpers, original scan, admission, rejected initial output, corrected output,
Kali replay and frozen private capsule. Private geometry, raw face/corner IDs,
connection metadata and correspondence remain outside Git.

## Requirement and upstream admission

Continue the [previous source-surface reconstruction](../935-untried-acquired-pairs-20261106/README.md)
with the owner's documented-assumption permission, before editable solid,
physics or manufacturing admission. The upstream independent read-only census
retains 217 pairs on 65 walks. It excludes all 1,488 historical attempted pair
identities, inferred owner normals and unchanged small whole-loop proposals.
That census explicitly grants no constructor admission.

This increment tests a separate possible **material-side wall** between opposed
acquired skins. It assumes original acquired owner windings are outward solely
for this exploratory construction. This is not measured physical orientation or
anatomical classification. Same-facing gap caps and opposed-skin walls have
different geometrical conditions; the former's failed thresholds are not relaxed.

All midpoint/crossed-endpoint distances stay at most 0.5 nominal mm. Tangents
must have dot product at most −0.8; acquired owner normals must be opposed
with dot product at most −0.8. Both crossed gap vectors must point towards the
negative-normal side of both owners, also at most −0.8. The two outward edge
binormals must align at least 0.8, and each forward wall triangle must align
at least 0.8 with its corresponding binormal. Numerical units remain assumed;
none of these bounds is a specimen tolerance.

## Complete source owners and incident masks

[Admission](source/admit_opposed_walls.py) recovers all 434 selected edges from
their original acquired owner facets and directed raw vertex corners. Coincident
distinct original vertices are not welded or identified by coordinate hashes.
It checks kind-0 owners, actual acquired origins, the exact selected walk,
positive original corner fans and both independently verified diagonal flags.
Every original incident face at all four corners belongs to the local mask.

[The separate checker](source/verify_wall_inputs.py) independently reindexes the
complete directed parent edge table, verifies each edge's only owner, recovers
its raw key/normal and recomputes every full incident mask by Boolean face
membership. It does not import the admission producer or its sorted-corner
index. All 217 masks and 434 owners pass. The existing scalar opposed-geometry
and raw-identity checkers are unchanged, hash-bound dependencies.

Nine native/mask/incidence controls cover positive border incidence, reversed
winding, duplicate patches, an already interior parent edge, native-valid
planar local geometry and fans, a complete mask, a missing row, a duplicated row
and a newly incident face invalidating an old mask. Eight opposed-geometry and
five raw-identity controls pass as well. Native planar walls are accepted without
requiring nonzero tetrahedron volume. Winding reversal and the opposite gap side
remain meaningful refusals under the explicit hypothesis.

## Actual construction and the preserved provenance failure

Both original-point forward diagonals are tried for all 217 pairs, with complete
admitted incident haloes, native local intersection/zero-area predicates and
corner fans. All 434 local diagonal trials pass. Deterministic area selection
chooses one diagonal per pair; the cumulative edge budget refuses one complete
wall because an additional use would conflict. No alternate reselection,
original-point movement or parent-face removal follows. The composite retains
216 walls / 432 triangles.

The [first constructor](source/build_opposed_walls.py) accidentally assigns new
faces the already occupied surface kind 6. Whole native intersections pass, but
the independent provenance inspector refuses that output before admission.
The failed source, composite, logs and execution ledger remain immutable.
[Version 2](source/build_opposed_walls_v2.py) changes exactly that one assignment
from 6 to the reserved kind 7. Complete masks/owners and native controls are
replayed with the corrected source before construction is rerun.

All original coordinates, triangles, OBJ bytes and every other metadata array
are exactly identical between those two proposals. Only the 432 new kind values
change. New wall ancestry uses separate pair, parent-walk and immediate-parent
fields, legacy labels starting at 60,000,000 and unclosed boundary origin 8.
All earlier source, omission, cap, strip and immediate-parent channels remain
exact; their numeric labels cannot be confused with the new wall namespace.

## Whole-candidate verification and source support

[The new inspector](source/inspect_opposed_walls.py), a versioned descendant of
the unchanged previous inspector, verifies actual complete saved OBJ/NPZ bytes.
Whole native predicates report zero intersections and zero excluded degenerate
faces. Edge incidence/winding, duplicate faces and all used vertex fans have
zero conflicts. Eighteen unused vertices are retained explicitly.

All 66,096 degree-16 samples on every new triangle remain below the predeclared
0.25 nominal-mm raw-source support bound; the maximum is **0.2228887**. The
219,476 previous source probes and 46,184 omission probes are recomputed and
nonincreasing pointwise, with the original 1e−8 arithmetic guard. No whole wall
requires removal, so the [whole-wall filter](source/filter_opposed_walls.py) is
exercised on synthetic ancestry/refusal tests only, not invoked on this candidate.

The full forward cohort still reaches **49.7737 nominal mm**, including previous
provisional component exclusions. The omission cohort reaches 0.2042844; the
separate 100,000-point reverse random sample reaches 0.2004010. Random reverse
sampling cannot replace the complete inherited forward cohort. These finite
distances are not Hausdorff bounds, missing-surface truth, physical calibration
or manufacturing tolerances.

The walls consume 442 old acquired edges and leave 312 new cross-edges, for a
net reduction of **130 open edges**. Walk count rises by 151 through partial-band
subdivision; this does not mean that 216 entire holes close. Original owner,
direction and origin are verified for every inherited boundary edge. Ten
components remain, including five single-facet components; the largest contains
2,398,351 facets. Component size does not establish bare-head anatomy.

## Independent Kali replay and reproducibility

[The bounded stdin runner](source/run_streamed_replay.py) streams the unchanged
frozen checker and exactly **126,841,410 parent/candidate bytes** to Kali1 RAM.
Every payload is hash-checked. The existing trusted SSH identity is used without
agent forwarding or host-key bypass. Two CPUs, 4 GiB address space, a 110-second
remote deadline and a 120-second local deadline apply. No persistent payload
file or runtime package is installed on Kali's nearly full disk.

Kali1's Python 3.14.7 / NumPy 2.3.5 independently confirms the complete source
prefix/provenance, full edge incidence/winding, duplicates/degeneracy, 95,949
open edges and 18 unused vertices in **6.99 seconds**. Its peak RSS is
1,640,944 KiB. This limited Linux witness does not claim intersection or vertex
fan replay. The SSH child is reaped; actual remote completion is observed.

The Mac uses the unchanged isolated Python 3.12.13 / NumPy 2.5.4 / SciPy 1.18.1 /
OCP 7.9.3.1 runtime and separately hash-bound libigl 2.6.3 addon. Six generic
bounded groups and the Kali replay preserve six completed groups and the one
provenance stop. Every owned scientific/SSH child is reaped. The local groups
have a shared 600-second deadline, 4 GiB sampled child RSS bound and 4 GiB local
disk floor; the peak complete-audit sample is 3,151,648 KiB.

The frozen/rehashed private capsule contains **71 payload files / 393,572,083
bytes**, under manifest
`530ca269207b7174bf9b1fa1eba2df885bf0161868afc5f212b297801473e2ad`.
It includes both initial/corrected outputs, all sources and jobs, masks, local
trials/refusals, native proofs, distance witnesses, topology and complete logs.
Executed parents and frozen evidence are not edited. Public sources require
the private hash-bound jobs and native runtimes; public CI does not reconstruct
the private head from absent scan bytes.

## Validation and remaining full objective

[Synthetic contract tests](../../../tests/test_935_opposed_wall_trials.py)
exercise independent complete masks, missing/duplicated/unrelated masks,
newly incident faces, old/new label separation, whole-wall filtering and
incidence/winding/origin refusal. They also bind public source/helper hashes,
the versioned one-line provenance correction and false release gates. Exact-head
full native-Linux `make check` and publication status are recorded separately
on [PR #516](https://github.com/cluster2600/porscheparts/pull/516).

Qwen/CADAM remains the prescribed local auxiliary proposal service; no new
inference occurs here. PicoGK and acquired STEP/FreeCAD references retain their
editable geometry authority. This source-facet study does not create a complete
solid interchange model. Gmsh/OpenFOAM/CalculiX and Adamantine admission remain
separate; the inherited hypothetical Gmsh domain still has 996 failing minSICN
cells, and no new head physics is accepted or rerun on this open surface.

The objective still includes complete faithful editable head geometry,
admissible/correlated simulation and a qualified metal fabrication file.
Specimen identity, measured units/interfaces, hidden passages, operating loads,
machine/material/powder/support/toolpath qualification, physical metrology and
professional engine review remain open. **G0–G5, physical acceptance and
manufacturing authorisation remain false.** The next upstream audit must use
the changed boundary ancestry to distinguish genuinely new mixed-surface
openings from unchanged previously refused inputs before further construction.

There is no new Vast rental/spend, external AI scan transfer, supplier outreach,
merge, physical print or release. The owner's scan-on-Vast permission and original
$35 total / $30 compute / $5 reserve persist. Current balance is not inferred.
