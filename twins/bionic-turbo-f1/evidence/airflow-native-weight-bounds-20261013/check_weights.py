"""Native mathematical face weights with pinned centred moments."""
import gzip,hashlib,importlib.util,json,math,subprocess,time
from pathlib import Path
from fractions import Fraction as F
from collections import defaultdict,Counter
W=Path(__file__).parent
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def load(name,path,digest):
 assert sha(path)==digest
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
h=load('centred',Path('work/bionic-centre-interval-bounds-20261013/centred.py'),'4f366b9571c931fa8d4bf19e90e94c5bd77d0093c193a1e0de9caf1f3590361b');b=h.b;I=b.I;Q=b.Q
S=F(float('1e-300'));LIMIT=F(float('0.05'))
def interval(a,z):return I(math.floor(a*Q),math.ceil(z*Q),True)
def absolute(l,r):return max(F(0),l,-r),max(abs(l),abs(r))
def rational_weight(a,z,c,d):
 low=min(a/(a+d+S),c/(c+z+S));high=min(F(1,2),z/(z+c+S),d/(d+a+S))
 return low,high
def weight(x,y):
 low,high=rational_weight(*absolute(F(x.lo,Q),F(x.hi,Q)),*absolute(F(y.lo,Q),F(y.hi,Q)))
 return math.floor(low*Q),math.ceil(high*Q)
def references():
 assert rational_weight(S,S,S,S)==(F(1,3),F(1,3))
 assert rational_weight(S,S,2*S,2*S)==(F(1,4),F(1,4))
 n=2
 for x,y in [(1,1),(-1,2),(2,-1),(S,S),(S,2*S),(0,1)]:
  exact=min(abs(F(x)),abs(F(y)))/(abs(F(x))+abs(F(y))+S);l,r=weight(I(x),I(y));assert F(l,Q)<=exact<=F(r,Q);n+=1
 assert weight(interval(F(-1),F(1)),I(1))[0]==0;n+=1
 templates=((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7))
 for scale in (F(1),F(1,1000),F(1,1000000)):
  cells=[]
  for shift in (0,1):
   ps=[[I(scale*(x+shift)),I(scale*y),I(scale*z)] for x,y,z in ((0,0,0),(1,0,0),(1,1,0),(0,1,0),(0,0,1),(1,0,1),(1,1,1),(0,1,1))]
   geo=[h.face([ps[i] for i in f]) for f in templates];C,V=h.cell(geo);assert F(V.lo,Q)<=scale**3<=F(V.hi,Q);cells.append((C,geo))
  cf,A=cells[0][1][3];x=b.dot(A,b.minus(cf,cells[0][0]));y=b.dot(A,b.minus(cells[1][0],cf));l,r=weight(x,y);expected=(scale**3/2)/(scale**3+S);assert F(l,Q)<=expected<=F(r,Q);n+=1
 return n

def main():
 start=time.monotonic();refs=references();deps=json.loads(Path('work/bionic-native-volume-ratio-bounds-20261013/dependencies.json').read_text())['manifests'];p=Path('work/bionic-airflow-delivery-20261013-native-volume-ratio-bounds/file-manifest.json');deps[str(p)]=sha(p);count=0;anchor='efc7b2488dde73e5a1ae21b86fe2347f40d0ab0f'
 for name,digest in deps.items():
  p=Path(name);phase=p.parent.name.split('20261013-',1)[1];raw=subprocess.check_output(['git','show',anchor+':twins/bionic-turbo-f1/evidence/airflow-'+phase+'-20261013/file-manifest.json']);assert hashlib.sha256(raw).hexdigest()==sha(p)==digest
  for row in json.loads(raw)['files']:
   fp=Path('work')/row['path'];assert sha(fp)==row['sha256'] and fp.stat().st_size==row['bytes'];count+=1
 assert len(deps)==15 and count==357
 (W/'dependencies.json').write_text(json.dumps({'anchor_commit':anchor,'manifests':deps,'payload_entries_verified':count},indent=2)+'\n')
 native=Path('work/bionic-native-volume-ratio-bounds-20261013');tools=(native/'polyMeshTools.C').read_text();check=(native/'polyMeshCheck.C').read_text();app=Path('work/bionic-native-admission-dossier-20261013/checkGeometry.C').read_text()
 assert 'min(dNei,dOwn)/(dNei+dOwn+VSMALL)' in tools and 'if (faceWght[facei] < minWeight)' in check and 'mesh.checkFaceWeight(true, 0.05, &faces)' in app
 src=json.loads(Path('work/bionic-buffered-transition-20261013/construction.json').read_text());sy=json.loads(Path('work/bionic-joint-constraints-20261013/system.json').read_text());bind={r['point']:r for r in sy['coordinate_bindings']};u=F(sy['archived_regression_point']['u']);boxes=json.loads(Path('work/bionic-angular-independent-bounds-20261013/certificate-readback.json').read_text())['box_results'];domain=[boxes[0]['lower'],boxes[-1]['upper']]
 fs=[];reg=defaultdict(list)
 for cid,block in enumerate(src['blocks']):
  n=4 if src['stages'][cid]=='buffer' else 3;lo,hi=block[:n],block[4:4+n];faces=[lo[::-1],hi]+[[lo[j],lo[(j+1)%n],hi[(j+1)%n],hi[j]] for j in range(n)];fs.append(faces)
  for i,f in enumerate(faces):reg[tuple(sorted(f))].append((cid,i))
 keys=sorted(reg);assert len(keys)==18560
 assert {k for k,v in reg.items() if len(v)==1}=={tuple(sorted(set(f))) for f in src['walls']}
 assert len(src['mrf_faces'])==384 and all(len(reg[tuple(sorted(f))])==2 for f in src['mrf_faces'])
 anchors=[[I(F(x)) for x in src['vertices'][block[0]]] for block in src['blocks']]
 def evaluator(low,high):
  v=interval(F(low),F(high));ps=[];cache={}
  for i,p in enumerate(src['vertices']):
   r=bind.get(i)
   if r:
    t=I(u) if r['variable']=='u' else v;ps.append([I(F(r['x_coefficient']))*t,I(F(r['y_coefficient']))*t,I(F(r['z_exact']))])
   else:ps.append([I(F(x)) for x in p])
  def cell(cid):
   if cid not in cache:
    try:
     geo=[h.face([b.minus(ps[i],anchors[cid]) for i in f]) for f in fs[cid]];C,V=h.cell(geo);cache[cid]=(b.plus(C,anchors[cid]),[(b.plus(cf,anchors[cid]),A) for cf,A in geo])
    except ZeroDivisionError:cache[cid]=None
   return cache[cid]
  def evaluate(rank):
   incidence=reg[keys[rank]]
   if len(incidence)==1:return [Q,Q],'positive'
   (a,i),(c,j)=incidence;own=cell(a);nei=cell(c)
   if own is None or nei is None:return None,'unknown'
   cf,A=own[1][i];x=b.dot(A,b.minus(cf,own[0]));y=b.dot(A,b.minus(nei[0],cf));l,r=weight(x,y)
   return [x.lo,x.hi,y.lo,y.hi,l,r],('positive' if F(l,Q)>=LIMIT else 'refused' if F(r,Q)<LIMIT else 'unknown')
  return evaluate
 counts=Counter();unknown=[];minimum=None;rows=0
 with gzip.open(W/'weight-bounds.jsonl.gz','xt',compresslevel=3) as out:
  def emit(dom,rank,data,status):
   nonlocal minimum,rows
   out.write(json.dumps([dom,rank,data,status],separators=(',',':'))+'\n');rows+=1;counts[str(dom)+':'+status]+=1
   if status=='positive':minimum=data[-2] if minimum is None else min(minimum,data[-2])
  calc=evaluator(*domain)
  for rank in range(len(keys)):
   data,status=calc(rank);emit('envelope',rank,data,status)
   if status=='unknown':unknown.append(rank)
  print(json.dumps({'envelope_counts':dict(counts),'local_faces':len(unknown)}),flush=True)
  for box in boxes:
   if not unknown:break
   calc=evaluator(box['lower'],box['upper'])
   for rank in unknown:
    data,status=calc(rank);emit(box['parent_leaf'],rank,data,status)
   print(json.dumps({'box':box['parent_leaf'],'records':rows,'elapsed_s':time.monotonic()-start}),flush=True)
 result={'source_sha256':sha(Path(__file__)),'preflight_sha256':sha(W/'preflight.md'),'dependencies_sha256':sha(W/'dependencies.json'),'bounds_sha256':sha(W/'weight-bounds.jsonl.gz'),'domain_v':domain,'source_boxes':153,'faces':18560,'internal_faces':13696,'uncoupled_wall_faces':4864,'mrf_internal_faces':384,'fractional_bits':160,'references':refs,'counts':dict(counts),'envelope_unknown_ranks':unknown,'records':rows,'minimum_positive_lower':str(F(minimum,Q)),'VSMALL':str(S),'threshold':str(LIMIT),'native_admission':False,'roundoff_bounded':False,'elapsed_s':time.monotonic()-start}
 (W/'readback.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ('counts','envelope_unknown_ranks')}),flush=True)
if __name__=='__main__':main()
