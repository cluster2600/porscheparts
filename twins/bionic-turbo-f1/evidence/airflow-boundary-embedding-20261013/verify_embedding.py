"""Independent exact barycentric/edge intersection verification; no primary import."""
import gzip,hashlib,itertools,json,time
from pathlib import Path
from fractions import Fraction as F
from collections import defaultdict,Counter
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def difference(x,y):return tuple(a-b for a,b in zip(x,y))
def determinant(a,b,c):
 return sum(((-1 if ((p[0]>p[1])+(p[0]>p[2])+(p[1]>p[2]))%2 else 1)*a[p[0]]*b[p[1]]*c[p[2]] for p in itertools.permutations(range(3))),F(0))
def plane(T,x):return determinant(difference(T[1],T[0]),difference(T[2],T[0]),difference(x,T[0]))
def project_axes(T):
 a,b=difference(T[1],T[0]),difference(T[2],T[0])
 return next((i,j) for i,j in itertools.combinations(range(3),2) if a[i]*b[j]-a[j]*b[i])
def inside(x,T):
 if plane(T,x):return False
 i,j=project_axes(T);u,v,w=difference(T[1],T[0]),difference(T[2],T[0]),difference(x,T[0]);den=u[i]*v[j]-u[j]*v[i]
 b=(w[i]*v[j]-w[j]*v[i])/den;c=(u[i]*w[j]-u[j]*w[i])/den
 return b>=0 and c>=0 and b+c<=1

def intersection(A,B):
 pts={x for x in A if inside(x,B)}|{x for x in B if inside(x,A)}
 for T,U in ((A,B),(B,A)):
  e1=tuple(-x for x in difference(U[1],U[0]));e2=tuple(-x for x in difference(U[2],U[0]))
  for x,y in zip(T,T[1:]+T[:1]):
   direction=difference(y,x);rhs=difference(U[0],x);den=determinant(direction,e1,e2)
   if not den:continue
   t=determinant(rhs,e1,e2)/den;b=determinant(direction,rhs,e2)/den;c=determinant(direction,e1,rhs)/den
   if 0<=t<=1 and b>=0 and c>=0 and b+c<=1:pts.add(tuple(xx+t*dd for xx,dd in zip(x,direction)))
 if all(plane(A,x)==0 for x in B):
  i,j=project_axes(A)
  for x,y in zip(A,A[1:]+A[:1]):
   d=difference(y,x)
   for u,v in zip(B,B[1:]+B[:1]):
    e=difference(v,u);w=difference(u,x);den=d[i]*e[j]-d[j]*e[i]
    if not den:continue
    t=(w[i]*e[j]-w[j]*e[i])/den;s=(w[i]*d[j]-w[j]*d[i])/den
    if 0<=t<=1 and 0<=s<=1:pts.add(tuple(xx+t*dd for xx,dd in zip(x,d)))
 return pts

def references():
 A=((0,0,0),(2,0,0),(0,2,0));examples=[(((3,0,0),(4,0,0),(3,1,0)),set()),(((2,0,0),(3,0,0),(2,1,0)),{(2,0,0)}),(((0,0,0),(2,0,0),(0,-2,0)),{(0,0,0),(2,0,0)}),(((0,0,0),(1,0,0),(0,1,0)),{(0,0,0),(1,0,0),(0,1,0)}),(((0,0,1),(2,0,1),(0,2,1)),set()),(((1,0,-1),(1,0,1),(1,2,0)),{(1,0,0),(1,1,0)}),(((0,0,0),(0,0,1),(-1,0,1)),{(0,0,0)})];n=0
 for scale in (F(1),F(1,1000),F(1,1000000)):
  cv=lambda rows:tuple(tuple(F(x)*scale for x in row) for row in rows)
  for B,expected in examples:assert intersection(cv(A),cv(B))==intersection(cv(B),cv(A))==set(cv(expected));n+=1
 return n

def main():
 start=time.monotonic();w=Path(__file__).parent;r=json.loads((w/'readback.json').read_text())
 for name,key in [('check_embedding.py','source_sha256'),('preflight.md','preflight_sha256'),('dependencies.json','dependencies_sha256'),('triangles.json','triangles_sha256'),('pairs.jsonl.gz','pairs_sha256')]:assert sha(w/name)==r[key]
 deps=json.loads((w/'dependencies.json').read_text())
 for name,digest in deps['manifests'].items():
  p=Path(name);assert sha(p)==digest
  for row in json.loads(p.read_text())['files']:
   f=Path('work')/row['path'];assert f.stat().st_size==row['bytes'] and sha(f)==row['sha256']
 refs=references();source=json.loads(Path('work/bionic-buffered-transition-20261013/construction.json').read_text());system=json.loads(Path('work/bionic-joint-constraints-20261013/system.json').read_text());bindings={x['point']:x for x in system['coordinate_bindings']};u=F(system['archived_regression_point']['u']);points=[tuple(F(v) for v in x) for x in source['vertices']]
 templates=((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7));reg=defaultdict(list)
 for block in source['blocks']:
  for temp in templates:
   f=[]
   for i in temp:
    if not f or f[-1]!=block[i]:f.append(block[i])
   if f[-1]==f[0]:f.pop()
   if len(f)>=3:reg[frozenset(f)].append(f)
 zlo,zhi=F(source['stations_m'][0]),F(source['stations_m'][-1]);tri=[];alltri=[];verts={};cap_edges={'lower':set(),'upper':set()};lateral_count=0
 for entries in reg.values():
  if len(entries)!=1:continue
  f=entries[0];labels=['v:'+str(i) for i in f];centre='f:'+','.join(map(str,sorted(f)));fan=[(centre,labels[k],labels[(k+1)%len(f)]) for k in range(len(f))];alltri.extend(fan)
  if all(points[i][2]==zlo for i in f) or all(points[i][2]==zhi for i in f):continue
  lateral_count+=1
  for i,label in zip(f,labels):
   assert i not in bindings or bindings[i]['variable']=='u'
   if i in bindings:
    v=bindings[i];assert points[i]==(F(v['x_coefficient'])*u,F(v['y_coefficient'])*u,F(v['z_exact']))
   verts[label]=points[i]
  verts[centre]=tuple(sum((points[i][k] for i in f),F(0))/len(f) for k in range(3));tri.extend(fan)
 geometry=json.loads((w/'triangles.json').read_text());assert geometry['vertices']=={k:list(map(str,v)) for k,v in verts.items()} and geometry['triangles']==[list(x) for x in tri]
 assert lateral_count==r['lateral_faces']==2304
 ed=defaultdict(list);link=defaultdict(list)
 for index,t in enumerate(alltri):
  for j,x in enumerate(t):ed[frozenset((x,t[(j+1)%3]))].append((index,x,t[(j+1)%3]));link[x].append((t[j-1],t[(j+1)%3]))
 adj=defaultdict(set)
 for entries in ed.values():assert len(entries)==2 and entries[0][1:]==entries[1][1:][::-1];i,j=entries[0][0],entries[1][0];adj[i].add(j);adj[j].add(i)
 def connected(g):
  seen=set();todo=[next(iter(g))]
  while todo:
   x=todo.pop()
   if x not in seen:seen.add(x);todo.extend(set(g[x])-seen)
  return seen==set(g)
 assert connected(adj) and len(adj)==len(alltri)==r['boundary_triangles']
 for arcs in link.values():
  graph=defaultdict(list)
  for x,y in arcs:graph[x].append(y);graph[y].append(x)
  assert all(len(v)==2 for v in graph.values()) and connected(graph)
 assert len(link)==r['boundary_vertex_links']
 cap=json.loads(Path('work/bionic-parametric-boundary-20261013/readback.json').read_text())
 for t in tri:
  assert all(zlo<=verts[k][2]<=zhi for k in t);project_axes([verts[k] for k in t])
  for side,z in [('lower',zlo),('upper',zhi)]:
   hit=[k for k in t if verts[k][2]==z];assert len(hit)<3
   if len(hit)==2:cap_edges[side].add(frozenset(hit))
 for side,report in cap['cap_reports'].items():
  expected={frozenset(('v:'+str(x),'v:'+str(y))) for loop in (report['outer_loop'],report['inner_loop']) for x,y in zip(loop,loop[1:]+loop[:1])};assert cap_edges[side]==expected
  rim=set().union(*expected);z=zlo if side=='lower' else zhi
  assert all(k in rim for t in tri for k in t if verts[k][2]==z)
 bounds=[[(min(verts[k][d] for k in t),max(verts[k][d] for k in t)) for d in range(3)] for t in tri];order=sorted(range(len(tri)),key=lambda k:(bounds[k][0][0],k));active=[];counts=Counter();checked=0
 with gzip.open(w/'pairs.jsonl.gz','rt') as stream:
  for j in order:
   active=[i for i in active if bounds[i][0][1]>=bounds[j][0][0]]
   for i in active:
    if any(max(bounds[i][d][0],bounds[j][d][0])>min(bounds[i][d][1],bounds[j][d][1]) for d in (1,2)):continue
    row=json.loads(next(stream));assert row['pair']==[i,j] and row['allowed']
    common=sorted(set(tri[i])&set(tri[j]));assert common==row['common'];actual=intersection(tuple(verts[k] for k in tri[i]),tuple(verts[k] for k in tri[j]));expected={verts[k] for k in common}
    assert actual==expected=={tuple(F(v) for v in x) for x in row['intersection']};checked+=1;counts[['empty','vertex','edge'][len(common)]]+=1
   active.append(j)
  assert next(stream,None) is None
 assert checked==r['exact_pairs_checked'] and dict(counts)==r['intersection_types']
 boxes=json.loads(Path('work/bionic-angular-independent-bounds-20261013/boxes.json').read_text());assert r['domain_v']==cap['domain_v']==[boxes[0]['lower'],boxes[-1]['upper']]
 result=dict(source_sha256=sha(Path(__file__)),primary_readback_sha256=sha(w/'readback.json'),triangles_sha256=sha(w/'triangles.json'),pairs_sha256=sha(w/'pairs.jsonl.gz'),analytic_references=refs,lateral_triangles=len(tri),exhaustive_pairs=len(tri)*(len(tri)-1)//2,exact_candidates_verified=checked,intersection_types=counts,all_intersections_equal_common_simplex=True,cap_contacts_verified=True,closed_connected_oriented_boundary_links_verified=len(link),domain_v=r['domain_v'],old_polynomial_runs_replayed=False,elapsed_s=time.monotonic()-start)
 (w/'independent-readback.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
