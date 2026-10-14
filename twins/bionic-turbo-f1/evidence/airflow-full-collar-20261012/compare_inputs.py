"""Verify unchanged numerical inputs; the full collar is a different domain."""
import json,sys
from pathlib import Path
sys.path.insert(0,'twins/bionic-turbo-f1/cfd')
from prepare_case import sha
w=Path(__file__).parent;root=Path('work/bionic-airflow-20261012');a=root/'inner-equilibrium-061';b=root/'full-collar-equilibrium-064'
x=json.loads((a/'manifest.json').read_text());y=json.loads((b/'manifest.json').read_text())
assert set(x['file_sha256'])==set(y['file_sha256']) and x['criteria']==y['criteria']
changed=[]
for n,h in x['file_sha256'].items():
 assert sha(a/n)==h and sha(b/n)==y['file_sha256'][n]
 if h!=y['file_sha256'][n]:changed.append(n)
assert changed and all(n.startswith('constant/polyMesh/') for n in changed)
result=dict(reader_sha256=sha(Path(__file__)),criteria_unchanged=True,all_nonmesh_prepared_inputs_byte_identical=True,changed_prepared_paths=changed,geometry_unchanged=False,limitation='Different axial extent, radii and cell counts; this is not a physical performance comparison.')
with (w/'paired-inputs.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
