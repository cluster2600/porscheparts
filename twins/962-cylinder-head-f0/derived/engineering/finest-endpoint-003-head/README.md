# Endpoint003 actual head pass: partial improvement, rejected proposal

One separately authorised pass completed on the immutable original indexed
head under the unchanged **0.0625 mm** local source-envelope budget. It made
**284 endpoint collapses** and reduced the number of triangles below the
declared necessary triangle screen **2/29 from 744 to 266**. The global minimum
triangle SICN remained **0.0000022723905926649325**. The required zero-remaining-
bad-face gate therefore **fails**, and the proposal is **rejected**.

| Actual full-array diagnostic | Original | Proposal |
|---|---:|---:|
| Referenced vertices | 902,145 | 901,861 |
| Oriented triangles | 1,804,706 | 1,804,138 |
| Triangles below 2/29 | 744 | 266 |
| Minimum triangle SICN | 0.0000022723905926649325 | 0.0000022723905926649325 |

Native exit code **0**, `candidate_written=true` and
`full_quality_objective=true` are preserved exactly. The helper's latter flag
means the total bad-face count decreased and the global minimum did not worsen;
it does not mean the required count reached zero or that the surface was
admitted. Procedural phase success, native local improvement and independent
surface acceptance are distinct ledgers. The original pending-independent-
check flags and the phase's false admission flags remain unchanged.

The root and peer reviews read all actual output coordinates and origin IDs.
All **900,845 fixed original vertices** and every original exterior oriented
face remain exact. Every retained coordinate equals its recorded original
coordinate, with unique in-range origins and no unreferenced output vertices.
The map records each retained coordinate's original index; it is not complete
ancestry for removed vertices. The root review counts zero remaining bad
triangles whose three original vertices are all fixed. These quality values
are binary64 full-array diagnostics, not interval certificates.

Version003 uses the exact immutable original **4,704 patch faces** referencing
**3,858 original vertices** for the CGAL subset-envelope constructor. Both raw
ordered ID exports match the independent original selection and frozen
expected bytes. Thirteen flushed scalar progress events and the final native
report are preserved. The subset construction is a conservative local
candidate-to-original screen because distance(x,complete original) is no
greater than distance(x,original subset). It does not establish reverse
coverage or whole-head continuous distance.

There was **no independent CUB query, complete topology or global intersection
audit, tetrahedralisation, thermal/structural solve, material or LPBF
calculation** after this rejection. The native `closed_valid_triangle_mesh`
flag is retained as the helper's own check and is not promoted to an
independent topology audit. No complete Porsche/OEM semantic interface map,
finest head representation, solver admission or manufacturing release is
established. Later distinct evidence cannot change this capsule's rejected
scope.

The actual controller window was **15.359576124930754 s**. The immutable image
ran with two CPUs, **4 GiB** memory, no swap, a read-only root filesystem,
network disabled and a 300 s external bound. The native process exited without
OOM; the attach process was reaped and the exact owned container removed.
This window includes container lifecycle overhead. Actual peak RSS and CPU
usage were not sampled; the memory limit is not a peak measurement. The prior
[endpoint002 OOM](../finest-endpoint-head-001/README.md) remains a separate
unchanged result, with its internal allocation stage unknown. No retry or
resource escalation is credited here.

The **64,944,000-byte** proposal, SHA-256
`a963c8ba7e043cd45e51083da1c12e3e620141b599b8f7a66d16d08cd1c5f193`,
and **7,214,888-byte** coordinate-origin map, SHA-256
`1f7e98ee191709c4350e0fc61615087c2aaaefc43c868b6c1a4bf8e3929099b5`,
remain local and are omitted from this Git capsule. The native
`quality-candidate.bin` and `proposed-surface.bin` are byte-identical; their
filenames do not imply admission. Neither the unchanged original source nor
this proposal has physical or manufacturing qualification. A possible later
download archive requires separate review; no archive creation or upload is
recorded here.

`native/` contains exact small report/log/reference-ID copies. Safe exact
root and independent reviews are included. Explicit allowlisted contract,
execution and phase projections omit commands, private absolute paths,
container identities/owner values, PIDs and host metadata. The complete
**142-entry** original input map is stored once; both original before/after
maps equal it, and current file hashes were checked again during preparation.
The full **12-artifact** original inventory includes omitted binaries, large
arrays and private receipts as hashes; the phase-summary hash is separate.

New full source copies are not duplicated. Their exact existing public
locations and SHA-256 identities are in `source-bindings.json`, linked to the
[sealed endpoint003 compile/fixture capsule](../finest-endpoint-003-fixtures/README.md)
and earlier unchanged cleanup/shared helpers. That fixture capsule also
contains the preserved subset proof, source diff and licence provenance.
Original project material follows the repository
[LICENSE](../../../../../LICENSE); no commercial CGAL licence is claimed.

The source input identity is
`894ece6e63d99684fd7c8710caf73132cd73731ac8bc667548c21c85962d4c95`.
No original head arrays or executable binaries are redistributed here.
Consequently, the public small evidence supports inspection of the retained
reviews and diagnostics; it is not a self-contained repeat of their complete
private head-array comparisons. Integrity checks need only the standard library:

```sh
python3 - <<'PYVERIFY'
from pathlib import Path
import hashlib, json
base = Path('twins/962-cylinder-head-f0/derived/engineering/finest-endpoint-003-head')
r = json.loads((base / 'receipt.json').read_text())
paths = list(base.rglob('*'))
assert not any(p.is_symlink() for p in paths)
assert {str(p.relative_to(base)) for p in paths if p.is_file()} == set(r['payload_sha256']) | {'receipt.json'}
for name, digest in r['payload_sha256'].items():
    assert hashlib.sha256((base / name).read_bytes()).hexdigest() == digest, name
assert r['remaining_triangles_below_2_over29'] == 266
assert r['candidate_surface_admitted'] is False
assert r['head_physics_executed'] is False
print('Exact partial-rejection capsule verified; no head admission or physics credited.')
PYVERIFY
```
