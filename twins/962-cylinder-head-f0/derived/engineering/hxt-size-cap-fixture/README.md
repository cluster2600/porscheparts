# HXT size-cap fixture: insertion control only

Two separately authorised, serial software cube cases preserve an identical
7 × 7 × 7 mm surface (eight vertices, twelve outward triangles). Both use
Gmsh 4.15.2 HXT with `Mesh.Optimize=0`; their only option difference is
`Mesh.MeshSizeMax`: the uncapped default `1e22` versus **1.75 mm**.
No head geometry is read. The fixture asks whether actual referenced interior
nodes increase while retaining the exact boundary, positive finite volumes and
Jacobians, opposite internal-face orientation and saved-file identity.

| Actual case | Nodes | Interior nodes | Tetrahedra | Minimum SICN |
|---|---:|---:|---:|---:|
| Uncapped | 9 | 1 | 12 | 0.5485850609397153 |
| 1.75 mm cap | 42 | 34 | 191 | 0.027175498119979526 |

Both volume sums are exactly **343 mm³** in the retained native and independent
reports. The capped case establishes the insertion mechanism, but **fails the
unchanged SICN ≥ 0.1 head criterion**. Software-fixture success does not mean
head-quality success. The cap is not an actual edge bound or a sectional,
thermal-resolution or convergence certificate. No head, thermal, stress, LPBF,
fitment, historical-fidelity or manufacturing result follows.

The controller retains both zero exits, no stop reason, all nine native RSS
samples and per-case wall times about 0.46 s. Native controls were a 30 s
process-group deadline per case, 1 GiB sampled RSS stop, 16 MiB sampled total
output stop and two Gmsh threads, with no automatic retry. These are sampled
controls/thread settings, not hard address-space/OS CPU quotas or peak-memory
guarantees. Complete original resource values are retained in the per-case
payloads; the later reader's exact execution receipt retains its six samples.

The independently frozen reader opened both existing MSHs without generating,
optimising, writing a mesh or solving. It checked all coordinates/connectivity,
all native qualities, every tetrahedron's independent volume, the complete
exterior/internal oriented face incidence and strictly interior referenced
nodes. Its exact report is `independent-readback.json`. The exact root review
checks receipts/bindings/resources and reads that independent result; root did
not repeat the native reader. Both MSH identities are bound, but mesh arrays
and native runtime binaries are omitted here.

This is an **assembled whitelist projection**, not full native records or
standalone native reproduction. `provenance.json` identifies each exact safe
copy and each field projection with its original SHA-256. Native commands,
absolute runtime paths, process identifiers and raw logs remain private.
Source/test snapshots are exact: six executed controller/helper sources, the
prelaunch test and the later independent reader. Copied source includes generic
launcher logic, not private executed commands. The retained three prelaunch
tests are attributed to the authorization record; publication reruns no test
or native case. Preparation, later authorization, actual runs and postrun
reviews remain distinct. The earlier revision 001 remained unrun. Release-source
inspection explains the size clamp, but does not attest how the installed
Gmsh binary was built. No head-admission record is duplicated here.

`receipt.json` seals this directory's payloads. From the repository root,
check their hashes and numeric/resource bookkeeping without native execution:

```sh
python3 - <<'PYVERIFY'
from pathlib import Path
import hashlib, json
base = Path('twins/962-cylinder-head-f0/derived/engineering/hxt-size-cap-fixture')
r = json.loads((base / 'receipt.json').read_text())
for name, digest in r['payload_sha256'].items():
    p = base / name
    assert p.is_file() and not p.is_symlink()
    assert hashlib.sha256(p.read_bytes()).hexdigest() == digest, name
assert {str(p.relative_to(base)) for p in base.rglob('*') if p.is_file()} == set(r['payload_sha256']) | {'receipt.json'}
summary = json.loads((base / 'resource-summary.json').read_text())
for case in ['uncapped', 'capped-1p75']:
    samples = json.loads((base / case / 'resource-samples.json').read_text())['samples']
    assert len(samples) == summary['observed'][case]['sample_count']
    assert max(s['RSS_bytes'] for s in samples) == summary['observed'][case]['max_observed_RSS_bytes']
o = json.loads((base / 'outcome.json').read_text())
a, b = [o['cases'][c] for c in ['uncapped', 'capped-1p75']]
assert b['referenced_interior_nodes'] > a['referenced_interior_nodes']
assert b['minimum_SICN'] < 0.1
assert o['scope']['head_accepted'] is False
print('Public payload and bookkeeping agree; insertion evidence only.')
PYVERIFY
```

These checks do not repeat native meshing or independent geometric readback.
The [mutable engineering overview](../../../ANALYSIS_QUALITY_ENGINEERING.md)
provides navigation outside this sealed payload. Any head execution requires a
separate reviewed contract and authorisation.
