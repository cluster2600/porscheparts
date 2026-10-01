#!/usr/bin/env python3
"""Export this concept's native mesh, rejecting open or disconnected results."""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from scipy.spatial import cKDTree
import trimesh
from pxr import Gf, Usd, UsdGeom, Sdf

if len(sys.argv) != 3:
    raise SystemExit('Usage: export.py <native-output-directory> <export-directory>')
native, output = map(Path, sys.argv[1:])
here = Path(__file__).resolve().parent
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
raw = native / 'carrier-concept.stl'
mesh = trimesh.load_mesh(raw, process=False)
original_vertices = mesh.vertices.copy()
original_triangles = len(mesh.faces)
# ponytail: fixed 1 micrometer weld for a 1 mm voxel concept; reject other resolutions.
metrics = json.loads((native / 'native-metrics.json').read_text())
assert metrics['voxel_size_mm'] == 1, 'Use the documented 1 mm concept export.'
mesh.merge_vertices(digits_vertex=3)
mesh.update_faces(mesh.nondegenerate_faces(height=0.001))
mesh.update_faces(mesh.unique_faces())
mesh.remove_unreferenced_vertices()
max_vertex_displacement = float(cKDTree(mesh.vertices).query(original_vertices)[0].max())
assert max_vertex_displacement <= 0.002, 'Cleanup moved the sampled surface too far.'
assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume > 0
assert len(mesh.split(only_watertight=False)) == 1, 'Disconnected concept mesh.'
assert mesh.euler_number == -6, 'Expected two windows and two boss bores.'
assert np.all(mesh.extents <= [601, 51, 51]), 'Declared envelope exceeded.'

output.mkdir(parents=True, exist_ok=True)
stl = output / 'carrier-concept.stl'
mesh.export(stl)
usd = output / 'carrier-concept.usdc'
stage = Usd.Stage.CreateNew(str(usd))
UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
UsdGeom.SetStageMetersPerUnit(stage, 0.001)
root = UsdGeom.Xform.Define(stage, '/CarrierConcept')
stage.SetDefaultPrim(root.GetPrim())
root.GetPrim().CreateAttribute('partNumber', Sdf.ValueTypeNames.String).Set('993 115 021 53')
root.GetPrim().CreateAttribute('validationStatus', Sdf.ValueTypeNames.String).Set('concept_not_oem_not_for_manufacturing')
surface = UsdGeom.Mesh.Define(stage, '/CarrierConcept/Surface')
surface.CreatePointsAttr([Gf.Vec3f(*p) for p in mesh.vertices])
surface.CreateFaceVertexCountsAttr([3] * len(mesh.faces))
surface.CreateFaceVertexIndicesAttr(mesh.faces.reshape(-1).tolist())
surface.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
surface.CreateExtentAttr([Gf.Vec3f(*p) for p in mesh.bounds])
surface.CreateDisplayColorAttr([Gf.Vec3f(0.55, 0.59, 0.62)])
stage.GetRootLayer().Save()
reopened = Usd.Stage.Open(str(usd))
assert UsdGeom.GetStageMetersPerUnit(reopened) == 0.001
assert UsdGeom.GetStageUpAxis(reopened) == UsdGeom.Tokens.z
check = UsdGeom.Mesh(reopened.GetPrimAtPath('/CarrierConcept/Surface'))
assert np.array_equal(np.asarray(check.GetPointsAttr().Get()), mesh.vertices.astype(np.float32))
assert np.array_equal(np.asarray(check.GetFaceVertexIndicesAttr().Get()), mesh.faces.reshape(-1))

report = {
    'status': 'checked_digital_concept_not_oem_not_for_manufacturing',
    'native': metrics,
    'mesh': {'triangles_before_cleanup': original_triangles, 'triangles': len(mesh.faces),
             'vertices': len(mesh.vertices), 'watertight': bool(mesh.is_watertight),
             'winding_consistent': bool(mesh.is_winding_consistent), 'connected_components': 1,
             'euler_characteristic': int(mesh.euler_number), 'volume_mm3': float(mesh.volume),
             'bounds_mm': mesh.extents.tolist(), 'max_original_vertex_distance_mm': max_vertex_displacement,
             'weld_decimal_digits': 3, 'degenerate_face_height_threshold_mm': 0.001,
             'self_intersection_checked': False, 'oem_fidelity_checked': False},
    'usd': {'version': list(Usd.GetVersion()), 'reopened': True, 'mesh_arrays_match': True,
            'meters_per_unit': 0.001, 'up_axis': 'Z', 'physics_assigned': False, 'simready_validated': False},
    'inputs': {'Program.cs': digest(here / 'Program.cs'), 'inference.json': digest(here / 'inference.json'),
               'export.py': digest(Path(__file__)), 'native_stl': digest(raw),
               'native_metrics': digest(native / 'native-metrics.json')},
    'outputs': {stl.name: digest(stl), usd.name: digest(usd)},
    'physical_part_access_confirmed': False, 'is_fitment_validated': False,
    'is_material_qualified': False, 'is_manufacturing_release': False
}
(output / 'checks.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report['mesh'], indent=2))
