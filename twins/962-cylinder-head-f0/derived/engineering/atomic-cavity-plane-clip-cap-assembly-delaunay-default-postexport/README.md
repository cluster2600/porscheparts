# Default-optimized Delaunay volume: rejected, independently read back

The saved volume **fails the unchanged minimum SICN >= 0.1 gate**. One default-force optimization returned, its element cache was refreshed, and the saved-file identity check completed. A separate read-only query confirmed **3,438 positive poor tetrahedra, zero nonpositive SICN values, and minimum SICN 0.000025872861583260695**. No accepted volume or head physics result is claimed.

| Completed operation | Actual outcome |
|---|---|
| One `optimize('', force=True)`, then `rebuildElementCache(False)` | Native RC2 for quality rejection; no resource stop; 177.576841 s controller window; saved identity completed |
| Independent saved-MSH diagnosis | RC0; no stop; 25.641620 s; all four tagged arrays, three native quality hashes/distributions, signed volumes and reference counts match the single optimizer `worker.after` proof |

There are **3,802,217 tetrahedra, 1,104,778 mesh nodes, 233,047 referenced interior nodes and zero orphans**. All Jacobians, native volumes and independently calculated signed volumes are finite and positive. The signed-volume sum is 915,453.1236217882 mm³ (relative difference 1.1102230246251565e-16 from the source bookkeeping volume). These counts establish no thermal resolution or convergence.

The current poor-cell classification uses boundary tags 1..871731, including the 3,092 retained cap Steiner points:

| Boundary vertices per positive poor cell | Count |
|---|---:|
| 0 | 8 |
| 1 | 12 |
| 2 | 708 |
| 3 | 1,275 |
| 4 | 1,435 |

The [complete diagnosis](reports/diagnosis-report.json) retains one deterministic minimum `(SICN, tetrahedron_tag)` witness per nonempty class: five witnesses, not a statistical sample. The [result peer](reviews/diagnosis-result-peer.json) checked their JSON dyadic determinants without replaying the mesh or native runtime.

The 1,435 all-boundary poor cells cannot change through interior-node motion alone **while connectivity and boundary coordinates stay fixed**. This does not prove the boundary must change, or that the other 2,003 cells can be repaired. The report's `fixed_boundary_only_nonpositive_cells=true` is vacuous for its empty nonpositive-cell list; it does not classify positive poor cells.

The [earlier raw Delaunay evidence](../atomic-cavity-plane-clip-cap-assembly-delaunay/README.md) preserves its 300 s generation/audit stop and 120 s optional-reopen stop. Before this optimizer call, a fresh load compared all four arrays and classifications with that single completed first-pass audit. The earlier incomplete reader remains incomplete; there is no fabricated second worker proof.

The [exact optimizer worker](reports/optimizer-worker.json) records one optimizer return, one cache refresh, full after-metrics, exact boundary/internal-face checks and saved-file identity. The new direct diagnosis repeats arrays, native metrics, signed volumes, explicit surface coordinates/connectivity and node references. Full tetra-face incidence, internal orientation and entity classification remain **worker-only observations**. The minimum and poor-cell count improved, but the volume still fails 0.1. `Mesh.OptimizeThreshold=0.3` concerns Gmsh's optimizer criterion; it is not a replacement SICN admission threshold.

Declared limits were 1,200 s for the optimizer and 120 s for diagnosis, each two threads, sampled 8 GiB RSS and sampled 1 GiB output. Maximum observed RSS was 4,734,746,624 B (346 optimizer samples) and 2,325,315,584 B (50 diagnosis samples). These are sampled observations, not hard OS memory/CPU quotas or peak-RSS proofs. No separate OS PID-absence probe is claimed. The diagnosis generated, optimized, wrote or solved no mesh. No automatic retry or threshold relaxation occurred.

[Original records](original-records.json) enumerate every exact copy and explicit projection, complete original output inventories and linked unchanged source bodies. All input hash values are retained. Runtime binding-map paths use role keys; actual argv, personal host paths, RSS series, runtime binaries and large geometry are omitted explicitly. Historical held/pending flags remain unchanged; completed test, child and result ledgers are separate. Five new source guards for each adapter passed once in the copied root logs; unchanged historical classifier/runner test outcomes are reuse evidence, not fresh reruns.

This is a selected review subset, not full private closure or a standalone executable reproducer. Sources retain their repository/path dependencies; missing geometry and pinned runtime dependencies are required to rerun them. [Project licence](LICENSE.project) applies to project material; external Gmsh/Python/NumPy rights remain separate. The copied verifier checks only sealed bytes:

```sh
python3 -B verify.py
```

No MSH, new archive or release asset is included here. The saved MSH is 243,246,094 B, SHA-256 `e32ef35be1171ec55477e921dd75def0066f9f1e21bd2821dfbe363270354522`. The source remains the 871,731-vertex / 1,743,878-face assembled surface. Its 0.0625 mm numerical distance budget is no OEM tolerance; the 414 stronger Mesh_2 shape failures are not upgraded. Semantic/OEM evidence, mesh convergence/resolution, head PDE/strength, material/process, physical and manufacturing qualification remain open.
