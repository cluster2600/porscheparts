"""Exactly two private central hypotheses after G14 span68; no new FEA."""
import argparse
import json
from pathlib import Path
import shutil
import signal
import time

import g14_cad_private as previous
cq,g11,g13,g7,carrier,audit,assembly=previous.cq,previous.g11,previous.g13,previous.g7,previous.carrier,previous.audit,previous.assembly
ROOT=previous.REPO
PRIOR=ROOT/'work/m64-g14/cad-v1'
PRIOR_SHA='3637a51b2d9fa03d97dd7316a7e6b281bb17db29d677ab204a3fade10420b905'
SPECS=(('centre_spine68_local_under_journals',dict(local_abs_x_mm=[34,48],local_z_mm=[123,137],width_mm=30)),
       ('centre_spine68_t40',dict(spine_span_mm=68,width_mm=40,first_unchanged_height_mm=1,transition_height_mm=9)))


def tools(p):
    top=max(v[0][2] for v in carrier.axes(p).values())+9
    return {f'central_mount_pilot_{sx}':previous._cyl([sx*p['carrier_mount_x'],0,p['carrier_face_height']-1],
             [sx*p['carrier_mount_x'],0,top+1],3.3) for sx in (-1,1)}


def candidate(base,p,ident):
    z0=p['carrier_face_height'];top=max(v[0][2] for v in carrier.axes(p).values())+9
    if ident=='centre_spine68_local_under_journals':
        addition=cq.Solid.makeBox(14,30,14,cq.Vector(-48,-15,123)).fuse(
            cq.Solid.makeBox(14,30,14,cq.Vector(34,-15,123)))
    elif ident=='centre_spine68_t40':
        profile=[(-5.5,z0+1),(5.5,z0+1),(20,z0+10),(20,top),(-20,top),(-20,z0+10)]
        wire=cq.Wire.makePolygon([cq.Vector(-34,y,z) for y,z in profile],close=True)
        addition=cq.Solid.extrudeLinear(wire,[],cq.Vector(68,0,0))
    else:raise ValueError('outside the two authorized hypotheses')
    for tool in list(tools(p).values())+list(g11.oil_paths(p,'central_diaphragm').values()):addition=addition.cut(tool)
    return base.fuse(addition).clean()


def run(output):
    output.mkdir(parents=True,exist_ok=False);shutil.copyfile(__file__,output/'g14_central_followup_private.py')
    report=dict(classification='G14_two_central_followup_CAD_hypotheses_not_FEA',source_sha256=g11.sha256(Path(__file__)),
        prior_CAD_receipt_sha256=PRIOR_SHA,started_epoch=time.time(),complete=False,error=None,variants=[],
        FEA_executed=False,material_or_boundary_conditions_changed=False,manufacturing_authorized=False,engine_start_authorized=False,
        rationale='Priority: small under-journal links where node-sampled +x displacement separates from the spine. Width40 is one larger-volume global comparator; neither predicts 0.040mm achievement.',
        crank_samples_deg=list(range(0,720,5)),motion_scope='144 sampled rigid poses of all 27 existing moving components, not continuous/deformable validation')
    try:
        if g11.sha256(PRIOR/'receipt.json')!=PRIOR_SHA:raise ValueError('prior CAD fingerprint changed')
        old=json.loads((PRIOR/'receipt.json').read_text())
        if not old['complete'] or old['error'] is not None:raise ValueError('prior CAD incomplete')
        for name,want in old['frozen_sources_sha256'].items():
            if g11.sha256(ROOT/name)!=want:raise ValueError('frozen source changed')
        if g11.sha256(Path(previous.__file__))!=old['source_sha256']:raise ValueError('private helper changed')
        if g11.sha256(g11.BASELINE)!=old['G7_receipt_sha256']:raise ValueError('G7 receipt changed')
        baseline=json.loads(g11.BASELINE.read_text());p=baseline['values'];reference,_=g7.parts(p)
        if abs(reference['head'].Volume()-baseline['head_volume_mm3'])>.01:raise ValueError('head replay changed')
        report['values']=p;report['G7_receipt_sha256']=old['G7_receipt_sha256'];report['frozen_sources_sha256']=old['frozen_sources_sha256']
        report['prior_private_source_sha256']=old['source_sha256']
        prior=next(r for r in old['variants'] if r['id']=='centre_spine68_t30');path=PRIOR/prior['step']
        if not prior['cad_accepted'] or g11.sha256(path)!=prior['step_sha256']:raise ValueError('span68 baseline not accepted')
        base=cq.importers.importStep(str(path)).val();report['baseline_step_sha256']=prior['step_sha256']
        envelope=g7.native_bounds(cq.Compound.makeCompound(list(reference.values())));shapes={}
        for ident,params in SPECS:
            shape=candidate(base,p,ident);folder=output/ident;folder.mkdir()
            step=folder/'central_diaphragm.step';cq.exporters.export(cq.Workplane().add(shape),str(step))
            cq.exporters.export(cq.Workplane().add(shape),str(folder/'preview.svg'),opt={'projectionDir':(1,-1,-.8),'showHidden':False,'width':900,'height':600})
            section=shape.cut(cq.Solid.makeBox(1000,1000,1000,cq.Vector(0,-500,-500)))
            cq.exporters.export(cq.Workplane().add(section),str(folder/'section-x0.svg'),opt={'projectionDir':(1,0,0),'showHidden':False,'width':900,'height':600})
            bounds=g7.native_bounds(shape);void=audit.closed_voids(shape)
            slab=cq.Solid.makeBox(400,200,1,cq.Vector(-200,-100,p['carrier_face_height']))
            first=g13.difference(shape.intersect(slab),base.intersect(slab))
            land,meta=g13.support_land(shape,p);land0,meta0=g13.support_land(base,p)
            foot=g13.difference(land,land0);bands=previous.journal_masks(shape,base,p)
            oil={k:dict(residual_solid_mm3=audit.overlap(shape,t),tool_connected_solids=len(t.Solids())) for k,t in g11.oil_paths(p,'central_diaphragm').items()}
            new_material=shape.cut(base)
            tool_checks={k:dict(new_material_overlap_mm3=audit.overlap(new_material,t),baseline_overlap_mm3=audit.overlap(base,t),total_overlap_mm3=audit.overlap(shape,t)) for k,t in tools(p).items()}
            collisions=[dict(part=n,volume_mm3=v) for n,s in reference.items() if n!='central_diaphragm' and (v:=audit.overlap(shape,s))>g11.TOL]
            failures=[]
            if not assembly.brep_valid(shape) or len(shape.Solids())!=1:failures.append('invalid_or_disconnected_BRep')
            if not void['no_enclosed_void_detected']:failures.append('enclosed_void')
            if any(v>g11.TOL for d in [first,foot,*bands.values()] for v in d.values()) or abs(meta['bottom_planar_area_mm2']-meta0['bottom_planar_area_mm2'])>g11.TOL:failures.append('foot_or_journal_changed')
            if base.cut(shape).Volume()>g11.TOL:failures.append('baseline_material_removed')
            if any(v['residual_solid_mm3']>g11.TOL or v['tool_connected_solids']!=1 for v in oil.values()):failures.append('oil_path_changed')
            if any(v['new_material_overlap_mm3']>g11.TOL for v in tool_checks.values()):failures.append('new_material_obstructs_existing_tool')
            if any(bounds[k]<envelope[k]-1e-6 for k in ('xmin','ymin','zmin')) or any(bounds[k]>envelope[k]+1e-6 for k in ('xmax','ymax','zmax')):failures.append('outside_assembly_envelope')
            if collisions:failures.append('static_interference')
            row=dict(id=ident,component='central_diaphragm',parameters=params,step=str(step.relative_to(output)),step_sha256=g11.sha256(step),baseline_step_sha256=prior['step_sha256'],
                journal_width_mm=11,journal_diameter_mm=2*(p['rocker_pivot_radius']+p['carrier_journal_radial_clearance']),volume_mm3=shape.Volume(),added_to_spine68_volume_mm3=shape.Volume()-base.Volume(),
                BRep_valid=assembly.brep_valid(shape),solid_count=len(shape.Solids()),bounds_mm=bounds,closed_void_check=void,oil_paths=oil,first_1mm_difference_mm3=first,
                existing_functional_tool_checks=tool_checks,tool_scope='Only existing central-mount pilot tools and real fastener collision envelopes; full tool approach/assembly sequence not qualified',
                bottom_land_difference=foot,support_land=meta,journal_neighbourhood_difference=bands,static_interferences=collisions,sampled_motion_interferences=[],motion_samples_checked=0,rejections=failures,cad_accepted=False,
                native_views={f.name:g11.sha256(f) for f in (folder/'preview.svg',folder/'section-x0.svg')},view_scope='Isolated support BRep and section, no full head or stress field')
            report['variants'].append(row);shapes[ident]=shape
            print(json.dumps({'stage':'static','id':ident,'rejections':failures,'collisions':collisions,'added_volume_mm3':row['added_to_spine68_volume_mm3']}),flush=True)
        accepted=[r for r in report['variants'] if not r['rejections']]
        for angle in report['crank_samples_deg']:
            moving=g11.moving_shapes(p,reference,angle)
            if set(moving)!=set(g11.moving_names(reference)):raise ValueError('moving coverage changed')
            for row in accepted:
                for name,part in moving.items():
                    if (v:=audit.overlap(shapes[row['id']],part))>g11.TOL:row['sampled_motion_interferences'].append(dict(crank_deg=angle,part=name,volume_mm3=v))
                row['motion_samples_checked']+=1
            if angle%60==0:
                with (output/f'checkpoint-{angle:03d}.json').open('x') as f:json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
                print(json.dumps({'stage':'motion','crank_deg':angle}),flush=True)
        for row in accepted:
            if row['sampled_motion_interferences']:row['rejections'].append('sampled_motion_interference')
            row['cad_accepted']=not row['rejections'] and row['motion_samples_checked']==144
        report['complete']=True
    except BaseException as exc:report['error']=type(exc).__name__+': '+str(exc)
    finally:
        signal.alarm(0);report['finished_epoch']=time.time()
        with (output/'receipt.json').open('x') as f:json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
    return 0 if report['complete'] and report['error'] is None else 2


if __name__=='__main__':
    def interrupted(signum,frame):raise TimeoutError('private CAD timebox reached or interrupted')
    signal.signal(signal.SIGALRM,interrupted);signal.signal(signal.SIGTERM,interrupted);signal.alarm(600)
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    raise SystemExit(run(parser.parse_args().output))
