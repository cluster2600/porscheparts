# Original-source quality candidate: preliminary geometry evidence

This immutable capsule records one local quality pass and its preliminary quality, topology and scoped feature checks. Its permanent scope excludes continuous-distance results, tetrahedral meshing, head physics, material qualification and manufacturing release. Later distance or tetra results belong to separate records; they do not rewrite this checkpoint.

The original inspected bore95 STL has SHA-256 `ba7a0e28dade659550705e9737177c64c7f6fecd8d86d01e31732d7e739cd906`; its exact indexed input is `894ece6e63d99684fd7c8710caf73132cd73731ac8bc667548c21c85962d4c95`. Every original ordered oriented triangle was checked, preserving winding and multiplicity. The candidate is `7f0d96988684f7d36dab8f65c5b63b1919c2c2121768cf9caec466867a5c2b43`, not an earlier collapsed candidate.

One CGAL5.6 atomic pass uses target0, no splits/collapses, fixed exterior-incidence and clip-plane vertices, and projection onto an immutable ORIGINAL-source AABB tree. Fixtures verify sliver improvement1→0, fixed-anchor stagnation rejection and existing-output refusal. Native execution took3.82s without OOM/deadline expiry. Independent full-array and root reviews confirm744→0 facets below the necessary triangle-SICN bound2/29, minimum2.2723905926649325e-6→0.06923322066867299, unchanged902145vertices/1804706faces, every900845fixed coordinate and all exterior oriented faces exact. Passing this necessary face screen does not establish tetrahedral SICN>=0.1.

The separately retained topology001 attempt stopped on an API-adapter error before any candidate global-intersection query. No result is credited to it. The corrected002 adapter and source are separately preserved. That audit passed one-component/Euler−208/positive-volume/edge-and-vertex-manifold checks and a complete global query with zero intersection pairs, with all five known-result intersection fixtures passing. It completed in18.724s within2CPUs/4GiB/no-swap/300s/no-network, with arrays and all43 bound inputs unchanged.

The scoped feature screen verifies all228 incidence patches remain manifold disks with the exact same oriented fixed boundary coordinates. All eight retained opening-point signed distances are identical and strictly positive in original/candidate direct-float64 VTK geometry. Water/dry hashes and the original sampled4.439295271064934mm clearance receipt remain unchanged. That clearance concerns water versus dry geometry only. It is not candidate wall thickness, channel-section, OEM-interface or conformal-CHT proof. See `feature-location-review.md` for construction-region correspondence and the exact missing semantic-provenance/sectional-coverage gap.

`provenance.json` distinguishes exact records, executed snapshots, whitelist projections and the unexecuted verbatim intersection-functions excerpt. Commands/host paths, raw arrays and runtime binaries remain local. The header-inspection setup refusal and both topology adapters are retained with their original scope. Historical flags describe the corresponding run, not later programme state. Full numerical reruns need the retained native arrays/runtime bundles; the public capsule alone does not reproduce geometry computations.

From the repository root, verify every published payload with the standard library:

```sh
python3 - <<'PYVERIFY'
from pathlib import Path
import hashlib, json
base = Path('twins/962-cylinder-head-f0/derived/engineering/analysis-quality-candidate')
receipt = json.loads((base / 'receipt.json').read_text())
for name, digest in receipt['payload_sha256'].items():
    path = base / name
    assert path.is_file() and not path.is_symlink()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, name
assert {str(p.relative_to(base)) for p in base.rglob('*') if p.is_file()} == set(receipt['payload_sha256']) | {'receipt.json'}
print('Public capsule payload hashes match; no numerical or physical acceptance follows.')
PYVERIFY
```

The source snapshots retain their historical paths and runtime expectations; they are review evidence, not standalone runnable fixtures in this directory. The source licence is included. No upstream/runtime binary is distributed. The navigational `ANALYSIS_QUALITY_ENGINEERING.md` lives outside this immutable payload and may later link separately versioned results.
