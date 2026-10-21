# Endpoint003 head evidence: inventory correction

This companion corrects one sentence in the frozen
[head003 capsule README](finest-endpoint-003-head/README.md). The capsule's
receipt remains byte-identical, SHA-256
`f9e48ab519389a6dc633cca2ee4e1bc9ecbd4e2a56fcf9ae2a94931e5631b193`.

The **12-artifact original phase inventory contains no executable binary**.
It records three controller-source snapshots, the frozen execution contract,
the execution receipt, the native log, the native report, two ordered patch-ID
exports, two byte-identical proposal/candidate arrays and the coordinate-origin
array. The phase-summary hash is separate from that inventory.

The applied executable is instead bound among the **142 frozen inputs**:
SHA-256 `ae6afd3bddf99775c3b38c11b40fb98a90a05ed222256e53ab99a419552f6eae`.
Its identity is also stated in the public `source-bindings.json` and
`contract-projection.json`. The executable is not redistributed in the small
capsule. The README's statement that the 12-artifact inventory includes omitted
binaries should therefore be read as **omitted large arrays**; binary identity
belongs to the separate input-binding ledger.

The root review's count of zero remaining bad triangles with all three
original vertices fixed is a mask observation. It establishes no complete
semantic constraint map, feasible repair, or further-pass outcome.

The proposal remains rejected: 266 triangles still fall below the declared
2/29 screen, and the minimum quality is unchanged. This correction adds no
geometry, CUB, topology/intersection, volume or physics result and changes no
frozen source, native output, receipt or qualification flag.
