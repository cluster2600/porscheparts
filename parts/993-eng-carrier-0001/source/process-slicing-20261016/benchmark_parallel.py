"""Check ordered four-process slicing against the original carrier midplanes."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import time

import pyslm
from benchmark import equal_result, sha, HISTORICAL, SOURCE
from parallel_layers import ParallelLayers


def run(source, expected, output, workers):
    source, output = Path(source).resolve(), Path(output).resolve()
    if sha(source) != expected:
        raise ValueError('Input mesh identity mismatch')
    spec = importlib.util.spec_from_file_location('historical_slicing', HISTORICAL)
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    part = pyslm.Part('parallel-slice-comparison')
    part.setGeometry(old.exact_mesh(source), fixGeometry=False, mergeVertices=False)
    part.rotation = old.PARAMETERS['rotation_degrees_xyz']
    part.dropToPlatform(old.PARAMETERS['support_gap_mm'])
    indices = [0, 166, 167, 299, 518, 701, 900, 1033]
    heights = [(i + .5) * old.PARAMETERS['layer_height_mm'] for i in indices]
    sources = [Path(__file__), SOURCE / 'benchmark.py', SOURCE / 'layers.py', SOURCE / 'parallel_layers.py', HISTORICAL]
    frozen = {p.name: sha(p) for p in sources}
    output.mkdir(parents=True, exist_ok=False)
    for path in sources:
        shutil.copyfile(path, output / path.name)
    started = time.monotonic()
    reference = [old.layer_geometry(part, z) for z in heights]
    serial_seconds = time.monotonic() - started
    checks = []
    with ParallelLayers(old.PARAMETERS, workers=workers, heights=heights) as calculate:
        for i, z, first in zip(indices, heights, reference):
            candidate = calculate(part, z)
            same = equal_result(first, candidate)
            checks.append({'layer': i, 'z_mm': z, 'all_arrays_area_and_order_exactly_equal': same})
            if not same:
                raise ValueError('Parallel slicing changed a declared layer')
    if sha(source) != expected or frozen != {p.name: sha(p) for p in sources}:
        raise ValueError('Input or source changed during slicing comparison')
    receipt = {'status': 'passed', 'input_sha256': expected, 'sources_sha256': frozen,
               'checks': checks, 'serial_seconds': serial_seconds, 'parallel': calculate.receipt(),
               'observed_eight_layer_speedup_including_worker_startup': serial_seconds / calculate.receipt()['elapsed_seconds'],
               'scope': 'Exact native outputs on eight predetermined real carrier planes; timing includes process startup, not a full-build time claim.'}
    (output / 'assessment.json').write_text(json.dumps(receipt, indent=2, allow_nan=False) + '\n')
    print(json.dumps(receipt))
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--workers', type=int, choices=(1, 2, 4), default=4)
    args = parser.parse_args()
    run(args.source, args.sha256, args.output, args.workers)
