"""Audit exact prompt overlap and evaluate a frozen, disjoint final subset once."""
import argparse
from collections import Counter
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import photo_run
import refine


def partition(rows):
    key=lambda r: json.dumps(r['messages'][:2],sort_keys=True,separators=(',',':'))
    pools={s:{key(r) for r in rows if r['split']==s} for s in ('train','valid','test')}
    seen=pools['train']|pools['valid']; selected=[]; excluded=[]
    for r in rows:
        if r['split']!='test':continue
        if key(r) in seen:excluded.append(r['id'])
        else:selected.append(r['id']);seen.add(key(r))
    return {'selected_ids':selected,'excluded_ids':excluded,
            'unique_train_prompts':len(pools['train']),
            'train_overlap_rows':{s:sum(r['split']==s and key(r) in pools['train'] for r in rows) for s in ('valid','test')},
            'per_domain':dict(sorted(Counter(r['domain'] for r in rows if r['id'] in selected).items())),
            'limits':'Exact prompt separation only. Shared API, formula and decision recipes; no independent-family, automotive or manufacturing qualification.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('register','evaluate'));args=p.parse_args()
    root=refine.ROOT;run=root/'work/qwen-engineering-005';out=root/'work/qwen-engineering-final-005'
    source=root/'work/qwen-engineering-003/cases.json';rows=json.loads(source.read_text())
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    audit=partition(rows)
    if args.action=='register':
        assert not (run/'fresh-after-responses.json').exists(), 'register before final predictions'
        out.mkdir(exist_ok=False)
        audit.update(cases_sha256=digest(source),script_sha256=digest(Path(__file__)),registered_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),candidate_run='qwen-engineering-005',baseline_run='qwen-engineering-003/checkpoint-1200')
        (out/'partition.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(audit,indent=2));return
    registered=json.loads((out/'partition.json').read_text())
    assert all(registered[k]==v for k,v in audit.items()) and digest(source)==registered['cases_sha256'] and digest(Path(__file__))==registered['script_sha256']
    assert not (out/'started.json').exists(), 'one final evaluation only; preserve interrupted receipts'
    result=json.loads((run/'results.json').read_text());step=result['selected_step']
    assert step is not None and result['trials'][str(step)]['eligible'], 'unchanged full validation gate must pass first'
    manifest=json.loads((run/'manifest.json').read_text())
    assert all(digest(Path(f))==h for f,h in {**manifest['files_sha256'],**manifest['native_sha256']}.items())
    lock=(refine.RUNTIME/'train.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_IMPLICIT_TOKEN='1',HF_HUB_DISABLE_TELEMETRY='1',PXR_WORK_THREAD_LIMIT='1')
    sys.path.insert(0,str(root/'training/qwen-engineering-20261002'))
    old=refine.module('disjoint_registered_runner',root/'training/qwen-engineering-20261002/run.py')
    private=root/'work/qwen-engineering-002/helpers';_,save,child,configure,exact,_,_=old.helpers(private)
    baseline=root/'work/qwen-engineering-003/checkpoint-1200';candidate=run/f'checkpoint-{step}'
    assert digest(baseline/'adapters.safetensors')==manifest['warm_sha256']
    assert digest(candidate/'adapters.safetensors')==result['trials'][str(step)]['adapter_sha256']
    save(out/'started.json',{'baseline_sha256':digest(baseline/'adapters.safetensors'),'candidate_sha256':digest(candidate/'adapters.safetensors'),'partition_sha256':digest(out/'partition.json')})
    tests=[r for r in rows if r['id'] in registered['selected_ids']];assert len(tests)==len(registered['selected_ids'])
    model=refine.RUNTIME/'model-cache/models--mlx-community--Qwen2.5-Coder-1.5B-Instruct-4bit/snapshots/b3252a2f97102b1fb1571fec2c9b27219a8536be'
    assert digest(model/'model.safetensors')==old.BASE_SHA
    from mlx_lm import load,stream_generate
    from mlx_lm.sample_utils import make_sampler
    import mlx.core as mx
    scored=[]
    for label,adapter in [('before',baseline),('after',candidate)]:
        save(out/'status.json',{'phase':label});net,tok=load(str(model),adapter_path=str(adapter),tokenizer_config={'trust_remote_code':False});configure(tok);mx.random.seed(42);responses=[]
        for row in tests:
            prompt=tok.apply_chat_template(row['messages'][:2],tokenize=False,add_generation_prompt=True)
            response=''.join(x.text for x in stream_generate(net,tok,prompt=prompt,max_tokens=1024,sampler=make_sampler(temp=0)))
            responses.append({'id':row['id'],'response':response});save(out/(label+'-responses.json'),responses)
        del net,tok;mx.clear_cache()
        save(out/(label+'-cases.json'),[r for r in tests if r['domain'] in old.DOMAINS])
        child([str(refine.USD_PYTHON),str(root/'training/qwen-engineering-20261002/run.py'),'score','--training-checkout',str(private),'--usd-python',str(refine.USD_PYTHON),'--sdk',str(refine.PICO/'dotnet/dotnet'),'--dll',str(refine.PICO/'picogk-bin/PicoGK.dll'),'--input',str(out/(label+'-cases.json')),'--responses',str(out/(label+'-responses.json')),'--output',str(out/label)],out/(label+'.log'),timeout=1800)
        scores=json.loads((out/label/'scores.json').read_text());answers={r['id']:photo_run.strip(r['response']) for r in responses};by_id={r['id']:r for r in tests};requests=[]
        for r in scores:
            if r['domain']=='python' and r['passed']:
                try:r['passed']=refine.parameterized(answers[r['id']],by_id[r['id']]['expected'],old.calculate)
                except (ValueError,SyntaxError,ZeroDivisionError):r['passed']=False
        for row in tests:
            if row['domain'] in old.DOMAINS:continue
            answer=answers[row['id']];passed=False
            try:passed=exact(answer,row['expected']) if row['domain']=='engineering' else photo_run.deck_signature(answer)==photo_run.deck_signature(row['expected']['deck'])
            except (ValueError,TypeError):pass
            scores.append({'id':row['id'],'domain':row['domain'],'passed':passed,'response_sha256':hashlib.sha256(answer.encode()).hexdigest()})
            if passed and row['domain']=='calculix':requests.append({**row['expected'],'id':row['id'],'deck':answer})
        receipts={r['id']:r for r in photo_run.native(requests)}
        for r in scores:
            if r['id'] in receipts:r['native']=receipts[r['id']];r['passed']=receipts[r['id']]['passed']
        mapped={r['id']:r for r in scores};scores=[mapped[r['id']] for r in tests];save(out/(label+'-scores.json'),scores);scored.append(scores)
    outcome=photo_run.qualification(*scored)
    assert digest(source)==registered['cases_sha256'] and digest(Path(__file__))==registered['script_sha256']
    assert all(digest(Path(f))==h for f,h in {**manifest['files_sha256'],**manifest['native_sha256']}.items())
    assert digest(candidate/'adapters.safetensors')==result['trials'][str(step)]['adapter_sha256']
    save(out/'results.json',{'qualification':outcome,'partition':registered,'previous_photo_test_fresh_label_invalid':True,'default_adapter_replaced':False,'physical_validation':False})
    save(out/'status.json',{'phase':'complete_candidate_only' if outcome['eligible'] else 'complete_rejected'});print(json.dumps(outcome,indent=2))


if __name__=='__main__':main()
