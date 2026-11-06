# 935 volume conditioning with preserved convex local domains

Two verified local topology passes reduce cells below diagnostic mean ratio
0.01 from **526,110 to 254,353 (51.654%)**, passing the unchanged relative
50% target. All 4,181,299 node coordinates and the complete oriented source
boundary remain exact. Every changed region has an independent local-domain
preservation proof; the complete volume passes cell-sign and face checks after
each pass. This admits the numerical preservation/relative-quality result,
not a field solver, functional head or metal build. The absolute shape gate
still fails and case-specific conditioning admission remains open.

Full source/input/output hashes, controls and numerical results are in
[results.json](results.json). The final private candidate is
`pass-002/construction/candidate.npz`, SHA-256
`233f7bd83072772fa0b92d0287f20cec3cf44c4988546be42addf5579630299e`.
It is a computational tetrahedral mesh, not a new printing or analytic CAD master.

## Admission and coverage before changing connectivity

The [preceding exclusion audit](../935-constrained-relocation-20261105/README.md)
shows why interior-node relocation cannot reach the target at fixed
connectivity. Native global optimization also reaches its bounded worker alarm.
This study instead considers closed degree-three edge stars in the already
checked raw Gmsh checkpoint. The inherited hypothetical surface, source scale,
closures, hidden-geometry and physical-interface limits are unchanged.

An initial sparse audit counts the global incidence of every edge touching any
bad source cell. It recovers 291,073 closed three-vertex-link cavities, with an
optimistic coverage of 297,725 bad cells. A separate algorithm sorts **all
79,503,456 edge occurrences** into 21,542,559 distinct edges, reproducing every
selected-edge count, cavity key, incident-cell row and link. Controls include
an absent edge, an open fan, a closed cycle and counting across the 50,000-cell
chunk boundary. No coordinates or cells change during these audits.

Each proposed 3-to-2 replacement must satisfy strict convex supporting-face
tests, preserve its oriented boundary chain exactly, introduce a previously
absent central face, improve the local bad-cell count, retain the local minimum
quality and not increase the 0.0001 bin. All sign-ambiguous cases use exact
fractions of stored coordinates. Of the initial cavities, 269,118 meet these
conditions. Deterministic packing chooses descending integer repair gain then
ascending edge key, requiring disjoint old cells within a pass and distinct
new central faces. The first pack has 251,367 replacements and predicted repair
gain 253,811, below the cumulative target by 9,244 cells.

## Bounded iteration and independent preservation

Before the first edit, the plan declares at most three passes, stopping at the
original 50% target, no admissible improvements or the resource budget. The
original 526,110-cell denominator is retained across passes. Intermediate
geometry must pass independent checks before supplying another cavity rebuild;
the target is not reset to a smaller problem. No iteration-count sweep is run.

The producer keeps every coordinate and source boundary index unchanged,
removes only the selected disjoint triples, and inserts their two-cell
replacements. An independent verifier uses a different geometric criterion:
the removed edge must pierce the strict interior of the new equatorial
triangle. Certified endpoint-side and barycentric numerator signs establish
that the old three-cell fan and new two-cell pair partition the same convex
bipyramid. It also checks the exact source-to-candidate cell mapping and every
unaffected cell. Convex, concave, coplanar, forged-orientation, overlapping-cell
and duplicate-new-face controls are retained across the producer/verifiers.

The separate frozen [whole-volume inspector](../935-unoptimized-volume-20261105/source/inspect_interval_volume.py)
then checks every cell, source coordinate, complete oriented boundary and
internal face pair. Only after both local and global checks pass is the next
intermediate used. The second rebuild admits another 17,821 disjoint
replacements and repairs 17,946 more bad cells. The target is reached after
two passes, so no third pass is executed.

| Metric | Original raw checkpoint | First checked pass | Second checked pass |
|---|---:|---:|---:|
| Tetrahedra | 13,250,576 | 12,999,209 | 12,981,388 |
| Below mean ratio 0.01 | 526,110 | 272,299 | 254,353 |
| Below 0.0001 | 149,190 | 48,688 | 36,838 |
| Minimum mean ratio | 2.91459e-12 | 9.10427e-12 | 1.29101e-11 |
| Cumulative relative target | Not passed | Not passed | Passed |
| Absolute shape gate | Not passed | Not passed | Not passed |

The final inspector proves 12,981,245 signs positive by outward intervals and
143 by exact fractions. All 21,853,547 internal face pairs have opposite
orientation; all 8,218,458 boundary faces and source vertices remain exact.
Relative volume difference from the frozen source is 1.33e-15. Local domain
proofs compose across the two passes, including where later cavities contain
earlier replacement cells. The whole-volume inspector does not exhaustively
test every tetrahedron pair; the independent local proofs certify the changed
regions. Neither scope establishes physical specimen identity.

## Phase ledger and release boundary

| Phase | Concrete source / inputs | Result |
|---|---|---|
| Input admission | Frozen raw arrays and complete interval/face report | Positive consistent hypothetical domain; shape failure retained |
| Sparse cavity audit | `audit_cavity_coverage.py`, all bad-cell edges | Optimistic initial topology coverage above target |
| Independent incidence | `verify_global_incidence.py`, every source edge | Every cavity and incidence count reproduced |
| Local feasibility | `assess_initial_cavities.py`, certified signs and global face queries | Convexity, topology, quality and packing controls pass |
| First construction | `apply_initial_pass.py`, frozen packed proposal | Intermediate exported, cumulative target still pending |
| First domain proof | `verify_local_domains.py`, source/proposal/candidate | Every changed convex region and unaffected cell preserved |
| Rebuild and continuation | `construct_iterated_pass.py`, checked intermediate | Second packed pass exported; no node motion |
| Iterated domain proof | `verify_iterated_domains.py`, parent inspection and mapping | Every second-pass domain preserved |
| Whole-volume admission | Frozen independent inspector after each pass | All cells and faces pass; relative target reached |
| Orchestration | `run_local_continuation.py`, original denominator and bounded stages | Stops after pass two; absolute/physical gates remain open |
| Native solver / process admission | Conditioned candidate plus case controls, loads, materials and process data | Still pending |

All eight sources provide `--help`. Exact arguments, runtime and commands are
retained privately. Use Python 3.12.11 and NumPy 2.5.4 on arm64 with the frozen
scientific site on `PYTHONPATH`; this increment does not invoke a native Gmsh
optimizer. The raw parent and its tool authority remain documented. Source
hashes bind reused numerical primitives and independent inspectors. This is
the A-CAE verification path within the existing
[architecture](../../architecture/README.md) and
[local-compute decision](../../decisions/0012-local-compute-gpu-last.md).

Workers have 600-second kernel alarms. The retained controller enforces wall
time, 40 GiB sampled RSS and 4 GiB free disk, and terminates/reaps only its own
children. Continuation has a further 900-second wall budget and a maximum of
three total passes. All actual task processes are terminal. The private
`935-local-cavity-20261105-001` capsule contains 72 indexed files, 1,552,424,943
bytes excluding its manifest, all rehashed and made read-only. Its manifest
SHA-256 is `2ed59fd27b26539a1fadcf2b8ac0585bed065fc88af6123333184b5baf9c7629`.
Only sources and aggregate receipts enter Git.

The original scan, raw MSH/NPZ, numerical source surface and printing-master
3MF are freshly rehashed unchanged. No new print/support/contour job, analytic
head CAD master, native solver export, field solution, paid resource or supplier
message is produced. Remaining very flat cells require separate numerical
conditioning and case-specific admission. Functional interfaces, operating
data and calibrated metal-process/physical qualification remain separate gates.
The complete engineering goal remains active.
