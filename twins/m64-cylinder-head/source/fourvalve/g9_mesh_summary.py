#!/usr/bin/env python3
"""Compare G9 mesh observables; do not equate stabilization with qualification."""
import hashlib
import json
import math
from pathlib import Path
import sys


def summarize(report):
    rows = {(r['case'], r['direction']): r for r in report['cases']}
    expected = {('witness-2.0', 'x')} | {(c+'-'+str(s), d)
        for c in ('central_diaphragm', 'carrier_base_p') for s in (3., 2., 1.5) for d in ('x', 'minus_z')}
    if (report.get('complete') is not True or set(rows) != expected
            or len(rows) != len(report['cases'])
            or not all(r['numerical_crosscheck_passed'] for r in rows.values())):
        raise ValueError('complete, unique, cross-checked 13-case campaign required')
    groups = []
    for component in ('central_diaphragm', 'carrier_base_p'):
        for direction in ('x', 'minus_z'):
            values = [rows[component+'-'+str(s), direction]['mechanics'] for s in (3., 2., 1.5)]
            medium, fine = values[1:]
            displacement_changes = []
            for side in ('intake', 'exhaust'):
                u = fine['journal_weighted_displacement_mm'][side]
                v = medium['journal_weighted_displacement_mm'][side]
                if len(u) != 3 or len(v) != 3 or not all(map(math.isfinite, u+v)) or math.hypot(*u) <= 0:
                    raise ValueError('invalid journal displacement')
                displacement_changes.append(math.dist(u, v)/math.hypot(*u))
            stress_changes = {}
            for metric in ('von_Mises_p95_MPa', 'von_Mises_max_MPa'):
                a, b = medium[metric], fine[metric]
                if not all(math.isfinite(v) and v > 0 for v in (a, b)):
                    raise ValueError('invalid stress statistic')
                stress_changes[metric] = abs(a-b)/b
            motion = max(math.hypot(*fine['journal_weighted_displacement_mm'][s]) for s in ('intake', 'exhaust'))
            groups.append({'component': component, 'direction': direction,
                'medium_to_fine_max_journal_vector_change': max(displacement_changes),
                'medium_to_fine_stress_change': stress_changes,
                'selected_observables_stabilized': max(displacement_changes) <= .01 and stress_changes['von_Mises_p95_MPa'] <= .05,
                'fine_max_journal_motion_mm': motion, 'G7_working_motion_screen_passed': motion <= .04})
    return {'classification': 'G9_mesh_observable_comparison_not_discretization_error_bound',
            'manufacturing_authorized': False, 'engine_start_authorized': False,
            'thresholds': {'relative_journal_vector_change': .01, 'relative_stress_p95_change': .05,
                           'G7_working_journal_motion_mm': .04},
            'maximum_stress_convergence_qualified': False, 'groups': groups}


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('usage: g9_mesh_summary.py REPORT NEW_SUMMARY')
    source, output = map(Path, sys.argv[1:])
    result = summarize(json.loads(source.read_text()))
    result['campaign_sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
    result['source_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    with output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
