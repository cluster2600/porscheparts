"""Generate a separate native study with finite-radius inner cavity ends.

The retained 24af bundle is read-only. Generated private copies have explicit
source-path rebases and one cavity-cutter edit. No NURBS reinforcement is added.
"""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import signal
import sys
import time
import traceback


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--native-site',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve();bundle=a.bundle.resolve()
    if out.exists():raise ValueError('Fresh output required')
    out.mkdir(parents=True);start=time.monotonic();report=dict(status='incomplete',design='finite-radius inner hollow ends, no added NURBS patches',parameters=dict(inner_cavity_trim_absolute_X_mm=70,inner_cavity_corner_radius_mm=.6),manufacturing_authorized=False)
    resource.setrlimit(resource.RLIMIT_CPU,(360,380));signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('420 second CAD wall bound')));signal.alarm(420)
    try:
        sys.path.insert(0,str(a.native_site.resolve()))
        import os
        os.nice(10)
        from OCP.OSD import OSD_ThreadPool
        OSD_ThreadPool.DefaultPool_s().Init(1)
        original=bundle/'generator';generated=out/'generator';(generated/'normal-builder').mkdir(parents=True)
        payload=bundle/'payload/parts/993-eng-carrier-0001/source';inputs=out/'inputs';inputs.mkdir()
        for name in ['bounded-webs.json','bounded-webs-plan.json']:
            d=json.loads((payload/'design-20261016'/name).read_text());d['design_id']='carrier-rounded-hollow-root-20261020'
            if name.endswith('plan.json'):d['rounded_inner_cavity_end']=report['parameters']
            (inputs/name).write_text(json.dumps(d,indent=2)+'\n')
        stock=(original/'build_stock.py').read_text();stock=stock.replace("SOURCE = Path(__file__).resolve().parents[1] / 'payload/parts/993-eng-carrier-0001/source/design-20261016'",f'SOURCE = Path({str(inputs)!r})');stock=stock.replace("sys.path.insert(0,str(SOURCE.parent/'bionic-20261011/correction-20261013'))",f'sys.path.insert(0,{str(payload/"bionic-20261011/correction-20261013")!r})');(generated/'build_stock.py').write_text(stock)
        correction=(original/'corrected_cad.py').read_text().replace("SOURCE = Path(__file__).resolve().parents[1] / 'payload/parts/993-eng-carrier-0001/source/bionic-20261011/correction-20261013'",f'SOURCE = Path({str(payload/"bionic-20261011/correction-20261013")!r})');(generated/'corrected_cad.py').write_text(correction)
        normal=(original/'normal-builder/cad.py').read_text();needle='return [extrude(Face(Wire(edges[i:i+6])), amount=200, dir=(0, 1, 0))\n            for i in (0, 6)]'
        if normal.count(needle)!=1:raise ValueError('Retained cavity constructor differs')
        change='''cores = [extrude(Face(Wire(edges[i:i+6])), amount=200, dir=(0, 1, 0)) for i in (0, 6)]
    from build123d import Box
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    from OCP.TopExp import TopExp_Explorer
    from OCP import TopAbs
    rounded = []
    for core in cores:
        side = 1 if core.center().X > 0 else -1
        # Keep the end-eye-side cutter unchanged; only the inner cusp is removed.
        trimmed = core & (Pos(side*185, 0, 0) * Box(230, 202, 100))
        chosen = [e for e in trimmed.edges() if abs(e.center().X-side*70)<1e-7 and abs(e.length-200)<1e-6]
        if len(chosen)!=2:raise ValueError('Expected both inner end-cap edges')
        export_brep(trimmed, ROUND_OUTPUT/f'core-{ROUND_COUNTER[0]}-trimmed.brep')
        candidate = fillet(chosen, .6)
        export_brep(candidate, ROUND_OUTPUT/f'core-{ROUND_COUNTER[0]}-rounded.brep')
        if not candidate.is_valid or len(candidate.solids())!=1:raise ValueError('Rounded cutter invalid')
        cut=BRepAlgoAPI_Cut(candidate.wrapped,core.wrapped);cut.SetNonDestructive(True);cut.SetRunParallel(False);cut.SetFuzzyValue(0.);cut.Build()
        if not cut.IsDone():raise ValueError('Cutter containment operation refused')
        counts={name:int(TopExp_Explorer(cut.Shape(),getattr(TopAbs,'TopAbs_'+name)).More())for name in ['SOLID','FACE','EDGE','VERTEX']}
        row=dict(index=ROUND_COUNTER[0],side=side,radius_mm=.6,inner_trim_absolute_X_mm=70,selected_edges=len(chosen),valid=candidate.is_valid,original_volume_mm3=core.volume,rounded_volume_mm3=candidate.volume,new_minus_original_entity_presence=counts)
        with (ROUND_OUTPUT/'cutter-ledger.jsonl').open('a')as stream:stream.write(json.dumps(row)+'\\n')
        ROUND_COUNTER[0]+=1
        if any(counts.values()):raise ValueError('Rounded cutter is not strictly contained in original')
        rounded.append(candidate)
    return rounded'''
        normal=normal.replace(needle,change);normal+='\nROUND_OUTPUT=Path('+repr(str(out))+')\nROUND_COUNTER=[0]\n';(generated/'normal-builder/cad.py').write_text(normal)
        report['source_sha256']={str(p):sha(p)for p in [original/'build_stock.py',original/'corrected_cad.py',original/'normal-builder/cad.py',generated/'build_stock.py',generated/'corrected_cad.py',generated/'normal-builder/cad.py',Path(__file__)]}
        (out/'construction-plan.json').write_text(json.dumps(report,indent=2)+'\n')
        import importlib.util
        spec=importlib.util.spec_from_file_location('_rounded_cavity_private_stock',generated/'build_stock.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        result=module.build(out/'candidate')
        report.update(status='native_rounded_inner_cavities_generated',geometry=result,pending=['strict complete parent retention','all protected interfaces','complete surface/volume checks','new mechanical comparisons','full print preparation'])
    except BaseException as error:report['failure']=dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc());raise
    finally:signal.alarm(0);report['elapsed_seconds']=time.monotonic()-start;(out/'assessment.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],mass_kg=result['dense_reference_mass_kg'])))

if __name__=='__main__':main()
