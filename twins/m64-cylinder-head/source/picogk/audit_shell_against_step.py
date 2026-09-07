#!/usr/bin/env python3
"""Locate one private roundtrip boundary shell and compare its region with STEP.

Two runtimes may be used: ``extract`` needs Trimesh/SciPy; ``occt`` needs OCP.
Source geometry is never changed. All coordinates and derived regions remain
private. Boolean results concern the supplied CAD under kernel tolerances,
not physical porosity, certified fitment, repair permission or fabrication.
"""
import argparse
import json
from pathlib import Path

from compare_meshes import atomic_private_json
from export_master import sha256


def private_directory(path):
    path = Path(path)
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.mkdir(parents=True, mode=0o700)


def extract(args):
    import numpy as np
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    from audit_roundtrip_shells import read_exact_welded_mesh, verified_receipt
    receipt, receipt_hash, candidate_hash = verified_receipt(args)
    private_directory(args.output)
    mesh = read_exact_welded_mesh(args.candidate)
    if len(mesh.faces) != receipt['roundtrip']['triangles']:
        raise ValueError('candidate_triangle_count_mismatch')
    adjacency = mesh.face_adjacency
    graph = coo_matrix((np.ones(len(adjacency), dtype=np.int8), (adjacency[:, 0], adjacency[:, 1])),
                       shape=(len(mesh.faces), len(mesh.faces))).tocsr()
    count, labels = connected_components(graph, directed=False)
    if not 0 <= args.shell_index < count:
        raise ValueError('requested_shell_index_not_present')
    indices = np.flatnonzero(labels == args.shell_index)
    triangles = mesh.triangles[indices]
    center = (triangles.min(axis=(0, 1)) + triangles.max(axis=(0, 1))) / 2
    shifted = triangles - center
    volume = float(np.einsum('ij,ij->i', shifted[:, 0],
                            np.cross(shifted[:, 1], shifted[:, 2])).sum() / 6)
    payload = {
        'schema': 'm64-private-exact-shell-triangles/v1', 'candidate_STL_sha256': candidate_hash,
        'boundary_shell_index': args.shell_index, 'input_face_indices_private': indices.tolist(),
        'triangles_private': triangles.tolist(), 'signed_volume_scan_units_cubed': volume,
    }
    triangle_path = args.output / 'shell-triangles-private.json'
    atomic_private_json(triangle_path, payload)
    report = {
        'schema': 'm64-private-shell-location/v1', 'audit_source_sha256': sha256(Path(__file__)),
        'candidate_STL_sha256': candidate_hash, 'run_receipt_sha256': receipt_hash,
        'master_STL_sha256_from_run': args.master_sha256, 'voxel_size_scan_units': args.voxel_size,
        'boundary_shell_index': args.shell_index, 'total_boundary_shells': int(count),
        'triangles': len(triangles), 'signed_volume_scan_units_cubed': volume,
        'bounds_private': [triangles.min(axis=(0, 1)).tolist(), triangles.max(axis=(0, 1)).tolist()],
        'bbox_center_private': center.tolist(), 'triangle_payload_sha256': sha256(triangle_path),
        'boundary_shell_connectivity': 'faces_connected_by_shared_edges',
        'absolute_scale_certified': False, 'geometry_modified': False,
        'manufacturing_authorized': False,
    }
    if sha256(args.candidate) != candidate_hash or sha256(args.run_report) != receipt_hash:
        raise ValueError('source_changed_during_shell_extraction')
    report['source_unchanged_after_extraction'] = True
    atomic_private_json(args.output / 'shell-location-private.json', report)
    print(json.dumps({'shell_index': args.shell_index, 'triangles': len(triangles),
                      'signed_volume': volume, 'source_unchanged': True}), flush=True)
    return 0


def shape_counts(shape):
    from OCP.TopAbs import TopAbs_SOLID, TopAbs_SHELL, TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX
    from OCP.TopExp import TopExp
    from OCP.TopTools import TopTools_IndexedMapOfShape
    result = {}
    for name, kind in [('solids', TopAbs_SOLID), ('shells', TopAbs_SHELL), ('faces', TopAbs_FACE),
                       ('edges', TopAbs_EDGE), ('vertices', TopAbs_VERTEX)]:
        mapping = TopTools_IndexedMapOfShape()
        if not shape.IsNull():
            TopExp.MapShapes_s(shape, kind, mapping)
        result[name] = mapping.Extent()
    return result


def shape_volume(shape):
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    properties = GProp_GProps()
    if not shape.IsNull():
        BRepGProp.VolumeProperties_s(shape, properties)
    return float(properties.Mass())


def valid_shape(shape):
    from OCP.BRepCheck import BRepCheck_Analyzer
    if shape.IsNull():
        return True
    analyzer = BRepCheck_Analyzer(shape, True)
    analyzer.SetExactMethod(True)
    return bool(analyzer.IsValid())


def region_from_triangles(triangles):
    from OCP.BRepBuilderAPI import (BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace,
                                   BRepBuilderAPI_Sewing, BRepBuilderAPI_MakeSolid)
    from OCP.BRepLib import BRepLib
    from OCP.Precision import Precision
    from OCP.TopoDS import TopoDS
    from OCP.gp import gp_Pnt
    sewing = BRepBuilderAPI_Sewing(Precision.Confusion_s())
    for triangle in triangles:
        polygon = BRepBuilderAPI_MakePolygon()
        for point in triangle:
            polygon.Add(gp_Pnt(*point))
        polygon.Close()
        if not polygon.IsDone():
            raise ValueError('diagnostic_triangle_wire_failed')
        face = BRepBuilderAPI_MakeFace(polygon.Wire(), True)
        if not face.IsDone():
            raise ValueError('diagnostic_triangle_face_failed')
        sewing.Add(face.Face())
    sewing.Perform()
    shell = sewing.SewedShape()
    counts = shape_counts(shell)
    if counts['shells'] != 1 or counts['faces'] != len(triangles):
        raise ValueError('single_exact_triangle_shell_required')
    solid = BRepBuilderAPI_MakeSolid(TopoDS.Shell_s(shell)).Solid()
    # A negative-oriented STL shell describes a removed region. Orient only
    # this separate Boolean diagnostic operand outward, never the source mesh.
    if not BRepLib.OrientClosedSolid_s(solid) or not valid_shape(solid) or shape_volume(solid) <= 0:
        raise ValueError('positive_valid_closed_diagnostic_region_required')
    return solid


def boolean_partition(region, master):
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut, BRepAlgoAPI_Common
    from OCP.TopTools import TopTools_ListOfShape
    region_volume = shape_volume(region)
    results = {}
    for name, operation in [('region_minus_master', BRepAlgoAPI_Cut),
                            ('region_intersect_master', BRepAlgoAPI_Common)]:
        arguments = TopTools_ListOfShape(); arguments.Append(region)
        tools = TopTools_ListOfShape(); tools.Append(master)
        algorithm = operation()
        algorithm.SetArguments(arguments); algorithm.SetTools(tools)
        algorithm.SetNonDestructive(True); algorithm.SetFuzzyValue(0.0); algorithm.SetRunParallel(False)
        algorithm.Build()
        if not algorithm.IsDone():
            raise ValueError('diagnostic_boolean_operation_failed_' + name)
        shape = algorithm.Shape()
        results[name] = {'is_done': True, 'exact_BRep_check_valid': valid_shape(shape),
                         'topology_counts': shape_counts(shape), 'signed_volume': shape_volume(shape)}
    cut = results['region_minus_master']; common = results['region_intersect_master']
    error = abs(cut['signed_volume'] + common['signed_volume'] - region_volume) / abs(region_volume)
    results.update({
        'diagnostic_region_volume': region_volume, 'partition_relative_volume_error': error,
        'partition_volume_crosscheck_passed': bool(error < 1e-8),
        'volume_crosscheck_tolerance': 1e-8,
        'region_minus_master_topologically_empty': all(value == 0 for value in cut['topology_counts'].values()),
        'full_region_inside_master_supported_under_OCCT_tolerances': bool(
            all(value == 0 for value in cut['topology_counts'].values())
            and cut['exact_BRep_check_valid'] and common['exact_BRep_check_valid'] and error < 1e-8
            and abs(common['signed_volume'] - region_volume) / abs(region_volume) < 1e-8),
        'geometrically_exact_or_physical_containment_certified': False,
    })
    return results


def occt(args):
    import OCP
    from OCP.STEPControl import STEPControl_Reader
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.Precision import Precision
    if args.output.exists() or args.output.is_symlink():
        raise FileExistsError(args.output)
    if args.output.parent.stat().st_mode & 0o077:
        raise ValueError('private_output_directory_required')
    before = sha256(args.step)
    if before != args.step_sha256:
        raise ValueError('master_STEP_sha256_mismatch')
    export_hash = sha256(args.master_export_report)
    export = json.loads(args.master_export_report.read_text())
    location_hash = sha256(args.location)
    location = json.loads(args.location.read_text())
    payload_hash = sha256(args.triangles)
    payload = json.loads(args.triangles.read_text())
    if (export['source_STEP_sha256'] != before
            or export['mesh_sha256'] != location['master_STL_sha256_from_run']
            or export.get('source_STEP_unchanged') is not True
            or export.get('new_coordinate_transform_applied') is not False
            or payload_hash != location['triangle_payload_sha256']
            or payload['candidate_STL_sha256'] != location['candidate_STL_sha256']
            or payload['boundary_shell_index'] != location['boundary_shell_index']
            or len(payload['triangles_private']) != location['triangles']):
        raise ValueError('private_shell_payload_provenance_mismatch')
    reader = STEPControl_Reader()
    if reader.ReadFile(str(args.step)) != IFSelect_RetDone or reader.TransferRoots() < 1:
        raise ValueError('master_STEP_read_failed')
    master = reader.OneShape()
    if shape_counts(master)['solids'] != 1 or not valid_shape(master) or shape_volume(master) <= 0:
        raise ValueError('master_must_be_one_valid_positive_solid')
    region = region_from_triangles(payload['triangles_private'])
    shell_volume_error = abs(shape_volume(region) - abs(payload['signed_volume_scan_units_cubed'])) / abs(
        payload['signed_volume_scan_units_cubed'])
    if shell_volume_error >= 1e-8:
        raise ValueError('diagnostic_region_volume_differs_from_exact_triangle_shell')
    report = {
        'schema': 'm64-private-shell-STEP-boolean-audit/v1', 'OCP_version': OCP.__version__,
        'audit_source_sha256': sha256(Path(__file__)), 'master_STEP_sha256': before,
        'master_export_report_sha256': export_hash,
        'candidate_STL_sha256': location['candidate_STL_sha256'],
        'shell_location_sha256': location_hash, 'shell_triangles_sha256': payload_hash,
        'boundary_shell_index': location['boundary_shell_index'], 'triangles': location['triangles'],
        'original_shell_signed_volume': payload['signed_volume_scan_units_cubed'],
        'diagnostic_operand_oriented_outward_only': True,
        'diagnostic_operand_volume_relative_difference': shell_volume_error,
        'OCCT_sewing_tolerance_scan_units': Precision.Confusion_s(), 'boolean_fuzzy_value': 0.0,
        'master_exact_BRep_check_valid': True, 'diagnostic_operand_exact_BRep_check_valid': True,
        'boolean_partition': boolean_partition(region, master),
        'point_sampling_used_as_containment_proof': False,
        'source_geometry_modified': False, 'physical_porosity_identified': False,
        'manufacturing_authorized': False, 'cavity_removal_authorized_by_this_diagnostic': False,
    }
    if (sha256(args.step) != before or sha256(args.master_export_report) != export_hash
            or sha256(args.location) != location_hash
            or sha256(args.triangles) != payload_hash):
        raise ValueError('source_changed_during_OCCT_audit')
    report['source_files_unchanged'] = True
    atomic_private_json(args.output, report)
    print(json.dumps({'shell_index': location['boundary_shell_index'],
                      'partition': report['boolean_partition'], 'source_files_unchanged': True}), flush=True)
    return 0 if report['boolean_partition']['partition_volume_crosscheck_passed'] else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    export = commands.add_parser('extract')
    export.add_argument('--candidate', type=Path, required=True)
    export.add_argument('--candidate-sha256', required=True)
    export.add_argument('--run-report', type=Path, required=True)
    export.add_argument('--master-sha256', required=True)
    export.add_argument('--voxel-size', type=float, required=True)
    export.add_argument('--shell-index', type=int, required=True)
    export.add_argument('--output', type=Path, required=True)
    export.set_defaults(function=extract)
    classify = commands.add_parser('occt')
    classify.add_argument('--step', type=Path, required=True)
    classify.add_argument('--step-sha256', required=True)
    classify.add_argument('--master-export-report', type=Path, required=True)
    classify.add_argument('--triangles', type=Path, required=True)
    classify.add_argument('--location', type=Path, required=True)
    classify.add_argument('--output', type=Path, required=True)
    classify.set_defaults(function=occt)
    args = parser.parse_args()
    return args.function(args)


if __name__ == '__main__':
    raise SystemExit(main())
