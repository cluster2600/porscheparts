"""Use the eligible experimental PicoGK plan adapter; never execute model code."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path

import pilot


def accepted(text, finish):
    if finish != 'stop': raise ValueError('Response did not reach EOS')
    return pilot.parse(text)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work',type=Path);p.add_argument('--prompt');p.add_argument('--output',type=Path)
    p.add_argument('--self-check',action='store_true');a=p.parse_args()
    if a.self_check:
        raw='{"recipe":"pipe","parameters_mm":[14,9,5],"missing":[]}'
        assert accepted(raw,'stop')['parameters_mm']==[14,9,5]
        for text,finish in [(raw,'length'),('```json\n'+raw+'\n```','stop')]:
            try:accepted(text,finish)
            except ValueError:pass
            else:raise AssertionError('Incomplete or repaired response accepted')
        print('PicoGK inference boundary self-check passed');return
    if not a.work or not a.prompt or not a.output:p.error('--work, --prompt and --output required')
    if a.output.exists() or not a.output.parent.is_dir():p.error('Use a new output file in an existing directory')
    work=a.work.resolve();pilot.verify(work);run=work/'run-001';result=pilot.load(run/'results.json')
    if not result.get('test_opened') or not all(result[k]['eligible'] for k in ('validation','retention','test')):
        p.error('Adapter did not pass the registered bounded gates')
    adapter=run/'adapter'
    if pilot.digest(adapter/'adapters.safetensors')!=result['adapter_sha256']:p.error('Adapter hash changed')
    lock=(pilot.RUNTIME/'train.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_IMPLICIT_TOKEN='1',HF_HUB_DISABLE_TELEMETRY='1')
    from mlx_lm import load,stream_generate
    from mlx_lm.sample_utils import make_sampler
    import mlx.core as mx
    mx.set_memory_limit(8*1024**3);mx.set_cache_limit(256*1024**2);mx.random.seed(9931212)
    model,tok=load(str(pilot.BASE),adapter_path=str(adapter),tokenizer_config={'trust_remote_code':False})
    tok.add_eos_token('<|im_end|>')
    prompt=tok.apply_chat_template([{'role':'system','content':pilot.SYSTEM},{'role':'user','content':a.prompt}],tokenize=False,add_generation_prompt=True)
    if len(tok.encode(prompt))>1024:p.error('Prompt exceeds the registered course context limit')
    text='';last=None
    for last in stream_generate(model,tok,prompt=prompt,max_tokens=192,sampler=make_sampler(temp=0)):text+=last.text
    receipt={'raw_response':text,'adapter_sha256':result['adapter_sha256'],'prompt_sha256':hashlib.sha256(a.prompt.encode()).hexdigest(),
             'semantic_intent_verified':False,'geometry_executed':False,'manufacturing_qualified':False}
    try:
        receipt.update(plan=accepted(text,last.finish_reason if last else None),structure_passed=True)
    except ValueError as e:receipt.update(plan=None,structure_passed=False,error=str(e))
    pilot.save(a.output,receipt);print(json.dumps(receipt,ensure_ascii=False,indent=2))
    if not receipt['structure_passed']:raise SystemExit(2)


if __name__=='__main__':main()
