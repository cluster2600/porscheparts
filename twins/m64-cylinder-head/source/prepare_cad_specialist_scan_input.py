#!/usr/bin/env python3
"""Prepare a private raw-scan crop, never a repaired/manufacturing model.

Both specialist CAD models consume the same 256 normalized surface points.
The retained triangle subset is intentionally uncapped and unmodified.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

import numpy as np


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def read_obj(path):
    vertices, faces = [], []
    with Path(path).open() as stream:
        for line in stream:
            if line.startswith('v '):
                vertices.append([float(v) for v in line.split()[1:4]])
            elif line.startswith('f '):
                row = line.split()[1:]
                if len(row) != 3:
                    raise ValueError('only_triangular_OBJ_supported')
                ids = [int(v.split('/')[0]) for v in row]
                if any(i <= 0 for i in ids):
                    raise ValueError('positive_OBJ_indices_required')
                faces.append([i - 1 for i in ids])
    vertices, faces = np.asarray(vertices, dtype=np.float64), np.asarray(faces, dtype=np.int64)
    if vertices.ndim != 2 or vertices.shape[1] != 3 or not np.isfinite(vertices).all():
        raise ValueError('finite_vertices_required')
    if not len(faces) or faces.min() < 0 or faces.max() >= len(vertices):
        raise ValueError('valid_nonempty_faces_required')
    return vertices, faces


def normalize(vertices):
    center = (vertices.min(axis=0) + vertices.max(axis=0)) / 2
    longest = float(np.ptp(vertices, axis=0).max())
    if longest <= 0:
        raise ValueError('nonzero_extent_required')
    return (vertices - center) * (2 / longest), center, longest / 2


def sample_surface(triangles, count, seed):
    rng = np.random.default_rng(seed)
    area2 = np.linalg.norm(np.cross(triangles[:, 1] - triangles[:, 0],
                                    triangles[:, 2] - triangles[:, 0]), axis=1)
    if not np.isfinite(area2).all() or area2.sum() <= 0:
        raise ValueError('positive_surface_area_required')
    ids = rng.choice(len(triangles), count, p=area2 / area2.sum())
    uv = rng.random((count, 2))
    root = np.sqrt(uv[:, 0])
    weights = np.column_stack([1 - root, root * (1 - uv[:, 1]), root * uv[:, 1]])
    return np.einsum('ij,ijk->ik', weights, triangles[ids]), ids, weights


def write_stl(path, triangles):
    with Path(path).open('wb') as stream:
        stream.write(b'PRIVATE raw scan crop; not repaired or released'.ljust(80, b' '))
        stream.write(struct.pack('<I', len(triangles)))
        for triangle in triangles:
            normal = np.cross(triangle[1] - triangle[0], triangle[2] - triangle[0])
            length = np.linalg.norm(normal)
            normal = normal / length if length else np.zeros(3)
            stream.write(struct.pack('<12fH', *normal, *triangle.reshape(-1), 0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scan', type=Path, required=True)
    parser.add_argument('--scan-sha256', required=True)
    parser.add_argument('--interfaces', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--crop-min', type=float, nargs=3, required=True)
    parser.add_argument('--crop-max', type=float, nargs=3, required=True)
    args = parser.parse_args()
    if sha(args.scan) != args.scan_sha256:
        raise ValueError('raw_scan_hash_mismatch')
    if args.output.exists():
        raise FileExistsError(args.output)
    before_interfaces = sha(args.interfaces)
    interface = json.loads(args.interfaces.read_text())
    frame = np.asarray(interface['frame_rows_A_B_C'], dtype=float)
    if frame.shape != (3, 3) or not np.allclose(frame @ frame.T, np.eye(3), atol=1e-10):
        raise ValueError('orthonormal_frame_required')
    lower, upper = np.asarray(args.crop_min), np.asarray(args.crop_max)
    if not np.isfinite([lower, upper]).all() or not np.all(upper > lower):
        raise ValueError('valid_crop_bounds_required')
    vertices, faces = read_obj(args.scan)
    abc = vertices @ frame.T
    inside = ((abc >= lower) & (abc <= upper)).all(axis=1)
    retained = np.flatnonzero(inside[faces].all(axis=1))
    if not len(retained):
        raise ValueError('empty_crop')
    triangles = abc[faces[retained]]
    norm, center, scale = normalize(triangles.reshape(-1, 3))
    norm = norm.reshape(-1, 3, 3)
    args.output.mkdir(parents=True)
    np.save(args.output / 'triangles-normalized.npy', norm)
    np.save(args.output / 'original-face-indices.npy', retained)
    points, ids, weights = sample_surface(norm, 256, 20260912)
    np.save(args.output / 'points.npy', points.astype(np.float32))
    np.savez(args.output / 'point-provenance.npz', original_face_indices=retained[ids],
             barycentric_weights=weights)
    for name, seed in [('reference', 20260913), ('reference-repeat', 20260914)]:
        samples, _, _ = sample_surface(norm, 32768, seed)
        np.save(args.output / f'{name}-32768.npy', samples)
    write_stl(args.output / 'scan-crop-normalized.stl', norm)
    np.savetxt(args.output / 'points.xyz', points, fmt='%.9g')
    unique, inverse = np.unique(triangles.reshape(-1, 3), axis=0, return_inverse=True)
    local_faces = inverse.reshape(-1, 3)
    edges = np.sort(np.concatenate([local_faces[:, [0, 1]], local_faces[:, [1, 2]],
                                   local_faces[:, [2, 0]]]), axis=1)
    _, incidence = np.unique(edges, axis=0, return_counts=True)
    zero_area = np.count_nonzero(np.linalg.norm(np.cross(norm[:, 1] - norm[:, 0],
                                                        norm[:, 2] - norm[:, 0]), axis=1) == 0)
    files = {p.name: {'sha256': sha(p), 'bytes': p.stat().st_size}
             for p in sorted(args.output.iterdir()) if p.is_file()}
    report = {
        'schema': 'm64-specialist-raw-scan-input/v1',
        'source_kind': 'unrepaired_triangle_crop_from_user_supplied_935_reference_scan',
        'not_certified_M64_geometry': True, 'absolute_units_verified': False,
        'source_scan_private': str(args.scan), 'source_scan_sha256': args.scan_sha256,
        'interface_frame_source_private': str(args.interfaces),
        'interface_frame_source_sha256': before_interfaces, 'preparer_sha256': sha(__file__),
        'zone': 'low_B_port_mouth_and_flange_local_reference',
        'selection': 'original_triangle_retained_only_if_all_three_vertices_in_ABC_box',
        'crop_ABC_min': lower.tolist(), 'crop_ABC_max': upper.tolist(),
        'source_triangles': len(faces), 'retained_triangles': len(retained),
        'unique_vertices_exact': len(unique), 'boundary_edges': int(np.sum(incidence == 1)),
        'nonmanifold_edges': int(np.sum(incidence > 2)), 'zero_area_triangles': int(zero_area),
        'watertight_by_edge_incidence': bool(np.all(incidence == 2)),
        'caps_or_repair_added': False, 'model_points_count': 256,
        'sampling': 'area_weighted_independent_uniform_barycentric_PCG64_seed_20260912',
        'evaluation_sampling': '32768_independent_points_seed_20260913_repeat_20260914',
        'transform': {
            'frame_rows_A_B_C': frame.tolist(), 'center_ABC': center.tolist(),
            'scan_units_per_normalized_unit': scale,
            'forward': 'p_normalized=(p_raw@frame.T-center_ABC)/scan_units_per_normalized_unit',
            'inverse': 'p_raw=(p_normalized*scan_units_per_normalized_unit+center_ABC)@frame',
            'generated_CAD_to_normalized_scale_expected': 0.01,
            'generated_CAD_scale_must_be_verified_by_runner': True,
        },
        'source_files_unchanged': sha(args.scan) == args.scan_sha256 and sha(args.interfaces) == before_interfaces,
        'files': files,
        'limitations': ['256 points cannot preserve every fin or edge',
                        'open crop: reconstructed closure is unobserved geometry',
                        'no M64 interface, material, thermomechanical or manufacturing validation'],
    }
    (args.output / 'input-report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ['retained_triangles', 'boundary_edges', 'source_files_unchanged']}))


if __name__ == '__main__':
    main()
