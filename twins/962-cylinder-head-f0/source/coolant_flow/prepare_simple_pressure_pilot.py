"""Compare classical SIMPLE with fully resolved pressure on the same audited state."""
import argparse
import json
from pathlib import Path

from prepare_precise_pressure_pilot import prepare_pilot
from prepare_restart import sha


def prepare_simple(parent, audit, output):
    report = prepare_pilot(parent, audit, output)
    path = output / 'system/fvSolution'; text = path.read_text()
    control = output / 'system/controlDict'; controls = control.read_text()
    if text.count('consistent yes;') != 1 or controls.count('writeInterval 100;') != 1:
        raise ValueError('Unexpected consistent algorithm or output interval')
    path.write_text(text.replace('consistent yes;', 'consistent no;'))
    control.write_text(controls.replace('writeInterval 100;', 'writeInterval 10;'))
    report.update(status='prepared_classical_simple_pressure_pilot_not_a_result',
        consistent_pressure_velocity=False, write_interval=10)
    report['source_hashes'][Path(__file__).name] = sha(Path(__file__))
    for name in ('system/fvSolution', 'system/controlDict'):
        report['case_hashes'][name] = sha(output / name)
    (output / 'case-report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('parent', 'audit', 'output'): parser.add_argument(name, type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare_simple(*(p.resolve() for p in
        (args.parent, args.audit, args.output))), indent=2))
