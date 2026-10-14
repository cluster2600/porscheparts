#!/usr/bin/env python3
"""Check conditional MRF results; solver completion never grants engineering approval."""
import argparse
import json
import math
from pathlib import Path
import re
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'twins/reference-917-engine/source'))
from publish_aircooled_4v_f34 import dump, last_rows, relative_difference, require_local_unpublished_output, sha256


def assess(case):
    case = Path(case).resolve()
    metadata = json.loads((case / 'case-metadata.json').read_text())
    if metadata['classification'] != 'conditional_square_duct_not_935_installation':
        raise ValueError('Expected conditional test duct metadata')
    inputs = metadata['prepared_input_sha256']
    required = {'system/controlDict', 'system/fvSolution', 'system/fvSchemes', 'constant/MRFProperties',
                'constant/triSurface/rotor.stl', '0/U', '0/p', '0/k', '0/omega', '0/nut'}
    if not required.issubset(inputs) or any(Path(p).is_absolute() or '..' in Path(p).parts or
                         not (case / p).resolve().is_relative_to(case) or
                         sha256(case / p) != digest for p, digest in inputs.items()):
        raise ValueError('Prepared CFD inputs changed')
    solver = (case / 'simpleFoam.log').read_text()
    if ((case / 'solver.exit').read_text().strip() != '0' or
        not re.search(r'^End\s*$', solver, re.M) or 'FOAM FATAL' in solver or
        'Mesh OK.' not in (case / 'checkMesh.log').read_text()):
        raise ValueError('Completed solver and accepted mesh logs required')
    q, rho, rpm = (metadata[k] for k in ('specified_volume_flow_m3_s', 'density_kg_m3', 'rotor_rpm'))
    if any(isinstance(x, bool) or not math.isfinite(x) for x in (q, rho, rpm)) or q <= 0 or rho <= 0 or rpm == 0:
        raise ValueError('Finite operating conditions required')
    rows, hashes = {}, {}
    for name, filename, columns in [('inletFlow','surfaceFieldValue.dat',2), ('outletFlow','surfaceFieldValue.dat',2),
        ('inletPressure','surfaceFieldValue.dat',3), ('outletPressure','surfaceFieldValue.dat',3), ('forces','moment.dat',10)]:
        files = list((case / 'postProcessing' / name).glob('*/' + filename))
        rows[name] = [list(map(float, row)) for row in last_rows(case / 'postProcessing' / name, '*/' + filename)]
        if not rows[name] or any(len(row) != columns or not all(math.isfinite(x) for x in row) for row in rows[name]):
            raise ValueError('Missing, malformed or nonfinite CFD history')
        hashes.update({str(p.relative_to(case)):sha256(p) for p in files})
    times = [row[0] for row in rows['inletFlow']]
    end = re.search(r'\bendTime\s+([0-9.]+)\s*;', (case / 'system/controlDict').read_text())
    if not end or times[-1] != float(end[1]):
        raise ValueError('Histories do not reach the prescribed final iteration')
    if any([row[0] for row in values] != times for values in rows.values()):
        raise ValueError('CFD histories have different sampling times')
    series = []
    for i, time in enumerate(times):
        inlet, outlet = rows['inletPressure'][i], rows['outletPressure'][i]
        if inlet[2] < 0 or outlet[2] < 0:
            raise ValueError('Negative squared velocity')
        flow_in, flow_out = rows['inletFlow'][i][1], rows['outletFlow'][i][1]
        series.append({'iteration':time, 'total_pressure_rise_Pa':rho*(outlet[1]-inlet[1]+(outlet[2]-inlet[2])/2),
            'resisting_torque_z_Nm':-rows['forces'][i][3],
            'mass_imbalance_relative':abs(flow_in+flow_out)/q,
            'imposed_flow_relative_error':max(abs(flow_in+q),abs(flow_out-q))/q})
    last = times[-1]
    windows = [[row for row in series if last-upper < row['iteration'] <= last-lower]
               for lower, upper in ((0,100),(100,200))]
    if any(len(w) < 10 or w[-1]['iteration']-w[0]['iteration'] < 90 for w in windows):
        raise ValueError('Two complete 100-iteration sampling windows required')
    metrics = {}
    for name in ('total_pressure_rise_Pa','resisting_torque_z_Nm'):
        values = [[row[name] for row in w] for w in windows]
        mean = statistics.mean(values[0])
        spread = (max(values[0])-min(values[0]))/max(abs(mean),1e-30)
        drift = relative_difference(mean, statistics.mean(values[1]))
        metrics[name] = {'final_window_mean':mean, 'peak_to_peak_relative':spread,
                         'successive_window_mean_relative_change':drift, 'stationarity_pass':spread < .01 and drift < .01}
    mass_error = max(row['mass_imbalance_relative'] for row in windows[0])
    flow_error = max(row['imposed_flow_relative_error'] for row in windows[0])
    return {'classification':metadata['classification'], 'metadata_sha256':sha256(case/'case-metadata.json'),
        'input_digest_capture':metadata.get('input_digest_capture', 'during preparation before solver execution'),
        'prepared_input_sha256':inputs, 'result_sha256':{**hashes, 'simpleFoam.log':sha256(case/'simpleFoam.log'),
                                                       'checkMesh.log':sha256(case/'checkMesh.log')},
        'rotor_sha256':metadata['rotor_sha256'], 'rotor_rpm':rpm, 'specified_volume_flow_m3_s':q,
        'density_kg_m3':rho, 'last_iteration':last, 'window_iterations':100, 'metrics':metrics,
        'maximum_final_window_mass_imbalance_relative':mass_error, 'maximum_imposed_flow_relative_error':flow_error,
        'single_mesh_pilot_pass':mass_error < .001 and flow_error < .001 and all(x['stationarity_pass'] for x in metrics.values()),
        'three_mesh_convergence_established':False, 'accepted_for_935_fan_curve':False,
        'physical_validation':False, 'manufacturing_authorized':False, 'series':series}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    report = assess(args.case)
    out = require_local_unpublished_output(args.output)
    out.mkdir(mode=0o700, parents=True)
    dump(out / 'assessment.json', report)
    print('Conditional single-mesh pilot pass:', report['single_mesh_pilot_pass'])
