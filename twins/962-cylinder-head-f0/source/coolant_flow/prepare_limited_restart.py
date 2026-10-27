"""Compare limited non-orthogonal corrections on the same frozen iteration-900 seed."""
import argparse
import json
from pathlib import Path

from prepare_restart import prepare, sha


def prepare_limited(parent, stop, output):
    report = prepare(parent, stop, output)
    path = output / 'system/fvSchemes'
    text = path.read_text()
    for before, after in (
        ('laplacianSchemes { default Gauss linear corrected; }',
         'laplacianSchemes { default Gauss linear limited corrected 0.5; }'),
        ('snGradSchemes { default corrected; }',
         'snGradSchemes { default limited corrected 0.5; }')):
        if text.count(before) != 1:
            raise ValueError('Unexpected parent normal-gradient scheme')
        text = text.replace(before, after)
    path.write_text(text)
    report['non_orthogonal_correction_limiter'] = .5
    report['source_hashes'][Path(__file__).name] = sha(Path(__file__))
    report['case_hashes']['system/fvSchemes'] = sha(path)
    (output / 'case-report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('parent', 'stop', 'output'): parser.add_argument(name, type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare_limited(*(p.resolve() for p in
        (args.parent, args.stop, args.output))), indent=2))
