# 935 source-contact bridge study — November 6, 2026

Six explicitly inferred bridge triangles join six previously disconnected face
fans. Complete used-vertex inspection reduces the inherited non-manifold vertex
count from 48 to 42. The actual saved OBJ preserves all 1,248,924 coordinates
and all 2,401,792 preceding triangles, including the 52 earlier quarantine patch
facets. Nothing is moved, deleted or hidden by duplicating vertex indices.
The candidate now has 2,401,798 triangles. It remains an **open partial surface,
not a complete faithful head, admitted conservative surface or printable part**.

The [reviewed scalar receipt](results.json) binds six new executed sources,
five frozen helpers, private reports, full-source measurements and the private
capsule manifest. Source geometry, vertex IDs, correspondence maps, raw trials
and OBJ/NPZ artifacts remain outside Git. No functional catalogue release is
created by this study.

## Requirement and admission

This increment advances the used-vertex requirement in section 4 of the
[scan reconstruction workflow](../../architecture/scan-repair-workflow.md),
following the [quarantine-patch study](../935-quarantine-patches-20261106/README.md).
The [engineering architecture](../../architecture/README.md) and
[local-compute decision](../../decisions/0012-local-compute-gpu-last.md) retain
authority. PicoGK/STEP and the prescribed Qwen/CADAM, Gmsh, OpenFOAM, CalculiX
and Adamantine roles are unchanged. Local facet repair is upstream of complete
functional CAD and solver-domain admission; it does not replace that chain.

The immutable input passes full intersection, degeneracy, edge-incidence and
duplicate-face checks, but has 48 non-manifold used vertices. A literal native
control demonstrates why splitting vertex indices is insufficient: two source
triangles sharing one point are not reported as a self-intersection until that
point is represented by separate coincident indices. Another control confirms
that a crossing beyond a shared vertex is detected. Index separation is therefore
not used to claim a geometric repair or a passing manufacturing gate.

## Explicit contact-bridge hypothesis

At a contact between open face fans, an added triangle can reverse one incoming
boundary edge from one fan and one outgoing edge from another. Its third edge
becomes an explicitly inferred boundary segment. This proposes a small missing
surface between neighbouring acquired facets. It does not establish the physical
role of the opening, casting geometry or internal passages.

All fan orders are retained. A contact involving a closed fan cannot be joined
by this boundary-addition method and is refused. The fixed experimental screen
requires a triangle bounding-box diagonal at most 3 nominal mm, positive area,
and a **signed** normal dot product at least 0.8 against each of its two source
neighbours. These are local trial parameters, not physical tolerances. No
threshold is relaxed after inspecting results.

Independent inspection reconstructs fan counts from the actual source halo,
checks the exact boundary directions and contact anchor, requires all contact
fans to join and no other used-vertex fan count to increase, then runs native
intersection predicates on the halo. Selection uses minimum added area among
passing proposals, followed by lexicographic source indices. Global conflicts
remove every implicated contact's complete bridge set, with no automatic
alternate selection or source-face deletion.

| Stage | Outcome |
|---|---|
| Complete contact population | 48: 23 involve a closed fan; 25 admit boundary-addition proposals |
| Enumerated orders | 54 proposals; 41 fail the fixed signed-normal screen |
| Independent local inspection | 13 proposals pass, covering eight selected contacts |
| First complete candidate | Zero detected intersections; one conflicting edge implicates two contacts |
| Whole-contact rejection | Both implicated sets removed; failed composite retained |
| Final complete candidate | Six bridge triangles; zero intersection pairs, excluded degenerates, duplicate faces or edge conflicts |
| Whole used-vertex graph | Exactly six contacts join; all other fan counts unchanged; 42 remain non-manifold |

The saved full OBJ is parsed by the preceding frozen independent OBJ reader and
compared to the canonical source plus checked masks. NPZ face-level provenance
retains original source/fragment and quarantine-patch links; `source_contact_vertex_ids`
identifies new contact faces. `inferred_surface_kind` distinguishes original
retained geometry (0), preceding quarantine patches (1) and contact bridges (2).
New contact faces also use a disjoint private label namespace in the legacy
`source_patch_curve_ids` channel; those labels do not identify physical curves.

## Complete boundary accounting and deviations

The candidate has 98,762 boundary edges in 941 freshly enumerated fan-aware
walks. Twelve previous boundary segments become internal: eight from raw
acquisition openings and four exposed by quarantined source facets. Six new
segments belong to the bridges. All other edges and directions are checked
against an independent complete boundary-change mask.

New boundary origin kind **4** identifies inferred bridge edges; kinds 1, 2 and
3 retain acquisition, quarantine and declared-cut provenance. The current edge
counts are 97,864 / 166 / 726 / 6 respectively. Raw-curve ancestor links and a
fresh private review row for every walk remain traceable. Equal total walk counts
before and after repair do not imply unchanged contour identities: local fan
joining can split or merge walks. Every physical classification remains
unreviewed and every closure-authority field remains false.

Both deviation directions are rechecked against the original scan. The same
219,476 raw-source probes include 100,000 area-weighted points, all 99,876 raw
boundary vertices and 19,600 quarantined-facet probes. No source-probe distance
increases relative to the preceding candidate, under the unchanged arithmetic
guard. The raw-source random sampled maximum remains 49.6927 nominal mm,
including provisionally excluded attached components; that component separation
is still a hypothesis.

All six new bridges receive their own 1,000 area-weighted probes, centroids and
vertices: 6,024 probes in total, with a sampled maximum source distance of
0.08393 nominal mm. Whole-candidate area sampling and all current boundary
vertices are checked separately. The previous 27-patch deviation witnesses
remain applicable because their facets and the raw target are unchanged.
The owner-declared project unit convention is one OBJ unit per millimetre.
These sampled distances are **not Hausdorff bounds, independent physical
calibration, dimensional certification or manufacturing tolerances**.

## Reproducibility and unfinished work

The [executed sources](source/) and aggregate receipt publish no raw geometry.
Six bounded execution groups completed with all owned children reaped. Private
ledgers pin concrete commands, inputs, source hashes, expected outputs and stop
rules. Replay each with the frozen
`run_local_delivery.py --plan <ledger> --output <fresh-directory>`; preserve every
failed attempt and never edit a frozen source or result. The controls use the
isolated Python 3.12.13 / NumPy 2.5.4 / SciPy 1.18.1 / libigl 2.6.3 environment.
The existing base runtime and copied addon remain unchanged and are rehashed.
Each group has a 600-second shared wall limit, sampled 4-GiB child RSS limit and
4-GiB disk floor; RSS sampling is not an operating-system hard memory cap.

Nine synthetic adversarial tests cover two/three/closed fans, wrong/reversed
anchors and boundary directions, fixed size and signed-normal limits, predicate
rejection, full boundary-change masks and source/receipt consistency. Native
predicate execution is evidenced by the private full-resolution receipts;
public CI has no scan and checks synthetic/repository contracts only.

Forty-two contacts remain, including all 23 closed-fan cases. Those are not
proof of scan damage or authorization to delete smaller source components.
Remaining open-fan contacts and the freshly attributed boundary walks need
further bounded reconstruction hypotheses and independent checks. Complete
interfaces, missing internal geometry, a closed faithful head, admissible meshes,
correlated engine physics, material/machine/process qualification and physical
inspection remain open. The inherited hypothetical Gmsh domain's 996 rejected
minSICN cells are not superseded by this surface study.

No new paid compute or Vast resource is created here. Scan transfer to Vast is
authorized for subsequent prepared tasks within the existing $35 total / $30
compute / $5 reserve budget. No external AI/CAD scan transfer, supplier outreach,
merge, print or physical/manufacturing release occurs. The full goal stays active.
