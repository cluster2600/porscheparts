"""Replay prior USD training more often; preserve frozen six-domain qualification."""
import argparse
import fcntl
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import photo_run
import refine


def weighted(rows):
    # ponytail: repeat verified training rows, add new families when measured generalisation needs them.
    return [r for r in rows if r['split']=='train' for _ in range(
        3 if r['domain']=='openusd' and r.get('retention') else
        4 if r['domain']=='calculix' else 2 if r['domain']=='engineering' else 1)]


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--output',type=Path,required=True); args=p.parse_args()
    previous=refine.ROOT/'work/qwen-engineering-003'; out=args.output.resolve()
    prior=json.loads((previous/'manifest.json').read_text()); result=json.loads((previous/'results.json').read_text())
    assert not result['fresh_photo_tests_opened']
    assert importlib.metadata.version('mlx-lm')=='0.31.3' and shutil.disk_usage(refine.ROOT).free>3*1024**3
    subprocess.run([str(refine.USD_PYTHON),'-c','from pxr import Usd; assert Usd.GetVersion()==(0,25,5)'],check=True)
    out.mkdir(exist_ok=False); lock=(refine.RUNTIME/'train.lock').open('a'); fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_IMPLICIT_TOKEN='1',HF_HUB_DISABLE_TELEMETRY='1',PXR_WORK_THREAD_LIMIT='1')
    sys.path.insert(0,str(refine.ROOT/'training/qwen-engineering-20261002'))
    old=refine.module('retention_registered',refine.ROOT/'training/qwen-engineering-20261002/run.py')
    private=refine.ROOT/'work/qwen-engineering-002/helpers'; digest,save,child,configure,exact,pico,usd=old.helpers(private)
    assert all(digest(Path(f))==h for f,h in prior['files_sha256'].items())
    assert all(digest(Path(f))==h for f,h in prior['native_sha256'].items())
    model=refine.RUNTIME/'model-cache/models--mlx-community--Qwen2.5-Coder-1.5B-Instruct-4bit/snapshots/b3252a2f97102b1fb1571fec2c9b27219a8536be'
    warm=previous/'checkpoint-1200'; selected=refine.RUNTIME/'coding-003/checkpoint-600'
    assert digest(model/'model.safetensors')==old.BASE_SHA and digest(selected/'adapters.safetensors')==old.PRIOR_SHA
    assert digest(warm/'adapters.safetensors')==result['trials']['1200']['adapter_sha256']
    rows=json.loads((previous/'cases.json').read_text()); train=weighted(rows); data=out/'data'; data.mkdir()
    for split,subset in [('train',train),('valid',[r for r in rows if r['split']=='valid']),('test',[r for r in rows if r['split']=='test'])]:
        (data/(split+'.jsonl')).write_text(''.join(json.dumps({'messages':r['messages']})+'\n' for r in subset))
    frozen={**prior['files_sha256'],str(Path(__file__).resolve()):digest(Path(__file__)),**{str(f):digest(f) for f in data.glob('*.jsonl')}}
    frozen.update({str(previous/f):digest(previous/f) for f in ('manifest.json','results.json','validation-before.json','validation-1200-responses.json','validation-1200/scores-independent.json')})
    save(out/'manifest.json',{'files_sha256':frozen,'parent_scores_sha256':digest(previous/'validation-1200/scores-independent.json'),'native_sha256':prior['native_sha256'],'warm_sha256':digest(warm/'adapters.safetensors'),
        'registered_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=refine.ROOT,text=True).strip(),'iterations':480,'batch_size':2,'learning_rate':.00001,'seed':42,'maximum_sequence_tokens':prior['maximum_sequence_tokens'],
        'distinct_training_rows':sum(r['split']=='train' for r in rows),'weighted_training_instances':len(train),'replay_weights':{'retained_usd':3,'calculix':4,'engineering':2,'other':1},
        'selection':'At least 95% per domain and preserve union of prior passing obligations and actual parent 1200 passes. Fresh photo tests only after eligibility. Shared task recipes; no default replacement or physical qualification.'})
    def phase(name):save(out/'status.json',{'phase':name});print(name,flush=True)
    from mlx_lm import load,stream_generate
    from mlx_lm.sample_utils import make_sampler
    import mlx.core as mx
    def infer(label,adapter,subset):
        phase(label); net,tok=load(str(model),adapter_path=str(adapter),tokenizer_config={'trust_remote_code':False});configure(tok);mx.random.seed(42);answers=[]
        for r in subset:
            prompt=tok.apply_chat_template(r['messages'][:2],tokenize=False,add_generation_prompt=True)
            answer=''.join(x.text for x in stream_generate(net,tok,prompt=prompt,max_tokens=1024,sampler=make_sampler(temp=0)))
            answers.append({'id':r['id'],'response':answer});save(out/(label+'-responses.json'),answers)
        del net,tok;mx.clear_cache();return answers
    common=[str(refine.ROOT/'training/qwen-engineering-20261002/run.py'),'score','--training-checkout',str(private),'--usd-python',str(refine.USD_PYTHON),'--sdk',str(refine.PICO/'dotnet/dotnet'),'--dll',str(refine.PICO/'picogk-bin/PicoGK.dll')]
    def grade(label,subset,responses):
        base=[r for r in subset if r['domain'] in old.DOMAINS];save(out/(label+'-cases.json'),base);save(out/(label+'-responses.json'),responses)
        child([str(refine.USD_PYTHON),*common,'--input',str(out/(label+'-cases.json')),'--responses',str(out/(label+'-responses.json')),'--output',str(out/label)],out/(label+'.log'),timeout=1800)
        scores=json.loads((out/label/'scores.json').read_text());answers={r['id']:photo_run.strip(r['response']) for r in responses};by_id={r['id']:r for r in subset}
        for r in scores:
            if r['domain']=='python' and r['passed']:
                try:r['passed']=refine.parameterized(answers[r['id']],by_id[r['id']]['expected'],old.calculate)
                except (ValueError,SyntaxError,ZeroDivisionError):r['passed']=False
        requests=[]
        for r in subset:
            if r['domain'] in old.DOMAINS:continue
            answer=answers[r['id']];passed=False
            try:passed=exact(answer,r['expected']) if r['domain']=='engineering' else photo_run.deck_signature(answer)==photo_run.deck_signature(r['expected']['deck'])
            except (ValueError,TypeError):pass
            scores.append({'id':r['id'],'domain':r['domain'],'passed':passed,'response_sha256':hashlib.sha256(answer.encode()).hexdigest()})
            if passed and r['domain']=='calculix':requests.append({**r['expected'],'id':r['id'],'deck':answer})
        receipts={r['id']:r for r in photo_run.native(requests)}
        for r in scores:
            if r['id'] in receipts:r['native']=receipts[r['id']];r['passed']=receipts[r['id']]['passed']
        scored={r['id']:r for r in scores};scores=[scored[r['id']] for r in subset];save(out/label/'scores-independent.json',scores);return scores
    validation=[r for r in rows if r['split']=='valid'];parent=json.loads((previous/'validation-1200/scores-independent.json').read_text())
    phase('verify_frozen_grader_equivalence')
    rescored=grade('parent-check',validation,json.loads((previous/'validation-1200-responses.json').read_text()))
    assert [(r['id'],r['passed'],r.get('response_sha256')) for r in rescored]==[(r['id'],r['passed'],r.get('response_sha256')) for r in parent]
    obligations={r['id']:r for r in json.loads((previous/'validation-before.json').read_text())}
    before=[{**r,'parent_passed':r['passed'],'earlier_obligation_passed':obligations[r['id']]['passed'],'passed':r['passed'] or obligations[r['id']]['passed']} for r in parent]
    save(out/'validation-obligations.json',before)
    phase('training')
    command=[sys.executable,'-m','mlx_lm','lora','--model',str(model),'--data',str(data),'--train','--iters','480','--batch-size','2','--num-layers','16','--learning-rate','0.00001','--max-seq-length','1024','--mask-prompt','--seed','42','--steps-per-report','20','--steps-per-eval','480','--val-batches','-1','--save-every','240','--resume-adapter-file',str(warm/'adapters.safetensors'),'--adapter-path',str(out/'adapter')]
    save(out/'training-command.json',command);child(command,out/'training.log',timeout=3600)
    trials={};chosen=None
    for step in (240,480):
        folder=out/f'checkpoint-{step}';folder.mkdir();shutil.copy2(out/'adapter'/f'{step:07d}_adapters.safetensors',folder/'adapters.safetensors');shutil.copy2(out/'adapter/adapter_config.json',folder/'adapter_config.json')
        scores=grade(f'validation-{step}',validation,infer(f'validation-{step}',folder,validation));trials[str(step)]={**photo_run.qualification(before,scores),'adapter_sha256':digest(folder/'adapters.safetensors')};save(out/'trials.json',trials)
        if trials[str(step)]['eligible']:chosen=step;break
    result={'selected_step':chosen,'trials':trials,'fresh_photo_tests_opened':False,'default_adapter_replaced':False,'manufacturing_authorized':False}
    if chosen is not None:
        tests=[r for r in rows if r['split']=='test' and r['id'].startswith('photo-')]
        baseline=grade('fresh-before',tests,infer('fresh-before',warm,tests));after=grade('fresh-after',tests,infer('fresh-after',out/f'checkpoint-{chosen}',tests))
        result.update(fresh_photo_tests_opened=True,fresh_result=photo_run.qualification(baseline,after))
    assert all(digest(Path(f))==h for f,h in frozen.items()) and all(digest(Path(f))==h for f,h in prior['native_sha256'].items())
    assert digest(selected/'adapters.safetensors')==old.PRIOR_SHA
    save(out/'results.json',result);phase('complete_candidate_only' if chosen is not None and result['fresh_result']['eligible'] else 'complete_rejected');print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
