#!/usr/bin/env python3
"""Inspect existing native geometry for a 6 mm intake flowbench, never build it.

Diagnostic collar and receiver disks are probes only. No chamber, cap, fluid
domain or modified product is written. Coordinates and full reports stay private.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time

SOURCE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SOURCE))
import build_four_valve_distribution as design

EXPECTED = {
    'body': '92640fd2ce03b1ffedf35b47063c50d150057ff2fdbac181b640236a0b5f596f',
    'intake': '72e0a786a601b96250380d16296004de9e6746caa3888ee470b6cd218f2d0251',
    'module': 'fac380b277add2e3d265d7fa8265baeb0ce460b9f69075730d14ece555e76a76',
    'build': '7b501ab6ba49b3d8d8cbd2905e6759d38cb8ec2baa1c69f1490d9e87d62ad36e',
    'registration': 'ca2d8656f343f5e61d124d511e6a446190b24fb010ef484ce3c8bc5fb8bb3eb2',
}


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(data)
    return value.hexdigest()


def axial_probe(throat_radius, port_start, seat_top):
    if not all(math.isfinite(x) for x in (throat_radius, port_start, seat_top)):
        raise ValueError('finite_dimensions_required')
    if throat_radius <= 0 or seat_top <= port_start:
        raise ValueError('positive_nominal_overlap_required')
    return {'radius': throat_radius, 'axial_start': port_start, 'axial_end': seat_top,
            'length': seat_top - port_start,
            'cylinder_volume': math.pi * throat_radius ** 2 * (seat_top - port_start)}


def lift_translation(angle_deg, lift_mm):
    if not math.isfinite(angle_deg) or not math.isfinite(lift_mm) or lift_mm < 0:
        raise ValueError('finite_nonnegative_lift_required')
    angle = math.radians(angle_deg)
    return [-lift_mm * math.sin(angle), 0., -lift_mm * math.cos(angle)]


def run(args):
    import OCP
    from OCP.BRep import BRep_Builder
    from OCP.BRepTools import BRepTools
    from OCP.TopoDS import TopoDS_Shape, TopoDS
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Cut
    from OCP.TopTools import TopTools_ListOfShape
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Plane
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeFace
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.TopAbs import TopAbs_IN, TopAbs_OUT, TopAbs_ON
    from OCP.gp import gp_Circ
    started = time.monotonic()
    paths = {name: getattr(args, name) for name in EXPECTED}
    hashes = {name: digest(path) for name, path in paths.items()}
    if hashes != EXPECTED:
        raise ValueError('exact_source_hashes_required')
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.mkdir(parents=True, mode=0o700)
    report = {'schema': 'm64-intake-6mm-geometry-inspection/v1', 'status': 'in_progress',
              'inputs_sha256': hashes, 'source_sha256': digest(Path(__file__)),
              'design_source_sha256': digest(Path(design.__file__)), 'OCP_version': OCP.__version__,
              'lift_mm_design': 6., 'receiver_diameter_mm_design_hypothesis': 100.,
              'units': 'scan_units_under_unverified_1_unit_per_mm_hypothesis',
              'manufacturing_authorized': False, 'CFD_executed': False,
              'fluid_domain_created': False, 'chamber_created': False}
    def save():
        path = args.output/'inspection.json'
        path.write_text(json.dumps(report, indent=2) + '\n')
        path.chmod(0o600)
    save()
    cad = design.CAD()
    def common(a, b, cut=False):
        first = TopTools_ListOfShape(); first.Append(a)
        second = TopTools_ListOfShape(); second.Append(b)
        op = (BRepAlgoAPI_Cut if cut else BRepAlgoAPI_Common)()
        op.SetArguments(first); op.SetTools(second)
        op.SetNonDestructive(True); op.SetFuzzyValue(0.); op.SetRunParallel(False)
        op.Build()
        if not op.IsDone() or not cad.valid(op.Shape()):
            raise ValueError('diagnostic_boolean_failed')
        return op.Shape()
    def volume(shape):
        prop = cad.GProp_GProps()
        error = cad.BRepGProp.VolumeProperties_s(shape, prop, 1e-9, True)
        return {'volume': prop.Mass(), 'relative_quadrature_error_estimate_not_bound': error}
    def area(shape):
        prop = cad.GProp_GProps()
        error = cad.BRepGProp.SurfaceProperties_s(shape, prop, 1e-9, True)
        return {'area': prop.Mass(), 'relative_quadrature_error_estimate_not_bound': error}
    def register(shape):
        tr = cad.gp_Trsf()
        tr.SetRotation(cad.gp_Ax1(cad.gp_Pnt(0,0,0), cad.gp_Dir(0,0,1)), -math.pi/2)
        tr.SetTranslationPart(cad.gp_Vec(0,0,3))
        return cad.BRepBuilderAPI_Transform(shape, tr, True).Shape()
    def disk(radius, z):
        circle = gp_Circ(cad.gp_Ax2(cad.gp_Pnt(0,0,z), cad.gp_Dir(0,0,1)), radius)
        wire = BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(circle).Edge()).Wire()
        return BRepBuilderAPI_MakeFace(wire).Face()
    registration = json.loads(args.registration.read_text())
    if registration['registration'] != {'scale_scan_units_per_mm_hypothesis':1.,
            'rotation_Z_deg_hypothesis':-90., 'translation_Z_hypothesis':3.}:
        raise ValueError('recorded_registration_required')
    build = json.loads(args.build.read_text())
    p = design.Parameters(**build['parameters']).validate()
    module = cad.read_step(args.module); body = cad.read_step(args.body)
    bank = TopoDS_Shape()
    if not BRepTools.Read_s(bank, str(args.intake), BRep_Builder()):
        raise ValueError('native_intake_read_failed')
    for name, shape, count in [('body',body,1),('module',module,12),('intake',bank,1)]:
        if not cad.valid(shape) or cad.indexed(shape,cad.TopAbs_SOLID).Extent()!=count:
            raise ValueError('source_shape_invalid_'+name)
    actual = cad.indexed(module,cad.TopAbs_SOLID)
    identities = {row['name']:row['imported_module_solid_id'] for row in registration['components_imported_from_exact_STEP']}
    report['intake_components'] = []
    for part in design.construct(cad,p,{'intake_mm':0.,'exhaust_mm':0.}):
        if part['spec']['kind'] != 'intake':
            continue
        imported = actual.FindKey(identities[part['name']])
        difference = volume(common(imported, part['shape'], cut=True))['volume']
        reverse = volume(common(part['shape'], imported, cut=True))['volume']
        if max(abs(difference),abs(reverse)) > 1e-7:
            raise ValueError('actual_STEP_component_identity_failed')
        if part['role'] == 'valve':
            tr = cad.gp_Trsf(); tr.SetTranslation(cad.gp_Vec(*lift_translation(part['spec']['axis_angle_deg'],6.)))
            imported = cad.BRepBuilderAPI_Transform(imported,tr,True).Shape()
        placed = register(imported)
        record = {'name':part['name'], 'module_solid_index':identities[part['name']],
                  'symmetric_difference_volume_components':[difference,reverse],
                  'lift_mm':6. if part['role']=='valve' else 0.,
                  'overlap_with_raw_intake_negative':volume(common(placed,bank)),
                  'overlap_with_reference_body':volume(common(placed,body))}
        report['intake_components'].append(record); save()
    report['throat_join_probes'] = []
    for spec in design.valve_specs(p):
        if spec['kind'] != 'intake':
            continue
        prof = design.profiles(p,spec)[0]['seat']
        probe = axial_probe(min(r for r,z in prof),5.99,max(z for r,z in prof))
        collar = cad.BRepPrimAPI_MakeCylinder(cad.gp_Ax2(cad.gp_Pnt(0,0,probe['axial_start']),
                  cad.gp_Dir(0,0,1)),probe['radius'],probe['length']).Shape()
        collar = register(cad.pose(collar,spec))
        overlap = volume(common(collar,bank))
        report['throat_join_probes'].append({'name':spec['name'], 'nominal':probe,
                'overlap_with_intake':overlap, 'fraction':overlap['volume']/probe['cylinder_volume'],
                'probe_is_not_fluid_domain':True})
        save()
    faces = cad.indexed(body,cad.TopAbs_FACE); bottom = []
    for index in range(1,faces.Extent()+1):
        face = TopoDS.Face_s(faces.FindKey(index)); surface = BRepAdaptor_Surface(face,True)
        if surface.GetType() != GeomAbs_Plane:
            continue
        plane = surface.Plane()
        if abs(plane.Axis().Direction().Z()) > 1-1e-12 and abs(plane.Location().Z()) < 1e-6:
            bottom.append(face)
    receiver_disk = disk(50.,0.)
    bottom_shape = cad.compound(bottom)
    covered = area(common(receiver_disk,bottom_shape))
    open_area = area(common(receiver_disk,bottom_shape,cut=True))
    report['existing_flat_bottom_at_z0'] = {'face_count':len(bottom), 'area':area(bottom_shape),
            'receiver_disk_area':math.pi*50**2, 'covered_disk':covered, 'uncovered_disk':open_area,
            'meaning':'existing_reconstruction_cap_not_OEM_combustion_roof; no_new_chamber',
            'area_partition_error':covered['area']+open_area['area']-math.pi*50**2}
    classifier = BRepClass3d_SolidClassifier(body)
    report['private_centerline_body_states'] = []
    for z in (-.1,.001,1.,3.,6.,10.):
        classifier.Perform(cad.gp_Pnt(0,0,z),1e-7)
        state = {TopAbs_IN:'IN',TopAbs_OUT:'OUT',TopAbs_ON:'ON'}.get(classifier.State(),'UNKNOWN')
        report['private_centerline_body_states'].append({'point':[0.,0.,z],'state':state})
    report['input_files_unchanged'] = {name:digest(path)==hashes[name] for name,path in paths.items()}
    report['elapsed_seconds'] = time.monotonic()-started
    report['status'] = 'geometry_inspection_completed_not_flow_domain_qualification'
    save()
    print(json.dumps({'status':report['status'],'elapsed_seconds':report['elapsed_seconds']}),flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in EXPECTED:
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args())
