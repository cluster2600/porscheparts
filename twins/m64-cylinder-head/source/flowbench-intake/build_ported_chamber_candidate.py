#!/usr/bin/env python3
"""One private native intake cut into the existing chambered body.

No receiver, guide-fixture extension, master overwrite, repair or scaling.
Opening masks are diagnostics, never proof that every old void is legitimate.
Wall rays traverse the newly cut solid, not distances to the old body.
"""
import argparse
import json
import math
from pathlib import Path
import shutil
import time

import inspect_pilot as inspection
import audit_port_skin_openings as skin
import build_scan_seeded_ports as ports

EXPECTED={
    'body':'ba5701be9381c686d6840cc8a0630f38be1ef56fd278d8d9cb0bbcccab3e9e67',
    **{k:inspection.EXPECTED[k] for k in ('module','build','registration','intake')},
    'chamber':'8643968ccf678fde1a4ba68ff7866fc468ec8faadbf79a53cc055e50c0010dc8',
    'chamber_report':'cc7d10e2b34cf3c2f786b0fbf6452f52d1a8f23f7ab59c1c711ec1fb58e36830',
    'intake_report':'53beca98c5d152f2cb59d530934fc3fe8481fb7b4e49f541b97ed200ad430e8c'}


def wall_summary(rows, limit=1.5):
    if not math.isfinite(limit) or limit<=0:raise ValueError('positive_screening_limit_required')
    resolved=[r['material_segment_length'] for r in rows if r.get('status')=='resolved']
    if any(not math.isfinite(v) or v<=0 for v in resolved):raise ValueError('invalid_material_segment')
    return {'samples':len(rows),'resolved':len(resolved),'unresolved':len(rows)-len(resolved),
            'minimum_resolved_material_segment':min(resolved,default=None),
            'resolved_below_screening_limit':sum(v<limit for v in resolved),
            'screening_limit_scan_units':limit,'global_minimum_verified':False,
            'sampling_is_not_surface_area_fraction_or_manufacturing_qualification':True}


def candidate_screen(valid, solids, unexpected_area, contact_losses, wall):
    if not valid or solids!=1:return 'rejected_native_integrity'
    if unexpected_area is None:return 'pending_boundary_contact_audit'
    if not math.isfinite(unexpected_area) or abs(unexpected_area)>1e-4:return 'rejected_unexpected_boundary_contacts'
    if any(math.isfinite(v) and v < -1e-5 for v in contact_losses):return 'rejected_nonconservative_housing_contact_increase'
    if any(not math.isfinite(v) or v>1e-5 for v in contact_losses):return 'rejected_housing_contact_loss_requires_design_review'
    if wall.get('resolved_below_screening_limit',0):return 'rejected_sampled_thin_material_requires_design_review'
    return 'candidate_only_global_skin_wall_and_engine_qualification_incomplete'


def inspect_retained_guides(report_path, module_path, registration_path, output):
    """Read a persisted candidate; no further body cut or geometry repair."""
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Cylinder
    from OCP.BRepCheck import BRepCheck_Analyzer
    started=time.monotonic()
    report_path=Path(report_path);module_path=Path(module_path);registration_path=Path(registration_path);output=Path(output)
    prior=json.loads(report_path.read_text());record=prior['exports']['candidate_native']
    candidate_path=report_path.parent/record['file']
    if (inspection.digest(candidate_path)!=record['sha256'] or inspection.digest(module_path)!=EXPECTED['module']
            or inspection.digest(registration_path)!=EXPECTED['registration']):raise ValueError('persisted_candidate_provenance_mismatch')
    if output.exists():raise FileExistsError(output)
    output.mkdir(parents=True,mode=0o700)
    cad=inspection.design.CAD();candidate=skin.native_read(candidate_path);module=cad.read_step(module_path)
    if not BRepCheck_Analyzer(candidate,True,False,True).IsValid():raise ValueError('persisted_native_candidate_invalid')
    registration=json.loads(registration_path.read_text());actual=cad.indexed(module,cad.TopAbs_SOLID)
    ids={r['name']:r['imported_module_solid_id'] for r in registration['components_imported_from_exact_STEP']}
    result={'schema':'m64-ported-chamber-guide-retention-read-only/v1','source_sha256':inspection.digest(__file__),
        'candidate_sha256':record['sha256'],'prior_report_sha256':inspection.digest(report_path),
        'body_cut_repeated':False,'geometry_modified':False,'manufacturing_authorized':False,
        'units':prior['units'],'guides':[],'full_body_BOP_checked':False}
    for tool in registration['tools_private']:
        if not tool['name'].startswith('intake_'):continue
        tr=cad.gp_Trsf();tr.SetRotation(cad.gp_Ax1(cad.gp_Pnt(0,0,0),cad.gp_Dir(0,0,1)),-math.pi/2)
        tr.SetTranslationPart(cad.gp_Vec(0,0,3));name=tool['name']+'_guide'
        insert=cad.BRepBuilderAPI_Transform(actual.FindKey(ids[name]),tr,True).Shape();radius=tool['guide_OD']/2
        lateral=[face for face in skin.indexed_faces(cad,insert) if BRepAdaptor_Surface(face,True).GetType()==GeomAbs_Cylinder
                 and abs(BRepAdaptor_Surface(face,True).Cylinder().Radius()-radius)<1e-7]
        if len(lateral)!=1:raise ValueError('one_nominal_OD_face_required')
        patch,_=skin.boolean(cad,lateral[0],candidate,'common');path=output/(name+'-retained-OD-contact.brep');skin.native_write(path,patch)
        rows=[];axis=tool['axis_direction'];origin=tool['axis_origin']
        for face in skin.indexed_faces(cad,patch):
            surface=BRepAdaptor_Surface(face,True)
            if surface.GetType()!=GeomAbs_Cylinder:raise ValueError('nominal_OD_patch_not_cylindrical')
            ends=[]
            for v in (surface.FirstVParameter(),surface.LastVParameter()):
                point=surface.Value(surface.FirstUParameter(),v)
                ends.append(sum(a*(x-o) for a,x,o in zip(axis,[point.X(),point.Y(),point.Z()],origin)))
            lo,hi=sorted(ends);area=cad.area(face);expected=2*math.pi*radius*(hi-lo)
            rows.append({'axial_interval':[lo,hi],'area':area,'full_circumference_area_for_interval':expected,
                'area_matches_full_circumference':abs(area-expected)<=max(1e-7,1e-7*expected),
                'angular_parameter_span':surface.LastUParameter()-surface.FirstUParameter()})
        previous=next(row for row in prior['housing_contacts'] if row['name']==name)
        total_area=sum(row['area'] for row in rows)
        if abs(total_area-previous['candidate_contact_area'])>1e-5:raise ValueError('retained_area_does_not_match_prior_run')
        complete=len(rows)==1 and rows[0]['area_matches_full_circumference'] and abs(rows[0]['angular_parameter_span']-2*math.pi)<1e-7
        result['guides'].append({'name':name,'contact_BRep_sha256':inspection.digest(path),'native_patches':rows,
            'nominal_insert_axial_interval':tool['guide_axial_interval'],'retained_contact_area':total_area,
            'one_complete_cylindrical_retained_interval':complete,
            'retained_contact_length':rows[0]['axial_interval'][1]-rows[0]['axial_interval'][0] if complete else None,
            'support_pressure_temperature_and_required_retention_length_qualified':False})
    sampled={r['source_new_wall_face_id'] for r in prior['wall_ray_samples_private']}
    result['ray_coverage_clarification']={'sampled_faces':len(sampled),
        'new_wall_faces':len(prior['new_cavity_wall_face_ids_private']),
        'unsampled_face_ids_private':sorted(set(prior['new_cavity_wall_face_ids_private'])-sampled),
        'global_minimum_verified':False,'unresolved_ray_count_excludes_faces_without_valid_sample_point':True}
    result['input_hashes_unchanged']=(inspection.digest(candidate_path)==record['sha256']
        and inspection.digest(report_path)==result['prior_report_sha256']
        and inspection.digest(module_path)==EXPECTED['module']
        and inspection.digest(registration_path)==EXPECTED['registration'])
    result['elapsed_seconds']=time.monotonic()-started
    target=output/'guide-retention-report.json';target.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');target.chmod(0o600)
    return result


def verify_saved_material_rays(report_path, target):
    """Re-read same solid and prove saved lengths end at the FIRST boundary."""
    from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.TopAbs import TopAbs_IN, TopAbs_OUT
    from OCP.gp import gp_Lin
    started=time.monotonic();report_path=Path(report_path);target=Path(target)
    if target.exists():raise FileExistsError(target)
    source=json.loads(report_path.read_text());record=source['exports']['candidate_native'];path=report_path.parent/record['file']
    if inspection.digest(path)!=record['sha256']:raise ValueError('saved_native_candidate_changed')
    cad=inspection.design.CAD();body=skin.native_read(path)
    intersector=IntCurvesFace_ShapeIntersector();intersector.Load(body,1e-8)
    classifier=BRepClass3d_SolidClassifier(body);rows=[]
    for saved in source['wall_ray_samples_private']:
        if saved['status']!='resolved':continue
        origin=saved['point_private'];direction=saved['direction_into_material_private']
        intersector.Perform(gp_Lin(cad.gp_Pnt(*origin),cad.gp_Dir(*direction)),0.,300.)
        hits=sorted(intersector.WParameter(i) for i in range(1,intersector.NbPnt()+1) if intersector.WParameter(i)>1e-7)
        d=hits[0] if hits else None
        def state_at(distance):
            classifier.Perform(cad.gp_Pnt(*(o+distance*v for o,v in zip(origin,direction))),1e-8)
            return classifier.State()
        passed=d is not None and abs(d-saved['material_segment_length'])<1e-7
        if d is not None:
            epsilon=min(1e-6,d/10.)
            states=[state_at(t*d)==TopAbs_IN for t in (.1,.5,.9)]
            transition=state_at(d-epsilon)==TopAbs_IN and state_at(d+epsilon)==TopAbs_OUT
            passed=passed and all(states) and transition
        rows.append({'face_id':saved['source_new_wall_face_id'],'saved_length':saved['material_segment_length'],
            'first_positive_boundary_distance':d,'matches_first_exit_with_material_interior':passed})
    result={'schema':'m64-ported-chamber-material-ray-replay/v1','source_sha256':inspection.digest(__file__),
        'candidate_sha256':record['sha256'],'prior_report_sha256':inspection.digest(report_path),
        'same_saved_origins_and_directions':True,'geometry_modified':False,'body_cut_repeated':False,
        'rows':rows,'all_saved_resolved_rays_verified':len(rows)>0 and all(r['matches_first_exit_with_material_interior'] for r in rows),
        'global_minimum_verified':False,'manufacturing_authorized':False,'elapsed_seconds':time.monotonic()-started}
    target.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');target.chmod(0o600)
    return result


def run(args):
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Cut
    from OCP.TopTools import TopTools_ListOfShape
    from OCP.BRepTools import BRepTools
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Plane, GeomAbs_Cylinder
    from OCP.BOPAlgo import BOPAlgo_ArgumentAnalyzer
    from OCP.BRepClass import BRepClass_FaceClassifier
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
    from OCP.TopAbs import TopAbs_IN, TopAbs_OUT
    from OCP.gp import gp_Lin
    import OCP
    started=time.monotonic();paths={name:getattr(args,name) for name in EXPECTED}
    if {k:inspection.digest(v) for k,v in paths.items()}!=EXPECTED:raise ValueError('exact_native_sources_required')
    if args.output.exists():raise FileExistsError(args.output)
    args.output.mkdir(parents=True,mode=0o700)
    code=args.output/'builder-source.py';shutil.copyfile(__file__,code);code.chmod(0o600)
    report={'schema':'m64-ported-chamber-candidate/v1','status':'in_progress','inputs_sha256':EXPECTED,
        'source_sha256':inspection.digest(__file__),'dependencies_sha256':{
            'inspection':inspection.digest(inspection.__file__),'skin':inspection.digest(skin.__file__),
            'routing':inspection.digest(ports.__file__),'design':inspection.digest(inspection.design.__file__)},
        'OCP_version':OCP.__version__,'units':'scan_units_under_unverified_1_unit_per_mm_hypothesis',
        'master_modified':False,'body_registration_reapplied':False,'intake_registration_reapplied':False,
        'receiver_or_stem_fixture_used_as_cutting_tool':False,'full_body_BOP_checked':False,
        'native_tolerances_modified':False,'Boolean_fuzzy_value':0.,'manufacturing_authorized':False,
        'CFD_executed':False,'thermal_or_strength_validation_performed':False,
        'opening_mask_does_not_qualify_existing_pockets':True,'global_wall_minimum_verified':False,
        'only_expected_exterior_openings_proven':False,'stages':[]}
    def save(stage):
        report['stage']=stage;report['elapsed_seconds']=time.monotonic()-started
        target=args.output/'ported-chamber-report.json'
        target.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');target.chmod(0o600)
        print(json.dumps({'stage':stage}),flush=True)
    cad=inspection.design.CAD()
    def valid(shape):return BRepCheck_Analyzer(shape,True,False,True).IsValid()
    def volume(shape):
        p=cad.GProp_GProps();error=cad.BRepGProp.VolumeProperties_s(shape,p,1e-9,True)
        return {'value':p.Mass(),'relative_quadrature_estimate_not_bound':error}
    def boolean(a,b,cut=False):
        aa=TopTools_ListOfShape();aa.Append(a);bb=TopTools_ListOfShape();bb.Append(b)
        op=(BRepAlgoAPI_Cut if cut else BRepAlgoAPI_Common)()
        op.SetArguments(aa);op.SetTools(bb);op.SetFuzzyValue(0.);op.SetRunParallel(False);op.SetNonDestructive(True);op.Build()
        if not op.IsDone():raise ValueError('native_boolean_not_done')
        return op.Shape(),op
    def write(name,shape):
        path=args.output/(name+'.brep');skin.native_write(path,shape)
        return {'file':path.name,'sha256':inspection.digest(path)}
    def registered(shape):
        tr=cad.gp_Trsf();tr.SetRotation(cad.gp_Ax1(cad.gp_Pnt(0,0,0),cad.gp_Dir(0,0,1)),-math.pi/2)
        tr.SetTranslationPart(cad.gp_Vec(0,0,3));return cad.BRepBuilderAPI_Transform(shape,tr,True).Shape()
    try:
        save('native_preflight_no_transform')
        registration=json.loads(args.registration.read_text());checkpoint=json.loads(args.intake_report.read_text())
        chamber_report=json.loads(args.chamber_report.read_text())
        p=inspection.design.Parameters(**json.loads(args.build.read_text())['parameters']).validate()
        ports.check_registered_axes(p,registration['tools_private'])
        if (checkpoint['exports']['native_BRep_sha256']!=EXPECTED['intake'] or
            chamber_report['exports']['chambered-candidate']['brep_sha256']!=EXPECTED['body']):raise ValueError('native_receipt_chain_mismatch')
        body=skin.native_read(args.body);bank=skin.native_read(args.intake);chamber=skin.native_read(args.chamber)
        if any(not valid(s) or cad.indexed(s,cad.TopAbs_SOLID).Extent()!=1 for s in (body,bank,chamber)):
            raise ValueError('one_valid_native_body_bank_and_chamber_required')
        analyzer=BOPAlgo_ArgumentAnalyzer();analyzer.SetShape1(bank)
        analyzer.SelfInterMode=True;analyzer.SmallEdgeMode=True;analyzer.RebuildFaceMode=True
        analyzer.ContinuityMode=True;analyzer.CurveOnSurfaceMode=True;analyzer.Perform()
        report['intake_BOP']={'has_faulty':analyzer.HasFaulty(),'has_errors':analyzer.HasErrors(),
            'faults':[str(r.GetCheckStatus()).split('.')[-1] for r in analyzer.GetCheckResult()]}
        if analyzer.HasFaulty() or analyzer.HasErrors():raise ValueError('native_intake_BOP_rejected')
        original_faces=skin.indexed_faces(cad,body);bank_faces=skin.indexed_faces(cad,bank)
        module=cad.read_step(args.module);actual=cad.indexed(module,cad.TopAbs_SOLID)
        ids={r['name']:r['imported_module_solid_id'] for r in registration['components_imported_from_exact_STEP']}
        report['preflight']={'body_faces':len(original_faces),'body_volume':volume(body),
            'bank_faces':len(bank_faces),'bank_volume':volume(bank),'body_BRep_valid_exact':True,
            'native_same_frame_from_source_chain':True,'module_only_registered_once':True}
        removed,_=boolean(body,bank);report['removed_material']={'BRep_valid':valid(removed),
            'solids':cad.indexed(removed,cad.TopAbs_SOLID).Extent(),'volume':volume(removed)}
        if not valid(removed) or report['removed_material']['volume']['value']<=0:raise ValueError('empty_or_invalid_material_removal')
        report['exports']={'removed_material':write('removed-intake-material',removed)}
        save('one_native_body_minus_intake_cut')
        candidate,cut=boolean(body,bank,True)
        report['candidate']={'BRep_valid_exact':valid(candidate),'solids':cad.indexed(candidate,cad.TopAbs_SOLID).Extent(),
            'volume':volume(candidate),'area':cad.area(candidate)}
        report['candidate']['bbox_max_delta']=max(abs(a-b) for a,b in zip(skin.conservative_bbox(body),skin.conservative_bbox(candidate)))
        report['candidate']['volume_partition_error']=report['preflight']['body_volume']['value']-report['candidate']['volume']['value']-report['removed_material']['volume']['value']
        report['exports']['candidate_native']=write('ported-chamber-candidate',candidate)
        save('native_candidate_exported_before_diagnostics')
        if not valid(candidate) or report['candidate']['solids']!=1:raise ValueError('candidate_native_integrity_rejected')
        reread=skin.native_read(args.output/'ported-chamber-candidate.brep')
        report['candidate']['native_roundtrip_BRep_valid_exact']=valid(reread)
        stp=args.output/'ported-chamber-candidate.step';cad.write_step(stp,[{'name':'candidate_intake_ported_chamber','role':'body','shape':candidate}]);stp.chmod(0o600)
        step_read=cad.read_step(stp)
        report['exports']['candidate_STEP']={'file':stp.name,'sha256':inspection.digest(stp)}
        report['candidate']['STEP_roundtrip_BRep_valid_exact']=valid(step_read)
        report['candidate']['STEP_roundtrip_solids']=cad.indexed(step_read,cad.TopAbs_SOLID).Extent()
        report['candidate']['STEP_roundtrip_volume']=volume(step_read)
        report['STEP_BOP_qualified']=False
        # Compare the REAL insert lateral surfaces against before and after
        # solids. Intersecting the tool with an insert alone does not measure
        # retention, nor does this nominal contact measure contact pressure.
        save('compare_actual_insert_housing_material_contacts')
        report['housing_contacts']=[];housing_masks=[]
        for tool in registration['tools_private']:
            origin,axis=tool['axis_origin'],tool['axis_direction']
            for role in ('seat','guide'):
                name=tool['name']+'_'+role;insert=registered(actual.FindKey(ids[name]));radius=tool[role+'_OD']/2
                lateral=[f for f in skin.indexed_faces(cad,insert) if BRepAdaptor_Surface(f,True).GetType()==GeomAbs_Cylinder and abs(BRepAdaptor_Surface(f,True).Cylinder().Radius()-radius)<1e-7]
                if len(lateral)!=1:raise ValueError('unique_insert_OD_surface_required')
                a,_=boolean(lateral[0],body);b,_=boolean(lateral[0],candidate)
                if not valid(a) or not valid(b):raise ValueError('invalid_contact_patch_'+name)
                aa=cad.area(a);bb=cad.area(b)
                report['housing_contacts'].append({'name':name,'reference_contact_area':aa,'candidate_contact_area':bb,
                    'lost_contact_area':aa-bb,'contact_pressure_or_hot_retention_qualified':False})
                # Bound expected hole communication by the actual original
                # cylinder face extents, not an arbitrary infinite cylinder.
                for face in original_faces:
                    s=BRepAdaptor_Surface(face,True)
                    if s.GetType()!=GeomAbs_Cylinder or abs(s.Cylinder().Radius()-radius)>1e-7:continue
                    line=s.Cylinder().Axis();q=line.Location();direction=line.Direction()
                    offset=[q.X()-origin[0],q.Y()-origin[1],q.Z()-origin[2]];axial=sum(a*b for a,b in zip(axis,offset))
                    radial=math.sqrt(sum((v-axial*a)**2 for v,a in zip(offset,axis)))
                    if radial>1e-7 or abs(abs(sum(a*b for a,b in zip(axis,[direction.X(),direction.Y(),direction.Z()])))-1)>1e-7:continue
                    ends=[]
                    for v in (s.FirstVParameter(),s.LastVParameter()):
                        point=s.Value(s.FirstUParameter(),v);ends.append(sum(a*(v-o) for a,v,o in zip(axis,[point.X(),point.Y(),point.Z()],origin)))
                    lo,hi=sorted(ends)
                    housing_masks.append(cad.BRepPrimAPI_MakeCylinder(cad.gp_Ax2(cad.gp_Pnt(*ports.add(origin,ports.mul(axis,lo))),cad.gp_Dir(*axis)),radius,hi-lo).Shape())
                save('housing_contact_'+name)
        # Retain the complete raw skin contacts, including pre-existing void
        # walls. Diagnostic masks cannot hide these records from the review.
        save('measure_all_original_skin_contacts_and_unexpected_residual')
        bank_box=skin.conservative_bbox(bank)
        possible=[(i,f) for i,f in enumerate(original_faces,1) if not skin.disjoint_boxes(skin.conservative_bbox(f),bank_box)]
        raw,history=boolean(cad.compound([f for _,f in possible]),bank)
        if not valid(raw):raise ValueError('raw_boundary_contact_BRep_invalid')
        report['boundary_contacts']={'raw':skin.surface_summary(cad,raw),
            'history_private':skin.raw_face_history(cad,history,raw,possible),
            'raw_scope':'all_old_boundary_faces_including_internal_voids_not_only_exterior'}
        report['exports']['raw_boundary_contacts']=write('all-raw-boundary-contacts',raw)
        mouth=skin.mouth_authorization(cad,ports.native(),checkpoint['seed_sections_private']+[checkpoint['extension_private']],'ruled')
        residual=raw
        for mask in [mouth,chamber,*housing_masks]:
            residual,_=boolean(residual,mask,True)
            if not valid(residual):raise ValueError('invalid_diagnostic_boundary_residual')
        report['boundary_contacts']['residual_outside_documented_windows']=skin.surface_summary(cad,residual)
        report['boundary_contacts']['window_definitions']=['independent_ruled_recorded_intake_sections','actual_two_plane_chamber_tool','actual_original_housing_cylinder_extents']
        report['boundary_contacts']['only_expected_openings_proven']=False
        report['exports']['unexpected_boundary_contacts']=write('unexpected-boundary-contacts',residual)
        save('sample_material_segments_inside_new_candidate')
        candidate_faces=cad.indexed(candidate,cad.TopAbs_FACE);new_ids=set()
        for source in bank_faces:
            for shape in [source,*list(cut.Modified(source)),*list(cut.Generated(source))]:
                index=candidate_faces.FindIndex(shape)
                if index:new_ids.add(index)
        report['new_cavity_wall_face_ids_private']=sorted(new_ids)
        ray=IntCurvesFace_ShapeIntersector();ray.Load(candidate,1e-8)
        classifier=BRepClass3d_SolidClassifier(candidate)
        def state(point):classifier.Perform(point,1e-8);return classifier.State()
        def moved(point,direction,distance):return cad.gp_Pnt(point.X()+direction[0]*distance,point.Y()+direction[1]*distance,point.Z()+direction[2]*distance)
        rows=[]
        for face_id in sorted(new_ids):
            if len(rows)>=96 or time.monotonic()-started>245:break
            face=cad.TopoDS.Face_s(candidate_faces.FindKey(face_id));surface=BRepAdaptor_Surface(face,True)
            bounds=BRepTools.UVBounds_s(face);accepted=0
            for fu,fv in ((.5,.5),(.25,.25),(.75,.75),(.25,.75),(.75,.25),(.5,.25),(.5,.75),(.25,.5),(.75,.5)):
                if accepted>=3 or len(rows)>=96:break
                u=bounds[0]+fu*(bounds[1]-bounds[0]);v=bounds[2]+fv*(bounds[3]-bounds[2])
                point=cad.gp_Pnt();du=cad.gp_Vec();dv=cad.gp_Vec();surface.D1(u,v,point,du,dv)
                if BRepClass_FaceClassifier(face,point,1e-8).State()!=TopAbs_IN:continue
                normal=du.Crossed(dv)
                if normal.Magnitude()<1e-12:continue
                normal.Normalize();direction=[normal.X(),normal.Y(),normal.Z()]
                signs=[sign for sign in (1.,-1.) if state(moved(point,direction,sign*1e-5))==TopAbs_IN]
                row={'source_new_wall_face_id':face_id,'point_private':[point.X(),point.Y(),point.Z()],
                     'status':'unresolved_not_one_material_side'};accepted+=1
                if len(signs)!=1:rows.append(row);continue
                direction=[signs[0]*x for x in direction];ray.Perform(gp_Lin(point,cad.gp_Dir(*direction)),0.,300.)
                hits=sorted((ray.WParameter(i),i) for i in range(1,ray.NbPnt()+1) if ray.WParameter(i)>1e-5)
                row['status']='unresolved_no_verified_material_exit'
                # Never jump across an unresolved first interface to a later
                # exit and mislabel several material/void segments as one wall.
                for distance,index in hits[:1]:
                    epsilon=min(1e-5,distance/4)
                    if state(moved(point,direction,distance-epsilon))==TopAbs_IN and state(moved(point,direction,distance+epsilon))==TopAbs_OUT:
                        row.update(status='resolved',material_segment_length=distance,
                            exit_candidate_face_id=candidate_faces.FindIndex(ray.Face(index)),
                            direction_into_material_private=direction);break
                rows.append(row)
        report['wall_ray_samples_private']=rows;report['wall_screen']=wall_summary(rows)
        report['wall_screen']['new_wall_faces']=len(new_ids)
        report['wall_screen']['sampling_bounded_early']=len(rows)>=96 or time.monotonic()-started>245
        report['status']=candidate_screen(report['candidate']['BRep_valid_exact'],report['candidate']['solids'],
            report['boundary_contacts']['residual_outside_documented_windows']['area_scan_units_squared'],
            [r['lost_contact_area'] for r in report['housing_contacts']],report['wall_screen'])
        report['inputs_unchanged']=all(inspection.digest(v)==EXPECTED[k] for k,v in paths.items())
        save('complete')
        return 0 if not report['status'].startswith('rejected') else 3
    except Exception as exc:
        report['status']='rejected_or_incomplete';report['error']=type(exc).__name__+': '+str(exc)
        report['inputs_unchanged']=all(inspection.digest(v)==EXPECTED[k] for k,v in paths.items())
        save('failed');raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in EXPECTED:parser.add_argument('--'+name.replace('_','-'),dest=name,type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    raise SystemExit(run(parser.parse_args()))
