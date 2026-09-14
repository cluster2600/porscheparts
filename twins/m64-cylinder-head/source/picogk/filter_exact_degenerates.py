#!/usr/bin/env python3
"""Create private derived STL copies omitting only exactly zero-area triangles.

All retained 50-byte STL triangle records are copied unchanged, including vertex
coordinates, winding, stored normals and attributes. No tolerance-based welding,
surface repair, smoothing, voxel edit, master edit or manufacturing acceptance.
"""
import argparse
import json
from pathlib import Path
import struct

from audit_cooling_domains import boundary_shells
from compare_meshes import read_mesh
from export_master import load_binary_stl, mesh_summary, sha256


def filter_records(data, triangles):
    import numpy as np
    cross = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    # Each input coordinate is binary32 promoted to binary64 by the STL loader.
    # Exact zero is intentional; near-zero triangles are retained and audited.
    removed = np.all(cross == 0., axis=1)
    if len(data) != 84 + 50 * len(triangles):
        raise ValueError('binary_STL_record_count_mismatch')
    records = np.frombuffer(data, dtype='V50', offset=84)
    result = data[:80] + struct.pack('<I', int((~removed).sum())) + records[~removed].tobytes()
    return result, np.flatnonzero(removed).tolist()


def run(args):
    import numpy as np
    if args.output.exists():
        raise FileExistsError(args.output)
    manifest_path = args.directory / 'cooling-domain-report.json'
    manifest_hash = sha256(manifest_path)
    manifest = json.loads(manifest_path.read_text())
    master = json.loads(args.master_report.read_text())
    if (manifest['input_sha256'] != master['mesh_sha256'] or not manifest['input_unchanged']
            or manifest['transform'] != 'identity'):
        raise ValueError('cooling_master_provenance_or_frame_mismatch')
    expected = {'unclassified-void-complement.stl', 'geometric-clearance-core-1p5mm.stl',
                'geometric-protected-skin-1p5mm.stl'}
    if {item['filename'] for item in manifest['outputs']} != expected:
        raise ValueError('expected_exact_three_geometry_domains')
    args.output.mkdir(parents=True, mode=0o700)
    args.output.chmod(0o700)
    report = {
        'schema': 'm64-private-exact-degenerate-STL-filter/v1',
        'source_script_sha256': sha256(Path(__file__)), 'numpy_version': np.__version__,
        'source_native_manifest_sha256': manifest_hash,
        'input_master_STL_sha256': manifest['input_sha256'], 'voxel_scan_units': manifest['voxel_mm'],
        'length_unit': 'scan_unit_under_unverified_1_mm_hypothesis',
        'filter': 'remove_only_triangles_with_exact_zero_cross_product_in_binary64',
        'retained_triangle_binary_records_are_identical': True,
        'removed_triangle_indices_are_zero_based': True,
        'original_STL_and_VDB_and_master_modified': False,
        'tolerance_based_repair_or_coordinate_changes': False,
        'source_sampled_occupancy_result': manifest.get('sampled_occupancy_partition'),
        'source_native_volume_API_audit': manifest.get('native_volume_api_audit'),
        'boundary_shell_counts_are_not_connected_fluid_volume_counts': True,
        'self_intersections_or_shell_nesting_certified': False,
        'thermal_or_structural_validation': False, 'manufacturing_authorized': False,
        'records': [],
    }
    for item in manifest['outputs']:
        path = args.directory / item['filename']
        original_hash = sha256(path)
        if original_hash != item['sha256']:
            raise ValueError('source_domain_hash_mismatch')
        triangles = load_binary_stl(path)
        if len(triangles) != item['triangles']:
            raise ValueError('source_triangle_count_mismatch')
        before = mesh_summary(triangles)
        filtered, removed = filter_records(path.read_bytes(), triangles)
        target = args.output / path.name
        target.write_bytes(filtered)
        target.chmod(0o600)
        retained = np.ones(len(triangles), dtype=bool)
        retained[removed] = False
        if not np.array_equal(load_binary_stl(target), triangles[retained]):
            raise ValueError('retained_coordinates_changed')
        mesh, after = read_mesh(target)
        relative = abs(after['signed_volume_scan_units_cubed'] - before['signed_volume_scan_units_cubed']) / max(
            abs(before['signed_volume_scan_units_cubed']), 1e-30)
        bounds_identical = after['bounds_scan_units_private'] == before['bounds_scan_units_private']
        gate = (after['edge_manifold_closed'] and after['winding_consistent_on_two_face_edges']
                and after['zero_area_triangles'] == 0 and after['duplicate_triangles_ignoring_winding'] == 0
                and mesh.is_watertight and mesh.is_winding_consistent and mesh.volume > 0
                and bounds_identical and relative < 1e-12)
        shells = boundary_shells(mesh)
        record = {
            'filename': path.name, 'original_sha256': original_hash, 'derived_sha256': sha256(target),
            'original_triangles': len(triangles), 'derived_triangles': after['triangles'],
            'removed_zero_area_triangle_indices': removed, 'removed_count': len(removed),
            'before': before, 'after': after, 'bounds_identical': bounds_identical,
            'signed_volume_relative_change': relative,
            'independent_trimesh_volume_scan_units_cubed': float(mesh.volume),
            'surface_boundary_shells': shells,
            'closed_oriented_surface_and_unchanged_geometry_gate_passed': bool(gate),
        }
        report['records'].append(record)
        if sha256(path) != original_hash:
            raise ValueError('source_domain_changed_during_read_only_filter')
        print(json.dumps({'filename': path.name, 'removed_exact_zero_area_triangles': len(removed),
                          'derived_topology_gate': bool(gate), 'boundary_shells': len(shells)}), flush=True)
    if sha256(manifest_path) != manifest_hash:
        raise ValueError('source_manifest_changed_during_filter')
    report['all_derived_topology_and_geometry_gates_passed'] = all(
        item['closed_oriented_surface_and_unchanged_geometry_gate_passed'] for item in report['records'])
    target_report = args.output / 'strict-degenerate-filter-report.json'
    target_report.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    target_report.chmod(0o600)
    return 0 if report['all_derived_topology_and_geometry_gates_passed'] else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--master-report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    return run(parser.parse_args())


if __name__ == '__main__':
    raise SystemExit(main())
