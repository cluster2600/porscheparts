"""Compare the unchanged full-mesh path with Z-filtered native slicing."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import time

import numpy as np
import pyslm
import layers

SOURCE = Path(__file__).resolve().parent
HISTORICAL = SOURCE.parent / 'process-20261016/build_pyslm.py'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def equal_result(first, second):
    return (len(first[0]) == len(second[0]) and len(first[1]) == len(second[1])
            and all(np.array_equal(a, b) for a, b in zip(first[0], second[0]))
            and all(np.array_equal(a, b) for a, b in zip(first[1], second[1]))
            and np.array_equal(first[2], second[2]) and first[3] == second[3])


def benchmark(source, expected, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    if sha(source) != expected:
        raise ValueError('Input mesh identity mismatch')
    spec = importlib.util.spec_from_file_location('historical_pyslm_slicing', HISTORICAL)
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    mesh = old.exact_mesh(source)
    part = pyslm.Part('slice-comparison')
    part.setGeometry(mesh, fixGeometry=False, mergeVertices=False)
    part.rotation = old.PARAMETERS['rotation_degrees_xyz']
    part.dropToPlatform(old.PARAMETERS['support_gap_mm'])
    started = time.monotonic()
    bounds = layers.face_z_bounds(part.geometry)
    preparation_seconds = time.monotonic() - started
    output.mkdir(parents=True, exist_ok=False)
    frozen = {p.name: sha(p) for p in (Path(__file__), SOURCE / 'layers.py', HISTORICAL)}
    for path in (Path(__file__), SOURCE / 'layers.py'):
        shutil.copyfile(path, output / path.name)
    rows = []
    # Actual layer midplanes, fixed before the benchmark and independent of timing.
    for index in [0, 166, 167, 299, 518, 701, 900, 1033]:
        z = (index + .5) * old.PARAMETERS['layer_height_mm']
        started = time.monotonic()
        reference = old.layer_geometry(part, z)
        old_seconds = time.monotonic() - started
        started = time.monotonic()
        candidate = layers.layer_geometry(part, z, old.PARAMETERS, bounds)
        new_seconds = time.monotonic() - started
        same = equal_result(reference, candidate)
        row = {'layer': index, 'z_mm': z, 'full_seconds': old_seconds,
               'filtered_seconds': new_seconds, 'arrays_and_path_order_exactly_equal': same,
               'part_area_mm2': candidate[3], 'boundary_count': len(candidate[0]),
               'hatch_segments': len(candidate[2])}
        rows.append(row)
        print(json.dumps(row), flush=True)
        if not same:
            raise ValueError('Filtered slicing changed contours, ordering, hatch vectors or area')
    if sha(source) != expected or frozen != {p.name: sha(p) for p in (Path(__file__), SOURCE / 'layers.py', HISTORICAL)}:
        raise ValueError('Input or source changed during the benchmark')
    old_total = sum(row['full_seconds'] for row in rows)
    new_total = sum(row['filtered_seconds'] for row in rows)
    receipt = {'status': 'passed', 'input_sha256': expected, 'source_sha256': frozen,
               'preparation_seconds': preparation_seconds, 'rows': rows,
               'total_full_seconds': old_total, 'total_filtered_seconds': new_total,
               'observed_speedup_including_preparation': old_total / (new_total + preparation_seconds),
               'same_native_implementation_and_tolerance': True,
               'equivalence_scope': 'Eight fixed real carrier midplanes; all path coordinates, ordering, hatch vectors and polygon areas compared exactly.'}
    (output / 'benchmark.json').write_text(json.dumps(receipt, indent=2, allow_nan=False) + '\n')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--sha256', required=True)
    args = parser.parse_args()
    benchmark(args.source, args.sha256, args.output)
