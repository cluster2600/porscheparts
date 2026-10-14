"""Read pinned manifests and payloads; no geometry evaluation."""
import hashlib,json,subprocess,time
from pathlib import Path
W=Path(__file__).parent;BASE='050b28b932aee9eaafe4b07e43fad17a6f6ee157'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
parents=json.loads(Path('work/bionic-native-face-tets-audit-20261013/source-audit.json').read_text())['manifests'];parents['work/bionic-airflow-delivery-20261013-native-face-tets-audit/file-manifest.json']='493479118abd5ff20af1ba39d7d39b6f5a2f08bdf49f9cfec7315c730ed061b5';entries=0;allfiles={}
for name,digest in parents.items():
 p=Path(name);phase=p.parent.name.split('20261013-',1)[1];raw=subprocess.check_output(['git','show',BASE+':twins/bionic-turbo-f1/evidence/airflow-'+phase+'-20261013/file-manifest.json']);assert hashlib.sha256(raw).hexdigest()==digest==sha(p)
 for r in json.loads(raw)['files']:
  f=Path('work')/r['path'];assert f.stat().st_size==r['bytes'] and sha(f)==r['sha256'];allfiles[str(f)]=r['sha256'];entries+=1
paths=['work/bionic-volume-representation-20261013/'+n for n in ('readback.json','independent-readback.json','models.jsonl.gz')]+['work/bionic-parametric-boundary-20261013/'+n for n in ('readback.json','independent-readback-v2.json','models.json','proof.md')]+['work/bionic-boundary-embedding-20261013/'+n for n in ('triangles.json','readback.json','independent-readback.json','gluing-readback.json','proof.md')]+['work/bionic-buffered-transition-20261013/construction.json']
inputs=[]
for name in paths:
 p=Path(name);digest=sha(p)
 # Construction is pinned explicitly by the inherited source receipts.
 if name.endswith('construction.json'):assert digest=='ddda1839b41b7dfde9b7303d90f47e35c0ac35726f1db1278117366de71eb9e4'
 else:assert digest==allfiles[name]
 inputs.append({'path':name,'sha256':digest})
assert len(parents)==19 and entries==520
out={'created_at_unix':time.time(),'anchor_commit':BASE,'manifests':parents,'payload_entries_verified':entries,'inputs':inputs,'geometry_recomputed':False}
with (W/'input-inventory.json').open('x') as f:json.dump(out,f,indent=2)
print('19 manifests, 520 payload entries verified; no geometry recomputation.')
