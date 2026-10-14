"""Independent reconstruction from reduced hex templates, no primary import."""
import gzip,hashlib,itertools,json,time
from pathlib import Path
from collections import defaultdict,Counter
W=Path(__file__).parent
T=((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7))
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def cycle(s):return min(s[i:]+s[:i] for i in range(len(s)))
def even(s):
 # Permutations generated via an even number of transpositions.
 out={tuple(s)};todo=[tuple(s)]
 while todo:
  a=todo.pop()
  for i,j,k in itertools.combinations(range(len(a)),3):
   b=list(a);b[i],b[j],b[k]=a[j],a[k],a[i];b=tuple(b)
   if b not in out:out.add(b);todo.append(b)
 return min(out)
def check(ts):
 unique=set();faces=defaultdict(list)
 for t in ts:
  assert len(set(t))==len(t) and frozenset(t) not in unique;unique.add(frozenset(t))
  for j in range(len(t)):
   f=t[:j]+t[j+1:]
   if j%2:f=f[::-1] if len(f)==2 else (f[1],f[0])+f[2:]
   faces[frozenset(f)].append(f)
 for key,ff in faces.items():
  assert len(ff) in (1,2)
  if len(ff)==2:
   if len(ff[0])==2:assert ff[0]==ff[1][::-1]
   else:assert cycle(ff[0])==cycle(ff[1][::-1])
 return faces

def references():
 a=('a','b','c','d');b=('e','b','d','c');assert Counter(map(len,check([a,b]).values()))=={1:6,2:1}
 for bad in [[a,a],[a,('e','b','c','d')],[a,b,('f','b','d','c')]]:
  try:check(bad)
  except AssertionError:pass
  else:raise AssertionError('Invalid incidence accepted')
 assert Counter(map(len,check([('a','b','c'),('a','c','d')]).values()))=={1:4,2:1}
 try:check([('a','b','c'),('a','d','c')])
 except AssertionError:pass
 else:raise AssertionError('Invalid cap accepted')
 return 6

def main():
 start=time.monotonic();inv=json.loads((W/'input-inventory.json').read_text())
 for r in inv['inputs']:assert sha(Path(r['path']))==r['sha256']
 primary=json.loads((W/'readback.json').read_text());assert primary['input_inventory_sha256']==sha(W/'input-inventory.json') and primary['proof_sha256']==sha(W/'proof.md')
 s=json.loads(Path('work/bionic-buffered-transition-20261013/construction.json').read_text());tets=[];recordset=set();owners=defaultdict(set);cellpoints={};reg=defaultdict(set)
 for cid,block in enumerate(s['blocks']):
  cellpoints[cid]=set(block)
  for template in T:
   f=[]
   for i in template:
    if not f or block[i]!=f[-1]:f.append(block[i])
   if f and f[0]==f[-1]:f.pop()
   if len(f)<3:continue
   assert len(f)==len(set(f));reg[tuple(sorted(f))].add(cid)
   centre='f:'+','.join(map(str,sorted(f)))
   for i in range(len(f)):
    tet=('c:'+str(cid),centre,'v:'+str(f[i]),'v:'+str(f[(i+1)%len(f)]));tets.append(tet)
    key=(cid,even(tet));assert key not in recordset;recordset.add(key)
    for mask in range(1,15):
     sub=tuple(sorted(tet[j] for j in range(4) if mask>>j&1));owners[sub].add(cid)
 assert len(tets)==119808 and len(s['blocks'])==6144
 ff=check(tets);border={tuple(sorted(k)):v[0] for k,v in ff.items() if len(v)==1};assert len(border)==17920
 assert {str(k):v for k,v in Counter(map(len,ff.values())).items()}==primary['tetrahedral_face_incidence_counts']
 assert sha(W/'abstract-tetrahedra.jsonl.gz')==primary['abstract_tetrahedra_sha256']
 remaining=set(recordset);count=0
 with gzip.open(W/'abstract-tetrahedra.jsonl.gz','rt') as f:
  for line in f:
   cid,vertices,sign=json.loads(line);vertices=tuple(vertices)
   if sign<0:vertices=(vertices[1],vertices[0])+vertices[2:]
   remaining.remove((cid,even(vertices)));count+=1
 assert not remaining and count==len(recordset)
 caps=json.loads(Path('work/bionic-parametric-boundary-20261013/models.json').read_text());capread=json.loads(Path('work/bionic-parametric-boundary-20261013/readback.json').read_text());capkeys=set();capreports=[];capedges=set()
 for cap in caps['caps']:
  ts=[]
  for r in cap['faces']:
   f=r['face'];centre='f:'+','.join(map(str,sorted(f)));assert len(reg[tuple(sorted(f))])==1
   for a,b in zip(f,f[1:]+f[:1]):ts.append((centre,'v:'+str(a),'v:'+str(b)))
  capkeys.update(tuple(sorted(t)) for t in ts);edges=check(ts);ends={tuple(sorted(k)) for k,v in edges.items() if len(v)==1};loops=capread['cap_reports'][cap['side']];expected=set()
  for name in ('outer_loop','inner_loop'):
   loop=loops[name]
   for i in range(len(loop)):expected.add(tuple(sorted(('v:'+str(loop[i-1]),'v:'+str(loop[i])))))
  assert ends==expected and len(ends)==512;capedges.update(ends)
  capreports.append({'side':cap['side'],'triangles':len(ts),'edge_incidence_counts':{str(k):v for k,v in Counter(map(len,edges.values())).items()},'boundary_edges':len(ends)})
 assert capreports==primary['caps'] and caps['domain_v']==primary['domain_v']
 lateral=json.loads(Path('work/bionic-boundary-embedding-20261013/triangles.json').read_text())['triangles'];latkeys={tuple(sorted(t)) for t in lateral};assert capkeys.isdisjoint(latkeys) and capkeys|latkeys==set(border)
 ledges=check([tuple(t) for t in lateral]);loops={tuple(sorted(k)) for k,v in ledges.items() if len(v)==1};assert len(loops)==1024 and loops==capedges
 assert set().union(*capkeys)&set().union(*latkeys)==set().union(*loops)
 pairs=defaultdict(set)
 for simplex,cs in owners.items():
  for pair in itertools.combinations(sorted(cs),2):pairs[pair].add(simplex)
 assert sha(W/'contacts.jsonl.gz')==primary['contacts_sha256'];seen=set();counts=Counter()
 with gzip.open(W/'contacts.jsonl.gz','rt') as f:
  for line in f:
   a,b,record=json.loads(line);key=(a,b);assert key not in seen;seen.add(key)
   common=pairs[key];maximal={x for x in common if not any(set(x)<set(y) for y in common)}
   assert maximal=={tuple(x) for x in record};assert cellpoints[a]&cellpoints[b]
   counts[max(map(len,maximal))-1]+=1
 assert seen==set(pairs) and len(seen)==primary['cell_pairs_with_shared_subcomplex']
 assert {str(k):v for k,v in counts.items()}==primary['contact_counts_by_max_dimension']
 result={'source_sha256':sha(Path(__file__)),'primary_readback_sha256':sha(W/'readback.json'),'all_oriented_tetrahedra_and_cell_assignments_match':True,'tetrahedra':count,'all_new_incidence_predicates_confirmed':True,'all_contact_subcomplexes_match':True,'contact_pairs':len(seen),'domain_v':caps['domain_v'],'old_geometry_recomputed':False,'proof_is_formally_machine_checked':False,'native_admission':False,'elapsed_s':time.monotonic()-start}
 with (W/'independent-readback.json').open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps(result),flush=True)
if __name__=='__main__':
 import sys
 if '--references' in sys.argv:print(json.dumps({'references':references()}))
 else:main()
