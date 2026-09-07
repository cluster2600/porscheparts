#!/usr/bin/env python3
"""Export a hash-bound private STEP body for PicoGK; never repair the master.

Coordinates retain scan units. Calling those units millimetres is explicitly a
working hypothesis, not metrology. STL is a derived binary float32 surface mesh.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def load_binary_stl(path):
    import numpy as np
    with Path(path).open('rb') as stream:
        header = stream.read(84)
        if len(header) != 84:
            raise ValueError('binary_STL_header_required')
        count = struct.unpack('<I', header[80:84])[0]
        if count == 0 or Path(path).stat().st_size != 84 + count * 50:
            raise ValueError('nonempty_binary_STL_exact_size_required')
        dtype = np.dtype([('normal', '<f4', (3,)), ('vertices', '<f4', (3, 3)), ('attribute', '<u2')])
        rows = np.fromfile(stream, dtype=dtype, count=count)
    triangles = rows['vertices'].astype(float)
    if not np.isfinite(triangles).all():
        raise ValueError('finite_STL_coordinates_required')
    return triangles


def mesh_summary(triangles):
    """Exact float-coordinate welding only: no tolerance-based mesh repair."""
    import numpy as np
    triangles = np.asarray(triangles, dtype=float)
    if triangles.ndim != 3 or triangles.shape[1:] != (3, 3) or not len(triangles):
        raise ValueError('nonempty_triangles_required')
    if not np.isfinite(triangles).all():
        raise ValueError('finite_triangles_required')
    vertices, inverse = np.unique(triangles.reshape(-1, 3), axis=0, return_inverse=True)
    faces = inverse.reshape(-1, 3)
    raw_edges = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    unique_edges, edge_inverse, edge_counts = np.unique(np.sort(raw_edges, axis=1), axis=0,
                                                        return_inverse=True, return_counts=True)
    orientation = np.where(raw_edges[:, 0] < raw_edges[:, 1], 1, -1)
    edge_orientation = np.bincount(edge_inverse, weights=orientation, minlength=len(unique_edges))
    parents = np.arange(len(vertices))

    def root(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    for first, second in unique_edges:
        r1, r2 = root(first), root(second)
        if r1 != r2:
            parents[r2] = r1
    components = len({int(root(index)) for index in range(len(vertices))})
    cross = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    twice_area = np.linalg.norm(cross, axis=1)
    edge_square_sum = sum(np.sum((triangles[:, a] - triangles[:, b]) ** 2, axis=1)
                          for a, b in ((0, 1), (1, 2), (2, 0)))
    quality = np.divide(2 * math.sqrt(3) * twice_area, edge_square_sum,
                        out=np.zeros_like(twice_area), where=edge_square_sum > 0)
    centered = triangles - vertices.mean(axis=0)
    volume = float(np.einsum('ij,ij->i', centered[:, 0],
                            np.cross(centered[:, 1], centered[:, 2])).sum() / 6)
    bounds = np.array([vertices.min(axis=0), vertices.max(axis=0)])
    return {
        'triangles': len(triangles), 'exact_welded_vertices': len(vertices),
        'exact_welded_edges': len(unique_edges), 'connected_vertex_components': components,
        'boundary_edges': int(np.sum(edge_counts == 1)),
        'nonmanifold_edges': int(np.sum(edge_counts > 2)),
        'edge_manifold_closed': bool(np.all(edge_counts == 2)),
        'winding_consistent_on_two_face_edges': bool(np.all(edge_orientation[edge_counts == 2] == 0)),
        'zero_area_triangles': int(np.sum(twice_area == 0)),
        'duplicate_triangles_ignoring_winding': len(faces) - len(np.unique(np.sort(faces, axis=1), axis=0)),
        'euler_characteristic': len(vertices) - len(unique_edges) + len(faces),
        'triangle_quality_equilateral_1': {
            'minimum': float(quality.min()), 'p01': float(np.quantile(quality, .01)),
            'p50': float(np.quantile(quality, .5))},
        'signed_volume_scan_units_cubed': volume,
        'area_scan_units_squared': float(twice_area.sum() / 2),
        'bounds_scan_units_private': bounds.tolist(),
        'extents_scan_units': (bounds[1] - bounds[0]).tolist(),
        'coordinate_welding': 'identical_float_values_only_no_tolerance_repair',
        'self_intersections_tested': False,
    }


def validate_settings(deflection, angle):
    if not math.isfinite(deflection) or not 0 < deflection <= .05:
        raise ValueError('absolute_deflection_must_be_positive_and_at_most_0p05_scan_unit')
    if not math.isfinite(angle) or not 0 < angle <= .25:
        raise ValueError('angular_deflection_must_be_positive_and_at_most_0p25_radian')


def export(args):
    validate_settings(args.deflection, args.angular_deflection)
    before = sha256(args.step)
    if before != args.sha256:
        raise ValueError('master_STEP_hash_mismatch')
    if args.output.exists():
        raise FileExistsError(args.output)
    import OCP
    from OCP.STEPControl import STEPControl_Reader
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.StlAPI import StlAPI_Writer
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from OCP.TopAbs import TopAbs_SOLID, TopAbs_SHELL
    from OCP.TopExp import TopExp
    from OCP.TopTools import TopTools_IndexedMapOfShape

    reader = STEPControl_Reader()
    if reader.ReadFile(str(args.step)) != IFSelect_RetDone or reader.TransferRoots() < 1:
        raise ValueError('STEP_import_failed')
    shape = reader.OneShape()
    if shape.IsNull():
        raise ValueError('null_STEP_shape')
    analyzer = BRepCheck_Analyzer(shape, True)
    analyzer.SetExactMethod(True)
    if not analyzer.IsValid():
        raise ValueError('master_BRep_invalid')
    counts = {}
    for label, kind in [('solids', TopAbs_SOLID), ('shells', TopAbs_SHELL)]:
        mapping = TopTools_IndexedMapOfShape()
        TopExp.MapShapes_s(shape, kind, mapping)
        counts[label] = mapping.Extent()
    if counts != {'solids': 1, 'shells': 1}:
        raise ValueError('single_body_single_shell_required_not_assembly')
    properties = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, properties)
    volume = float(properties.Mass())
    if volume <= 0:
        raise ValueError('positive_BRep_volume_required')
    mesher = BRepMesh_IncrementalMesh(shape, args.deflection, False, args.angular_deflection, True)
    if not mesher.IsDone():
        raise RuntimeError('STEP_tessellation_failed')
    args.output.mkdir(parents=True, mode=0o700)
    stl = args.output / 'master-body.stl'
    writer = StlAPI_Writer()
    writer.ASCIIMode = False
    if not writer.Write(shape, str(stl)):
        raise RuntimeError('binary_STL_export_failed')
    stl.chmod(0o600)
    summary = mesh_summary(load_binary_stl(stl))
    unchanged = sha256(args.step) == before
    report = {
        'schema': 'm64-picogk-private-master-export/v1', 'source_STEP_sha256': before,
        'export_source_sha256': sha256(Path(__file__)), 'mesh_sha256': sha256(stl),
        'OCP_version': OCP.__version__, 'BRep_exact_check_valid': True, 'BRep_counts': counts,
        'BRep_volume_scan_units_cubed': volume,
        'tessellation': {'linear_deflection_scan_units': args.deflection, 'relative': False,
                         'angular_deflection_radians': args.angular_deflection,
                         'settings_are_not_global_Hausdorff_or_manufacturing_tolerance': True,
                         'STL_coordinate_representation': 'IEEE_float32'},
        'mesh': summary,
        'STL_to_BRep_volume_relative_error': abs(summary['signed_volume_scan_units_cubed'] - volume) / volume,
        'length_unit': 'scan_unit', 'millimetres_per_scan_unit_working_hypothesis': 1.0,
        'absolute_scale_certified': False, 'registration_already_applied_in_body': True,
        'new_coordinate_transform_applied': False, 'source_STEP_unchanged': unchanged,
        'private_derived_geometry_not_for_publication': True,
        'manufacturing_authorized': False, 'engine_operation_authorized': False,
    }
    valid = (unchanged and summary['edge_manifold_closed'] and summary['winding_consistent_on_two_face_edges']
             and summary['connected_vertex_components'] == 1 and summary['zero_area_triangles'] == 0
             and summary['duplicate_triangles_ignoring_winding'] == 0
             and summary['signed_volume_scan_units_cubed'] > 0)
    report['voxel_input_topology_gate_passed'] = valid
    target = args.output / 'export-report.json'
    target.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    target.chmod(0o600)
    print(json.dumps({'mesh_sha256': report['mesh_sha256'], 'triangles': summary['triangles'],
                      'voxel_input_topology_gate_passed': valid, 'manufacturing_authorized': False}))
    return 0 if valid else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--step', type=Path, required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--deflection', type=float, default=.05)
    parser.add_argument('--angular-deflection', type=float, default=.15)
    return export(parser.parse_args())


if __name__ == '__main__':
    raise SystemExit(main())
