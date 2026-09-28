"""One private outer CAD hypothesis: shorten the existing lower haunch to 2 mm."""
import argparse
import json
from pathlib import Path
import shutil
import signal
import time

import g14_extended_haunch_private as extended

lower,previous=extended.lower,extended.previous
cq,g11,g13,g7,carrier,audit,assembly=extended.cq,extended.g11,extended.g13,extended.g7,extended.carrier,extended.audit,extended.assembly
ROOT=extended.ROOT
PRIOR=ROOT/'work/m64-g14/cad-extended-v1'
PRIOR_SHA='f495427952c68eefd8b31c1a0b43a32a83515fbb8acf334ad70674d093ea97e6'
EXTENDED_SHA='f97eb345ec66a5d6de36db078dbfdf0df2ce8401f803dc272b5716037886dded'
PROBE=ROOT/'work/m64-g14/outer-root-fields.json'
PROBE_SHA='b8975869616beff230730efc19ddf4e69f2313bbb9e9a3e4ba0118b36ca14c00'


def inputs():
    for path,want in ((PRIOR/'receipt.json',PRIOR_SHA),(Path(extended.__file__),EXTENDED_SHA),(PROBE,PROBE_SHA)):
        if g11.sha256(path)!=want:raise ValueError('prior evidence or helper changed')
    old=json.loads((PRIOR/'receipt.json').read_text())
    if not old['complete'] or old['error'] is not None:raise ValueError('extended CAD incomplete')
    if old['source_sha256']!=EXTENDED_SHA:raise ValueError('extended source identity changed')
    _,original,p=extended.inputs()
    for name,want in old['frozen_sources_sha256'].items():
        if g11.sha256(ROOT/name)!=want:raise ValueError('frozen source changed')
    for name,want in old['private_helper_sha256'].items():
        if g11.sha256(Path(__file__).parent/name)!=want:raise ValueError('private helper changed')
    for name,want in json.loads(PROBE.read_text())['input_files_sha256'].items():
        if g11.sha256(ROOT/name)!=want:raise ValueError('observed field changed')
    if {r['id'] for r in old['variants']}!={'outer_high_cheeks_extended_haunch_p','outer_high_cheeks_extended_haunch_m'}:raise ValueError('unexpected prior variants')
    if not all(r['cad_accepted'] and r['motion_samples_checked']==144 and not r['rejections'] for r in old['variants']):raise ValueError('prior geometry not accepted')
    return old,original,p


def reinforced(base,p,sy):
    z0=p['carrier_face_height'];pieces=[]
    for side,(_,cam) in carrier.axes(p).items():
        lo,hi=(cam[0]-20,-32) if side=='intake' else (32,cam[0]+20)
        front=p[side+'_valve_y']+p['spring_outer_diameter']/2+1
        # The existing zero-width root at z0+1 is retained. Full forward depth
        # is reached at z0+3, then retained to108; only new material is added.
        profile=[(45,z0+1),(45,108),(front,108),(front,z0+3)]
        wire=cq.Wire.makePolygon([cq.Vector(lo,sy*y,z) for y,z in profile],close=True)
        pieces.append(cq.Solid.extrudeLinear(wire,[],cq.Vector(hi-lo,0,0)))
    addition=pieces[0].fuse(pieces[1])
    for tool in lower.functional_tools(p,sy).values():addition=addition.cut(tool)
    for tool in g11.oil_paths(p,'carrier_base_p').values():
        addition=addition.cut(tool if sy==1 else tool.mirror('XZ'))
    return base.fuse(addition).clean()


def run(output):
    output.mkdir(parents=True,exist_ok=False);shutil.copyfile(__file__,output/Path(__file__).name)
    report=dict(classification='G14_outer_root_transition_CAD_hypothesis_not_FEA',source_sha256=g11.sha256(Path(__file__)),
        prior_CAD_receipt_sha256=PRIOR_SHA,field_probe_sha256=PROBE_SHA,started_epoch=time.time(),complete=False,error=None,variants=[],
        FEA_executed=False,material_or_boundary_conditions_changed=False,manufacturing_authorized=False,engine_start_authorized=False,
        rationale='Node-sampled minus-z Uy remains shared by frame and local journal region. Shorten existing lower forward haunch transition to2mm, preserving first1mm and land. No compliance or energy partition and no predicted gain or 0.040mm pass.',
        crank_samples_deg=list(range(0,720,5)),motion_scope='144 sampled rigid poses only; no continuous or deformable clearance qualification',
        combined_modified_supports_clearance_qualified=False)
    try:
        old,original,p=inputs();reference,_=g7.parts(p)
        report['values']=p;report['G7_receipt_sha256']=original['G7_receipt_sha256'];report['frozen_sources_sha256']=original['frozen_sources_sha256']
        report['private_helper_sha256']={Path(m.__file__).name:g11.sha256(Path(m.__file__)) for m in (extended,lower,previous)}
        envelope=g7.native_bounds(cq.Compound.makeCompound(list(reference.values())))
        shapes={}
        for tag,sy in (('p',1),('m',-1)):
            prior=next(r for r in old['variants'] if r['id']=='outer_high_cheeks_extended_haunch_'+tag)
            step=PRIOR/prior['step']
            if g11.sha256(step)!=prior['step_sha256']:raise ValueError('prior STEP changed')
            base=cq.importers.importStep(str(step)).val();shape=reinforced(base,p,sy)
            ident='outer_high_cheeks_extended_root2_'+tag;folder=output/ident;folder.mkdir()
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
            new_material=shape.cut(base);removed=base.cut(shape).Volume()
            tool_checks={k:dict(new_material_overlap_mm3=audit.overlap(new_material,t),baseline_overlap_mm3=audit.overlap(base,t),total_overlap_mm3=audit.overlap(shape,t)) for k,t in lower.functional_tools(p,sy).items()}
            collisions=[dict(part=n,volume_mm3=v) for n,s in reference.items() if n!='carrier_base_'+tag and (v:=audit.overlap(shape,s))>g11.TOL]
            failures=[]
            if not assembly.brep_valid(shape) or len(shape.Solids())!=1:failures.append('invalid_or_disconnected_BRep')
            if not void['no_enclosed_void_detected']:failures.append('enclosed_void')
            if any(v>g11.TOL for d in [first,foot,*bands.values()] for v in d.values()) or abs(meta['bottom_planar_area_mm2']-meta0['bottom_planar_area_mm2'])>g11.TOL:failures.append('foot_or_journal_changed')
            if removed>g11.TOL:failures.append('baseline_material_removed')
            if any(v['residual_solid_mm3']>g11.TOL or v['tool_connected_solids']!=1 for v in oil.values()):failures.append('oil_path_changed')
            if any(v['new_material_overlap_mm3']>g11.TOL for v in tool_checks.values()):failures.append('new_material_obstructs_existing_tool')
            if any(bounds[k]<envelope[k]-1e-6 for k in ('xmin','ymin','zmin')) or any(bounds[k]>envelope[k]+1e-6 for k in ('xmax','ymax','zmax')):failures.append('outside_assembly_envelope')
            if collisions:failures.append('static_interference')
            row=dict(id=ident,component='carrier_base_'+tag,step=str(path.relative_to(output)),step_sha256=g11.sha256(path),baseline_step_sha256=prior['step_sha256'],
                parameters=dict(first_unchanged_height_mm=1,transition_height_mm=2,prior_transition_height_mm=108-p['carrier_face_height']-1,
                    full_width_z_mm=[p['carrier_face_height']+3,108],unchanged_extension_z_mm=[108,137],
                    front_y_absolute_mm={s:p[s+'_valve_y']+p['spring_outer_diameter']/2+1 for s in ('intake','exhaust')},back_y_absolute_mm=45,
                    extension_x_mm={s:[cam[0]-20,-32] if s=='intake' else [32,cam[0]+20] for s,(_,cam) in carrier.axes(p).items()}),
                journal_width_mm=8,journal_diameter_mm=12.58,volume_mm3=shape.Volume(),added_to_extended_volume_mm3=shape.Volume()-base.Volume(),added_fraction=(shape.Volume()-base.Volume())/base.Volume(),baseline_removed_volume_mm3=removed,
                BRep_valid=assembly.brep_valid(shape),solid_count=len(shape.Solids()),bounds_mm=bounds,closed_void_check=void,oil_paths=oil,first_1mm_difference_mm3=first,
                existing_functional_tool_checks=tool_checks,tool_scope='Original finite tool definitions preserved; inherited baseline obstructions, full tool approach and maintenance sequence remain unqualified',
                bottom_land_difference=foot,support_land=meta,journal_neighbourhood_difference=bands,static_interferences=collisions,sampled_motion_interferences=[],motion_samples_checked=0,rejections=failures,cad_accepted=False,
                native_views={f.name:g11.sha256(f) for f in (folder/'preview.svg',folder/'section-x0.svg')},view_scope='Isolated support and section, no full head or stress field')
            report['variants'].append(row);shapes[tag]=shape
            print(json.dumps({'stage':'static','id':ident,'rejections':failures,'collisions':collisions,'added_volume_mm3':row['added_to_extended_volume_mm3']}),flush=True)
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
