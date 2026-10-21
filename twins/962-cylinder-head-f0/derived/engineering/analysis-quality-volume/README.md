# Numerical quality-volume trial: deadline stop, no saved mesh

This immutable capsule records one authorized HXT meshing attempt on the separately admitted original-source quality candidate. It is a numerical volume-quality trial only. It credits no head thermal field, stress result, LPBF simulation, material qualification or manufacturing release.

The candidate SHA-256 is `7f0d96988684f7d36dab8f65c5b63b1919c2c2121768cf9caec466867a5c2b43`, with 902,145 boundary vertices, 1,804,706 triangles and signed volume 915,458.4757034747 mm^3. The prior numerical surface admission covers the explicitly scoped preliminary quality/topology/opening-patch checks and separate continuous-distance evidence. Its features gate is not a complete OEM/CSG semantic map, candidate wall-thickness qualification or conformal CHT interface.

The frozen Gmsh 4.15.2 ARM64 trial used HXT, two Gmsh threads, standard optimization, preserved linear source facets and a 300 s watchdog. It stopped during generation/optimization at 300.1272330421489 s, native return code -9, with stop reason `native_deadline`. The maximum observed RSS was 6,417,481,728 bytes over 584 samples; the 8 GiB sampled RSS threshold did not trigger. RSS sampling is not a hard peak-memory limit, and no hard OS CPU/address-space quota is claimed. Maximum sampled output was 112,821 bytes.

The exact source coordinate, triangle-tag, winding and multiplicity import passed before generation. There is **no `head-volume.msh`**. Final tetrahedron count, minimum SICN/Jacobian, actual tetrahedral boundary, internal face orientation, saved-mesh readback and interior thermal DOFs remain null/unrun. Logged intermediate element counts are not accepted final counts. The worker JSON still says `running` because it is the last checkpoint preserved before the watchdog killed the process; root independently verified that the process had stopped. The definitive controller record is a deadline stop.

The independent root review verifies all 258 surface-admission input bindings, all five executed source/snapshot bindings, the exact candidate import, all 584 resource samples, deadline/output facts, stopped process and absent mesh. It is included byte-for-byte as `root-independent-review.json`. The source review closes the missing-mesh/digest, internal-face-orientation and watchdog-start cleanup guard defects before launch. Six focused tests were reported passing by the implementer and root; the independent reviewer inspected source/tests and did not repeat native meshing.

`provenance.json` distinguishes exact records/source snapshots from safe whitelist projections and newly authored summaries. Commands, personal host paths, runtime binaries and the complete native log remain local; original receipt/log hashes are retained. Public source copies match the actual stopped-trial captures. No retry, new settings or additional native run is inferred or authorized by this capsule.

From the repository root, verify the immutable public payload:

```sh
python3 - <<'PYVERIFY'
from pathlib import Path
import hashlib, json
base = Path('twins/962-cylinder-head-f0/derived/engineering/analysis-quality-volume')
receipt = json.loads((base / 'receipt.json').read_text())
for name, digest in receipt['payload_sha256'].items():
    path = base / name
    assert path.is_file() and not path.is_symlink()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, name
assert {str(p.relative_to(base)) for p in base.rglob('*') if p.is_file()} == set(receipt['payload_sha256']) | {'receipt.json'}
samples = json.loads((base / 'resource-samples-projection.json').read_text())['samples']
summary = json.loads((base / 'resource-summary.json').read_text())
assert len(samples) == summary['sample_count']
assert max(s['RSS_bytes'] for s in samples) == summary['max_observed_RSS_bytes']
assert max(s['output_bytes'] for s in samples) == summary['max_observed_output_bytes']
print('Payload and resource summaries match; no volume/physics admission follows.')
PYVERIFY
```

Hash verification and sample aggregation do not reproduce native geometry. Navigation outside this folder is not part of its immutable payload. Later mesh or physics evidence must use a separate record and cannot upgrade this stopped trial retroactively.
