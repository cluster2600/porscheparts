#!/usr/bin/env python3
"""Local PicoGK code fine-tuning with frozen graph tasks and real native witnesses."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

from dataset import ROOT, digest
from run import configure_tokenizer, save, child

HERE = Path(__file__).resolve().parent
SYSTEM = ('Write only C# statements for an existing PicoGK.Lattice named lattice. '
          'Use lattice.AddBeam(new Vector3(xf, yf, zf), radiusf, '
          'new Vector3(xf, yf, zf), radiusf, true/false); with numeric literals. '
          'No declarations, loops, comments, Markdown or other APIs. Coordinates are '
          'designed millimeters, not measured engine dimensions. Return one statement per edge.')
NUMBER = r'(-?(?:\d+(?:\.\d*)?|\.\d+))[fF]'
VECTOR = r'new\s+Vector3\s*\(\s*' + r'\s*,\s*'.join([NUMBER]*3) + r'\s*\)'
BEAM = re.compile(r'lattice\.AddBeam\s*\(\s*' + VECTOR + r'\s*,\s*' + NUMBER +
                  r'\s*,\s*' + VECTOR + r'\s*,\s*' + NUMBER + r'\s*,\s*(true|false)\s*\)\s*;')


def parse(text):
    text = re.sub(r'^```(?:csharp|cs)?\s*([\s\S]*?)\s*```$', r'\1', text.strip())
    beams, position = [], 0
    for match in BEAM.finditer(text):
        if text[position:match.start()].strip():
            raise ValueError('outside the literal AddBeam contract')
        values = [float(x) for x in match.groups()[:8]]
        if any(abs(x) > 100 for x in values) or not all(0.25 <= values[i] <= 5 for i in (3, 7)):
            raise ValueError('outside witness bounds')
        beams.append(values + [match[9] == 'true'])
        position = match.end()
    if text[position:].strip() or not 1 <= len(beams) <= 6:
        raise ValueError('invalid or empty literal code')
    return text, beams


def code(beams):
    def f(x): return f'{x:g}f'
    return '\n'.join('lattice.AddBeam(new Vector3(' + ', '.join(map(f, b[:3])) + '), ' + f(b[3]) +
                     ', new Vector3(' + ', '.join(map(f, b[4:7])) + '), ' + f(b[7]) +
                     ', ' + str(b[8]).lower() + ');' for b in beams)


def signature(beams):
    # Edge order/direction is irrelevant when corresponding end radii move with it.
    return sorted((min(tuple(b[:4]), tuple(b[4:8])), max(tuple(b[:4]), tuple(b[4:8])), b[8]) for b in beams)


def corpus():
    rows = []
    for split, count in [('train', 64), ('valid', 8), ('test', 16)]:
        for i in range(count):
            n = i + {'train': 0, 'valid': 100, 'test': 200}[split]
            length, height = 10 + n % 19, 6 + n % 11
            z = (n % 5) - 2
            pts = [[-length/2, 0, z], [length/2, 0, z], [length/2, height, z], [-length/2, height, z]]
            shape = ['strut', 'elbow', 'frame', 'brace'][i % 4]
            edges = {'strut': [(0,1)], 'elbow': [(0,1),(1,2)],
                     'frame': [(0,1),(1,2),(2,3),(3,0)], 'brace': [(0,2),(1,3)]}[shape]
            group = 'parameter_holdout'
            if split == 'test' and i >= 8:
                group = 'composition_holdout'
                shape = 'triangle' if i % 2 else 'spatial_tripod'
                if shape == 'triangle': edges = [(0,1),(1,2),(2,0)]
                else:
                    pts[3] = [0, height/2, 8 + i]
                    edges = [(0,3),(1,3),(2,3)]
            diameter_a = [2, 3, 4, 5][(n//4) % 4]
            diameter_b = diameter_a if n % 3 else diameter_a + 1
            rounded = n % 2 == 0
            beams = [pts[a] + [diameter_a/2] + pts[b] + [diameter_b/2] + [rounded] for a,b in edges]
            prompt = (f'Build a synthetic {shape}. Vertices in mm: ' + json.dumps(dict(zip('ABCD', pts))) +
                      '. Directed edges: ' + ', '.join('ABCD'[a]+'->'+'ABCD'[b] for a,b in edges) +
                      f'. Each edge has start diameter {diameter_a} mm and end diameter {diameter_b} mm. '
                      f'Rounded caps: {str(rounded).lower()}. Convert diameters to radii. Emit every edge exactly once.')
            rows.append({'id': f'{split}-{i:03d}', 'split': split, 'group': group,
                         'shape': shape, 'expected': beams, 'messages': [
                             {'role':'system','content':SYSTEM}, {'role':'user','content':prompt},
                             {'role':'assistant','content':code(beams)}]})
    assert len({r['messages'][1]['content'] for r in rows}) == len(rows)
    return rows


def expanded_corpus(generation=2):
    """Fresh numeric/edge instances, with shared task grammar across partitions."""
    import itertools
    import random
    rows=[]
    if generation not in (2,3):raise ValueError('unsupported curriculum generation')
    settings=[('train',128,9931),('valid',16,9932),('test',16,9933)] if generation==2 else [('train',512,19931),('valid',16,19932),('test',24,19933)]
    for split,count,seed in settings:
        rng=random.Random(seed)
        for i in range(count):
            pts=rng.sample(list(itertools.product(range(-16,17,4),repeat=3)),4)
            edges=rng.sample(list(itertools.combinations(range(4),2)),1+i%6)
            edges=[(a,b) if rng.randrange(2) else (b,a) for a,b in edges]
            da,db=rng.choice([2,3,4,5]),rng.choice([2,3,4,5])
            rounded=bool(i%2)
            beams=[list(pts[a])+[da/2]+list(pts[b])+[db/2]+[rounded] for a,b in edges]
            prompt=('Build a synthetic graph. Vertices in mm: '+json.dumps(dict(zip('ABCD',pts)))+
                    '. Directed edges: '+', '.join('ABCD'[a]+'->'+'ABCD'[b] for a,b in edges)+
                    f'. Each edge has start diameter {da} mm and end diameter {db} mm. '
                    f'Rounded caps: {str(rounded).lower()}. Convert diameters to radii. Emit every edge exactly once.')
            rows.append({'id':f'pico{generation}-{split}-{i:03d}','split':split,'group':'fresh_graph_instances',
                'shape':'graph','expected':beams,'messages':[{'role':'system','content':SYSTEM},
                {'role':'user','content':prompt},{'role':'assistant','content':code(beams)}]})
    return rows


def witness(source, folder, sdk, dll, compile_only=False):
    """Only parsed, bounded literal calls reach compilation/execution; never arbitrary model code."""
    if compile_only:
        # Compilation never executes model source; only the allowlisted path below runs.
        clean = re.sub(r'^```(?:csharp|cs)?\s*([\s\S]*?)\s*```$', r'\1', source.strip())
    else:
        clean, _ = parse(source)
    folder.mkdir()
    # Fixed project: no model-controlled MSBuild, packages, imports or command arguments.
    import html
    (folder / 'Witness.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup>'
        '<OutputType>Exe</OutputType><TargetFramework>net9.0</TargetFramework>'
        '<ImplicitUsings>enable</ImplicitUsings></PropertyGroup><ItemGroup>'
        f'<Reference Include="PicoGK"><HintPath>{html.escape(str(dll))}</HintPath></Reference>'
        '</ItemGroup></Project>')
    (folder / 'Program.cs').write_text('using System.Numerics;\nusing PicoGK;\n'
        'using Library lib = new(0.5f);\nusing Lattice lattice = new(lib);\n' + clean +
        '\nusing Voxels solid = new(lattice);\nsolid.CalculateProperties(out float volume, out BBox3 box);\n'
        'using Mesh mesh = new(solid);\nConsole.WriteLine(System.Text.Json.JsonSerializer.Serialize(new { '
        'volume, triangles = mesh.nTriangleCount(), min = new[]{box.vecMin.X,box.vecMin.Y,box.vecMin.Z}, '
        'max = new[]{box.vecMax.X,box.vecMax.Y,box.vecMax.Z} }));\n')
    result = subprocess.run([str(sdk), 'build', str(folder/'Witness.csproj'), '-c','Release', '-o',str(folder/'bin'),
                             '--nologo','-v','q'], capture_output=True, text=True, timeout=60)
    (folder/'build.log').write_text(result.stdout + result.stderr)
    if result.returncode:
        return {'compiled':False,'native_passed':False}
    if compile_only:
        return {'compiled':True,'native_passed':False}
    env = os.environ.copy()
    env['DYLD_LIBRARY_PATH'] = str(dll.parent)
    result = subprocess.run([str(sdk),str(folder/'bin/Witness.dll')], capture_output=True,text=True,timeout=30,env=env)
    (folder/'native.log').write_text(result.stdout + result.stderr)
    if result.returncode:
        return {'compiled':True,'native_passed':False}
    metrics = json.loads(result.stdout.strip().splitlines()[-1])
    return {'compiled':True,'native_passed':metrics['volume'] > 0 and metrics['triangles'] > 0,'metrics':metrics}


def evaluate(output, model, sdk, dll, adapter=None, split='test'):
    from mlx_lm import load, stream_generate
    from mlx_lm.sample_utils import make_sampler
    network, tokenizer = load(str(model), adapter_path=str(adapter) if adapter else None,
                               tokenizer_config={'trust_remote_code':False})
    configure_tokenizer(tokenizer)
    label = 'adapter' if adapter else 'base'
    results = []
    for row in json.loads((output/'cases.json').read_text()):
        if row['split'] != split: continue
        started = time.perf_counter()
        prompt = tokenizer.apply_chat_template(row['messages'][:2],tokenize=False,add_generation_prompt=True)
        text = ''.join(r.text for r in stream_generate(network,tokenizer,prompt=prompt,max_tokens=512,sampler=make_sampler(temp=0)))
        result = {'id':row['id'],'group':row['group'],'response':text,'seconds':time.perf_counter()-started,
                  'contract_passed':False,'semantic_passed':False,'compiled':False,'native_passed':False}
        try:
            _, beams = parse(text)
            result['contract_passed'] = True
            result['semantic_passed'] = signature(beams) == signature(row['expected'])
            result.update(witness(text,output/f'{label}-{row["id"]}',sdk,dll))
        except ValueError as exc:
            result['error'] = str(exc)
            result.update(witness(text,output/f'{label}-{row["id"]}',sdk,dll,compile_only=True))
        result['passed'] = all(result[k] for k in ('contract_passed','semantic_passed','compiled','native_passed'))
        results.append(result)
        print(f'{label} {row["id"]}: {result["passed"]}',flush=True)
        save(output/f'{label}-evaluation.json',results)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--sdk',type=Path,required=True)
    parser.add_argument('--dll',type=Path,required=True)
    parser.add_argument('--model',type=Path,required=True)
    parser.add_argument('--evaluate',action='store_true')
    parser.add_argument('--adapter',type=Path)
    parser.add_argument('--split',choices=['valid','test'],default='test')
    args = parser.parse_args()
    for name in ('output','sdk','dll','model'): setattr(args,name,getattr(args,name).resolve())
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',DOTNET_CLI_TELEMETRY_OPTOUT='1')
    if args.evaluate:
        evaluate(args.output,args.model,args.sdk,args.dll,args.adapter,args.split)
        return
    config = json.loads((HERE/'model.json').read_text())
    if digest(args.model/'model.safetensors') != config['weights_sha256']: raise ValueError('model hash mismatch')
    args.output.mkdir(parents=True,exist_ok=False)
    rows = corpus()
    save(args.output/'cases.json',rows)
    data = args.output/'data'; data.mkdir()
    for split in ('train','valid','test'):
        (data/f'{split}.jsonl').write_text(''.join(json.dumps({'messages':r['messages']})+'\n' for r in rows if r['split']==split))
    from mlx_lm import load
    _, tokenizer = load(str(args.model),tokenizer_config={'trust_remote_code':False})
    lengths = [len(tokenizer.apply_chat_template(r['messages'],tokenize=True)) for r in rows]
    if max(lengths)>1024: raise ValueError('sequence would be truncated')
    save(args.output/'manifest.json',{'model':config,'dataset_sha256':digest(args.output/'cases.json'),
        'source_sha256':digest(Path(__file__)),'dll_sha256':digest(args.dll),
        'native_sha256':digest(args.dll.parent/'picogk.26.2.dylib'),
        'picogk_revision':'0e6cf6b6f4993ec16dbcd72d8f27f26b999980f3',
        'sdk':subprocess.check_output([str(args.sdk),'--version'],text=True).strip(),
        'counts':{s:sum(r['split']==s for r in rows) for s in ('train','valid','test')},
        'max_sequence_tokens':max(lengths),'iterations':100,'seed':42,'learning_rate':0.0001,
        'num_layers':4,'max_seq_length':1024,'max_generation_tokens':512,
        'training_license':'New synthetic examples, repository proprietary license; local owner-authorized training',
        'promotion_rule':'All 16 semantic, compile and native checks pass; strict improvement; no per-case regression',
        'limitations':'Shared graph specification format; composition holdout is small. Not arbitrary PicoGK programs or engineering validation.'})
    # Oracle must pass before the base evaluation or training begins.
    for row in rows:
        assert signature(parse(code(row['expected']))[1]) == signature(row['expected'])
    for row in (r for r in rows if r['split']=='test'):
        result = witness(code(row['expected']),args.output/f'oracle-{row["id"]}',args.sdk,args.dll)
        if not result['native_passed']: raise RuntimeError('oracle failed')
    command = [sys.executable,str(Path(__file__).resolve()),'--output',str(args.output),'--sdk',str(args.sdk),
               '--dll',str(args.dll),'--model',str(args.model),'--evaluate']
    save(args.output/'status.json',{'phase':'base_evaluation'})
    child(command,args.output/'base.log')
    save(args.output/'status.json',{'phase':'training'})
    child([sys.executable,'-m','mlx_lm','lora','--model',str(args.model),'--data',str(data),
           '--train','--iters','100','--batch-size','1','--num-layers','4','--learning-rate','0.0001',
           '--max-seq-length','1024','--mask-prompt','--seed','42','--steps-per-report','10',
           '--steps-per-eval','50','--val-batches','-1','--save-every','100',
           '--adapter-path',str(args.output/'adapter')],args.output/'training.log',timeout=3600)
    save(args.output/'status.json',{'phase':'adapter_evaluation'})
    child(command+['--adapter',str(args.output/'adapter')],args.output/'adapter.log')
    before = json.loads((args.output/'base-evaluation.json').read_text())
    after = json.loads((args.output/'adapter-evaluation.json').read_text())
    regressions = [a['id'] for b,a in zip(before,after) if b['passed'] and not a['passed']]
    summary = {label:{key:sum(r[key] for r in results) for key in
               ('contract_passed','semantic_passed','compiled','native_passed','passed')}
               for label,results in [('base',before),('adapter',after)]}
    summary.update(total=16,regressions=regressions,
                   decision='candidate_adapter' if sum(r['passed'] for r in after)==16 and sum(r['passed'] for r in before)<16 and not regressions else 'keep_base',
                   adapter_sha256=digest(args.output/'adapter/adapters.safetensors'))
    save(args.output/'comparison.json',summary)
    save(args.output/'status.json',{'phase':'complete'})
    print(json.dumps(summary,indent=2))

if __name__ == '__main__':
    main()
