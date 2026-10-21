# Original-source endpoint pass: terminal 4 GiB OOM

One separately authorised geometry pass ran the exact compiled endpoint002
helper on the original indexed head surface: **902,145 vertices and
1,804,706 oriented triangles**, source SHA-256
`894ece6e63d99684fd7c8710caf73132cd73731ac8bc667548c21c85962d4c95`.
The requested source-envelope budget remained **0.0625 mm**. The three prior
synthetic fixture outcomes remained separate prerequisites.

The actual container exited **137**, with **OOMKilled=true**, under the
unchanged **4,294,967,296-byte (4 GiB)** memory limit, two-CPU limit, no swap,
read-only rootfs and no network. Its controller window was
**19.158029792131856 s**, before the 300 s external deadline. The attach process
was reaped, the final state was stopped with PID zero, and the owned container
was removed without cleanup errors. All **74** frozen source/input/runtime/
fixture bindings remain unchanged.

The native output directory is empty. There is **no proposal, candidate,
native report or source-coordinate origin map**. The exact native log is zero
bytes, SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
No minimum quality, triangle reduction, accepted-collapse count, distance,
feature/topology/intersection result or volume result is available. The empty
log does not identify the internal stage or allocation that exhausted memory.
Actual peak RSS was not sampled; the memory limit is not a peak measurement.
No retry, resource escalation, alternate geometry, CUB call, tetrahedralisation
or thermal/strength solve followed this attempt.

`source-snapshots/` contains only the two new exact head controller/test files.
Unchanged [cleanup core](../finest-endpoint-fixtures/source-snapshots/twins/962-cylinder-head-f0/source/run_finest_endpoint_preflight.py)
and [optional-field metadata source](../finest-endpoint-fixtures/source-snapshots/twins/962-cylinder-head-f0/source/run_finest_endpoint_metadata.py)
remain in the sealed fixture capsule, linked with exact digests in
`helper-bindings.json`. The actual applied metadata format and all three source
attributions remain distinct. The source snapshots are review evidence; their
presence does not authorise running them or substitute for the original
frozen child and runtime.

The public contract, execution and summary files are explicitly allowlisted
**projections**, not byte-identical originals. The complete 74-entry input map
is stored once; the actual original before/after maps both match it exactly.
Original summary/contract/native receipt identities and the full original
six-artifact inventory are preserved. Commands, private absolute paths,
container identities and host metadata remain local. Binaries, upstream
headers and the large original head input are not redistributed. Original
project source follows the repository `LICENSE`; the existing CGAL licence
provenance remains in the sibling fixture capsule.

The summary's `native_pass_finished=false` and all unadmitted geometry/solver
flags remain unchanged. A null controller error records successful wrapper
handling and cleanup, not native success. Root and peer reviews inspect the
retained failure without rerunning the geometry. This capsule establishes no
accepted finest head representation, volume quality, thermal field,
convergence, material performance, CHT, LPBF, fitment or manufacturing release.

Root and independent retained-output reviews confirm this bounded OOM stop and
absence of exports. Their exact safe records are included; the payload is
sealed in `receipt.json`. The prior fixture capsule and every earlier rejection
remain intact. Hash checks require no native execution:

```sh
python3 - <<'PYVERIFY'
from pathlib import Path
import hashlib, json
base = Path('twins/962-cylinder-head-f0/derived/engineering/finest-endpoint-head-001')
r = json.loads((base / 'receipt.json').read_text())
for name, digest in r['payload_sha256'].items():
    p = base / name
    assert p.is_file() and not p.is_symlink()
    assert hashlib.sha256(p.read_bytes()).hexdigest() == digest, name
assert {str(p.relative_to(base)) for p in base.rglob('*') if p.is_file()} == set(r['payload_sha256']) | {'receipt.json'}
assert (base / 'original-head.native.log').stat().st_size == 0
assert r['candidate_surface_admitted'] is False
print('Exact bounded-failure payload verified; no geometry result credited.')
PYVERIFY
```
