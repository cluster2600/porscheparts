"""Assemble the two saved patches and preserve every raw native Boolean."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import sys
import time
import traceback


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.root.resolve();out=args.output.resolve()
    spec=importlib.util.spec_from_file_location('_saved_patch_helpers',Path(__file__).with_name('point_radius_trial.py'))
    helpers=importlib.util.module_from_spec(spec);spec.loader.exec_module(helpers)
    require,write,sha=helpers.require,helpers.write,helpers.sha
    require(not out.exists(),'Fresh output required');out.mkdir(parents=True)
    report=dict(status='incomplete',candidate_adopted=False,patches_regenerated=False,booleans=[])
    began=time.monotonic()
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('150 second inner limit')))
    signal.alarm(150);resource.setrlimit(resource.RLIMIT_CPU,(140,141))
    try:
        require(os.getpriority(os.PRIO_PROCESS,0)==10 and all(os.environ.get(k)=='1' for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']),'Original execution limits required')
        old=root/'work/carrier-process-20261017/bounded-webs-first-window-corner-slide-law-API-observer-preparation-001'
        p=json.loads((old/'plan.json').read_text());sys.path.insert(0,str(root/p['native_site']))
        from build123d import import_brep
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse,BRepAlgoAPI_Cut,BRepAlgoAPI_Common
        from OCP.BRepTools import BRepTools
        from OCP.TopTools import TopTools_ListOfShape,TopTools_IndexedMapOfShape
        from OCP.TopExp import TopExp
        from OCP import TopAbs
        from OCP.OSD import OSD_ThreadPool
        from OCP.BRepCheck import BRepCheck_Analyzer
        from OCP.BRepGProp import BRepGProp
        from OCP.GProp import GProp_GProps
        from OCP.Bnd import Bnd_Box
        from OCP.BRepBndLib import BRepBndLib
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
        from OCP.gp import gp_Ax2,gp_Pnt,gp_Dir
        OSD_ThreadPool.DefaultPool_s().Init(1)
        master=root/p['master_BREP'];require(sha(master)==helpers.MASTER,'Current baseline differs')
        body=import_brep(master).wrapped
        patch_folder=root/'work/carrier-resume-20261020/nurbs-root-patch-001/output'
        patch_record=json.loads((patch_folder/'assessment.json').read_text())
        require(len(patch_record['patches'])==2 and all(row['valid'] and row['solid_count']==1 for row in patch_record['patches']),'Saved patch validity differs')
        patches=[import_brep(patch_folder/f'patch-{i}.brep').wrapped for i in range(2)]
        report['input_hashes']={str(q.relative_to(root)):sha(q) for q in [master,patch_folder/'assessment.json',*[patch_folder/f'patch-{i}.brep' for i in range(2)]]}

        def summary(shape):
            counts={}
            for key in ['VERTEX','EDGE','WIRE','FACE','SHELL','SOLID','COMPSOLID']:
                mapping=TopTools_IndexedMapOfShape();TopExp.MapShapes_s(shape,getattr(TopAbs,'TopAbs_'+key),mapping)
                counts[key]=mapping.Extent()
            props=GProp_GProps();BRepGProp.VolumeProperties_s(shape,props)
            box=Bnd_Box();BRepBndLib.AddOptimal_s(shape,box,False,False)
            return dict(entity_counts=counts,topologically_empty=not any(counts.values()),valid=BRepCheck_Analyzer(shape).IsValid(),volume_mm3=props.Mass(),bounds_mm=None if box.IsVoid() else list(box.Get()))

        def boolean(cls,a,b,name):
            op=cls();arguments=TopTools_ListOfShape();tools=TopTools_ListOfShape()
            arguments.Append(a)
            for tool_shape in (b if isinstance(b,list) else [b]):tools.Append(tool_shape)
            op.SetArguments(arguments);op.SetTools(tools)
            op.SetNonDestructive(True);op.SetRunParallel(False);op.SetFuzzyValue(0.);op.Build()
            require(op.IsDone(),'Native Boolean failed: '+name)
            shape=op.Shape();path=out/(name+'.brep')
            BRepTools.Write_s(shape,str(path));require(path.is_file(),'Raw native result was not saved')
            row=dict(name=name,sha256=sha(path),HasErrors=op.HasErrors(),HasWarnings=op.HasWarnings(),**summary(shape));report['booleans'].append(row)
            write(out/'assessment-progress.json',report)
            return shape,row

        candidate,row=boolean(BRepAlgoAPI_Fuse,body,patches,'fuse-all')
        require(row['valid'] and row['entity_counts']['SOLID']==1 and not row['HasErrors'],'Whole simultaneous union did not produce one valid solid')
        BRepTools.Write_s(candidate,str(out/'candidate-native.brep'))
        report['candidate']=dict(sha256=sha(out/'candidate-native.brep'),**summary(candidate))
        report['candidate']['mass_kg']=report['candidate']['volume_mm3']*4420e-9
        _,retention=boolean(BRepAlgoAPI_Cut,body,candidate,'baseline-minus-candidate')
        _,addition=boolean(BRepAlgoAPI_Cut,candidate,body,'candidate-minus-baseline')
        contract=json.loads((root/p['interface_contract']).read_text())
        commons=[]
        for i,(x,y) in enumerate(contract['study_central_centres_xy_mm']):
            tool=BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(x,y,4.),gp_Dir(0,0,1)),12.5,40.).Shape()
            _,row=boolean(BRepAlgoAPI_Common,candidate,tool,f'tool-common-{i}')
            commons.append(row['topologically_empty'])
        report['checks']=dict(strict_all_dimensional_native_retention=retention['topologically_empty'],positive_added_solid=addition['entity_counts']['SOLID']>0,valid_single_solid=report['candidate']['valid'] and report['candidate']['entity_counts']['SOLID']==1,mass_below_1_30_kg=0<report['candidate']['mass_kg']<=1.3,original_four_tool_commons_empty=all(commons))
        report['status']='candidate_geometry_screen_passed' if all(report['checks'].values()) else 'candidate_geometry_screen_refused'
        report['pending']=['full protected-interface rosters','introduced seam and endcap continuity audit','fresh surface and T10 meshes','all20 mechanics and refined peak comparisons']
    except Exception as error:
        report['failure']=dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc())
    finally:
        signal.alarm(0);report['elapsed_seconds']=time.monotonic()-began;write(out/'assessment.json',report)
    print(json.dumps(dict(status=report['status'],assessment_sha256=sha(out/'assessment.json'))))
    return 0 if report['status'].startswith('candidate_geometry_screen_') else 1


if __name__=='__main__':
    raise SystemExit(main())
