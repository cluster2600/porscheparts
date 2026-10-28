"""Bound a short check of absolute pressure linear-solve accuracy on the same checkpoint."""
import argparse
import json
from pathlib import Path

from prepare_damped_checkpoint import prepare_checkpoint
from prepare_restart import sha


def prepare_pilot(parent, audit, output):
    report = prepare_checkpoint(parent, audit, output)
    path = output / 'system/fvSolution'; text = path.read_text()
    before = 'tolerance 1e-8; relTol 0.01; smoother GaussSeidel;'
    runner = output / 'run_restart.sh'; script = runner.read_text()
    deadline = '--kill-after=30s 1800 mpirun'
    if text.count(before) != 1 or script.count(deadline) != 1:
        raise ValueError('Unexpected parent pressure solver or deadline')
    path.write_text(text.replace(before, 'tolerance 1e-10; relTol 0; smoother GaussSeidel;'))
    runner.write_text(script.replace(deadline, '--kill-after=30s 300 mpirun'))
    report.update(status='prepared_absolute_pressure_accuracy_pilot_not_a_result',
        pressure_linear_absolute_tolerance=1e-10, pressure_linear_relative_tolerance=0,
        maximum_solver_seconds=300, maximum_job_seconds_including_kill_grace=330)
    report['source_hashes'][Path(__file__).name] = sha(Path(__file__))
    for name in ('system/fvSolution', 'run_restart.sh'):
        report['case_hashes'][name] = sha(output / name)
    (output / 'case-report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('parent', 'audit', 'output'): parser.add_argument(name, type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare_pilot(*(p.resolve() for p in
        (args.parent, args.audit, args.output))), indent=2))
