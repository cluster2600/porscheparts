"""Compare full pressure updates in the existing consistent pressure/velocity algorithm."""
import argparse
import json
from pathlib import Path

from prepare_limited_restart import prepare_limited
from prepare_restart import sha


def prepare_consistent(parent, stop, output):
    report = prepare_limited(parent, stop, output)
    path = output / 'system/fvSolution'; text = path.read_text()
    if text.count('consistent yes;') != 1 or text.count('fields { p 0.3; }') != 1:
        raise ValueError('Unexpected consistent algorithm or pressure relaxation')
    path.write_text(text.replace('fields { p 0.3; }', 'fields { p 1; }'))
    report['pressure_field_relaxation'] = 1
    report['source_hashes'][Path(__file__).name] = sha(Path(__file__))
    report['case_hashes']['system/fvSolution'] = sha(path)
    (output / 'case-report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('parent', 'stop', 'output'): parser.add_argument(name, type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare_consistent(*(p.resolve() for p in
        (args.parent, args.stop, args.output))), indent=2))
