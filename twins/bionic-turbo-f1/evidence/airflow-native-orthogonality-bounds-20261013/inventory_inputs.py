"""Inventory pinned inherited certificates; no geometric or criterion replay."""
import hashlib,json,subprocess
from pathlib import Path
from fractions import Fraction as F
W=Path(__file__).parent
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
base='b18528da4ac7abc26ce6114b3720e8d1d91fc8d3'
dep=json.loads(Path('work/bionic-native-skewness-bounds-20261013/dependencies.json').read_text())['manifests']
dep['work/bionic-airflow-delivery-20261013-native-skewness-bounds/file-manifest.json']='2adda74b89de0dda2c893773802f8dba8a97f1542460948d805d60b431815fb0'
entries=0
for name,digest in dep.items():
 p=Path(name);phase=p.parent.name.split('20261013-',1)[1]
 raw=subprocess.check_output(['git','show',base+':twins/bionic-turbo-f1/evidence/airflow-'+phase+'-20261013/file-manifest.json'])
 assert hashlib.sha256(raw).hexdigest()==digest==sha(p)
 for r in json.loads(raw)['files']:
  q=Path('work')/r['path'];assert sha(q)==r['sha256'];assert q.stat().st_size==r['bytes'];entries+=1
boxes=json.loads(Path('work/bionic-angular-independent-bounds-20261013/certificate-readback.json').read_text())['box_results']
old=Path('work/bionic-centre-interval-bounds-20261013/centred-certificate.json');rows={r['parent_leaf']:r for r in json.loads(old.read_text())['rows']}
cert=Path('work/bionic-feasibility-bounds-20261013/certificate.json');kap=list(map(F,json.loads(cert.read_text())['kappa']))
covered=[]
for box in boxes:
 r=rows[box['parent_leaf']];assert (r['lower'],r['upper'])==(box['lower'],box['upper']);assert len(r['angles'])==2
 for angle in r['angles']:
  a,b=map(F,angle['combined']['D']);c,d=map(F,angle['combined']['residual']);assert 0<a<=b and 0<c+kap[0]<=d+kap[1]
  assert 'Q' not in angle['raw']
 covered.append(r['parent_leaf'])
out={'source_sha256':sha(Path(__file__)),'anchor_commit':base,'manifests':dep,'payload_entries_verified':entries,'matrix_variables':9470,'matrix_rows_expected':9470*len(boxes),'witnesses':2,'witness_domains_verified':len(covered),'witness_D_and_R_plus_kappa_strictly_positive':True,'witness_Q_explicitly_stored':False,'witness_Q_recovery_identity':'Q = D^2/(R+kappa), R=D^2/Q-kappa','constant_internal_faces_inherited_count':4224,'constant_internal_numerical_bounds_inventoried':False,'uncoupled_walls_inherited_count':4864,'source_boxes':covered,'geometric_reconstruction':False,'new_orthogonality_bounds_computed':False,'native_admission':False}
(W/'input-inventory.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ('manifests','source_boxes')}))
