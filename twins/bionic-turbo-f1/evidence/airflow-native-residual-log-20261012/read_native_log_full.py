"""Read native log-control parity and finest-grid GAMG L1 residual products."""
import json,re,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha,IMAGE
from audit_diagnostic import ascii_list
w=Path(__file__).parent;base=Path('work/bionic-airflow-20261012')
a=base/'directed-equilibrium-044';b=base/'native-residual-full-055'
num=r'[-+0-9.eE]+'
summary=re.compile(r'^GAMG:  Solving for p, Initial residual = ('+num+r'), Final residual = ('+num+r'), No Iterations (\d+)$',re.M)
cycle=re.compile(r'GAMG:  Solving for p, Initial residual = ('+num+r'), Final residual = ('+num+r'), No Iterations (\d+)')

def parse(log):
    records=[];time=None;pending=None;cycles=[]
    for line in log.splitlines():
        if line.startswith('Time = '):time=float(line.split('=')[1])
        if 'Normalisation factor = ' in line:
            assert pending is None and time is not None
            pending=float(line.split('Normalisation factor = ')[1]);cycles=[]
            assert np.isfinite(pending) and pending>0
        m=cycle.search(line)
        if m:
            assert pending is not None
            values=(float(m[1]),float(m[2]),int(m[3]));assert np.isfinite(values).all()
            if summary.fullmatch(line):
                initial,final,iters=values
                assert [c[2] for c in cycles]==list(range(iters))
                assert all(c[0]==initial for c in cycles)
                assert not cycles or cycles[-1][1]==final
                records.append(dict(time_s=time,normalization_factor=pending,initial_normalized=initial,final_normalized=final,iterations=iters,initial_L1_product=pending*initial,final_L1_product=pending*final))
                pending=None
            else:cycles.append(values)
    assert pending is None and records
    return records
sample='Time = 1\n   Normalisation factor = 2\nDICPCG:  Solving for p, Initial residual = 9, Final residual = 8, No Iterations 4\nPost-smoothing scaling factors: GAMG:  Solving for p, Initial residual = 3, Final residual = 1, No Iterations 0\nGAMG:  Solving for p, Initial residual = 3, Final residual = 1, No Iterations 1\n'
assert parse(sample)[0]['final_L1_product']==2
try:parse(sample.replace('No Iterations 0','No Iterations 2'))
except AssertionError:pass
else:raise AssertionError('Skipped cycle accepted')

def fields(case):
    receipt=json.loads((case/'report.json').read_text());manifest=json.loads((case/'manifest.json').read_text())
    assert receipt['native_exit_code']==0 and receipt['native_end'] and receipt['samples']==200
    assert sha(case/'manifest.json')==receipt['manifest_sha256'] and sha(case/'execution.json')==receipt['execution_sha256']
    assert all(sha(case/n)==h for n,h in receipt['output_sha256'].items())
    assert all(sha(case/n)==h for n,h in manifest['file_sha256'].items())
    assert manifest['image']==IMAGE and manifest.get('executable','rhoPimpleFoam')=='rhoPimpleFoam'
    assert case==a or (case/'log.binary-sha').read_text().split()[0]=='85e40da38fc4fd0ba24ef1560f659390684f334677554ebfb0ac2d0f41ba3467'
    owner=ascii_list((case/'constant/polyMesh/owner').read_text());neighbour=ascii_list((case/'constant/polyMesh/neighbour').read_text())
    cells=int(max(owner.max(),neighbour.max())+1);assert cells==12480 and len(neighbour)==25936
    result={}
    for name in ('p','T','U','rho','phi'):
        path=case/'2e-05'/name;text=path.read_text()
        m=re.search(r'internalField\s+nonuniform\s+List<(scalar|vector)>\s+(\d+)\s*\((.*?)\)\s*;',text,re.S)
        count=len(neighbour) if name=='phi' else cells;assert m and int(m[2])==count
        data=np.fromstring(m[3].translate(str.maketrans('()','  ')),sep=' ')
        assert data.size==count*(3 if name=='U' else 1) and np.isfinite(data).all()
        result[name]=dict(sha256=sha(path),entries=count,min=float(data.min()),max=float(data.max()))
    return manifest,result
ma,fa=fields(a);mb,fb=fields(b)
assert set(ma['file_sha256'])==set(mb['file_sha256'])
changed=[n for n in ma['file_sha256'] if ma['file_sha256'][n]!=mb['file_sha256'][n]]
assert changed==['system/fvSolution']
assert (b/changed[0]).read_text()==(a/changed[0]).read_text().replace('p {solver GAMG;','p {solver GAMG; log 2;')
# The original 044 runner has a different command wrapper; inputs and image are checked independently.
assert mb['executable']=='rhoPimpleFoam'
assert fa==fb
rows=parse((b/'log.rhoPimpleFoam').read_text());assert len(rows)==800
assert np.allclose([r['time_s'] for r in rows],np.repeat(np.arange(1,201)*1e-7,4),rtol=0,atol=1e-18)
original=summary.findall((a/'log.rhoPimpleFoam').read_text());assert len(original)==len(rows)
assert [(float(i),float(f),int(n)) for i,f,n in original]==[(r['initial_normalized'],r['final_normalized'],r['iterations']) for r in rows]
result=dict(reader_sha256=sha(Path(__file__)),all_receipts_and_payloads_verified=True,only_input_change=changed,command_parity_claimed=False,fields_byte_identical=True,fields=fb,pressure_solves=rows,all_original_pressure_summaries_identical=True,physical_duration_s=2e-5,units='algebraic residual numeric product; physical units not independently measured',physical_equilibrium_qualified=False,linear_convergence_qualified=False,performance_ranking_authorized=False)
with (w/'native-full-readback.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
