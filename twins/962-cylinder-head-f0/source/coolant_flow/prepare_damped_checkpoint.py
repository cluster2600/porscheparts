"""Continue an audited saved state in a fresh case with damped transport equations."""
import argparse
import json
from pathlib import Path
import shutil

from prepare_restart import sha, verify


def prepare_checkpoint(parent, audit_path, output):
    audit = json.loads(audit_path.read_text())
    old = json.loads((parent / 'case-report.json').read_text())
    mesh = json.loads((parent / 'mesh-report.json').read_text())
    if (audit['status'] != 'audited_isothermal_restart_not_physical_validation'
            or audit['case_report_sha256'] != sha(parent / 'case-report.json')
            or audit['mesh_report_sha256'] != sha(parent / 'mesh-report.json')
            or audit['cells'] != mesh['cells'] or audit['cells'] != old['cells']
            or audit['positive_turbulence_fields'] is not True):
        raise ValueError('Missing bound, positive-field checkpoint audit')
    verify(parent, old['case_hashes'])
    verify(parent, mesh['source_hashes'])
    verify(parent, audit['history_hashes'])
    verify(parent, audit['log_hashes'])
    time = audit['saved_iteration']
    if type(time) not in (int, float) or not float(time).is_integer() or not old['start_iteration'] < time < old['end_iteration']:
        raise ValueError('Checkpoint must advance the parent iteration')
    saved = str(int(time))
    if set(audit['final_field_hashes']) != {'U', 'p', 'phi', 'k', 'omega', 'nut'}:
        raise ValueError('Incomplete checkpoint')
    verify(parent / saved, audit['final_field_hashes'])
    control = (parent / 'system/controlDict').read_text()
    start = 'startTime ' + str(old['start_iteration']) + ';'
    solution = (parent / 'system/fvSolution').read_text()
    before = 'equations { U 0.5; k 0.5; omega 0.5; }'
    prototype = Path(__file__).with_name('run_restart.sh')
    runner = prototype.read_text()
    if control.count(start) != 1 or solution.count(before) != 1 or runner.count('-time 900') != 1:
        raise ValueError('Unexpected parent controls or runner prototype')
    if output.exists():
        raise ValueError('Checkpoint output must be fresh')
    output.mkdir(parents=True)
    for name in ('constant', 'system'):
        shutil.copytree(parent / name, output / name)
    (output / saved).mkdir()
    for name in audit['final_field_hashes']:
        shutil.copy2(parent / saved / name, output / saved / name)
    if (parent / saved / 'uniform').exists():
        shutil.copytree(parent / saved / 'uniform', output / saved / 'uniform')
    for name in ('case-report.json', 'mesh-report.json'):
        shutil.copy2(parent / name, output / ('parent-' + name))
    shutil.copy2(audit_path, output / 'parent-audit.json')
    shutil.copy2(parent / 'accept_mesh.py', output / 'accept_mesh.py')
    (output / 'run_restart.sh').write_text(runner.replace('-time 900', '-time ' + saved))
    (output / 'system/controlDict').write_text(control.replace(start, 'startTime ' + saved + ';'))
    (output / 'system/fvSolution').write_text(solution.replace(before,
        'equations { U 0.3; k 0.3; omega 0.3; }'))
    report = dict(old)
    report.update(status='prepared_damped_checkpoint_not_a_solver_result',
        start_iteration=int(time), transport_equation_relaxation=.3,
        parent_case_report_sha256=sha(parent / 'case-report.json'),
        parent_mesh_report_sha256=sha(parent / 'mesh-report.json'),
        parent_audit_sha256=sha(audit_path),
        generated_runner_replacement={'prototype_time': 900, 'checkpoint_time': int(time)},
        manufacturing_authorized=False)
    report['source_hashes'] = dict(old['source_hashes'])
    for p in (Path(__file__), prototype): report['source_hashes'][p.name] = sha(p)
    report['case_hashes'] = {str(p.relative_to(output)): sha(p)
        for p in sorted(output.rglob('*')) if p.is_file()}
    (output / 'case-report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    (output / 'case.foam').touch()
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('parent', 'audit', 'output'): parser.add_argument(name, type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare_checkpoint(*(p.resolve() for p in
        (args.parent, args.audit, args.output))), indent=2))
