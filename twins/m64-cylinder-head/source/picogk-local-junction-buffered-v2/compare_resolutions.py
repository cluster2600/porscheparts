#!/usr/bin/env python3
"""Comparaison exploratoire de deux extractions à masque monde fixé, non convergence."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np
from audit_buffered_surface import load_helpers


def added_volume_screen(coarse, fine, threshold):
    if not all(math.isfinite(value) for value in (coarse, fine)) or fine <= 0 or coarse <= 0:
        return {'relative_difference': None, 'pass': False}
    relative = abs(coarse - fine) / abs(fine)
    return {'relative_difference': relative, 'pass': relative <= threshold}


def sample_points(triangles, maximum):
    # Indices régulièrement espacés, sans prétention de tirage surfacique uniforme.
    vertices = np.unique(triangles.reshape(-1, 3), axis=0)
    centers = triangles.mean(axis=1)
    half = maximum // 2
    samples = []
    for array, cap in ((vertices, half), (centers, maximum - half)):
        ids = np.linspace(0, len(array) - 1, min(cap, len(array)), dtype=np.int64)
        samples.append(array[ids])
    return np.concatenate(samples)


def sampled_distance(source, target, maximum):
    from vtkmodules.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray
    from vtkmodules.vtkCommonCore import vtkPoints
    from vtkmodules.vtkCommonDataModel import vtkCellArray, vtkPolyData
    from vtkmodules.vtkFiltersCore import vtkImplicitPolyDataDistance
    points = vtkPoints()
    points.SetData(numpy_to_vtk(np.ascontiguousarray(target.reshape(-1, 3)), deep=True))
    cells = vtkCellArray()
    cells.SetData(numpy_to_vtkIdTypeArray(np.arange(0, 3 * len(target) + 1, 3, dtype=np.int64), deep=True),
                  numpy_to_vtkIdTypeArray(np.arange(3 * len(target), dtype=np.int64), deep=True))
    surface = vtkPolyData()
    surface.SetPoints(points)
    surface.SetPolys(cells)
    distance = vtkImplicitPolyDataDistance()
    distance.SetInput(surface)
    samples = sample_points(source, maximum)
    values = np.asarray([abs(distance.EvaluateFunction(point)) for point in samples])
    if not np.isfinite(values).all():
        raise ValueError('Non-finite closest-triangle distance')
    return {'sample_count': len(samples), 'maximum_world_units': float(values.max()),
            'p95_world_units': float(np.percentile(values, 95)), 'mean_world_units': float(values.mean()),
            'sample_to_complete_target_triangle_surface': True,
            'continuous_Hausdorff_upper_bound': False}


def run(coarse_dir, fine_dir, coarse_audit, fine_audit, output):
    topo, _ = load_helpers()
    topo.MAX_FACES, topo.MAX_VERTICES = 500_000, 1_500_000
    start = time.monotonic()
    source = Path(__file__)
    policy_path = source.with_name('criteria-0p1-fixed-margin.json')
    policy = json.loads(policy_path.read_text())
    paths = [source, policy_path, coarse_audit, fine_audit,
             coarse_dir / 'run-report.json', fine_dir / 'run-report.json']
    hashes = {str(path): topo.sha(path) for path in paths}
    records = [json.loads(path.read_text()) for path in (coarse_audit, fine_audit)]
    native = [json.loads((directory / 'run-report.json').read_text()) for directory in (coarse_dir, fine_dir)]
    if (native[0]['voxel_world_units'] != .2 or native[1]['voxel_world_units'] != .1
            or native[0]['policy_sha256'] != policy['coarse_policy_sha256']
            or topo.sha(coarse_dir / 'run-report.json') != policy['coarse_native_report_sha256']
            or native[1]['policy_sha256'] != topo.sha(policy_path)):
        raise ValueError('This comparison requires the exact two policy-bound witness runs')
    for key in ('authorized_ROI_low', 'authorized_ROI_high', 'inner_ROI_low', 'inner_ROI_high',
                'radius_world_units', 'margin_world_units'):
        if native[0][key] != native[1][key]:
            raise ValueError('World geometry changed: no fixed-geometry comparison permitted')
    if any(row['schema'] != 'm64-picogk-buffered-surface-audit/v2' for row in records):
        raise ValueError('Both resolutions require the hardened v2 audit')
    meshes = [{}, {}]
    mesh_hashes = {}
    for index, directory in enumerate((coarse_dir, fine_dir)):
        if records[index]['native_report_sha256'] != topo.sha(directory / 'run-report.json'):
            raise ValueError('Audit/native hash mismatch')
        for name in ('before', 'after', 'added'):
            path = directory / (name + '.stl')
            triangles, digest = topo.load_binary_stl(path)
            if digest != native[index]['exports'][name]['sha256']:
                raise ValueError('STL differs from native receipt')
            mesh_hashes[str(path)] = digest
            zero = topo.exact_zero_area_mask(triangles.reshape(-1, 3), np.arange(triangles.size // 3).reshape(-1, 3))
            normalized = triangles[~zero]
            if hashlib.sha256(np.asarray(normalized, dtype='<f8').tobytes()).hexdigest() != records[index]['meshes'][name]['normalized']['retained_oriented_triangles_sha256']:
                raise ValueError('Normalized oriented triangles differ from audited arrays')
            meshes[index][name] = normalized
    actual = [row['actual_added_volume_after_minus_before'] for row in records]
    volume = added_volume_screen(*actual, policy['relative_actual_added_volume_difference_threshold'])
    metric_rows = {}
    for name in ('before', 'after', 'added'):
        forward = sampled_distance(meshes[0][name], meshes[1][name], policy['distance_max_samples_per_direction'])
        reverse = sampled_distance(meshes[1][name], meshes[0][name], policy['distance_max_samples_per_direction'])
        largest = max(forward['maximum_world_units'], reverse['maximum_world_units'])
        metric_rows[name] = {'coarse_to_fine': forward, 'fine_to_coarse': reverse,
                            'bidirectional_sample_max_world_units': largest,
                            'sampled_distance_screen_pass': largest <= policy['sampled_bidirectional_surface_distance_threshold_world_units']}
    guards = all(row['normalized_pipeline_status'] == 'declared_exploratory_screen_pass' for row in records)
    distance_pass = all(row['sampled_distance_screen_pass'] for row in metric_rows.values())
    if any(topo.sha(Path(path)) != digest for path, digest in {**hashes, **mesh_hashes}.items()):
        raise ValueError('An input changed during comparison')
    report = {
        'schema': 'm64-buffered-two-resolution-comparison/v1', 'source_and_inputs_sha256_private': hashes,
        'mesh_sha256_private': mesh_hashes, 'voxel_world_units': [.2, .1],
        'margin_world_units': [.6, .6], 'margin_voxels': [3, 6],
        'same_intended_world_geometry_verified': True,
        'unexecuted_alternative_3h_at_fine_would_change_world_geometry': True,
        'hardened_normalized_guards_both_pass': guards,
        'actual_added_volume_after_minus_before': actual,
        'actual_added_volume_relative_difference_screen': volume,
        'relative_difference_denominator': 'absolute_fine_actual_added_volume',
        'diagnostic_added_mesh_volumes': [row['meshes']['added']['normalized']['topology']['signed_triangle_volume_scan_units_cubed'] for row in records],
        'diagnostic_volume_residuals': [row['normalized_volume_residual_after_minus_before_minus_added'] for row in records],
        'residuals_explained': False, 'sampled_surface_distances': metric_rows,
        'sampling_not_continuous_Hausdorff_bound': True,
        'thresholds': {'relative_actual_added_volume': .05, 'sampled_distance_world_units': .2},
        'comparison_screen_pass': guards and volume['pass'] and distance_pass,
        'asymptotic_convergence_claimed': False, 'raw_rejections_retained': True,
        'private_head_processed': False, 'CFD_qualified': False, 'manufacturing_authorized': False,
        'numpy_version': np.__version__, 'elapsed_seconds': time.monotonic() - start,
    }
    topo.write_private_new_json(output, report)
    print(json.dumps({'output': str(output), 'comparison_screen_pass': report['comparison_screen_pass'],
                      'actual_added_volumes': actual, 'volume_screen': volume,
                      'sampled_surface_maxima': {name: row['bidirectional_sample_max_world_units'] for name, row in metric_rows.items()}}, indent=2))
    return 0 if report['comparison_screen_pass'] else 3


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('coarse-dir', 'fine-dir', 'coarse-audit', 'fine-audit', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.coarse_dir, args.fine_dir, args.coarse_audit, args.fine_audit, args.output))
