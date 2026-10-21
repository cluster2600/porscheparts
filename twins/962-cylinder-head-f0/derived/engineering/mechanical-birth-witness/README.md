# Mechanical birth and support-release software evidence

**Hypothetical numerical verification only. No head, calibrated alloy/process or manufacturing authorization.**

The exact native attempt002 completed six equilibrium solves in 0.668 s. All
5514 numerical comparisons pass, including 4224 tensor components across every
active 2 x 2 x 2 Gauss point and all active nodal displacement/history/reaction values.
Old material retains its plastic strain; new material initializes relative to
its declared birth field. End support release gives zero stress and 0.037 mm
end displacement, matching the pre-native reference. These are software
verification results, not cylinder-head/LPBF predictions.

The accepted freeze, initial freeze, original checker and assessment remain
byte-identical to their retained originals. Attempt 001 was an input-wiring
refusal before any timestep. Attempt 002 only disables inherited displacement
coupling on the inactive placeholder kernel; it changes no material law,
reference, geometry or tolerance. The original and hardened assessments have
identical numerical results. Later hardening adds exact quadrature identity,
complete artifact-manifest coverage and authentication against the independently
recorded original capture/receipt digests. Thirteen focused tests pass.

`native-provenance.json` is a whitelist projection of runtime/command receipt
metadata. It retains original receipt/capture hashes and complete native
filename-to-hash maps, including the unpublished Exodus file. Commands,
private host/user paths, access identities and raw transport captures are
excluded. The portable wrapper is later source and did not produce the
original SSH run. No native solve was repeated for checker hardening.

The receipt hashes every delivered file. Reproduce numerical comparisons
using only Python's standard library, from the repository root:

```sh
python3 -B - <<'PYTHON'
from pathlib import Path
import hashlib,importlib.util,json
p=Path('twins/962-cylinder-head-f0/derived/engineering/mechanical-birth-witness')
r=json.loads((p/'receipt.json').read_text())
for name,digest in r['artifact_sha256'].items():
    assert hashlib.sha256((p/name).read_bytes()).hexdigest()==digest,name
spec=importlib.util.spec_from_file_location('witness',p/'source-snapshots/hardened-assess.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
frozen=json.loads((p/'accepted-frozen-contract.json').read_text())
a=m.assess_fields(p/'data',frozen)
assert a['passed'] and a['field_comparisons']==5514
print(a['status'],a['field_comparisons'],a['max_absolute_errors'])
PYTHON
```

This reproduces all field/reference comparisons. Full original native/capture
attestation additionally requires the retained private bundle and the complete
`assess.py` command in the source README; public hash-only projections do not
reconstruct private transport contents. They are not third-party signatures.
The catalogue and manufacturing qualification remain unchanged.
