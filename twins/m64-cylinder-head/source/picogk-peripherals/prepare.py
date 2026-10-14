#!/usr/bin/env python3
"""Tessellate retained private geometry; never author new CAD or change the head."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path

PINS = {
    'head': '9c40df1642d5eb47a3c1a1aae68c761b23b77e3f7e02e0818294e88ee0322598',
    'module': 'fac380b277add2e3d265d7fa8265baeb0ce460b9f69075730d14ece555e76a76',
    'registration': 'ca2d8656f343f5e61d124d511e6a446190b24fb010ef484ce3c8bc5fb8bb3eb2',
}
NAMES = [f'{bank}_{n}' for bank in ('intake', 'exhaust') for n in (1, 2)]


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, data):
    with Path(path).open('x') as stream:
        json.dump(data, stream, indent=2, allow_nan=False)
        stream.write('\n')


def validate_registration(data):
    frame = data.get('registration', {})
    if any(type(frame.get(k)) not in (int, float) for k in (
            'scale_scan_units_per_mm_hypothesis', 'rotation_Z_deg_hypothesis', 'translation_Z_hypothesis')):
        raise ValueError('Numeric registration required')
    if data.get('registration') != {
        'scale_scan_units_per_mm_hypothesis': 1.,
        'rotation_Z_deg_hypothesis': -90., 'translation_Z_hypothesis': 3.,
    } or data.get('module_sha256') != PINS['module']:
        raise ValueError('Exact retained registration required')
    rows = data['tools_private']
    if len(rows) != 4 or {r['name'] for r in rows} != set(NAMES):
        raise ValueError('Four distinct registered axes required')
    for row in rows:
        bank, n = row['name'].split('_')
        sign = 1 if bank == 'intake' else -1
        origin = [-22.5 if n == '1' else 22.5, 18. if sign == 1 else -23.5, 3.]
        axis = [0., sign * math.sin(math.radians(8)), math.cos(math.radians(8))]
        if (len(row['axis_direction']) != 3 or any(type(v) not in (float, int) or not math.isfinite(v)
                                                  for v in row['axis_direction'])):
            raise ValueError('Finite numeric axis required')
        if (row['axis_origin'] != origin or math.dist(row['axis_direction'], axis) > 1e-12
                or row['guide_OD'] != 11. or row['guide_axial_interval'] != [20., 55.]):
            raise ValueError('Registered axis or guide changed')
    parts = data['components_imported_from_exact_STEP']
    expected = [(f'{name}_{role}', i * 3 + j + 1) for i, name in enumerate(NAMES)
                for j, role in enumerate(('valve', 'seat', 'guide'))]
    if sorted((r['name'], r['imported_module_solid_id']) for r in parts) != sorted(expected):
        raise ValueError('Exact twelve-part module mapping required')
    return rows, parts


def run(head, module, registration, output):
    paths = dict(head=head, module=module, registration=registration)
    for role, path in paths.items():
        if path.is_symlink() or not path.is_file() or sha(path) != PINS[role]:
            raise ValueError('Exact private source required: ' + role)
    rows, parts = validate_registration(json.loads(registration.read_text()))
    if output.exists():
        raise FileExistsError(output)
    import OCP
    from OCP.BRep import BRep_Builder
    from OCP.BRepTools import BRepTools
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    from OCP.STEPControl import STEPControl_Reader
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.TopAbs import TopAbs_SOLID
    from OCP.TopExp import TopExp
    from OCP.TopTools import TopTools_IndexedMapOfShape
    from OCP.TopoDS import TopoDS_Shape
    from OCP.StlAPI import StlAPI_Writer
    from OCP.gp import gp_Trsf, gp_Ax1, gp_Pnt, gp_Dir, gp_Vec
    if OCP.__version__ != '7.9.3.1':
        raise ValueError('Retained OCP version required')
    body = TopoDS_Shape()
    if not BRepTools.Read_s(body, str(head), BRep_Builder()):
        raise ValueError('Head read failed')
    reader = STEPControl_Reader()
    if reader.ReadFile(str(module)) != IFSelect_RetDone or reader.TransferRoots() <= 0:
        raise ValueError('Module read failed')
    solids = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(reader.OneShape(), TopAbs_SOLID, solids)
    if solids.Extent() != 12:
        raise ValueError('Twelve solids required')
    transform = gp_Trsf()
    transform.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), -math.pi / 2)
    transform.SetTranslationPart(gp_Vec(0, 0, 3))
    shapes = [('head', 'head', body)] + [
        (r['name'], r['name'].rsplit('_', 1)[1],
         BRepBuilderAPI_Transform(solids.FindKey(r['imported_module_solid_id']), transform, True).Shape())
        for r in parts]
    os.umask(0o077)
    output.mkdir(parents=True, exist_ok=False)
    exports = []
    for name, role, shape in shapes:
        if not BRepCheck_Analyzer(shape, True, False, True).IsValid():
            raise ValueError('Invalid retained shape: ' + name)
        mesher = BRepMesh_IncrementalMesh(shape, .18, False, .25, False)
        if not mesher.IsDone():
            raise ValueError('Incomplete tessellation: ' + name)
        target = output / (name + '.stl')
        writer = StlAPI_Writer()
        writer.ASCIIMode = False
        if not writer.Write(shape, str(target)):
            raise ValueError('STL export failed: ' + name)
        exports.append(dict(name=name, role=role, filename=target.name, sha256=sha(target)))
        print(json.dumps(exports[-1]), flush=True)
    if any(sha(path) != PINS[role] for role, path in paths.items()):
        raise ValueError('Private source changed during export')
    write_json(output / 'inputs.json', dict(
        schema='m64-peripheral-inputs/v1', source_sha256=PINS, parts=exports,
        axes=[dict(name=r['name'], origin=r['axis_origin'], direction=r['axis_direction']) for r in rows],
        registration_hypothesis=json.loads(registration.read_text())['registration'],
        unit='uncalibrated_scan_unit_assumed_mm', source_master_modified=False,
        module_transform_applied_once=True, source_files_unchanged=True,
        OCP_version=OCP.__version__, prepare_sha256=sha(__file__),
        tessellation=dict(linear_deflection=.18, angular_deflection_radians=.25,
                          smoothing=False, decimation=False),
        assembly_complete=False, manufacturing_authorized=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('head', 'module', 'registration', 'output'):
        parser.add_argument('--' + key, required=True, type=Path)
    args = parser.parse_args()
    run(args.head, args.module, args.registration, args.output)
