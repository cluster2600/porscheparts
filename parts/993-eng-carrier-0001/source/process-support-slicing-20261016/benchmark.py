"""Compare serial/parallel exact cuts on fixed planes of retained real support sheets."""
import argparse
import json
from pathlib import Path
import time

import numpy as np
import trimesh
from parallel_support_sections import ParallelSupportSections, sha, support_section

INDICES = (0, 166, 167, 299, 500, 518, 701, 900, 1000, 1033)


def benchmark(directory, output):
    directory, output = Path(directory), Path(output)
    checkpoint = json.loads((directory / 'support-stage.json').read_text())
    paths = sorted(directory.glob('support-*.npz'))
    for path in paths:
        if sha(path) != checkpoint['outputs_sha256'][path.name]:
            raise ValueError('Support sheet differs from its retained checkpoint')
    heights = [(index+.5)*checkpoint['parameters']['layer_height_mm'] for index in INDICES]
    surfaces, bounds = [], []
    for path in paths:
        with np.load(path, allow_pickle=False) as data:
            surface = trimesh.Trimesh(data['vertices'], data['faces'], process=False)
        z = surface.vertices[surface.faces, 2]
        surfaces.append(surface)
        bounds.append(np.column_stack((z.min(axis=1), z.max(axis=1))))
    started = time.monotonic()
    expected = [[support_section(s, z, b) for s, b in zip(surfaces, bounds)] for z in heights]
    serial_seconds = time.monotonic()-started
    calculate = ParallelSupportSections(paths, heights, workers=4)
    started = time.monotonic()
    rows = []
    with calculate:
        for i, z in enumerate(heights):
            count = 0
            for j, (surface, box) in enumerate(zip(surfaces, bounds)):
                actual = calculate(surface, z, box)
                if not np.array_equal(actual, expected[i][j]):
                    raise ValueError('Parallel exact cuts differ from the unchanged serial hook')
                count += len(actual)
            rows.append({'layer': INDICES[i], 'z_mm': z, 'raw_support_segments': count,
                         'all_arrays_and_order_exact': True})
    parallel_seconds = time.monotonic()-started
    # CORE exports the same surfaces after slicing; readonly protection must allow it.
    scene = trimesh.Scene(surfaces).export(file_type='glb')
    output.mkdir(parents=True, exist_ok=False)
    result = {'status': 'passed',
              'scope': 'Exact slicing equivalence/performance on retained rejected support sheets; no support geometry admission.',
              'source_sha256': sha(__file__), 'input_checkpoint_sha256': sha(directory / 'support-stage.json'),
              'support_surfaces': len(paths), 'support_faces': sum(len(s.faces) for s in surfaces), 'rows': rows,
              'serial_seconds': serial_seconds, 'parallel_seconds_including_startup': parallel_seconds,
              'speedup': serial_seconds/parallel_seconds, 'parallel_runtime': calculate.receipt(),
              'readonly_surface_scene_export_bytes': len(scene)}
    (output / 'benchmark.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({k: result[k] for k in ('status', 'serial_seconds', 'parallel_seconds_including_startup', 'speedup')}))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    benchmark(args.directory, args.output)
