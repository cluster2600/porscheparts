"""Compare completed rest controls using their original criteria and verified payloads."""
import json
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
from static_mrf_witness import assess

results = []
for name in ('directed-equilibrium-044', 'wall-flux-pressure-051'):
    case = Path('work/bionic-airflow-20261012') / name
    receipt = json.loads((case / 'report.json').read_text())
    manifest = json.loads((case / 'manifest.json').read_text())
    assert receipt['native_exit_code'] == 0 and receipt['native_end']
    assert sha(case / 'manifest.json') == receipt['manifest_sha256']
    for path, digest in receipt['output_sha256'].items():
        assert sha(case / path) == digest
    low = np.loadtxt(case / 'postProcessing/minima/0/volFieldValue.dat')
    high = np.loadtxt(case / 'postProcessing/maxima/0/volFieldValue.dat')
    assert low.shape == high.shape == (200, 4)
    assert np.array_equal(low[:, 0], high[:, 0]) and abs(high[-1, 0] - 2e-5) < 1e-15
    result = assess(low, high, manifest['criteria'])
    assert result['observed'] == receipt['observed']
    exceeding = high[:, 3] > manifest['criteria']['max_speed_m_s'] ** 2
    result.update(case=name, receipt_sha256=sha(case / 'report.json'),
                  first_speed_threshold_exceedance_s=float(high[exceeding, 0][0]) if exceeding.any() else None)
    results.append(result)
output = dict(source_sha256=sha(Path(__file__)), controls=results, physical_performance_validated=False)
with Path(__file__).with_name('history-comparison.json').open('x') as stream:
    json.dump(output, stream, indent=2)
print(json.dumps(output))
