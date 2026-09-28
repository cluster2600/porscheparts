"""One private central hypothesis: local caps above the protected journals."""
import argparse
import json
from pathlib import Path
import shutil
import signal
import time

import g14_central_root_private as root

cq,g11,g13,g7,carrier,audit,assembly=root.cq,root.g11,root.g13,root.g7,root.carrier,root.audit,root.assembly
ROOT=root.ROOT
PRIOR=ROOT/'work/m64-g14/cad-central-root-v1'
PRIOR_SHA='ec14ff714b2042b26941120d26d27e0288d7015f47265af250a30f8ba0324f01'
ROOT_SOURCE_SHA='fc634708cdf82a21232f60add7ffcf173b3f8c6d587c2a11c6fa87409fe21fbe'
PROBE=ROOT/'work/m64-g14/fea/central-ear-fields-v1.json'
PROBE_SHA='1ca2a24c6409a6d6e2c9a04113365a7ca5831e04d2551642638e0199f80e77ac'
IDENT='centre_spine68_t40_root2_upper_caps'


def inputs():
    for path,want in ((PRIOR/'receipt.json',PRIOR_SHA),(Path(root.__file__),ROOT_SOURCE_SHA),(PROBE,PROBE_SHA)):
        if g11.sha256(path)!=want:raise ValueError('prior evidence or helper changed')
    root.inputs()  # Recheck the unchanged width40 source and original chain.
    old=json.loads((PRIOR/'receipt.json').read_text())
    if not old['complete'] or old['error'] is not None:raise ValueError('prior CAD incomplete')
    if g11.sha256(PRIOR/Path(root.__file__).name)!=ROOT_SOURCE_SHA:raise ValueError('executed root source changed')
    prior=next(r for r in old['variants'] if r['id']==root.IDENT);path=PRIOR/prior['step']
    if not prior['cad_accepted'] or prior['motion_samples_checked']!=144 or g11.sha256(path)!=prior['step_sha256']:raise ValueError('root2 baseline not accepted')
    return old,prior,old['values'],cq.importers.importStep(str(path)).val()


def cap_boxes(p):
    boxes={}
    for side,(pivot,_) in carrier.axes(p).items():
        lo,hi=(pivot[0]-9,-31) if side=='intake' else (31,pivot[0]+9)
        boxes[side]=dict(x_mm=[lo,hi],y_mm=[-20,20],z_mm=[pivot[2]+8.5,pivot[2]+11.5])
    return boxes


def reinforced(base,p):
    pieces=[cq.Solid.makeBox(q['x_mm'][1]-q['x_mm'][0],40,3,cq.Vector(q['x_mm'][0],-20,q['z_mm'][0])) for q in cap_boxes(p).values()]
    addition=pieces[0].fuse(pieces[1])
    for tool in list(root.followup.tools(p).values())+list(g11.oil_paths(p,'central_diaphragm').values()):addition=addition.cut(tool)
    return base.fuse(addition).clean()


def run(output):
    output.mkdir(parents=True,exist_ok=False);shutil.copyfile(__file__,output/Path(__file__).name)
    report=dict(classification='G14_central_upper_caps_CAD_hypothesis_not_FEA',source_sha256=g11.sha256(Path(__file__)),
        prior_CAD_receipt_sha256=PRIOR_SHA,field_probe_sha256=PROBE_SHA,started_epoch=time.time(),complete=False,error=None,variants=[],
        FEA_executed=False,material_or_boundary_conditions_changed=False,manufacturing_authorized=False,engine_start_authorized=False,
        rationale='Node-sampled upper-ear Ux and Uz remain different from the spine after the root change. Test only two local upper caps outside the protected journal boxes, preserving the entire baseline. No energy partition or predicted 0.040mm pass.',
        crank_samples_deg=list(range(0,720,5)),motion_scope='144 sampled rigid poses only, not continuous or deformable clearance',combined_modified_supports_clearance_qualified=False)
    try:
        old,prior,p,base=inputs();reference,_=g7.parts(p)
        report['values']=p;report['G7_receipt_sha256']=old['G7_receipt_sha256'];report['frozen_sources_sha256']=old['frozen_sources_sha256']
        report['private_helper_sha256']={Path(m.__file__).name:g11.sha256(Path(m.__file__)) for m in (root,root.followup,root.previous)}
        shape=reinforced(base,p);folder=output/IDENT;folder.mkdir();step=folder/'central_diaphragm.step'
        cq.exporters.export(cq.Workplane().add(shape),str(step))
        cq.exporters.export(cq.Workplane().add(shape),str(folder/'preview.svg'),opt={'projectionDir':(1,-1,-.8),'showHidden':False,'width':900,'height':600})
        section=shape.cut(cq.Solid.makeBox(1000,1000,1000,cq.Vector(0,-500,-500)))
        cq.exporters.export(cq.Workplane().add(section),str(folder/'section-x0.svg'),opt={'projectionDir':(1,0,0),'showHidden':False,'width':900,'height':600})
        envelope=g7.native_bounds(cq.Compound.makeCompound(list(reference.values())));bounds=g7.native_bounds(shape);void=audit.closed_voids(shape)
        slab=cq.Solid.makeBox(400,200,1,cq.Vector(-200,-100,p['carrier_face_height']))
        first=g13.difference(shape.intersect(slab),base.intersect(slab));land,meta=g13.support_land(shape,p);land0,meta0=g13.support_land(base,p)
        foot=g13.difference(land,land0);bands=root.previous.journal_masks(shape,base,p)
        oil={k:dict(residual_solid_mm3=audit.overlap(shape,t),tool_connected_solids=len(t.Solids())) for k,t in g11.oil_paths(p,'central_diaphragm').items()}
        added=shape.cut(base);removed=base.cut(shape).Volume()
        tools={k:dict(new_material_overlap_mm3=audit.overlap(added,t),baseline_overlap_mm3=audit.overlap(base,t),total_overlap_mm3=audit.overlap(shape,t)) for k,t in root.followup.tools(p).items()}
        collisions=[dict(part=n,volume_mm3=v) for n,s in reference.items() if n!='central_diaphragm' and (v:=audit.overlap(shape,s))>g11.TOL]
        failures=[]
        if not assembly.brep_valid(shape) or len(shape.Solids())!=1:failures.append('invalid_or_disconnected_BRep')
        if not void['no_enclosed_void_detected']:failures.append('enclosed_void')
        if any(v>g11.TOL for d in [first,foot,*bands.values()] for v in d.values()) or abs(meta['bottom_planar_area_mm2']-meta0['bottom_planar_area_mm2'])>g11.TOL:failures.append('foot_or_journal_changed')
        if removed>g11.TOL:failures.append('baseline_material_removed')
        if any(v['residual_solid_mm3']>g11.TOL or v['tool_connected_solids']!=1 for v in oil.values()):failures.append('oil_path_changed')
        if any(v['new_material_overlap_mm3']>g11.TOL for v in tools.values()):failures.append('new_material_obstructs_existing_tool')
        if any(bounds[k]<envelope[k]-1e-6 for k in ('xmin','ymin','zmin')) or any(bounds[k]>envelope[k]+1e-6 for k in ('xmax','ymax','zmax')):failures.append('outside_assembly_envelope')
        if collisions:failures.append('static_interference')
        row=dict(id=IDENT,component='central_diaphragm',parameters=dict(cap_boxes=cap_boxes(p),spine_span_mm=68,width_mm=40,root_transition_mm=2),
            step=str(step.relative_to(output)),step_sha256=g11.sha256(step),baseline_step_sha256=prior['step_sha256'],journal_width_mm=11,journal_diameter_mm=12.58,
            volume_mm3=shape.Volume(),added_to_root2_volume_mm3=shape.Volume()-base.Volume(),added_fraction=(shape.Volume()-base.Volume())/base.Volume(),baseline_removed_volume_mm3=removed,
            BRep_valid=assembly.brep_valid(shape),solid_count=len(shape.Solids()),bounds_mm=bounds,closed_void_check=void,oil_paths=oil,first_1mm_difference_mm3=first,
            existing_functional_tool_checks=tools,tool_scope='Existing pilots and actual fastener envelopes only; no full tool approach or assembly-sequence qualification',
            bottom_land_difference=foot,support_land=meta,journal_neighbourhood_difference=bands,static_interferences=collisions,sampled_motion_interferences=[],motion_samples_checked=0,rejections=failures,cad_accepted=False,
            native_views={f.name:g11.sha256(f) for f in (folder/'preview.svg',folder/'section-x0.svg')},view_scope='Isolated support BRep and section, not full head or stress map')
        report['variants'].append(row)
        print(json.dumps({'stage':'static','id':IDENT,'rejections':failures,'collisions':collisions,'added_volume_mm3':row['added_to_root2_volume_mm3']}),flush=True)
        if not failures:
            for angle in report['crank_samples_deg']:
                moving=g11.moving_shapes(p,reference,angle)
                if set(moving)!=set(g11.moving_names(reference)):raise ValueError('moving coverage changed')
                for name,part in moving.items():
                    if (v:=audit.overlap(shape,part))>g11.TOL:row['sampled_motion_interferences'].append(dict(crank_deg=angle,part=name,volume_mm3=v))
                row['motion_samples_checked']+=1
                if angle%60==0:
                    with (output/f'checkpoint-{angle:03d}.json').open('x') as f:json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
                    print(json.dumps({'stage':'motion','crank_deg':angle}),flush=True)
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
