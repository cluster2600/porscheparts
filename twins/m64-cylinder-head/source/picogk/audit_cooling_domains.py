#!/usr/bin/env python3
"""Independent private topology/winding/volume audit of three cooling domains.

Surface-shell connectivity is not connected fluid-volume classification.
No flood fill, physical calculation, master edit, or manufacturing release.
"""
import argparse
import json
from pathlib import Path

from export_master import sha256
from compare_meshes import read_mesh


def boundary_shells(mesh):
    import numpy as np
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    adjacency = mesh.face_adjacency
    graph = coo_matrix((np.ones(len(adjacency), dtype=np.int8), (adjacency[:, 0], adjacency[:, 1])),
                       shape=(len(mesh.faces), len(mesh.faces))).tocsr()
    count, labels = connected_components(graph, directed=False)
    records = []
    for label in range(count):
        triangles = mesh.triangles[labels == label]
        center = (triangles.min(axis=(0, 1)) + triangles.max(axis=(0, 1))) * .5
        shifted = triangles - center
        volume = float(np.einsum('ij,ij->i', shifted[:, 0],
                                np.cross(shifted[:, 1], shifted[:, 2])).sum() / 6)
        records.append({'boundary_shell_index': label, 'triangles': len(triangles),
                        'signed_volume_scan_units_cubed': volume,
                        'orientation_sign': 'positive' if volume > 0 else 'negative' if volume < 0 else 'zero'})
    return records


def run(args):
    import math
    import numpy as np
    import trimesh
    if args.output.exists():
        raise FileExistsError(args.output)
    manifest_path = args.directory / 'cooling-domain-report.json'
    before = sha256(manifest_path)
    manifest = json.loads(manifest_path.read_text())
    master = json.loads(args.master_report.read_text())
    if (manifest['input_sha256'] != master['mesh_sha256'] or not manifest['input_unchanged']
            or manifest['transform'] != 'identity'):
        raise ValueError('cooling_master_provenance_or_frame_mismatch')
    expected = {'unclassified-void-complement.stl', 'geometric-clearance-core-1p5mm.stl',
                'geometric-protected-skin-1p5mm.stl'}
    if {item['filename'] for item in manifest['outputs']} != expected:
        raise ValueError('expected_exact_three_geometry_domains')
    report = {
        'schema': 'm64-private-cooling-domain-independent-mesh-audit/v1',
        'audit_source_sha256': sha256(Path(__file__)), 'source_manifest_sha256': before,
        'input_master_STL_sha256': manifest['input_sha256'], 'voxel_scan_units': manifest['voxel_mm'],
        'length_unit': 'scan_unit_under_unverified_1_mm_hypothesis', 'numpy_version': np.__version__,
        'trimesh_version': trimesh.__version__, 'records': [],
        'boundary_shell_counts_are_not_connected_fluid_volume_counts': True,
        'continuum_self_intersections_or_shell_nesting_certified': False,
        'flood_fill_performed': False, 'CFD_boundary_conditions_assigned': False,
        'thermal_or_structural_simulation': False, 'manufacturing_authorized': False,
        'source_sampled_occupancy_result': manifest.get('sampled_occupancy_partition'),
        'source_native_volume_API_audit': manifest.get('native_volume_api_audit'),
    }
    for item in manifest['outputs']:
        path = args.directory / item['filename']
        source_hash = sha256(path)
        if source_hash != item['sha256']:
            raise ValueError('domain_STL_hash_mismatch')
        mesh, summary = read_mesh(path)
        if summary['triangles'] != item['triangles']:
            raise ValueError('domain_triangle_count_mismatch')
        shells = boundary_shells(mesh)
        volume = float(mesh.volume)
        csharp_volume = float(item['oriented_mesh_volume_mm3'])
        relative = abs(volume - csharp_volume) / max(abs(csharp_volume), 1e-30)
        summary_volume_error = abs(volume - summary['signed_volume_scan_units_cubed']) / max(abs(volume), 1e-30)
        shell_sum = math.fsum(row['signed_volume_scan_units_cubed'] for row in shells)
        gate = (summary['edge_manifold_closed'] and summary['winding_consistent_on_two_face_edges']
                and summary['boundary_edges'] == 0 and summary['nonmanifold_edges'] == 0
                and summary['zero_area_triangles'] == 0 and summary['duplicate_triangles_ignoring_winding'] == 0
                and mesh.is_watertight and mesh.is_winding_consistent and volume > 0
                and relative < 1e-8 and summary_volume_error < 1e-8)
        record = {
            'filename': item['filename'], 'sha256': source_hash, 'mesh_summary': summary,
            'trimesh_watertight': bool(mesh.is_watertight),
            'trimesh_winding_consistent': bool(mesh.is_winding_consistent),
            'trimesh_signed_volume_scan_units_cubed': volume,
            'CSharp_compensated_signed_volume_scan_units_cubed': csharp_volume,
            'CSharp_volume_relative_difference': relative,
            'independent_numpy_triangle_volume_relative_difference': summary_volume_error,
            'boundary_shells': shells, 'oriented_shell_volume_sum_scan_units_cubed': shell_sum,
            'shell_sum_relative_difference': abs(shell_sum - volume) / max(abs(volume), 1e-30),
            'closed_oriented_surface_and_volume_crosscheck_passed': bool(gate),
            'gate_is_not_material_or_manufacturing_acceptance': True,
        }
        report['records'].append(record)
        if sha256(path) != source_hash:
            raise ValueError('domain_changed_during_audit')
        print(json.dumps({'filename': item['filename'], 'surface_boundary_shells': len(shells),
                          'signed_volume': volume, 'topology_and_volume_gate': bool(gate)}), flush=True)
    if sha256(manifest_path) != before:
        raise ValueError('domain_manifest_changed_during_audit')
    report['source_files_unchanged_after_read_only_audit'] = True
    report['all_three_surface_topology_and_volume_crosschecks_passed'] = all(
        row['closed_oriented_surface_and_volume_crosscheck_passed'] for row in report['records'])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    args.output.chmod(0o600)
    return 0 if report['all_three_surface_topology_and_volume_crosschecks_passed'] else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--master-report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    return run(parser.parse_args())


if __name__ == '__main__':
    raise SystemExit(main())
