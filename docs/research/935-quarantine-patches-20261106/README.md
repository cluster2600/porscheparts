# 935 retained-source quarantine patch trials — November 6, 2026

Twenty-seven small inferred patches now replace part of the surface quarantined
by the intersection audit. The complete retained candidate contains 52 new
triangles and preserves its 2,401,740 input triangles and 1,248,924 coordinates
exactly. This is an open, partial reconstruction study. **It is not an admitted
conservative surface, closed head, functional CAD or printable metal part.**

The [scalar receipt](results.json) binds the executed sources, private reports,
runtime controls, failures, process exits and immutable private capsule. The
private OBJ and NPZ include the actual geometry and face-level provenance;
geometry, source indices and correspondence maps are excluded from Git.

## Requirement, workflow and upstream admission

This increment addresses masked local retriangulation in sections 3–4 of the
[scan reconstruction workflow](../../architecture/scan-repair-workflow.md),
within the [engineering architecture](../../architecture/README.md) and
[local-compute decision](../../decisions/0012-local-compute-gpu-last.md).
It consumes the
[retained boundary origin audit](../935-retained-boundaries-20261106/README.md)
and the [exact transition cuts](../935-source-transition-cuts-20261106/README.md).
The frozen original OBJ still has SHA-256
`4623d5d3b73fe3d03ca988a47543a8dd1be7834d3040e6f7efd1e1e95c766486`.

Before patch generation, full libigl/CGAL predicates found zero intersections
and zero excluded degenerate triangles in the exact retained input. That admits
bounded local surface trials only. All 59 quarantine-only walks were considered;
the 898 acquisition-only, six mixed-origin and five declared cut contours were
outside this experiment's closure mask. The 204 original quarantined facets and
180 original intersection pairs were rejoined into 33 coupled defect groups.
No opening was identified anatomically or accepted as a physical interface.

## Construction and independent acceptance

| Stage | Observed outcome |
|---|---|
| Exact source-contour screen | 52 admitted; five non-simple or zero exact projections and two self-contact walks refused |
| Native CGAL explicit-edge requests | All 52 constructors exited successfully; this did not grant geometric acceptance |
| Independent local inspection | 30 accepted; 13 folded/reversed/zero projected proposals and nine intersecting proposals rejected |
| First complete assembly | No intersections; two global edge conflicts implicated three patches |
| Fixed whole-patch conflict policy | All three implicated patches removed, preserving the failed first assembly |
| Filtered complete assembly | 27 patches, 52 inferred faces; zero intersections, excluded degenerates, duplicate faces or edge conflicts |
| Used-vertex inspection | 48 inherited non-manifold used vertices remain, with unchanged face-fan counts |
| Remaining boundary | 98,768 open edges across 941 original walks; 106 quarantine edges closed |

The native constructor operates on exact source-face halos with point-contact
fans split into separate indices. The inspector restores original source vertex
identities before intersection predicates, preventing that temporary index split
from hiding source contact. Original coordinates, face coverage and winding,
the exact selected vertex/perimeter mask, complete disk topology, and exact
Fraction-based projected orientation and area are checked independently. No
normal or distance threshold was relaxed to rescue rejected trials.

A literal prism control independently verifies complete closure of one selected
opening while preserving a second opening. A request for an interior edge is
refused. Synthetic adversaries in
`tests/test_935_quarantine_patches.py` additionally reject moved vertices, missing
or duplicate source faces, wrong-opening caps, incomplete or reversed patches,
folded projected disks, self-contact and invalid edge incidence.

The whole candidate's saved OBJ is parsed and rejoined to the immutable base
and accepted face masks. An independent full-resolution intersection pass,
edge/face checks and all-used-vertex graph then inspect the assembled candidate.
The narrower `source_preserving_surface_checks_passed` flag describes the edge,
face and intersection subset. It **does not** override
`conservative_surface_workflow_fully_admitted=false`, because 48 used vertices
still have multiple disconnected face fans.

## Bidirectional deviations and coverage limits

Distances use the owner-declared project convention of one OBJ unit per
millimetre. Independent physical calibration remains unverified. Maxima below
are sampled distances, **not Hausdorff bounds or manufacturing tolerances**.

| Probe population | Result in nominal mm |
|---|---|
| 100,000 area-weighted raw-source probes to retained candidate | p99 13.1694; sampled maximum 49.6927; 98.073% within 0.05 |
| All 99,876 raw boundary vertices to retained candidate | sampled maximum 49.7737 |
| 100,000 area-weighted candidate probes to raw source | sampled maximum 7.42e-14 |
| 27,158 explicit probes on every inferred patch | p95 0.03177; sampled maximum 0.08642; 98.870% within 0.05 |
| 19,600 probes on the 196 non-degenerate quarantined source facets | median decreases from 0.01249 before filling to 0.00687 after filling |

The large raw-source-to-candidate distances include the components provisionally
removed as attached hardware. Their separation is still a hypothesis; it is not
evidence that those omitted surfaces were erroneous. Reporting only the tiny
candidate-to-source error would conceal that asymmetry. All sampled raw-source
distances were checked pointwise against the unpatched retained input and did
not increase. The eight recorded zero-area original facets are excluded only
from the distance target; that exclusion does not add or remove candidate faces.
Each inferred patch has its own retained probes and nearest-source witnesses,
so its tiny surface area cannot make it disappear from whole-surface sampling.

## Runtime, reproducibility and private delivery

The executed Python/C++ sources are in [source](source/). The existing CGAL
native binary and its dynamic dependencies are pinned in the private job.
The published C++ file is the unchanged constructor reference, not a claim that
it was rebuilt in this trial. Python 3.12.13, NumPy 2.5.4, SciPy 1.18.1 and
libigl 2.6.3 run locally. A private copy of the existing libigl installation is
isolated from the frozen CAD runtime; no packages were downloaded or installed
into that runtime. Before/after input hashes are checked by phase controllers.

Nine recorded bounded executions completed with all owned children reaped.
Each uses a 600-second shared wall limit, a sampled 4-GiB child RSS limit and a
4-GiB disk floor. Sampling is not an operating-system hard memory limit.
Ledgers contain exact commands, input hashes, expected outputs and stop rules;
the receipt retains per-phase exit codes, elapsed time and sampled peak memory.
The saved private capsule also retains rejected native proposals, failed
composites, source masks and distance witnesses. See `private_capsule` in the
receipt for its manifest and byte counts.

Commands are replayed from those private phase ledgers with the frozen
`run_local_delivery.py --plan <ledger> --output <new-execution-directory>`.
Use a fresh output directory for every scientific attempt; never edit a frozen
input, source copy or result in place. Public CI exercises synthetic contracts
and scalar/hash consistency. It has no private scan and cannot rerun these
full-source measurements.

No new Vast resource was rented for this increment and no new paid compute was
used. The owner authorizes the scan on Vast for subsequent prepared jobs within
the existing budget. CADAM/Qwen remain auxiliary and local; PicoGK/STEP,
Gmsh, OpenFOAM, CalculiX and Adamantine retain their documented downstream roles.
This increment does not replace that suite or claim solver execution.

## Remaining work and release status

Thirty-two of 59 quarantine-only contours remain unresolved by this constructor
and acceptance policy. The 48 point-contact vertices and 941 remaining boundary
walks need further source-traceable reconstruction and hypothesis review.
Blindly filling acquisition or mixed-origin openings would invent head geometry.
Interface identity, internal passages, complete volume, mesh convergence, engine
loads, material/process qualification and manufacturing files remain separate
open requirements. This partial surface has no new functional catalogue release.
The full goal remains active; physical acceptance and printing authorization are
false.
