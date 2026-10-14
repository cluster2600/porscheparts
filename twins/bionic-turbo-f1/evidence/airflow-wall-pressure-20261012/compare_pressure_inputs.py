"""Verify the single prescribed pressure-boundary change against the pinned control."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha

base = Path('work/bionic-airflow-20261012')
a, b = (base / name for name in ('directed-equilibrium-044', 'wall-flux-pressure-051'))
manifests = [json.loads((case / 'manifest.json').read_text()) for case in (a, b)]
assert manifests[0]['criteria'] == manifests[1]['criteria']
assert set(manifests[0]['file_sha256']) == set(manifests[1]['file_sha256'])
for case, manifest in zip((a, b), manifests):
    assert all(sha(case / name) == digest for name, digest in manifest['file_sha256'].items())
changed = [name for name in manifests[0]['file_sha256'] if sha(a / name) != sha(b / name)]
assert changed == ['0/p']
old, new = 'walls {type zeroGradient;}', 'walls {type fixedFluxPressure; value uniform 101325;}'
assert (a / '0/p').read_text().count(old) == 1
assert (a / '0/p').read_text().replace(old, new) == (b / '0/p').read_text()
result = dict(source_sha256=sha(Path(__file__)), cases=[str(a), str(b)],
              manifests_sha256=[sha(case / 'manifest.json') for case in (a, b)],
              changed_inputs=changed, exact_pressure_substitution=True,
              unchanged_criteria=manifests[0]['criteria'], physical_performance_validated=False)
with Path(__file__).with_name('paired-inputs.json').open('x') as stream:
    json.dump(result, stream, indent=2)
print(json.dumps(result))
