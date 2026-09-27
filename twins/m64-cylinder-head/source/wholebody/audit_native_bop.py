#!/usr/bin/env python3
"""Error-aware companion to the frozen native checker; no geometry modification."""
import argparse
from collections import Counter
import json
from pathlib import Path
import signal
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import profile_strict_check as native


def admitted(result):
    return (result.get('exact_valid') is True and type(result.get('solids')) is int and result['solids'] == 1
            and result.get('has_faulty') is False and result.get('has_errors') is False
            and result.get('has_warnings') is False and result.get('inputs_unchanged') is True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--sha256', required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.output.exists() or native.sha(args.input) != args.sha256:
        raise ValueError('fresh_output_and_exact_input_required')
    import OCP
    from OCP.BOPAlgo import BOPAlgo_ArgumentAnalyzer
    signal.alarm(300)
    start = time.monotonic()
    shape = native.read_shape(args.input)
    result = {'schema': 'm64-native-error-aware-bop/v1', 'input_sha256': args.sha256,
              'source_sha256': native.sha(__file__), 'helper_sha256': native.sha(native.__file__),
              'OCP_version': OCP.__version__, 'manufacturing_authorized': False,
              'exact_valid': native.brepcheck(shape, True)['valid'],
              'tolerances': native.tolerances(shape), 'selected_modes': list(native.BOP_OPTIONS)}
    result['solids'] = result['tolerances']['solids']
    checker = BOPAlgo_ArgumentAnalyzer()
    checker.SetShape1(shape)
    for name in native.BOP_OPTIONS:
        setattr(checker, name, True)
    checker.Perform()
    result.update(has_faulty=bool(checker.HasFaulty()), has_errors=bool(checker.HasErrors()),
                  has_warnings=bool(checker.HasWarnings()),
                  fault_counts=dict(Counter(str(r.GetCheckStatus()) for r in checker.GetCheckResult())),
                  inputs_unchanged=native.sha(args.input) == args.sha256,
                  wall_seconds=time.monotonic()-start)
    result['passed'] = admitted(result)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps({k: result[k] for k in ('passed', 'has_faulty', 'has_errors', 'has_warnings', 'wall_seconds')}))
    return 0 if result['passed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
