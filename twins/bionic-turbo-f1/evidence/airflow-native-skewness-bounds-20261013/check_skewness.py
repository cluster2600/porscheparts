"""Native mathematical skewness with pinned centred moments."""
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
S=F(float('1e-150'));LIMIT=F(4)
def interval(a,z):return I(math.floor(a*Q),math.ceil(z*Q),True)
def pair(x):return F(x.lo,Q),F(x.hi,Q)
def divide(a,z,c,d):
 if c<=0<=d:raise ZeroDivisionError('signed denominator contains zero')
 vals=[x/y for x in (a,z) for y in (c,d)];return interval(min(vals),max(vals))
def quotient(x,y,add=F(0)):
 a,z=pair(x);c,d=pair(y);return divide(a,z,c+add,d+add)
def absolute(x):
 a,z=pair(x);return interval(max(F(0),a,-z),max(abs(a),abs(z)))
def skew(cf,A,co,cn,points):
 c=b.minus(cf,co);normA=b.norm(A)
 if cn is None:
  if pair(normA)[1]<S:n=[I(0)]*3
  elif pair(normA)[0]>=S:n=[quotient(x,normA) for x in A]
  else:raise ZeroDivisionError('normalised branch undecided')
  d=b.mul(n,b.dot(n,c));alpha=F(float('0.4'))
 else:d=b.minus(cn,co);alpha=F(float('0.2'))
 projection=b.dot(A,d);factor=quotient(b.dot(A,c),projection,S)
 sv=b.minus(c,b.mul(d,factor));ns=b.norm(sv)
 hat=[]
 for x in sv:
  z=quotient(x,ns,S);hat.append(interval(max(F(-1),pair(z)[0]),min(F(1),pair(z)[1])))
 nd=b.norm(d);lo,hi=pair(nd);lo=alpha*lo+S;hi=alpha*hi+S
 for p in points:
  a,z=pair(absolute(b.dot(hat,b.minus(p,cf))));lo=max(lo,a);hi=max(hi,z)
 result=divide(*pair(ns),lo,hi)
 # fd remains exact here; the recorded dyadic enclosure is diagnostic only.
 fd=interval(lo,hi)
 vals=[normA,projection,ns,fd,result]
 return [q for x in vals for q in (x.lo,x.hi)]
def references():
 assert pair(divide(S,S,2*S,2*S))==(F(1,2),F(1,2))
 assert pair(divide(F(0),F(0),S,S))==(F(0),F(0))
 try:divide(F(1),F(1),F(-1),F(1))
 except ZeroDivisionError:pass
 else:raise AssertionError('pole accepted')
 count=3
 for scale in (F(1),F(1,1000),F(1,1000000)):
  # Collinear native analytic centre configuration, with additive retained.
  cf=[I(scale),I(0),I(0)];co=[I(0)]*3;cn=[I(2*scale),I(0),I(0)];A=[I(scale**2),I(0),I(0)]
  points=[[I(scale),I(y*scale),I(z*scale)] for y,z in ((-1,-1),(1,-1),(1,1),(-1,1))]
  for boundary in (False,True):
   data=skew(cf,A,co,None if boundary else cn,points)
   dd=scale if boundary else 2*scale;alpha=F(float('0.4' if boundary else '0.2'))
   expected=(scale*S/(scale**2*dd+S))/(alpha*dd+S)
   assert F(data[-2],Q)<=expected<=F(data[-1],Q);count+=1
 # normalised's zero branch: S_area=0, d=0, sv=(1,0,0), vertex projection=1/(1+r).
 data=skew([I(1),I(0),I(0)],[I(0)]*3,[I(0)]*3,None,[[I(2),I(0),I(0)]])
 assert F(data[-2],Q)<=1+S<=F(data[-1],Q);count+=1
 return count

def main():
 start=time.monotonic();refs=references();deps=json.loads(Path('work/bionic-native-weight-bounds-20261013/dependencies.json').read_text())['manifests'];p=Path('work/bionic-airflow-delivery-20261013-native-weight-bounds/file-manifest.json');deps[str(p)]=sha(p);count=0;anchor='056526bccf0537fa1992a465c42a4b8c677ec700'
 for name,digest in deps.items():
  p=Path(name);phase=p.parent.name.split('20261013-',1)[1];raw=subprocess.check_output(['git','show',anchor+':twins/bionic-turbo-f1/evidence/airflow-'+phase+'-20261013/file-manifest.json']);assert hashlib.sha256(raw).hexdigest()==sha(p)==digest
  for row in json.loads(raw)['files']:
   fp=Path('work')/row['path'];assert sha(fp)==row['sha256'] and fp.stat().st_size==row['bytes'];count+=1
 assert len(deps)==16 and count==379
 (W/'dependencies.json').write_text(json.dumps({'anchor_commit':anchor,'manifests':deps,'payload_entries_verified':count},indent=2)+'\n')
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
   (a,i)=incidence[0];own=cell(a)
   nei=cell(incidence[1][0]) if len(incidence)==2 else None
   if own is None or (len(incidence)==2 and nei is None):return None,'unknown'
   cf,A=own[1][i]
   try:data=skew(cf,A,own[0],nei[0] if nei else None,[ps[label] for label in fs[a][i]])
   except ZeroDivisionError:return None,'unknown'
   return data,('positive' if F(data[-1],Q)<=LIMIT else 'refused' if F(data[-2],Q)>LIMIT else 'unknown')
  return evaluate
 counts=Counter();unknown=[];maximum=None;rows=0
 with gzip.open(W/'skewness-bounds.jsonl.gz','xt',compresslevel=3) as out:
  def emit(dom,rank,data,status):
   nonlocal maximum,rows
   out.write(json.dumps([dom,rank,data,status],separators=(',',':'))+'\n');rows+=1;counts[str(dom)+':'+status]+=1
   if status=='positive':maximum=data[-1] if maximum is None else max(maximum,data[-1])
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
 result={'source_sha256':sha(Path(__file__)),'preflight_sha256':sha(W/'preflight.md'),'dependencies_sha256':sha(W/'dependencies.json'),'bounds_sha256':sha(W/'skewness-bounds.jsonl.gz'),'domain_v':domain,'source_boxes':153,'faces':18560,'internal_faces':13696,'uncoupled_wall_faces':4864,'mrf_internal_faces':384,'fractional_bits':160,'references':refs,'counts':dict(counts),'envelope_unknown_ranks':unknown,'records':rows,'maximum_positive_upper':str(F(maximum,Q)),'ROOTVSMALL':str(S),'threshold':str(LIMIT),'native_admission':False,'roundoff_bounded':False,'elapsed_s':time.monotonic()-start}
 (W/'readback.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ('counts','envelope_unknown_ranks')}),flush=True)
if __name__=='__main__':main()
