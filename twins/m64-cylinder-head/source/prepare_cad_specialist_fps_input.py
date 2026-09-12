#!/usr/bin/env python3
"""Second immutable input variant: 8192 surface samples -> deterministic FPS256.

Matches the sampling strategy used by both official specialist repositories,
not their RNG sequence nor a claimed bitwise PyTorch3D implementation match.
The original uniform256 input and inverse transform remain untouched.
"""
import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np

spec = importlib.util.spec_from_file_location('specialist_prepare', Path(__file__).with_name('prepare_cad_specialist_scan_input.py'))
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


def farthest_indices(points, count):
    points = np.asarray(points, dtype=np.float32)
    if points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(points).all():
        raise ValueError('finite_Nx3_points_required')
    if not 1 <= count <= len(points) or len(np.unique(points, axis=0)) < count:
        raise ValueError('enough_distinct_points_required')
    distances = np.full(len(points), np.inf, dtype=np.float32)
    chosen = np.empty(count, dtype=np.int64)
    selected = 0
    for step in range(count):
        chosen[step] = selected
        difference = points - points[selected]
        squared = np.sum(difference * difference, axis=1, dtype=np.float32)
        distances = np.minimum(distances, squared)
        selected = int(np.argmax(distances))
    return chosen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    report_path = args.reference / 'input-report.json'
    prior = json.loads(report_path.read_text())
    before = {name: prepare.sha(args.reference / name) for name in
              ['points.npy', 'triangles-normalized.npy', 'original-face-indices.npy', 'input-report.json']}
    for name in ['points.npy', 'triangles-normalized.npy', 'original-face-indices.npy']:
        if before[name] != prior['files'][name]['sha256']:
            raise ValueError('common_input_hash_mismatch')
    triangles = np.load(args.reference / 'triangles-normalized.npy', allow_pickle=False)
    original_faces = np.load(args.reference / 'original-face-indices.npy', allow_pickle=False)
    dense, triangle_ids, weights = prepare.sample_surface(triangles, 8192, 20260912)
    chosen = farthest_indices(dense, 256)
    args.output.mkdir()
    np.save(args.output / 'points.npy', dense[chosen].astype(np.float32))
    np.save(args.output / 'dense-pool-8192.npy', dense)
    np.save(args.output / 'fps-indices.npy', chosen)
    np.savez(args.output / 'point-provenance.npz',
             original_face_indices=original_faces[triangle_ids[chosen]],
             barycentric_weights=weights[chosen])
    report = {
        'schema': 'm64-specialist-FPS-input/v1',
        'source_kind': prior['source_kind'], 'zone': prior['zone'],
        'source_scan_sha256': prior['source_scan_sha256'],
        'base_input_report_sha256': before['input-report.json'],
        'base_input_private': str(args.reference),
        'source_sha256': prepare.sha(__file__),
        'sampler_source_sha256': prepare.sha(prepare.__file__),
        'sampling': {'surface_pool_size': 8192, 'surface_rng': 'NumPy_PCG64_seed_20260912',
                     'surface_distribution': 'area_weighted_uniform_barycentric',
                     'selection': 'greedy_farthest_point_min_squared_Euclidean',
                     'distance_dtype': 'float32', 'start_index': 0,
                     'tie_policy': 'first_index_numpy_argmax', 'selected_count': 256,
                     'matches_official_sampling_strategy': True,
                     'bitwise_PyTorch3D_equivalence_verified': False,
                     'official_random_seed_reproduction_claimed': False},
        'official_sources': [
            'https://github.com/filaPro/cad-recode/blob/main/demo.ipynb',
            'https://github.com/col14m/cadrille/blob/master/dataset.py'],
        'transform': prior['transform'],
        'source_files_unchanged': all(prepare.sha(args.reference / name) == value
                                      for name, value in before.items()),
        'files': {p.name: {'sha256': prepare.sha(p), 'bytes': p.stat().st_size}
                  for p in sorted(args.output.iterdir()) if p.is_file()},
        'not_certified_M64_geometry': True, 'absolute_units_verified': False,
        'caps_or_repair_added': False, 'manufacturing_release': False,
    }
    (args.output / 'input-report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'points_sha256': report['files']['points.npy']['sha256'],
                      'source_files_unchanged': report['source_files_unchanged']}))


if __name__ == '__main__':
    main()
