"""Audit saved rounded-cavity CAD independently; never rerun its construction."""
import argparse
from fractions import Fraction as F
import hashlib
import shutil
import json
from pathlib import Path
import resource
import signal
import sys
import time
import traceback


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--body',type=Path,required=True);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--native-site',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--radius-proof',type=Path,required=True);p.add_argument('--surface',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True);start=time.monotonic();report=dict(status='incomplete',construction_repeated=False,manufacturing_authorized=False)
    resource.setrlimit(resource.RLIMIT_CPU,(180,195));signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('210 second audit bound')));signal.alarm(210)
    try:
        sys.path.insert(0,str(a.native_site.resolve()))
        from build123d import import_brep,export_stl
        from OCP.OSD import OSD_ThreadPool
        from OCP.BRepCheck import BRepCheck_Analyzer
        from OCP.BRepGProp import BRepGProp
        from OCP.GProp import GProp_GProps
        from OCP.BRepAdaptor import BRepAdaptor_Surface
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
        from OCP.BRepTools import BRepTools
        from OCP.TopTools import TopTools_ListOfShape,TopTools_IndexedMapOfShape
        from OCP.TopExp import TopExp
        from OCP import TopAbs
        OSD_ThreadPool.DefaultPool_s().Init(1)
        candidate=import_brep(a.body);baseline=import_brep(a.baseline)
        if hashlib.sha256(a.baseline.read_bytes()).hexdigest()!='24af058467fd82a9f0c1d391bf947d427dffd311371cf8f73dafa492d204f4fd':raise ValueError('Retained master differs')
        props=GProp_GProps();integration=BRepGProp.VolumeProperties_s(candidate.wrapped,props,1e-10,True,False);volume=props.Mass();box=candidate.bounding_box()
        radii=[]
        for face in candidate.faces():
            s=BRepAdaptor_Surface(face.wrapped)
            if str(s.GetType()).endswith('GeomAbs_Cylinder'):
                cylinder=s.Cylinder();loc=cylinder.Location();direction=cylinder.Axis().Direction()
                if 69<abs(loc.X())<73 and abs(direction.Y())>.999999:radii.append(dict(radius_mm=cylinder.Radius(),axis_location_mm=list(loc.Coord()),axis_direction=list(direction.Coord())))
        report.update(candidate_native_valid=BRepCheck_Analyzer(candidate.wrapped).IsValid(),native_solid_count=len(candidate.solids()),native_volume_mm3=volume,integration_relative_error_estimate=integration,mass_kg=volume*4.42e-6,mass_ceiling_kg=1.3,bounds_mm=[list(box.min),list(box.max)],local_cavity_end_cylinders=radii,source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [a.body,a.baseline,Path(__file__)]})
        radius=json.loads(a.radius_proof.read_text())
        if hashlib.sha256(a.body.read_bytes()).hexdigest()not in radius['source_sha256'].values()or radius['status']!='complete_native_root_radial_geometry_certificate_passed'or len(radius['faces'])!=4 or F(radius['maximum_complete_radial_deviation_mm'])>F(1,100000000):raise ValueError('Complete radial proof not bound to this body')
        report['complete_native_radial_certificate']=dict(path=str(a.radius_proof),sha256=hashlib.sha256(a.radius_proof.read_bytes()).hexdigest(),maximum_radial_error_mm=radius['maximum_complete_radial_deviation_mm'])
        shutil.copyfile(a.surface,a.output/'candidate-fine.stl')
        report['fine_STL_sha256']=hashlib.sha256((a.output/'candidate-fine.stl').read_bytes()).hexdigest();(a.output/'progress.json').write_text(json.dumps(report,indent=2)+'\n')
        op=BRepAlgoAPI_Cut();arguments=TopTools_ListOfShape();tools=TopTools_ListOfShape();arguments.Append(baseline.wrapped);tools.Append(candidate.wrapped);op.SetArguments(arguments);op.SetTools(tools);op.SetNonDestructive(True);op.SetRunParallel(False);op.SetFuzzyValue(0.);op.Build()
        if not op.IsDone():raise ValueError('Strict full-parent difference operation failed')
        difference=op.Shape();BRepTools.Write_s(difference,str(a.output/'baseline-minus-candidate.brep'));counts={}
        for kind in ['VERTEX','EDGE','WIRE','FACE','SHELL','SOLID','COMPSOLID']:
            m=TopTools_IndexedMapOfShape();TopExp.MapShapes_s(difference,getattr(TopAbs,'TopAbs_'+kind),m);counts[kind]=m.Extent()
        report['strict_parent_difference']=dict(operation_succeeded=True,entity_counts=counts,topologically_empty=not any(counts.values()),raw_sha256=hashlib.sha256((a.output/'baseline-minus-candidate.brep').read_bytes()).hexdigest())
        passed=report['candidate_native_valid']and report['native_solid_count']==1 and report['mass_kg']<=1.3 and radius['status']=='complete_native_root_radial_geometry_certificate_passed'and not any(counts.values())
        report['status']='native_valid_mass_radial_certificate_and_strict_parent_retention_passed'if passed else'native_scope_refused'
        report['pending']=['complete protected interfaces','complete surface audit','volume mesh and mechanical cases','print preparation']
    except BaseException as error:report['failure']=dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc());raise
    finally:signal.alarm(0);report['elapsed_seconds']=time.monotonic()-start;(a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k]for k in ['status','mass_kg','native_solid_count','strict_parent_difference']}));return 0 if passed else 2

if __name__=='__main__':raise SystemExit(main())
