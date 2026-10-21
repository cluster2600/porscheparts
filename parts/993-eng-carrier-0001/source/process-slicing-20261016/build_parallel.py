"""Prepare admitted support geometry and publish four-process layers in their original order."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

SOURCE = Path(__file__).resolve().parent
sys.path.insert(0, str(SOURCE.parent / 'process-skins-20261016'))
from build_pyslm_skins import build, CORE
from parallel_layers import ParallelLayers


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(source, output, expected=None, identity=None, reuse=None, workers=4):
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError('Use a fresh build preparation directory')
    spec = importlib.util.spec_from_file_location('carrier_parallel_parameters', CORE)
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    extensions = [SOURCE / name for name in ('build_parallel.py', 'parallel_layers.py', 'layers.py')]
    frozen = {str(path): sha(path) for path in extensions}
    calculate = ParallelLayers(core.PARAMETERS, workers=workers)
    try:
        with calculate:
            report = build(source, output, expected, identity, reuse,
                           layer_generator=calculate, extra_sources=extensions)
    finally:
        if output.is_dir():
            (output / 'parallel-runtime.json').write_text(json.dumps(calculate.receipt(), indent=2, allow_nan=False) + '\n')
    if frozen != {str(path): sha(path) for path in extensions}:
        raise ValueError('Parallel slicing source changed during the build')
    receipt = calculate.receipt()
    if (not receipt['worker_group_closed'] or receipt['completed_layers'] != report['n_layers']
            or receipt['completed_layers'] != receipt['declared_layers']):
        raise ValueError('All declared layers and worker cleanup must complete')
    report['parallel_slicing'] = receipt
    report['outputs_sha256']['parallel-runtime.json'] = sha(output / 'parallel-runtime.json')
    # The outer entry point finishes the fresh stage before its workflow receipt is sealed.
    (output / 'report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    identity = parser.add_mutually_exclusive_group(required=True)
    identity.add_argument('--sha256')
    identity.add_argument('--identity-receipt', type=Path)
    parser.add_argument('--reuse-supports', type=Path)
    parser.add_argument('--workers', type=int, choices=(1, 2, 4), default=4)
    args = parser.parse_args()
    report = run(args.input, args.output, args.sha256, args.identity_receipt, args.reuse_supports, args.workers)
    print(json.dumps({key: report[key] for key in ('status', 'n_layers', 'part_hatch_segments', 'support_scan_segments')}))
