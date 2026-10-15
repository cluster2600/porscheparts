"""Verify unchanged numerical inputs; the full collar is a different domain."""
import json,sys
from pathlib import Path
sys.path.insert(0,'twins/bionic-turbo-f1/cfd')
from prepare_case import sha
w=Path(__file__).parent;root=Path('work/bionic-airflow-20261012');a=root/'full-collar-equilibrium-064';b=root/'connected-equilibrium-076'
x=json.loads((a/'manifest.json').read_text());y=json.loads((b/'manifest.json').read_text())
assert x['criteria']==y['criteria']
assert {n for n in x['file_sha256'] if not n.startswith('constant/polyMesh/')}=={n for n in y['file_sha256'] if not n.startswith('constant/polyMesh/')}
changed=[]
for n,h in x['file_sha256'].items():
 assert sha(a/n)==h and sha(b/n)==y['file_sha256'][n]
 if h!=y['file_sha256'][n]:changed.append(n)
added=sorted(set(y['file_sha256'])-set(x['file_sha256']));assert changed and all(n.startswith('constant/polyMesh/') for n in changed+added)
for n in added:assert sha(b/n)==y['file_sha256'][n]
result=dict(reader_sha256=sha(Path(__file__)),criteria_unchanged=True,all_nonmesh_prepared_inputs_byte_identical=True,added_prepared_paths=added,changed_prepared_paths=changed,geometry_unchanged=False,limitation='Same connectivity and rotating geometry; exterior synthetic boundary differs after projection. Not a physical performance comparison.')
with (w/'paired-inputs.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
