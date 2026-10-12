"""One bounded, source-pinned PicoGK plan adaptation with native geometry witnesses."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import fcntl
import hashlib
import html
import importlib.metadata
import json
import math
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'training/qwen-research-corpus'))
from prepare import sequence_length
RUNTIME = Path('/Users/maxime/.codex/worktrees/m64-local-architecture-qwen/3dprinting993/work/m64-qwen')
BASE = RUNTIME / 'model-cache/models--mlx-community--Qwen2.5-Coder-1.5B-Instruct-4bit/snapshots/b3252a2f97102b1fb1571fec2c9b27219a8536be'
PARENT = RUNTIME / 'coding-008/checkpoint-400'
PICO = Path('/Users/maxime/projects/3dprinting993/work/m64-private-20260907/nemo-picogk-20260928.ADELugEK')
USD = Path('/Users/maxime/projects/3dprinting993/work/cad-recode-tools-venv/bin/python')
RECIPES = ('cylinder', 'pipe', 'washer', 'bcc', 'thread', 'needs_measurement')
CARDS = {
    'cylinder': 'ShapeKernel BaseCylinder(LocalFrame, length, radius). parameters_mm=[length,radius].',
    'pipe': 'ShapeKernel BasePipe(LocalFrame,length,innerRadius,outerRadius). parameters_mm=[length,outerRadius,innerRadius].',
    'washer': 'PicoGK_Fasteners Fastener(fWasherThickness,fWasherDiameter,fCloseFit).Washer(LocalFrame). parameters_mm=[thickness,outerRadius,boreRadius]. Explicit dimensions; no nominal fit defaults.',
    'bcc': 'LatticeLibrary RegularUnitCell(side,side,side,noise=0); BodyCentreLattice.AddCell; ConstantBeamThickness expects DIAMETER. parameters_mm=[cellSide,beamDiameter].',
    'thread': 'HelixHeatX ThreadCutter(LocalFrame,length,maxRadius,coreRadius,slope). parameters_mm=[length,maxRadius,coreRadius,pitch]. Synthetic thread cutter; no manufactured thread standard.',
    'needs_measurement': 'Unknown measured interfaces cannot be inferred. parameters_mm=[]; missing=["measured_interfaces"].'
}
SYSTEM = ('Return one JSON object only, with exactly recipe, parameters_mm and missing. '
          'Use one supported recipe and its ordered numeric parameters in millimeters. '
          'Convert requested diameters to radii except BCC beam thickness, which is a diameter. '
          'Never infer unknown Porsche measurements or qualify a part. All complete geometry requests are synthetic. '
          'For unavailable measured interfaces use needs_measurement. No code, fences or explanations. '
          'Pinned recipe/API cards: ' + json.dumps(CARDS, ensure_ascii=False))


def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p, value):
    temporary = p.with_suffix(p.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    temporary.replace(p)
def load(p): return json.loads(p.read_text())


def unique(pairs):
    d = {}
    for k,v in pairs:
        if k in d: raise ValueError('Duplicate JSON key')
        d[k] = v
    return d


def parse(text):
    d = json.loads(text, object_pairs_hook=unique)
    if not isinstance(d,dict) or set(d) != {'recipe','parameters_mm','missing'}: raise ValueError('Plan schema')
    if d['recipe'] not in RECIPES or not isinstance(d['parameters_mm'],list) or not isinstance(d['missing'],list): raise ValueError('Plan types')
    p = d['parameters_mm']; recipe = d['recipe']
    if recipe == 'needs_measurement':
        if p or d['missing'] != ['measured_interfaces']: raise ValueError('Missing-interface contract')
        return d
    if d['missing'] or len(p) != {'cylinder':2,'pipe':3,'washer':3,'bcc':2,'thread':4}[recipe]: raise ValueError('Parameter count')
    if any(type(v) not in (int,float) or not math.isfinite(v) or not 0.5 <= v <= 24 for v in p): raise ValueError('Numeric bounds')
    if recipe in ('pipe','washer') and p[2] >= p[1]: raise ValueError('Bore must be smaller')
    if recipe == 'bcc' and (p[1] > p[0]/3 or p[0] > 18): raise ValueError('Lattice bounds')
    if recipe == 'thread' and (p[2] >= p[1] or p[3] < 2 or p[0]/p[3] > 6): raise ValueError('Thread bounds')
    return d


def matches(actual, expected):
    return (actual['recipe'] == expected['recipe'] and actual['missing'] == expected['missing'] and
            len(actual['parameters_mm']) == len(expected['parameters_mm']) and
            all(math.isclose(a,b,rel_tol=0,abs_tol=1e-6) for a,b in zip(actual['parameters_mm'],expected['parameters_mm'])))


def cases():
    rows = []; intents = set()
    for split,count,seed in [('train',40,9931201),('valid',8,9931202),('test',4,9931203)]:
        rng = random.Random(seed)
        for recipe in RECIPES:
            for i in range(count):
                while True:
                    length = 6+rng.randrange(56)/4; outer = 4+rng.randrange(28)/4
                    inner = min(1.5+rng.randrange(14)/4,outer-1.5)
                    p = {'cylinder':[length,outer], 'pipe':[length,outer,inner],
                         'washer':[2+rng.randrange(8)/4,outer,inner],
                         'bcc':[8+rng.randrange(24)/4,1.5+rng.randrange(4)/4],
                         'thread':[6+rng.randrange(24)/4,outer,inner,2+rng.randrange(5)/4],
                         'needs_measurement':[]}[recipe]
                    key = recipe+json.dumps(p)
                    if recipe == 'needs_measurement' or key not in intents: break
                intents.add(key)
                expected = {'recipe':recipe,'parameters_mm':p,'missing':['measured_interfaces'] if not p else []}
                parse(json.dumps(expected))
                unit = 'cm' if i%3==1 else 'mm'; factor = 10 if unit=='cm' else 1
                def n(value): return f'{value/factor:g}'
                french = i%2 == 0
                label = f'{split}-{recipe}-{i:03d}'
                if recipe == 'cylinder':
                    q = (f'Cylindre plein ShapeKernel : longueur {n(p[0])} {unit}, diamètre {n(2*p[1])} {unit}.' if french else
                         f'Solid ShapeKernel cylinder: length {n(p[0])} {unit}, diameter {n(2*p[1])} {unit}.')
                elif recipe in ('pipe','washer'):
                    name = ('tube ShapeKernel' if recipe=='pipe' else 'rondelle PicoGK-Fasteners') if french else ('ShapeKernel pipe' if recipe=='pipe' else 'PicoGK-Fasteners washer')
                    q = (f'{name} : longueur/épaisseur {n(p[0])} {unit}, diamètre extérieur {n(2*p[1])} {unit}, alésage {n(2*p[2])} {unit}.' if french else
                         f'{name}: length/thickness {n(p[0])} {unit}, outer diameter {n(2*p[1])} {unit}, bore diameter {n(2*p[2])} {unit}.')
                elif recipe == 'bcc':
                    q = (f'Une cellule BCC LatticeLibrary, côté {n(p[0])} {unit}, diamètre des barres {n(p[1])} {unit}, bruit zéro.' if french else
                         f'One LatticeLibrary BCC cell, side {n(p[0])} {unit}, beam diameter {n(p[1])} {unit}, zero noise.')
                elif recipe == 'thread':
                    q = (f'Outil ThreadCutter HelixHeatX : longueur {n(p[0])} {unit}, diamètre maxi {n(2*p[1])} {unit}, diamètre noyau {n(2*p[2])} {unit}, pas {n(p[3])} {unit}.' if french else
                         f'HelixHeatX ThreadCutter: length {n(p[0])} {unit}, maximum diameter {n(2*p[1])} {unit}, core diameter {n(2*p[2])} {unit}, pitch {n(p[3])} {unit}.')
                else:
                    q = (f'Reproduis les interfaces de fixation originales 993 Turbo pour dossier {label}. Aucune mesure des trous, axes ou faces n’est fournie.' if french else
                         f'Reproduce original 993 Turbo attachment interfaces for dossier {label}. No hole, axis or mating-face measurements are supplied.')
                rows.append({'id':label,'split':split,'domain':recipe,'expected':expected,
                             'language':'fr' if french else 'en','synthetic':True,
                             'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':q},
                                         {'role':'assistant','content':json.dumps(expected,separators=(',',':'))}]})
    assert len({r['id'] for r in rows})==len(rows) and len({r['messages'][1]['content'] for r in rows})==len(rows)
    return rows


def native(work, plan, folder, voxel=0.5):
    folder.mkdir(); save(folder/'plan.json',plan)
    env = os.environ.copy(); env['DYLD_LIBRARY_PATH'] = str(PICO/'picogk-bin')
    r = subprocess.run([str(PICO/'dotnet/dotnet'),str(work/'host/bin/GeometryHost.dll'),str(folder/'plan.json'),
                        str(folder/'raw.stl'),str(voxel)],env=env,capture_output=True,text=True,timeout=45)
    (folder/'native.log').write_text(r.stdout+r.stderr)
    if r.returncode: raise ValueError('Native geometry failed; see receipt')
    d = json.loads(r.stdout.strip().splitlines()[-1]); p = plan['parameters_mm']
    okay = (d['volume']>0 and d['triangles']>0 and d['roundtrip_triangles']==d['triangles'] and
            d['material_inside'] and not d['distant_point_inside'] and
            d['axis_inside']==(plan['recipe'] not in ('pipe','washer')))
    if plan['recipe'] in ('cylinder','pipe','washer'):
        analytic = math.pi*(p[1]**2-(p[2]**2 if len(p)==3 else 0))*p[0]
        d['analytic_volume_mm3']=analytic; d['relative_volume_error']=abs(d['volume']-analytic)/analytic
        okay = okay and d['relative_volume_error']<=0.15
    d.update(geometry_screen_passed=bool(okay),raw_stl_sha256=digest(folder/'raw.stl'),manufacturing_qualified=False)
    save(folder/'metrics.json',d); return d


def build_host(work):
    sources = [HERE/'GeometryHost.cs']
    for repo,folders in [('LEAP71_ShapeKernel',['ShapeKernel']),('LEAP71_LatticeLibrary',['LatticeLibrary','ImplicitLibrary']),('LEAP71_HelixHeatX',['src'])]:
        for folder in folders: sources += sorted((work/'sources'/repo/folder).rglob('*.cs'))
    sources += [work/'sources/PicoGK-Fasteners'/name for name in ('FastenerTools.cs','FastenerUtils.cs')]
    items = ''.join('<Compile Include="'+html.escape(str(p))+'" />' for p in sources)
    host = work/'host'; host.mkdir(exist_ok=True)
    (host/'GeometryHost.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net9.0</TargetFramework><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable><EnableDefaultCompileItems>false</EnableDefaultCompileItems></PropertyGroup><ItemGroup>'+items+'<Reference Include="PicoGK"><HintPath>'+str(PICO/'picogk-bin/PicoGK.dll')+'</HintPath></Reference></ItemGroup></Project>')
    with (host/'build.log').open('w') as log:
        subprocess.run([str(PICO/'dotnet/dotnet'),'build',str(host/'GeometryHost.csproj'),'-c','Release','-o',str(host/'bin'),'--nologo','-v','q'],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
    env=os.environ.copy();env['DYLD_LIBRARY_PATH']=str(PICO/'picogk-bin')
    (work/'api-catalog.json').write_text(subprocess.check_output([str(PICO/'dotnet/dotnet'),str(host/'bin/GeometryHost.dll'),'--api'],env=env,text=True))
    return sources


def prepare(work):
    dataset=work/'dataset';dataset.mkdir()
    sources=build_host(work); rows=cases()
    previous=RUNTIME/'coding-008'; old_manifest=load(previous/'manifest.json')
    old_usd=[json.loads(s) for s in (previous/'usd-cases.jsonl').read_text().splitlines()]
    old_pico=load(previous/'picogk-cases.json')
    for name in ('usd-cases.jsonl','picogk-cases.json'):
        if digest(previous/name)!=old_manifest['files_sha256'][name]:raise ValueError('Historical data changed')
    rng=random.Random(9931210); replay=[]; retention=[]
    for domain,pool in [('openusd',old_usd),('picogk',old_pico)]:
        replay += rng.sample([r for r in pool if r['split']=='train'],96)
        retention += [{**r,'domain':domain} for r in rng.sample([r for r in pool if r['split']=='valid'],8)]
    save(dataset/'cases.json',rows);save(dataset/'retention.json',retention)
    data=dataset/'data';data.mkdir()
    for split in ('train','valid'):
        selected=[r for r in rows if r['split']==split]+(replay if split=='train' else [])
        (data/(split+'.jsonl')).write_text(''.join(json.dumps({'messages':r['messages']},ensure_ascii=False)+'\n' for r in selected))
    from transformers import AutoTokenizer
    tokenizer=AutoTokenizer.from_pretrained(str(BASE),local_files_only=True,trust_remote_code=False)
    lengths=[sequence_length(tokenizer.apply_chat_template(r['messages'],tokenize=True)) for r in rows+replay]
    if max(lengths)>1024:raise ValueError('Sequence truncation forbidden')
    reference=dataset/'reference';reference.mkdir()
    for row in rows:
        if row['split']=='valid' and row['domain']!='needs_measurement':
            if not native(work,row['expected'],reference/row['id'])['geometry_screen_passed']:raise ValueError('Gold native check failed')
    files=[HERE/'pilot.py',ROOT/'training/qwen-research-corpus/prepare.py',ROOT/'training/qwen-research-corpus/curriculum.py',
           ROOT/'training/qwen-porsche-corpus/corpus.py',ROOT/'training/qwen-porsche-corpus/train.py',
           *sources,work/'api-catalog.json',work/'retrieved.json',
           *sorted(dataset.glob('*.json')),*sorted(data.glob('*.jsonl')),work/'host/bin/GeometryHost.dll',
           ROOT/'training/m64-qwen/picogk.py',ROOT/'training/m64-qwen/run.py',ROOT/'training/m64-qwen/dataset.py',
           ROOT/'training/m64-engineer/openusd.py',ROOT/'training/qwen-engineering-20261002/run.py',ROOT/'training/qwen-engineering-20261002/curriculum.py',
           PICO/'picogk-bin/PicoGK.dll',PICO/'picogk-bin/picogk.26.2.dylib',PARENT/'adapters.safetensors',PARENT/'adapter_config.json',
           BASE/'model.safetensors',*sorted(BASE.glob('*.json')),BASE/'merges.txt']
    for item in load(work/'retrieved.json'):
        files += [p for p in Path(item['path']).rglob('*') if p.is_file() and '.git' not in p.parts and (p.suffix in ('.cs','.md') or p.name=='LICENSE')]
    save(dataset/'FROZEN.json',{'files':{str(p):digest(p) for p in dict.fromkeys(files)},'counts':dict(Counter(r['split'] for r in rows)),
         'training_rows':240+192,'maximum_tokens':max(lengths),'retention_cases':16,
         'limits':'Synthetic scenario-disjoint shared recipes; native screening, not general API mastery, meshing or physical qualification.'})
    print('Prepared 432 training, 48 validation, 24 closed test and 16 old retention cases',flush=True)


def verify(work):
    frozen=load(work/'dataset/FROZEN.json')
    if any(digest(Path(p))!=h for p,h in frozen['files'].items()):raise ValueError('Frozen input changed')
    return frozen


def gate(before,after):
    if [r['id'] for r in before]!=[r['id'] for r in after]:raise ValueError('Evaluation coverage differs')
    counts={k:{'before':sum(r['passed'] for r in before if r['domain']==k),'after':sum(r['passed'] for r in after if r['domain']==k),
               'total':sum(r['domain']==k for r in after)} for k in sorted({r['domain'] for r in after})}
    regressions=[b['id'] for b,a in zip(before,after) if b['passed'] and not a['passed']]
    return {'counts':counts,'regressions':regressions,'eligible':not regressions and all(v['after']>=math.ceil(0.95*v['total']) for v in counts.values())}


def run(work):
    frozen=verify(work);out=work/'run-001';out.mkdir()
    lock=(RUNTIME/'train.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if importlib.metadata.version('mlx-lm')!='0.31.3':raise ValueError('MLX runtime changed')
    if digest(PARENT/'adapters.safetensors')!='09024cfb346f3dd7f8994e5fe1cd89e11976db5354b8dac9c0167d57ee7aacb6':raise ValueError('Parent changed')
    if digest(BASE/'model.safetensors')!='daeab4764fb420d161721791cf2e509e2de81a7af4223646e7bed2bf82c57b58':raise ValueError('Base changed')
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_IMPLICIT_TOKEN='1',HF_HUB_DISABLE_TELEMETRY='1',DOTNET_CLI_TELEMETRY_OPTOUT='1',PXR_WORK_THREAD_LIMIT='1',OMP_NUM_THREADS='2')
    command=[sys.executable,'-m','mlx_lm','lora','--model',str(BASE),'--data',str(work/'dataset/data'),'--train','--iters','480','--batch-size','2','--num-layers','16','--learning-rate','0.000005','--max-seq-length','1024','--mask-prompt','--seed','9931212','--steps-per-report','40','--steps-per-eval','480','--val-batches','-1','--save-every','480','--resume-adapter-file',str(PARENT/'adapters.safetensors'),'--adapter-path',str(out/'adapter')]
    protocol={'registered_at':datetime.now(timezone.utc).isoformat(),'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
              'frozen_sha256':digest(work/'dataset/FROZEN.json'),'frozen_inputs':frozen,'training_command':command,
              'generation':{'seed':9931212,'temperature':0,'plan_max_tokens':192,'retention_max_tokens':1024},
              'selection':'Only final step 480. Every new category >=95%, no lost baseline pass, all old retention passes preserved; only then compare the fresh final cases once. No default adoption.',
              'runtime':{p:importlib.metadata.version(p) for p in ('mlx','mlx-lm','transformers')},'limits':frozen['limits']}
    save(out/'protocol.json',protocol);protocol_hash=digest(out/'protocol.json')
    from mlx_lm import load as load_model,stream_generate
    from mlx_lm.sample_utils import make_sampler
    import mlx.core as mx
    mx.set_memory_limit(8*1024**3);mx.set_cache_limit(256*1024**2)
    rows=load(work/'dataset/cases.json');retention=load(work/'dataset/retention.json')
    def infer(label,adapter,selected,maximum=192):
        model,tok=load_model(str(BASE),adapter_path=str(adapter),tokenizer_config={'trust_remote_code':False})
        tok.add_eos_token('<|im_end|>');mx.random.seed(9931212)
        answers=[]
        for row in selected:
            prompt=tok.apply_chat_template(row['messages'][:2],tokenize=False,add_generation_prompt=True)
            last=None;text=''
            for last in stream_generate(model,tok,prompt=prompt,max_tokens=maximum,sampler=make_sampler(temp=0)):text+=last.text
            if last is None:raise ValueError('No model response')
            answers.append({'id':row['id'],'response':text,'tokens':last.generation_tokens,'finish_reason':last.finish_reason})
            save(out/(label+'-answers.json'),answers);print(label,len(answers),'/',len(selected),flush=True)
        del model,tok;mx.clear_cache();return answers
    def grade(label,selected,answers):
        folder=out/label;folder.mkdir();scored=[]
        for row,answer in zip(selected,answers):
            item={'id':row['id'],'domain':row['domain'],'passed':False,'complete':answer['finish_reason']=='stop'}
            try:
                plan=parse(answer['response']);item['intent_passed']=matches(plan,row['expected'])
                if plan['recipe']=='needs_measurement':item['native_required']=False;okay=True
                else:item['native']=native(work,plan,folder/row['id']);okay=item['native']['geometry_screen_passed']
                item['passed']=item['intent_passed'] and item['complete'] and okay
            except (ValueError,TypeError,KeyError,subprocess.TimeoutExpired) as e:item['error']=str(e)
            scored.append(item)
        save(out/(label+'-scores.json'),scored);return scored
    def old_grade(label,answers):
        responses=out/(label+'-responses.json');save(responses,answers)
        cmd=[str(USD),str(ROOT/'training/qwen-engineering-20261002/run.py'),'score','--training-checkout',str(ROOT),'--usd-python',str(USD),'--sdk',str(PICO/'dotnet/dotnet'),'--dll',str(PICO/'picogk-bin/PicoGK.dll'),'--input',str(work/'dataset/retention.json'),'--responses',str(responses),'--output',str(out/label)]
        with (out/(label+'.log')).open('w') as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=1200)
        return load(out/label/'scores.json')
    reference=old_grade('retention-reference',[{'id':r['id'],'response':r['messages'][-1]['content']} for r in retention])
    if not all(r['passed'] for r in reference):raise ValueError('Old native reference failed')
    valid=[r for r in rows if r['split']=='valid']
    before=grade('valid-before',valid,infer('valid-before',PARENT,valid))
    old_before=old_grade('retention-before',infer('retention-before',PARENT,retention,1024))
    print('training',flush=True)
    with (out/'training.log').open('w') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=3600)
    if any(token in (out/'training.log').read_text().lower() for token in ('nan','inf loss')):raise ValueError('Non-finite training metric')
    tensors=mx.load(str(out/'adapter/adapters.safetensors'))
    if not tensors or not all(bool(mx.all(mx.isfinite(v)).item()) for v in tensors.values()):raise ValueError('Non-finite adapter tensors')
    save(out/'adapter-finiteness.json',{'arrays':len(tensors),'all_finite':True,'parameters':sum(v.size for v in tensors.values())})
    after=grade('valid-after',valid,infer('valid-after',out/'adapter',valid))
    old_after=old_grade('retention-after',infer('retention-after',out/'adapter',retention,1024))
    results={'validation':gate(before,after),'retention':gate(old_before,old_after),'weights_updated':True,'default_replaced':False,'manufacturing_qualified':False,'test_opened':False,'adapter_sha256':digest(out/'adapter/adapters.safetensors')}
    if results['validation']['eligible'] and results['retention']['eligible']:
        tests=[r for r in rows if r['split']=='test']
        tb=grade('test-before',tests,infer('test-before',PARENT,tests));ta=grade('test-after',tests,infer('test-after',out/'adapter',tests))
        results.update(test_opened=True,test=gate(tb,ta))
    verify(work)
    if digest(out/'protocol.json')!=protocol_hash:raise ValueError('Protocol changed')
    save(out/'results.json',results);print(json.dumps(results),flush=True)


def self_check():
    assert sequence_length({'input_ids':[1,2,3],'attention_mask':[1,1,1]})==3
    assert sequence_length([1,2,3])==3
    rows=cases();assert len(rows)==312
    assert all(matches(parse(r['messages'][-1]['content']),r['expected']) for r in rows)
    row=rows[0];correct=row['expected'];assert gate([{'id':'a','domain':'cylinder','passed':True}],[{'id':'a','domain':'cylinder','passed':True}])['eligible']
    for bad in [dict(correct,parameters_mm=[True,5]),dict(correct,parameters_mm=[float('nan'),5]),dict(correct,extra='ignore schema'),{'recipe':'pipe','parameters_mm':[5,3,3],'missing':[]}]:
        try:parse(json.dumps(bad))
        except ValueError:pass
        else:raise AssertionError('Invalid plan admitted')
    try:parse('{"recipe":"cylinder","recipe":"pipe","parameters_mm":[5,4,2],"missing":[]}')
    except ValueError:pass
    else:raise AssertionError('Duplicate key admitted')
    assert not matches({'recipe':'cylinder','parameters_mm':[correct['parameters_mm'][0],correct['parameters_mm'][1]*2],'missing':[]},correct)
    print('PicoGK course self-check passed: partitions, units, strict plans and gates')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['self-check','prepare','run']);p.add_argument('--work',type=Path)
    a=p.parse_args()
    if a.action=='self-check':self_check()
    else:
        if not a.work:p.error('--work required')
        (prepare if a.action=='prepare' else run)(a.work.resolve())
