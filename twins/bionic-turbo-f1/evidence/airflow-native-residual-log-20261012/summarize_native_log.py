"""Join verified solve diagnostics to unchanged native extrema histories."""
import csv,json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
w=Path(__file__).parent;base=Path('work/bionic-airflow-20261012');a=base/'directed-equilibrium-044';b=base/'native-residual-full-055'
r=json.loads((w/'native-full-readback.json').read_text());assert r['fields_byte_identical'] and r['all_original_pressure_summaries_identical']
arrays={}
for kind in ('maxima','minima'):
    path=Path('postProcessing')/kind/'0/volFieldValue.dat'
    x=np.loadtxt(a/path);y=np.loadtxt(b/path)
    assert x.shape==y.shape==(200,4) and np.isfinite(y).all() and np.array_equal(x,y)
    arrays[kind]=y
assert np.array_equal(arrays['maxima'][:,0],arrays['minima'][:,0])
speed=np.sqrt(arrays['maxima'][:,3]);assert np.all(arrays['maxima'][:,3]>=0)
rows=r['pressure_solves'];steps=[]
for i in range(200):
    group=rows[4*i:4*i+4];assert all(abs(x['time_s']-arrays['maxima'][i,0])<1e-18 for x in group)
    steps.append(dict(time_s=float(arrays['maxima'][i,0]),max_speed_m_s=float(speed[i]),pressure_cap_hits=sum(x['iterations']==1000 for x in group),max_final_L1_product=max(x['final_L1_product'] for x in group),max_final_normalized=max(x['final_normalized'] for x in group),max_normalization_factor=max(x['normalization_factor'] for x in group)))
with (w/'pressure-history.csv').open('x',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=list(steps[0]));writer.writeheader();writer.writerows(steps)
observed=dict(max_abs_p_error_Pa=float(max(np.max(abs(arrays[k][:,1]-101325)) for k in arrays)),max_abs_T_error_K=float(max(np.max(abs(arrays[k][:,2]-298.15)) for k in arrays)),max_speed_m_s=float(speed.max()))
assert observed==json.loads((a/'report.json').read_text())['observed']
failed=np.flatnonzero(speed>1e-8);assert len(failed)
result=dict(source_sha256=sha(Path(__file__)),readback_sha256=sha(w/'native-full-readback.json'),histories_identical=True,observed=observed,first_speed_threshold_exceeded=steps[int(failed[0])],first_step=steps[0],last_step=steps[-1],pressure_solves=len(rows),pressure_cap_hits=sum(x['iterations']==1000 for x in rows),final_L1_product_range=[min(x['final_L1_product'] for x in rows),max(x['final_L1_product'] for x in rows)],normalization_factor_range=[min(x['normalization_factor'] for x in rows),max(x['normalization_factor'] for x in rows)],rest_accepted=False,linear_convergence_qualified=False,causal_attribution=False,performance_ranking_authorized=False)
assert result['pressure_cap_hits']==647
with (w/'history-summary.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
