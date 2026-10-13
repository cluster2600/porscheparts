"""Independent reconstruction and inclusion reader; no primary imports."""
import gzip,hashlib,json,time
from pathlib import Path
from collections import defaultdict,Counter
from fractions import Fraction as F
import quality_independent_v2 as q
W=Path(__file__).parent
T=((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7))
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def cycle(f):return list(min(tuple(f[j:]+f[:j]) for j in range(len(f))))
def conjunction(s):return 'refused' if any(x=='refused' for x in s) else 'positive' if all(x=='positive' for x in s) else 'unknown'
def disjunction(s):return 'positive' if any(x=='positive' for x in s) else 'refused' if all(x=='refused' for x in s) else 'unknown'
def status(data,owner=False,strict=False):
 if data[1] is None:return 'unknown'
 lo,hi=[F(x,1<<160) for x in data[1][-2:]]
 return q.classify((-hi,-lo) if owner else (lo,hi),strict)
def main():
 start=time.monotonic();receipt=json.loads((W/'readback.json').read_text());assert sha(W/'face-tets-bounds.jsonl.gz')==receipt['bounds_sha256']
 for p,d in json.loads((W/'before-application.json').read_text())['files'].items():assert sha(Path(p))==d
 src=json.loads(Path('work/bionic-buffered-transition-20261013/construction.json').read_text());sy=json.loads(Path('work/bionic-joint-constraints-20261013/system.json').read_text());binding={r['point']:r for r in sy['coordinate_bindings']};u=F(sy['archived_regression_point']['u'])
 boxes=json.loads(Path('work/bionic-angular-independent-bounds-20261013/certificate-readback.json').read_text())['box_results'];assert len(boxes)==153
 hull=[boxes[0]['lower'],boxes[-1]['upper']];assert receipt['domain_v']==hull
 cells=[];registry=defaultdict(list)
 for cid,b in enumerate(src['blocks']):
  faces=[]
  for template in T:
   f=[]
   for j in template:
    if not f or b[j]!=f[-1]:f.append(b[j])
   if len(f)>1 and f[0]==f[-1]:f.pop()
   if len(f)<3:continue
   f=cycle(f);faces.append(f);registry[tuple(sorted(f))].append((cid,len(faces)-1))
  cells.append(faces)
 keys=sorted(registry);assert len(keys)==18560
 internal={k for k,v in registry.items() if len(v)==2};walls={k for k,v in registry.items() if len(v)==1}
 assert len(internal)==13696 and len(walls)==4864 and internal|walls==set(keys)
 assert walls=={tuple(sorted(set(f))) for f in src['walls']}
 mrf={tuple(sorted(set(f))) for f in src['mrf_faces']};assert len(mrf)==384 and mrf<=internal
 for k in internal:
  (a,j),(b,l)=registry[k];assert cycle(cells[a][j][::-1])==cells[b][l]
 anchors=[[q.R(F(x)) for x in src['vertices'][b[0]]] for b in src['blocks']]
 intervals=0;tet_count=0;null_tets=0;counts=Counter();unknown=[];faces_read=0;null_faces=0
 def geometry(lo,hi):
  points=[];cache={};v=q.R(F(lo),F(hi))
  for i,p in enumerate(src['vertices']):
   r=binding.get(i)
   if r:
    t=q.R(u) if r['variable']=='u' else v;points.append([q.R(F(r['x_coefficient']))*t,q.R(F(r['y_coefficient']))*t,q.R(F(r['z_exact']))])
   else:points.append([q.R(F(x)) for x in p])
  def cell(cid):
   if cid not in cache:
    polys=[[q.g.vsub(points[i],anchors[cid]) for i in face] for face in cells[cid]]
    try:
     centre,vol,geo=q.h.moments(polys);assert vol.a>0;cache[cid]=(q.g.vadd(centre,anchors[cid]),[q.g.vadd(cf,anchors[cid]) for cf,area in geo])
    except ZeroDivisionError:cache[cid]=None
   return cache[cid]
  return points,cell
 def verify_tet(data,points,owner=False,strict=False):
  nonlocal intervals,tet_count,null_tets
  tet_count+=1;ind,branch=q.quality(points)
  if data[1] is None:
   assert data[0]=='unknown';null_tets+=1;return 'unknown'
  assert branch==data[0] and ind is not None and len(data[1])==8
  for j,item in enumerate(ind):
   a,b=map(lambda x:F(x,1<<160),data[1][2*j:2*j+2]);assert a<=item.a<=item.b<=b;intervals+=1
  claim=status(data,owner,strict);a,b=ind[-1].a,ind[-1].b
  independent=q.classify((-b,-a) if owner else (a,b),strict)
  if claim!='unknown':assert claim==independent
  return claim
 with gzip.open(W/'face-tets-bounds.jsonl.gz','rt') as stream:
  domains=[('envelope',*hull)]+[(b['parent_leaf'],b['lower'],b['upper']) for b in boxes]
  for dom,lo,hi in domains:
   ranks=range(18560) if dom=='envelope' else unknown
   if not ranks:continue
   points,cell=geometry(lo,hi)
   for rank in ranks:
    row=json.loads(next(stream));assert row[:2]==[dom,rank];fans,bases,claim=row[2:];inc=registry[keys[rank]];(cid,j)=inc[0];own=cell(cid);nei=cell(inc[1][0]) if len(inc)==2 else None
    faces_read+=1;counts[str(dom)+':'+claim]+=1
    if fans is None:
     assert bases is None and claim=='unknown';null_faces+=1
    else:
     assert own is not None and (len(inc)==1 or nei is not None)
     face=cells[cid][j];pts=[points[i] for i in face];cf=own[1][j];centres=[own[0]]+([nei[0]] if nei is not None else []);n=len(pts)
     assert len(fans)==n*len(centres);states=[]
     for index,(side,edge,data) in enumerate(fans):
      assert (side,edge)==divmod(index,n);states.append(verify_tet(data,[pts[edge],pts[(edge+1)%n],cf,centres[side]],side==0))
     base_states=[];assert 1<=len(bases)<=n
     for bi,(base,records,bs) in enumerate(bases):
      assert base==bi and len(records)==(n-2)*len(centres);ss=[]
      for ix,(side,offset,data) in enumerate(records):
       s,o=divmod(ix,n-2);assert side==s and offset==o+1
       a,b=pts[(base+offset)%n],pts[(base+offset+1)%n]
       if side:a,b=b,a
       ss.append(verify_tet(data,[centres[side],pts[base],a,b],strict=True))
      assert bs==conjunction(ss);base_states.append(bs)
      if bi<len(bases)-1:assert bs!='positive'
     assert base_states[-1]=='positive' or len(bases)==n
     assert claim==conjunction([conjunction(states),disjunction(base_states)])
    if dom=='envelope' and claim=='unknown':unknown.append(rank)
   print(json.dumps({'domain':dom,'face_records':faces_read,'intervals':intervals,'elapsed_s':time.monotonic()-start}),flush=True)
  assert stream.readline()==''
 assert unknown==receipt['envelope_unknown_ranks'] and dict(counts)==receipt['counts'] and faces_read==receipt['face_records'] and tet_count==receipt['tet_records'] and null_faces==receipt['null_face_records']
 out={'source_sha256':sha(Path(__file__)),'quality_sha256':sha(W/'quality_independent_v2.py'),'primary_readback_sha256':sha(W/'readback.json'),'face_records':faces_read,'tet_records':tet_count,'intervals_included':intervals,'null_tets_without_numeric_inclusion_claim':null_tets,'null_faces_without_numeric_inclusion_claim':null_faces,'all_claimed_signs_confirmed':True,'all_finite_intervals_included':True,'internal_faces':13696,'walls':4864,'internal_mrf':384,'native_admission':False,'elapsed_s':time.monotonic()-start}
 with (W/'independent-readback.json').open('x') as f:f.write(json.dumps(out,indent=2)+'\n')
 print(json.dumps(out),flush=True)
if __name__=='__main__':main()
