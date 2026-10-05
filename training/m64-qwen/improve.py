#!/usr/bin/env python3
"""Continue the local coding adapter; choose on validation, then open the test set once."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys

from dataset import ROOT, digest
from run import child, save
import picogk


def select(before, candidates, focus_picogk=False):
    """Select by validation gains, preserving the required per-case passes."""
    eligible=[]
    for step,result in candidates.items():
        for domain in ('usd','picogk'):
            if [r['id'] for r in before[domain]] != [r['id'] for r in result[domain]]:
                raise ValueError('validation coverage differs')
        if focus_picogk:
            if any(b['passed'] and not a['passed'] for d in ('usd','picogk') for b,a in zip(before[d],result[d])):continue
            pico=sum(r['passed'] for r in result['picogk'])
            if pico<=sum(r['passed'] for r in before['picogk']):continue
            eligible.append((pico,sum(r['passed'] for r in result['usd']),-step,step))
            continue
        if any(b['passed'] and not a['passed'] for b,a in zip(before['picogk'],result['picogk'])):continue
        usd=sum(r['passed'] for r in result['usd'])
        if usd<=sum(r['passed'] for r in before['usd']):continue
        eligible.append((usd,sum(r['passed'] for r in result['picogk']),-step,step))
    return max(eligible)[-1] if eligible else None


def split_rows(usd, pico, split, replay_weight=1, usd_replay_weight=1):
    rows=[r for r in usd+pico if r['split']==split]
    if split=='train':
        rows += [r for r in pico if r['split']=='train' and r['id'].startswith('train-')]*(replay_weight-1)
        rows += [r for r in usd if r['split']=='train']*(usd_replay_weight-1)
    return rows


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('output','previous','model','usd-python','usd-reviewed','sdk','dll'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--warm-start',type=Path,help='Adapter directory for a validation-driven continuation')
    p.add_argument('--usd-extra',type=Path,help='Additional verified USD training and fresh test examples; cannot alter validation')
    p.add_argument('--iterations',type=int,default=800)
    p.add_argument('--learning-rate',type=float,default=0.0001)
    p.add_argument('--replay-weight',type=int,default=1,help='Training-only repeat count of the original PicoGK examples')
    p.add_argument('--usd-replay-weight',type=int,default=1,help='Training-only repeat count of the OpenUSD examples')
    p.add_argument('--focus-picogk',action='store_true',help='Continue a completed coding run with fresh graphs and a single final checkpoint')
    p.add_argument('--num-layers',type=int,choices=[4,16],default=4)
    a=p.parse_args()
    if not 2<=a.iterations<=4000 or a.iterations%2 or not 0<a.learning_rate<=0.001 or not all(1<=w<=16 for w in (a.replay_weight,a.usd_replay_weight)):
        p.error('require even iterations 2..4000, learning rate (0,0.001], replay weight 1..16')
    # Resolving the Python symlink bypasses its venv and loses the Pixar package.
    for name,value in vars(a).items():
        if isinstance(value,Path):setattr(a,name,value.absolute() if name=='usd_python' else value.resolve())
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',DOTNET_CLI_TELEMETRY_OPTOUT='1')
    config=json.loads((ROOT/'training/m64-qwen/model.json').read_text())
    if digest(a.model/'model.safetensors')!=config['weights_sha256']:raise ValueError('base weights differ')
    if importlib.metadata.version('mlx-lm')!=config['mlx_lm_version']:raise ValueError('MLX version differs')
    if shutil.disk_usage(ROOT).free<2*1024**3:raise ValueError('need 2 GiB working reserve')
    import subprocess
    subprocess.run([str(a.usd_python),'-c','from pxr import Usd; assert Usd.GetVersion() == (0,25,5)'],check=True)
    previous=json.loads((a.previous/'manifest.json').read_text())
    for filename,key in [('usd-cases.jsonl','usd_cases_sha256'),('picogk-cases.json','picogk_cases_sha256')]:
        expected=previous['files_sha256'][filename] if a.focus_picogk else previous[key]
        if digest(a.previous/filename)!=expected:raise ValueError('previous corpus changed')
    initial_adapter=a.previous/'adapter'
    expected_adapter='c7d62072762ceafdf79c76d39aeccdefd8f5371196784f409417725cec0ae434'
    if a.focus_picogk:
        prior_result=json.loads((a.previous/'results.json').read_text())
        initial_adapter=a.previous/f'checkpoint-{prior_result["selected_step"]}'
        expected_adapter=prior_result['adapter_sha256']
    warm_start=a.warm_start or initial_adapter
    if digest(initial_adapter/'adapters.safetensors')!=expected_adapter:raise ValueError('previous adapter changed')
    a.output.mkdir(parents=True,exist_ok=False)
    def phase(name):
        save(a.output/'status.json',{'phase':name});print(name,flush=True)
    phase('prepare')
    usd_files=[a.previous/'usd-cases.jsonl'] if a.focus_picogk else [a.previous/'usd-cases.jsonl',a.usd_reviewed]
    usd=[json.loads(x) for file in usd_files for x in file.read_text().splitlines()]
    if a.usd_extra:
        extra=[json.loads(x) for x in a.usd_extra.read_text().splitlines()]
        if any(r['split'] not in ('train','test') or r['domain']!='openusd' for r in extra):
            raise ValueError('extra USD examples must be training or fresh tests only')
        usd+=extra
    spec=importlib.util.spec_from_file_location('engineering_data',ROOT/'training/m64-engineer/dataset.py')
    engineering=importlib.util.module_from_spec(spec);spec.loader.exec_module(engineering)
    engineering.check(usd)
    fresh=picogk.expanded_corpus(3 if a.focus_picogk else 2)
    pico=json.loads((a.previous/'picogk-cases.json').read_text())+fresh
    rows=usd+pico
    if len({r['id'] for r in rows})!=len(rows) or len({r['messages'][1]['content'] for r in rows})!=len(rows):
        raise ValueError('duplicate case or prompt')
    data=a.output/'data';data.mkdir()
    effective_counts={}
    for split in ('train','valid','test'):
        part=split_rows(usd,pico,split,a.replay_weight,a.usd_replay_weight)
        effective_counts[split]=len(part)
        (data/(split+'.jsonl')).write_text(''.join(json.dumps({'messages':r['messages']})+'\n' for r in part))
    (a.output/'usd-cases.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in usd))
    save(a.output/'picogk-cases.json',pico)
    from mlx_lm import load
    network,tok=load(str(a.model),tokenizer_config={'trust_remote_code':False})
    lengths=[len(tok.apply_chat_template(r['messages'],tokenize=True)) for r in rows]
    if max(lengths)>1024:raise ValueError('sequence would be truncated')
    del network,tok
    sources=[Path(__file__).resolve(),ROOT/'training/m64-qwen/picogk.py',ROOT/'training/m64-engineer/openusd.py']
    manifest={'base_model':{k:v for k,v in config.items() if k!='training'},
        'initial_adapter_sha256':digest(initial_adapter/'adapters.safetensors'),
        'source_sha256':{str(f.relative_to(ROOT)):digest(f) for f in sources},
        'files_sha256':{str(f.relative_to(a.output)):digest(f) for f in [a.output/'usd-cases.jsonl',a.output/'picogk-cases.json',*sorted(data.glob('*.jsonl'))]},
        'counts':{s:{'usd':sum(r['split']==s for r in usd),'picogk':sum(r['split']==s for r in pico)} for s in ('train','valid','test')},
        'maximum_sequence_tokens':max(lengths),'steps':[a.iterations] if a.focus_picogk else [a.iterations//2,a.iterations],'learning_rate':a.learning_rate,'seed':42,
        'warm_start_sha256':digest(warm_start/'adapters.safetensors'),'replay_weight':a.replay_weight,'usd_replay_weight':a.usd_replay_weight,'effective_counts':effective_counts,
        'extra_usd_sha256':digest(a.usd_extra) if a.usd_extra else None,
        'num_layers':a.num_layers,'rank':8,'lora_scale':20,'batch_size':1,'mask_prompt':True,
        'selection':'Higher PicoGK validation count with no per-case USD or PicoGK regression.' if a.focus_picogk else 'Higher USD validation pass count; no per-case PicoGK validation regression; ties use PicoGK count then earlier step.',
        'test_policy':'Tests open only after selection. Fresh cases: pico3-test and registered extra USD tests if provided. All older tests are regressions. Shared grammar, not independent families.',
        'native_sha256':{f.name:digest(f) for f in [a.dll,a.dll.parent/'picogk.26.2.dylib']}}
    save(a.output/'manifest.json',manifest)
    phase('native_oracles')
    def oracle(row):
        if picogk.signature(picogk.parse(row['messages'][-1]['content'])[1])!=picogk.signature(row['expected']):raise ValueError('oracle semantics')
        result=picogk.witness(row['messages'][-1]['content'],a.output/('oracle-'+row['id']),a.sdk,a.dll)
        if not result['compiled'] or not result['native_passed']:raise ValueError('native oracle failed')
        return {'id':row['id'],**result}
    for row in fresh:
        if picogk.signature(picogk.parse(row['messages'][-1]['content'])[1])!=picogk.signature(row['expected']):raise ValueError('oracle semantics')
    # ponytail: sample native training witnesses; all reference literals are parsed above.
    native_rows=[r for r in fresh if r['split']!='train' or int(r['id'].rsplit('-',1)[1])<24] if a.focus_picogk else fresh
    with ThreadPoolExecutor(max_workers=4) as pool:oracles=list(pool.map(oracle,native_rows))
    save(a.output/'native-oracles.json',oracles)
    phase('training')
    command=[sys.executable,'-m','mlx_lm','lora','--model',str(a.model),'--data',str(data),
        '--train','--iters',str(a.iterations),'--batch-size','1','--num-layers',str(a.num_layers),'--learning-rate',str(a.learning_rate),
        '--max-seq-length','1024','--mask-prompt','--seed','42','--steps-per-report','20',
        '--steps-per-eval',str(a.iterations if a.focus_picogk else a.iterations//2),'--val-batches','-1','--save-every',str(a.iterations if a.focus_picogk else a.iterations//2),
        '--resume-adapter-file',str(warm_start/'adapters.safetensors'),'--adapter-path',str(a.output/'adapter')]
    save(a.output/'training-command.json',command)
    child(command,a.output/'training.log',timeout=3600)
    usd_script=ROOT/'training/m64-engineer/openusd.py'
    def evaluate(label,adapter,split):
        phase(label)
        common=['--input',str(a.output/'usd-cases.jsonl'),'--split',split]
        responses=a.output/(label+'-responses.jsonl');scores=a.output/(label+'-scores.jsonl')
        child([sys.executable,str(usd_script),'infer',*common,'--model',str(a.model),'--adapter',str(adapter),'--output',str(responses)],a.output/(label+'-infer.log'))
        child([str(a.usd_python),str(usd_script),'score',*common,'--responses',str(responses),'--output',str(scores)],a.output/(label+'-score.log'))
        folder=a.output/(label+'-picogk');folder.mkdir();save(folder/'cases.json',pico)
        child([sys.executable,str(ROOT/'training/m64-qwen/picogk.py'),'--evaluate','--split',split,'--output',str(folder),
               '--model',str(a.model),'--adapter',str(adapter),'--sdk',str(a.sdk),'--dll',str(a.dll)],a.output/(label+'-picogk.log'))
        return {'usd':[json.loads(x) for x in scores.read_text().splitlines()],
                'picogk':json.loads((folder/'adapter-evaluation.json').read_text())}
    before=evaluate('valid-before',initial_adapter,'valid')
    candidates={}
    for step in manifest['steps']:
        folder=a.output/f'checkpoint-{step}';folder.mkdir()
        shutil.copy2(a.output/'adapter'/f'{step:07d}_adapters.safetensors',folder/'adapters.safetensors')
        shutil.copy2(a.output/'adapter/adapter_config.json',folder/'adapter_config.json')
        candidates[step]=evaluate(f'valid-{step}',folder,'valid')
    selected=select(before,candidates,a.focus_picogk)
    selection={'selected_step':selected,'before':before,'candidates':candidates}
    save(a.output/'selection.json',selection)
    if selected is None:
        phase('no_validation_improvement');return
    test_before=evaluate('test-before',initial_adapter,'test')
    test_after=evaluate('test-after',a.output/f'checkpoint-{selected}','test')
    for name,expected in manifest['files_sha256'].items():
        if digest(a.output/name)!=expected:raise ValueError('frozen corpus changed')
    if digest(initial_adapter/'adapters.safetensors')!=manifest['initial_adapter_sha256']:raise ValueError('previous adapter changed')
    save(a.output/'results.json',{'manifest':manifest,'selected_step':selected,
        'adapter_sha256':digest(a.output/f'checkpoint-{selected}/adapters.safetensors'),
        'before':test_before,'after':test_after,'decision':'experimental_only'})
    phase('complete')


if __name__=='__main__':main()
