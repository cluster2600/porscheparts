"""Independent incidences and exact arithmetic; inherited volume proof is not rerun."""
import gzip,hashlib,json,re,subprocess,tarfile,time
from pathlib import Path
from fractions import Fraction as F
from collections import defaultdict,Counter
W=Path(__file__).parent
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
SMALL=F(float('1e-300'));THRESHOLD=F(float('0.01'))
def small(a,b):return (a+b-abs(a-b))/2
def large(a,b):return (a+b+abs(a-b))/2
def enc(a,b):return small(a[0],b[0])/(large(a[1],b[1])+SMALL),small(a[1],b[1])/(large(a[0],b[0])+SMALL)
def quotient_check(q,n,d):
 assert d>0
 # q == n/d checked without another rational division.
 assert q.numerator*n.denominator*d.numerator==q.denominator*n.numerator*d.denominator

def main():
 start=time.monotonic();references=0
 for a,b,expected in ((F(1),F(1),1/(1+SMALL)),(F(1),F(2),1/(2+SMALL)),(F(2),F(1),1/(2+SMALL)),(SMALL,SMALL,F(1,2)),(SMALL,2*SMALL,F(1,3))):assert enc((a,a),(b,b))==(expected,expected);references+=1
 assert enc((F(1),F(2)),(F(2),F(3)))==(1/(3+SMALL),2/(2+SMALL));references+=1
 report=json.loads((W/'readback.json').read_text());dep=json.loads((W/'dependencies.json').read_text());audit=json.loads((W/'source-audit.json').read_text());assert dep['anchor_commit']=='7a1282bdbe43411ade9c0e79e831cc5c9973bb6d';entries=0
 for name,key in (('check_ratios.py','source_sha256'),('preflight.md','preflight_sha256'),('dependencies.json','dependencies_sha256'),('source-audit.json','source_audit_sha256'),('ratio-bounds.jsonl.gz','bounds_sha256')):assert sha(W/name)==report[key]
 for name,digest in dep['manifests'].items():
  p=Path(name);phase=p.parent.name.split('20261013-',1)[1];blob=subprocess.check_output(['git','show',dep['anchor_commit']+':twins/bionic-turbo-f1/evidence/airflow-'+phase+'-20261013/file-manifest.json']);assert hashlib.sha256(blob).hexdigest()==sha(p)==digest
  for row in json.loads(blob)['files']:
   p=Path('work')/row['path'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'];entries+=1
 assert len(dep['manifests'])==14 and entries==332==dep['payload_entries_verified']
 archive=Path('work/bionic-native-diagnostics-20261012/OpenFOAM-v2406.tgz');assert sha(archive)==audit['archive_sha256']=='8d1450fb89eec1e7cecc55c3bb7bc486ccbf63d069379d1d5d7518fa16a4686a'
 with tarfile.open(archive) as tar:
  for row in audit['members']:
   data=tar.extractfile(row['member']).read();assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256'] and data==(W/Path(row['member']).name).read_bytes()
 assert audit['formula'] in (W/'polyMeshTools.C').read_text() and audit['rejection'] in (W/'polyMeshCheck.C').read_text() and audit['call'] in Path('work/bionic-native-admission-dossier-20261013/checkGeometry.C').read_text()
 assert audit['VSMALL']==report['VSMALL']==str(SMALL) and audit['threshold']==report['threshold']==str(THRESHOLD)
 src=json.loads(Path('work/bionic-buffered-transition-20261013/construction.json').read_text());boxes=json.loads(Path('work/bionic-angular-independent-bounds-20261013/certificate-readback.json').read_text())['box_results'];domain=[boxes[0]['lower'],boxes[-1]['upper']];assert report['domain_v']==domain and len(boxes)==153
 model=Path('work/bionic-volume-representation-20261013/models.jsonl.gz');assert sha(model)==report['inherited_models_sha256']=='780a6bece9fa9aafd010a7ff91fc78d571a1e4c3e1102b0ebef1f04cd191ea9a'
 for name in ('readback.json','independent-readback.json'):
  old=json.loads((model.parent/name).read_text());assert old['models_sha256']==sha(model) and old['domain_v']==domain
 assert old['all_coefficients_and_bounds_exact'] and old['cells_verified']==6144
 volumes={}
 with gzip.open(model,'rt') as stream:
  for line in stream:
   r=json.loads(line)
   if r['kind']=='cell':volumes[r['cell']]=tuple(map(F,r['fan_signed_volume']['bounds']))
 assert len(volumes)==6144 and all(0<a<=b for a,b in volumes.values())
 templates=((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7));registry=defaultdict(list)
 def reduce(face):
  result=[]
  for i in face:
   if not result or result[-1]!=i:result.append(i)
  if result[-1]==result[0]:result.pop()
  return result
 def canonical(face):return min(tuple(face[i:]+face[:i]) for i in range(len(face)))
 for cid,block in enumerate(src['blocks']):
  for template in templates:
   face=reduce([block[j] for j in template])
   if len(face)>2:registry[tuple(sorted(face))].append((cid,canonical(face)))
 boundary={}
 for key,uses in registry.items():
  assert len(uses) in (1,2)
  if len(uses)==2:assert canonical(list(reversed(uses[0][1])))==uses[1][1]
  else:boundary[key]=uses[0][1]
 assert boundary=={tuple(sorted(reduce(f))):canonical(reduce(f)) for f in src['walls']}
 text=Path('work/bionic-buffered-transition-20261013/blockMeshDict').read_text().split('boundary',1)[1];tokens=re.findall(r'[A-Za-z_]+|\d+|[(){};]',text);assert tokens[:8]==['(','walls','{','type','wall',';','faces','(']
 i=8;faces=[]
 while tokens[i]=='(':
  i+=1;f=[]
  while tokens[i]!=')':f.append(int(tokens[i]));i+=1
  i+=1;faces.append(f)
 assert tokens[i:]==[')',';','}',')',';'] and faces==src['walls']
 assert len(src['mrf_faces'])==384 and all(len(registry[tuple(sorted(reduce(f)))])==2 for f in src['mrf_faces'])
 counts=Counter();minimum=None
 with gzip.open(W/'ratio-bounds.jsonl.gz','rt') as stream:
  for rank,(key,uses) in enumerate(sorted(registry.items())):
   row=json.loads(next(stream));cells=[c for c,f in uses];assert row['rank']==rank and row['face']==list(key) and row['cells']==cells and row['volumes']==[list(map(str,volumes[c])) for c in cells]
   if len(cells)==1:
    expected=(F(1),F(1));assert row['branch']=='uncoupled_wall'
   else:
    assert row['branch']=='internal';a,b=map(volumes.__getitem__,cells);expected=enc(a,b);quotient_check(F(row['ratio'][0]),small(a[0],b[0]),large(a[1],b[1])+SMALL);quotient_check(F(row['ratio'][1]),small(a[1],b[1]),large(a[0],b[0])+SMALL)
   assert tuple(map(F,row['ratio']))==expected
   status='positive' if expected[0]>=THRESHOLD else ('refused' if expected[1]<THRESHOLD else 'unknown');assert status==row['status'];counts[status]+=1;minimum=expected[0] if minimum is None else min(minimum,expected[0])
  assert next(stream,None) is None
 assert len(registry)==report['faces']==18560 and len(boundary)==report['uncoupled_wall_faces']==4864 and len(registry)-len(boundary)==report['internal_faces']==13696 and dict(counts)==report['counts'] and str(minimum)==report['minimum_ratio_lower']
 result={'source_sha256':sha(Path(__file__)),'primary_readback_sha256':sha(W/'readback.json'),'incidences_reconstructed':True,'faces_verified':len(registry),'internal_ratio_bounds_verified':13696,'uncoupled_wall_initializations_verified':4864,'mrf_internal_faces_verified':384,'all_bounds_exact':True,'counts':dict(counts),'minimum_ratio_lower':str(minimum),'analytic_references':references,'manifests_verified':14,'payload_entries_verified':entries,'native_volumes_inherited_not_recomputed':True,'native_execution_roundoff_bounded':False,'native_admission':False,'elapsed_s':time.monotonic()-start}
 (W/'independent-readback.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
