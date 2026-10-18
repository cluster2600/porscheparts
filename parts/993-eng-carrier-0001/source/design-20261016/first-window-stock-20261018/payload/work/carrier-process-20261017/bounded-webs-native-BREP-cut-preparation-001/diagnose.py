"""Fresh-import Boolean quantification, detached baseline control and independent protection."""
import faulthandler
import os
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import shutil
import signal
import sys
import time
import traceback
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def write(path,value):
    with Path(path).open('x') as stream:
        json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')


def run():
    started=time.monotonic();faulthandler.enable(all_threads=True)
    plan=json.loads((HERE/'plan.json').read_text())
    before={name:sha(ROOT/name) for name in plan['files_sha256']};assert before==plan['files_sha256']
    output=ROOT/plan['output_directory'];assert not output.exists() and not output.is_symlink();output.mkdir()
    events=(output/'events.jsonl').open('x')
    def event(name,**fields):
        events.write(json.dumps(dict(event=name,elapsed_seconds=time.monotonic()-started,**fields),allow_nan=False)+'\n')
        events.flush();os.fsync(events.fileno())
        print(json.dumps(dict(event=name)),flush=True)
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Native BREP Cut diagnostic wall budget')))
    signal.alarm(560);resource.setrlimit(resource.RLIMIT_CPU,(520,540))
    report=dict(schema='isolated-old-minus-native-BREP-Cut-diagnostic-1',status='incomplete',candidate_qualified=False,
                new_fillet_Build=False,new_candidate=False,FEA_executed=False,sources_before=before)
    try:
        event('before_imports')
        sys.path.insert(0,str(ROOT/plan['native_site']))
        from build123d import import_step,import_brep
        from OCP.BRep import BRep_Tool
        from OCP.BRepAdaptor import BRepAdaptor_Surface
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
        from OCP.BRepBndLib import BRepBndLib
        from OCP.BRepCheck import BRepCheck_Analyzer
        from OCP.BRepGProp import BRepGProp
        from OCP.Bnd import Bnd_Box
        from OCP.GProp import GProp_GProps
        from OCP.OSD import OSD_ThreadPool
        from OCP.TopAbs import TopAbs_SOLID,TopAbs_FACE,TopAbs_EDGE,TopAbs_VERTEX
        from OCP.TopExp import TopExp
        from OCP.TopTools import TopTools_IndexedMapOfShape,TopTools_ListOfShape
        from OCP.TopoDS import TopoDS
        OSD_ThreadPool.DefaultPool_s().Init(1)
        volume=load('_isolated_cut_precise_volume',ROOT/plan['volume_source'])
        def entities(raw,kind):
            mapping=TopTools_IndexedMapOfShape();TopExp.MapShapes_s(raw,kind,mapping)
            return [mapping.FindKey(i) for i in range(1,mapping.Extent()+1)]

        def bbox(raw):
            box=Bnd_Box();BRepBndLib.Add_s(raw,box,False)
            return None if box.IsVoid() else list(box.Get())

        def summary(raw):
            if raw is None or raw.IsNull():
                return dict(native_null=True,counts=dict(solids=0,faces=0,edges=0,vertices=0),
                            material_solid_volume_mm3=0.,native_topologically_empty=True,bounds_mm=None)
            parts={name:entities(raw,kind) for name,kind in [('solids',TopAbs_SOLID),('faces',TopAbs_FACE),('edges',TopAbs_EDGE),('vertices',TopAbs_VERTEX)]}
            result=dict(native_null=False,native_type=str(raw.ShapeType()),native_valid=BRepCheck_Analyzer(raw).IsValid(),
                        counts={key:len(value) for key,value in parts.items()},bounds_mm=bbox(raw),solids=[],tolerances_mm={})
            for solid in parts['solids']:
                mass,error=volume.precise_volume(SimpleNamespace(wrapped=solid))
                result['solids'].append(dict(volume_mm3=mass,estimated_relative_integration_error=error,
                                             native_valid=BRepCheck_Analyzer(solid).IsValid(),bounds_mm=bbox(solid)))
            result['material_solid_volume_mm3']=sum(item['volume_mm3'] for item in result['solids'])
            result['sum_absolute_solid_volume_mm3']=sum(abs(item['volume_mm3']) for item in result['solids'])
            result['volume_scope']='BRepGProp adaptive integrals of each actual Solid only; no fictitious material volume integrated from an open face or edge residue.'
            casts={'faces':TopoDS.Face_s,'edges':TopoDS.Edge_s,'vertices':TopoDS.Vertex_s}
            for kind,cast in casts.items():
                tolerances=[BRep_Tool.Tolerance_s(cast(item)) for item in parts[kind]]
                result['tolerances_mm'][kind]=dict(count=len(tolerances),minimum=min(tolerances) if tolerances else None,
                                                maximum=max(tolerances) if tolerances else None)
            areas=[];types={}
            for face in parts['faces']:
                face=TopoDS.Face_s(face);props=GProp_GProps();BRepGProp.SurfaceProperties_s(face,props)
                areas.append(props.Mass());key=str(BRepAdaptor_Surface(face,True).GetType());types[key]=types.get(key,0)+1
            result['surface_area_sum_mm2']=sum(areas)
            result['surface_types']=types
            result['degenerated_edge_count']=sum(BRep_Tool.Degenerated_s(TopoDS.Edge_s(edge)) for edge in parts['edges'])
            result['native_topologically_empty']=all(not values for values in parts.values())
            result['highest_topological_dimension']=next((dim for name,dim in [('solids',3),('faces',2),('edges',1),('vertices',0)] if parts[name]),None)
            return result

        left=import_step(ROOT/plan['baseline_STEP']);right=import_brep(ROOT/plan['candidate_BREP'])
        assert left.is_valid and right.is_valid and len(left.solids())==len(right.solids())==1
        event('fresh_inputs_loaded')
        cut=BRepAlgoAPI_Cut();args=TopTools_ListOfShape();tools=TopTools_ListOfShape()
        args.Append(left.wrapped);tools.Append(right.wrapped)
        cut.SetArguments(args);cut.SetTools(tools)
        cut.SetNonDestructive(True);cut.SetRunParallel(False);cut.SetFuzzyValue(0.)
        event('before_Build',NonDestructive=True,RunParallel=False,FuzzyValue=0.)
        cut.Build()
        event('after_Build')
        done=cut.IsDone();event('after_IsDone',IsDone=done)
        report['IsDone']=done
        if not done:raise ValueError('Single native Cut did not complete')
        event('before_Shape');raw=cut.Shape();event('after_Shape')
        event('before_quantification');report['residue']=summary(raw);event('after_quantification')
        write(output/'residue.json',report['residue'])
        report['strict_native_empty']=report['residue']['native_topologically_empty']
        report['status']='native_BREP_strict_native_empty_pass'if report['strict_native_empty']else'refused_native_BREP_nonempty_residue'
    except BaseException as error:
        report['failure']=dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc())
    finally:
        signal.alarm(0)
        after={name:sha(ROOT/name)for name in before}
        report.update(sources_after=after,sources_unchanged=before==after,elapsed_seconds=time.monotonic()-started)
        if before!=after:report['status']='refused_input_drift'
        write(output/'assessment.json',report);event('assessment_written',sha256=sha(output/'assessment.json'));events.close()
    return 0 if report['status']=='native_BREP_strict_native_empty_pass' and report['sources_unchanged'] else 1

if __name__=='__main__':raise SystemExit(run())
