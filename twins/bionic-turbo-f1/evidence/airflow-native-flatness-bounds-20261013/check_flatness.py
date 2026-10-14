"""Outward bounds for mathematical native-centre flatness and guards."""
import gzip,hashlib,importlib.util,json,math,subprocess,time
from pathlib import Path
from fractions import Fraction as F
from collections import defaultdict,Counter
W=Path(__file__).parent
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def load(name,path,digest):
 assert sha(path)==digest
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
c=load('centred',Path('work/bionic-centre-interval-bounds-20261013/centred.py'),'4f366b9571c931fa8d4bf19e90e94c5bd77d0093c193a1e0de9caf1f3590361b');b=c.b;I=b.I
ROOT=F(float('1e-150'));SMALL=F(float('1e-300'));LIMIT=F(float('0.8'))
def lower(x):return F(x.lo,b.Q)
def upper(x):return F(x.hi,b.Q)
def interval(a,z):return I(math.floor(a*b.Q),math.ceil(z*b.Q),True)
def geometry(q):
 if len(q)==3:
  cf=b.mean(q);S=b.mul(b.cross(b.minus(q[1],q[0]),b.minus(q[2],q[0])),F(1,2));return {'magS':b.norm(S),'flatness':I(1)},S
 cf,S=c.face(q);seed=b.mean(q)
 weight=sum(b.norm(b.cross(b.minus(y,x),b.minus(seed,x))) for x,y in zip(q,q[1:]+q[:1]))
 area=sum(b.norm(b.mul(b.cross(b.minus(y,x),b.minus(cf,x)),F(1,2))) for x,y in zip(q,q[1:]+q[:1]))
 mag=b.norm(S);return {'W':weight,'magS':mag,'A':area,'flatness':mag/(area+I(ROOT))},S

def references():
 count=0
 for scale in (F(1),F(1,1000),F(1,1000000)):
  shapes=[[(0,0,0),(1,0,0),(0,1,0)],[(-1,-1,0),(1,-1,0),(1,1,0),(-1,1,0)],[(-1,-1,1),(1,-1,-1),(1,1,1),(-1,1,-1)]]
  for i,points in enumerate(shapes):
   r,_=geometry([[I(scale*x) for x in p] for p in points]);lo,hi=lower(r['flatness']),upper(r['flatness']);A=4*scale**2
   if i<2:
    expected=F(1) if i==0 else A/(A+ROOT);assert lo<=expected<=hi
   else:
    t=lambda x:(A-ROOT*x)/(A*x)
    assert lo>0 and t(lo)>0 and t(lo)**2>=2 and (t(hi)<=0 or t(hi)**2<=2)
   count+=1
 return count

def main():
 start=time.monotonic();refs=references();deps=json.loads(Path('work/bionic-native-admission-dossier-20261013/dependencies.json').read_text())['manifests'];p=Path('work/bionic-airflow-delivery-20261013-native-admission-dossier/file-manifest.json');deps[str(p)]=sha(p);count=0
 anchor='cbf1a91cf4d53872ad2b067b0dc1fe5fe95e7f2b'
 for name,digest in deps.items():
  p=Path(name);phase=p.parent.name.split('20261013-',1)[1];raw=subprocess.check_output(['git','show',anchor+':twins/bionic-turbo-f1/evidence/airflow-'+phase+'-20261013/file-manifest.json']);assert hashlib.sha256(raw).hexdigest()==digest==sha(p)
  for row in json.loads(raw)['files']:
   fp=Path('work')/row['path'];assert sha(fp)==row['sha256'] and fp.stat().st_size==row['bytes'];count+=1
 (W/'dependencies.json').write_text(json.dumps({'anchor_commit':anchor,'manifests':deps,'payload_entries_verified':count},indent=2)+'\n')
 source=json.loads(Path('work/bionic-buffered-transition-20261013/construction.json').read_text());system=json.loads(Path('work/bionic-joint-constraints-20261013/system.json').read_text());bindings={r['point']:r for r in system['coordinate_bindings']};u=F(system['archived_regression_point']['u']);boxes=json.loads(Path('work/bionic-angular-independent-bounds-20261013/certificate-readback.json').read_text())['box_results'];domain=[boxes[0]['lower'],boxes[-1]['upper']]
 registry=defaultdict(list);canon=lambda f:min(tuple(f[i:]+f[:i]) for i in range(len(f)))
 for cid,block in enumerate(source['blocks']):
  n=4 if source['stages'][cid]=='buffer' else 3;lo,hi=block[:n],block[4:4+n]
  for f in [lo[::-1],hi]+[[lo[j],lo[(j+1)%n],hi[(j+1)%n],hi[j]] for j in range(n)]:registry[tuple(sorted(f))].append((cid,canon(f)))
 keys=sorted(registry);assert len(keys)==18560
 def points(v):
  result=[]
  for i,p in enumerate(source['vertices']):
   r=bindings.get(i)
   if r:
    x=I(u) if r['variable']=='u' else v;result.append([I(F(r['x_coefficient']))*x,I(F(r['y_coefficient']))*x,I(F(r['z_exact']))])
   else:result.append([I(F(x)) for x in p])
  return result
 def evaluate(rank,ps):
  f=registry[keys[rank]][0][1];anchor=[I(F(x)) for x in source['vertices'][f[0]]];r,_=geometry([b.minus(ps[i],anchor) for i in f]);passed=(len(f)==3 or (lower(r['W'])>=ROOT and lower(r['magS'])>ROOT)) and lower(r['flatness'])>=LIMIT
  return {'rank':rank,'face':list(f),'bounds':{k:x.pair() for k,x in r.items()},'status':'positive' if passed else 'unknown'}
 hullpoints=points(interval(*map(F,domain)));hull=[];unknown=[];localcounts=Counter()
 with gzip.open(W/'flatness-bounds.jsonl.gz','wt') as out:
  for rank in range(len(keys)):
   r=evaluate(rank,hullpoints);r['domain']='envelope';out.write(json.dumps(r,separators=(',',':'))+'\n');hull.append(r)
   if r['status']=='unknown':unknown.append(rank)
  for box in boxes:
   if not unknown:break
   ps=points(interval(F(box['lower']),F(box['upper'])))
   for rank in unknown:
    r=evaluate(rank,ps);r['domain']=box['parent_leaf'];out.write(json.dumps(r,separators=(',',':'))+'\n');localcounts[r['status']]+=1
 # New guard application of inherited volume bounds; no polynomial evaluation.
 volumes={}
 model=Path('work/bionic-volume-representation-20261013/models.jsonl.gz')
 with gzip.open(model,'rt') as inp:
  for line in inp:
   r=json.loads(line)
   if r['kind']=='cell':volumes[r['cell']]=r
 internal=defaultdict(list)
 for rank,key in enumerate(keys):
  if len(registry[key])==2:
   for cid,_ in registry[key]:internal[cid].append(rank)
 guards=[]
 for cid in range(6144):
  ranks=internal[cid];Elo=sum(F(hull[i]['bounds']['magS'][0]) for i in ranks);Ehi=sum(F(hull[i]['bounds']['magS'][1]) for i in ranks)
  vr=volumes[cid];Vlo=F(vr['fan_signed_volume']['bounds'][0]);Vhi=F(vr['fan_signed_volume']['bounds'][1]);guards.append({'cell':cid,'internal_faces':len(ranks),'E':[str(Elo),str(Ehi)],'triple_volume':[str(3*Vlo),str(3*Vhi)],'determinant_guard_inactive':bool(ranks) and Elo>=ROOT,'volume_guard_inactive':3*Vlo>SMALL})
 (W/'guards.json').write_text(json.dumps(guards,separators=(',',':'))+'\n')
 out={'source_sha256':sha(Path(__file__)),'preflight_sha256':sha(W/'preflight.md'),'dependencies_sha256':sha(W/'dependencies.json'),'bounds_sha256':sha(W/'flatness-bounds.jsonl.gz'),'guards_sha256':sha(W/'guards.json'),'inherited_models_sha256':sha(model),'domain_v':domain,'source_boxes':153,'faces':len(keys),'triangles':sum(len(k)==3 for k in keys),'quads':sum(len(k)==4 for k in keys),'envelope_positive':len(keys)-len(unknown),'envelope_unknown':len(unknown),'local_counts':dict(localcounts),'references':refs,'ROOTVSMALL':str(ROOT),'VSMALL':str(SMALL),'flatness_threshold':str(LIMIT),'determinant_guards_inactive':sum(r['determinant_guard_inactive'] for r in guards),'volume_guards_inactive':sum(r['volume_guard_inactive'] for r in guards),'native_execution_roundoff_bounded':False,'candidate_created':False,'native_admission':False,'elapsed_s':time.monotonic()-start}
 (W/'readback.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out),flush=True)
if __name__=='__main__':main()
