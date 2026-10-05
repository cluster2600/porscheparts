#!/usr/bin/env python3
"""Build auditable synthetic candidates; split only reviewed, verified records."""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import random
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
SYSTEM = ('You are an engineering coding assistant. Use the supplied software version and '
          'units. Distinguish synthetic design inputs from measured Porsche data. '
          'Never invent missing specifications, validation results or manufacturing approval.')


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def write_rows(path, rows):
    with path.open('x') as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=True, allow_nan=False) + '\n')


def topology(n, edges):
    # Small witnesses only: n <= 5, so canonicalization costs at most 120 permutations.
    return min(tuple(sorted(tuple(sorted((p[a], p[b]))) for a, b in edges))
               for p in itertools.permutations(range(n)))


def candidates():
    rng = random.Random(993)
    source = {'id':'new-synthetic-generator', 'uri':'repo:training/m64-engineer/dataset.py',
              'revision_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'license':'Repository proprietary; owner-authorized local training', 'training_allowed':True}
    rows = []
    for i in range(80):
        n = rng.randint(3,5)
        points = rng.sample(list(itertools.product(range(-12,13,4),repeat=3)),n)
        edges = [(j,rng.randrange(j)) for j in range(1,n)]
        extra = [e for e in itertools.combinations(range(n),2) if tuple(sorted(e)) not in [tuple(sorted(x)) for x in edges]]
        rng.shuffle(extra)
        edges += extra[:rng.randint(0,min(6-len(edges),len(extra)))]
        rng.shuffle(edges)
        radii = [rng.choice([0.5,1.0,1.5,2.0]) for _ in range(n)]
        rounded = bool(i%2)
        def vec(p): return 'new Vector3(' + ', '.join(f'{x:g}f' for x in p) + ')'
        code = '\n'.join(f'lattice.AddBeam({vec(points[a])}, {radii[a]:g}f, {vec(points[b])}, {radii[b]:g}f, {str(rounded).lower()});' for a,b in edges)
        prompt = ('PicoGK commit 0e6cf6b6f4993ec16dbcd72d8f27f26b999980f3. '
                  'Generate only literal lattice.AddBeam calls, including float suffixes and explicit cap flags. '
                  'lattice already exists. Connect every supplied edge exactly once. '
                  'Synthetic vertices in mm: ' + json.dumps(points) + '; vertex radii in mm: ' + json.dumps(radii) +
                  '; zero-based edges: ' + json.dumps(edges) + '; rounded caps: ' + str(rounded).lower() + '.')
        rows.append({'id':f'lattice-{i:03d}', 'family_id':f'graph-{n}-'+sha(repr(topology(n,edges)))[:12],
                     'domain':'picogk', 'messages':[{'role':'system','content':SYSTEM},
                     {'role':'user','content':prompt},{'role':'assistant','content':code}],
                     'sources':[source], 'validation':{'status':'pending','method':'not yet compiled'},
                     'synthetic':True})
    for i in range(40):
        # Independent unit tests check representative values. These are analytical fixtures.
        bore, stroke, cylinders = rng.choice([80,90,100,110]), rng.choice([60,70,76.4,80]), 6
        displacement = cylinders*math.pi/4*(bore/1000)**2*(stroke/1000)*1e6
        answer = f'Vd = N*pi/4*B^2*S = {displacement:.6f} cm^3. B and S were converted from mm to m; 1 m^3 = 1e6 cm^3. Synthetic input; this is not a measured engine.'
        rows.append({'id':f'volume-{i:03d}','family_id':f'displacement-bore-{bore}', 'domain':'physics',
                     'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':
                     f'For synthetic fixture {i}, calculate displacement in cm^3 for {cylinders} cylinders, bore {bore} mm and stroke {stroke} mm. Show units.'},
                     {'role':'assistant','content':answer}], 'sources':[source], 'synthetic':True,
                     'validation':{'status':'pending','method':'analytical oracle; independent review still required'}})
    return rows


def load(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def check(rows):
    ids, prompts = set(), set()
    for r in rows:
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',r['id']): raise ValueError('invalid id')
        if r['id'] in ids: raise ValueError('duplicate id')
        ids.add(r['id'])
        m = r['messages']
        if [x['role'] for x in m] != ['system','user','assistant']: raise ValueError('expected S/U/A')
        if any(not isinstance(x['content'],str) or not x['content'].strip() for x in m): raise ValueError('empty message')
        prompt = sha(' '.join(m[1]['content'].split()))
        if prompt in prompts: raise ValueError('duplicate normalized prompt')
        prompts.add(prompt)
        if not r['family_id'] or not r['sources']: raise ValueError('missing provenance')
        if any(s.get('training_allowed') is not True or not s.get('license') or len(s.get('revision_sha256',''))!=64 for s in r['sources']):
            raise ValueError('source rights/hash missing')
        v = r['validation']
        if v.get('status')!='verified' or v.get('answer_sha256')!=sha(m[-1]['content']) or not v.get('evidence'):
            raise ValueError(f'{r["id"]}: verification evidence missing or stale')
        for evidence in v['evidence']:
            path=Path(evidence['path']).resolve()
            path.relative_to((ROOT/'work').resolve())
            if path.suffix!='.json' or path.stat().st_size>1_000_000: raise ValueError('invalid receipt')
            if hashlib.sha256(path.read_bytes()).hexdigest()!=evidence['sha256']: raise ValueError('receipt hash mismatch')
            if json.loads(path.read_text())['answer_sha256']!=v['answer_sha256']: raise ValueError('stale receipt')


def split(rows):
    check(rows)
    groups = sorted({r['family_id'] for r in rows})
    if len(groups)<10: raise ValueError('need at least 10 independent families')
    random.Random(42).shuffle(groups)
    count = max(1,len(groups)//10)
    mapping = {g:('test' if i<count else 'valid' if i<2*count else 'train') for i,g in enumerate(groups)}
    return {name:[r for r in rows if mapping[r['family_id']]==name] for name in ('train','valid','test')}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['generate','verify-lattice','prepare'])
    p.add_argument('--input',type=Path)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--sdk',type=Path)
    p.add_argument('--dll',type=Path)
    a=p.parse_args()
    if a.action=='generate': write_rows(a.output,candidates()); return
    if a.input is None: p.error('--input required')
    rows=load(a.input)
    if a.action=='verify-lattice':
        if a.sdk is None or a.dll is None: p.error('--sdk and --dll required')
        sys.path.insert(0,str(ROOT/'training/m64-qwen'))
        from picogk import witness
        evidence=a.output.with_suffix('.evidence'); evidence.mkdir(exist_ok=False)
        verified=[]
        for r in rows:
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',r['id']): raise ValueError('invalid id')
            if r['domain']!='picogk': continue
            result=witness(r['messages'][-1]['content'],(evidence/r['id']).resolve(),a.sdk.resolve(),a.dll.resolve())
            if not all(result[k] for k in ('compiled','native_passed')): raise ValueError('reference code failed')
            answer_hash=sha(r['messages'][-1]['content'])
            receipt=evidence/(r['id']+'.json')
            receipt.write_text(json.dumps({'answer_sha256':answer_hash,'result':result,
                'dll_sha256':hashlib.sha256(a.dll.read_bytes()).hexdigest()},indent=2)+'\n')
            r['validation']={'status':'verified','answer_sha256':answer_hash,'method':'bounded literal code compiled and ran; not engineering validation',
                             'evidence':[{'path':str(receipt),'sha256':hashlib.sha256(receipt.read_bytes()).hexdigest()}]}
            verified.append(r)
        if not verified: raise ValueError('no PicoGK candidates')
        write_rows(a.output,verified); return
    partitions=split(rows)
    a.output.mkdir(exist_ok=False,parents=True)
    for name,data in partitions.items(): write_rows(a.output/(name+'.jsonl'),data)
    manifest={'counts':{s:len(v) for s,v in partitions.items()},'input_sha256':hashlib.sha256(a.input.read_bytes()).hexdigest(),
              'files':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(a.output.glob('*.jsonl'))},
              'note':'Grouped by graph isomorphism / source family. Add independently authored benchmark cases; this alone is not sufficient evaluation.'}
    (a.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

if __name__=='__main__': main()
