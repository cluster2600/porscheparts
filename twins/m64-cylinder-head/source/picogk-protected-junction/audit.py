#!/usr/bin/env python3
"""Counter-check the shared-SDF witness; never promote a private head."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.parent / 'picogk-local-junction-buffered-v2'


def load(name):
    spec = importlib.util.spec_from_file_location(name, PREVIOUS / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


hardened = load('audit_buffered_surface')
comparison = load('compare_resolutions')


def validate_native(row, h, policy_sha):
    if row.get('method') not in ('closing', 'smooth-union'):
        raise ValueError('Unknown construction method')
    expected = {
        'schema': 'm64-picogk-protected-junction-witness/v1',
        'policy_sha256': policy_sha, 'voxel_world_units': h,
        'authorized_ROI_low': [-8, -3, -8], 'authorized_ROI_high': [8, 3, 8],
        'inner_ROI_low': [-7.4, -2.4, -7.4], 'inner_ROI_high': [7.4, 2.4, 7.4],
        'radius_world_units': 1, 'margin_world_units': .6,
        'radial_mask_radius_world_units': 8.8,
        'shared_primitive_self_checks_passed': True,
        'analytic_addition_support_restricted': row['method'] == 'smooth-union',
        'operation': 'A_union_C_intersect_protected_mask',
        'difference_shell_used_for_candidate': False,
        'source_master_modified': False, 'private_head_processed': False,
        'exact_BRep_created': False, 'CFD_qualified': False, 'manufacturing_authorized': False,
    }
    for key, value in expected.items():
        actual = row.get(key)
        numeric_pair = type(value) in (float, int) and type(actual) in (float, int)
        if actual != value or (type(actual) is not type(value) and not numeric_pair):
            raise ValueError('Wrong witness, policy, geometry or authority: ' + key)


def run(coarse, fine, output):
    if output.exists():
        raise ValueError('Output must be new')
    topo, direct = hardened.load_helpers()
    policy_path = HERE / 'criteria.json'
    policy = json.loads(policy_path.read_text())
    topo.MAX_FACES, topo.MAX_VERTICES = policy['audit_max_faces'], 3 * policy['audit_max_faces']
    sources = [Path(__file__), policy_path, HERE/'Program.cs', HERE/'ProtectedMask.cs',
               HERE/'ProtectedJunction.csproj', Path(hardened.__file__), Path(comparison.__file__),
               Path(topo.__file__), Path(direct.__file__),
               HERE.parents[3]/'parts/picogk-catalog/common/Sdf.cs',
               HERE.parents[3]/'parts/picogk-catalog/engine/EngineSdf.cs']
    pins = {p: topo.sha(p) for p in sources}
    rows, meshes, native_rows = [], [], []
    for directory, h in ((coarse, .2), (fine, .1)):
        receipt = directory / 'run-report.json'
        pins[receipt] = topo.sha(receipt)
        native = json.loads(receipt.read_text())
        validate_native(native, h, pins[policy_path])
        native_rows.append(native)
        vdb = directory / 'native-fields.vdb'
        pins[vdb] = topo.sha(vdb)
        if pins[vdb] != native['native_VDB']['sha256']:
            raise ValueError('VDB hash mismatch')
        normalized, per_mesh = {}, {}
        for name in ('before', 'after', 'added'):
            path = directory / (name + '.stl')
            triangles, pins[path] = topo.load_binary_stl(path)
            if pins[path] != native['exports'][name]['sha256'] or len(triangles) != native['exports'][name]['triangles']:
                raise ValueError('STL hash or triangle count mismatch')
            raw = topo.audit_arrays(triangles.reshape(-1, 3), np.arange(triangles.size//3).reshape(-1, 3))
            normalized[name], norm = direct.normalize_exact_zero(triangles)
            per_mesh[name] = {'raw': raw, 'normalized': norm}
        roi = direct.roi_difference(normalized['before'], normalized['after'],
                                    native['authorized_ROI_low'], native['authorized_ROI_high'])
        volumes = {k: v['normalized']['topology']['signed_triangle_volume_scan_units_cubed'] for k,v in per_mesh.items()}
        rows.append({'voxel_world_units': h, 'meshes': per_mesh, 'roi': roi,
                     'normalized_guards_pass': hardened.declared_screen(native, per_mesh, roi),
                     'raw_topology_pass': all(v['raw']['closed_oriented_combinatorial_surface_screen_pass'] for v in per_mesh.values()),
                     'actual_added_volume': volumes['after'] - volumes['before'],
                     'diagnostic_volume_residual': volumes['after'] - volumes['before'] - volumes['added'],
                     'native_receipt_sha256': pins[receipt]})
        meshes.append(normalized)
    if any(native_rows[0][k] != native_rows[1][k] for k in ('method', 'assembly_sha256', 'picogk_assembly_sha256', 'runtime')):
        raise ValueError('Different builds or runtime: not a resolution comparison')
    volume = comparison.added_volume_screen(*(r['actual_added_volume'] for r in rows),
                                            policy['relative_actual_added_volume_difference_threshold'])
    distances = {name: max(comparison.sampled_distance(meshes[i][name], meshes[1-i][name], 20000)['maximum_world_units']
                           for i in (0, 1)) for name in ('before', 'after', 'added')}
    passed = (all(r['normalized_guards_pass'] for r in rows) and volume['pass'] and
              max(distances.values()) <= policy['sampled_bidirectional_surface_distance_threshold_world_units'])
    if any(topo.sha(p) != s for p,s in pins.items()):
        raise ValueError('An input changed during audit')
    report = {'schema': 'm64-picogk-transfer-comparison/v1', 'method': native_rows[0]['method'], 'resolutions': rows,
              'actual_added_volume_screen': volume, 'sampled_bidirectional_maxima': distances,
              'comparison_screen_pass': passed, 'input_hashes_unchanged': True,
              'source_and_input_hashes': {str(p): s for p,s in pins.items()},
              'raw_rejections_retained': True, 'normalization_is_exact_zero_deletion_only': True,
              'continuous_distance_bound': False, 'asymptotic_convergence_proved': False,
              'physical_clearance_proved': False, 'private_head_processed': False,
              'manufacturing_authorized': False}
    topo.write_private_new_json(output, report)
    print(json.dumps({k: report[k] for k in ('comparison_screen_pass','actual_added_volume_screen','sampled_bidirectional_maxima')}))
    return 0 if passed else 3


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('coarse', 'fine', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.coarse, args.fine, args.output))
