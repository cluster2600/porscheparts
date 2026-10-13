"""Exact conservative native volume-ratio bounds from certified parent volumes."""
import gzip,hashlib,json,re,subprocess,tarfile,time
from pathlib import Path
from fractions import Fraction as F
from collections import defaultdict,Counter
W=Path(__file__).parent
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
S=F(float('1e-300'));LIMIT=F(float('0.01'))
def ratio(a,b):return [min(a[0],b[0])/(max(a[1],b[1])+S),min(a[1],b[1])/(max(a[0],b[0])+S)]
def references():
 for a,b,target in ((F(1),F(1),1/(1+S)),(F(1),F(2),1/(2+S)),(F(2),F(1),1/(2+S)),(S,S,F(1,2)),(S,2*S,F(1,3))):assert ratio([a,a],[b,b])==[target,target]
 assert ratio([F(1),F(2)],[F(2),F(3)])==[1/(3+S),2/(2+S)]
 return 6
def main():
 start=time.monotonic();refs=references();deps=json.loads(Path('work/bionic-native-flatness-bounds-20261013/dependencies.json').read_text())['manifests'];p=Path('work/bionic-airflow-delivery-20261013-native-flatness-bounds/file-manifest.json');deps[str(p)]=sha(p);entries=0;anchor='7a1282bdbe43411ade9c0e79e831cc5c9973bb6d'
 for name,digest in deps.items():
  p=Path(name);phase=p.parent.name.split('20261013-',1)[1];raw=subprocess.check_output(['git','show',anchor+':twins/bionic-turbo-f1/evidence/airflow-'+phase+'-20261013/file-manifest.json']);assert hashlib.sha256(raw).hexdigest()==sha(p)==digest
  for r in json.loads(raw)['files']:
   p=Path('work')/r['path'];assert sha(p)==r['sha256'] and p.stat().st_size==r['bytes'];entries+=1
 assert len(deps)==14 and entries==332
 (W/'dependencies.json').write_text(json.dumps({'anchor_commit':anchor,'manifests':deps,'payload_entries_verified':entries},indent=2)+'\n')
 archive=Path('work/bionic-native-diagnostics-20261012/OpenFOAM-v2406.tgz');assert sha(archive)=='8d1450fb89eec1e7cecc55c3bb7bc486ccbf63d069379d1d5d7518fa16a4686a';members=[]
 with tarfile.open(archive,'r:gz') as tar:
  for name in ('polyMeshTools.C','polyMeshCheck.C'):
   member='OpenFOAM-v2406/src/OpenFOAM/meshes/polyMesh/polyMeshCheck/'+name;raw=tar.extractfile(member).read();assert raw==(W/name).read_bytes();members.append({'member':member,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
 tools=(W/'polyMeshTools.C').read_text();check=(W/'polyMeshCheck.C').read_text();app=Path('work/bionic-native-admission-dossier-20261013/checkGeometry.C').read_text();assert 'min(volOwn,volNei)/(max(volOwn, volNei)+VSMALL)' in tools and 'if (volRatio[facei] < minRatio)' in check and 'mesh.checkVolRatio(true, 0.01, &faces)' in app
 (W/'source-audit.json').write_text(json.dumps({'archive_sha256':sha(archive),'members':members,'formula':'min(volOwn,volNei)/(max(volOwn, volNei)+VSMALL)','rejection':'volRatio[facei] < minRatio','call':'mesh.checkVolRatio(true, 0.01, &faces)','WM_DP_conditional':True,'VSMALL':str(S),'threshold':str(LIMIT)},indent=2)+'\n')
 src=json.loads(Path('work/bionic-buffered-transition-20261013/construction.json').read_text());boxes=json.loads(Path('work/bionic-angular-independent-bounds-20261013/certificate-readback.json').read_text())['box_results'];domain=[boxes[0]['lower'],boxes[-1]['upper']];model=Path('work/bionic-volume-representation-20261013/models.jsonl.gz');assert sha(model)=='780a6bece9fa9aafd010a7ff91fc78d571a1e4c3e1102b0ebef1f04cd191ea9a'
 for name in ('readback.json','independent-readback.json'):
  r=json.loads((model.parent/name).read_text());assert r['domain_v']==domain and r['models_sha256']==sha(model)
 assert r['all_coefficients_and_bounds_exact'] and r['cells_verified']==6144
 volumes={}
 with gzip.open(model,'rt') as stream:
  for line in stream:
   r=json.loads(line)
   if r['kind']=='cell':volumes[r['cell']]=list(map(F,r['fan_signed_volume']['bounds']))
 assert len(volumes)==6144 and all(0<a<=b for a,b in volumes.values())
 registry=defaultdict(list)
 for cid,block in enumerate(src['blocks']):
  n=4 if src['stages'][cid]=='buffer' else 3;lo,hi=block[:n],block[4:4+n]
  for f in [lo[::-1],hi]+[[lo[j],lo[(j+1)%n],hi[(j+1)%n],hi[j]] for j in range(n)]:registry[tuple(sorted(f))].append(cid)
 def reduced(f):return tuple(sorted(set(f)))
 boundary={k for k,v in registry.items() if len(v)==1};assert boundary=={reduced(f) for f in src['walls']}
 old=Path('work/bionic-buffered-transition-20261013/blockMeshDict').read_text();tail=old[old.index('boundary'):];match=re.fullmatch(r'boundary\s*\(\s*walls\s*\{type wall; faces \((.*)\);\}\);\s*',tail,re.S);assert match
 wallfaces=[list(map(int,s.split())) for s in re.findall(r'\(([^()]*)\)',match[1])];assert wallfaces==src['walls']
 assert len(src['mrf_faces'])==384 and all(len(registry[reduced(f)])==2 for f in src['mrf_faces'])
 counts=Counter();minimum=None;worst=None
 with gzip.open(W/'ratio-bounds.jsonl.gz','wt') as out:
  for rank,(face,cells) in enumerate(sorted(registry.items())):
   assert len(cells) in (1,2)
   bounds=ratio(volumes[cells[0]],volumes[cells[1]]) if len(cells)==2 else [F(1),F(1)]
   status='positive' if bounds[0]>=LIMIT else ('refused' if bounds[1]<LIMIT else 'unknown');counts[status]+=1
   if minimum is None or bounds[0]<minimum:minimum=bounds[0];worst={'rank':rank,'face':face,'cells':cells}
   out.write(json.dumps({'rank':rank,'face':face,'cells':cells,'branch':'internal' if len(cells)==2 else 'uncoupled_wall','volumes':[list(map(str,volumes[c])) for c in cells],'ratio':list(map(str,bounds)),'status':status},separators=(',',':'))+'\n')
 result={'source_sha256':sha(Path(__file__)),'preflight_sha256':sha(W/'preflight.md'),'dependencies_sha256':sha(W/'dependencies.json'),'source_audit_sha256':sha(W/'source-audit.json'),'bounds_sha256':sha(W/'ratio-bounds.jsonl.gz'),'inherited_models_sha256':sha(model),'domain_v':domain,'source_boxes':len(boxes),'faces':len(registry),'internal_faces':len(registry)-len(boundary),'uncoupled_wall_faces':len(boundary),'mrf_faces_internal':384,'counts':dict(counts),'minimum_ratio_lower':str(minimum),'minimum_location':worst,'analytic_references':refs,'VSMALL':str(S),'threshold':str(LIMIT),'old_volume_polynomials_recomputed':False,'native_execution_roundoff_bounded':False,'native_admission':False,'elapsed_s':time.monotonic()-start}
 (W/'readback.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
