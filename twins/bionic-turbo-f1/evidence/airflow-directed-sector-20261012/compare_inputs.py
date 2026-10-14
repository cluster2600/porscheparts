"""Compare exact prepared inputs; never compare only scenario names."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
root=Path('work/bionic-airflow-20261012');names=('directed-equilibrium-044','directed-inertial-045','directed-halfstep-046');manifests={name:json.loads((root/name/'manifest.json').read_text()) for name in names};base=manifests[names[0]]['file_sha256'];result=[]
for name,expected in zip(names[1:],('constant/MRFProperties','system/controlDict')):
 current=manifests[name]['file_sha256'];assert set(base)==set(current);changed=[p for p in base if base[p]!=current[p]];assert changed==[expected]
 assert all(sha(root/name/p)==h for p,h in current.items());result.append(dict(reference=names[0],case=name,changed_prepared_files=changed,only_expected_change=True))
with Path(__file__).with_name('paired-inputs.json').open('x') as f:json.dump(dict(source_sha256=sha(Path(__file__)),comparisons=result),f,indent=2)
print(json.dumps(result))
