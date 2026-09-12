#!/usr/bin/env python3
"""Approximate normalized bidirectional point distances; not metrology/CFD.

Reference crop is open. Candidate completion outside observed surfaces cannot
be interpreted as measured material. Report sampling baseline and both directions.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import struct

import numpy as np
from scipy.spatial import cKDTree

spec = importlib.util.spec_from_file_location('specialist_input', Path(__file__).with_name('prepare_cad_specialist_scan_input.py'))
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


def read_stl(path):
    data = Path(path).read_bytes()
    if len(data) > 100_000_000 or len(data) < 84:
        raise ValueError('bounded_binary_STL_required')
    count = struct.unpack('<I', data[80:84])[0]
    if not count or len(data) != 84 + 50 * count:
        raise ValueError('exact_binary_STL_size_required')
    dtype = np.dtype([('normal', '<f4', (3,)), ('vertices', '<f4', (3, 3)), ('attribute', '<u2')])
    triangles = np.frombuffer(data, dtype, count=count, offset=84)['vertices'].astype(float)
    if not np.isfinite(triangles).all():
        raise ValueError('finite_STL_required')
    return triangles


def statistics(values):
    return {'mean': float(np.mean(values)), 'rms': float(np.sqrt(np.mean(values**2))),
            'p50': float(np.quantile(values, .5)), 'p95': float(np.quantile(values, .95)),
            'p99': float(np.quantile(values, .99)), 'sampled_max_not_Hausdorff': float(values.max())}


def compare(reference, candidate, repeat):
    ref_tree, cand_tree = cKDTree(reference), cKDTree(candidate)
    return {
        'reference_to_candidate': statistics(cand_tree.query(reference)[0]),
        'candidate_to_reference': statistics(ref_tree.query(candidate)[0]),
        'reference_resampling_baseline': statistics(ref_tree.query(repeat)[0]),
    }


def verified_points(path, expected_sha256, count=32768):
    if path.stat().st_size > 2_000_000 or prepare.sha(path) != expected_sha256:
        raise ValueError('reference_points_hash_or_size_mismatch')
    points = np.load(path, allow_pickle=False)
    if points.shape != (count, 3) or points.dtype.kind not in 'fi' or not np.isfinite(points).all():
        raise ValueError('finite_reference_Nx3_points_required')
    if prepare.sha(path) != expected_sha256:
        raise ValueError('reference_points_changed_during_read')
    return points


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--candidate-stl', type=Path, required=True)
    parser.add_argument('--model-input-report', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    triangles = read_stl(args.candidate_stl)
    candidate, _, _ = prepare.sample_surface(triangles, 32768, 20260915)
    actual_input = args.model_input_report or args.reference / 'input-report.json'
    actual = json.loads(actual_input.read_text())
    base = json.loads((args.reference / 'input-report.json').read_text())
    reference_hashes = {name: base['files'][name]['sha256'] for name in
                        ['reference-32768.npy', 'reference-repeat-32768.npy']}
    reference = verified_points(args.reference / 'reference-32768.npy', reference_hashes['reference-32768.npy'])
    repeat = verified_points(args.reference / 'reference-repeat-32768.npy', reference_hashes['reference-repeat-32768.npy'])
    if actual['transform'] != base['transform'] or actual['source_scan_sha256'] != base['source_scan_sha256']:
        raise ValueError('input_reference_transform_or_source_mismatch')
    if args.model_input_report and actual.get('base_input_report_sha256') != prepare.sha(args.reference / 'input-report.json'):
        raise ValueError('FPS_parent_report_mismatch')
    if prepare.sha(actual_input.parent / 'points.npy') != actual['files']['points.npy']['sha256']:
        raise ValueError('model_input_points_hash_mismatch')
    result = {
        'schema': 'specialist-CAD-sampled-distance/v1',
        'method': 'bidirectional_finite_surface_samples_nearest_neighbour_not_exact_surface_distance',
        'sample_count_each': 32768, 'length_unit': 'normalized_longest_crop_extent_equals_2',
        'candidate_stl_sha256': prepare.sha(args.candidate_stl),
        'input_report_sha256': prepare.sha(args.reference / 'input-report.json'),
        'model_input_report_sha256': prepare.sha(actual_input),
        'model_input_points_sha256': actual['files']['points.npy']['sha256'],
        'consumed_reference_points_sha256': reference_hashes,
        'consumed_reference_hashes_verified_before_and_after_read': True,
        'consumed_reference_shape_and_finiteness_verified': True,
        'source_sha256': prepare.sha(__file__), 'candidate_triangles': len(triangles),
        'metrics': compare(reference, candidate, repeat),
        'bounds_alignment_optimized': False,
        'inverse_transform_applied_for_fitting': False,
        'acceptance_threshold_predefined': False, 'geometry_promoted_to_master': False,
        'limitations': ['open reference: inferred closures are not observed surfaces',
                        'finite sampled distances include sampling error; no global Hausdorff bound',
                        'no material, thermal, pressure, fatigue, fitment or LPBF validation'],
    }
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['metrics']))


if __name__ == '__main__':
    main()
