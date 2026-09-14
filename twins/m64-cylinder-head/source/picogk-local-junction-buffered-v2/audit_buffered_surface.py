#!/usr/bin/env python3
"""Audit séparé brut/normalisé, réutilisant les prédicats exacts déjà testés."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import time

import numpy as np


def load_helpers():
    folder = Path(__file__).resolve().parent.parent / 'picogk-local-junction'
    names = ('audit_surface_topology', 'audit_direct_union_surface')
    loaded = []
    for name in names:
        spec = importlib.util.spec_from_file_location(name, folder / (name + '.py'))
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        loaded.append(module)
    return loaded


FIELD_NAMES = {'original_A', 'closing_C', 'ROI_inner', 'C_intersect_inner_ROI',
               'buffered_candidate', 'diagnostic_added'}


def declared_screen(native, rows, roi):
    names = ('outside_ROI_changed_nodes', 'protected_changed_nodes',
             'lost_original_gas_nodes', 'added_nodes_touching_ROI_boundary')
    signs = all(native[name] == [0, 0] for name in names)
    changed = len(native['changed_nodes']) == 2 and all(value > 0 for value in native['changed_nodes'])
    vdb = native['native_VDB']['roundtrip_bitwise_comparison']
    restored = set(vdb) == FIELD_NAMES and all(
        row['exact_value_comparison_pass'] is True and row['bitwise_value_differences'] == 0
        and row['max_abs_delta_world_units'] == 0 and row['compared_native_bbox_nodes'] > 0
        and row['bbox_indices_equal'] is True for row in vdb.values())
    sdf = native['SDF_comparison']
    field_pass = (sdf['finite_comparable_pairs'] > 0 and sdf['unavailable_pairs'] == 0
                  and sdf['outside_ROI_value_changes'] == 0 and sdf['protected_value_changes'] == 0
                  and sdf['max_abs_outside_ROI_delta_world_units'] == 0
                  and sdf['max_abs_protected_delta_world_units'] == 0)
    normalized = set(rows) == {'before', 'after', 'added'} and all(
        row['normalized']['topology']['closed_oriented_combinatorial_surface_screen_pass'] is True
        for row in rows.values())
    contained = roi['all_changed_triangle_supports_inside_convex_ROI'] is True
    return bool(signs and changed and restored and field_pass and normalized and contained)


def run(directory, output, max_faces):
    topo, direct = load_helpers()
    start = time.monotonic()
    policy_path = Path(__file__).with_name('criteria-0p1-fixed-margin.json')
    source = Path(__file__)
    helper_files = [Path(topo.__file__), Path(direct.__file__)]
    source_hashes = {path.name: topo.sha(path) for path in [source, policy_path, *helper_files]}
    native_path = directory / 'run-report.json'
    native_hash = topo.sha(native_path)
    native = json.loads(native_path.read_text())
    policy = json.loads(policy_path.read_text())
    h = native['voxel_world_units']
    if h == .2:
        if (native['schema'] != 'm64-picogk-local-junction-buffered-witness/v1'
                or native_hash != policy['coarse_native_report_sha256']
                or native['policy_sha256'] != policy['coarse_policy_sha256'] or max_faces != 150_000):
            raise ValueError('Coarse audit requires the frozen original receipt and historical resource bound')
    elif h == .1:
        if (native['schema'] != 'm64-picogk-local-junction-buffered-witness/v2'
                or native['policy_sha256'] != source_hashes[policy_path.name] or max_faces != 500_000):
            raise ValueError('Fine audit requires its new policy and explicit 500000 face resource opt-in')
        # Process-local resource opt-in only; no file or geometric predicate changes.
        topo.MAX_FACES, topo.MAX_VERTICES = max_faces, 3 * max_faces
    else:
        raise ValueError('Only the declared two witness resolutions are accepted')
    if (native['private_head_processed'] is not False or
            native['authorized_ROI_low'] != [-8, -3, -8] or native['authorized_ROI_high'] != [8, 3, 8]
            or native['margin_world_units'] != .6 or native['radius_world_units'] != 1
            or native['inner_ROI_low'] != [-7.4, -2.4, -7.4] or native['inner_ROI_high'] != [7.4, 2.4, 7.4]):
        raise ValueError('The exact intended world geometry or synthetic scope changed')
    vdb = directory / native['native_VDB']['filename']
    if topo.sha(vdb) != native['native_VDB']['sha256']:
        raise ValueError('VDB differs from native receipt')
    normalized, rows = {}, {}
    for name in ('before', 'after', 'added'):
        triangles, digest = topo.load_binary_stl(directory / (name + '.stl'))
        if digest != native['exports'][name]['sha256'] or len(triangles) != native['exports'][name]['triangles']:
            raise ValueError('STL hash or triangle count differs from native receipt')
        raw = topo.audit_arrays(triangles.reshape(-1, 3), np.arange(triangles.size // 3).reshape(-1, 3))
        normalized[name], norm = direct.normalize_exact_zero(triangles)
        rows[name] = {'source_STL_sha256': digest, 'raw': raw, 'normalized': norm}
    roi = direct.roi_difference(normalized['before'], normalized['after'],
                                native['authorized_ROI_low'], native['authorized_ROI_high'])
    if (native_hash != topo.sha(native_path) or topo.sha(vdb) != native['native_VDB']['sha256'] or
            any(topo.sha(path) != source_hashes[path.name] for path in [source, policy_path, *helper_files]) or
            any(topo.sha(directory / (name + '.stl')) != row['source_STL_sha256'] for name, row in rows.items())):
        raise ValueError('An input or helper changed during audit')
    raw_pass = all(row['raw']['closed_oriented_combinatorial_surface_screen_pass'] for row in rows.values())
    normalized_pass = declared_screen(native, rows, roi)
    volumes = {name: row['normalized']['topology']['signed_triangle_volume_scan_units_cubed']
               for name, row in rows.items()}
    report = {
        'schema': 'm64-picogk-buffered-surface-audit/v2', 'source_sha256': source_hashes,
        'native_report_sha256': native_hash, 'native_VDB_sha256': topo.sha(vdb),
        'native_occupancy_status_retained': native['status'],
        'numpy_version': np.__version__, 'voxel_world_units': h, 'fixed_margin_world_units': .6,
        'audit_resource_max_faces': max_faces, 'audit_resource_max_vertices': topo.MAX_VERTICES,
        'historical_helpers_changed_on_disk': False, 'meshes': rows, 'normalized_mesh_ROI_check': roi,
        'raw_status': 'raw_combinatorial_surface_screen_pass' if raw_pass else 'rejected_raw_surface_screen',
        'raw_rejection_overridden': False,
        'normalized_pipeline_status': 'declared_exploratory_screen_pass' if normalized_pass else 'rejected_declared_exploratory_screen',
        'normalization_is_separate_exact_zero_face_deletion_only': True,
        'original_meshes_changed': False, 'normalized_meshes_written': False,
        'nonzero_face_deletion_or_retriangulation_or_vertex_motion': False,
        'actual_added_volume_after_minus_before': volumes['after'] - volumes['before'],
        'normalized_volume_residual_after_minus_before_minus_added': volumes['after'] - volumes['before'] - volumes['added'],
        'volume_residual_cause_proved': False,
        'SDF_value_comparison_retained': native['SDF_comparison'],
        'continuous_SDF_or_BRep_preservation_proved': False,
        'geometric_intersections_or_shell_nesting_qualified': False,
        'fine_witness_resolution_executed': h == .1,
        'further_resolution_or_private_head_authorized': False,
        'CFD_qualified': False, 'manufacturing_authorized': False,
        'elapsed_seconds': time.monotonic() - start,
    }
    topo.write_private_new_json(output, report)
    print(json.dumps({'output': str(output), 'raw_status': report['raw_status'],
                      'normalized_pipeline_status': report['normalized_pipeline_status'],
                      'ROI': roi, 'volume_residual': report['normalized_volume_residual_after_minus_before_minus_added']}, indent=2))
    return 0 if normalized_pass else 3


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--max-faces', type=int, choices=(150000, 500000), required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.directory, args.output, args.max_faces))
