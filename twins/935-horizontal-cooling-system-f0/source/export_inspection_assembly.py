#!/usr/bin/env python3
"""Audit real PicoGK placements and export an inspection-only GLB/USD assembly."""
import argparse
import json
from pathlib import Path
import struct

import numpy as np
import trimesh

from run_reconstruction import fresh, save, sha
from stl_moments import DTYPE

FLAGS = ('scale_verified', 'interfaces_verified', 'mechanism_dynamics_validated',
         'historical_installation_verified', 'manufacturing_authorized', 'physical_validation')
COLORS = {'engine_context': (.55, .61, .65), 'drive_observed': (.72, .43, .20),
          'rotor_candidate': (.20, .57, .76), 'provisional_shroud': (.47, .66, .40)}


def triangles(path):
    path = Path(path)
    with path.open('rb') as stream:
        header = stream.read(84)
    if len(header) != 84:
        raise ValueError('Binary STL required')
    count = struct.unpack('<I', header[80:])[0]
    if count == 0 or count > 5000000 or path.stat().st_size != 84 + 50 * count:
        raise ValueError('Bounded nonempty binary STL required')
    return np.memmap(path, mode='r', dtype=DTYPE, offset=84, shape=(count,))['vertices']


def placement_error(source, placed, matrix):
    matrix = np.asarray(matrix, dtype=float)
    if matrix.shape != (4, 4) or not np.isfinite(matrix).all():
        raise ValueError('Finite 4x4 transform required')
    if source.shape != placed.shape:
        raise ValueError('Triangle count changed')
    maximum = 0.
    for start in range(0, len(source), 100000):
        expected = source[start:start+100000].astype(float) @ matrix[:3, :3].T + matrix[:3, 3]
        difference = np.abs(expected - placed[start:start+100000])
        if not np.isfinite(difference).all():
            raise ValueError('Nonfinite triangle coordinates')
        maximum = max(maximum, float(difference.max()))
    if maximum > .0002:
        raise ValueError('PicoGK placement differs from column-vector transform')
    return maximum


def radial_minimum(faces):
    """Exact XY distance to each projected triangle, including its edge interiors."""
    p = np.asarray(faces, dtype=float)[..., :2]
    if p.ndim != 3 or p.shape[1:] != (3, 2) or not len(p) or not np.isfinite(p).all():
        raise ValueError('Finite nonempty triangles required')
    minimum = np.full(len(p), np.inf)
    crosses = []
    for index in range(3):
        a, b = p[:, index], p[:, (index+1) % 3]
        d = b-a; length = np.sum(d*d, axis=1)
        t = np.clip(-np.sum(a*d, axis=1) / np.maximum(length, 1e-30), 0, 1)
        minimum = np.minimum(minimum, np.linalg.norm(a + t[:, None]*d, axis=1))
        crosses.append(a[:, 0]*b[:, 1] - a[:, 1]*b[:, 0])
    crosses = np.asarray(crosses).T
    inside = np.all(crosses > 0, axis=1) | np.all(crosses < 0, axis=1)
    minimum[inside] = 0
    return float(minimum.min())


def cylinder_candidates(faces, zlow, zhigh, rlow, rhigh):
    """Conservative triangle-box witnesses; zero certifies surface separation only."""
    low, high = faces.min(axis=1), faces.max(axis=1)
    nearest_xy = np.where((low[:, :2] <= 0) & (high[:, :2] >= 0), 0,
                          np.minimum(np.abs(low[:, :2]), np.abs(high[:, :2])))
    radial_low = np.linalg.norm(nearest_xy, axis=1)
    radial_high = np.linalg.norm(faces[..., :2], axis=2).max(axis=1)
    return int(np.count_nonzero((high[:, 2] >= zlow) & (low[:, 2] <= zhigh)
                               & (radial_low <= rhigh) & (radial_high >= rlow)))


def export(native, output):
    from pxr import Gf, Usd, UsdGeom, Vt
    native = Path(native).resolve()
    case_path, receipt_path = native/'case.json', native/'receipt.json'
    case, receipt = json.loads(case_path.read_text()), json.loads(receipt_path.read_text())
    if (receipt.get('status') != 'PicoGK_inspection_assembly_not_verified_installation'
            or any(receipt.get(key) is not False for key in FLAGS)
            or case.get('scale_verified') is not False or sha(case_path) != receipt['case_sha256']):
        raise ValueError('Uncalibrated PicoGK inspection receipt required')
    rows = receipt['components']; ids = [row['id'] for row in rows]
    expected_ids = set(COLORS)
    if set(ids) != expected_ids or len(ids) != len(expected_ids):
        raise ValueError('Expected engine, observed drive, candidate rotor and provisional shroud')
    errors = {}
    for row in rows:
        if Path(row['file']).name != row['file'] or sha(native/row['file']) != row['sha256']:
            raise ValueError('Component hash mismatch')
        if len(triangles(native/row['file'])) != row['triangles']:
            raise ValueError('Receipt triangle count mismatch')
    for item in case['imports']:
        if sha(item['path']) != item['sha256']:
            raise ValueError('Original input changed')
        errors[item['id']] = placement_error(triangles(item['path']),
            triangles(native/(item['id']+'.stl')), item['source_to_assembly_mm'])
    origin = np.asarray(case['shroud']['origin_mm'])
    rotor = triangles(native/'rotor_candidate.stl').astype(float) - origin
    rotor_radius = float(np.linalg.norm(rotor[..., :2], axis=-1).max())
    rotor_inner_radius = radial_minimum(rotor)
    shroud = triangles(native/'provisional_shroud.stl').astype(float) - origin
    shroud_radius = radial_minimum(shroud)
    if shroud_radius <= rotor_radius:
        raise ValueError('No certified radial rotor/shroud separation')
    drive = triangles(native/'drive_observed.stl').astype(float) - origin
    drive_rotor = cylinder_candidates(drive, rotor[..., 2].min(), rotor[..., 2].max(), rotor_inner_radius, rotor_radius)
    drive_shroud = cylinder_candidates(drive, shroud[..., 2].min(), shroud[..., 2].max(),
                                      shroud_radius, np.linalg.norm(shroud[..., :2], axis=-1).max())
    engine_max_z = float(triangles(native/'engine_context.stl')[..., 2].max())
    engine_gaps = {row['id']:float(triangles(native/row['file'])[..., 2].min())-engine_max_z
                   for row in rows if row['id'] != 'engine_context'}
    shroud_mesh = trimesh.load_mesh(native/'provisional_shroud.stl', process=True)
    if not shroud_mesh.is_watertight or not shroud_mesh.is_winding_consistent or shroud_mesh.volume <= 0:
        raise ValueError('Provisional shroud topology failed')
    out = fresh(output)
    stage_path = out/'assembly-inspection.usdc'
    stage = Usd.Stage.CreateNew(str(stage_path))
    UsdGeom.SetStageMetersPerUnit(stage, 1); UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    world = UsdGeom.Xform.Define(stage, '/World'); stage.SetDefaultPrim(world.GetPrim())
    world.GetPrim().SetCustomData({**{key: False for key in FLAGS},
        'classification': receipt['status'], 'engine_context_family': receipt['engine_context_family']})
    scene = trimesh.Scene()
    for row in rows:
        name = row['id']; mesh = trimesh.load_mesh(native/row['file'], process=False)
        mesh.apply_scale(.001)
        color = COLORS[name]; mesh.visual.face_colors = np.asarray(np.array([*color, 1])*255, dtype=np.uint8)
        scene.add_geometry(mesh, node_name=name, geom_name=name)
        geometry = UsdGeom.Mesh.Define(stage, '/World/'+name)
        geometry.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(np.asarray(mesh.vertices, dtype=np.float32)))
        geometry.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(len(mesh.faces), 3, dtype=np.int32)))
        geometry.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(np.asarray(mesh.faces, dtype=np.int32).ravel()))
        geometry.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
        geometry.CreateDisplayColorAttr([Gf.Vec3f(*color)])
        geometry.CreateExtentAttr([Gf.Vec3f(*p) for p in mesh.bounds])
        geometry.GetPrim().SetCustomData({'classification':row['classification'], 'input_sha256':row['sha256']})
    stage.GetRootLayer().Save()
    glb = out/'assembly-inspection.glb'
    from trimesh.exchange.gltf import export_glb
    glb.write_bytes(export_glb(scene, include_normals=False))
    reopened = trimesh.load(glb, force='scene', process=False)
    usd = Usd.Stage.Open(str(stage_path))
    if (set(reopened.geometry) != expected_ids or set(reopened.graph.nodes_geometry) != expected_ids
            or UsdGeom.GetStageMetersPerUnit(usd) != 1):
        raise ValueError('Export lost component identity or SI units')
    for name, mesh in scene.geometry.items():
        matrix, geometry_name = reopened.graph[name]
        if geometry_name != name or not np.array_equal(matrix, np.eye(4)):
            raise ValueError('GLB introduced an unexpected component pose')
        candidate = reopened.geometry[name]
        if not np.array_equal(mesh.faces, candidate.faces) or not np.allclose(mesh.vertices, candidate.vertices, rtol=0, atol=1e-6):
            raise ValueError('GLB triangle transport failed')
        geometry = UsdGeom.Mesh(usd.GetPrimAtPath('/World/'+name))
        if (not np.array_equal(np.asarray(geometry.GetFaceVertexIndicesAttr().Get()), mesh.faces.ravel())
                or not np.allclose(np.asarray(geometry.GetPointsAttr().Get()), mesh.vertices, rtol=0, atol=1e-6)):
            raise ValueError('USD triangle transport failed')
    save(out/'report.json', {'status':'inspection_exports_audited', 'native_receipt_sha256':sha(receipt_path),
        'placement_max_error_mm_hypothesis':errors, 'components':rows,
        'assembly_mm_to_import_source':{item['id']:np.linalg.inv(np.asarray(item['source_to_assembly_mm'])).tolist()
                                       for item in case['imports']},
        'engine_context_family':receipt['engine_context_family'],
        'rotor_shroud_360_degree_radial_separation_mm_hypothesis':shroud_radius-rotor_radius,
        'drive_surface_vs_swept_rotor_annular_envelope_candidate_triangles':drive_rotor,
        'swept_rotor_annular_envelope_radius_range_mm_hypothesis':[rotor_inner_radius, rotor_radius],
        'drive_surface_vs_shroud_annular_envelope_candidate_triangles':drive_shroud,
        'engine_bounding_box_vertical_separation_mm_hypothesis':engine_gaps,
        'surface_screen_scope':'zero candidate triangles or positive box gaps certify observed surface separation at this pose; no inferred occupied interiors or mounting contact',
        'clearance_scope':'conservative triangle projection; rotor/shroud only, ambient assumed scale, no thermal or elastic effects',
        'entire_assembly_interference_checked':False, 'shroud_watertight':True,
        'glb_sha256':sha(glb), 'usd_sha256':sha(stage_path), 'millimetre_to_metre_scale':.001,
        'export_triangles_preserved':True, **{key: False for key in FLAGS}})
    print(json.dumps({'output':str(out), 'components':len(rows), 'radial_gap_mm_hypothesis':shroud_radius-rotor_radius}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('native_output'); parser.add_argument('new_private_output')
    args = parser.parse_args(); export(args.native_output, args.new_private_output)
