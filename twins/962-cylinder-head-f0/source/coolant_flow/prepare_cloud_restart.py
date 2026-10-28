"""Prepare a bounded MPI comparison from an independently audited checkpoint."""
import argparse
import json
from pathlib import Path
import re
import shutil

from prepare_restart import sha, verify


def prepare(parent, audit_path, output, ranks, iterations, seconds):
    if ranks not in (4, 8, 16, 32) or not 100 <= iterations <= 20000 or not 60 <= seconds <= 7200:
        raise ValueError('Unsupported rank count, iteration count or solver deadline')
    old = json.loads((parent / 'case-report.json').read_text())
    mesh = json.loads((parent / 'mesh-report.json').read_text())
    audit = json.loads(audit_path.read_text())
    if (audit['status'] != 'audited_isothermal_restart_not_physical_validation'
            or audit['case_report_sha256'] != sha(parent / 'case-report.json')
            or audit['mesh_report_sha256'] != sha(parent / 'mesh-report.json')
            or audit['cells'] != mesh['cells'] or mesh['cells'] != old['cells']
            or mesh['status'] != 'mesh_numerical_gate_passed_not_physical_validation'
            or audit['positive_turbulence_fields'] is not True
            or old['residual_target'] != 1e-5):
        raise ValueError('Missing bound checkpoint, mesh admission or original residual target')
    for record, key in ((old, 'case_hashes'), (mesh, 'source_hashes'),
                        (audit, 'history_hashes'), (audit, 'log_hashes')):
        verify(parent, record[key])
    time = audit['saved_iteration']
    if type(time) not in (int, float) or not float(time).is_integer() or not old['start_iteration'] < time <= old['end_iteration']:
        raise ValueError('Expected an advanced integer checkpoint')
    saved = str(int(time))
    if set(audit['final_field_hashes']) != {'U', 'p', 'phi', 'k', 'omega', 'nut'}:
        raise ValueError('Incomplete checkpoint fields')
    verify(parent / saved, audit['final_field_hashes'])
    control = (parent / 'system/controlDict').read_text()
    decompose = (parent / 'system/decomposeParDict').read_text()
    for pattern in (r'\bstartTime\s+\d+\s*;', r'\bendTime\s+\d+\s*;'):
        if len(re.findall(pattern, control)) != 1:
            raise ValueError('Ambiguous iteration controls')
    if len(re.findall(r'\bnumberOfSubdomains\s+\d+\s*;', decompose)) != 1:
        raise ValueError('Ambiguous MPI decomposition')
    if output.exists():
        raise ValueError('Cloud restart output must be fresh')
    output.mkdir(parents=True)
    for name in ('constant', 'system', saved):
        shutil.copytree(parent / name, output / name)
    for name in ('case-report.json', 'mesh-report.json'):
        shutil.copy2(parent / name, output / ('parent-' + name))
    shutil.copy2(audit_path, output / 'parent-audit.json')
    shutil.copy2(parent / 'accept_mesh.py', output / 'accept_mesh.py')
    runner = Path(__file__).with_name('run_cloud_restart.sh')
    shutil.copy2(runner, output / runner.name)
    control = re.sub(r'\bstartTime\s+\d+\s*;', 'startTime ' + saved + ';', control)
    control = re.sub(r'\bendTime\s+\d+\s*;', 'endTime ' + str(int(time) + iterations) + ';', control)
    (output / 'system/controlDict').write_text(control)
    (output / 'system/decomposeParDict').write_text(re.sub(
        r'\bnumberOfSubdomains\s+\d+\s*;', 'numberOfSubdomains ' + str(ranks) + ';', decompose))
    report = dict(old)
    report.update(status='prepared_cloud_restart_not_launched', start_iteration=int(time),
        end_iteration=int(time) + iterations, parallel_ranks=ranks, planned_processes=ranks,
        maximum_solver_seconds=seconds, parent_case_report_sha256=sha(parent / 'case-report.json'),
        parent_mesh_report_sha256=sha(parent / 'mesh-report.json'), parent_audit_sha256=sha(audit_path),
        checkpoint_field_hashes=audit['final_field_hashes'],
        paid_instance_created=False, manufacturing_authorized=False)
    report['source_hashes'] = dict(old['source_hashes'])
    for path in (Path(__file__), runner):
        report['source_hashes'][path.name] = sha(path)
    report['case_hashes'] = {str(p.relative_to(output)): sha(p)
        for p in sorted(output.rglob('*')) if p.is_file()}
    (output / 'case-report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    (output / 'case.foam').touch()
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('parent', 'audit', 'output'):
        parser.add_argument(name, type=Path)
    parser.add_argument('--ranks', type=int, required=True)
    parser.add_argument('--iterations', type=int, required=True)
    parser.add_argument('--seconds', type=int, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.parent.resolve(), args.audit.resolve(), args.output.resolve(),
                             args.ranks, args.iterations, args.seconds), indent=2))
