from translation import translate
from fractions import Fraction as Q
from pathlib import Path
import numpy as np,json
rng=np.random.default_rng(993)
v=np.vstack([rng.uniform(-128,128,(3000,3)).astype(np.float32),np.array([[2**-60,-2**-149,2**-149],[0,0,0],[.01,-.01,1e-8]],np.float32)]).astype(float)
rows=[]
for origin in [[77,-29,0],[-76.04271846268657,-29,0],[0,0,0]]:
 world,error,report=translate(v,origin)
 for i in range(len(v)):
  exact_l1=Q(0)
  for k in range(3):
   residual=Q(float(v[i,k]))+Q(float(origin[k]))-Q(float(world[i,k]));assert residual==Q(float(error[i,k]));exact_l1+=abs(residual)
  assert exact_l1<=Q(report['complete_translation_bound_mm'])
 rows.append(report)
assert rows[0]['nonexact_coordinate_additions']>0 and rows[2]['all_additions_exact']
for bad,origin in [(np.array([[np.nan,0,0]]),[0,0,0]),(np.array([[257.,0,0]]),[0,0,0]),(np.array([[.1,0,0]],float),[0,0,0])]:
 try:translate(bad,origin)
 except ValueError:pass
 else:raise AssertionError('Invalid input admitted')
(Path(__file__).resolve().parent/'controls.json').write_text(json.dumps(dict(status='exact_fraction_translation_controls_passed',exact_scalar_equalities=3*len(v)*3,cases=rows),indent=2)+'\n');print('PASS',3*len(v)*3,'exact scalar equalities')
