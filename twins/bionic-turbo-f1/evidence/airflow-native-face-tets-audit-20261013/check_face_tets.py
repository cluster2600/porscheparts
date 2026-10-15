"""New native mathematical face-tet application on inherited closed boxes."""
import gzip,hashlib,json,time
from pathlib import Path
from collections import defaultdict,Counter
from fractions import Fraction as F
import quality_primary as q
W=Path(__file__).parent

def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def canonical(f):return list(min(tuple(f[i:]+f[:i]) for i in range(len(f))))
def all_of(states):return 'refused' if 'refused' in states else 'positive' if all(s=='positive' for s in states) else 'unknown'
def any_of(states):return 'positive' if 'positive' in states else 'refused' if all(s=='refused' for s in states) else 'unknown'
def packed(points):
 values,branch=q.quality(points)
 return [branch,None if values is None else [i for v in values for i in (v.lo,v.hi)]]
def tet_status(data,owner=False,strict=False):
 if data[1] is None:return 'unknown'
 a,b=(F(v,q.Q) for v in data[1][-2:]);return q.classify((-b,-a) if owner else (a,b),strict)
def main():
 started=time.monotonic();frozen=json.loads((W/'before-application.json').read_text())
 for name,digest in frozen['files'].items():assert sha(Path(name))==digest
 audit=json.loads((W/'source-audit.json').read_text())
 for name,digest in audit['manifests'].items():
  p=Path(name);assert sha(p)==digest
  for r in json.loads(p.read_text())['files']:
   path=Path('work')/r['path'];assert sha(path)==r['sha256'] and path.stat().st_size==r['bytes']
 src=json.loads(Path('work/bionic-buffered-transition-20261013/construction.json').read_text());sy=json.loads(Path('work/bionic-joint-constraints-20261013/system.json').read_text());bindings={r['point']:r for r in sy['coordinate_bindings']};u=F(sy['archived_regression_point']['u']);boxes=json.loads(Path('work/bionic-angular-independent-bounds-20261013/certificate-readback.json').read_text())['box_results'];domain=[boxes[0]['lower'],boxes[-1]['upper']]
 fs=[];reg=defaultdict(list)
 for cid,block in enumerate(src['blocks']):
  n=4 if src['stages'][cid]=='buffer' else 3;lo,hi=block[:n],block[4:4+n];faces=[canonical(f) for f in [lo[::-1],hi]+[[lo[j],lo[(j+1)%n],hi[(j+1)%n],hi[j]] for j in range(n)]];fs.append(faces)
  for j,f in enumerate(faces):reg[tuple(sorted(f))].append((cid,j))
 keys=sorted(reg);assert len(keys)==18560
 assert {key for key,inc in reg.items() if len(inc)==1}=={tuple(sorted(set(f))) for f in src['walls']}
 anchors=[[q.I(F(x)) for x in src['vertices'][block[0]]] for block in src['blocks']]
 def evaluator(lo,hi):
  v=q.interval(F(lo),F(hi));points=[];cache={}
  for i,p in enumerate(src['vertices']):
   r=bindings.get(i)
   if r:
    t=q.I(u) if r['variable']=='u' else v;points.append([q.I(F(r['x_coefficient']))*t,q.I(F(r['y_coefficient']))*t,q.I(F(r['z_exact']))])
   else:points.append([q.I(F(x)) for x in p])
  def cell(cid):
   if cid not in cache:
    try:
     geo=[q.h.face([q.b.minus(points[i],anchors[cid]) for i in f]) for f in fs[cid]];centre,vol=q.h.cell(geo)
     assert vol.lo>0;cache[cid]=(q.b.plus(centre,anchors[cid]),[q.b.plus(cf,anchors[cid]) for cf,area in geo])
    except ZeroDivisionError:cache[cid]=None
   return cache[cid]
  def evaluate(rank):
   inc=reg[keys[rank]];(a,j)=inc[0];own=cell(a);nei=cell(inc[1][0]) if len(inc)==2 else None
   if own is None or (len(inc)==2 and nei is None):return None,None,'unknown'
   face=fs[a][j];pts=[points[i] for i in face];cf=own[1][j];centres=[own[0]]+([nei[0]] if nei else []);fans=[];bases=[]
   for side,centre in enumerate(centres):
    for edge,p in enumerate(pts):fans.append([side,edge,packed([p,pts[(edge+1)%len(pts)],cf,centre])])
   fan_status=all_of([tet_status(data,owner=(side==0)) for side,edge,data in fans])
   for base in range(len(pts)):
    records=[]
    for side,centre in enumerate(centres):
     for offset in range(1,len(pts)-1):
      a,b=pts[(base+offset)%len(pts)],pts[(base+offset+1)%len(pts)]
      if side:a,b=b,a
      records.append([side,offset,packed([centre,pts[base],a,b])])
    status=all_of([tet_status(data,strict=True) for side,offset,data in records]);bases.append([base,records,status])
    if status=='positive':break
   base_status=any_of([r[2] for r in bases]);return fans,bases,all_of([fan_status,base_status])
  return evaluate
 counts=Counter();unknown=[];records=0;tets=0;null_faces=0
 with gzip.open(W/'face-tets-bounds.jsonl.gz','xt',compresslevel=3) as stream:
  def emit(dom,rank,result):
   nonlocal records,tets,null_faces
   fans,bases,status=result;stream.write(json.dumps([dom,rank,fans,bases,status],separators=(',',':'))+'\n');records+=1;counts[str(dom)+':'+status]+=1
   if fans is None:null_faces+=1
   else:tets+=len(fans)+sum(len(b[1]) for b in bases)
  calc=evaluator(*domain)
  for rank in range(18560):
   result=calc(rank);emit('envelope',rank,result)
   if result[-1]=='unknown':unknown.append(rank)
   if rank%1024==0:print(json.dumps({'envelope_rank':rank,'tet_records':tets,'elapsed_s':time.monotonic()-started}),flush=True)
  print(json.dumps({'envelope_counts':dict(counts),'local_faces':len(unknown)}),flush=True)
  for box in boxes:
   if not unknown:break
   calc=evaluator(box['lower'],box['upper'])
   for rank in unknown:emit(box['parent_leaf'],rank,calc(rank))
   print(json.dumps({'box':box['parent_leaf'],'face_records':records,'tet_records':tets,'elapsed_s':time.monotonic()-started}),flush=True)
 report={'source_sha256':sha(Path(__file__)),'quality_sha256':sha(W/'quality_primary.py'),'bounds_sha256':sha(W/'face-tets-bounds.jsonl.gz'),'domain_v':domain,'fractional_bits':160,'source_boxes':153,'faces':18560,'counts':dict(counts),'envelope_unknown_ranks':unknown,'face_records':records,'tet_records':tets,'null_face_records':null_faces,'threshold_interval':list(map(str,q.TOL)),'native_first_passing_base_claimed':False,'native_admission':False,'elapsed_s':time.monotonic()-started}
 with (W/'readback.json').open('x') as stream:stream.write(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k not in ('counts','envelope_unknown_ranks')}),flush=True)
if __name__=='__main__':main()
