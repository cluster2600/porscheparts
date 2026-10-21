# Sized raw HXT head trial: saved mesh, rejected quality

One separately authorised `Mesh.Optimize=0` trial applies a **1.75 mm** size
request to the source-bound bore95 numerical candidate. Its exact saved
Gmsh 4.1 binary MSH is **211,471,998 bytes**, SHA-256
`b142e05973f288f7fbee4f56b7fa7a4ed79adb2f4345aa6657764a2bf1a693f4`.
It has **3,059,463 linear tetrahedra**, **979,452 nodes**, **77,307 referenced
interior nodes** and zero unreferenced nodes. MSH carries no standard unit
declaration; this study interprets its coordinates as millimetres.

The unchanged **minimum SICN ≥ 0.1** criterion rejects the result:
**284,806 tetrahedra fall below 0.1**, two have nonpositive SICN, and the minimum
is **−1.2793193015693403e−14**. All native Jacobians and signed volumes are
positive; positivity does not establish element quality. The worker retains
exact exterior tetrahedral incidence, 5,216,573 opposite-oriented internal
face pairs and saved tagged-array identity. The volume sum remains exactly
915,458.4757034747 mm³, with zero relative bookkeeping error.

The controller ends with return code 2 after 109.4522545831278 s without a
resource stop. Its 213 samples reach 6,416,007,168 bytes maximum observed RSS.
The unchanged controls are a 300 s process-group watchdog, 8 GiB sampled RSS
stop, 1 GiB sampled output stop and two Gmsh threads. These are sampled
controls/thread settings, not hard OS CPU/address-space quotas or peak-memory
guarantees. Separate process verification records the worker absent/reaped.

An independently frozen read-only diagnostic opens the exact saved file with
**no generate, optimise, mesh-write or solve calls**. It compares all tagged
node/tetrahedron array hashes, exact original boundary coordinates and explicit
surface connectivity, every native SICN/Jacobian/volume, every independent
signed volume and all referenced-node counts. Its controller completes in
12.033298207912594 s with 24 samples and 1,793,048,576 bytes maximum observed
RSS under a 120 s watchdog/4 GiB sampled stop; the report's numerical reader
window is separately recorded as 10.832686749985442 s. The exact
`independent-readback.json` preserves all scalar findings. The reader **does
not repeat full tetra-face sorting**: exterior/internal incidence remains
explicitly retained worker evidence. Explicit surface elements alone do not
prove tetrahedral exterior incidence.

The two nonpositive-SICN tetrahedra have tags **4,365,900** and **5,927,920**.
All eight diagnostic nodes are exact original fixed-boundary coordinates;
the report preserves their tags, coordinates and actual metrics. The final
root review reads the full reader/results, checks all 85 direct bindings,
three runtime bindings, 24 resource samples and tagged metric equality, and
directly matches the eight coordinates. Root does not rerun the native reader.
Moving other nodes with unchanged connectivity cannot change these two cells;
a connectivity change or separately admitted boundary change would be needed
to alter them. No such change is authorised by this capsule.

The size request is a coarse assumption: half the generator's assumed 3.5 mm
BCC beam diameter. More interior nodes do not establish an actual edge bound,
minimum-wall measurement, sectional resolution, convergence or head thermal
resolution. The [cube fixture](../hxt-size-cap-fixture/README.md) establishes
insertion control only; its capped SICN also fails 0.1. The earlier
[raw-seed rejection](../analysis-quality-volume-seed/README.md) and
[no-MSH deadline trial](../analysis-quality-volume/README.md) remain unchanged.
No head thermal, stress, LPBF, fitment, historical-fidelity or manufacturing
result is credited.

This is an **assembled whitelist projection**, not full native records or
standalone native reproduction. `provenance.json` identifies exact safe
source/test/sizing-basis and root/reader copies separately from projections.
All original frozen records remain unchanged. The preliminary root review
that said readback pending is retained with that historical scope; later
independent and final root reviews remain distinct. The full 258-entry
surface admission is referenced by its hash and prior safe projection rather
than duplicated. Native commands, private runtime paths, process identifiers,
binaries, complete logs and mesh arrays remain outside this capsule. No
release-source/build attestation for the installed Gmsh binary is inferred.

Verify the sealed public payload and resource bookkeeping from the repository
root without native execution:

```sh
python3 - <<'PYVERIFY'
from pathlib import Path
import hashlib, json
base = Path('twins/962-cylinder-head-f0/derived/engineering/analysis-quality-volume-sized')
r = json.loads((base / 'receipt.json').read_text())
for name, digest in r['payload_sha256'].items():
    p = base / name
    assert p.is_file() and not p.is_symlink()
    assert hashlib.sha256(p.read_bytes()).hexdigest() == digest, name
assert {str(p.relative_to(base)) for p in base.rglob('*') if p.is_file()} == set(r['payload_sha256']) | {'receipt.json'}
s = json.loads((base / 'resource-summary.json').read_text())
for name, role in [('native-resource-samples.json', 'native_trial'), ('readback-resource-samples.json', 'independent_saved_file_readback')]:
    samples = json.loads((base / name).read_text())['samples']
    assert len(samples) == s[role]['sample_count']
    assert max(v['RSS_bytes'] for v in samples) == s[role]['max_observed_RSS_bytes']
o = json.loads((base / 'outcome.json').read_text())
assert o['SICN_gate_passed'] is False
assert o['tetrahedra_below_point1'] == 284806
assert o['fixed_boundary_only_nonpositive_cells'] is True
print('Public payload/resources agree; sized mesh remains quality rejected.')
PYVERIFY
```

Hash checks do not reproduce native geometry. The
[mutable engineering overview](../../../ANALYSIS_QUALITY_ENGINEERING.md)
provides navigation outside this sealed payload.
