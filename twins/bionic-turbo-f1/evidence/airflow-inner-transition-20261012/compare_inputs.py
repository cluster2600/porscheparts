"""Verify unchanged numerical inputs and exactly matching native MRF face geometry."""
import json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,'twins/bionic-turbo-f1/cfd')
from prepare_case import sha
from uniform_interface_projection import read_mesh
w=Path(__file__).parent;root=Path('work/bionic-airflow-20261012');a=root/'conformal-equilibrium-059';b=root/'inner-equilibrium-061'
x=json.loads((a/'manifest.json').read_text());y=json.loads((b/'manifest.json').read_text())
assert set(x['file_sha256'])==set(y['file_sha256']) and x['criteria']==y['criteria']
changed=[]
for n,h in x['file_sha256'].items():
 assert sha(a/n)==h and sha(b/n)==y['file_sha256'][n]
 if h!=y['file_sha256'][n]:changed.append(n)
assert changed and all(n.startswith('constant/polyMesh/') for n in changed)
a=root/'conformal-transition-058';b=root/'inner-transition-060'
pa,fa,ia,_=read_mesh(a);pb,fb,ib,_=read_mesh(b)
def keys(p,f,ids):return {tuple(sorted(tuple(float(v) for v in p[j]) for j in f[i])) for i in ids}
assert keys(pa,fa,ia)==keys(pb,fb,ib) and len(ia)==len(ib)==1280
result=dict(reader_sha256=sha(Path(__file__)),criteria_unchanged=True,all_nonmesh_prepared_inputs_byte_identical=True,changed_prepared_paths=changed,interface_face_coordinates_exactly_equal=True,interface_quads=1280,physical_walls_identical=False,limitation='Different synthetic polygonal boundaries and cell topology; identical equations are not a single-factor physical performance comparison.')
with (w/'paired-inputs.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
