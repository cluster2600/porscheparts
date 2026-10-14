"""Read-only feasibility of native radial block subdivision, not a new mesh."""
import json,re,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
w=Path(__file__).parent;c=Path('work/bionic-airflow-20261012/full-collar-063');r=json.loads((c/'report.json').read_text());assert all(sha(c/n)==h for n,h in r['output_sha256'].items())
p=np.array(json.loads((c/'construction.json').read_text())['vertices']);text=(c/'system/blockMeshDict').read_text();blocks=re.findall(r'hex \(([^()]*)\)( rotorZone)? \(1 1 1\) simpleGrading \(1 1 1\)',text);assert len(blocks)==27136
fixed=[];max_cross=0.
for labels,zone in blocks:
 v=np.fromstring(labels,sep=' ',dtype=int);assert len(v)==8
 if not zone:
  a,b=p[v[0]],p[v[1]];assert a[2]==b[2] and np.linalg.norm(b[:2])>np.linalg.norm(a[:2]);cross=abs(a[0]*b[1]-a[1]*b[0]);max_cross=max(max_cross,float(cross));fixed.append(v.tolist())
assert len(fixed)==6784 and max_cross<1e-18
result=dict(source_sha256=sha(Path(__file__)),parent_report_sha256=sha(c/'report.json'),block_dictionary_sha256=sha(c/'system/blockMeshDict'),fixed_hex_blocks=len(fixed),rotating_prism_blocks=len(blocks)-len(fixed),first_edge_is_radial=True,max_xy_cross_m2=max_cross,proposed_native_cells_for_fixed_blocks=[2,1,1],mesh_created=False,admission_proven=False,limitation='A prospective first-direction split must independently preserve interface and boundary coverage and pass full and isolated-region native checks. No block dictionary changed.')
with (w/'radial-block-feasibility.json').open('x') as f:json.dump(result,f,indent=2)
print(result)
