#!/usr/bin/env python3
"""Private two-plane chamber demonstrator derived from the existing seat lips.

Not an OEM chamber, compression-ratio design, fluid-domain release or master edit.
"""
import argparse
import json
import math
from pathlib import Path
import time

import inspect_pilot as inspection


def roof_definition(parameters, translation_z=3.):
    p = parameters.validate()
    slope = math.tan(math.radians(p.bank_inclination_deg))
    cosine = math.cos(math.radians(p.bank_inclination_deg))
    if not 0 < slope < 1 or p.intake_x_mm >= 0 or p.exhaust_x_mm <= 0:
        raise ValueError('two_opposed_nonzero_inclined_banks_required')
    intercepts = {}
    for spec in inspection.design.valve_specs(p):
        profiles, _ = inspection.design.profiles(p, spec)
        lip = min(z for r,z in profiles['seat'])
        # The existing module is registered Rz(-90) then translated to Z3.
        value = translation_z + lip/cosine + abs(spec['center'][0])*slope
        intercepts[spec['kind']] = value
    intake, exhaust = intercepts['intake'], intercepts['exhaust']
    ridge_y = (intake-exhaust)/(2*slope)
    ridge_z = (intake+exhaust)/2
    if ridge_z <= 0:
        raise ValueError('positive_roof_required')
    return {'intake_intercept': intake, 'exhaust_intercept': exhaust,
            'slope_magnitude': slope, 'ridge_y': ridge_y, 'ridge_z': ridge_z,
            'exhaust_zero_y': -exhaust/slope, 'intake_zero_y': intake/slope,
            'bounding_cylinder_radius': p.bore_mm/2,
            'definition': 'z_roof=min(intake_intercept-slope*y,exhaust_intercept+slope*y); positive portion only'}


def run(args):
    from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Cut
    from OCP.TopTools import TopTools_ListOfShape
    from OCP.BRepTools import BRepTools
    from OCP.BOPAlgo import BOPAlgo_ArgumentAnalyzer
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Plane
    import OCP
    start = time.monotonic()
    names = ('body','module','build','registration')
    if any(inspection.digest(getattr(args,k)) != inspection.EXPECTED[k] for k in names):
        raise ValueError('exact_sources_required')
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.mkdir(parents=True, mode=0o700)
    report = {'schema':'m64-two-plane-chamber-demonstrator/v1','status':'started',
              'inputs_sha256':{k:inspection.EXPECTED[k] for k in names},
              'script_sha256':inspection.digest(__file__),
              'design_source_sha256':inspection.digest(inspection.design.__file__),
              'OCP_version':OCP.__version__,
              'units':'scan_units_under_unverified_1_unit_per_mm_hypothesis',
              'bore_diameter_design_hypothesis':100.,
              'manufacturing_authorized':False,'OEM_geometry_claimed':False,
              'compression_ratio_computed':False,'fluid_domain_qualified':False,
              'ports_cut':False,'guides_leakage_boundaries_completed':False,
              'spark_plug':{'central_axis_reserved':[0.,0.,1.],'origin_xy':[0.,0.],
                            'hole_created':False,'reference_selected':False},
              'full_body_BOP_checked':False,
              'limits':['Planar ridge has no finished blend or selected plug package.',
                        'Cylinder100 is a design bound, not an OEM sealing-interface contract.',
                        'A connected chamber tool is not the complete flowbench fluid domain.',
                        'No piston, deck clearance or compression ratio is inferred.']}
    def save():
        path=args.output/'chamber-report.json'
        path.write_text(json.dumps(report,indent=2)+'\n');path.chmod(0o600)
    def step(name):
        report['stage']=name;report['elapsed_seconds']=time.monotonic()-start;save()
        print(json.dumps({'stage':name}),flush=True)
    cad=inspection.design.CAD()
    def volume(shape):
        prop=cad.GProp_GProps()
        estimate=cad.BRepGProp.VolumeProperties_s(shape,prop,1e-9,True)
        return {'value':prop.Mass(),'relative_quadrature_estimate_not_bound':estimate}
    def operation(first,second,cut=False):
        a=TopTools_ListOfShape();a.Append(first)
        b=TopTools_ListOfShape();b.Append(second)
        op=(BRepAlgoAPI_Cut if cut else BRepAlgoAPI_Common)()
        op.SetArguments(a);op.SetTools(b);op.SetNonDestructive(True)
        op.SetRunParallel(False);op.SetFuzzyValue(0.);op.Build()
        if not op.IsDone():raise ValueError('boolean_operation_failed')
        return op.Shape()
    def bbox(shape):
        box=Bnd_Box();BRepBndLib.AddOptimal_s(shape,box,False,False)
        return list(box.Get())
    def register(shape):
        tr=cad.gp_Trsf()
        tr.SetRotation(cad.gp_Ax1(cad.gp_Pnt(0,0,0),cad.gp_Dir(0,0,1)),-math.pi/2)
        tr.SetTranslationPart(cad.gp_Vec(0,0,3))
        return cad.BRepBuilderAPI_Transform(shape,tr,True).Shape()
    try:
        step('read_exact_inputs')
        registration=json.loads(args.registration.read_text())
        if registration['registration'] != {'scale_scan_units_per_mm_hypothesis':1.,
              'rotation_Z_deg_hypothesis':-90.,'translation_Z_hypothesis':3.}:
            raise ValueError('recorded_registration_required')
        p=inspection.design.Parameters(**json.loads(args.build.read_text())['parameters']).validate()
        if p.bore_mm != 100.:raise ValueError('authorized_bore_is_100_only')
        roof=roof_definition(p);report['roof']=roof
        body=cad.read_step(args.body);module=cad.read_step(args.module)
        if not cad.valid(body):raise ValueError('input_body_invalid')
        radius=roof['bounding_cylinder_radius'];side=radius+1.
        wire=cad.BRepBuilderAPI_MakePolygon()
        for y,z in ((roof['exhaust_zero_y'],0.),(roof['intake_zero_y'],0.),
                    (roof['ridge_y'],roof['ridge_z'])):
            wire.Add(cad.gp_Pnt(-side,y,z))
        wire.Close()
        face=cad.BRepBuilderAPI_MakeFace(wire.Wire()).Face()
        prism=BRepPrimAPI_MakePrism(face,cad.gp_Vec(2*side,0,0)).Shape()
        cylinder=cad.BRepPrimAPI_MakeCylinder(cad.gp_Ax2(cad.gp_Pnt(0,0,0),
                  cad.gp_Dir(0,0,1)),radius,roof['ridge_z']+1.).Shape()
        tool=operation(prism,cylinder)
        report['chamber_tool']={'BRep_valid':cad.valid(tool),
            'solid_count':cad.indexed(tool,cad.TopAbs_SOLID).Extent(),'volume':volume(tool)}
        if not report['chamber_tool']['BRep_valid'] or report['chamber_tool']['solid_count']!=1:
            raise ValueError('chamber_tool_not_one_valid_solid')
        step('BOP_chamber_tool_only')
        checker=BOPAlgo_ArgumentAnalyzer();checker.SetShape1(tool)
        checker.SelfInterMode=True;checker.SmallEdgeMode=True;checker.RebuildFaceMode=True
        checker.ContinuityMode=True;checker.CurveOnSurfaceMode=True;checker.Perform()
        report['chamber_tool']['BOP']={'has_faulty':checker.HasFaulty(),
                                     'has_errors':checker.HasErrors(),'has_warnings':checker.HasWarnings()}
        if checker.HasFaulty() or checker.HasErrors():raise ValueError('chamber_tool_BOP_rejected')
        report['chamber_tool']['outside_bounding_cylinder_volume']=volume(operation(tool,cylinder,True))
        step('check_actual_seats_and_guides_not_amputated')
        ids={r['name']:r['imported_module_solid_id'] for r in registration['components_imported_from_exact_STEP']}
        actual=cad.indexed(module,cad.TopAbs_SOLID)
        report['insert_tool_intersections']=[]
        for name,index in ids.items():
            if not name.endswith(('_seat','_guide')):continue
            inserted=register(actual.FindKey(index))
            overlap=operation(tool,inserted)
            row={'name':name,'intersection_BRep_valid':cad.valid(overlap),'volume':volume(overlap)}
            report['insert_tool_intersections'].append(row)
            if not row['intersection_BRep_valid'] or abs(row['volume']['value'])>1e-7:
                raise ValueError('insert_amputation_or_invalid_intersection_'+name)
        step('compute_actual_added_cavity_common_with_master')
        removed=operation(body,tool)
        report['actual_removed_solid']={'BRep_valid':cad.valid(removed),
             'solid_count':cad.indexed(removed,cad.TopAbs_SOLID).Extent(),'volume':volume(removed),
             'count_means_removed_material_pieces_not_fluid_components':True}
        if not cad.valid(removed) or report['actual_removed_solid']['solid_count']<1:
            raise ValueError('actual_removed_material_invalid_or_empty')
        step('cut_private_copy_of_master')
        candidate=operation(body,tool,True)
        report['candidate']={'BRep_valid_before_export':cad.valid(candidate),
            'solid_count':cad.indexed(candidate,cad.TopAbs_SOLID).Extent(),
            'body_volume':volume(body),'volume':volume(candidate),
            'original_bbox':bbox(body),'bbox':bbox(candidate)}
        row=report['candidate'];row['bbox_max_delta']=max(abs(a-b) for a,b in zip(row['original_bbox'],row['bbox']))
        row['volume_partition_error']=row['body_volume']['value']-row['volume']['value']-report['actual_removed_solid']['volume']['value']
        if not row['BRep_valid_before_export'] or row['solid_count']!=1 or row['bbox_max_delta']>1e-6 or abs(row['volume_partition_error'])>1e-3:
            raise ValueError('candidate_integrity_or_conservation_rejected')
        step('check_existing_bottom_surface_outside_bore_unchanged')
        def bottom(shape):
            faces=cad.indexed(shape,cad.TopAbs_FACE);found=[]
            for i in range(1,faces.Extent()+1):
                face=cad.TopoDS.Face_s(faces.FindKey(i));s=BRepAdaptor_Surface(face,True)
                if s.GetType()==GeomAbs_Plane and abs(s.Plane().Axis().Direction().Z())>1-1e-12 and abs(s.Plane().Location().Z())<1e-6:
                    found.append(face)
            return cad.compound(found)
        original_bottom=bottom(body);new_bottom=bottom(candidate)
        outer=operation(original_bottom,cylinder,True)
        lost=operation(outer,new_bottom,True)
        report['bottom_outside_design_bore']={'original_area':cad.area(outer),'lost_area':cad.area(lost),
                    'functional_sealing_land_identification':False,'seal_fitment_qualified':False}
        if abs(report['bottom_outside_design_bore']['lost_area'])>1e-5:
            raise ValueError('bottom_outside_bore_changed')
        step('export_and_reimport_private_artifacts')
        report['exports']={}
        for label,shape in [('chamber-tool',tool),('added-cavity',removed),('chambered-candidate',candidate)]:
            brep=args.output/(label+'.brep');BRepTools.Write_s(shape,str(brep));brep.chmod(0o600)
            stp=args.output/(label+'.step')
            cad.write_step(stp,[{'name':label,'role':'body','shape':shape}]);stp.chmod(0o600)
            reread=cad.read_step(stp)
            row={'brep_sha256':inspection.digest(brep),'step_sha256':inspection.digest(stp),
                 'BRep_valid_after_STEP':cad.valid(reread),
                 'solid_count_after_STEP':cad.indexed(reread,cad.TopAbs_SOLID).Extent(),
                 'volume_after_STEP':volume(reread)}
            report['exports'][label]=row
            expected_count = report['actual_removed_solid']['solid_count'] if label=='added-cavity' else 1
            if not row['BRep_valid_after_STEP'] or row['solid_count_after_STEP']!=expected_count:
                raise ValueError('roundtrip_rejected_'+label)
        report['inputs_unchanged']=all(inspection.digest(getattr(args,k))==inspection.EXPECTED[k] for k in names)
        report['status']='two_plane_chamber_geometry_checks_passed_not_head_or_fluid_domain_qualification'
        step('complete')
    except Exception as exc:
        report['status']='rejected_or_incomplete';report['error']=str(exc);save();raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('body','module','build','registration','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    run(parser.parse_args())
