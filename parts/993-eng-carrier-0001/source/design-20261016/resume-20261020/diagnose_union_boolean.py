"""Native classifier and self/copy Cut controls for the saved union refusal."""
import argparse
import importlib.util
import json
from pathlib import Path
import resource
import signal
import sys
import traceback


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.root.resolve();out=args.output.resolve()
    spec=importlib.util.spec_from_file_location('_boolean_control_helpers',Path(__file__).with_name('point_radius_trial.py'))
    helpers=importlib.util.module_from_spec(spec);spec.loader.exec_module(helpers)
    require,write,sha=helpers.require,helpers.write,helpers.sha
    require(not out.exists(),'Fresh output required');out.mkdir(parents=True)
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('150 second inner limit')))
    signal.alarm(150);resource.setrlimit(resource.RLIMIT_CPU,(140,141))
    report=dict(status='incomplete',scope='Diagnostic controls; no geometry mutation or candidate adoption',classifiers={},cuts=[])
    try:
        p=json.loads((root/'work/carrier-process-20261017/bounded-webs-first-window-corner-slide-law-API-observer-preparation-001/plan.json').read_text())
        sys.path.insert(0,str(root/p['native_site']))
        from build123d import import_brep
        from OCP.BRepClass3d import BRepClass3d_SolidClassifier
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
        from OCP.BRepGProp import BRepGProp
        from OCP.GProp import GProp_GProps
        from OCP.TopTools import TopTools_ListOfShape,TopTools_IndexedMapOfShape
        from OCP.TopExp import TopExp
        from OCP.TopAbs import TopAbs_SOLID
        from OCP.BRepTools import BRepTools
        from OCP.gp import gp_Pnt
        from OCP.OSD import OSD_ThreadPool
        OSD_ThreadPool.DefaultPool_s().Init(1)
        files={'baseline':root/p['master_BREP'],'candidate':root/'work/carrier-resume-20261020/nurbs-assembly-together-001/output/fuse-all.brep','patch0':root/'work/carrier-resume-20261020/nurbs-root-patch-001/output/patch-0.brep','patch1':root/'work/carrier-resume-20261020/nurbs-root-patch-001/output/patch-1.brep'}
        report['inputs']={k:dict(path=str(v.relative_to(root)),sha256=sha(v))for k,v in files.items()}
        bodies={k:import_brep(v).wrapped for k,v in files.items()}
        for name,shape in bodies.items():
            classifier=BRepClass3d_SolidClassifier(shape)
            classifier.PerformInfinitePoint(1e-7)
            row=dict(infinite_point=str(classifier.State()),nominal_datum_probes=[])
            for label,point in [('central_pad_origin',[0.,0.,0.]),('nominal_lightening_void',[20.,0.,0.]),('outside_bounds',[1000.,1000.,1000.])]:
                classifier.Perform(gp_Pnt(*point),1e-7)
                row['nominal_datum_probes'].append(dict(label=label,point_mm=point,state=str(classifier.State())))
            report['classifiers'][name]=row
        for name,a,b in [('baseline-self',bodies['baseline'],bodies['baseline']),('baseline-independent-import',bodies['baseline'],import_brep(files['baseline']).wrapped),('candidate-self',bodies['candidate'],bodies['candidate'])]:
            op=BRepAlgoAPI_Cut();arguments=TopTools_ListOfShape();tools=TopTools_ListOfShape();arguments.Append(a);tools.Append(b)
            op.SetArguments(arguments);op.SetTools(tools);op.SetNonDestructive(True);op.SetRunParallel(False);op.SetFuzzyValue(0.);op.Build();require(op.IsDone(),'Control Cut failed')
            result=op.Shape();BRepTools.Write_s(result,str(out/(name+'.brep')))
            solids=TopTools_IndexedMapOfShape();TopExp.MapShapes_s(result,TopAbs_SOLID,solids)
            props=GProp_GProps();BRepGProp.VolumeProperties_s(result,props)
            report['cuts'].append(dict(name=name,solid_count=solids.Extent(),volume_mm3=props.Mass()))
            write(out/'progress.json',report)
        report['status']='native_classifier_and_cut_controls_recorded'
    except Exception as error:report['failure']=dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc())
    finally:signal.alarm(0);write(out/'assessment.json',report)
    print(json.dumps(report))
    return 0 if report['status']=='native_classifier_and_cut_controls_recorded' else 1


if __name__=='__main__':raise SystemExit(main())
