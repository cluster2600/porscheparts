"""Attempt one predeclared local R1mm concave blend on the retained contour-2."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

SOURCE=Path(__file__).resolve().parent
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(base,output):
    from OCP.OSD import OSD_ThreadPool
    OSD_ThreadPool.DefaultPool_s().Init(1)
    from build123d import import_step,export_step,export_stl,export_brep,fillet,Pos,Box
    sys.path.insert(0,str(SOURCE.parent.parent/'bionic-20261011/correction-20261013'))
    from corrected_cad import precise_volume
    base,output=Path(base),Path(output)
    assert not output.exists();plan=json.loads((SOURCE/'plan.json').read_text())
    assert sha(base/'carrier.step')==plan['base_STEP_sha256']
    output.mkdir();(output/'construction-plan.json').write_bytes((SOURCE/'plan.json').read_bytes())
    (output/'source-snapshot.py').write_bytes(Path(__file__).read_bytes())
    settings=json.loads((base/'study.json').read_text())
    body=import_step(base/'carrier.step');original=body;all_edges=list(body.edges())
    chosen=[]
    for rule in plan['selected_edges']:
        edge=all_edges[rule['edge_index_zero_based']]
        assert abs(edge.length-rule['edge_length_mm'])<1e-7
        assert max(abs(a-b) for a,b in zip(edge.center(),rule['edge_centre_mm']))<1e-7
        chosen.append(edge)
    assert len(chosen)==plan['selected_edge_count']==2
    original_volume,_=precise_volume(original)
    try:
        # One simultaneous fixed-radius attempt. No radius search or repair.
        body=fillet(chosen,plan['radius_mm'])
        assert body.is_valid and len(body.solids())==1
        volume,error=precise_volume(body)
        removed=original-body;added=body-original
        removed_volume=abs(precise_volume(removed)[0]) if removed is not None else 0
        added_volume=abs(precise_volume(added)[0]) if added is not None else 0
        assert removed_volume<=plan['required_removed_reference_volume_mm3_max'],removed_volume
        assert added_volume>0
        pad=Pos(0,0,0)*Box(130,72,8)
        before_pad,after_pad=original&pad,body&pad
        differences=[before_pad-after_pad,after_pad-before_pad]
        pad_difference=sum(abs(precise_volume(s)[0]) if s is not None else 0 for s in differences)
        assert pad_difference<=plan['required_pad_difference_mm3_max'],pad_difference
        mass=volume*settings['material']['density_tonne_mm3']*1000
        assert mass<=plan['mass_ceiling_kg']
        box=body.bounding_box()
        for actual,expected in zip(list(box.min)+list(box.max),[-296,-36.5,-22,296,36.5,30]):
            assert abs(actual-expected)<1e-6
        addition_bounds=added.bounding_box()
        assert addition_bounds.min.X>=-105.001 and addition_bounds.max.X<=105.001
        assert addition_bounds.min.Y>=8 and addition_bounds.max.Y<=28
        assert addition_bounds.min.Z>=10 and addition_bounds.max.Z<=24
        export_brep(body,output/'native-body.brep')
        export_step(body,output/'carrier.step')
        export_stl(body,output/'carrier.stl',tolerance=.06,angular_tolerance=.10)
        reread=import_step(output/'carrier.step');read_volume,read_error=precise_volume(reread)
        assert reread.is_valid and len(reread.solids())==1
        assert abs(read_volume/volume-1)<=plan['required_STEP_relative_volume_difference_max']
        settings['design_id']=plan['design_id'];settings['local_root_fillet']=plan
        (output/'study.json').write_text(json.dumps(settings,indent=2)+'\n')
        receipt={'design_id':plan['design_id'],'base_STEP_sha256':sha(base/'carrier.step'),
          'source_sha256':sha(__file__),'plan_sha256':sha(SOURCE/'plan.json'),
          'CAD_valid':True,'solid_count':1,'radius_mm':plan['radius_mm'],'selected_edges':plan['selected_edges'],
          'volume_mm3':volume,'readback_volume_mm3':read_volume,'dense_reference_mass_kg':mass,
          'added_volume_mm3':added_volume,'removed_volume_mm3':removed_volume,
          'central_pad_symmetric_difference_mm3':pad_difference,
          'STEP_readback_relative_volume_difference':read_volume/volume-1,
          'integration_errors':[error,read_error],'bounds_mm':[list(box.min),list(box.max)],
          'addition_bounds_mm':[list(addition_bounds.min),list(addition_bounds.max)],
          'declared_mass_ceiling_kg':plan['mass_ceiling_kg'],'mass_ceiling_pass':mass<=plan['mass_ceiling_kg'],
          'geometry_sha256':{n:sha(output/n) for n in ('carrier.step','carrier.stl')},
          'mechanics_evaluated':False}
        (output/'geometry.json').write_text(json.dumps(receipt,indent=2)+'\n')
        print(json.dumps(receipt),flush=True);return receipt
    except BaseException as error:
        failure={'status':'rejected','error_type':type(error).__name__,'reason':str(error),
          'source_sha256':sha(__file__),'plan_sha256':sha(SOURCE/'plan.json'),
          'base_STEP_sha256':sha(base/'carrier.step'),'radius_mm':plan['radius_mm'],
          'further_radius_attempts':0}
        (output/'rejection.json').write_text(json.dumps(failure,indent=2)+'\n')
        print(json.dumps(failure),flush=True);raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();build(args.base,args.output)
