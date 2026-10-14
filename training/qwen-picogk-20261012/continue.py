"""One registered ambiguous-vertex correction; preserve the first PicoGK pilot."""
import argparse
import importlib.util
import itertools
import json
from pathlib import Path
import random
import sys

import pilot


def prepare(previous, work):
    pilot.verify(previous); work.mkdir()
    (work/'dataset').symlink_to(previous/'dataset',target_is_directory=True)
    (work/'host').symlink_to(previous/'host',target_is_directory=True)
    data=work/'data';data.mkdir()
    sys.path.insert(0,str(pilot.ROOT/'training/m64-qwen'))
    import picogk
    rng=random.Random(9931220); extra=[]; prompts=set()
    historical=json.loads((pilot.RUNTIME/'coding-008/picogk-cases.json').read_text())
    blocked={r['messages'][1]['content'] for r in historical if r['split']!='train'}
    for i in range(256):
        while True:
            x,y,z=[rng.choice(range(-16,5,4)) for _ in range(3)]
            dx,dy,dz=[rng.choice([4,8,12]) for _ in range(3)]
            points=[[x,y,z],[x,y+dy,z+dz],[x+dx,y,z+dz],[x+dx,y+dy,z]]
            edges=rng.sample(list(itertools.combinations(range(4),2)),6 if i%2 else 3+i%4)
            edges=[(b,a) if rng.randrange(2) else (a,b) for a,b in edges]
            da,db=rng.sample([2,3,4,5],2);rounded=bool(i%2)
            prompt=('Build a synthetic graph. Vertices in mm: '+json.dumps(dict(zip('ABCD',points)))+
                    '. Directed edges: '+', '.join('ABCD'[a]+'->'+'ABCD'[b] for a,b in edges)+
                    f'. Each edge has start diameter {da} mm and end diameter {db} mm. '
                    f'Rounded caps: {str(rounded).lower()}. Convert diameters to radii. Emit every edge exactly once.')
            if prompt not in prompts and prompt not in blocked:break
        prompts.add(prompt)
        expected=[points[a]+[da/2]+points[b]+[db/2]+[rounded] for a,b in edges]
        assert len(picogk.signature(expected))==len(set(picogk.signature(expected)))==len(edges)
        text=picogk.code(expected);assert picogk.signature(picogk.parse(text)[1])==picogk.signature(expected)
        extra.append({'messages':[{'role':'system','content':picogk.SYSTEM},{'role':'user','content':prompt},{'role':'assistant','content':text}]})
    old=[json.loads(x) for x in (previous/'dataset/data/train.jsonl').read_text().splitlines()]
    (data/'train.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in old+extra))
    (data/'valid.jsonl').write_bytes((previous/'dataset/data/valid.jsonl').read_bytes())
    from transformers import AutoTokenizer
    tok=AutoTokenizer.from_pretrained(str(pilot.BASE),local_files_only=True,trust_remote_code=False)
    maximum=max(pilot.sequence_length(tok.apply_chat_template(r['messages'],tokenize=True)) for r in old+extra)
    if maximum>1024:raise ValueError('Sequence truncation forbidden')
    bindings=[Path(__file__),pilot.HERE/'pilot.py',pilot.ROOT/'training/m64-qwen/picogk.py',
              data/'train.jsonl',data/'valid.jsonl',previous/'run-001/adapter/adapters.safetensors',
              previous/'run-001/adapter/adapter_config.json',previous/'run-001/adapter-finiteness.json']
    pilot.save(work/'continuation.json',{'previous':str(previous),'training_rows':len(old+extra),'additional_graphs':256,
        'maximum_tokens':maximum,'source_exclusions':'Only old train rows and new synthetic graphs; no known validation/test prompts copied.',
        'iterations':240,'learning_rate':0.0000025,'files':{str(p):pilot.digest(p) for p in bindings}})


def run(work):
    registration=pilot.load(work/'continuation.json')
    if any(pilot.digest(Path(p))!=h for p,h in registration['files'].items()):raise ValueError('Continuation input changed')
    previous=Path(registration['previous']);original_save=pilot.save
    def register(path,value):
        if path.name=='protocol.json':
            command=value['training_command']
            changes={'--data':str(work/'data'),'--resume-adapter-file':str(previous/'run-001/adapter/adapters.safetensors'),
                     '--iters':'240','--save-every':'240','--steps-per-eval':'240','--learning-rate':'0.0000025'}
            for flag,text in changes.items():command[command.index(flag)+1]=text
            value['frozen_inputs']['files'].update(registration['files'])
            value.update(continuation=registration,baseline='Original coding-008; fresh matched answers under unchanged profiles.',
                         selection='Fixed final step 240. Same >=95% per-category and no-regression gates. First pilot and old results unchanged; no default promotion. Final cases stay closed unless eligible.')
        original_save(path,value)
    pilot.save=register
    pilot.run(work)
    if any(pilot.digest(Path(p))!=h for p,h in registration['files'].items()):raise ValueError('Continuation input changed during run')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','run']);p.add_argument('--work',type=Path,required=True);p.add_argument('--previous',type=Path)
    a=p.parse_args()
    if a.action=='prepare':
        if not a.previous:p.error('--previous required')
        prepare(a.previous.resolve(),a.work.resolve())
    else:run(a.work.resolve())
