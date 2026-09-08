#!/usr/bin/env python3
"""Native seat contacts and real stem-guide leakage passages for a flowbench.

Imports the exact V2 components. Exports private diagnostic passage/fixture
faces, never plugs or modifies the head. A native contact is not a leak test.
"""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import resource
import sys
import time

import inspect_pilot as inspection
import build_local_port_junction_fillet as local
import audit_local_port_junction_fillet as native_audit


def annular_section(stem_diameter, diametral_clearance, length):
    if not all(math.isfinite(x) and x > 0 for x in (stem_diameter,diametral_clearance,length)):
        raise ValueError('Positive finite stem, diametral clearance and length required')
    inner = stem_diameter/2
    outer = (stem_diameter+diametral_clearance)/2
    area = math.pi*(outer-inner)*(outer+inner)
    return {'stem_radius':inner,'bore_radius':outer,'radial_gap':diametral_clearance/2,
            'area':area,'length':length,'volume':area*length,
            'zero_leakage_cannot_be_inferred_from_positive_gap':True}


def contact_area(parameters, spec):
    _, (inner,outer) = inspection.design.profiles(parameters,spec)
    return math.pi*(outer*outer-inner*inner)/math.cos(math.radians(parameters.seat_angle_from_transverse_plane_deg))


def registered(cad, shape, spec=None, lift=0.):
    tr = cad.gp_Trsf()
    tr.SetRotation(cad.gp_Ax1(cad.gp_Pnt(0,0,0),cad.gp_Dir(0,0,1)),-math.pi/2)
    shift = (0.,0.,3.)
    if lift:
        if spec is None:
            raise ValueError('Valve spec required for axial lift')
        local_shift = inspection.lift_translation(spec['axis_angle_deg'],lift)
        shift = (local_shift[1],-local_shift[0],3.+local_shift[2])
    tr.SetTranslationPart(cad.gp_Vec(*shift))
    return cad.BRepBuilderAPI_Transform(shape,tr,True).Shape()


def annular_face(cad, inner, outer, z):
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeFace
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    from OCP.gp import gp_Circ
    def disc(radius):
        circle = gp_Circ(cad.gp_Ax2(cad.gp_Pnt(0,0,z),cad.gp_Dir(0,0,1)),radius)
        return BRepBuilderAPI_MakeFace(BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(circle).Edge()).Wire()).Face()
    if not 0 < inner < outer:
        raise ValueError('Nonempty annular face required')
    return native_audit.boolean(BRepAlgoAPI_Cut,disc(outer),disc(inner))


def native_contact(cad, valve, seat):
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
    from OCP.BRepTools import BRepTools
    from OCP.GeomAbs import GeomAbs_Cone
    cones = []
    for shape in (valve,seat):
        faces = cad.indexed(shape,cad.TopAbs_FACE)
        cones.append([cad.TopoDS.Face_s(faces.FindKey(i)) for i in range(1,faces.Extent()+1)
                      if BRepAdaptor_Surface(cad.TopoDS.Face_s(faces.FindKey(i)),False).GetType()==GeomAbs_Cone])
    contacts, rows = [], []
    for first in cones[0]:
        for second in cones[1]:
            common = native_audit.boolean(BRepAlgoAPI_Common,first,second)
            faces = cad.indexed(common,cad.TopAbs_FACE)
            for i in range(1,faces.Extent()+1):
                face = cad.TopoDS.Face_s(faces.FindKey(i))
                surface = BRepAdaptor_Surface(face,False)
                uv = BRepTools.UVBounds_s(face)
                contacts.append(face)
                rows.append({'area_scan_units_squared':cad.area(face),'BRep_valid':cad.valid(face),
                             'carrier_is_cone':surface.GetType()==GeomAbs_Cone,
                             'angular_parameter_span_radians':uv[1]-uv[0]})
    return {'contact_faces':rows,'total_contact_area_scan_units_squared':sum(row['area_scan_units_squared'] for row in rows),
            'minimum_component_distance':cad.distance(valve,seat),
            'method':'native conical-face intersections; whole-solid Common alone discards touching faces',
            'pressure_sealing_or_contact_mechanics_tested':False}, cad.compound(contacts)


def boundary_row_pass(row, kind):
    contact, gap = row['contact'], row['stem_guide']
    return (contact['expected_state_area_matches'] and
            (kind!='exhaust' or contact['full_angular_band_native']) and
            gap['native_passage_BRep_valid'] and gap['native_passage_solids']==1 and
            gap['volume_matches_analytic'] and
            abs(gap['native_passage_guide_overlap_volume']['value'])<=1e-7 and
            all(gap[label+'_area_matches_gap'] and gap[label+'_annular_face']['BRep_valid']
                for label in ('lower','upper')))


def run(args):
    import OCP
    from OCP.BRepTools import BRepTools
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut, BRepAlgoAPI_Common
    started = time.monotonic()
    if args.output.exists() or args.output.is_symlink():
        raise FileExistsError(args.output)
    paths = {'module':args.module,'build':args.build,'registration':args.registration,
             'intake':args.intake,'chamber_report':args.chamber_dir/'chamber-report.json',
             'chamber_body':args.chamber_dir/'chambered-candidate.brep',
             'chamber_tool':args.chamber_dir/'chamber-tool.brep',
             'source':Path(__file__),'design_source':Path(inspection.design.__file__),
             'inspection_source':Path(inspection.__file__), 'local_source':Path(local.__file__),
             'boolean_source':Path(native_audit.__file__)}
    hashes = {k:inspection.digest(p) for k,p in paths.items()}
    if any(hashes[k]!=inspection.EXPECTED[k] for k in ('module','build','registration','intake')):
        raise ValueError('Exact V2/module registration/intake required')
    chamber = json.loads(paths['chamber_report'].read_text())
    if (hashes['chamber_body']!=chamber['exports']['chambered-candidate']['brep_sha256'] or
            hashes['chamber_tool']!=chamber['exports']['chamber-tool']['brep_sha256'] or
            not chamber['inputs_unchanged'] or chamber['inputs_sha256']['module']!=hashes['module']):
        raise ValueError('Exact chamber provenance required')
    registration = json.loads(args.registration.read_text())
    if registration['registration'] != {'scale_scan_units_per_mm_hypothesis':1.,'rotation_Z_deg_hypothesis':-90.,'translation_Z_hypothesis':3.}:
        raise ValueError('Only exact recorded single registration supported')
    p = inspection.design.Parameters(**json.loads(args.build.read_text())['parameters']).validate()
    args.output.mkdir(parents=True,mode=0o700)
    report = {'schema':'m64-intake-gas-boundary-audit/v1','created_at_utc':datetime.now(timezone.utc).isoformat(),
        'status':'running','inputs_sha256':hashes,'OCP_version':OCP.__version__,
        'units':'scan_units_under_unverified_1_unit_per_mm_hypothesis',
        'valve_state':{'intake_lift_design':6.,'exhaust_lift_design':0.},
        'native_component_registration_count':1,'head_registration_reapplied':False,
        'numeric_area_comparison_tolerance_scan_units_squared':1e-7,
        'numeric_volume_comparison_tolerance_scan_units_cubed':1e-7,
        'physical_clearances_and_seals_qualified':False,'complete_gas_domain_built':False,
        'manufacturing_authorized':False,'CFD_executed':False,'master_modified':False,
        'rows':[]}
    def save(name):
        report['elapsed_seconds']=time.monotonic()-started
        local.ports.save(args.output/(name+'.json'),report)
    def volume(shape):
        prop=cad.GProp_GProps();error=cad.BRepGProp.VolumeProperties_s(shape,prop,1e-10,True)
        return {'value':prop.Mass(),'relative_quadrature_error_estimate_not_bound':error}
    def export(name,shape,role):
        path=args.output/(name+'.brep');BRepTools.Write_s(shape,str(path));path.chmod(0o600)
        return {'path_private':str(path),'sha256':inspection.digest(path),'role':role,
                'area_scan_units_squared':cad.area(shape),'BRep_valid':cad.valid(shape)}
    save('preregistration')
    cad=inspection.design.CAD()
    try:
        module=cad.read_step(args.module);actual=cad.indexed(module,cad.TopAbs_SOLID)
        ids={row['name']:row['imported_module_solid_id'] for row in registration['components_imported_from_exact_STEP']}
        specs=inspection.design.valve_specs(p)
        expected={spec['name']+'_'+role for spec in specs for role in ('valve','seat','guide')}
        if set(ids)!=expected or len(set(ids.values()))!=12 or actual.Extent()!=12:
            raise ValueError('Exact complete 12-component manifest required')
        intake=local.read_native(args.intake)
        # Body and tool are read to confirm native validity, not re-registered.
        body=local.read_native(paths['chamber_body']);tool=local.read_native(paths['chamber_tool'])
        if not all(cad.valid(s) for s in (module,intake,body,tool)):
            raise ValueError('Native input invalid')
        for spec in specs:
            name=spec['name'];lift=6. if spec['kind']=='intake' else 0.
            parts={role:registered(cad,actual.FindKey(ids[name+'_'+role]),spec,lift if role=='valve' else 0.)
                   for role in ('valve','seat','guide')}
            row={'name':name,'component_ids_bound_to_exact_module':{role:ids[name+'_'+role] for role in parts},
                 'lift':lift,'contact':{},'stem_guide':{}}
            contact,contact_shape=native_contact(cad,parts['valve'],parts['seat'])
            expected_area=contact_area(p,spec) if spec['kind']=='exhaust' else 0.
            contact['expected_contact_area_scan_units_squared']=expected_area
            contact['expected_state_area_matches']=abs(contact['total_contact_area_scan_units_squared']-expected_area)<=1e-7
            if spec['kind']=='exhaust':
                contact['full_angular_band_native']=len(contact['contact_faces'])==1 and all(
                    r['BRep_valid'] and r['carrier_is_cone'] and abs(r['angular_parameter_span_radians']-2*math.pi)<=1e-9
                    for r in contact['contact_faces'])
                contact['native_contact_surface']=export(name+'-closed-seat-contact',contact_shape,'wall_exhaust_valve_seat_contact_NOT_open_boundary')
            else:
                contact['open_intake_has_no_seat_contact']=not contact['contact_faces']
            row['contact']=contact
            gap=annular_section(p.stem_diameter_mm,spec['guide_diametral_clearance_mm'],p.guide_length_mm)
            z=p.guide_start_above_gauge_mm
            bore=cad.BRepPrimAPI_MakeCylinder(cad.gp_Ax2(cad.gp_Pnt(0,0,z),cad.gp_Dir(0,0,1)),gap['bore_radius'],p.guide_length_mm).Shape()
            bore=registered(cad,cad.pose(bore,spec))
            passage=native_audit.boolean(BRepAlgoAPI_Cut,bore,parts['valve'])
            overlaps_guide=native_audit.boolean(BRepAlgoAPI_Common,passage,parts['guide'])
            actual_volume=volume(passage)
            row['stem_guide']={'analytic':gap,'native_passage_volume':actual_volume,
                'native_passage_BRep_valid':cad.valid(passage),'native_passage_solids':cad.indexed(passage,cad.TopAbs_SOLID).Extent(),
                'native_passage_guide_overlap_volume':volume(overlaps_guide),
                'volume_matches_analytic':abs(actual_volume['value']-gap['volume'])<=1e-7,
                'passage':export(name+'-stem-guide-gas',passage,'real_stem_guide_clearance_gas_NOT_solid_plug'),
                'raw_intake_overlap_volume':volume(native_audit.boolean(BRepAlgoAPI_Common,passage,intake)),
                'full_domain_connectivity_not_established_by_overlap_alone':True}
            lower=annular_face(cad,gap['stem_radius'],gap['bore_radius'],z)
            upper=annular_face(cad,gap['stem_radius'],gap['bore_radius'],z+p.guide_length_mm)
            for label,face,role in (('lower',lower,'guide_clearance_connection_NOT_a_wall'),
                                    ('upper',upper,'fixture_stem_seals_idealized_bench_boundary_NOT_actual_seal_CAD')):
                face=registered(cad,cad.pose(face,spec))
                row['stem_guide'][label+'_annular_face']=export(name+'-'+label+'-annular-face',face,role)
                row['stem_guide'][label+'_area_matches_gap']=abs(cad.area(face)-gap['area'])<=1e-7
            row['stem_guide']['fixture_policy']='Only the upper annular end is an ideal sealed bench boundary; never cap the lower entrance or fill the guide bore with metal.'
            report['rows'].append(row);save(name+'-checkpoint')
            if not boundary_row_pass(row,spec['kind']):
                raise ValueError('Native contact or annular passage diagnostic failed for '+name)
        report['required_boundary_semantics']={
            'inlet':'one actual upstream intake-bank opening, identified against its native face',
            'outlet':'receiver end only; two valve throats are INTERNAL, never pressure outlets',
            'exhaust':'closed conical valve-seat contact; no fictitious exhaust throat outlet or solid-filled port',
            'stem_seals':'explicit upper annular ideal bench seals; micron-scale radial gap remains in full native gas model',
            'insert_OD_joints':'seats/guides seated to head are ideal no-bypass interfaces for this pilot; press fits/leakage/contact mechanics not qualified',
            'spark_plug':'no spark-plug hole exists in candidate; do not invent a plug leak or sealed plug CAD',
            'receiver_to_head':'ideal fixture joint at declared working-bore plane, not a certified Porsche sealing land',
            'all_remaining_faces':'must match physical wall or explicit fixture; otherwise boundary assignment fails',
            'disconnected_exhaust_guide_pockets':'must be classified from actual fluid connectivity before inclusion/exclusion; not silently filled'}
        report['readiness_for_builder']='contact_and_clearance_geometry_checked_complete_boundary_assignment_still_required'
        report['status']='native_boundary_primitives_audited_not_complete_flow_domain_or_physical_sealing_validation'
    except Exception as exc:
        report['status']='stopped_partial';report['error']=type(exc).__name__+': '+str(exc)
    report['inputs_unchanged']=all(inspection.digest(p)==hashes[k] for k,p in paths.items())
    if not report['inputs_unchanged']:report['status']='rejected_provenance_changed'
    report['process_peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024)
    report['serial_native_booleans']=True
    save('boundary-audit-report')
    print(json.dumps({'status':report['status'],'rows':len(report['rows']),'elapsed_seconds':report['elapsed_seconds'],
                      'output':str(args.output),'error':report.get('error')}))
    return 0 if report['status'].startswith('native_boundary_primitives_audited') else 3


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('module','build','registration','intake','chamber-dir','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    resource.setrlimit(resource.RLIMIT_CPU,(300,305))
    resource.setrlimit(resource.RLIMIT_DATA,(4*1024**3,4*1024**3))
    raise SystemExit(run(parser.parse_args()))
