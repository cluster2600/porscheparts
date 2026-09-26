"""Private bounded G14 CAD hypotheses; no FEA or manufacture qualification."""
import argparse
import json
from pathlib import Path
import signal
import shutil
import sys
import time

REPO=Path(__file__).resolve().parents[2]
HERE=REPO/'twins/m64-cylinder-head/source/fourvalve'
sys.path[:0]=[str(HERE),str(HERE/'cad')]
import cadquery as cq
import assembly
import audit_g6 as audit
import carrier
import g7
import g11_cad as g11
import g13_cad as g13
from cadcommon import _cyl


def central(p,base,span,shoulder):
    axes=carrier.axes(p);z0=p['carrier_face_height']
    top=max(v[0][2] for v in axes.values())+9
    row=next(r for r in g13.candidates() if r['parameters']['spine_width_mm']==30)
    profile=g13.spine_profile(row,top-z0)
    wire=cq.Wire.makePolygon([cq.Vector(-span/2,y,z0+z) for y,z in profile],close=True)
    add=cq.Solid.extrudeLinear(wire,[],cq.Vector(span,0,0))
    if shoulder:
        # Explicit construction taper, never a subtraction of moving-part envelopes.
        points=[(-35,z0),(35,z0),(35,140),(30,143),(30,top),(-30,top),(-30,143),(-35,140)]
        clip=cq.Wire.makePolygon([cq.Vector(x,-16,z) for x,z in points],close=True)
        add=add.intersect(cq.Solid.extrudeLinear(clip,[],cq.Vector(0,32,0)))
    shape=base.fuse(add)
    for x in (-p['carrier_mount_x'],p['carrier_mount_x']):
        shape=shape.cut(_cyl([x,0,z0-1],[x,0,top+1],3.3))
    for tool in g11.oil_paths(p,'central_diaphragm').values():shape=shape.cut(tool)
    return shape.clean()


def outer(p,base,sy):
    pieces=[];tools=[]
    for side,(pivot,cam) in carrier.axes(p).items():
        x,z=pivot[0],pivot[2];y=g7.support_positions(p,side)
        lo,hi=sorted((sy*(y-4),sy*p['carrier_end_y']))
        top=min(z+9,cam[2]-.5)
        for dx in (-15,7.5):
            pieces.append(cq.Solid.makeBox(7.5,hi-lo,top-138,cq.Vector(x+dx,lo,138)))
        # Exact existing cap-bolt pilot tools from carrier.parts, not new holes.
        for dx in (-15,15):
            bx=cam[0]+dx
            tools.append(_cyl([bx,sy*p['carrier_end_y'],cam[2]-12],
                             [bx,sy*p['carrier_end_y'],cam[2]+14],2.5))
    for x in (-p['carrier_mount_x'],p['carrier_mount_x']):
        y=sy*p['carrier_end_y'];z=p['carrier_face_height']
        tools.append(_cyl([x,y,z+p['carrier_foot_height']],[x,y,z+120],7))
    addition=pieces[0].fuse(*pieces[1:])
    for tool in tools:addition=addition.cut(tool)
    for tool in g11.oil_paths(p,'carrier_base_p').values():
        addition=addition.cut(tool if sy==1 else tool.mirror('XZ'))
    return base.fuse(addition).clean()


def journal_masks(shape,base,p):
    # Broader than the old 8-mm band: preserve the full through-axis neighbourhood.
    r=p['rocker_pivot_radius']+p['carrier_journal_radial_clearance']+1
    out={}
    for side,(pivot,_) in carrier.axes(p).items():
        box=cq.Solid.makeBox(2*r,140,2*r,cq.Vector(pivot[0]-r,-70,pivot[2]-r))
        out[side]=g13.difference(shape.intersect(box),base.intersect(box))
    return out


def run(output):
    started=time.time();output.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(__file__,output/'g14_cad_private.py')
    report=dict(classification='G14_private_geometric_hypotheses_not_stiffness_results',
        complete=False,FEA_executed=False,manufacturing_authorized=False,engine_start_authorized=False,
        source_sha256=g11.sha256(Path(__file__)),started_epoch=started,deadline_epoch=started+1800,
        variants=[],crank_samples_deg=list(range(0,720,5)),error=None,
        motion_scope='144 sampled rigid poses of 27 existing moving components, not continuous/deformable validation')
    sequence=0
    def save():
        nonlocal sequence
        sequence+=1
        with (output/f'checkpoint-{sequence:03d}.json').open('x') as f:
            json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
    try:
        baseline=json.loads(g11.BASELINE.read_text())
        old=json.loads((REPO/'twins/m64-cylinder-head/evidence/g13-support-reference-20260926/cad.json').read_text())
        for module,want in ((g11,old['g11_source_sha256']),(g13,old['source_sha256'])):
            if g11.sha256(Path(module.__file__))!=want:raise ValueError('frozen CAD source mismatch')
        for name,want in baseline['source_sha256'].items():
            if g11.sha256(REPO/name)!=want:raise ValueError('frozen G7 source mismatch')
        report['frozen_sources_sha256']=dict(baseline['source_sha256'],**{str(Path(m.__file__).relative_to(REPO)):g11.sha256(Path(m.__file__)) for m in (g11,g13)})
        report['G7_receipt_sha256']=g11.sha256(g11.BASELINE)
        p=baseline['values'];reference,_=g7.parts(p)
        if abs(reference['head'].Volume()-baseline['head_volume_mm3'])>.01:raise ValueError('head replay changed')
        centre=g11.candidate_shape(next(r for r in g11.candidates() if r['id']=='centre_w11'),p,reference)
        outer_p,outer_m=g13.outer_mirror_shapes(p,reference)
        envelope=g7.native_bounds(cq.Compound.makeCompound(list(reference.values())))
        specs=[('centre_spine70_t30','central_diaphragm',central(p,centre,70,False),centre,
                dict(span_mm=70,width_mm=30,shoulder=False)),
               ('centre_spine68_t30','central_diaphragm',central(p,centre,68,False),centre,
                dict(span_mm=68,width_mm=30,shoulder=False)),
               ('centre_spine70_shoulder_t30','central_diaphragm',central(p,centre,70,True),centre,
                dict(span_mm=70,width_mm=30,shoulder=True,shoulder_z_mm=[140,143],upper_span_mm=60)),
               ('outer_high_cheeks_p','carrier_base_p',outer(p,outer_p,1),outer_p,
                dict(cheek_offset_from_axis_mm=[7.5,15],bottom_z_mm=138,top_below_cam_cap_mm=.5,journal_width_mm=8)),
               ('outer_high_cheeks_m','carrier_base_m',outer(p,outer_m,-1),outer_m,
                dict(cheek_offset_from_axis_mm=[7.5,15],bottom_z_mm=138,top_below_cam_cap_mm=.5,journal_width_mm=8))]
        shapes={}
        for ident,component,shape,base,params in specs:
            folder=output/ident;folder.mkdir();step=folder/(component+'.step')
            cq.exporters.export(cq.Workplane().add(shape),str(step))
            cq.exporters.export(cq.Workplane().add(shape),str(folder/'preview.svg'),opt={'projectionDir':(1,-1,-.8),'showHidden':False,'width':900,'height':600})
            section=shape.cut(cq.Solid.makeBox(1000,1000,1000,cq.Vector(0,-500,-500)))
            cq.exporters.export(cq.Workplane().add(section),str(folder/'section-x0.svg'),opt={'projectionDir':(1,0,0),'showHidden':False,'width':900,'height':600})
            bounds=g7.native_bounds(shape);void=audit.closed_voids(shape)
            land,meta=g13.support_land(shape,p);land0,meta0=g13.support_land(base,p)
            bands=journal_masks(shape,base,p);delta=g13.difference(land,land0)
            tools=g11.oil_paths(p,'central_diaphragm' if component=='central_diaphragm' else 'carrier_base_p')
            if component=='carrier_base_m':tools={k:t.mirror('XZ') for k,t in tools.items()}
            oil={k:dict(residual_solid_mm3=audit.overlap(shape,t),tool_connected_solids=len(t.Solids())) for k,t in tools.items()}
            collisions=[dict(part=n,volume_mm3=v) for n,s in reference.items() if n!=component and (v:=audit.overlap(shape,s))>g11.TOL]
            failures=[]
            if not assembly.brep_valid(shape) or len(shape.Solids())!=1:failures.append('invalid_or_disconnected_BRep')
            if not void['no_enclosed_void_detected']:failures.append('enclosed_void')
            if any(v>g11.TOL for d in [delta,*bands.values()] for v in d.values()) or abs(meta['bottom_planar_area_mm2']-meta0['bottom_planar_area_mm2'])>g11.TOL:failures.append('fixed_land_or_journal_changed')
            if any(v['residual_solid_mm3']>g11.TOL or v['tool_connected_solids']!=1 for v in oil.values()):failures.append('oil_path_changed')
            if base.cut(shape).Volume()>g11.TOL:failures.append('baseline_material_removed')
            if any(bounds[k]<envelope[k]-1e-6 for k in ('xmin','ymin','zmin')) or any(bounds[k]>envelope[k]+1e-6 for k in ('xmax','ymax','zmax')):failures.append('assembly_envelope_changed')
            if collisions:failures.append('static_interference')
            row=dict(id=ident,component=component,parameters=params,step=str(step.relative_to(output)),step_sha256=g11.sha256(step),
                volume_mm3=shape.Volume(),added_volume_mm3=shape.Volume()-base.Volume(),BRep_valid=assembly.brep_valid(shape),solid_count=len(shape.Solids()),
                native_views={f.name:g11.sha256(f) for f in (folder/'preview.svg',folder/'section-x0.svg')},view_scope='Isolated support BRep and x=0 section; no full cylinder head or simulated stress map',
                bounds_mm=bounds,closed_void_check=void,oil_paths=oil,bottom_land_difference=delta,support_land=meta,journal_neighbourhood_difference=bands,
                static_interferences=collisions,motion_samples_checked=0,sampled_motion_interferences=[],rejections=failures,cad_accepted=False)
            report['variants'].append(row);shapes[ident]=shape;save()
            print(json.dumps({'stage':'static','id':ident,'rejections':failures,'collisions':collisions,'added_volume_mm3':row['added_volume_mm3']}),flush=True)
        report['outer_independent_mirror_difference_mm3']=g13.difference(shapes['outer_high_cheeks_m'],shapes['outer_high_cheeks_p'].mirror('XZ'))
        if any(v>g11.TOL for v in report['outer_independent_mirror_difference_mm3'].values()):raise ValueError('independent outer mirror mismatch')
        accepted=[r for r in report['variants'] if not r['rejections']]
        for angle in report['crank_samples_deg']:
            moving=g11.moving_shapes(p,reference,angle)
            if set(moving)!=set(g11.moving_names(reference)):raise ValueError('moving component coverage changed')
            for row in accepted:
                for name,part in moving.items():
                    if (v:=audit.overlap(shapes[row['id']],part))>g11.TOL:row['sampled_motion_interferences'].append(dict(crank_deg=angle,part=name,volume_mm3=v))
                row['motion_samples_checked']+=1
            if angle%60==0:save();print(json.dumps({'stage':'motion','crank_deg':angle}),flush=True)
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
    def interrupted(signum,frame):raise TimeoutError('private CAD 30-minute limit reached or interrupted')
    signal.signal(signal.SIGALRM,interrupted);signal.signal(signal.SIGTERM,interrupted);signal.alarm(1800)
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    raise SystemExit(run(parser.parse_args().output))
