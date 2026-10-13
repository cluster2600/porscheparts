"""Additive orthogonality: inherited intervals and constant native moments."""
import gzip, hashlib, importlib.util, json, math, time
from pathlib import Path
from fractions import Fraction as F
from collections import defaultdict, Counter
W=Path(__file__).parent
BITS=160; SCALE=1<<BITS; ROOT=F(float('1e-150'))
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def load(name,path,digest):
 assert sha(path)==digest
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
h=load('ortho_centred',Path('work/bionic-centre-interval-bounds-20261013/centred.py'),'4f366b9571c931fa8d4bf19e90e94c5bd77d0093c193a1e0de9caf1f3590361b');b=h.b;I=b.I

def root_bounds(x):
 assert x>=0
 n=math.isqrt((x.numerator*SCALE*SCALE)//x.denominator)
 lo=F(n,SCALE);hi=lo if lo*lo==x else F(n+1,SCALE)
 assert lo*lo<=x<=hi*hi
 return lo,hi

def quotient(d,den):
 assert 0<den[0]<=den[1]
 vals=[x/y for x in d for y in den]
 return (math.floor(min(vals)*SCALE),math.ceil(max(vals)*SCALE))

def evaluate(d,q):
 assert d[0]<=d[1] and 0<q[0]<=q[1]
 low=root_bounds(q[0])[0]+ROOT;high=root_bounds(q[1])[1]+ROOT
 return quotient(d,(low,high))

def recover_q(d,res,kap):
 assert d[0]>0 and res[0]+kap[0]>0
 return d[0]**2/(res[1]+kap[1]),d[1]**2/(res[0]+kap[0])

def status(d,c,threshold):
 if d[0]>0 and F(c[0],SCALE)>=threshold[1]:return 'positive'
 if d[1]<=0 or F(c[1],SCALE)<threshold[0]:return 'refused'
 return 'unknown'

def native_dq(owner,neighbour,area):
 delta=b.minus(neighbour,owner);d=b.dot(delta,area);q=b.dot(delta,delta)*b.dot(area,area)
 return (F(d.lo,SCALE),F(d.hi,SCALE)),(F(q.lo,SCALE),F(q.hi,SCALE))

def constant_records(src,sy):
 bind={r['point']:r for r in sy['coordinate_bindings']};u=F(sy['archived_regression_point']['u']);points={};fs=[];reg=defaultdict(list)
 for i,p in enumerate(src['vertices']):
  r=bind.get(i)
  if r and r['variable']=='v':continue
  points[i]=[I(F(r['x_coefficient'])*u),I(F(r['y_coefficient'])*u),I(F(r['z_exact']))] if r else [I(F(x)) for x in p]
 for cid,block in enumerate(src['blocks']):
  n=4 if src['stages'][cid]=='buffer' else 3;lo,hi=block[:n],block[4:4+n]
  faces=[lo[::-1],hi]+[[lo[j],lo[(j+1)%n],hi[(j+1)%n],hi[j]] for j in range(n)];fs.append(faces)
  for j,f in enumerate(faces):reg[tuple(sorted(f))].append((cid,j))
 fixed={i for i,block in enumerate(src['blocks']) if all(p in points for p in block)};cache={}
 assert len(fixed)==2304
 def cell(cid):
  if cid not in cache:
   anchor=points[src['blocks'][cid][0]];geo=[h.face([b.minus(points[p],anchor) for p in f]) for f in fs[cid]];c,v=h.cell(geo)
   assert v.lo>0;cache[cid]=(b.plus(c,anchor),[a for _,a in geo])
  return cache[cid]
 walls={key for key,inc in reg.items() if len(inc)==1};assert walls=={tuple(sorted(set(f))) for f in src['walls']} and len(walls)==4864
 keys=[key for key,inc in sorted(reg.items()) if len(inc)==2 and all(cid in fixed for cid,_ in inc)]
 assert len(keys)==4224 and {tuple(sorted(f)) for f in src['mrf_faces']}<=set(keys) and len(src['mrf_faces'])==384
 for rank,key in enumerate(keys):
  (a,j),(c,k)=reg[key];own=cell(a);nei=cell(c);d,q=native_dq(own[0],nei[0],own[1][j])
  yield rank,list(key),a,c,d,q

def main():
 start=time.monotonic();frozen=json.loads((W/'before-application.json').read_text())
 for name,digest in frozen['files'].items():assert sha(Path(name))==digest
 inventory=json.loads((W/'input-inventory.json').read_text())
 for name,digest in inventory['manifests'].items():
  p=Path(name);assert sha(p)==digest
  for r in json.loads(p.read_text())['files']:
   q=Path('work')/r['path'];assert q.stat().st_size==r['bytes'] and sha(q)==r['sha256']
 base=Path('work/bionic-angular-independent-bounds-20261013');boxes=json.loads((base/'certificate-readback.json').read_text())['box_results'];order=json.loads((base/'order.json').read_text())
 cert=json.loads(Path('work/bionic-feasibility-bounds-20261013/certificate.json').read_text());kap=tuple(map(F,cert['kappa']));threshold=(root_bounds(kap[0])[0],root_bounds(kap[1])[1]);counts=Counter();rows=0
 with gzip.open(W/'orthogonality-bounds.jsonl.gz','xt',compresslevel=3) as out:
  def emit(category,dom,rank,d,q):
   nonlocal rows
   c=evaluate(d,q);s=status(d,c,threshold);out.write(json.dumps([category,dom,rank,list(c),s],separators=(',',':'))+'\n');rows+=1;counts[f'{category}:{dom}:{s}']+=1
  with gzip.open(base/'angular-bounds.jsonl.gz','rt') as stream:
   for box in boxes:
    for rank in range(9470):
     old=json.loads(next(stream));assert old[:2]==[box['parent_leaf'],rank]
     d=tuple(F(x,1<<192) for x in old[2:4]);q=tuple(F(x,1<<192) for x in old[4:6]);emit('matrix',box['parent_leaf'],rank,d,q)
    print(json.dumps({'matrix_box':box['parent_leaf'],'rows':rows,'elapsed_s':time.monotonic()-start}),flush=True)
   assert next(stream,None) is None
  witnesses={r['parent_leaf']:r for r in json.loads(Path('work/bionic-centre-interval-bounds-20261013/centred-certificate.json').read_text())['rows']}
  recovered=[]
  for box in boxes:
   row=witnesses[box['parent_leaf']];assert (row['lower'],row['upper'])==(box['lower'],box['upper'])
   for rank,a in enumerate(row['angles']):
    d=tuple(map(F,a['combined']['D']));res=tuple(map(F,a['combined']['residual']));q=recover_q(d,res,kap);emit('witness',box['parent_leaf'],rank,d,q)
    recovered.append({'leaf':box['parent_leaf'],'rank':rank,'D':list(map(str,d)),'R':list(map(str,res)),'Q':list(map(str,q))})
  (W/'recovered-witnesses.json').write_text(json.dumps(recovered,indent=2)+'\n')
  src=json.loads(Path('work/bionic-buffered-transition-20261013/construction.json').read_text());sy=json.loads(Path('work/bionic-joint-constraints-20261013/system.json').read_text());constants=[]
  for rank,key,a,c,d,q in constant_records(src,sy):
   emit('constant','envelope',rank,d,q);constants.append({'rank':rank,'face':key,'owner':a,'neighbour':c,'D':list(map(str,d)),'Q':list(map(str,q))})
  (W/'constant-inputs.json').write_text(json.dumps(constants,indent=2)+'\n')
 assert rows==1448910+306+4224
 result={'source_sha256':sha(Path(__file__)),'bounds_sha256':sha(W/'orthogonality-bounds.jsonl.gz'),'constant_inputs_sha256':sha(W/'constant-inputs.json'),'recovered_witnesses_sha256':sha(W/'recovered-witnesses.json'),'fractional_bits':BITS,'records':rows,'counts':dict(counts),'threshold':list(map(str,threshold)),'ROOTVSMALL':str(ROOT),'domain_v':[boxes[0]['lower'],boxes[-1]['upper']],'walls_inherited_value':1,'uncoupled_walls':4864,'source_boxes':153,'matrix_geometry_recomputed':False,'constant_faces_new_native_moments':4224,'native_admission':False,'native_roundoff_bounded':False,'elapsed_s':time.monotonic()-start}
 (W/'readback.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='counts'}),flush=True)
if __name__=='__main__':main()
