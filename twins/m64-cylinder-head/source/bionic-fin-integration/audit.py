"""Independent raw-mesh and bounded-zone inspection; never repairs a head."""
import argparse
import importlib.util
import json
import math
from pathlib import Path
import struct

import numpy as np

HERE = Path(__file__).resolve().parent
HELPER = HERE.parent/'picogk/export_master.py'
SPEC = importlib.util.spec_from_file_location('head_mesh_auditor', HELPER)
mesh = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mesh)


def raw_surface_summary(triangles):
    """Same exact coordinate indexing as the existing auditor; sparse connectivity."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    if triangles.ndim != 3 or triangles.shape[1:] != (3, 3) or not len(triangles) or not np.isfinite(triangles).all():
        raise ValueError('Nonempty finite triangles required')
    vertices, inverse = np.unique(triangles.reshape(-1, 3), axis=0, return_inverse=True)
    faces = inverse.astype(np.int32).reshape(-1, 3)
    del inverse
    raw_edges = np.concatenate([faces[:, p] for p in ((0, 1), (1, 2), (2, 0))])
    edges, ids, counts = np.unique(np.sort(raw_edges, axis=1), axis=0, return_inverse=True, return_counts=True)
    directions = (raw_edges[:, 0] < raw_edges[:, 1]).astype(np.int8)*2-1
    balance = np.bincount(ids, weights=directions, minlength=len(edges))
    del raw_edges, ids, directions
    graph = coo_matrix((np.ones(len(edges), dtype=np.uint8), (edges[:, 0], edges[:, 1])),
                       shape=(len(vertices), len(vertices))).tocsr()
    components = int(connected_components(graph, directed=False, return_labels=False))
    del graph
    duplicate = len(faces)-len(np.unique(np.sort(faces, axis=1), axis=0))
    origin = vertices.mean(axis=0)
    volume, area, zero = [], [], 0
    for start in range(0, len(triangles), 100_000):
        t = triangles[start:start+100_000]
        crosses = np.cross(t[:, 1]-t[:, 0], t[:, 2]-t[:, 0])
        norms = np.linalg.norm(crosses, axis=1)
        zero += int((norms == 0).sum()); area.append(float(norms.sum()/2))
        centred = t-origin
        volume.append(float(np.einsum('ij,ij->i', centred[:, 0], np.cross(centred[:, 1], centred[:, 2])).sum()/6))
    bounds = np.array([vertices.min(axis=0), vertices.max(axis=0)])
    return dict(triangles=len(triangles), connected_vertex_components=components,
                boundary_edges=int((counts == 1).sum()), nonmanifold_edges=int((counts > 2).sum()),
                edge_manifold_closed=bool((counts == 2).all()),
                winding_consistent_on_two_face_edges=bool((balance[counts == 2] == 0).all()),
                zero_area_triangles=zero, duplicate_triangles_ignoring_winding=duplicate,
                signed_volume_scan_units_cubed=math.fsum(volume), area_scan_units_squared=math.fsum(area),
                bounds_scan_units_private=bounds.tolist(), coordinate_welding='identical_float_values_only_no_tolerance_repair',
                self_intersections_tested=False)


def in_zones(points, zones, halo):
    result = np.zeros(len(points), dtype=bool)
    for zone in zones:
        result |= ((points >= np.array(zone['min'])-halo) &
                   (points <= np.array(zone['max'])+halo)).all(axis=1)
    return result


def bbox_clearance(lo, hi, zones, halo):
    return min(float(np.linalg.norm(np.maximum(np.maximum(np.array(z['min'])-halo-hi,
                                                          lo-np.array(z['max'])-halo), 0))) for z in zones)


def validate_report(report, contract):
    if report.get('schema') != 'm64-bionic-head-integration/v1' or report.get('fin_count') != 6:
        raise ValueError('Exact six-fin integration required')
    for key in ('source_master_modified', 'full_functional_assembly', 'thermal_gain_transferred_from_coupon',
                'thermal_simulation', 'structural_simulation', 'manufacturing_authorized',
                'physical_root_attachment_verified', 'measured_interfaces_verified'):
        if report.get(key) is not False:
            raise ValueError('Promoted or missing engineering authority: '+key)
    native = report.get('representation') == 'native_cad_with_analytic_picogk_profile_counterpart'
    if native:
        preservation = (report.get('native_solid_count') == report.get('native_shell_count') == 1
                        and report.get('native_validity_and_readback_passed') is True
                        and report.get('native_outside_mask_solid_counts') == [0, 0]
                        and report.get('core_preservation_is_at_voxel_resolution_only') is False)
    else:
        preservation = (report.get('voxel_scan_units') in (.3, .15)
                        and report.get('outside_mask_halo_changes') == {'added_triangles': 0, 'removed_triangles': 0}
                        and report.get('core_preservation_is_at_voxel_resolution_only') is True)
    if report.get('units') != contract['units'] or not preservation:
        raise ValueError('Protected-region screen or units changed')
    rows = report['files']
    if len(rows) != 5 or {r['filename'] for r in rows} != {'baseline.stl', 'head-bionic.stl', 'fins.stl', 'added.stl', 'removed.stl'}:
        raise ValueError('Exact five outputs required')
    return rows


def run(inputs, directory, output):
    if output.exists():
        raise FileExistsError(output)
    contract_path = HERE/'contract.json'
    contract = json.loads(contract_path.read_text())
    receipt = directory/'integration.json'
    report = json.loads(receipt.read_text())
    rows = validate_report(report, contract)
    if report['contract_sha256'] != mesh.sha256(contract_path) or report['head_stl_sha256'] != contract['head_stl_sha256']:
        raise ValueError('Different retained contract or head')
    if mesh.sha256(inputs/'inputs.json') != contract['input_manifest_sha256']:
        raise ValueError('Different retained module')
    result = dict(schema='m64-bionic-head-inspection/v1', status='incomplete',
                  contract_sha256=mesh.sha256(contract_path), producer_sha256=mesh.sha256(receipt),
                  inspector_sha256=mesh.sha256(Path(__file__)), helper_sha256=mesh.sha256(HELPER),
                  meshes={}, references=[], manufacturing_authorized=False, real_engine_fit_verified=False,
                  geometric_self_intersections_checked=False, vertex_link_manifoldness_checked=False,
                  physical_wall_thickness_verified=False)
    # Complete raw arrays, one file at a time; no decimation or triangle deletion.
    for row in rows:
        path = directory/row['filename']
        if path.is_symlink() or mesh.sha256(path) != row['sha256']:
            raise ValueError('Output hash changed')
        with path.open('rb') as stream:
            count = struct.unpack('<I', stream.read(84)[80:84])[0]
        if not 0 < count <= 20_000_000:
            raise ValueError('Bounded twenty-million-face mesh required')
        triangles = mesh.load_binary_stl(path)
        summary = raw_surface_summary(triangles)
        dtype = np.dtype([('normal', '<f4', (3,)), ('vertices', '<f4', (3, 3)), ('attribute', '<u2')])
        raw = np.memmap(path, dtype=dtype, mode='r', offset=84, shape=(count,))
        summary['nonfinite_stl_normals'] = int((~np.isfinite(raw['normal']).all(axis=1)).sum())
        summary['sha256'] = row['sha256']
        if row['filename'] in ('added.stl', 'removed.stl', 'fins.stl'):
            outside = 0
            for block in range(0, len(triangles), 100_000):
                outside += int((~in_zones(triangles[block:block+100_000].reshape(-1, 3), contract['modified_zones'], contract['audit_halo'])).sum())
            summary['vertices_outside_independent_zone_halo'] = outside
        result['meshes'][row['filename']] = summary
        print(json.dumps(dict(file=row['filename'], components=summary['connected_vertex_components'],
                              boundary=summary['boundary_edges'], zero_area=summary['zero_area_triangles'])), flush=True)
        del triangles, raw
    for row in report['reference_parts']:
        if row['name'] == 'head':
            continue
        path = inputs/row['filename']
        if path.is_symlink() or mesh.sha256(path) != row['sha256']:
            raise ValueError('Reference part changed')
        triangles = mesh.load_binary_stl(path)
        clearance = bbox_clearance(triangles.min(axis=(0, 1)), triangles.max(axis=(0, 1)), contract['modified_zones'], contract['audit_halo'])
        if clearance <= 0:
            raise ValueError('Modification mask is not separated from a reference component')
        result['references'].append(dict(name=row['name'], sha256=row['sha256'],
                                         bounding_box_separation_from_change_halo=clearance,
                                         real_clearance_not_verified=True))
    bodies = [result['meshes'][n] for n in ('baseline.stl', 'head-bionic.stl')]
    passed = all(v['edge_manifold_closed'] and v['winding_consistent_on_two_face_edges']
                 and v['connected_vertex_components'] == 1 and v['zero_area_triangles'] == 0
                 and v['duplicate_triangles_ignoring_winding'] == 0 and v['nonfinite_stl_normals'] == 0
                 and v['signed_volume_scan_units_cubed'] > 0 for v in bodies)
    passed &= all(result['meshes'][n]['vertices_outside_independent_zone_halo'] == 0 for n in ('added.stl', 'removed.stl', 'fins.stl'))
    result.update(status='geometry_screen_passed_not_engineering_release' if passed else 'rejected_geometry_screen',
                  source_files_unchanged=all(mesh.sha256(inputs/r['filename']) == r['sha256'] for r in report['reference_parts']),
                  thermal_gain_for_integrated_head=None)
    if report.get('representation') == 'native_cad_with_analytic_picogk_profile_counterpart':
        from OCP.BRep import BRep_Builder
        from OCP.BRepTools import BRepTools
        from OCP.BRepCheck import BRepCheck_Analyzer
        from OCP.TopoDS import TopoDS_Shape
        from OCP.STEPControl import STEPControl_Reader
        from OCP.IFSelect import IFSelect_RetDone
        native_path, step_path = directory/'head-bionic.brep', directory/'head-bionic.step'
        if mesh.sha256(native_path) != report['brep_sha256'] or mesh.sha256(step_path) != report['step_sha256']:
            raise ValueError('Native export hash mismatch')
        shape = TopoDS_Shape()
        if not BRepTools.Read_s(shape, str(native_path), BRep_Builder()) or not BRepCheck_Analyzer(shape, True, False, True).IsValid():
            raise ValueError('Independent native BRep readback failed')
        reader = STEPControl_Reader()
        if reader.ReadFile(str(step_path)) != IFSelect_RetDone or reader.TransferRoots() <= 0:
            raise ValueError('STEP read failed')
        imported = reader.OneShape()
        result['native_brep'] = dict(sha256=report['brep_sha256'], exact_readback_valid=True, preferred_editable_artifact=True)
        step_valid = BRepCheck_Analyzer(imported, True, False, True).IsValid()
        result['step_export'] = dict(sha256=report['step_sha256'], standard_readback_valid=BRepCheck_Analyzer(imported, True, False, False).IsValid(),
                                     exact_readback_valid=step_valid, qualified_for_further_exact_cad=step_valid)
        if passed and not step_valid:
            result['status'] = 'native_geometry_screen_passed_step_export_unqualified'
    with output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    return 0 if passed and result['source_files_unchanged'] else 3


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('inputs', 'directory', 'output'):
        parser.add_argument('--'+key, type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.inputs, args.directory, args.output))
