"""Combinatorial gluing and inherited positive tetrahedron chain; no old bounds recomputed."""
import gzip,hashlib,json,time
from pathlib import Path
from collections import Counter,defaultdict
from fractions import Fraction as F
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def canonical(face):return min(tuple(face[i:]+face[:i]) for i in range(3))
def oriented(face):
 key=tuple(sorted(face));ids=[key.index(x) for x in face];sg=-1 if sum(ids[i]>ids[j] for i in range(3) for j in range(i+1,3))%2 else 1
 return key,sg

def main():
 start=time.monotonic();w=Path(__file__).parent;read=json.loads((w/'readback.json').read_text());ind=json.loads((w/'independent-readback.json').read_text());geo=json.loads((w/'triangles.json').read_text());assert sha(w/'triangles.json')==read['triangles_sha256']==ind['triangles_sha256']
 edge=defaultdict(list);links=defaultdict(list);adj=defaultdict(set)
 for i,t in enumerate(geo['triangles']):
  for k,x in enumerate(t):edge[tuple(sorted((x,t[(k+1)%3])))].append(i);links[x].append((t[k-1],t[(k+1)%3]))
 boundary_edges={k for k,v in edge.items() if len(v)==1};assert len(boundary_edges)==1024 and all(len(v) in (1,2) for v in edge.values());boundary_vertices=set().union(*boundary_edges)
 for v in edge.values():
  for x in v:adj[x].update(set(v)-{x})
 unseen=set(adj);components=[]
 while unseen:
  todo=[min(unseen)];seen=set()
  while todo:
   x=todo.pop()
   if x not in seen:seen.add(x);todo.extend(adj[x]-seen)
  unseen-=seen;components.append(len(seen))
 for vertex,arcs in links.items():
  graph=defaultdict(list)
  for x,y in arcs:graph[x].append(y);graph[y].append(x)
  degree=Counter(map(len,graph.values()));assert set(degree)<= {1,2}
  assert degree[1]==(2 if vertex in boundary_vertices else 0)
  seen=set();todo=[next(iter(graph))]
  while todo:
   x=todo.pop()
   if x not in seen:seen.add(x);todo.extend(set(graph[x])-seen)
  assert seen==set(graph)
 assert len(components)==2
 old=Path('work/bionic-volume-representation-20261013');receipt=json.loads((old/'readback.json').read_text());verification=json.loads((old/'independent-readback.json').read_text());assert receipt['domain_v']==read['domain_v']==verification['domain_v'];assert sha(old/'models.jsonl.gz')==receipt['models_sha256']==verification['models_sha256']
 chain=Counter();boundary=Counter();count=0;cells=0
 with gzip.open(old/'models.jsonl.gz','rt') as stream:
  for line in stream:
   row=json.loads(line)
   if row['kind']=='face':
    if len(row['occurrences'])==1:
     f=row['face'];sg=row['occurrences'][0][1];centre='f:'+','.join(map(str,sorted(f)))
     for i,x in enumerate(f):key,sign=oriented([centre,'v:'+str(x),'v:'+str(f[(i+1)%len(f)])]);boundary[key]+=sg*sign
   else:
    cells+=1;s='c:'+str(row['cell'])
    for t in row['tetrahedra']:
     assert F(t['bounds'][0])>0;f=t['face'];k=t['edge'];centre='f:'+','.join(map(str,sorted(f)));v=[s,centre,'v:'+str(f[k]),'v:'+str(f[(k+1)%len(f)])]
     if t['sign']<0:v[2],v[3]=v[3],v[2]
     for j in range(4):key,sg=oriented(v[:j]+v[j+1:]);chain[key]+=sg*((-1)**j)
     count+=1
 chain={k:v for k,v in chain.items() if v};boundary={k:v for k,v in boundary.items() if v};assert chain==boundary and len(chain)==17920 and all(abs(x)==1 for x in chain.values());assert count==119808 and cells==6144
 # Lateral labels/cycles equal the appropriate subchain of the inherited representation.
 for triangle in geo['triangles']:
  k,sg=oriented(triangle);assert boundary[k]==sg
 assert verification['counts']['positive_tetrahedra']==count and verification['all_coefficients_and_bounds_exact']
 result=dict(source_sha256=sha(Path(__file__)),primary_readback_sha256=sha(w/'readback.json'),independent_readback_sha256=sha(w/'independent-readback.json'),inherited_models_sha256=receipt['models_sha256'],inherited_verification_sha256=sha(old/'independent-readback.json'),domain_v=read['domain_v'],lateral_components=components,lateral_vertices=len(links),lateral_boundary_vertices=len(boundary_vertices),lateral_boundary_edges=len(boundary_edges),lateral_links_are_paths_or_cycles=True,tetrahedra_positive_bounds_inherited=count,cells=cells,tetrahedron_boundary_equals_global_fan_chain=True,external_triangles=len(chain),old_polynomial_bounds_recomputed=False,elapsed_s=time.monotonic()-start)
 (w/'gluing-readback.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
