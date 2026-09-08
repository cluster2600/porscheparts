#!/usr/bin/env python3
"""Build a private cold-flow intake gas candidate from existing native parts.

No master body is overwritten. The two guide-top annuli are explicit idealized
bench seals, not manufactured engine seals. No CFD or engine release follows.
"""
import argparse
import copy
import json
import math
from pathlib import Path
import shutil
import time

import inspect_pilot as inspection

EXPECTED = {
    **{k: inspection.EXPECTED[k] for k in ('module','build','registration','intake')},
    'body': '3d78fd2ac9e78e5446f1a8fddc2b5d5ad1702cf912a74f579d6b42940124c4a4',
    'chamber': '8643968ccf678fde1a4ba68ff7866fc468ec8faadbf79a53cc055e50c0010dc8',
    'chamber_report': 'cc7d10e2b34cf3c2f786b0fbf6452f52d1a8f23f7ab59c1c711ec1fb58e36830',
    'intake_report': '53beca98c5d152f2cb59d530934fc3fe8481fb7b4e49f541b97ed200ad430e8c',
}


def interior_profile(seat):
    """Use the exact V2 six-vertex insert meridian, not a replacement cylinder."""
    if len(seat)!=6 or any(not math.isfinite(v) for pair in seat for v in pair):
        raise ValueError('finite_six_vertex_seat_profile_required')
    inside = [seat[0], seat[5], seat[4], seat[3]]
    if any(r<=0 for r,z in inside) or any(z1>=z2 or r1<r2 for (r1,z1),(r2,z2) in zip(inside,inside[1:])):
        raise ValueError('ordered_exact_seat_interior_required')
    if seat[1][0]<=inside[0][0] or seat[2][0]<=inside[-1][0]:
        raise ValueError('positive_insert_wall_required')
    return [(0.,inside[0][1]),*inside,(0.,inside[-1][1])]


def guide_annulus_area(stem_diameter,diametral_clearance):
    if not all(math.isfinite(v) and v>0 for v in (stem_diameter,diametral_clearance)):
        raise ValueError('positive_finite_diameters_required')
    return math.pi*((stem_diameter+diametral_clearance)**2-stem_diameter**2)/4


def local_neck_passes(record):
    """A shared upstream trunk cannot substitute for each local open neck."""
    return (record['BRep_valid'] is True and record['solid_count']==1
            and record['BOP_no_faults'] is True
            and record['trunk_excluded_by_axial_bound'] is True
            and math.isfinite(record['other_seat_overlap_volume'])
            and abs(record['other_seat_overlap_volume'])<=1e-9
            and all(math.isfinite(a) and a>1e-7 for a in
                    (record['chamber_side_area'],record['throat_side_area'])))


def boundary_owner(matches, area, surface_type):
    """A construction tool is not a material owner of a real seat face."""
    distinct={row['role'] for row in matches}
    if len(distinct)==1:return next(iter(distinct)),None
    seats=[row for row in matches if row['role']=='walls_seat']
    chamber=[row for row in matches if row['role']=='walls_chamber']
    if (distinct=={'walls_chamber','walls_seat'} and surface_type=='GeomAbs_Plane'
            and len(seats)==1 and area>0
            and all(row['source'].startswith('chamber_tool_face_') for row in chamber)
            and all(abs(row['coincident_area']-area)<=max(1e-8,1e-7*area) for row in matches)):
        return 'walls_seat',{'method':'actual_seat_material_over_coincident_negative_construction_tool',
            'retained_material_source':seats[0]['source'],'whole_face_covered':True,
            'negative_tool_sources':[row['source'] for row in chamber],
            'coverage_ratios':[row['coincident_area']/area for row in matches]}
    return ('unknown' if not distinct else 'ambiguous'),None


def reclassify_report(source, target):
    """Non-geometric enrichment; retain failed BOP and local-neck gates."""
    source=Path(source);target=Path(target)
    if target.exists():raise FileExistsError(target)
    original=json.loads(source.read_text());report=copy.deepcopy(original)
    def verified_file(record):
        path=source.parent/record['file']
        if path.is_symlink() or path.resolve().parent!=source.parent.resolve() and source.parent.resolve() not in path.resolve().parents:
            raise ValueError('artifact_must_remain_in_private_run_directory')
        if inspection.digest(path)!=record['sha256']:raise ValueError('changed_native_artifact')
    verified_file(report['exports']['domain_brep'])
    roles={};unknown=[];ambiguous=[];resolved=[]
    for face in report['boundary_faces']:
        verified_file(face)
        role,resolution=boundary_owner(face['source_match'],face['area'],face['surface_type'])
        face['role']=role
        if resolution:
            face['ownership_resolution']=resolution;resolved.append(face['id'])
        if role=='unknown':unknown.append(face['id'])
        if role=='ambiguous':ambiguous.append({'face':face['id'],'roles':sorted({r['role'] for r in face['source_match']})})
        roles[role]=roles.get(role,0)+1
    report.update(boundary_role_counts=roles,unmatched_faces=unknown,ambiguous_faces=ambiguous)
    report['gates']['boundary_assignment_complete']=not unknown and not ambiguous and roles.get('inlet')==1 and roles.get('receiver_outlet')==1 and roles.get('fixture_stem_seals')==2
    report['classification_enrichment']={'source_report_sha256':inspection.digest(source),
        'classifier_source_sha256':inspection.digest(__file__),'resolved_face_ids':resolved,
        'geometry_changed':False,'new_native_run_executed':False,
        'BOP_or_neck_gates_changed':False}
    report['status']='native_domain_candidate_boundaries_complete_pending_independent_audit' if all(report['gates'].values()) else 'rejected_native_domain_or_boundaries'
    target.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');target.chmod(0o600)
    return report


def run(args):
    from OCP.BRep import BRep_Builder
    from OCP.BRepTools import BRepTools
    from OCP.TopoDS import TopoDS_Shape
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse
    from OCP.TopTools import TopTools_ListOfShape
    from OCP.BOPAlgo import BOPAlgo_ArgumentAnalyzer
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Plane
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    import OCP
    start=time.monotonic()
    paths={name:getattr(args,name) for name in EXPECTED}
    if {name:inspection.digest(path) for name,path in paths.items()}!=EXPECTED:
        raise ValueError('exact_native_sources_required')
    if args.output.exists():raise FileExistsError(args.output)
    args.output.mkdir(parents=True,mode=0o700)
    source_copy=args.output/'builder-source.py';shutil.copyfile(__file__,source_copy);source_copy.chmod(0o600)
    report={'schema':'m64-intake-gas-domain/v1','status':'building',
            'source_sha256':inspection.digest(__file__),'inputs_sha256':EXPECTED,
            'OCP_version':OCP.__version__,'units':'scan_units_under_unverified_1_unit_per_mm_hypothesis',
            'receiver':{'diameter':100.,'length':100.,'outlet_Z':-100.,'scope':'separate_bench_fixture_not_piston_or_OEM'},
            'lifts_design_mm':{'intake':6.,'exhaust':0.},
            'master_modified':False,'ports_cut_in_body':False,'CFD_executed':False,
            'manufacturing_authorized':False,'M64_fitment_validated':False,
            'closed_assembled_chamber_volume_computed':False,
            'independent_closure_audit_accepted':False,'gates':{},'stages':[],
            'fixture_stem_seal_authority':'explicit_parent_authorization_for_idealized_sealed_flowbench_only',
            'difference_order':args.difference_order,
            'difference_set_identity':'union(A_i) minus B equals union(A_i minus B); B contains all 12 actual components',
            'boundary_faces':[]}
    def save():
        target=args.output/'gas-domain-report.json'
        target.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');target.chmod(0o600)
    def stage(name):
        report['stage']=name;report['elapsed_seconds']=time.monotonic()-start;save()
        print(json.dumps({'stage':name}),flush=True)
    cad=inspection.design.CAD()
    def native_read(path):
        shape=TopoDS_Shape()
        if not BRepTools.Read_s(shape,str(path),BRep_Builder()):raise ValueError('native_read_failed')
        return shape
    def operation(kind,a,b):
        aa=TopTools_ListOfShape();bb=TopTools_ListOfShape();aa.Append(a)
        for shape in (b if isinstance(b,list) else [b]):bb.Append(shape)
        op=kind();op.SetArguments(aa);op.SetTools(bb);op.SetNonDestructive(True)
        op.SetRunParallel(False);op.SetFuzzyValue(0.);op.Build()
        if not op.IsDone():raise ValueError('native_boolean_failed')
        return op.Shape()
    def vol(shape):
        gp=cad.GProp_GProps();err=cad.BRepGProp.VolumeProperties_s(shape,gp,1e-9,True)
        return {'value':gp.Mass(),'relative_quadrature_estimate_not_bound':err}
    def props(face):
        gp=cad.GProp_GProps();cad.BRepGProp.SurfaceProperties_s(face,gp)
        q=gp.CentreOfMass();s=BRepAdaptor_Surface(face,True)
        b=Bnd_Box();BRepBndLib.AddOptimal_s(face,b,False,False)
        return {'area':gp.Mass(),'center':[q.X(),q.Y(),q.Z()],
                'surface_type':str(s.GetType()).split('.')[-1],'bbox':list(b.Get())}
    def faces(shape):
        index=cad.indexed(shape,cad.TopAbs_FACE)
        return [cad.TopoDS.Face_s(index.FindKey(i)) for i in range(1,index.Extent()+1)]
    def reg(shape):
        tr=cad.gp_Trsf();tr.SetRotation(cad.gp_Ax1(cad.gp_Pnt(0,0,0),cad.gp_Dir(0,0,1)),-math.pi/2)
        tr.SetTranslationPart(cad.gp_Vec(0,0,3))
        return cad.BRepBuilderAPI_Transform(shape,tr,True).Shape()
    def placed(shape,spec):return reg(cad.pose(shape,spec))
    def bop(shape):
        job=BOPAlgo_ArgumentAnalyzer();job.SetShape1(shape)
        job.SelfInterMode=True;job.SmallEdgeMode=True;job.RebuildFaceMode=True
        job.ContinuityMode=True;job.CurveOnSurfaceMode=True;job.Perform()
        return {'has_faulty':job.HasFaulty(),'has_errors':job.HasErrors(),'has_warnings':job.HasWarnings(),
                'faults':[str(row.GetCheckStatus()).split('.')[-1] for row in job.GetCheckResult()]}
    references=[]
    def reference(face,role,label):
        face=cad.TopoDS.Face_s(face)
        references.append({'shape':face,'role':role,'label':label,'properties':props(face)})
    try:
        stage('read_native_geometry_and_actual_module')
        source=cad.read_step(args.body);bank=native_read(args.intake);chamber=native_read(args.chamber)
        module=cad.read_step(args.module);solids=cad.indexed(module,cad.TopAbs_SOLID)
        build=json.loads(args.build.read_text());p=inspection.design.Parameters(**build['parameters']).validate()
        registration=json.loads(args.registration.read_text())
        if registration['registration']!={'scale_scan_units_per_mm_hypothesis':1.,'rotation_Z_deg_hypothesis':-90.,'translation_Z_hypothesis':3.}:
            raise ValueError('fixed_registration_required')
        ids={r['name']:r['imported_module_solid_id'] for r in registration['components_imported_from_exact_STEP']}
        parts=[]
        for part in inspection.design.construct(cad,p,{'intake_mm':0.,'exhaust_mm':0.}):
            shape=solids.FindKey(ids[part['name']])
            if part['role']=='valve' and part['spec']['kind']=='intake':
                tr=cad.gp_Trsf();tr.SetTranslation(cad.gp_Vec(*inspection.lift_translation(part['spec']['axis_angle_deg'],6.)))
                shape=cad.BRepBuilderAPI_Transform(shape,tr,True).Shape()
            parts.append({**part,'shape':reg(shape)})
        entry=json.loads(args.intake_report.read_text())['extension_private']
        for i,face in enumerate(faces(bank)):
            s=BRepAdaptor_Surface(face,True);is_entry=False
            if s.GetType()==GeomAbs_Plane:
                n=s.Plane().Axis().Direction();loc=s.Plane().Location()
                is_entry=abs(abs(n.Y())-1.)<1e-10 and abs(loc.Y()-entry['center'][1])<1e-7
            reference(face,'inlet' if is_entry else 'walls_port','raw_intake_face_'+str(i+1))
        for i,face in enumerate(faces(chamber)):reference(face,'walls_chamber','chamber_tool_face_'+str(i+1))
        # Receiver top remnants are physical deck only where the actual body has
        # a coincident Z0 face. Do not blindly relabel an invented top cap wall.
        for i,face in enumerate(faces(source)):
            s=BRepAdaptor_Surface(face,True)
            if s.GetType()==GeomAbs_Plane and abs(abs(s.Plane().Axis().Direction().Z())-1.)<1e-12 and abs(s.Plane().Location().Z())<1e-7:
                reference(face,'walls_chamber','actual_body_bottom_'+str(i+1))
        receiver=cad.BRepPrimAPI_MakeCylinder(cad.gp_Ax2(cad.gp_Pnt(0,0,-100),cad.gp_Dir(0,0,1)),50.,100.).Shape()
        for i,face in enumerate(faces(receiver)):
            s=BRepAdaptor_Surface(face,True)
            if s.GetType()==GeomAbs_Plane:
                if abs(s.Plane().Location().Z()+100.)<1e-7:reference(face,'receiver_outlet','receiver_lower_face')
            else:reference(face,'walls_receiver','receiver_cylinder')
        additions=[('chamber',chamber),('receiver',receiver)];neck_probes=[]
        report['guide_extensions']=[];report['seat_interiors']=[]
        for spec in inspection.design.valve_specs(p):
            if spec['kind']!='intake':continue
            profiles,_=inspection.design.profiles(p,spec)
            meridian=interior_profile(profiles['seat']);inner=placed(cad.revolve(meridian),spec)
            overlap=vol(operation(BRepAlgoAPI_Common,inner,bank))
            report['seat_interiors'].append({'name':spec['name'],'profile_private':meridian,
                  'existing_port_overlap':overlap,'volume':vol(inner)})
            if overlap['value']<=1e-7:raise ValueError('seat_throat_does_not_overlap_existing_port')
            additions.append((spec['name']+'_seat_interior',inner))
            # This probe cannot use the common upstream trunk to connect the
            # two banks: it is restricted to the exact throat radius and the
            # local gauge-to-seat-top interval. Its two end sections are
            # checked against the final gas, never against the probe alone.
            probe=cad.BRepPrimAPI_MakeCylinder(cad.gp_Ax2(cad.gp_Pnt(0,0,0),cad.gp_Dir(0,0,1)),
                                              meridian[-2][0],meridian[-2][1]).Shape()
            ends={}
            for face in faces(probe):
                adaptor=BRepAdaptor_Surface(face,True)
                if adaptor.GetType()==GeomAbs_Plane:
                    ends['chamber_side' if abs(adaptor.Plane().Location().Z())<1e-9 else 'throat_side']=placed(face,spec)
            neck_probes.append({'name':spec['name'],'shape':placed(probe,spec),'ends':ends,
                                'radius':meridian[-2][0],'axial_interval':[0.,meridian[-2][1]]})
            gi=(p.stem_diameter_mm+spec['guide_diametral_clearance_mm'])/2
            guide_cylinder=cad.BRepPrimAPI_MakeCylinder(cad.gp_Ax2(cad.gp_Pnt(0,0,20),cad.gp_Dir(0,0,1)),gi,35.).Shape()
            extension=placed(guide_cylinder,spec)
            valve=next(part['shape'] for part in parts if part['name']==spec['name']+'_valve')
            actual_annulus=operation(BRepAlgoAPI_Cut,extension,valve)
            communication=vol(operation(BRepAlgoAPI_Common,actual_annulus,bank))
            report['guide_extensions'].append({'name':spec['name'],'axial_interval':[20.,55.],
                'upper_fixture_seal_nominal_area':guide_annulus_area(p.stem_diameter_mm,spec['guide_diametral_clearance_mm']),
                'communication_with_original_negative_volume':communication,'full_annular_volume':vol(actual_annulus)})
            if communication['value']<=1e-7:raise ValueError('guide_extension_not_physically_connected_to_negative')
            additions.append((spec['name']+'_real_guide_inner_space',extension))
            # Only the real upper end, not a midway cap inherited from the raw
            # negative, is allowed to become an idealized bench seal patch.
            top=next(face for face in faces(guide_cylinder)
                     if BRepAdaptor_Surface(face,True).GetType()==GeomAbs_Plane
                     and abs(BRepAdaptor_Surface(face,True).Plane().Location().Z()-55.)<1e-7)
            reference(placed(top,spec),'fixture_stem_seals',spec['name']+'_guide_top_idealized_bench_seal')
        for part in parts:
            for i,face in enumerate(faces(part['shape'])):
                reference(face,'walls_'+part['role'],part['name']+'_face_'+str(i+1))
        if args.diagnose_pieces:
            stage('diagnose_seat_overlap_before_any_fusion')
            report['piece_seat_intersections']=[]
            for part in parts:
                if part['role']!='seat':continue
                for name,shape in [('raw_intake',bank),*additions]:
                    common=operation(BRepAlgoAPI_Common,shape,part['shape'])
                    row={'seat':part['name'],'piece':name,'volume':vol(common),
                         'BRep_valid':cad.valid(common),'solids':cad.indexed(common,cad.TopAbs_SOLID).Extent()}
                    if row['solids']:
                        target=args.output/(part['name']+'-'+name+'-intersection.brep')
                        BRepTools.Write_s(common,str(target));target.chmod(0o600)
                        row['intersection_sha256']=inspection.digest(target)
                    report['piece_seat_intersections'].append(row);save()
            report['status']='piece_intersection_diagnostic_only_no_gas_domain'
            report['inputs_unchanged']=all(inspection.digest(paths[k])==v for k,v in EXPECTED.items())
            stage('complete');return 0
        stage('fuse_existing_passages_and_exact_interior_extensions')
        gas=bank
        for name,shape in additions:
            gas=operation(BRepAlgoAPI_Fuse,gas,shape)
            row={'operation':'fuse','name':name,'BRep_valid':cad.valid(gas),
                 'solid_count':cad.indexed(gas,cad.TopAbs_SOLID).Extent(),'volume':vol(gas)}
            report['stages'].append(row);save()
            if not row['BRep_valid']:raise ValueError('invalid_union_'+name)
        stage('subtract_actual_valves_seats_guides')
        before_cut=args.output/'before-component-cut.brep'
        BRepTools.Write_s(gas,str(before_cut));before_cut.chmod(0o600)
        report['before_component_cut_sha256']=inspection.digest(before_cut)
        report['component_intersections_before_simultaneous_cut']=[]
        for part in parts:
            intersection=operation(BRepAlgoAPI_Common,gas,part['shape'])
            overlap=vol(intersection);overlap_solids=cad.indexed(intersection,cad.TopAbs_SOLID).Extent()
            if not cad.valid(intersection):raise ValueError('invalid_component_intersection_'+part['name'])
            report['component_intersections_before_simultaneous_cut'].append({'name':part['name'],
                     'intersection_volume':overlap,'intersection_solid_count':overlap_solids});save()
        tools=[part['shape'] for part in parts]
        if args.difference_order=='before-union':
            # The rejected after-union cut produced a touching micro-shell,
            # not a faulty individual face. Distribute the SAME difference
            # before fusion; no tool, contact face or small overlap is omitted.
            stage('subtract_all_12_components_from_each_original_constituent')
            free=[]
            for name,shape in [('raw_intake',bank),*additions]:
                cut=operation(BRepAlgoAPI_Cut,shape,tools)
                row={'operation':'constituent_cut_all_12_components','name':name,
                     'BRep_valid':cad.valid(cut),'solid_count':cad.indexed(cut,cad.TopAbs_SOLID).Extent(),
                     'volume_before':vol(shape),'volume_after':vol(cut)}
                report['stages'].append(row);save()
                if not row['BRep_valid']:raise ValueError('invalid_distributed_cut_'+name)
                free.append((name,cut))
            stage('fuse_exact_distributed_free_gas_constituents')
            gas=free[0][1]
            for name,shape in free[1:]:
                gas=operation(BRepAlgoAPI_Fuse,gas,shape)
                row={'operation':'fuse_free_constituent','name':name,'BRep_valid':cad.valid(gas),
                     'solid_count':cad.indexed(gas,cad.TopAbs_SOLID).Extent(),'volume':vol(gas)}
                report['stages'].append(row);save()
                if not row['BRep_valid']:raise ValueError('invalid_distributed_union_'+name)
        else:
            gas=operation(BRepAlgoAPI_Cut,gas,tools)
        row={'operation':'complete_'+args.difference_order+'_all_12_actual_components',
             'BRep_valid':cad.valid(gas),'solid_count':cad.indexed(gas,cad.TopAbs_SOLID).Extent(),'volume':vol(gas)}
        report['stages'].append(row);save()
        if not row['BRep_valid']:
            failed=args.output/'rejected-after-component-cut.brep'
            BRepTools.Write_s(gas,str(failed));failed.chmod(0o600)
            report['rejected_candidate_sha256']=inspection.digest(failed)
            raise ValueError('invalid_simultaneous_component_subtraction')
        report['gates'].update(single_solid=cad.indexed(gas,cad.TopAbs_SOLID).Extent()==1,
            brep_valid=cad.valid(gas),guide_extensions_communicate=True)
        if not report['gates']['single_solid']:raise ValueError('gas_domain_is_not_one_connected_solid')
        stage('check_each_local_intake_neck_without_shared_trunk')
        report['local_intake_necks']=[]
        seeds=json.loads(args.intake_report.read_text())['seed_sections_private']
        if any(abs(abs(row['normal'][1])-1.)>1e-12 for row in seeds):
            raise ValueError('documented_Y_axial_trunk_required_for_local_exclusion')
        trunk_min_y=min(row['center'][1] for row in seeds)
        for probe in neck_probes:
            local=operation(BRepAlgoAPI_Common,gas,probe['shape']);check=bop(local)
            box=Bnd_Box();BRepBndLib.AddOptimal_s(probe['shape'],box,False,False)
            other=next(shape for name,shape in additions if name.endswith('_seat_interior') and not name.startswith(probe['name']))
            row={'name':probe['name'],'probe_radius':probe['radius'],'axial_interval':probe['axial_interval'],
                 'BRep_valid':cad.valid(local),'solid_count':cad.indexed(local,cad.TopAbs_SOLID).Extent(),
                 'BOP_no_faults':not(check['has_faulty'] or check['has_errors']), 'BOP':check,
                 'trunk_excluded_by_axial_bound':box.Get()[4]<trunk_min_y,
                 'probe_max_Y':box.Get()[4],'documented_trunk_min_Y':trunk_min_y,
                 'other_seat_overlap_volume':vol(operation(BRepAlgoAPI_Common,probe['shape'],other))['value']}
            for name,face in probe['ends'].items():row[name+'_area']=cad.area(operation(BRepAlgoAPI_Common,local,face))
            row['passes']=local_neck_passes(row)
            report['local_intake_necks'].append(row);save()
        report['gates']['positive_intake_curtain']=len(report['local_intake_necks'])==2 and all(row['passes'] for row in report['local_intake_necks'])
        stage('audit_and_export_native_gas_candidate')
        report['native_BOP']=bop(gas)
        report['gates']['bop_no_faults']=not(report['native_BOP']['has_faulty'] or report['native_BOP']['has_errors'])
        report['domain_volume']=vol(gas)
        report['properties']={'volume':report['domain_volume']['value'],'area':cad.area(gas),
                              'solids':cad.indexed(gas,cad.TopAbs_SOLID).Extent()}
        native=args.output/'domain.brep';BRepTools.Write_s(gas,str(native));native.chmod(0o600)
        persisted=native_read(native)
        report['native_roundtrip_BOP']=bop(persisted)
        report['gates']['native_roundtrip_valid']=cad.valid(persisted) and cad.indexed(persisted,cad.TopAbs_SOLID).Extent()==1 and report['native_roundtrip_BOP']==report['native_BOP']
        stp=args.output/'domain.step';cad.write_step(stp,[{'name':'intake_cold_flow_candidate','role':'gas','shape':gas}]);stp.chmod(0o600)
        reread=cad.read_step(stp)
        report['STEP_BOP']=bop(reread)
        report['gates']['step_roundtrip_valid']=cad.valid(reread) and cad.indexed(reread,cad.TopAbs_SOLID).Extent()==1
        report['STEP_BOP_qualified']=not(report['STEP_BOP']['has_faulty'] or report['STEP_BOP']['has_errors'])
        report['exports']={'domain_brep':{'file':'domain.brep','sha256':inspection.digest(native)},
                           'STEP':{'file':'domain.step','sha256':inspection.digest(stp)}}
        save()
        stage('classify_each_persisted_native_boundary_face')
        output_faces=args.output/'faces';output_faces.mkdir(mode=0o700)
        roles={};unmatched=[];ambiguous=[]
        def boxes_overlap(a,b):return all(a[i]<=b[i+3]+1e-6 and b[i]<=a[i+3]+1e-6 for i in range(3))
        # Classification operates on the persisted native BRep used downstream,
        # not on STEP face indexes or body faces transplanted to another shape.
        for index,face in enumerate(faces(persisted),1):
            properties=props(face);area=properties['area'];matches=[]
            for ref in references:
                rp=ref['properties']
                if properties['surface_type']!=rp['surface_type'] or not boxes_overlap(properties['bbox'],rp['bbox']):continue
                if face.IsSame(ref['shape']):overlap=area
                else:
                    # Parallel planar carriers must coincide before an area
                    # Boolean is meaningful; this avoids crossing-face matches.
                    a=BRepAdaptor_Surface(face,True);b=BRepAdaptor_Surface(ref['shape'],True)
                    if a.GetType()==GeomAbs_Plane:
                        pa,pb=a.Plane(),b.Plane()
                        if abs(abs(pa.Axis().Direction().Dot(pb.Axis().Direction()))-1.)>1e-9 or abs(pa.Distance(pb.Location()))>1e-6:continue
                    overlap=cad.area(operation(BRepAlgoAPI_Common,face,ref['shape']))
                if abs(overlap-area)<=max(1e-8,1e-7*area):
                    matches.append({'role':ref['role'],'source':ref['label'],'coincident_area':overlap})
            role,resolution=boundary_owner(matches,area,properties['surface_type'])
            if role=='unknown':unmatched.append(index)
            elif role=='ambiguous':ambiguous.append({'face':index,'roles':sorted({r['role'] for r in matches})})
            target=output_faces/('face-%04d.brep'%index)
            BRepTools.Write_s(face,str(target));target.chmod(0o600)
            row={'id':index,'role':role,'file':str(target.relative_to(args.output)),
                 'sha256':inspection.digest(target),**properties,'source_match':matches}
            if resolution:row['ownership_resolution']=resolution
            report['boundary_faces'].append(row);roles[role]=roles.get(role,0)+1
            if index%10==0:save()
        report['boundary_role_counts']=roles
        report['unmatched_faces']=unmatched;report['ambiguous_faces']=ambiguous
        report['gates']['boundary_assignment_complete']=not unmatched and not ambiguous and roles.get('inlet')==1 and roles.get('receiver_outlet')==1 and roles.get('fixture_stem_seals')==2
        report['inputs_unchanged']=all(inspection.digest(paths[k])==v for k,v in EXPECTED.items())
        report['status']='native_domain_candidate_boundaries_complete_pending_independent_audit' if all(report['gates'].values()) else 'rejected_native_domain_or_boundaries'
        stage('complete')
        return 0 if all(report['gates'].values()) else 3
    except Exception as exc:
        report['status']='rejected_or_incomplete';report['error']=str(exc)
        report['elapsed_seconds']=time.monotonic()-start;save();raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in EXPECTED:parser.add_argument('--'+name.replace('_','-'),dest=name,type=Path,required=True)
    parser.add_argument('--diagnose-pieces',action='store_true',help='Measure primitive/seat intersections without fusing or producing gas')
    parser.add_argument('--difference-order',choices=('before-union','after-union'),default='before-union')
    parser.add_argument('--output',type=Path,required=True)
    raise SystemExit(run(parser.parse_args()))
