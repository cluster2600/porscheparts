"""Round the window/rib XY corner before extrusion; add only the upper skin."""
import argparse,hashlib,importlib.util,json,sys
from pathlib import Path

SOURCE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def corner_faces(settings,sx):
    import numpy as np
    from build123d import Edge,Wire,Face,Polygon,fillet
    r2=load_module('r2',SOURCE.parent/'reinforcement-2/build.py')
    plan=json.loads((SOURCE.parent/'reinforcement-2/plan.json').read_text())
    c=r2.elevated(plan['root_centreline_XY_mm']);w=r2.width_controls(2.8,6.)
    lower=[(sx*x,y-a/2) for (x,y),a in zip(c,w)]
    upper=[(sx*x,y+a/2) for (x,y),a in zip(c,w)]
    rib=Face(Wire([Edge.make_bezier(*lower),Edge.make_line(lower[-1],upper[-1]),
                   Edge.make_bezier(*upper[::-1]),Edge.make_line(upper[0],lower[0])]))
    g=settings['geometry'];points=np.array([[78,-25],[146,-20],[80,24]],float)
    centre=points.mean(axis=0);points=centre+g['window_scale']*(points-centre);points[:,0]*=sx
    triangle=Polygon(*(tuple(map(float,p)) for p in points),align=None)
    rounded=fillet(triangle.vertices(),6*g['window_scale']).faces()[0]
    window=Face(rounded.outer_wire().offset_2d(-g['window_edge_inset_mm']))
    mask=Polygon(*[(sx*x,y) for x,y in [(80,0),(110,0),(110,30),(80,30)]],align=None).faces()[0]
    old=((mask-window)+rib).faces()[0]
    corner=[sx*88.3799750736328,14.770923242430644,0.]
    vertex=min(old.vertices(),key=lambda v: np.linalg.norm(np.array(tuple(v))-corner))
    assert np.linalg.norm(np.array(tuple(vertex))-corner)<1e-7
    new=old.fillet_2d(1.,[vertex]);assert new.is_valid
    removed=old-new;assert abs(removed.area)<1e-8
    addition=new-old;assert addition.is_valid and addition.area>0
    return old,new,addition

def build(base,output):
    from OCP.OSD import OSD_ThreadPool
    OSD_ThreadPool.DefaultPool_s().Init(1)
    from build123d import import_step,export_step,export_brep,Pos,extrude,Box
    sys.path.insert(0,str(SOURCE.parent.parent/'bionic-20261011/correction-20261013'))
    from corrected_cad import precise_volume
    baseline_builder=load_module('frozen_arch',SOURCE.parent/'normal-builder/cad.py')
    plan=json.loads((SOURCE/'plan.json').read_text())
    assert sha(base/'carrier.step')==plan['base_STEP_sha256']
    assert sha(SOURCE.parent/'reinforcement-2/plan.json')==plan['root_rib_plan_sha256']
    assert not output.exists();output.mkdir(parents=True)
    (output/'source-snapshot.py').write_bytes(Path(__file__).read_bytes())
    (output/'construction-plan.json').write_bytes((SOURCE/'plan.json').read_bytes())
    settings=json.loads((base/'study.json').read_text());body=import_step(base/'carrier.step');original=body
    g=settings['geometry'];assert g['arm_shell']['cap_mm']==1.5 and g['arm_shell']['depth_mm']==44
    outer=baseline_builder.arm_envelope(44,8)
    cores=baseline_builder.arm_envelope(41,0,end=268)
    skins=(outer-cores[0]-cores[1])&(Pos(0,0,17)*Box(600,200,26))
    reports=[]
    try:
        for sx in plan['mirror_X']:
            old,new,addition=corner_faces(settings,sx)
            export_brep(old,output/f'reference-XY-X{sx}.brep');export_brep(new,output/f'rounded-XY-X{sx}.brep')
            # Intersect with the same analytical skins before adding to the
            # carrier. The core remains empty; no new vertical lamella exists.
            cap_addition=(Pos(0,0,-44)*extrude(addition,amount=88,dir=(0,0,1)))&skins
            assert cap_addition is not None and cap_addition.is_valid
            export_brep(cap_addition,output/f'cap-addition-X{sx}.brep')
            before=precise_volume(body)[0];body=body+cap_addition
            assert body.is_valid and len(body.solids())==1
            reports.append({'mirror_X':sx,'XY_added_area_mm2':addition.area,
                            'clipped_cap_addition_mm3':precise_volume(cap_addition)[0],
                            'actual_added_volume_mm3':precise_volume(body)[0]-before,
                            'cap_addition_bounds_mm':[[list(s.bounding_box().min),list(s.bounding_box().max)] for s in cap_addition.solids()]})
        removed=original-body;removed_volume=abs(precise_volume(removed)[0]) if removed is not None else 0
        assert removed_volume<=plan['removed_reference_volume_mm3_max']
        pad=Box(130,72,8);a,b=original&pad,body&pad
        pad_difference=sum(abs(precise_volume(s)[0]) if s is not None else 0 for s in (a-b,b-a))
        assert pad_difference<=plan['protected_pad_difference_mm3_max']
        volume,error=precise_volume(body);mass=volume*settings['material']['density_tonne_mm3']*1000
        assert mass<=plan['mass_ceiling_kg']
        export_step(body,output/'carrier.step');export_brep(body,output/'native-body.brep')
        reread=import_step(output/'carrier.step');read_volume,read_error=precise_volume(reread)
        assert reread.is_valid and len(reread.solids())==1
        assert abs(read_volume/volume-1)<=plan['native_and_STEP_relative_volume_difference_max']
        settings['design_id']=plan['design_id'];settings['rounded_window_corner']=plan
        (output/'study.json').write_text(json.dumps(settings,indent=2)+'\n')
        receipt={'design_id':plan['design_id'],'status':'intermediate_geometry_only','base_STEP_sha256':sha(base/'carrier.step'),
          'generator_sha256':sha(__file__),'plan_sha256':sha(SOURCE/'plan.json'),'mass_kg':mass,
          'volume_mm3':volume,'readback_volume_mm3':read_volume,'integration_errors':[error,read_error],
          'removed_reference_volume_mm3':removed_volume,'protected_pad_difference_mm3':pad_difference,
          'native_and_STEP_relative_volume_difference':read_volume/volume-1,'caps':reports,
          'geometry_sha256':{'carrier.step':sha(output/'carrier.step')},
          'junction_audit_complete':False,'mechanics_evaluated':False}
        (output/'geometry.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
    except BaseException as error:
        (output/'rejection.json').write_text(json.dumps({'status':'rejected','error_type':type(error).__name__,
             'reason':str(error),'completed_caps':reports},indent=2)+'\n');raise

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('base',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();build(a.base,a.output)
