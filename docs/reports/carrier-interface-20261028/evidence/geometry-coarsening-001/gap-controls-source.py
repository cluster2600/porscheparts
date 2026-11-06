from repair import repair
from pathlib import Path
import numpy as np,json
# Missing x=1 rectangle on a thin box, independently prescribed boundary order.
v=np.array([[1,0,0],[1,2**-25,0],[1,2**-25,1],[1,0,1],[0,0,0],[0,2**-25,0],[0,2**-25,1],[0,0,1]],float)
full=np.array([[0,1,2],[0,2,3],[4,7,6],[4,6,5],[0,4,5],[0,5,1],[3,2,6],[3,6,7],[0,3,7],[0,7,4],[1,5,6],[1,6,2]],np.uint64);f=full[2:]
g,p=repair(v,f);assert len(g)==len(full)and len(p)==1 and p[0]['bound_mm']==2**-25
edges=np.vstack([g[:,[0,1]],g[:,[1,2]],g[:,[2,0]]]);_,counts=np.unique(np.sort(edges,axis=1),axis=0,return_counts=True);assert np.all(counts==2)
rows=[dict(case='narrow_missing_rectangle',passed=True,exact_bound_mm=p[0]['bound_mm'])]
for name,a,b in [('wide_hole',v*np.array([1,2**25,1]),f),('nonplanar',v+np.array([[2**-30,0,0]]+[[0,0,0]]*7),f),('triangular_hole',v,full[1:])]:
 try:repair(a,b)
 except ValueError as e:rows.append(dict(case=name,passed=True,refusal=str(e)))
 else:raise AssertionError(name+' should be refused')
r=Path(__file__).resolve().parent;(r/'controls.json').write_text(json.dumps(dict(status='narrow_gap_controls_passed',cases=rows),indent=2)+'\n');print('PASS',len(rows))
