"""Round the four new concave end-cap/gusset junctions in a separate CAD trial."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import signal
import sys
import time
import traceback


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--body',type=Path,required=True);p.add_argument('--native-site',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--radius',type=float,required=True);a=p.parse_args()
    if not 0<a.radius<=.6:raise ValueError('Explicit side-junction design radius must be in (0,0.6] mm')
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True);start=time.monotonic();report=dict(status='incomplete',declared_radius_mm=a.radius,manufacturing_authorized=False)
    resource.setrlimit(resource.RLIMIT_CPU,(150,165));signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('180 second CAD bound')));signal.alarm(180)
    try:
        sys.path.insert(0,str(a.native_site.resolve()))
        from build123d import import_brep,export_brep,export_step,export_stl,fillet
        from OCP.OSD import OSD_ThreadPool
        from OCP.BRepTools import BRepTools
        from OCP.BRepGProp import BRepGProp
        from OCP.GProp import GProp_GProps
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
        from OCP.TopTools import TopTools_ListOfShape,TopTools_IndexedMapOfShape
        from OCP.TopExp import TopExp
        from OCP import TopAbs
        OSD_ThreadPool.DefaultPool_s().Init(1)
        body=import_brep(a.body);selected=[];rows=[]
        for edge in body.edges():
            box=edge.bounding_box();p0,p1=box.min,box.max
            if abs(abs(edge.center().X)-70)<1e-5 and 24<abs(edge.center().Y)<25 and p1.X-p0.X<1e-5 and p1.Y-p0.Y<1e-5 and 1<p1.Z-p0.Z<1.3:
                selected.append(edge);rows.append(dict(bounds_mm=[list(p0),list(p1)],length_mm=edge.length))
        report['selected_edges']=rows
        if len(selected)!=4:raise ValueError('Expected four complete vertical end-cap/gusset edges')
        (a.output/'plan.json').write_text(json.dumps(report,indent=2)+'\n');candidate=fillet(selected,a.radius)
        export_brep(candidate,a.output/'candidate-native.brep');export_step(candidate,a.output/'candidate.step')
        if not candidate.is_valid or len(candidate.solids())!=1 or len(candidate.shells())!=1:raise ValueError('One valid single-shell result required')
        op=BRepAlgoAPI_Cut();arguments=TopTools_ListOfShape();tools=TopTools_ListOfShape();arguments.Append(body.wrapped);tools.Append(candidate.wrapped);op.SetArguments(arguments);op.SetTools(tools);op.SetNonDestructive(True);op.SetRunParallel(False);op.SetFuzzyValue(0.);op.Build()
        if not op.IsDone():raise ValueError('Strict input-material retention operation failed')
        shape=op.Shape();BRepTools.Write_s(shape,str(a.output/'input-minus-candidate.brep'));counts={}
        for name in ['VERTEX','EDGE','WIRE','FACE','SHELL','SOLID','COMPSOLID']:
            m=TopTools_IndexedMapOfShape();TopExp.MapShapes_s(shape,getattr(TopAbs,'TopAbs_'+name),m);counts[name]=m.Extent()
        report['strict_input_retention']=dict(entity_counts=counts,topologically_empty=not any(counts.values()))
        props=GProp_GProps();BRepGProp.VolumeProperties_s(candidate.wrapped,props,1e-10,True,False);mass=props.Mass()*4.42e-6
        report.update(valid=candidate.is_valid,shells=len(candidate.shells()),mass_kg=mass,source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [a.body,Path(__file__)]})
        BRepTools.Clean_s(candidate.wrapped);export_stl(candidate,a.output/'candidate.stl',tolerance=.015,angular_tolerance=.08)
        passed=not any(counts.values())and mass<=1.3;report['status']='native_side_junctions_rounded_and_input_retained'if passed else'native_side_junction_trial_refused'
    except BaseException as error:report['failure']=dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc());raise
    finally:signal.alarm(0);report['elapsed_seconds']=time.monotonic()-start;(a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k]for k in ['status','mass_kg','strict_input_retention']}));return 0 if passed else 2

if __name__=='__main__':raise SystemExit(main())
