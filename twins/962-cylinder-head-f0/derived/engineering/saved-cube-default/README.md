# Saved-cube default optimizer: failed controller, successful file diagnosis

One authorised call to `optimize(method="", force=True)` ran on the saved 7 mm cube. It wrote a **9,430-byte** output, then the original in-memory after-audit failed with **`Unknown element 216`**. The controller returned 2. That original failure remains unchanged; this capsule does not retroactively mark the fixture controller as passing.

A separately frozen, read-only inspection opened the exact original and exported files, without generating, optimizing, writing a mesh or solving. It found:

| Saved file | Tetrahedra | Referenced interior nodes | Minimum SICN | SICN below 0.1 |
|---|---:|---:|---:|---:|
| Original capped cube | 191 | 34 | 0.027175498119979526 | 8 |
| Exported default-optimized cube | 182 | 34 | 0.19090538411389205 | 0 |

Both files contain 42 referenced nodes, no orphan nodes, the exact eight original boundary coordinates and twelve outward boundary triangles. All native Jacobians and independent signed volumes are finite and positive; both volume sums are exactly **343 mm³**. All internal shared faces have opposite orientations (376 before, 358 after). The optimizer changed connectivity and moved 23 interior nodes, with no boundary-node movement. The later saved-file diagnosis therefore supports strict SICN improvement and passing the **0.1 cube numerical criterion**. It proves no head-quality result, thermal resolution, strength, LPBF process, fitment or manufacturing release.

`Mesh.OptimizeThreshold=0.3` is the default optimizer's **Gamma** request; it is separate from the independently assessed minimum **SICN ≥ 0.1** criterion. The fixture deliberately supplies no `niter` limit because that parameter does not bound this backend's loop. Its external controls were a 30 s process-group watchdog, 1 GiB sampled RSS stop, 16 MiB sampled output stop, two threads and no retry. The actual failed controller window was 0.6222080830484629 s, without a resource stop; all six native samples are retained. Output sampling excludes atomic `.tmp` reports. The later reader took 0.9496770000550896 s under a separate 120 s/1 GiB sampled/two-thread scope; all eight samples are retained. Sampling and thread settings are not hard OS CPU/address-space quotas or peak-memory guarantees.

The exact independent result, full tiny arrays and root review are published separately from the original exact native worker record. Root recomputed both complete arrays, volumes and oriented face incidence without a native rerun. `source-cache-diagnosis.json` records a **source-supported inference**: quality lookup uses an element cache, topology changed, and a fresh-file read succeeded after the in-memory lookup error. This is consistent with stale cache state. It does not experimentally prove the root cause, attest the installed binary build, demonstrate a cache fix or imply an optimizer retry.

The before and after binary Gmsh 4.1 files are synthetic repository-generated cube data, not scans or third-party CAD. Their SHA-256 digests are:

- `meshes/before-capped-cube.msh` (9,790 bytes): `e773cc4a2f68187c623e984eb9f58441f3fa5eed2733295e7eb26bd7b3910ac1`
- `meshes/after-default-cube.msh` (9,430 bytes): `3676ea044e2e10ea91435271687cac7f2181704014dc4e0daf8ae5c9ede26613`

MSH has no standard unit declaration; this literal cube's coordinate convention is millimetres. Original project material follows `LICENSE`. No upstream source or runtime binary is redistributed. New optimizer source/test and independent reader snapshots are exact. Six unchanged helpers are referenced by exact public source paths and SHA-256 digests at commit `1112314d6b52b9b7dae9371193e0dcb3a9941cef` in `helper-bindings.json`.

This assembled whitelist projection preserves original record hashes and labels omissions. Private runtime paths, executed commands, process IDs, full logs and runtime binaries remain local. Preparing, authorising, attempting, failing and later reading remain distinct events. No head optimizer call is authorised by this capsule. Prior rejected head/seed/cube evidence is unchanged.

Verify the sealed payload and resource values from the repository root without native execution:

```sh
python3 - <<'PYVERIFY'
from pathlib import Path
import hashlib, json
base = Path('twins/962-cylinder-head-f0/derived/engineering/saved-cube-default')
r = json.loads((base / 'receipt.json').read_text())
for name, digest in r['payload_sha256'].items():
    p = base / name
    assert p.is_file() and not p.is_symlink()
    assert hashlib.sha256(p.read_bytes()).hexdigest() == digest, name
assert {str(p.relative_to(base)) for p in base.rglob('*') if p.is_file()} == set(r['payload_sha256']) | {'receipt.json'}
s = json.loads((base / 'resource-summary.json').read_text())
for file, role in [('native-resource-samples.json', 'native_optimizer'), ('readback-resource-samples.json', 'independent_readback')]:
    rows = json.loads((base / file).read_text())['samples']
    assert len(rows) == s[role]['sample_count']
    assert max(v['RSS_bytes'] for v in rows) == s[role]['max_observed_RSS_bytes']
o = json.loads((base / 'outcome.json').read_text())
assert o['original_controller_ledger']['software_mesh_passed'] is False
assert o['independent_saved_file_ledger']['assessment']['postrun_cube_quality_success'] is True
assert o['qualification']['head_accepted'] is False
print('Payload and bookkeeping agree; original failure and later cube diagnosis remain distinct.')
PYVERIFY
```

Full array values support independent arithmetic and face-incidence review. Hash/sample checks alone do not reproduce native quality metrics or authorize additional optimizer work. Navigation outside this folder is excluded from the immutable payload.
