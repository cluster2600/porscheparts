# Raw HXT seed: saved mesh, rejected quality

This capsule records a separate, explicitly authorized diagnostic on the source-bound quality candidate. `Mesh.Optimize=0` saved one raw HXT volume mesh before standard internal optimization. The unchanged **minimum SICN >= 0.1** gate rejected it. This is a numerical mesh-quality record; it credits no head temperature, stress, material qualification, LPBF result or manufacturing release.

The saved Gmsh 4.1 binary mesh is 210,476,070 bytes, SHA-256 `7bfb96b55af3fadd81ea1409f633882f6a0249f961ef4f2a7f549a0fd2da2e67`. It has 902,148 nodes and 3,096,408 linear tetrahedra. Its exact source surface retains 902,145 vertices and 1,804,706 triangles. The actual minimum SICN is -1.2793193015693403e-14; two elements have nonpositive SICN and 1,478,281 fall below 0.1. All native Jacobians and signed volumes are positive, but positivity does not establish element quality. Only **three referenced interior nodes** are present; no thermal resolution or convergence follows.

The native controller rejected the result in 126.03402208304033 s without a resource stop. Maximum observed RSS was 6,416,138,240 bytes across 244 samples. Two Gmsh threads, the frozen 300 s watchdog, an 8 GiB sampled RSS stop and a 1 GiB sampled-output stop were retained. No hard OS CPU/address-space quota or peak-memory guarantee is claimed. This trial is distinct from the prior Optimize1 deadline stop in `../analysis-quality-volume/` and does not replace that evidence.

An independently frozen, bounded postrun reader opened the exact saved file: **no generate, optimize, mesh write or solve**. It checked all four tagged node/tetra array hashes, exact original boundary coordinates and explicit surface connectivity, every native SICN/Jacobian/volume, all signed tetra volumes, and referenced node counts. The independent volume sum is 915,458.4757034747 mm^3, equal to the candidate reference. It completed in 10.58227995899506 s with 1,801,601,024 bytes maximum observed RSS, under a separate 120 s watchdog/4 GiB sampled stop. `independent-readback.json` is the exact result. The reader did **not** repeat full tetra-face incidence sorting: the worker's exact exterior tetra boundary and 5,290,463 opposite-oriented internal face pairs are explicitly retained worker evidence, rather than independent-reader claims. Exact explicit surface elements alone do not prove tetra exterior incidence.

Six executed mesher source snapshots match preflight hashes and actual captured files. The isolated seed wrapper preserves the frozen core, its admission/audit/cleanup gates and actual SICN threshold. Only the reserved output, Optimize0 and truthful stage attribution change. The two focused prelaunch test snapshots are tests, not native runtime inputs. The independently executed reader is a later diagnostic source, not a meshing input. Full original receipts/logs, mesh arrays, runtime binaries and private commands remain local; safe projections retain their hashes and declare each omission. The surface admission remains scoped to numerical bionic-source continuity, not a complete OEM/CSG feature map or conformal CHT interface.

The exact safe `root-independent-review.json` records the final root review of the original receipts, complete independent reader, saved-file identity, all 258 admission bindings and six executed-source captures. Root did not repeat the reader or full tetra-face incidence sorting. This capsule is sealed by `receipt.json`; subsequent results must remain separate records.

From the repository root, verify the sealed public payload without native execution:

```sh
python3 - <<'PYVERIFY'
from pathlib import Path
import hashlib, json
base = Path('twins/962-cylinder-head-f0/derived/engineering/analysis-quality-volume-seed')
receipt = json.loads((base / 'receipt.json').read_text())
for name, digest in receipt['payload_sha256'].items():
    path = base / name
    assert path.is_file() and not path.is_symlink()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, name
assert {str(p.relative_to(base)) for p in base.rglob('*') if p.is_file()} == set(receipt['payload_sha256']) | {'receipt.json'}
summary = json.loads((base / 'resource-summary.json').read_text())
for filename, role in [('native-resource-samples.json', 'native_trial'), ('readback-resource-samples.json', 'independent_saved_file_readback')]:
    samples = json.loads((base / filename).read_text())['samples']
    assert len(samples) == summary[role]['sample_count']
    assert max(s['RSS_bytes'] for s in samples) == summary[role]['max_observed_RSS_bytes']
outcome = json.loads((base / 'outcome.json').read_text())
assert outcome['SICN_gate_passed'] is False
assert outcome['actual_minimum_SICN'] < outcome['actual_minimum_SICN_gate']
print('Payload/resources agree; saved seed remains quality rejected.')
PYVERIFY
```

Hash verification does not reproduce native geometry. Later refinement, meshing or head physics requires separate authorization and evidence. Navigation outside this directory is excluded from the immutable payload.
