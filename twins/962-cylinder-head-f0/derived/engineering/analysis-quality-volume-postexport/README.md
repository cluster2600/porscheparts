# Head post-export optimizer: deadline stop, no mesh

One separately authorised default-force optimizer attempt ran on the exact saved sized-head input. The **300 s watchdog stopped the native worker at 300.0737672080286 s**, return code **−9**. The outer controller CLI completed with return code **2** in 302.93481470807455 s. Root verified the worker was reaped and absent. **No `head-volume.msh` was exported.** There is no new final mesh or final quality result.

`last-worker-checkpoint.json` is the exact original worker record. Its status remains `running`, stage `calling_default_postexport_optimizer`, because that is the stale checkpoint saved before the process was killed. It records **one API-call attempt**, with `optimizer_returned=false`; cache refresh was **not attempted or completed**. It does not describe a currently active process or a successful optimization. The stopped controller receipt and exact root review are authoritative for termination. No retry occurred.

All **583** original resource samples are preserved. Maximum observed RSS was **2,937,126,912 bytes**; maximum sampled output was **146,247 bytes**. This was a deadline stop, not an RSS/output stop. Unchanged controls were two threads, an 8 GiB sampled RSS stop and a 1 GiB sampled output stop. Sampling excludes atomic `.tmp` reports and is not a hard peak-memory, OS address-space or CPU quota.

Before the optimizer call, loaded node/coordinate/tetrahedron hashes matched both the retained sized-input worker and independent readback. Exact explicit source surface and entity classification were checked again. Earlier input quality and full tetra-face incidence were explicitly retained proof, not recomputed before optimization. Those input values describe the **already rejected sized mesh**, not a final optimized mesh. Final element count, minimum SICN, positive-volume result, exterior/internal incidence, saved readback and mesh identity remain **null/unrun** in `outcome.json`. The actual SICN ≥ 0.1 gate was not relaxed; Gamma 0.3 is a separate optimizer request.

The independent saved-file reader was prepared only. With no exported MSH, no readback contract was frozen and no reader was run. Its sources remain private and unexecuted. No new archive, geometry, head temperature/stress result, LPBF result or manufacturing qualification follows. This record preserves one bounded attempt; it does not reduce the wider engineering goal or upgrade earlier rejected evidence.

Root rechecked all **72** preflight/source/input/snapshot/runtime bindings, all **258** admission pins, all six executed source captures, every resource sample, process termination and output absence. `root-review.json`, authorization and outer CLI return are exact safe copies. New wrapper/test snapshots are exact. Five unchanged helpers are referenced by exact public source paths and SHA-256 at commit `1112314d6b52b9b7dae9371193e0dcb3a9941cef` rather than copied again. The original native log is retained locally by hash. This is a whitelist projection: actual commands, private host/runtime paths, process identifiers and binaries are omitted. No source-build attestation for installed Gmsh is inferred.

Verify the sealed payload and all resource samples from the repository root without native execution:

```sh
python3 - <<'PYVERIFY'
from pathlib import Path
import hashlib, json
base = Path('twins/962-cylinder-head-f0/derived/engineering/analysis-quality-volume-postexport')
r = json.loads((base / 'receipt.json').read_text())
for name, digest in r['payload_sha256'].items():
    p = base / name
    assert p.is_file() and not p.is_symlink()
    assert hashlib.sha256(p.read_bytes()).hexdigest() == digest, name
assert {str(p.relative_to(base)) for p in base.rglob('*') if p.is_file()} == set(r['payload_sha256']) | {'receipt.json'}
rows = json.loads((base / 'resource-samples.json').read_text())['samples']
s = json.loads((base / 'resource-summary.json').read_text())
assert len(rows) == s['sample_count'] == 583
assert max(v['RSS_bytes'] for v in rows) == s['max_observed_RSS_bytes']
assert max(v['output_bytes'] for v in rows) == s['max_sampled_output_bytes']
o = json.loads((base / 'outcome.json').read_text())
assert o['final_output']['mesh_exported'] is False
assert o['final_output']['minimum_SICN'] is None
assert o['independent_reader_run'] is False
print('Payload/resources agree; deadline stop, no final mesh or physics result.')
PYVERIFY
```

Navigation and later engineering records outside this directory are not part of this immutable payload.
