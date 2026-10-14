"""Prove exact prepared changes from fixed-wall 044 to cyclic 048."""
from pathlib import Path
import json,sys
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
root=Path('work/bionic-airflow-20261012');a=root/'directed-equilibrium-044';b=root/'periodic-equilibrium-048'
x=json.loads((a/'manifest.json').read_text())['file_sha256'];y=json.loads((b/'manifest.json').read_text())['file_sha256'];assert set(x)==set(y)
changed=sorted(n for n in x if x[n]!=y[n]);expected=['0/T','0/U','0/p','constant/polyMesh/boundary','constant/polyMesh/faces','constant/polyMesh/owner'];assert changed==expected,(changed,expected)
assert all(sha(b/n)==h for n,h in y.items())
for name in ('p','T','U'):
 first=(a/'0'/name).read_text();second=(b/'0'/name).read_text();assert second.replace('periodicLower {type cyclic;} periodicUpper {type cyclic;}','')==first
with Path(__file__).with_name('paired-inputs.json').open('x') as out:json.dump(dict(source_sha256=sha(Path(__file__)),reference=a.name,case=b.name,changed_prepared_files=changed,all_other_inputs_byte_identical=True,scope='Cyclic conditions replace only the synthetic angular cuts; face/owner/set permutations preserve topology as independently verified.'),out,indent=2)
print(changed)
