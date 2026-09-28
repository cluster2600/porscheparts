"""Single private central hypothesis: shorten the w40 root transition to 2 mm."""
import argparse
import json
from pathlib import Path
import shutil
import signal
import time

import g14_central_followup_private as followup

previous=followup.previous
cq,g11,g13,g7,carrier,audit,assembly=followup.cq,followup.g11,followup.g13,followup.g7,followup.carrier,followup.audit,followup.assembly
ROOT=followup.ROOT
PRIOR=ROOT/'work/m64-g14/cad-central-v2'
PRIOR_SHA='853240d3f5eec4425940da2868b237637df3cc50bed6a339db62276fe2103f81'
FOLLOWUP_SHA='44c8dc5033d29416bc533afa3d5bedb27bee08531eaccaa234cc351f6cc1c9eb'
PROBE=ROOT/'work/m64-g14/fea/central-root-fields.json'
PROBE_SHA='9a5fe2259ef65544a148ebc99d5c613aa5a2a61c95fa2f4ac592b0dc35c89594'
IDENT='centre_spine68_t40_root2'


def inputs():
    for path,want in ((PRIOR/'receipt.json',PRIOR_SHA),(Path(followup.__file__),FOLLOWUP_SHA),(PROBE,PROBE_SHA)):
        if g11.sha256(path)!=want:raise ValueError('prior evidence or helper changed')
    old=json.loads((PRIOR/'receipt.json').read_text())
    if not old['complete'] or old['error'] is not None:raise ValueError('prior CAD incomplete')
    for name,want in old['frozen_sources_sha256'].items():
        if g11.sha256(ROOT/name)!=want:raise ValueError('frozen source changed')
    if g11.sha256(Path(previous.__file__))!=old['prior_private_source_sha256']:raise ValueError('original private helper changed')
    if g11.sha256(g11.BASELINE)!=old['G7_receipt_sha256']:raise ValueError('G7 receipt changed')
    prior=next(r for r in old['variants'] if r['id']=='centre_spine68_t40')
    path=PRIOR/prior['step']
    if not prior['cad_accepted'] or prior['motion_samples_checked']!=144 or g11.sha256(path)!=prior['step_sha256']:raise ValueError('width40 baseline not accepted')
    return old,prior,json.loads(g11.BASELINE.read_text())['values'],cq.importers.importStep(str(path)).val()


def reinforced(base,p):
    z0=p['carrier_face_height']
    profile=[(-5.5,z0+1),(5.5,z0+1),(20,z0+3),(20,z0+10),(-20,z0+10),(-20,z0+3)]
    wire=cq.Wire.makePolygon([cq.Vector(-34,y,z) for y,z in profile],close=True)
    addition=cq.Solid.extrudeLinear(wire,[],cq.Vector(68,0,0))
    # Fill only the lower transition; never subtract the baseline or moving shapes.
    for tool in list(followup.tools(p).values())+list(g11.oil_paths(p,'central_diaphragm').values()):addition=addition.cut(tool)
    return base.fuse(addition).clean()


def run(output):
    output.mkdir(parents=True,exist_ok=False);shutil.copyfile(__file__,output/Path(__file__).name)
    report=dict(classification='G14_central_root_transition_CAD_hypothesis_not_FEA',source_sha256=g11.sha256(Path(__file__)),
        prior_CAD_receipt_sha256=PRIOR_SHA,field_probe_sha256=PROBE_SHA,started_epoch=time.time(),complete=False,error=None,variants=[],
        FEA_executed=False,material_or_boundary_conditions_changed=False,manufacturing_authorized=False,engine_start_authorized=False,
        rationale='Distributed +x displacement observed in width40 frame motivates one shortened root transition, 9 to2mm, without altering the entire first millimetre or fixed land. Node samples do not partition compliance or energy; no gain or 0.040mm pass is predicted.',
        crank_samples_deg=list(range(0,720,5)),motion_scope='144 sampled rigid poses, not continuous or deformable validation',
        combined_modified_supports_clearance_qualified=False)
    try:
        old,prior,p,base=inputs();reference,_=g7.parts(p)
        report['values']=p;report['G7_receipt_sha256']=old['G7_receipt_sha256'];report['frozen_sources_sha256']=old['frozen_sources_sha256']
        report['private_helper_sha256']={Path(m.__file__).name:g11.sha256(Path(m.__file__)) for m in (followup,previous)}
        shape=reinforced(base,p);folder=output/IDENT;folder.mkdir()
        step=folder/'central_diaphragm.step';cq.exporters.export(cq.Workplane().add(shape),str(step))
        cq.exporters.export(cq.Workplane().add(shape),str(folder/'preview.svg'),opt={'projectionDir':(1,-1,-.8),'showHidden':False,'width':900,'height':600})
        section=shape.cut(cq.Solid.makeBox(1000,1000,1000,cq.Vector(0,-500,-500)))
        cq.exporters.export(cq.Workplane().add(section),str(folder/'section-x0.svg'),opt={'projectionDir':(1,0,0),'showHidden':False,'width':900,'height':600})
        envelope=g7.native_bounds(cq.Compound.makeCompound(list(reference.values())))
        bounds=g7.native_bounds(shape);void=audit.closed_voids(shape)
        slab=cq.Solid.makeBox(400,200,1,cq.Vector(-200,-100,p['carrier_face_height']))
        first=g13.difference(shape.intersect(slab),base.intersect(slab))
        land,meta=g13.support_land(shape,p);land0,meta0=g13.support_land(base,p)
        foot=g13.difference(land,land0);bands=previous.journal_masks(shape,base,p)
        oil={k:dict(residual_solid_mm3=audit.overlap(shape,t),tool_connected_solids=len(t.Solids())) for k,t in g11.oil_paths(p,'central_diaphragm').items()}
        new_material=shape.cut(base);removed=base.cut(shape).Volume()
        tool_checks={k:dict(new_material_overlap_mm3=audit.overlap(new_material,t),baseline_overlap_mm3=audit.overlap(base,t),total_overlap_mm3=audit.overlap(shape,t)) for k,t in followup.tools(p).items()}
        collisions=[dict(part=n,volume_mm3=v) for n,s in reference.items() if n!='central_diaphragm' and (v:=audit.overlap(shape,s))>g11.TOL]
        failures=[]
        if not assembly.brep_valid(shape) or len(shape.Solids())!=1:failures.append('invalid_or_disconnected_BRep')
        if not void['no_enclosed_void_detected']:failures.append('enclosed_void')
        if any(v>g11.TOL for d in [first,foot,*bands.values()] for v in d.values()) or abs(meta['bottom_planar_area_mm2']-meta0['bottom_planar_area_mm2'])>g11.TOL:failures.append('foot_or_journal_changed')
        if removed>g11.TOL:failures.append('baseline_material_removed')
        if any(v['residual_solid_mm3']>g11.TOL or v['tool_connected_solids']!=1 for v in oil.values()):failures.append('oil_path_changed')
        if any(v['new_material_overlap_mm3']>g11.TOL for v in tool_checks.values()):failures.append('new_material_obstructs_existing_tool')
        if any(bounds[k]<envelope[k]-1e-6 for k in ('xmin','ymin','zmin')) or any(bounds[k]>envelope[k]+1e-6 for k in ('xmax','ymax','zmax')):failures.append('outside_assembly_envelope')
        if collisions:failures.append('static_interference')
        row=dict(id=IDENT,component='central_diaphragm',parameters=dict(spine_span_mm=68,width_mm=40,first_unchanged_height_mm=1,transition_height_mm=2,prior_transition_height_mm=9),
            step=str(step.relative_to(output)),step_sha256=g11.sha256(step),baseline_step_sha256=prior['step_sha256'],journal_width_mm=11,journal_diameter_mm=12.58,
            volume_mm3=shape.Volume(),added_to_width40_volume_mm3=shape.Volume()-base.Volume(),added_fraction=(shape.Volume()-base.Volume())/base.Volume(),baseline_removed_volume_mm3=removed,
            BRep_valid=assembly.brep_valid(shape),solid_count=len(shape.Solids()),bounds_mm=bounds,closed_void_check=void,oil_paths=oil,first_1mm_difference_mm3=first,
            existing_functional_tool_checks=tool_checks,tool_scope='Existing central-mount pilots and actual fastener envelopes only; full tool approach and assembly sequence not qualified',
            bottom_land_difference=foot,support_land=meta,journal_neighbourhood_difference=bands,static_interferences=collisions,sampled_motion_interferences=[],motion_samples_checked=0,rejections=failures,cad_accepted=False,
            native_views={f.name:g11.sha256(f) for f in (folder/'preview.svg',folder/'section-x0.svg')},view_scope='Isolated support and section, no full head or stress field')
        report['variants'].append(row)
        print(json.dumps({'stage':'static','id':IDENT,'rejections':failures,'collisions':collisions,'added_volume_mm3':row['added_to_width40_volume_mm3']}),flush=True)
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
