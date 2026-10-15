"""Independent arithmetic readback; native reconstruction only for constants."""
import gzip,hashlib,importlib.util,json,math,time
from pathlib import Path
from fractions import Fraction as F
from collections import defaultdict,Counter
W=Path(__file__).parent;BITS=192;SCALE=1<<BITS;ROOT=F(float('1e-150'))
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def module(name,path,digest):
 assert sha(path)==digest
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
h=module('ortho_independent',Path('work/bionic-centre-interval-bounds-20261013/verify_centres_v2.py'),'a259f163405dec0cfb4f1b707698249ea9069de9b02a9db1835fb172f1a0b992');g=h.g
k=module('ortho_dyadic',Path('work/bionic-remaining-cell-bounds-20261013/dyadic192.py'),'f216b134a93a893b0c04bbe47671eb5ba497e4836e0e2a346220f0b14d83ac14');g.R=k.R;R=g.R
T=((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7))
def root_bounds(x):
 assert x>=0
 n=(x.numerator << (2*BITS))//x.denominator
 if n==0:z=0
 else:
  z=1<<((n.bit_length()+1)//2)
  while True:
   y=(z+n//z)//2
   if y>=z:break
   z=y
 assert z*z<=n<(z+1)*(z+1)
 a=F(z,SCALE);b=a if a*a==x else F(z+1,SCALE)
 assert a*a<=x<=b*b
 return a,b

def quotient(d,den):
 assert den[0]>0
 reciprocals=(1/den[1],1/den[0]);v=[x*y for x in d for y in reciprocals]
 return math.floor(min(v)*SCALE),math.ceil(max(v)*SCALE)
def evaluate(d,q):
 assert d[0]<=d[1] and 0<q[0]<=q[1]
 return quotient(d,(root_bounds(q[0])[0]+ROOT,root_bounds(q[1])[1]+ROOT))
def recover_q(d,res,kap):
 assert d[0]>0 and res[0]+kap[0]>0
 a=d[0]*d[0]/(res[1]+kap[1]);b=d[1]*d[1]/(res[0]+kap[0])
 assert a*(res[1]+kap[1])==d[0]*d[0] and b*(res[0]+kap[0])==d[1]*d[1]
 return a,b
def status(d,c,threshold):
 if d[0]>0 and F(c[0],SCALE)>=threshold[1]:return 'positive'
 if d[1]<=0 or F(c[1],SCALE)<threshold[0]:return 'refused'
 return 'unknown'
def native_dq(owner,neighbour,area):
 delta=g.vsub(neighbour,owner);d=g.inner(delta,area);q=g.inner(delta,delta)*g.inner(area,area)
 return (d.a,d.b),(q.a,q.b)
def constant_records(src,sy):
 bindings={r['point']:r for r in sy['coordinate_bindings']};u=F(sy['archived_regression_point']['u']);points={};reg=defaultdict(list);faces=[]
 for i,p in enumerate(src['vertices']):
  r=bindings.get(i)
  if r is not None and r['variable']=='v':continue
  points[i]=[R(F(r['x_coefficient'])*u),R(F(r['y_coefficient'])*u),R(F(r['z_exact']))] if r else list(map(lambda x:R(F(x)),p))
 canon=lambda f:min(tuple(f[i:]+f[:i]) for i in range(len(f)))
 for cid,block in enumerate(src['blocks']):
  cell=[]
  for template in T:
   f=[]
   for j in template:
    if not f or f[-1]!=block[j]:f.append(block[j])
   if f[-1]==f[0]:f.pop()
   if len(f)>2:reg[tuple(sorted(f))].append((cid,len(cell)));cell.append(f)
  faces.append(cell)
 for incidences in reg.values():
  assert len(incidences) in (1,2)
  if len(incidences)==2:
   (a,i),(b,j)=incidences;assert canon(faces[a][i])==canon(faces[b][j][::-1])
 walls={f for f,inc in reg.items() if len(inc)==1};assert walls=={tuple(sorted(set(f))) for f in src['walls']} and len(walls)==4864
 fixed={cid for cid,block in enumerate(src['blocks']) if all(i in points for i in block)};assert len(fixed)==2304
 keys=[f for f,inc in sorted(reg.items()) if len(inc)==2 and all(cid in fixed for cid,_ in inc)];assert len(keys)==4224
 assert len(src['mrf_faces'])==384 and {tuple(sorted(f)) for f in src['mrf_faces']}<=set(keys)
 # Disjoint complete partition, using pinned labels, not archived floating angles.
 order=json.loads(Path('work/bionic-angular-independent-bounds-20261013/order.json').read_text())
 selected=json.loads(Path('work/bionic-feasibility-bounds-20261013/certificate.json').read_text())['selected'][:2]
 variable={tuple(sorted(r['face'])) for r in order};witness={tuple(sorted(r['face'])) for r in selected}
 assert len(variable)==9470 and len(witness)==2 and not variable&witness and not (variable|witness)&set(keys)
 assert variable|witness|set(keys)=={f for f,inc in reg.items() if len(inc)==2}
 for row in order+selected:
  inc=reg[tuple(sorted(row['face']))];assert sorted([row['owner'],row['neighbour']])==sorted(cid for cid,_ in inc)
 cache={}
 def cell(cid):
  if cid not in cache:
   origin=points[src['blocks'][cid][0]];c,v,geo=h.moments([[g.vsub(points[i],origin) for i in f] for f in faces[cid]])
   assert v.a>0;cache[cid]=(g.vadd(c,origin),[a for _,a in geo])
  return cache[cid]
 for rank,key in enumerate(keys):
  (a,i),(b,j)=reg[key];own=cell(a);nei=cell(b);d,q=native_dq(own[0],nei[0],own[1][i])
  yield rank,list(key),a,b,d,q

def main():
 start=time.monotonic();report=json.loads((W/'readback.json').read_text());assert sha(W/'orthogonality-bounds.jsonl.gz')==report['bounds_sha256']
 frozen=json.loads((W/'before-application.json').read_text())
 for name,digest in frozen['files'].items():assert sha(Path(name))==digest
 inv=json.loads((W/'input-inventory.json').read_text());entries=0
 for name,digest in inv['manifests'].items():
  p=Path(name);assert sha(p)==digest
  for row in json.loads(p.read_text())['files']:
   p=Path('work')/row['path'];assert sha(p)==row['sha256'] and p.stat().st_size==row['bytes'];entries+=1
 assert entries==419 and len(inv['manifests'])==17
 base=Path('work/bionic-angular-independent-bounds-20261013');boxes=json.loads((base/'certificate-readback.json').read_text())['box_results'];kap=tuple(map(F,json.loads(Path('work/bionic-feasibility-bounds-20261013/certificate.json').read_text())['kappa']));threshold=(root_bounds(kap[0])[0],root_bounds(kap[1])[1]);primary_threshold=tuple(map(F,report['threshold']));assert primary_threshold[0]<=threshold[0]<=threshold[1]<=primary_threshold[1]
 rows=0;counts=Counter();confirmed=Counter()
 with gzip.open(W/'orthogonality-bounds.jsonl.gz','rt') as stream:
  def check(category,dom,rank,d,q):
   nonlocal rows
   row=json.loads(next(stream));assert row[:3]==[category,dom,rank];actual=evaluate(d,q);lower,upper=(F(x,1<<160) for x in row[3]);lo,hi=(F(x,SCALE) for x in actual)
   assert lower<=lo<=hi<=upper,(category,dom,rank)
   expected='positive' if d[0]>0 and lower>=primary_threshold[1] else 'refused' if d[1]<=0 or upper<primary_threshold[0] else 'unknown'
   # Constant D may be narrower independently; classify original D separately below.
   assert row[4]==expected
   if row[4]!='unknown':assert status(d,actual,threshold)==row[4]
   counts[f'{category}:{dom}:{row[4]}']+=1;confirmed[row[4]]+=1;rows+=1
  with gzip.open(base/'angular-bounds.jsonl.gz','rt') as source:
   for box in boxes:
    for rank in range(9470):
     r=json.loads(next(source));assert r[:2]==[box['parent_leaf'],rank];check('matrix',box['parent_leaf'],rank,tuple(F(x,1<<192) for x in r[2:4]),tuple(F(x,1<<192) for x in r[4:6]))
    print(json.dumps({'box':box['parent_leaf'],'rows_verified':rows,'elapsed_s':time.monotonic()-start}),flush=True)
   assert next(source,None) is None
  old={r['parent_leaf']:r for r in json.loads(Path('work/bionic-centre-interval-bounds-20261013/centred-certificate.json').read_text())['rows']};recovered=json.loads((W/'recovered-witnesses.json').read_text());assert sha(W/'recovered-witnesses.json')==report['recovered_witnesses_sha256'];idx=0
  for box in boxes:
   r=old[box['parent_leaf']];assert (r['lower'],r['upper'])==(box['lower'],box['upper'])
   for rank,a in enumerate(r['angles']):
    d=tuple(map(F,a['combined']['D']));res=tuple(map(F,a['combined']['residual']));q=recover_q(d,res,kap);entry=recovered[idx];assert entry=={'leaf':box['parent_leaf'],'rank':rank,'D':list(map(str,d)),'R':list(map(str,res)),'Q':list(map(str,q))};idx+=1;check('witness',box['parent_leaf'],rank,d,q)
  assert idx==len(recovered)==306
  assert sha(W/'constant-inputs.json')==report['constant_inputs_sha256'];constants=json.loads((W/'constant-inputs.json').read_text());assert len(constants)==4224
  src=json.loads(Path('work/bionic-buffered-transition-20261013/construction.json').read_text());sy=json.loads(Path('work/bionic-joint-constraints-20261013/system.json').read_text())
  for rank,key,a,b,d,q in constant_records(src,sy):
   row=constants[rank];assert (row['rank'],row['face'],row['owner'],row['neighbour'])==(rank,key,a,b)
   for name,actual in [('D',d),('Q',q)]:
    low,high=map(F,row[name]);assert low<=actual[0]<=actual[1]<=high
   check('constant','envelope',rank,d,q)
  assert next(stream,None) is None
 assert rows==report['records']==1453440 and dict(counts)==report['counts']
 out={'source_sha256':sha(Path(__file__)),'primary_readback_sha256':sha(W/'readback.json'),'records_verified':rows,'counts':dict(confirmed),'all_output_bounds_contained':True,'constant_D_Q_intervals_verified':8448,'all_claimed_signs_confirmed':True,'internal_face_partition_verified':13696,'uncoupled_walls':4864,'boxes':153,'matrix_geometry_recomputed':False,'constant_geometry_independently_reconstructed':True,'native_admission':False,'elapsed_s':time.monotonic()-start}
 (W/'independent-readback.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out),flush=True)
if __name__=='__main__':main()
