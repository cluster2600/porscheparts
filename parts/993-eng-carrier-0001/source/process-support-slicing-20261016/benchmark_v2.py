"""Record every fixed plane, retaining invalid encodings before timing valid cuts."""
import argparse
import json
from pathlib import Path
import time

import numpy as np
import trimesh
from benchmark import INDICES
from parallel_support_sections import ParallelSupportSections, sha, support_section


def benchmark(directory, output):
    directory, output = Path(directory), Path(output)
    output.mkdir(parents=True, exist_ok=False)
    checkpoint = json.loads((directory/'support-stage.json').read_text())
    paths = sorted(directory.glob('support-*.npz'))
    surfaces, bounds = [], []
    for path in paths:
        if sha(path) != checkpoint['outputs_sha256'][path.name]:
            raise ValueError('Retained support checkpoint identity differs')
        with np.load(path, allow_pickle=False) as data:
            surface = trimesh.Trimesh(data['vertices'], data['faces'], process=False)
        z = surface.vertices[surface.faces, 2]
        surfaces.append(surface)
        bounds.append(np.column_stack((z.min(axis=1), z.max(axis=1))))
    rows, valid, serial_seconds = [], [], 0.
    for index in INDICES:
        z = (index+.5)*checkpoint['parameters']['layer_height_mm']
        started = time.monotonic()
        arrays, errors = [], []
        for j, (surface, box) in enumerate(zip(surfaces, bounds)):
            try:
                arrays.append(support_section(surface, z, box))
            except ValueError as error:
                arrays.append(None)
                errors.append(dict(surface=j, error=str(error)))
        seconds = time.monotonic()-started
        row = dict(layer=index, z_mm=z, serial_seconds=seconds, errors=errors,
                   all_surfaces_serially_encodable=not errors)
        if errors:
            calculate = ParallelSupportSections(paths, [z], workers=4)
            observed = None
            try:
                with calculate:
                    for surface, box in zip(surfaces, bounds):
                        calculate(surface, z, box)
            except ValueError as error:
                observed = str(error)
            if observed != errors[0]['error']:
                raise ValueError('Parallel and serial exact refusal differ')
            row.update(parallel_refusal_matches_serial=True, parallel_runtime=calculate.receipt())
        else:
            valid.append((row, arrays))
            serial_seconds += seconds
        rows.append(row)
    if not valid:
        raise ValueError('No complete valid fixed plane is available for timing')
    calculate = ParallelSupportSections(paths, [row['z_mm'] for row, _ in valid], workers=4)
    started = time.monotonic()
    with calculate:
        for row, expected in valid:
            count = 0
            for j, (surface, box) in enumerate(zip(surfaces, bounds)):
                actual = calculate(surface, row['z_mm'], box)
                if not np.array_equal(actual, expected[j]):
                    raise ValueError('Parallel result or original ordering differs')
                count += len(actual)
            row.update(raw_support_segments=count, all_arrays_and_order_exact=True)
    parallel_seconds = time.monotonic()-started
    scene = trimesh.Scene(surfaces).export(file_type='glb')
    result = dict(status='passed',
        scope='Equivalence and rejection behavior on ten fixed planes of rejected historical sheets; no geometry admission.',
        source_sha256=sha(__file__), input_checkpoint_sha256=sha(directory/'support-stage.json'),
        rows=rows, support_surfaces=len(paths), support_faces=sum(len(s.faces) for s in surfaces),
        valid_planes_timed=len(valid), rejected_planes=len(rows)-len(valid),
        valid_planes_serial_seconds=serial_seconds,
        parallel_seconds_including_startup=parallel_seconds,
        valid_planes_speedup=serial_seconds/parallel_seconds,
        parallel_runtime=calculate.receipt(), readonly_surface_scene_export_bytes=len(scene))
    (output/'benchmark.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({key: result[key] for key in ('status', 'valid_planes_timed', 'rejected_planes', 'valid_planes_speedup')}))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    benchmark(args.directory, args.output)
