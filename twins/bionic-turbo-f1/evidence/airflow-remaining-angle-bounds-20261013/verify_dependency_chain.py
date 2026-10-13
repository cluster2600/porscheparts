"""Anchor the six dependency manifests to the exact, verified PR236 merge commit."""
import hashlib,json,subprocess
from pathlib import Path
w=Path(__file__).parent;commit='3d549d8c2fcd73074dd8e4aef86d7e818251971e'
base='twins/bionic-turbo-f1/evidence/airflow-centre-interval-bounds-20261013/'
source=lambda name:subprocess.check_output(['git','show',commit+':'+base+name])
expected=json.loads(source('readback.json'))['dependencies']
receipt=json.loads(source('archive-receipt.json'))
expected['work/bionic-airflow-delivery-20261013-centre-interval-bounds/file-manifest.json']=receipt['manifest_sha256']
assert expected==json.loads((w/'dependencies.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();n=0
for path,digest in expected.items():
 p=Path(path);assert sha(p)==digest
 for r in json.loads(p.read_text())['files']:
  assert sha(Path('work')/r['path'])==r['sha256'];n+=1
out=dict(source_sha256=sha(Path(__file__)),anchor_commit=commit,manifest_count=len(expected),payload_entries_verified=n,manifests=expected,anchored_to_published_commit=True)
(w/'dependency-chain-readback.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
