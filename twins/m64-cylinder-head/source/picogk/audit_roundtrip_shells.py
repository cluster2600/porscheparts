#!/usr/bin/env python3
"""Classify oriented boundary shells of one unchanged, hash-bound roundtrip STL.

This is a private geometric diagnostic, not cavity nesting, fluid-volume
classification, material porosity identification, repair or manufacturing QA.
"""
import argparse
import json
import math
from pathlib import Path
import re

from audit_cooling_domains import boundary_shells
from compare_meshes import atomic_private_json
from export_master import load_binary_stl, sha256


def verified_receipt(args):
    for value in (args.master_sha256, args.candidate_sha256):
        if not re.fullmatch('[0-9a-f]{64}', value):
            raise ValueError('explicit_master_and_candidate_SHA256_required')
    if not math.isfinite(args.voxel_size) or args.voxel_size <= 0:
        raise ValueError('positive_finite_voxel_size_required')
    candidate_hash = sha256(args.candidate)
    receipt_hash = sha256(args.run_report)
    receipt = json.loads(args.run_report.read_text())
    output = receipt['roundtrip']
    if (candidate_hash != args.candidate_sha256 or candidate_hash != output['sha256']
            or output['filename'] != args.candidate.name
            or receipt['input_sha256'] != args.master_sha256
            or receipt.get('input_unchanged') is not True or receipt.get('transform') != 'identity'
            or not math.isclose(float(receipt['voxel_mm']), args.voxel_size, rel_tol=1e-6, abs_tol=1e-8)):
        raise ValueError('candidate_receipt_hash_input_frame_or_resolution_mismatch')
    if sha256(args.run_report) != receipt_hash:
        raise ValueError('run_receipt_changed_while_reading')
    return receipt, receipt_hash, candidate_hash


def read_exact_welded_mesh(path):
    import numpy as np
    import trimesh
    triangles = load_binary_stl(path)
    vertices, inverse = np.unique(triangles.reshape(-1, 3), axis=0, return_inverse=True)
    # Identical-coordinate welding only. No repair, tolerance merge, normal
    # correction, smoothing or deletion of even the smallest boundary shell.
    return trimesh.Trimesh(vertices=vertices, faces=inverse.reshape(-1, 3), process=False)


def run(args):
    import numpy as np
    import trimesh
    if args.output.exists() or args.output.is_symlink():
        raise FileExistsError(args.output)
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if args.output.parent.is_symlink() or args.output.parent.stat().st_mode & 0o077:
        raise ValueError('private_output_directory_required')
    receipt, receipt_hash, candidate_hash = verified_receipt(args)
    sources = {name: sha256(Path(__file__).with_name(name)) for name in (
        'audit_roundtrip_shells.py', 'audit_cooling_domains.py', 'compare_meshes.py', 'export_master.py')}
    mesh = read_exact_welded_mesh(args.candidate)
    if len(mesh.faces) != receipt['roundtrip']['triangles']:
        raise ValueError('candidate_triangle_count_mismatch')
    shells = boundary_shells(mesh)
    shell_sum = math.fsum(row['signed_volume_scan_units_cubed'] for row in shells)
    whole_volume = float(mesh.volume)
    relative_error = abs(shell_sum - whole_volume) / max(abs(whole_volume), 1e-30)
    triangles_match = sum(row['triangles'] for row in shells) == len(mesh.faces)
    oriented_closed = bool(mesh.is_watertight and mesh.is_winding_consistent)
    # Same numerical comparison tolerance as audit_cooling_domains.py. This is
    # not a physical tolerance, a small-shell removal threshold or design gate.
    sum_check = bool(math.isfinite(relative_error) and relative_error < 1e-8)
    report = {
        'schema': 'm64-private-roundtrip-oriented-shell-audit/v1', 'source_sha256': sources,
        'candidate_filename': args.candidate.name, 'candidate_STL_sha256': candidate_hash,
        'run_receipt_sha256': receipt_hash, 'master_STL_sha256_from_verified_run': args.master_sha256,
        'voxel_size_scan_units': args.voxel_size, 'triangles': len(mesh.faces),
        'length_unit': 'scan_unit_under_unverified_1_mm_hypothesis',
        'numpy_version': np.__version__, 'trimesh_version': trimesh.__version__,
        'coordinate_welding': 'identical_float_values_only_no_tolerance_repair',
        'boundary_shell_connectivity': 'faces_connected_by_shared_edges',
        'boundary_shell_count': len(shells), 'boundary_shells': shells,
        'positive_oriented_shells': sum(row['orientation_sign'] == 'positive' for row in shells),
        'negative_oriented_shells': sum(row['orientation_sign'] == 'negative' for row in shells),
        'zero_signed_volume_shells': sum(row['orientation_sign'] == 'zero' for row in shells),
        'trimesh_watertight': bool(mesh.is_watertight),
        'trimesh_winding_consistent': bool(mesh.is_winding_consistent),
        'whole_mesh_signed_volume_scan_units_cubed': whole_volume,
        'oriented_shell_volume_sum_scan_units_cubed': shell_sum,
        'shell_volume_sum_relative_difference': relative_error,
        'numerical_volume_comparison_relative_tolerance': 1e-8,
        'shell_triangle_counts_match_whole_mesh': triangles_match,
        'oriented_volume_crosscheck_passed': bool(oriented_closed and triangles_match and sum_check),
        'boundary_shell_counts_are_not_connected_fluid_volume_counts': True,
        'negative_shell_is_not_proof_of_material_porosity': True,
        'shell_nesting_or_self_intersections_tested': False,
        'master_geometry_reaudited': False, 'repair_or_small_shell_removal_performed': False,
        'absolute_scale_certified': False, 'thermal_or_structural_simulation': False,
        'manufacturing_authorized': False, 'engine_operation_authorized': False,
    }
    if sha256(args.candidate) != candidate_hash or sha256(args.run_report) != receipt_hash:
        raise ValueError('source_changed_during_shell_audit')
    if any(sha256(Path(__file__).with_name(name)) != digest for name, digest in sources.items()):
        raise ValueError('audit_code_changed_during_execution')
    report['source_files_unchanged_after_read_only_audit'] = True
    atomic_private_json(args.output, report)
    print(json.dumps({'candidate_sha256': candidate_hash, 'boundary_shells': shells,
                      'oriented_volume_crosscheck_passed': report['oriented_volume_crosscheck_passed']}), flush=True)
    return 0 if report['oriented_volume_crosscheck_passed'] else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--candidate-sha256', required=True)
    parser.add_argument('--run-report', type=Path, required=True)
    parser.add_argument('--master-sha256', required=True)
    parser.add_argument('--voxel-size', type=float, required=True)
    parser.add_argument('--output', type=Path, required=True)
    return run(parser.parse_args())


if __name__ == '__main__':
    raise SystemExit(main())
