"""Independent structural dossier/source verification; no mesh calculation."""
import hashlib,json,subprocess,tarfile
from pathlib import Path
from fractions import Fraction
W=Path(__file__).parent
H=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
J=lambda p:json.loads(p.read_text())
r=J(W/'readback.json');d=J(W/'dossier.json');s=J(W/'source-audit.json');deps=J(W/'dependencies.json')
for name,key in [('build_dossier.py','source_sha256'),('preflight.md','preflight_sha256'),('dossier.json','dossier_sha256'),('source-audit.json','source_audit_sha256'),('dependencies.json','dependencies_sha256')]:assert H(W/name)==r[key]
anchor='ed462661ca94c843b0f8c1379d88258595f552a4';assert d['anchor_commit']==deps['anchor_commit']==anchor
entries=0
for name,digest in deps['manifests'].items():
 p=Path(name);phase=p.parent.name.split('20261013-',1)[1]
 raw=subprocess.check_output(['git','show',anchor+':twins/bionic-turbo-f1/evidence/airflow-'+phase+'-20261013/file-manifest.json'])
 assert hashlib.sha256(raw).hexdigest()==digest==H(p)
 for row in json.loads(raw)['files']:
  f=Path('work')/row['path'];assert H(f)==row['sha256'] and f.stat().st_size==row['bytes'];entries+=1
assert entries==deps['payload_entries_verified']==r['payload_entries_verified']==284
archive=Path('work/bionic-native-diagnostics-20261012/OpenFOAM-v2406.tgz')
assert H(archive)==s['archive_sha256']=='8d1450fb89eec1e7cecc55c3bb7bc486ccbf63d069379d1d5d7518fa16a4686a'
with tarfile.open(archive) as tar:
 for row in s['members']:
  raw=tar.extractfile(row['member']).read();assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'] and raw==(W/row['file']).read_bytes()
for c in s['claims']:
 lines=(W/c['file']).read_text().splitlines();assert c['lines']==[i+1 for i,x in enumerate(lines) if c['literal'] in x]
# Join already-verified box receipts, without repeating their evaluations.
a=J(Path('work/bionic-angular-independent-bounds-20261013/certificate-readback.json'))
c=J(Path('work/bionic-remaining-cell-bounds-20261013/summary.json'))
assert len(a['box_results'])==d['source_boxes']==153
passing=[]
for i,b in enumerate(a['box_results']):
 leaf=b['parent_leaf'];assert leaf==1778+i
 if i:assert Fraction(a['box_results'][i-1]['upper'])==Fraction(b['lower'])
 assert Fraction(b['lower'])<Fraction(b['upper'])
 cell=c['box_results'][str(leaf)]
 ok=not cell['unknown_determinant_cells'] and cell['planes']['positive']==92160 and cell['volumes']['positive']==3840
 assert ok==b['all_variable_cell_predicates_positive']
 if ok and b['all_9472_variable_angles_positive']:passing.append(leaf)
assert passing==d['necessary_predicate_positive_leaves']==list(range(1816,1929))
assert d['domain_v']==[a['box_results'][0]['lower'],a['box_results'][-1]['upper']]
p=d['slice_dependencies'];assert (p['fixed_cells'],p['variable_cells'],p['fixed_angles'],p['variable_angles'],p['constant_planes'],p['variable_planes'],p['fixed_mrf_angles'])==(2304,3840,4224,9472,46080,92160,384)
ids=[x['id'] for x in d['obligations']];assert len(ids)==len(set(ids))==16
assert all(not x['native_admission'] and x['remaining_obligation'] for x in d['obligations'])
assert not d['candidate_created'] and not d['native_admission'] and d['new_geometry_evaluations']==0
out={'source_sha256':H(Path(__file__)),'primary_readback_sha256':H(W/'readback.json'),'dossier_sha256':H(W/'dossier.json'),'manifests_verified':len(deps['manifests']),'payload_entries_verified':entries,'source_members_verified':len(s['members']),'source_claim_locations_verified':len(s['claims']),'box_receipts_joined':153,'necessary_predicate_positive_boxes':len(passing),'obligations':len(ids),'role':'independent structural/provenance check; no new geometric or native proof','native_admission':False}
(W/'independent-readback.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
