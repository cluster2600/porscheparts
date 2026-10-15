"""Exact parametric incidence and planar cap coverage; no volume embedding claim."""
import hashlib,importlib.util,json,subprocess,time
from pathlib import Path
from fractions import Fraction as F
from collections import Counter,defaultdict
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def load(name,path,digest):
 assert sha(path)==digest
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
p=load('pinned_polynomials',Path('work/bionic-gram-interval-bounds-20261013/polynomials.py'),'f4122e6b4051c7e6b3aeaa464b04f8fdbc9f395a9f8a42bf831265f6e0ea00e0')
def canonical(f):return min(tuple(f[i:]+f[:i]) for i in range(len(f)))
def reduced(f):
 out=[]
 for i in f:
  if not out or i!=out[-1]:out.append(i)
 if out[-1]==out[0]:out.pop()
 return out

def main():
 w=Path(__file__).parent;start=time.monotonic();base='740cdf56a8fdc2b167d942759dc9d594d1b435d9';e='twins/bionic-turbo-f1/evidence/airflow-angular-independent-bounds-20261013/'
 deps=json.loads(subprocess.check_output(['git','show',base+':'+e+'dependencies.json']))['manifests'];receipt=json.loads(subprocess.check_output(['git','show',base+':'+e+'archive-receipt.json']));deps['work/bionic-airflow-delivery-20261013-angular-independent-bounds/file-manifest.json']=receipt['manifest_sha256'];entries=0
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
 faces=[];registry=defaultdict(list);neighbours=defaultdict(set)
 for c,block in enumerate(s['blocks']):
  n=4 if s['stages'][c]=='buffer' else 3;lo=block[:n];hi=block[4:4+n];fs=[lo[::-1],hi]+[[lo[i],lo[(i+1)%n],hi[(i+1)%n],hi[i]] for i in range(n)];edges=Counter()
  for f in fs:
   assert len(f)==len(set(f))
   for x,y in zip(f,f[1:]+f[:1]):edges[x,y]+=1
   registry[tuple(sorted(f))].append((c,f))
  assert all(v==1 and edges[y,x]==1 for (x,y),v in edges.items())
  assert len(set(block))-len(edges)//2+len(fs)==2
  faces.append(fs)
 boundary=[];shared=0
 for occurrences in registry.values():
  assert len(occurrences) in (1,2)
  if len(occurrences)==1:boundary.append(occurrences[0][1])
  else:
   (c,f),(d,g)=occurrences;assert canonical(f)==canonical(g[::-1]);shared+=1;neighbours[c].add(d);neighbours[d].add(c)
 assert shared==13696 and len(boundary)==4864
 assert Counter(canonical(f) for f in boundary)==Counter(canonical(reduced(f)) for f in s['walls'])
 reached={0};todo=[0]
 while todo:
  c=todo.pop()
  for d in neighbours[c]-reached:reached.add(d);todo.append(d)
 assert len(reached)==len(faces)==6144
 bedges=Counter();links=defaultdict(lambda:defaultdict(list))
 for f in boundary:
  for j,x in enumerate(f):
   prev,nxt=f[j-1],f[(j+1)%len(f)];bedges[x,nxt]+=1;links[x][prev].append(nxt);links[x][nxt].append(prev)
 assert all(count==1 and bedges[y,x]==1 for (x,y),count in bedges.items())
 for vertex,graph in links.items():
  assert all(len(v)==2 for v in graph.values());seen={next(iter(graph))};todo=list(seen)
  while todo:
   x=todo.pop()
   for y in graph[x]:
    if y not in seen:seen.add(y);todo.append(y)
  assert seen==set(graph)
 caps={};lateral=[]
 zlo,zhi=map(F,(s['stations_m'][0],s['stations_m'][-1]))
 for f in boundary:
  z={points[i][2] for i in f}
  if z=={(zlo,)}:caps.setdefault('lower',[]).append(f[::-1])
  elif z=={(zhi,)}:caps.setdefault('upper',[]).append(f)
  else:lateral.append(f)
 assert len(lateral)==2304 and all(len(poly)==1 for f in lateral for i in f for poly in points[i])
 assert all(len(poly)==1 for f in s['mrf_faces'] for i in f for poly in points[i])
 cross2=lambda x,y:p.sub(p.mul(x[0],y[1]),p.mul(x[1],y[0]))
 minus=lambda x,y:[p.sub(x[i],y[i]) for i in range(2)]
 allmodels=[];capreports={}
 for side,cap in caps.items():
  edge=Counter();models=[];total=(F(0),)
  for f in cap:
   assert len(f) in (3,4)
   for x,y in zip(f,f[1:]+f[:1]):edge[x,y]+=1
   xy=[points[i][:2] for i in f];centre=[p.times(p.summ(q[j] for q in xy),F(1,len(f))) for j in range(2)];tests=[]
   for i,q in enumerate(xy):
    nxt=xy[(i+1)%len(f)];direction=minus(nxt,q)
    for j,v in enumerate(xy):
     if j not in (i,(i+1)%len(f)):
      poly=cross2(direction,minus(v,q));coef=p.bernstein(poly,a,b);assert min(coef)>0;tests.append(dict(edge=i,vertex=j,polynomial=p.serialize(poly),bounds=[str(min(coef)),str(max(coef))]))
   fans=[]
   for q,nxt in zip(xy,xy[1:]+xy[:1]):
    poly=cross2(minus(q,centre),minus(nxt,centre));coef=p.bernstein(poly,a,b);assert min(coef)>0;fans.append(dict(polynomial=p.serialize(poly),bounds=[str(min(coef)),str(max(coef))]));total=p.add(total,p.times(poly,F(1,2)))
   models.append(dict(face=f,halfplanes=tests,fan_triangles=fans))
  net={e:n-edge[e[::-1]] for e,n in edge.items() if n-edge[e[::-1]]>0};assert all(n==1 for n in net.values())
  outgoing={};incoming=Counter()
  for x,y in net:assert x not in outgoing;outgoing[x]=y;incoming[y]+=1
  assert set(outgoing)==set(incoming) and set(incoming.values())=={1}
  remaining=set(outgoing);loops=[]
  while remaining:
   first=min(remaining);loop=[];x=first
   while not loop or x!=first:assert x in remaining;remaining.remove(x);loop.append(x);x=outgoing[x]
   loops.append(loop)
  assert len(loops)==2 and all(len(q)==256 for q in loops)
  assert all(len(poly)==1 for loop in loops for i in loop for poly in points[i])
  area=lambda loop:sum((points[x][0][0]*points[y][1][0]-points[x][1][0]*points[y][0][0] for x,y in zip(loop,loop[1:]+loop[:1])),F(0))/2
  outer=next(q for q in loops if area(q)>0);inner=next(q for q in loops if area(q)<0);inside=inner[::-1]
  orient=lambda x,y,z:(points[y][0][0]-points[x][0][0])*(points[z][1][0]-points[x][1][0])-(points[y][1][0]-points[x][1][0])*(points[z][0][0]-points[x][0][0])
  convex=[]
  for loop in (outer,inside):
   vals=[orient(x,y,z) for x,y in zip(loop,loop[1:]+loop[:1]) for z in loop if z not in (x,y)];assert min(vals)>0;convex.append(str(min(vals)))
  inclusion=[orient(x,y,z) for x,y in zip(outer,outer[1:]+outer[:1]) for z in inner];assert min(inclusion)>0
  expected=area(outer)+area(inner);assert total==(expected,)
  capreports[side]=dict(faces=len(cap),triangles=sum(len(x['fan_triangles']) for x in models),outer_loop=outer,inner_loop=inner,loop_convexity_minimum=convex,strict_inclusion_minimum=str(min(inclusion)),constant_area=str(expected),total_area_polynomial=p.serialize(total),minimum_triangle_double_area_bound=str(min(F(t['bounds'][0]) for m in models for t in m['fan_triangles'])))
  allmodels.append(dict(side=side,faces=models));print(json.dumps(dict(side=side,faces=len(cap),triangles=capreports[side]['triangles'])),flush=True)
 model=dict(domain_v=domain,normalized_t=[str(a),str(b)],parameter='v = u + (q_ext-u)*t; u fixed to source',caps=allmodels)
 (w/'models.json').write_text(json.dumps(model,separators=(',',':'))+'\n')
 out=dict(source_sha256=sha(Path(__file__)),preflight_sha256=sha(w/'preflight.md'),proof_sha256=sha(w/'proof.md'),dependencies_sha256=sha(w/'dependencies.json'),models_sha256=sha(w/'models.json'),domain_v=domain,source_boxes=153,cells=6144,internal_faces=shared,boundary_faces=len(boundary),boundary_vertices=len(links),boundary_edges=len(bedges)//2,boundary_euler_characteristic=len(links)-len(bedges)//2+len(boundary),boundary_vertex_links_single_cycles=True,cell_edge_chains_cancel=True,cell_face_graph_connected=True,shared_parametric_faces_exact=True,constant_lateral_faces=len(lateral),constant_mrf_faces=len(s['mrf_faces']),cap_reports=capreports,cap_triangle_coverage_proved=True,volume_cell_nonintersection_proved=False,geometric_embedding_3d_proved=False,native_executed=False,new_ratio_point=False,solution_accepted=False,elapsed_s=time.monotonic()-start)
 (w/'readback.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='cap_reports'}))
if __name__=='__main__':main()
