# Delaunay trial and first-pass saved-file audit

**The volume is rejected.** The saved-file first pass measured **73,924 tetrahedra with SICN < 0.1**, including **one nonpositive SICN** (minimum **−9.287625427659782e−17**). The original raw trial and its separate read-only audit both reached their deadlines. The audit's final reopen identity proof did not finish, so this is a preserved partial audit, not a completed saved-readback acceptance.

| Stopped operation | Recorded outcome |
| --- | --- |
| Raw Delaunay: Algorithm3D=1, Optimize=0, OptimizeNetgen=0 | Outer RC2 / worker −9; 300.401592625 s native window, 301.330048542 s outer; stopped while auditing tetrahedra after exporting the MSH. Its worker checkpoint contains no completed tetrahedral metrics, arrays or incidence proof. |
| Separate saved-MSH read-only audit | Outer RC2 / worker −9; 120.139321750 s controller, 120.235071417 s outer; first-pass audit and checkpoint completed, then stopped during the additional reopen stage. Final reopened-array comparison and terminal input recheck/completion were not saved. |

Both operations requested two software threads, sampled 8 GiB RSS and 1 GiB output stops. Their 300/120 s acceptance budgets include startup; cleanup can extend elapsed time. Observed RSS summaries are not certified peaks or hard OS RAM/CPU/disk quotas. There was no automatic retry or optimizer call. Runtime identity is the pinned macOS ARM64 Python 3.10.11 / NumPy 2.0.2 / Gmsh 4.15.2 route.

## What the first pass actually saved

The exact [partial report](reports/readback-report.json), SHA256 `1888c07cbf09931790a400e86a72d5d0cdc2ac35df4d54031380e02f0e7614eb`, retains status `reading_saved_mesh` and stage `reopening_saved_file_for_tagged_array_identity`. Its unchanged audit helpers computed complete distributions over **3,961,773 tetrahedra**, **1,104,778 referenced nodes**, **871,731 fixed surface nodes** and **233,047 referenced interior nodes**, with zero orphans.

| Full-array quantity | Minimum | Nonpositive | Count |
| --- | ---: | ---: | ---: |
| Native minimum Jacobian | 2.7755575615628914e−17 | 0 | 3,961,773 |
| Native volume (mm³) | 4.625929269271485e−18 | 0 | 3,961,773 |
| Native SICN | −9.287625427659782e−17 | 1 | 3,961,773 |
| Independent signed volume (mm³) | 4.625929269271485e−18 | 0 | 3,961,773 |

The negative SICN is retained as measured; positive Jacobian and signed-volume observations do not override the SICN ≥ 0.1 gate. These are two different tetrahedralizations: the earlier [HXT rejection](../atomic-cavity-plane-clip-cap-assembly-volume/) had 285,573 below-threshold cells among 2,989,608. This count comparison is not convergence, optimizer efficacy or proof of a repair.

The first pass saved exact source coordinates and oriented surface connectivity, fixed-coordinate bit identity, the complete **1,743,878-triangle** tetrahedral exterior, **zero nonmanifold volume faces**, and opposite orientation on all **7,051,607 internal faces**. Its four sorted tagged coordinate/node/tetra/connectivity digests are complete. Classification measured all fixed nodes on the surface and all 233,047 interior nodes at dimension 3, with no curve/surface periodic mapping. The summed independent volume is **915453.1236217882 mm³**, relative bookkeeping error **1.1102230246251565e−16** against 915453.1236217883 mm³. The 1e−6 bound is numerical bookkeeping, not a manufacturing tolerance.

Those completed first-pass checks are credited from the reviewed `audit_after` call and its checkpoint. No terminal `saved_file_reopen_array_identity_exact`, final `bound_inputs_unchanged`, completed-audit status or volume-admission flag is fabricated. Root's separate before/after input checks cover all 95 audit-child pins and three runtime identities; they do not substitute for the unfinished native reopen comparison. The [independent stopped-result review](reviews/readback-result-peer.json) verifies the six-file closure and saved associations without parsing or replaying the mesh.

## Source and evidence provenance

The exact executed [raw source](sources/delaunay/mesh_assembled_delaunay.py) is `a3268687edc90b0149775cf5d80a89df82175cc982bbf5d7184b6ea8935be8a4`. Its [four-literal delta](sources/delaunay/source-delta.json) from the existing HXT source changes only the docstring, output directory, Algorithm3D 10→1 and generation-stage label; the controller logic is unchanged. The prior twelve lifecycle mocks are inherited evidence, not a new Delaunay test. The raw trial's exact child explicitly authorized this separate experiment using unchanged surface evidence; the old HXT admission wording is not blanket launch authority.

The exact read-only [reader](sources/readback/reader.py) and [runner](sources/readback/run_readback.py) preserve source/admission hashes, selected runtime identities, owned process-group stop/wait, nonraising SIGTERM handling, handler restoration, remaining-budget timer and synchronous deadline refusal. The thirteen [small mocked guard cases](tests/readback-guards.json) passed once; ten prior methods are unchanged, and three cover active/exited output overruns and 8 GiB RSS. These mocks perform no scientific or mesh query. The reader selects only the unchanged `classifications`, `array_identity` and `audit_after` functions from [the existing helper](../atomic-cavity-volume-followup/sources/mesh_atomic_postexport_002.py), SHA256 `28746e14a041db464c3a41b732f1fc3e9ad9fd6ce96e886f728e5409d6ea0e36`; no optimizer setup or worker is selected.

The shared [four project dependencies and predecessor source](../atomic-cavity-plane-clip-cap-assembly-volume/sources/hxt/) are linked rather than duplicated. `original-records.json` lists their exact hashes. This selected evidence capsule is **not a standalone runnable workspace**: it omits geometry, installed runtime, upstream libraries and much parent evidence; original tree paths and separately reviewed launch bindings are required. Historical HELD/null/false metadata and the original root inventory-count understatement remain preserved; root review002 records the explicit correction before the actual child.

`original-records.json` distinguishes byte-exact copies from selected JSON projections, records original/public hashes and explicit omissions, and preserves every selected contract input-pin value. Runtime path keys/values become explicit role identifiers. Native argv, personal host paths and observer time series are omitted; private native logs are represented by original hashes, never rewritten as exact copies. The existing verifier checks this capsule's bytes and complete selected-file closure only. Run `python3 -B verify.py`; a seal is not a geometry, scientific or physics test.

## Geometry, rights and limits

The unchanged assembled source is `9d62eac6e2cd7b6a9ecb4a7ea5b632685820369b5c4ede379acc34238f50d7b4` (871,731 vertices / 1,743,878 oriented triangles). The stopped Delaunay MSH is **249,628,334 bytes**, SHA256 `3dd7939f34c8246a813334b2f570b2408b590965734bdf3761866569290e3593`; no MSH body is included. The existing [assembled surface review ZIP](https://github.com/cluster2600/porscheparts/releases/download/untagged-3dc4679a17c16edf0fb4/962-bore95-plane0-assembled-unadmitted-review.zip) remains the same asset, SHA256 `8ba6fc5dca47f3a51bc6298f481aaa334ac1096608552a96159a1d4688f6a4d5`. This companion adds no asset or duplicate geometry download.

The scoped [surface distance evidence](../atomic-cavity-plane-clip-cap-assembly-distance-cgal/) compares against the original **analysis mesh**, not an OEM/factory reference. Its 0.0625 mm analysis budget is not an OEM tolerance. Whole source-surface identity includes the 38 fixed cap cells; the volume kernel does not separately remeasure their semantic policy. All **414 stronger Mesh_2 shape failures** remain unadmitted. Full semantic feature/channel/OEM truth, professional engineering approval, mesh convergence, thermal resolution, head PDE, strength/fatigue, material qualification, calibrated LPBF, physical testing and manufacturing authorization remain unestablished. No optimizer outcome or feasibility is claimed here.

Original project code and records retain the [project proprietary licence](LICENSE.project). Third-party software retains its own rights; no Gmsh/NumPy/runtime/header binaries, source archives, supplier data or raw scans are redistributed in this capsule.
