"""Add the documented bounded velocity-gradient scheme to the limited-correction case."""
import argparse
import json
from pathlib import Path

from prepare_limited_restart import prepare_limited
from prepare_restart import sha


def prepare_bounded(parent, stop, output):
    report = prepare_limited(parent, stop, output)
    path = output / 'system/fvSchemes'
    text = path.read_text()
    before = 'gradSchemes { default Gauss linear; }'
    if text.count(before) != 1:
        raise ValueError('Unexpected parent velocity-gradient scheme')
    path.write_text(text.replace(before,
        'gradSchemes { default Gauss linear; grad(U) cellLimited Gauss linear 1; }'))
    report['velocity_gradient_limiter'] = 1
    report['source_hashes'][Path(__file__).name] = sha(Path(__file__))
    report['case_hashes']['system/fvSchemes'] = sha(path)
    (output / 'case-report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('parent', 'stop', 'output'): parser.add_argument(name, type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare_bounded(*(p.resolve() for p in
        (args.parent, args.stop, args.output))), indent=2))
