"""Independent reduced-hex and sparse-polynomial verification of every cap certificate."""
import hashlib,importlib.util,json,time
from pathlib import Path
from fractions import Fraction as F
from collections import Counter,defaultdict
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
p=Path('work/bionic-gram-interval-bounds-20261013/verify_models.py');assert sha(p)=='1a2c0167b9d76d6f515d20bca1d2f244d172aebdbf49887a8c36f603b891d97c'
spec=importlib.util.spec_from_file_location('pinned_sparse',p);q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
def cycle(face):return min(tuple(face[i:]+face[:i]) for i in range(len(face)))
def main():
 start=time.monotonic();w=Path(__file__).parent;r=json.loads((w/'readback.json').read_text());model=json.loads((w/'models.json').read_text())
 for name,key in [('check_boundary.py','source_sha256'),('preflight.md','preflight_sha256'),('proof.md','proof_sha256'),('models.json','models_sha256'),('dependencies.json','dependencies_sha256')]:assert sha(w/name)==r[key]
 for name,digest in json.loads((w/'dependencies.json').read_text())['manifests'].items():
  f=Path(name);assert sha(f)==digest
  for row in json.loads(f.read_text())['files']:
   payload=Path('work')/row['path'];assert payload.stat().st_size==row['bytes'] and sha(payload)==row['sha256']
 s=json.loads(Path('work/bionic-buffered-transition-20261013/construction.json').read_text());sy=json.loads(Path('work/bionic-joint-constraints-20261013/system.json').read_text());bindings={x['point']:x for x in sy['coordinate_bindings']}
 boxes=json.loads(Path('work/bionic-angular-independent-bounds-20261013/boxes.json').read_text());assert len(boxes)==153
 assert model['domain_v']==r['domain_v']==[boxes[0]['lower'],boxes[-1]['upper']]
 for left,right in zip(boxes,boxes[1:]):assert F(left['upper'])==F(right['lower'])
 u=F(sy['archived_regression_point']['u']);end=F(s['radial_ratios'][-1]);a,b=[(F(x)-u)/(end-u) for x in model['domain_v']];assert model['normalized_t']==[str(a),str(b)]
 points=[]
 for i,xyz in enumerate(s['vertices']):
  bind=bindings.get(i)
  if bind:
   scale={0:u,1:end-u} if bind['variable']=='v' else {0:u}
   xyzpoly=[q.times(scale,F(bind[k])) for k in ('x_coefficient','y_coefficient')]+[{0:F(bind['z_exact'])}]
   if bind['variable']=='u':assert xyzpoly==[{0:F(x)} if x else {} for x in xyz]
   points.append(xyzpoly)
  else:points.append([{0:F(x)} if x else {} for x in xyz])
 templates=((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7));reg=defaultdict(list)
 for c,block in enumerate(s['blocks']):
  edge=Counter();nfaces=0
  for temp in templates:
   face=[]
   for i in temp:
    if not face or face[-1]!=block[i]:face.append(block[i])
   if face[-1]==face[0]:face.pop()
   if len(face)<3:continue
   assert len(face)==len(set(face));nfaces+=1;reg[frozenset(face)].append((c,face))
   for x,y in zip(face,face[1:]+face[:1]):edge[x,y]+=1
  assert all(v==1 and edge[y,x]==1 for (x,y),v in edge.items());assert len(set(block))-len(edge)//2+nfaces==2
 graph=defaultdict(set);boundary=[]
 for entries in reg.values():
  if len(entries)==1:boundary.append(entries[0][1])
  else:
   assert len(entries)==2;(c,f),(d,g)=entries;assert cycle(f)==cycle(g[::-1]);graph[c].add(d);graph[d].add(c)
 reached=set();todo=[0]
 while todo:
  c=todo.pop()
  if c not in reached:reached.add(c);todo.extend(graph[c]-reached)
 assert len(reached)==6144 and len(boundary)==4864 and sum(len(x)==2 for x in reg.values())==13696
 def compact(face):
  f=[]
  for i in face:
   if not f or f[-1]!=i:f.append(i)
  if f[-1]==f[0]:f.pop()
  return f
 assert Counter(map(cycle,boundary))==Counter(cycle(compact(f)) for f in s['walls'])
 edges=Counter();links=defaultdict(list)
 for face in boundary:
  for j,i in enumerate(face):edges[i,face[(j+1)%len(face)]]+=1;links[i].append((face[j-1],face[(j+1)%len(face)]))
 assert all(n==1 and edges[y,x]==1 for (x,y),n in edges.items())
 for vertex,arcs in links.items():
  adj=defaultdict(list)
  for x,y in arcs:adj[x].append(y);adj[y].append(x)
  assert all(len(ns)==2 for ns in adj.values());visited=set();stack=[next(iter(adj))]
  while stack:
   v=stack.pop()
   if v not in visited:visited.add(v);stack.extend(set(adj[v])-visited)
  assert visited==set(adj)
 assert (len(links),len(edges)//2,len(links)-len(edges)//2+len(boundary))==(r['boundary_vertices'],r['boundary_edges'],0)
 fixed=lambda f:all(not(set(poly)-{0}) for i in f for poly in points[i])
 zlo,zhi=F(s['stations_m'][0]),F(s['stations_m'][-1]);caps={'lower':[],'upper':[]};lateral=[]
 for face in boundary:
  if all(points[i][2]=={0:zlo} for i in face):caps['lower'].append(face[::-1])
  elif all(points[i][2]=={0:zhi} for i in face):caps['upper'].append(face)
  else:lateral.append(face)
 assert len(lateral)==2304 and all(map(fixed,lateral));assert len(s['mrf_faces'])==384 and all(map(fixed,s['mrf_faces']))
 sub=lambda x,y:[q.difference(v,w) for v,w in zip(x,y)]
 determinant=lambda x,y:q.vector(x,y)[2]
 evaluated=0;triangles=0;summary={}
 def verify_poly(actual,entry):
  nonlocal evaluated
  assert actual==q.from_strings(entry['polynomial']);controls=q.restricted(actual,a,b);bounds=[min(controls),max(controls)];assert bounds==list(map(F,entry['bounds'])) and bounds[0]>0;evaluated+=1
 for part in model['caps']:
  side=part['side'];faces=caps[side];assert Counter(cycle(x['face']) for x in part['faces'])==Counter(map(cycle,faces));signed=Counter();total={}
  for m in part['faces']:
   face=m['face'];coords=[points[i] for i in face];mid=[q.times(q.total(x[k] for x in coords),F(1,len(coords))) for k in range(3)]
   expected=[(i,j) for i in range(len(coords)) for j in range(len(coords)) if j not in (i,(i+1)%len(coords))];assert [(x['edge'],x['vertex']) for x in m['halfplanes']]==expected
   for t in m['halfplanes']:
    i,j=t['edge'],t['vertex'];poly=determinant(sub(coords[(i+1)%len(coords)],coords[i]),sub(coords[j],coords[i]));verify_poly(poly,t)
   assert len(m['fan_triangles'])==len(face)
   for i,t in enumerate(m['fan_triangles']):
    poly=determinant(sub(coords[i],mid),sub(coords[(i+1)%len(coords)],mid));verify_poly(poly,t);total=q.total([total,q.times(poly,F(1,2))]);triangles+=1
   for x,y in zip(face,face[1:]+face[:1]):signed[min(x,y),max(x,y)]+=1 if x<y else -1
  residual={(x,y) if n>0 else (y,x) for (x,y),n in signed.items() if n};assert all(abs(n)<=1 for n in signed.values())
  declared=r['cap_reports'][side];outer,inner=declared['outer_loop'],declared['inner_loop'];expected_edges={(x,y) for loop in (outer,inner) for x,y in zip(loop,loop[1:]+loop[:1])}
  assert residual==expected_edges and len(outer)==len(set(outer))==256 and len(inner)==len(set(inner))==256 and not set(outer)&set(inner)
  assert fixed(outer) and fixed(inner)
  coord=lambda i:[points[i][k].get(0,F(0)) for k in range(2)]
  def orient(i,j,k):
   x,y,z=coord(i),coord(j),coord(k);return (y[0]-x[0])*(z[1]-x[1])-(y[1]-x[1])*(z[0]-x[0])
  minima=[]
  for loop in (outer,inner[::-1]):
   vals=[orient(x,y,z) for x,y in zip(loop,loop[1:]+loop[:1]) for z in loop if z not in (x,y)];assert min(vals)>0;minima.append(str(min(vals)))
  assert minima==declared['loop_convexity_minimum']
  inc=min(orient(x,y,z) for x,y in zip(outer,outer[1:]+outer[:1]) for z in inner);assert inc>0 and str(inc)==declared['strict_inclusion_minimum']
  areas=[]
  for loop in (outer,inner):
   # Origin triangle decomposition of the closed loop, independent of face fans.
   ar=sum((coord(x)[0]*coord(y)[1]-coord(x)[1]*coord(y)[0] for x,y in zip(loop,loop[1:]+loop[:1])),F(0))/2;areas.append(ar)
  assert areas[0]>0 and areas[1]<0 and total=={0:sum(areas)}==q.from_strings(declared['total_area_polynomial'])
  assert F(declared['constant_area'])==sum(areas)
  summary[side]=dict(faces=len(faces),triangles=sum(len(x['face']) for x in part['faces']),constant_area=str(sum(areas)),cap_plane_exact=True,strict_triangle_bounds_verified=True,strict_convexity_and_loop_inclusion_verified=True,oriented_chain_verified=True)
 out=dict(source_sha256=sha(Path(__file__)),pinned_sparse_sha256=sha(p),models_sha256=sha(w/'models.json'),primary_readback_sha256=sha(w/'readback.json'),domain_v=model['domain_v'],polynomial_bounds_verified=evaluated,fan_triangles_verified=triangles,caps=summary,parametric_face_sharing_verified=True,cell_and_boundary_edge_chains_verified=True,boundary_vertex_links_verified=len(links),cap_coverage_hypotheses_verified=True,volume_nonintersection_proved=False,native_executed=False,solution_accepted=False,elapsed_s=time.monotonic()-start)
 (w/'independent-readback-v2.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
if __name__=='__main__':main()
