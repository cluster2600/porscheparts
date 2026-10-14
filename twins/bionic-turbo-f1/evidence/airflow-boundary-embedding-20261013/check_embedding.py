"""Exact lateral triangle intersections and boundary compatibility."""
import gzip,hashlib,importlib.util,json,subprocess,time
from pathlib import Path
from fractions import Fraction as F
from collections import Counter,defaultdict
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def load(name,path,digest):
 assert sha(path)==digest
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def canonical(f):return min(tuple(f[i:]+f[:i]) for i in range(len(f)))
def reduced(f):
 out=[]
 for i in f:
  if not out or i!=out[-1]:out.append(i)
 if out[-1]==out[0]:out.pop()
 return out

def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def dot(a,b):return sum((x*y for x,y in zip(a,b)),F(0))
def normal(t):return cross(sub(t[1],t[0]),sub(t[2],t[0]))
def orient(a,b,c,k):
 axes=[i for i in range(3) if i!=k];i,j=axes
 return (b[i]-a[i])*(c[j]-a[j])-(b[j]-a[j])*(c[i]-a[i])
def lerp(a,b,t):return tuple(x+t*(y-x) for x,y in zip(a,b))
def section(t,n,p):
 d=[dot(n,sub(x,p)) for x in t];points={x for x,v in zip(t,d) if not v}
 for i in range(3):
  j=(i+1)%3
  if d[i]*d[j]<0:points.add(lerp(t[i],t[j],d[i]/(d[i]-d[j])))
 return list(points)
def intersect(A,B):
 na,nb=normal(A),normal(B);direction=cross(na,nb)
 if any(direction):
  aa=section(A,nb,B[0]);bb=section(B,na,A[0])
  if not aa or not bb:return []
  k=max(range(3),key=lambda i:abs(direction[i]));aa.sort(key=lambda x:x[k]);bb.sort(key=lambda x:x[k]);lo=max(aa[0][k],bb[0][k]);hi=min(aa[-1][k],bb[-1][k])
  if lo>hi:return []
  if len(aa)==1:return aa
  return list({lerp(aa[0],aa[-1],(x-aa[0][k])/(aa[-1][k]-aa[0][k])) for x in (lo,hi)})
 if dot(na,sub(B[0],A[0])):return []
 k=max(range(3),key=lambda i:abs(nb[i]));sg=1 if orient(*B,k)>0 else -1;poly=list(A)
 for i in range(3):
  edge=(B[i],B[(i+1)%3]);result=[]
  if not poly:break
  for x,y in zip(poly,poly[1:]+poly[:1]):
   dx=sg*orient(*edge,x,k);dy=sg*orient(*edge,y,k)
   if dx>=0:result.append(x)
   if (dx>=0)!=(dy>=0):result.append(lerp(x,y,dx/(dx-dy)))
  poly=list(dict.fromkeys(result))
 return poly
def allowed(found,common):
 if not common:return not found
 if len(common)==1:return bool(found) and all(x==common[0] for x in found)
 assert len(common)==2
 d=sub(common[1],common[0]);k=next(i for i,v in enumerate(d) if v)
 return bool(found) and all(not any(cross(sub(x,common[0]),d)) and 0<=(x[k]-common[0][k])/d[k]<=1 for x in found)
def references():
 v=lambda *xs:tuple(tuple(F(x) for x in row) for row in xs)
 A=v((0,0,0),(2,0,0),(0,2,0));examples=[(v((3,0,0),(4,0,0),(3,1,0)),0),(v((2,0,0),(3,0,0),(2,1,0)),1),(v((0,0,0),(2,0,0),(0,-2,0)),2),(v((0,0,0),(1,0,0),(0,1,0)),3),(v((0,0,1),(2,0,1),(0,2,1)),0),(v((1,0,-1),(1,0,1),(1,2,0)),2),(v((0,0,0),(0,0,1),(-1,0,1)),1)]
 count=0
 for scale in (F(1),F(1,1000),F(1,1000000)):
  scale_t=lambda t:tuple(tuple(x*scale for x in p) for p in t)
  for B,n in examples:
   ab=intersect(scale_t(A),scale_t(B));ba=intersect(scale_t(B),scale_t(A));assert len(set(ab))==n and set(ab)==set(ba);count+=1
 return count

def main():
 w=Path(__file__).parent;start=time.monotonic();base='c11b7bd5ae58049ccd4901627146c63666a50401';e='twins/bionic-turbo-f1/evidence/airflow-volume-representation-20261013/'
 deps=json.loads(subprocess.check_output(['git','show',base+':'+e+'dependencies.json']))['manifests'];receipt=json.loads(subprocess.check_output(['git','show',base+':'+e+'archive-receipt.json']));deps['work/bionic-airflow-delivery-20261013-volume-representation/file-manifest.json']=receipt['manifest_sha256'];entries=0
 for name,digest in deps.items():
  mf=Path(name);assert sha(mf)==digest
  for r in json.loads(mf.read_text())['files']:
   f=Path('work')/r['path'];assert f.stat().st_size==r['bytes'] and sha(f)==r['sha256'];entries+=1
 (w/'dependencies.json').write_text(json.dumps(dict(anchor_commit=base,manifests=deps,payload_entries_verified=entries),indent=2)+'\n')
 boxes=json.loads(Path('work/bionic-angular-independent-bounds-20261013/boxes.json').read_text());assert len(boxes)==153 and all(F(a['upper'])==F(b['lower']) for a,b in zip(boxes,boxes[1:]));domain=[boxes[0]['lower'],boxes[-1]['upper']]
 s=json.loads(Path('work/bionic-buffered-transition-20261013/construction.json').read_text());sys=json.loads(Path('work/bionic-joint-constraints-20261013/system.json').read_text());u=F(sys['archived_regression_point']['u']);end=F(s['radial_ratios'][-1]);a,b=[(F(x)-u)/(end-u) for x in domain];assert 0<a<b<1
 bind={x['point']:x for x in sys['coordinate_bindings']};points=[]
 for i,xyz in enumerate(s['vertices']):
  r=bind.get(i)
  if r and r['variable']=='v':points.append([(F(r[k])*u,F(r[k])*(end-u)) for k in ('x_coefficient','y_coefficient')]+[(F(r['z_exact']),)])
  else:
   q=[(F(x),) for x in xyz]
   if r:assert [F(r['x_coefficient'])*u,F(r['y_coefficient'])*u,F(r['z_exact'])]==[F(x) for x in xyz]
   points.append(q)
 refs=references();reg=defaultdict(list)
 for cid,block in enumerate(s['blocks']):
  n=4 if s['stages'][cid]=='buffer' else 3;lo=block[:n];hi=block[4:4+n]
  for f in [lo[::-1],hi]+[[lo[i],lo[(i+1)%n],hi[(i+1)%n],hi[i]] for i in range(n)]:reg[tuple(sorted(f))].append(f)
 boundary=[v[0] for v in reg.values() if len(v)==1];assert len(boundary)==4864
 zlo,zhi=F(s['stations_m'][0]),F(s['stations_m'][-1]);vertices={};triangles=[];alltris=[];caps={'lower':[],'upper':[]};lateral=[]
 for f in boundary:
  labels=['v:'+str(i) for i in f];mid='f:'+','.join(map(str,sorted(f)));fan=[(mid,labels[k],labels[(k+1)%len(f)]) for k in range(len(f))];alltris.extend(fan)
  side='lower' if all(points[i][2]==(zlo,) for i in f) else 'upper' if all(points[i][2]==(zhi,) for i in f) else None
  if side:caps[side].append(f);continue
  assert all(len(poly)==1 for i in f for poly in points[i]);lateral.append(f)
  for label,i in zip(labels,f):vertices[label]=tuple(x[0] for x in points[i])
  vertices[mid]=tuple(sum((vertices[label][k] for label in labels),F(0))/len(f) for k in range(3));triangles.extend(fan)
 assert len(lateral)==2304
 edges=defaultdict(list);links=defaultdict(list)
 for ti,t in enumerate(alltris):
  for k,x in enumerate(t):
   y=t[(k+1)%3];edges[tuple(sorted((x,y)))].append((ti,x,y));links[x].append((t[k-1],y))
 graph=defaultdict(set)
 for ev in edges.values():assert len(ev)==2 and ev[0][1:]==ev[1][1:][::-1];graph[ev[0][0]].add(ev[1][0]);graph[ev[1][0]].add(ev[0][0])
 visited=set();todo=[0]
 while todo:
  x=todo.pop()
  if x not in visited:visited.add(x);todo.extend(graph[x]-visited)
 assert len(visited)==len(alltris)
 for arcs in links.values():
  g=defaultdict(set)
  for x,y in arcs:g[x].add(y);g[y].add(x)
  assert all(len(v)==2 for v in g.values());seen=set();todo=[next(iter(g))]
  while todo:
   x=todo.pop()
   if x not in seen:seen.add(x);todo.extend(g[x]-seen)
  assert seen==set(g)
 cap_receipt=json.loads(Path('work/bionic-parametric-boundary-20261013/readback.json').read_text());end_edges={side:set() for side in caps}
 for t in triangles:
  T=[vertices[k] for k in t];assert any(normal(T)) and all(zlo<=x[2]<=zhi for x in T)
  for side,z in [('lower',zlo),('upper',zhi)]:
   ids=[k for k in t if vertices[k][2]==z];assert len(ids)<3
   if len(ids)==2:end_edges[side].add(tuple(sorted(ids)))
 for side,report in cap_receipt['cap_reports'].items():
  wanted={tuple(sorted(('v:'+str(x),'v:'+str(y)))) for loop in (report['outer_loop'],report['inner_loop']) for x,y in zip(loop,loop[1:]+loop[:1])};assert end_edges[side]==wanted
  for t in triangles:
   for label in t:
    if vertices[label][2]==(zlo if side=='lower' else zhi):assert any(label in edge for edge in wanted)
 coords=[[vertices[x] for x in t] for t in triangles];boxes=[[(min(x[k] for x in T),max(x[k] for x in T)) for k in range(3)] for T in coords];order=sorted(range(len(coords)),key=lambda i:(boxes[i][0][0],i));active=[];counts=Counter();pairs=0
 with gzip.open(w/'pairs.jsonl.gz','wt',compresslevel=3) as output:
  for j in order:
   active=[i for i in active if boxes[i][0][1]>=boxes[j][0][0]]
   for i in active:
    if any(boxes[i][k][1]<boxes[j][k][0] or boxes[j][k][1]<boxes[i][k][0] for k in (1,2)):continue
    common=sorted(set(triangles[i])&set(triangles[j]));assert len(common)<=2
    found=intersect(coords[i],coords[j]);ok=allowed(found,[vertices[x] for x in common]);kind=['empty','vertex','edge'][len(common)];pairs+=1;counts[kind]+=1
    row=dict(pair=[i,j],common=common,intersection=[list(map(str,x)) for x in sorted(found)],allowed=ok);output.write(json.dumps(row,separators=(',',':'))+'\n')
    if not ok:raise AssertionError(row)
   active.append(j)
   if j%1024==0:print(json.dumps(dict(triangle=j,pairs=pairs)),flush=True)
 geometry=dict(vertices={k:list(map(str,v)) for k,v in vertices.items()},triangles=triangles)
 (w/'triangles.json').write_text(json.dumps(geometry,separators=(',',':'))+'\n')
 result=dict(source_sha256=sha(Path(__file__)),preflight_sha256=sha(w/'preflight.md'),dependencies_sha256=sha(w/'dependencies.json'),triangles_sha256=sha(w/'triangles.json'),pairs_sha256=sha(w/'pairs.jsonl.gz'),domain_v=domain,source_boxes=153,lateral_faces=len(lateral),lateral_triangles=len(triangles),total_pairs=len(triangles)*(len(triangles)-1)//2,exact_pairs_checked=pairs,strict_bbox_separations=len(triangles)*(len(triangles)-1)//2-pairs,intersection_types=counts,analytic_references=refs,cap_join_edges={s:len(x) for s,x in end_edges.items()},boundary_triangles=len(alltris),boundary_connected=True,boundary_vertex_links=len(links),all_lateral_intersections_equal_common_simplex=True,cap_plane_contacts_only_declared_rims=True,global_volume_nonoverlap_not_inferred_by_this_program=True,native_executed=False,new_ratio_point=False,elapsed_s=time.monotonic()-start)
 (w/'readback.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
