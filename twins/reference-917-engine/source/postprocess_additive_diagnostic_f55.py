#!/usr/bin/env python3
"""Report observed temperatures and absorbed power without qualifying a recipe."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re


def evaluate(case):
    bounds = case / 'postProcessing/diagnosticTemperatureBounds/0/volFieldValue.dat'
    log = case / 'diagnostic-run.log'
    rows = [tuple(map(float, line.split())) for line in bounds.read_text().splitlines()
            if line.strip() and not line.lstrip().startswith('#')]
    if not rows or any(not math.isfinite(v) for row in rows for v in row):
        raise ValueError('invalid diagnostic samples')
    text = log.read_text()
    powers = [float(v) for v in re.findall(r'^absorbed power:\s*([0-9.eE+-]+)', text, re.MULTILINE)]
    times = [float(v) for v in re.findall(r'^Time =\s*([0-9.eE+-]+)', text, re.MULTILINE)]
    if not powers or not times or any(not math.isfinite(v) for v in powers + times):
        raise ValueError('missing or nonfinite runtime values')
    return {'case': case.name, 'temperature_max_k': max(r[1] for r in rows),
            'temperature_final_k': rows[-1][1], 'final_sample_time_s': rows[-1][0],
            'final_log_time_s': times[-1], 'absorbed_power_max_w': max(powers),
            'absorbed_power_final_w': powers[-1],
            'final_time_reached': abs(times[-1]-.00012)<1e-12 and abs(rows[-1][0]-.00012)<1e-12,
            'fatal_error_in_log': 'FOAM FATAL' in text,
            'evidence_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (bounds, log)},
            'process_qualified': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases', type=Path, nargs='+', required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise FileExistsError(a.output)
    report = {'schema': 'porsche-additive-cap-diagnostic-results-f55/v1',
              'cases': [evaluate(case) for case in a.cases],
              'classification': 'short_local_thermal_sensitivity_not_full_head_LPBF',
              'three_grid_melt_volume_convergence_proven': False,
              'supplier_recipe_calibrated': False, 'manufacturing_authorized': False}
    a.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
