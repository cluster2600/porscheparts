"""Train corrected photo lessons and mechanics; frozen graders and native INP checks."""
import argparse
import fcntl
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import photo_course
import refine

SSH = ['ssh', '-F', '/dev/null', '-i', '/Users/maxime/.ssh/id_cluster2600', '-o', 'IdentitiesOnly=yes',
       '-o', 'BatchMode=yes', '-o', 'UseKeychain=no', '-o', 'StrictHostKeyChecking=yes', '-o', 'UpdateHostKeys=no',
       '-o', 'ConnectTimeout=6', 'lolman@192.168.50.139']
CCX_SHA = 'db2ed33d0fd97ef4daad298def2fd8d3e9879e488647b0e7b44f52038b62ea0b'
REMOTE = r'''
import hashlib,json,math,os,pathlib,re,subprocess,sys,tempfile
assert hashlib.sha256(pathlib.Path('/usr/bin/ccx').read_bytes()).hexdigest() == 'db2ed33d0fd97ef4daad298def2fd8d3e9879e488647b0e7b44f52038b62ea0b'
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',CCX_NPROC_RESULTS='1',CCX_NPROC_STIFFNESS='1')
results=[]
for row in json.load(sys.stdin):
    root=pathlib.Path(tempfile.mkdtemp(prefix='codex-qwen-ccx-photo-'))
    deck=row['deck']; assert len(deck)<16000 and '*INCLUDE' not in deck.upper()
    (root/'case.inp').write_text(deck)
    result=subprocess.run(['/usr/bin/ccx','-i','case'],cwd=root,capture_output=True,text=True,timeout=30)
    (root/'solver.log').write_text(result.stdout+result.stderr)
    observed=[]
    data=root/'case.dat'
    if data.exists():
        for line in data.read_text().splitlines():
            words=line.split()
            if len(words)==row['width'] and re.fullmatch(r'\d+',words[0]):
                try: observed.append(float(words[row['column']].replace('D','E')))
                except ValueError: pass
    passed=result.returncode==0 and bool(observed) and all(math.isfinite(v) and math.isclose(v,row['value'],rel_tol=1e-5,abs_tol=1e-12) for v in observed)
    receipt={'id':row['id'],'passed':passed,'observed':observed,'expected':row['value'],'exit_code':result.returncode,'native_directory':str(root),'log_sha256':hashlib.sha256((root/'solver.log').read_bytes()).hexdigest()}
    (root/'receipt.json').write_text(json.dumps(receipt)); results.append(receipt)
print(json.dumps(results))
'''


def strip(answer):
    return re.sub(r'^```(?:python|json|inp|text|csharp|cs)?\s*([\s\S]*?)\s*```$', r'\1', answer.strip())


def deck_signature(source):
    """Conservative deck equivalence; no model-controlled include or executable."""
    if len(source)>16000: raise ValueError('deck exceeds limit')
    rows=[]
    for line in source.splitlines():
        line=line.strip()
        if not line or line.startswith('**'): continue
        fields=[]
        for field in line.split(','):
            field=field.strip().upper()
            try:
                n=float(field)
                if not math.isfinite(n): raise ValueError('nonfinite deck')
                fields.append(n)
            except ValueError:
                if not re.fullmatch(r'[A-Z*][A-Z0-9*= _.-]*',field): raise ValueError('unsupported deck field')
                fields.append(field)
        rows.append(fields)
    return rows


def native(rows):
    if not rows: return []
    quote=lambda s: "'"+s.replace("'", "'\\''")+"'"
    r=subprocess.run([*SSH,'python3 -c '+quote(REMOTE)],input=json.dumps(rows),capture_output=True,text=True,timeout=1800,check=True)
    return json.loads(r.stdout)


def qualification(before, after):
    assert [r['id'] for r in before] == [r['id'] for r in after]
    totals={d: {'passed':sum(r['passed'] for r in after if r['domain']==d),'total':sum(r['domain']==d for r in after)} for d in sorted({r['domain'] for r in after})}
    lost=[b['id'] for b,a in zip(before,after) if b['passed'] and not a['passed']]
    return {'per_domain':totals,'regressions':lost,'eligible':not lost and all(v['passed']>=math.ceil(.95*v['total']) for v in totals.values())}


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--output',type=Path,required=True); args=parser.parse_args()
    out=args.output.resolve(); previous=refine.ROOT/'work/qwen-engineering-002'
    assert (previous/'results.json').exists(), 'finish the prior measured run first'
    assert importlib.metadata.version('mlx-lm') == '0.31.3'
    assert shutil.disk_usage(refine.ROOT).free > 3*1024**3, 'keep 3 GiB free before starting'
    version=subprocess.run([str(refine.USD_PYTHON),'-c','from pxr import Usd; print(Usd.GetVersion())'],capture_output=True,text=True,check=True).stdout.strip()
    assert version == '(0, 25, 5)'
    out.mkdir(exist_ok=False)
    lock=(refine.RUNTIME/'train.lock').open('a'); fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_IMPLICIT_TOKEN='1',HF_HUB_DISABLE_TELEMETRY='1',PXR_WORK_THREAD_LIMIT='1')
    sys.path.insert(0,str(refine.ROOT/'training/qwen-engineering-20261002'))
    old=refine.module('photo_registered_runner',refine.ROOT/'training/qwen-engineering-20261002/run.py')
    private=previous/'helpers'; digest,save,child,configure,exact,pico,usd=old.helpers(private)
    prior_manifest=json.loads((previous/'manifest.json').read_text())
    assert all(digest(Path(f))==h for f,h in prior_manifest['files_sha256'].items())
    assert all(digest(Path(f))==h for f,h in prior_manifest['native_sha256'].items())
    model=refine.RUNTIME/'model-cache/models--mlx-community--Qwen2.5-Coder-1.5B-Instruct-4bit/snapshots/b3252a2f97102b1fb1571fec2c9b27219a8536be'
    selected=refine.RUNTIME/'coding-003/checkpoint-600'; warm=previous/'checkpoint-600'
    assert digest(model/'model.safetensors')==old.BASE_SHA and digest(selected/'adapters.safetensors')==old.PRIOR_SHA
    assert digest(warm/'adapters.safetensors') == json.loads((previous/'results.json').read_text())['trials']['600']['adapter_sha256']
    initial=json.loads((previous/'cases.json').read_text())
    more=photo_course.cases(refine,usd,refine.module('photo_ccx_reference',refine.ROOT/'scripts/cad_recode/ccx_smoke.py'))
    rows=initial+more; assert len({r['id'] for r in rows})==len(rows)
    save(out/'cases.json',rows); data=out/'data'; data.mkdir()
    for split in ('train','valid','test'):
        (data/(split+'.jsonl')).write_text(''.join(json.dumps({'messages':r['messages']})+'\n' for r in rows if r['split']==split))
    from mlx_lm import load,stream_generate
    from mlx_lm.sample_utils import make_sampler
    import mlx.core as mx
    network,tokenizer=load(str(model),tokenizer_config={'trust_remote_code':False})
    maximum=max(len(tokenizer.apply_chat_template(r['messages'],tokenize=True)) for r in rows)
    assert maximum<=1024
    del network,tokenizer; mx.clear_cache()
    files=[Path(__file__),Path(photo_course.__file__),Path(refine.__file__),Path(__file__).with_name('research.json'),refine.ROOT/'scripts/cad_recode/ccx_smoke.py',out/'cases.json',*data.glob('*.jsonl')]
    frozen={**prior_manifest['files_sha256'],**{str(f):digest(f) for f in files}}
    save(out/'manifest.json',{'files_sha256':frozen,'warm_sha256':digest(warm/'adapters.safetensors'),'base_sha256':old.BASE_SHA,'ccx_sha256':CCX_SHA,
        'native_sha256':prior_manifest['native_sha256'],'maximum_sequence_tokens':maximum,'iterations':1200,'batch_size':2,'seed':42,'learning_rate':.00002,'num_layers':16,
        'mlx_lm_version':'0.31.3','usd_version':version,'registered_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=refine.ROOT,text=True).strip(),
        'counts':{s:{d:sum(r['split']==s and r['domain']==d for r in rows) for d in sorted({r['domain'] for r in rows})} for s in ('train','valid','test')},
        'limits':'Shared API/formula/decision recipes. INP benchmark is axial T3D2 only. No engine qualification, general CAD mastery, arbitrary CHT, or calibrated surrogate claim.',
        'selection':'>=95% in every domain and no passing parent/selected validation case lost; fresh photo cases only after eligibility; default replacement is not automatic.'})
    def phase(name): save(out/'status.json',{'phase':name}); print(name,flush=True)
    def infer(label,adapter,subset):
        phase(label); network,tokenizer=load(str(model),adapter_path=str(adapter),tokenizer_config={'trust_remote_code':False}); configure(tokenizer); mx.random.seed(42)
        responses=[]
        for r in subset:
            prompt=tokenizer.apply_chat_template(r['messages'][:2],tokenize=False,add_generation_prompt=True)
            answer=''.join(x.text for x in stream_generate(network,tokenizer,prompt=prompt,max_tokens=1024,sampler=make_sampler(temp=0)))
            responses.append({'id':r['id'],'response':answer})
            save(out/(label+'-responses.json'),responses)
        del network,tokenizer; mx.clear_cache(); return responses
    common=[str(refine.ROOT/'training/qwen-engineering-20261002/run.py'),'score','--training-checkout',str(private),'--usd-python',str(refine.USD_PYTHON),'--sdk',str(refine.PICO/'dotnet/dotnet'),'--dll',str(refine.PICO/'picogk-bin/PicoGK.dll')]
    def grade(label,subset,responses):
        answers={r['id']:strip(r['response']) for r in responses}; base=[r for r in subset if r['domain'] in old.DOMAINS]
        save(out/(label+'-cases.json'),base); save(out/(label+'-all-responses.json'),responses)
        child([str(refine.USD_PYTHON),*common,'--input',str(out/(label+'-cases.json')),'--responses',str(out/(label+'-all-responses.json')),'--output',str(out/label)],out/(label+'.log'),timeout=1800)
        scores=json.loads((out/label/'scores.json').read_text()); by_id={r['id']:r for r in subset}
        for r in scores:
            if r['domain']=='python' and r['passed']:
                try:r['passed']=refine.parameterized(answers[r['id']],by_id[r['id']]['expected'],old.calculate)
                except (ValueError,SyntaxError,ZeroDivisionError):r['passed']=False
        requests=[]
        for r in subset:
            if r['domain'] in old.DOMAINS:continue
            answer=answers[r['id']]; result={'id':r['id'],'domain':r['domain'],'passed':False,'response_sha256':hashlib.sha256(answer.encode()).hexdigest()}
            try:
                result['passed']=exact(answer,r['expected']) if r['domain']=='engineering' else deck_signature(answer)==deck_signature(r['expected']['deck'])
                if result['passed'] and r['domain']=='calculix':requests.append({**r['expected'],'id':r['id'],'deck':answer})
            except (ValueError,TypeError):pass
            scores.append(result)
        witnesses={r['id']:r for r in native(requests)}
        for r in scores:
            if r['id'] in witnesses:r['native']=witnesses[r['id']]; r['passed']=witnesses[r['id']]['passed']
        scored={r['id']:r for r in scores}; scores=[scored[r['id']] for r in subset]; save(out/label/'scores-independent.json',scores); return scores
    phase('reference_checks')
    references=[r for r in more if r['split']=='train']
    assert all(r['passed'] for r in grade('references',references,[{'id':r['id'],'response':r['messages'][-1]['content']} for r in references]))
    validation=[r for r in rows if r['split']=='valid']
    parent={r['id']:r for r in json.loads((previous/'validation-600/scores-with-parameter-audit.json').read_text())}
    retained={r['id']:r for r in json.loads((previous/'validation-before.json').read_text())}
    for k,r in parent.items():
        r['parent_passed']=r['passed']; r['retained_adapter_passed']=retained[k]['passed']
        r['passed']=r['parent_passed'] or r['retained_adapter_passed']
        r['gate_semantics']='union of parent and retained passing cases; not a single-model baseline score'
    new=[r for r in validation if r['id'] not in parent]
    parent.update({r['id']:r for r in grade('new-before',new,infer('new-before',warm,new))}); before=[parent[r['id']] for r in validation]; save(out/'validation-before.json',before)
    phase('training')
    command=[sys.executable,'-m','mlx_lm','lora','--model',str(model),'--data',str(data),'--train','--iters','1200','--batch-size','2','--num-layers','16','--learning-rate','0.00002','--max-seq-length','1024','--mask-prompt','--seed','42','--steps-per-report','20','--steps-per-eval','1200','--val-batches','-1','--save-every','400','--resume-adapter-file',str(warm/'adapters.safetensors'),'--adapter-path',str(out/'adapter')]
    save(out/'training-command.json',command); child(command,out/'training.log',timeout=7200)
    trials={}; chosen=None
    for step in (400,800,1200):
        adapter=out/f'checkpoint-{step}'; adapter.mkdir(); shutil.copy2(out/'adapter'/f'{step:07d}_adapters.safetensors',adapter/'adapters.safetensors'); shutil.copy2(out/'adapter/adapter_config.json',adapter/'adapter_config.json')
        scores=grade(f'validation-{step}',validation,infer(f'validation-{step}',adapter,validation)); trials[str(step)]={**qualification(before,scores),'adapter_sha256':digest(adapter/'adapters.safetensors')}; save(out/'trials.json',trials)
        if trials[str(step)]['eligible']:chosen=step; break
    result={'selected_step':chosen,'trials':trials,'fresh_photo_tests_opened':False,'default_adapter_replaced':False,'manufacturing_authorized':False}
    if chosen is not None:
        tests=[r for r in more if r['split']=='test']
        base=grade('fresh-before',tests,infer('fresh-before',warm,tests)); candidate=grade('fresh-after',tests,infer('fresh-after',out/f'checkpoint-{chosen}',tests))
        result.update(fresh_photo_tests_opened=True,fresh_result=qualification(base,candidate))
    assert all(digest(Path(f))==h for f,h in frozen.items())
    assert digest(selected/'adapters.safetensors')==old.PRIOR_SHA
    assert all(digest(Path(f))==h for f,h in prior_manifest['native_sha256'].items())
    accepted=chosen is not None and result['fresh_result']['eligible']
    save(out/'results.json',result); phase('complete_candidate_only' if accepted else 'complete_rejected'); print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
