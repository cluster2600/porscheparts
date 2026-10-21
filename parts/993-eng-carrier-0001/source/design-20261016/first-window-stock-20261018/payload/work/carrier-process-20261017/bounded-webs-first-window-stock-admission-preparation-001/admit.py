"""Non-armed local geometry gates for the saved first-window stock alone."""
import importlib.util
import json
import math
import os
from pathlib import Path
import resource
import signal
import sys
import time
import traceback
from types import SimpleNamespace

H = Path(__file__).resolve().parent; R = H.parents[2]
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module
RECORDS = load('_closed_stock_records', H / 'records.py')
GATE = load('_original_local_gates', H.with_name('bounded-webs-C1-endfillet-preparation-002') / 'close_end.py')
sha, require, write = GATE.sha, GATE.require, GATE.write

def verify(path, expected, native=False):
    require(sha(path) == expected, 'Plan identity differs'); p = json.loads(Path(path).read_text())
    require(p['schema'] == 'first-window-stock-native-local-plan-1' and p['bounds'] == dict(outer=600, inner=560, CPU=[520,540], threads=1, workers=0), 'Reviewed local scope/resources differ')
    if native: require(p['launch_ready'] is True and p['root_GO_sha256'] is not None and sha(R / p['root_GO']) == p['root_GO_sha256'], 'NON-ARMED: stock-only ROOT review/GO required')
    before = {name: sha(R / name) for name in p['files_sha256']}; require(before == p['files_sha256'], 'A pinned input/source/runtime differs')
    source = RECORDS.closed_stock(); require(source['candidate_BREP']['path'] == p['candidate_BREP'] and source['candidate_BREP']['sha256'] == p['candidate_BREP_sha256'] == RECORDS.BREP_SHA, 'Stock candidate crossed')
    require(before[p['baseline_STEP']] == GATE.BASELINE and p['current07b_subset_required'] is False and p['old_complete7_law_inherited'] is False, 'Original baseline or new-design scope differs')
    out = R / p['output_directory']; require(not out.exists() and not any(q.is_symlink() for q in [out,*out.parents]), 'Fresh nonsymlink output required')
    if not native: require(not (R / p['execution_directory']).exists(), 'Fresh supervision required at preflight')
    return p, before, out, source

def strict_empty(row):
    require(row['native_topologically_empty'] is True and row.get('native_valid') is True and row['counts'] == dict(solids=0,faces=0,edges=0,vertices=0) and row.get('highest_topological_dimension') is None, 'Original baseline containment is not strictly empty in every dimension')

def run(path, expected):
    began=time.monotonic(); p,before,out,source=verify(path,expected,True); out.mkdir(); code=1
    report=dict(schema='first-window-stock-native-local-admission-1',status='refused_or_incomplete',candidate_version='first-window-stock-alone-v1',candidate_BREP_sha256=p['candidate_BREP_sha256'],candidate_qualified=False,failed_union_preserved=True,failed_union_used=False,current07b_subset_required=False,old_complete7_law_inherited=False,sources_before=before,downstream_checks={key:'PENDING' for key in GATE.PENDING},FEA_executed=False)
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('560s saved-stock local gate bound'))); signal.alarm(560); resource.setrlimit(resource.RLIMIT_CPU,(520,540))
    events=(out/'events.jsonl').open('x')
    def event(name,**values):
        events.write(json.dumps(dict(event=name,seconds=time.monotonic()-began,**values),allow_nan=False)+'\n');events.flush();os.fsync(events.fileno())
    try:
        require(os.getpriority(os.PRIO_PROCESS,0)==10,'nice10 child required');sys.path.insert(0,str(R/p['native_site']))
        from build123d import import_brep,import_step
        from OCP.BRep import BRep_Tool
        from OCP.BRepAdaptor import BRepAdaptor_Surface
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
        from OCP.BRepBndLib import BRepBndLib
        from OCP.BRepCheck import BRepCheck_Analyzer
        from OCP.BRepGProp import BRepGProp
        from OCP.BRepTools import BRepTools
        from OCP.Bnd import Bnd_Box
        from OCP.GProp import GProp_GProps
        from OCP.OSD import OSD_ThreadPool
        from OCP.TopAbs import TopAbs_SOLID,TopAbs_FACE,TopAbs_EDGE,TopAbs_VERTEX
        from OCP.TopExp import TopExp
        from OCP.TopTools import TopTools_IndexedMapOfShape,TopTools_ListOfShape
        from OCP.TopoDS import TopoDS
        OSD_ThreadPool.DefaultPool_s().Init(1)
        basis=load('_original_three_overload_observer',R/p['volume_observer_source']);volume=load('_original_adaptive_volume',R/p['volume_source'])
        summary=GATE.retain_cut_helpers(R/p['strict_cut_source'],dict(TopTools_IndexedMapOfShape=TopTools_IndexedMapOfShape,TopExp=TopExp,Bnd_Box=Bnd_Box,BRepBndLib=BRepBndLib,TopAbs_SOLID=TopAbs_SOLID,TopAbs_FACE=TopAbs_FACE,TopAbs_EDGE=TopAbs_EDGE,TopAbs_VERTEX=TopAbs_VERTEX,BRepCheck_Analyzer=BRepCheck_Analyzer,volume=volume,SimpleNamespace=SimpleNamespace,TopoDS=TopoDS,BRep_Tool=BRep_Tool,GProp_GProps=GProp_GProps,BRepGProp=BRepGProp,BRepAdaptor_Surface=BRepAdaptor_Surface))
        candidate=import_brep(R/p['candidate_BREP']);whole=summary(candidate.wrapped);write(out/'candidate-native-summary.json',whole);report['whole_candidate']=whole
        require(candidate.is_valid and len(candidate.solids())==1,'Fresh saved stock is not one valid Solid')
        solid=candidate.solids()[0].wrapped
        rows=basis.evaluate(solid,BRepGProp,GProp_GProps)
        observation=dict(schema='three-actual-volume-overloads-one-native-Solid-1',candidate_BREP_sha256=p['candidate_BREP_sha256'],same_Solid_native_identity=solid.IsSame(candidate.solids()[0].wrapped),one_reloaded_valid_native_Solid=BRepCheck_Analyzer(solid).IsValid(),methods=rows,operator_source_sha256=before[p['volume_observer_source']],Gmsh_getMass_mm3=None)
        write(out/'native-volume-overloads.json',observation);report['volume_observation']=observation
        native_volume=rows[2]['signed_mass_mm3'];reference=source['original_native_construction']['volume_mm3'];study=json.loads((R/p['study']).read_text());mass=native_volume*study['material']['density_tonne_mm3']*1000;box=candidate.bounding_box();bounds=[list(box.min),list(box.max)]
        measured=dict(native_adaptive_volume_mm3=native_volume,native_adaptive_error_estimate=rows[2]['returned_error_estimate'],native_FFF_volume_mm3=rows[0]['signed_mass_mm3'],mass_kg=mass,bounds_mm=bounds,construction_reference_mm3=reference,relative_reread_difference=native_volume/reference-1,existing_readback_relative_limit=1e-8,same_Solid_native_identity=observation['same_Solid_native_identity'],native_valid_after_volume=BRepCheck_Analyzer(solid).IsValid())
        write(out/'local-measurements-before-gates.json',measured);report['measurements']=measured
        summaries={}
        for name in ('baseline-minus-stock','stock-minus-baseline'):
            original=import_step(R/p['baseline_STEP']);require(original.is_valid and len(original.solids())==1,'Fresh original baseline is not one valid Solid')
            left,right=(original,candidate) if name=='baseline-minus-stock' else (candidate,original)
            cut=BRepAlgoAPI_Cut();args=TopTools_ListOfShape();tools=TopTools_ListOfShape();args.Append(left.wrapped);tools.Append(right.wrapped);cut.SetArguments(args);cut.SetTools(tools);cut.SetNonDestructive(True);cut.SetRunParallel(False);cut.SetFuzzyValue(0.)
            event('before_'+name,NonDestructive=True,RunParallel=False,FuzzyValue=0.);cut.Build();event('after_'+name,IsDone=cut.IsDone());require(cut.IsDone(),'Native stock Cut incomplete')
            raw=cut.Shape();raw_path=out/(name+'-raw.brep')
            if raw.IsNull():saved=dict(path=None,sha256=None,reason='completed_native_Cut_returned_a_null_shape')
            else:
                require(BRepTools.Write_s(raw,str(raw_path)) is True,'Raw native stock Cut export failed');saved=dict(path=raw_path.name,sha256=sha(raw_path),reason=None)
            write(out/(name+'-raw-preservation.json'),saved);report.setdefault('raw_Cut_preservation',{})[name]=saved;summaries[name]=summary(raw);write(out/(name+'.json'),summaries[name]);report['native_Cut_summaries']=summaries
        strict_empty(summaries['baseline-minus-stock']);added=summaries['stock-minus-baseline'];require(not added['native_topologically_empty'] and added.get('native_valid') is True and added['material_solid_volume_mm3']>0 and all(row['native_valid'] and row['volume_mm3']>0 for row in added.get('solids',[])),'Positive valid addition to the original baseline required')
        require(observation['same_Solid_native_identity'] and observation['one_reloaded_valid_native_Solid'] and measured['native_valid_after_volume'],'Same valid Solid was not retained across the three observations')
        require(abs(measured['relative_reread_difference'])<1e-8,'Existing volume readback criterion failed')
        report.update(GATE.local_gate_flags(summaries['baseline-minus-stock'],candidate.is_valid,len(candidate.solids()),mass,bounds,p),status='saved_first_window_stock_local_gates_complete_downstream_PENDING');code=0
    except BaseException as error:report['failure']=dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc())
    finally:
        signal.alarm(0);after={name:sha(R/name)for name in before};report.update(sources_after=after,sources_unchanged=before==after,elapsed_seconds=time.monotonic()-began)
        if before!=after:report['status']='refused_sources_changed';code=1
        write(out/'assessment.json',report);event('assessment_written',sha256=sha(out/'assessment.json'));events.close()
    print(json.dumps(dict(status=report['status'],candidate_qualified=False,assessment_sha256=sha(out/'assessment.json'))),flush=True);return code

if __name__=='__main__':
    mode,path,expected=sys.argv[1:]
    if mode=='preflight':verify(path,expected);print('SOURCE_ONLY: saved-stock provenance and pending local controls verified')
    elif mode=='run':raise SystemExit(run(path,expected))
    else:raise ValueError('Use preflight or run PLAN SHA')
