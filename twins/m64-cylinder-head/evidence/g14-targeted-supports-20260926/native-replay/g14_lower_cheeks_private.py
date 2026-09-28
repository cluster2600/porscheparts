"""Second private outer hypothesis: unchanged-foot lower haunches plus high cheeks."""
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


def functional_tools(p,sy):
    z=p['carrier_face_height'];tools={}
    for sx in (-1,1):
        x,y=sx*p['stud_span_x']/2,sy*p['stud_span_y']/2
        tools[f'stud_nut_access_{sx}']=previous._cyl([x,y,z-1],[x,y,z+20],11)
        x,y=sx*p['carrier_mount_x'],sy*p['carrier_end_y']
        tools[f'mount_tool_access_{sx}']=previous._cyl([x,y,z+p['carrier_foot_height']],[x,y,z+120],7)
    return tools


def reinforced(base,p,sy):
    z0=p['carrier_face_height']+1
    pieces=[]
    for side,(_,cam) in carrier.axes(p).items():
        lo,hi=(cam[0]-20,-32) if side=='intake' else (32,cam[0]+20)
        front=p[side+'_valve_y']+p['spring_outer_diameter']/2+1
        points=[(45,z0),(45,108),(front,108)]
        wire=cq.Wire.makePolygon([cq.Vector(lo,sy*y,z) for y,z in points],close=True)
        pieces.append(cq.Solid.extrudeLinear(wire,[],cq.Vector(hi-lo,0,0)))
    addition=pieces[0].fuse(pieces[1])
    # Preserve the original stud/nut access drilling; apply only to new material.
    for tool in functional_tools(p,sy).values():addition=addition.cut(tool)
    for tool in g11.oil_paths(p,'carrier_base_p').values():
        addition=addition.cut(tool if sy==1 else tool.mirror('XZ'))
    return base.fuse(addition).clean()


def run(output):
    output.mkdir(parents=True,exist_ok=False);shutil.copyfile(__file__,output/'g14_lower_cheeks_private.py')
    report=dict(classification='G14_second_outer_CAD_hypothesis_not_FEA',source_sha256=g11.sha256(Path(__file__)),
        prior_CAD_receipt_sha256=PRIOR_SHA,started_epoch=time.time(),complete=False,error=None,variants=[],
        FEA_executed=False,manufacturing_authorized=False,engine_start_authorized=False,
        rationale='Observed -z Uy is shared by frame and local rib; lower front haunches target frame bending while keeping the entire first millimetre and fixed land unchanged. No predicted 0.040mm performance.',
        crank_samples_deg=list(range(0,720,5)),motion_scope='144 sampled rigid poses only')
    try:
        if g11.sha256(PRIOR/'receipt.json')!=PRIOR_SHA:raise ValueError('prior CAD fingerprint changed')
        old=json.loads((PRIOR/'receipt.json').read_text())
        if not old['complete'] or old['error'] is not None:raise ValueError('prior CAD incomplete')
        for name,want in old['frozen_sources_sha256'].items():
            if g11.sha256(ROOT/name)!=want:raise ValueError('frozen source changed')
        if g11.sha256(Path(previous.__file__))!=old['source_sha256']:raise ValueError('private helper source changed')
        if g11.sha256(g11.BASELINE)!=old['G7_receipt_sha256']:raise ValueError('G7 receipt changed')
        baseline=json.loads(g11.BASELINE.read_text());p=baseline['values'];reference,_=g7.parts(p)
        envelope=g7.native_bounds(cq.Compound.makeCompound(list(reference.values())))
        shapes={}
        for tag,sy in (('p',1),('m',-1)):
            prior=next(r for r in old['variants'] if r['id']=='outer_high_cheeks_'+tag)
            step=PRIOR/prior['step']
            if not prior['cad_accepted'] or g11.sha256(step)!=prior['step_sha256']:raise ValueError('prior outer shape not accepted')
            base=cq.importers.importStep(str(step)).val();shape=reinforced(base,p,sy)
            ident='outer_high_cheeks_lower_haunch_'+tag;folder=output/ident;folder.mkdir()
            path=folder/('carrier_base_'+tag+'.step');cq.exporters.export(cq.Workplane().add(shape),str(path))
            cq.exporters.export(cq.Workplane().add(shape),str(folder/'preview.svg'),opt={'projectionDir':(1,-1,-.8),'showHidden':False,'width':900,'height':600})
            section=shape.cut(cq.Solid.makeBox(1000,1000,1000,cq.Vector(0,-500,-500)))
            cq.exporters.export(cq.Workplane().add(section),str(folder/'section-x0.svg'),opt={'projectionDir':(1,0,0),'showHidden':False,'width':900,'height':600})
            bounds=g7.native_bounds(shape);void=audit.closed_voids(shape)
            slab=cq.Solid.makeBox(400,200,1,cq.Vector(-200,-100,p['carrier_face_height']))
            first=g13.difference(shape.intersect(slab),base.intersect(slab))
            land,meta=g13.support_land(shape,p);land0,meta0=g13.support_land(base,p)
            foot=g13.difference(land,land0);bands=previous.journal_masks(shape,base,p)
            oil={k:dict(residual_solid_mm3=audit.overlap(shape,t if sy==1 else t.mirror('XZ')),tool_connected_solids=len(t.Solids())) for k,t in g11.oil_paths(p,'carrier_base_p').items()}
            new_material=shape.cut(base)
            tool_checks={k:dict(new_material_overlap_mm3=audit.overlap(new_material,t),baseline_overlap_mm3=audit.overlap(base,t),total_overlap_mm3=audit.overlap(shape,t)) for k,t in functional_tools(p,sy).items()}
            collisions=[dict(part=n,volume_mm3=v) for n,s in reference.items() if n!='carrier_base_'+tag and (v:=audit.overlap(shape,s))>g11.TOL]
            failures=[]
            if not assembly.brep_valid(shape) or len(shape.Solids())!=1:failures.append('invalid_or_disconnected_BRep')
            if not void['no_enclosed_void_detected']:failures.append('enclosed_void')
            if any(v>g11.TOL for d in [first,foot,*bands.values()] for v in d.values()) or abs(meta['bottom_planar_area_mm2']-meta0['bottom_planar_area_mm2'])>g11.TOL:failures.append('foot_or_journal_changed')
            if base.cut(shape).Volume()>g11.TOL:failures.append('baseline_material_removed')
            if any(v['residual_solid_mm3']>g11.TOL or v['tool_connected_solids']!=1 for v in oil.values()):failures.append('oil_path_changed')
            if any(v['new_material_overlap_mm3']>g11.TOL for v in tool_checks.values()):failures.append('new_material_obstructs_existing_tool')
            if any(bounds[k]<envelope[k]-1e-6 for k in ('xmin','ymin','zmin')) or any(bounds[k]>envelope[k]+1e-6 for k in ('xmax','ymax','zmax')):failures.append('outside_assembly_envelope')
            if collisions:failures.append('static_interference')
            row=dict(id=ident,component='carrier_base_'+tag,step=str(path.relative_to(output)),step_sha256=g11.sha256(path),baseline_step_sha256=prior['step_sha256'],
                parameters=dict(lower_haunch_z_mm=[p['carrier_face_height']+1,108],front_y_absolute_mm={s:p[s+'_valve_y']+16 for s in ('intake','exhaust')},stud_clearance_radius_mm=11),
                journal_width_mm=8,journal_diameter_mm=12.58,volume_mm3=shape.Volume(),added_to_high_cheeks_volume_mm3=shape.Volume()-base.Volume(),
                BRep_valid=assembly.brep_valid(shape),solid_count=len(shape.Solids()),bounds_mm=bounds,closed_void_check=void,oil_paths=oil,first_1mm_difference_mm3=first,
                existing_functional_tool_checks=tool_checks,tool_scope='Original finite tool definitions preserved; historical obstructions, full tool approach and maintenance sequence are not qualified',
                bottom_land_difference=foot,support_land=meta,journal_neighbourhood_difference=bands,static_interferences=collisions,sampled_motion_interferences=[],motion_samples_checked=0,rejections=failures,cad_accepted=False,
                native_views={f.name:g11.sha256(f) for f in (folder/'preview.svg',folder/'section-x0.svg')},view_scope='Isolated support and section, no full head/stress field')
            report['variants'].append(row);shapes[tag]=shape
            print(json.dumps({'stage':'static','id':ident,'rejections':failures,'collisions':collisions,'added_volume_mm3':row['added_to_high_cheeks_volume_mm3']}),flush=True)
        report['outer_independent_mirror_difference_mm3']=g13.difference(shapes['m'],shapes['p'].mirror('XZ'))
        if any(v>g11.TOL for v in report['outer_independent_mirror_difference_mm3'].values()):raise ValueError('outer mirror mismatch')
        accepted=[r for r in report['variants'] if not r['rejections']]
        for angle in report['crank_samples_deg']:
            moving=g11.moving_shapes(p,reference,angle)
            if set(moving)!=set(g11.moving_names(reference)):raise ValueError('moving coverage changed')
            for row in accepted:
                for name,part in moving.items():
                    if (v:=audit.overlap(shapes[row['component'][-1]],part))>g11.TOL:row['sampled_motion_interferences'].append(dict(crank_deg=angle,part=name,volume_mm3=v))
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
