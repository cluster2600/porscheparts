"""Keep the native head core and build the analytic counterpart of PicoGK fins."""
import argparse
import importlib.util
import json
import math
from pathlib import Path

import numpy as np
HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('native_head_export_helper', HERE.parent/'picogk/export_master.py')
mesh = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mesh)


def vertices(edge, sign, z, contract):
    scale = (contract['tip_abs_x']-contract['root_abs_x'])/contract['profile_radial_length']
    def point(p):
        return np.array([sign*(contract['root_abs_x']+p[1]*scale), -contract['depth']/2, z+p[0]])
    a, b = point(edge['a']), point(edge['b'])
    normal = np.cross([0.,1,0], b-a); normal /= np.linalg.norm(normal)
    return [a-normal*edge['t0_mm']/2, b-normal*edge['t1_mm']/2,
            b+normal*edge['t1_mm']/2, a+normal*edge['t0_mm']/2]


def material_balance(before, added, removed, after):
    if any(not math.isfinite(v) or v < 0 for v in (before, added, removed, after)) or before == 0 or after == 0:
        raise ValueError('Finite nonnegative volumes and positive bodies required')
    difference = math.fsum((before, added, -removed, -after))
    return difference, abs(difference)/math.fsum((before, added, removed, after))


def run(head, inputs, picogk, output):
    if output.exists():
        raise FileExistsError(output)
    contract_path, profile_path = HERE/'contract.json', HERE.parent/'bionic-fins/candidate.json'
    c = json.loads(contract_path.read_text()); profile = json.loads(profile_path.read_text())
    pins = {head: c['head_brep_sha256'], inputs/'inputs.json': c['input_manifest_sha256'],
            profile_path: c['profile_sha256'], picogk/'integration.json': mesh.sha256(picogk/'integration.json')}
    manifest = json.loads((inputs/'inputs.json').read_text())
    pins.update({inputs/r['filename']: r['sha256'] for r in manifest['parts']})
    for path, expected in pins.items():
        if path.is_symlink() or mesh.sha256(path) != expected:
            raise ValueError('Retained input hash mismatch')
    producer = json.loads((picogk/'integration.json').read_text())
    if producer['profile_sha256'] != c['profile_sha256'] or producer['contract_sha256'] != mesh.sha256(contract_path):
        raise ValueError('Different PicoGK profile or placement')
    import OCP
    from OCP.BRep import BRep_Builder
    from OCP.BRepTools import BRepTools
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse, BRepAlgoAPI_Common
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakePrism
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from OCP.TopExp import TopExp
    from OCP.TopAbs import TopAbs_SOLID, TopAbs_SHELL
    from OCP.TopTools import TopTools_IndexedMapOfShape, TopTools_ListOfShape
    from OCP.TopoDS import TopoDS_Shape
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.StlAPI import StlAPI_Writer
    from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.gp import gp_Pnt, gp_Vec
    if OCP.__version__ != '7.9.3.1':
        raise ValueError('Retained OCP version required')

    def count(shape, kind):
        table = TopTools_IndexedMapOfShape(); TopExp.MapShapes_s(shape, kind, table)
        return table.Extent()
    def volume(shape):
        properties = GProp_GProps(); BRepGProp.VolumeProperties_s(shape, properties, 1e-10, False, False)
        return float(properties.Mass())
    def operation(kind, a, b):
        arguments, tools = TopTools_ListOfShape(), TopTools_ListOfShape()
        arguments.Append(a); tools.Append(b)
        op = kind(); op.SetArguments(arguments); op.SetTools(tools); op.SetNonDestructive(True); op.Build()
        if not op.IsDone() or op.Shape().IsNull():
            raise ValueError('Native boolean failed')
        return op.Shape()
    def valid_body(shape):
        if not BRepCheck_Analyzer(shape, True, False, True).IsValid() or count(shape, TopAbs_SOLID) != 1 or count(shape, TopAbs_SHELL) != 1:
            raise ValueError('One native valid solid and shell required')

    body = TopoDS_Shape()
    if not BRepTools.Read_s(body, str(head), BRep_Builder()):
        raise ValueError('Native head read failed')
    valid_body(body)
    boxes = [BRepPrimAPI_MakeBox(gp_Pnt(*z['min']), gp_Pnt(*z['max'])).Shape() for z in c['modified_zones']]
    mask = operation(BRepAlgoAPI_Fuse, *boxes)
    retained = operation(BRepAlgoAPI_Cut, body, mask)
    valid_body(retained)
    print('Native core cut completed; reference file unchanged', flush=True)
    fins, contacts = None, []
    for sign in (-1, 1):
        for z in c['root_z']:
            leaf = None
            for e in profile['edges']:
                wire = BRepBuilderAPI_MakePolygon()
                for p in vertices(e, sign, z, c): wire.Add(gp_Pnt(*p))
                wire.Close()
                prism = BRepPrimAPI_MakePrism(BRepBuilderAPI_MakeFace(wire.Wire()).Face(), gp_Vec(0, c['depth'], 0)).Shape()
                leaf = prism if leaf is None else operation(BRepAlgoAPI_Fuse, leaf, prism)
            valid_body(leaf)
            contact = volume(operation(BRepAlgoAPI_Common, leaf, retained))
            if not math.isfinite(contact) or contact <= 0:
                raise ValueError('Native root is not attached')
            contacts.append(dict(side=sign, root_z=z, native_root_overlap_before_mask_clip=contact,
                                 physical_contact_or_load_capacity_verified=False))
            leaf = operation(BRepAlgoAPI_Common, leaf, mask)
            fins = leaf if fins is None else operation(BRepAlgoAPI_Fuse, fins, leaf)
    candidate = operation(BRepAlgoAPI_Fuse, retained, fins)
    valid_body(candidate)
    print('Six analytic PicoGK-profile fins fused into one native solid', flush=True)
    added = operation(BRepAlgoAPI_Cut, candidate, body)
    removed = operation(BRepAlgoAPI_Cut, body, candidate)
    outside = [operation(BRepAlgoAPI_Cut, shape, mask) for shape in (added, removed)]
    if any(count(s, TopAbs_SOLID) or abs(volume(s)) > 1e-8 for s in outside):
        raise ValueError('Native body changed outside the exact mask')
    difference, balance_relative = material_balance(volume(body), volume(added), volume(removed), volume(candidate))
    print(json.dumps(dict(native_material_balance=difference, relative_balance=balance_relative)), flush=True)
    # Use the requested relative quadrature accuracy, not an absolute unit-dependent threshold.
    if balance_relative > 1e-10:
        raise ValueError('Native material balance failed')
    voxel_fin = next(r for r in producer['files'] if r['filename'] == 'fins.stl')
    if abs(volume(fins)/voxel_fin['native_volume_scan_units_cubed']-1) > .02:
        raise ValueError('Analytic fin volume disagrees with PicoGK')
    output.mkdir(parents=True, mode=0o700)
    native_path = output/'head-bionic.brep'
    if not BRepTools.Write_s(candidate, str(native_path)):
        raise ValueError('Native BRep save failed')
    saved = TopoDS_Shape()
    if not BRepTools.Read_s(saved, str(native_path), BRep_Builder()):
        raise ValueError('Native BRep readback failed')
    valid_body(saved)
    writer = STEPControl_Writer()
    if writer.Transfer(saved, STEPControl_AsIs) != IFSelect_RetDone or writer.Write(str(output/'head-bionic.step')) != IFSelect_RetDone:
        raise ValueError('STEP export failed')
    files = []
    for name, shape in (('baseline', body), ('head-bionic', saved), ('fins', fins), ('added', added), ('removed', removed)):
        mesher = BRepMesh_IncrementalMesh(shape, .18, False, .25, False)
        if not mesher.IsDone(): raise ValueError('Native tessellation failed')
        path = output/(name+'.stl'); exporter = StlAPI_Writer(); exporter.ASCIIMode = False
        if not exporter.Write(shape, str(path)): raise ValueError('Native STL export failed')
        files.append(dict(filename=path.name, sha256=mesh.sha256(path), native_volume_scan_units_cubed=volume(shape)))
    if any(mesh.sha256(p) != value for p, value in pins.items()):
        raise ValueError('Source changed during native integration')
    report = dict(schema='m64-bionic-head-integration/v1', representation='native_cad_with_analytic_picogk_profile_counterpart',
                  status='native_geometry_candidate_not_qualified', voxel_scan_units=None, units=c['units'],
                  contract_sha256=mesh.sha256(contract_path), profile_sha256=c['profile_sha256'],
                  head_stl_sha256=c['head_stl_sha256'], input_manifest_sha256=c['input_manifest_sha256'],
                  source_brep_sha256=c['head_brep_sha256'], builder_sha256=mesh.sha256(Path(__file__)),
                  picogk_producer_sha256=pins[picogk/'integration.json'], OCP_version=OCP.__version__,
                  files=files, attachments=contacts, reference_parts=manifest['parts'], fin_count=6,
                  native_solid_count=1, native_shell_count=1, native_validity_and_readback_passed=True,
                  native_outside_mask_solid_counts=[count(s,TopAbs_SOLID) for s in outside],
                  native_material_balance_scan_units_cubed=difference,
                  native_material_balance_relative=balance_relative, native_volume_quadrature_relative_accuracy=1e-10,
                  analytic_to_picogk_fin_relative_volume_error=abs(volume(fins)/voxel_fin['native_volume_scan_units_cubed']-1),
                  brep_sha256=mesh.sha256(native_path), step_sha256=mesh.sha256(output/'head-bionic.step'),
                  tessellation=dict(linear_deflection=.18, angular_deflection_radians=.25),
                  core_preservation_is_at_voxel_resolution_only=False, source_master_modified=False,
                  full_functional_assembly=False, physical_root_attachment_verified=False,
                  measured_interfaces_verified=False, thermal_gain_transferred_from_coupon=False,
                  thermal_simulation=False, structural_simulation=False, manufacturing_authorized=False)
    (output/'integration.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('head', 'inputs', 'picogk', 'output'):
        parser.add_argument('--'+key, type=Path, required=True)
    args = parser.parse_args(); run(args.head, args.inputs, args.picogk, args.output)
