"""Prepare a separate four-rank restart from the frozen case-015 iteration 900."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(root, hashes):
    for name, digest in hashes.items():
        path = root / name
        if not path.resolve().is_relative_to(root.resolve()) or sha(path) != digest:
            raise ValueError('Changed or invalid input: ' + name)


def prepare(parent, stop_report, output):
    stop = json.loads(stop_report.read_text())
    if stop['latest_saved_iteration'] != 900 or stop['simple_residual_control_satisfied']:
        raise ValueError('Expected the unconverged iteration-900 snapshot')
    if sha(parent / 'case-report.json') != stop['case_report_sha256']:
        raise ValueError('Parent case receipt changed')
    if sha(parent / 'mesh-report.json') != stop['native_mesh_receipt_sha256']:
        raise ValueError('Parent mesh receipt changed')
    old = json.loads((parent / 'case-report.json').read_text())
    mesh = json.loads((parent / 'mesh-report.json').read_text())
    verify(parent, old['case_hashes'])
    verify(parent, mesh['source_hashes'])
    verify(parent / '900', stop['latest_saved_field_hashes'])
    if set(stop['latest_saved_field_hashes']) != {'U', 'p', 'phi', 'k', 'omega', 'nut'}:
        raise ValueError('Incomplete restart fields')
    if mesh['status'] != 'mesh_numerical_gate_passed_not_physical_validation':
        raise ValueError('Parent mesh has no admission receipt')
    if output.exists():
        raise ValueError('Restart output must be a fresh directory')
    output.mkdir(parents=True)
    for name in ('constant', 'system', '900'):
        shutil.copytree(parent / name, output / name)
    for name in ('case-report.json', 'mesh-report.json'):
        shutil.copy2(parent / name, output / ('parent-' + name))
    shutil.copy2(stop_report, output / 'parent-stop.json')
    shutil.copy2(parent / 'accept_mesh.py', output / 'accept_mesh.py')
    runner = Path(__file__).with_name('run_restart.sh')
    shutil.copy2(runner, output / runner.name)
    control = output / 'system/controlDict'
    text = control.read_text()
    before = 'startFrom startTime; startTime 0; stopAt endTime; endTime 2000;'
    if text.count(before) != 1:
        raise ValueError('Unexpected parent time controls')
    control.write_text(text.replace(before,
        'startFrom startTime; startTime 900; stopAt endTime; endTime 5000;'))
    solution = output / 'system/fvSolution'
    text = solution.read_text()
    if text.count('nNonOrthogonalCorrectors 0;') != 1:
        raise ValueError('Unexpected parent pressure controls')
    solution.write_text(text.replace('nNonOrthogonalCorrectors 0;',
                                    'nNonOrthogonalCorrectors 2;'))
    report = dict(old)
    report.update(status='prepared_restart_not_a_solver_result',
        cells=mesh['cells'], start_iteration=900, end_iteration=5000,
        non_orthogonal_correctors=2, parallel_ranks=4,
        parent_case_report_sha256=sha(parent / 'case-report.json'),
        parent_mesh_report_sha256=sha(parent / 'mesh-report.json'),
        parent_stop_report_sha256=sha(stop_report),
        source_hashes={p.name: sha(p) for p in (Path(__file__), runner)},
        residual_target=1e-5, maximum_solver_seconds=1800,
        manufacturing_authorized=False)
    report['case_hashes'] = {str(p.relative_to(output)): sha(p)
        for p in sorted(output.rglob('*')) if p.is_file()}
    (output / 'case-report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    (output / 'case.foam').touch()
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('parent', 'stop_report', 'output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(*(p.resolve() for p in
        (args.parent, args.stop_report, args.output))), indent=2))
