# Clipped surface: global topology and intersection reference

One fresh native audit passed the recorded global topology and intersection
subgates for the exact clipped candidate
`d2af68ee8ab242e992b15b6e2a93ac7e487972277af7f31a8496a7036ec32240`.
This is a **pre-repair reference**. Its 3,112 triangles below 2/29 still reject
the surface; these subgates grant no repair or engineering admission.

| Recorded whole-surface observation | Result |
| --- | ---: |
| Vertices / edges / triangles | 869,355 / 2,608,689 / 1,739,126 |
| Connected components | 1 |
| Measured Euler characteristic | −208 |
| Boundary / nonmanifold / orientation-imbalanced edges | 0 / 0 / 0 |
| Nonmanifold vertices | 0 |
| Global intersection pairs | 0, complete query |
| Finite positive signed surface volume | 915,453.1229484563 mm³ |

The whole clipped Euler value was measured without imposing the old −208
equality. The generic worker guard required an integer observation alongside
the declared one-component, closed-orientation and finite-positive-volume
criteria. The preserved legacy `require_topology` helper retains its historical
equality but was not called. This observed whole-surface value is separate from
the local incident-patch Euler −4. The signed volume is a geometric surface
calculation; no tetrahedral volume mesh was accepted.

The component fixtures returned `[1, 2]`. The five intersection fixtures returned
`[0, 1, 1, 1, 0]` for separate, crossing, coplanar-contained, coplanar shared-vertex
overlap and manifold-tetrahedron cases. Their input arrays remained unchanged.
The full candidate query retained `detect_only=true`, `first_only=false`,
`stitch_all=false` and the 100,001-pair cap. It returned no pairs with
`complete=true`. The worker reports unchanged candidate arrays and bound inputs;
both saved 44-input maps agree with the frozen launch contract.

The observed ARM64 runtime used Python 3.11.15, NumPy 2.2.6 and libigl 2.6.3.
The wrapper and all nine native-module hashes remain recorded. The owned
container used a read-only root, two CPUs, 4 GiB memory and equal memory-plus-swap
limit, no swap, no network, no tmpfs, two library threads and a 300-second
external deadline. Four input mounts were read-only; only output was writable.
The worker took 13.519 seconds and the controller 17.604 seconds. Saved records
show return code 0, no OOM, an empty native log, attach-process reaping and
stopped owned-container removal. Peak RSS, actual CPU use and a separate OS
PID-absence observation were not measured.

The [worker report](reports/worker-report.json), [native log](logs/atomic-topology.native.log),
[root result review](reviews/root-result.json) and [independent result review](reviews/peer-result.json)
are exact originals. Both reviews check saved provenance, lifecycle and
numerical consistency. The independent review performs no native replay or
full candidate topology recomputation. [Original records](original-records.json)
preserve the complete 17-file native inventory, the original receipt's full
16-artifact digest map, and both complete 44-input maps. This selected capsule
does not redistribute every native artifact or input.

[Projections](projections.json) retain the selected contract and lifecycle
values, every resource control, runtime binding, all five mount rules and every
control-call operation/return code. Original invocation commands, host mount
sources, ownership/container identifiers, numeric process identifiers,
timestamps and raw control-call output are omitted. The relative contract
candidate/output/preparation/review metadata is also outside that allowlist;
the complete original input maps and original record hashes remain available
in the inventory. The contract's null observation fields describe its state
before launch; the worker report supplies the measured outcome.

The exact [worker](sources/audit_atomic_topology.py), [executed controller](sources/run_atomic_topology.py),
[three controller-refusal tests](sources/test_atomic_topology.py),
[source reuse proof](preparation/source-reuse.json), [root source review](reviews/root-source.json)
and [source peer review](reviews/source-peer.json) retain their provenance.
The source peer's [test log](logs/controller-tests.log) records all three passes.
The separate [generic-guard test](sources/test_generic_guard.py) and its
[result](tests/generic-guard-result.json) record five accepted integer-Euler
literals and 23 invalid-input refusals, using only the extracted local guard.
Those 28 literal cases do not measure geometry. The test/source snapshots
depend on their original repository layout and bound inputs.

[Source bindings](source-bindings.json) identify the six unchanged audit
helpers and owned metadata/cleanup pair without duplicating their complete
sources or distributing upstream headers, installed libraries, runtime images,
executables or the large candidate. The exact [held preparation README](preparation/README.held.md)
preserves the earlier unrun stage; the completed receipt projections and result
reviews above record the subsequent run.

No semantic cap/void equivalence, cooling-passage or feature/interface mapping,
continuous distance acceptance, repair region, target or keeper selection,
accepted surface/volume mesh, head thermal/structural result, material selection,
LPBF qualification or manufacturing authorization is established. The 3,112 poor
triangles and all remaining acceptance gates stay recorded.

After sealing, `python3 -B verify.py` checks recorded payload hashes, sizes and
file closure using the reused standard-library verifier. It performs no native
import, geometry query or replay and adds no engineering acceptance.
