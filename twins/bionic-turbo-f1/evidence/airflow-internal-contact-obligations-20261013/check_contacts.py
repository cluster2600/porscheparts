"""New abstract incidence certificate; inherited geometry is not recomputed."""
import gzip,hashlib,itertools,json,time
from pathlib import Path
from fractions import Fraction
from collections import defaultdict,Counter
W=Path(__file__).parent
BASE='050b28b932aee9eaafe4b07e43fad17a6f6ee157'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def signed(seq):
 seq=tuple(seq);key=tuple(sorted(seq));assert len(set(seq))==len(seq)
 return key,(-1)**sum(seq[i]>seq[j] for i in range(len(seq)) for j in range(i+1,len(seq)))
def facets(simplices):
 out=defaultdict(list);seen=set()
 for s in simplices:
  key,_=signed(s);assert key not in seen;seen.add(key)
  for i in range(len(s)):
   key,sign=signed(s[:i]+s[i+1:]);out[key].append((-1)**i*sign)
 assert all(len(v) in (1,2) and (len(v)==1 or sum(v)==0) for v in out.values())
 return {k:v[0] for k,v in out.items() if len(v)==1},Counter(map(len,out.values()))
def references():
 a=('a','b','c','d');b=('e','b','d','c')
 assert facets([a,b])[1]=={1:6,2:1}
 for bad in [[a,a],[a,('e','b','c','d')],[a,b,('f','b','d','c')]]:
  try:facets(bad)
  except AssertionError:pass
  else:raise AssertionError('Invalid incidence accepted')
 assert facets([('a','b','c'),('a','c','d')])[1]=={1:4,2:1}
 try:facets([('a','b','c'),('a','d','c')])
 except AssertionError:pass
 else:raise AssertionError('Invalid triangle orientation accepted')
 return 6

def main():
 start=time.monotonic();inv=json.loads((W/'input-inventory.json').read_text());assert inv['anchor_commit']==BASE
 for row in inv['inputs']:
  assert sha(Path(row['path']))==row['sha256']
 old=Path('work/bionic-volume-representation-20261013');receipt=json.loads((old/'readback.json').read_text());ind=json.loads((old/'independent-readback.json').read_text());assert receipt['models_sha256']==ind['models_sha256']==sha(old/'models.jsonl.gz')
 domain=receipt['domain_v'];tets=[];faces={};cells={};simplices=defaultdict(set)
 with gzip.open(old/'models.jsonl.gz','rt') as f:
  for line in f:
   r=json.loads(line)
   if r['kind']=='face':faces[tuple(sorted(r['face']))]=r
   else:
    cid=r['cell'];assert cid not in cells;cells[cid]=[]
    for t in r['tetrahedra']:
     assert Fraction(t['bounds'][0])>0
     face=t['face'];i=t['edge'];s=('c:'+str(cid),'f:'+','.join(map(str,sorted(face))),'v:'+str(face[i]),'v:'+str(face[(i+1)%len(face)]))
     if t['sign']<0:s=s[:2]+(s[3],s[2])
     tets.append(s);cells[cid].append(s)
     for k in (1,2,3):simplices[cid].update(tuple(sorted(x)) for x in itertools.combinations(s,k))
 assert len(tets)==119808 and len(cells)==6144
 boundary,inc=facets(tets);expected={}
 for key,r in faces.items():
  if len(r['occurrences'])!=1:continue
  f=r['face'];sg=r['occurrences'][0][1];centre='f:'+','.join(map(str,key))
  for i in range(len(f)):
   tri=(centre,'v:'+str(f[i]),'v:'+str(f[(i+1)%len(f)]));k,v=signed(tri);expected[k]=sg*v
 assert boundary==expected and len(boundary)==17920
 caps=json.loads(Path('work/bionic-parametric-boundary-20261013/models.json').read_text());capread=json.loads(Path('work/bionic-parametric-boundary-20261013/readback.json').read_text());assert caps['domain_v']==domain
 capreports=[];captris=set();capedges=set()
 for cap in caps['caps']:
  triangles=[]
  for r in cap['faces']:
   f=r['face'];centre='f:'+','.join(map(str,sorted(f)))
   for i,t in enumerate(r['fan_triangles']):
    assert Fraction(t['bounds'][0])>0
    tri=(centre,'v:'+str(f[i]),'v:'+str(f[(i+1)%len(f)]));assert signed(tri)[0] in boundary
    triangles.append(tri);captris.add(tuple(sorted(tri)))
  border,counts=facets(triangles);report=capread['cap_reports'][cap['side']];edges=set()
  for name in ('outer_loop','inner_loop'):
   loop=report[name]
   for a,b in zip(loop,loop[1:]+loop[:1]):edges.add(tuple(sorted(('v:'+str(a),'v:'+str(b)))))
  assert set(border)==edges and len(edges)==512;capedges.update(edges)
  capreports.append({'side':cap['side'],'triangles':len(triangles),'edge_incidence_counts':dict(counts),'boundary_edges':len(edges)})
 lat=json.loads(Path('work/bionic-boundary-embedding-20261013/triangles.json').read_text())['triangles'];latset={tuple(sorted(x)) for x in lat};assert not captris&latset and captris|latset==set(boundary)
 latborder,_=facets([tuple(t) for t in lat]);assert len(latborder)==1024 and set(latborder)==capedges
 # Every cap/lateral shared simplex lies in the certified common boundary loops.
 caplabels=set().union(*captris);latlabels=set().union(*latset);assert caplabels&latlabels==set().union(*latborder)
 tetra_records=sorted((cid,signed(t)[0],signed(t)[1]) for cid,ts in cells.items() for t in ts)
 with gzip.open(W/'abstract-tetrahedra.jsonl.gz','xt') as f:
  for r in tetra_records:f.write(json.dumps(r,separators=(',',':'))+'\n')
 # Label intersections provide the complete contact subcomplex after proof.md.
 pointcells=defaultdict(set)
 for cid,ss in simplices.items():
  for s in ss:
   if len(s)==1 and s[0].startswith('v:'):pointcells[s[0]].add(cid)
 pairs=set()
 for cs in pointcells.values():pairs.update(itertools.combinations(sorted(cs),2))
 contact_counts=Counter()
 with gzip.open(W/'contacts.jsonl.gz','xt') as f:
  for a,b in sorted(pairs):
   common=simplices[a]&simplices[b];maximal=[]
   for s in sorted(common,key=lambda x:(-len(x),x)):
    if not any(set(s)<=set(t) for t in maximal):maximal.append(s)
   assert maximal;contact_counts[max(map(len,maximal))-1]+=1
   f.write(json.dumps([a,b,maximal],separators=(',',':'))+'\n')
 result={'source_sha256':sha(Path(__file__)),'input_inventory_sha256':sha(W/'input-inventory.json'),'proof_sha256':sha(W/'proof.md'),'domain_v':domain,'cells':len(cells),'tetrahedra':len(tets),'tetrahedral_face_incidence_counts':dict(inc),'external_triangles':len(boundary),'caps':capreports,'abstract_tetrahedra_sha256':sha(W/'abstract-tetrahedra.jsonl.gz'),'contacts_sha256':sha(W/'contacts.jsonl.gz'),'cell_pairs_with_shared_subcomplex':len(pairs),'cell_pairs_without_shared_subcomplex':6144*6143//2-len(pairs),'contact_counts_by_max_dimension':dict(contact_counts),'old_geometry_recomputed':False,'native_admission':False,'proof_is_formally_machine_checked':False,'elapsed_s':time.monotonic()-start}
 with (W/'readback.json').open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps(result),flush=True)
if __name__=='__main__':
 import sys
 if '--references' in sys.argv:print(json.dumps({'references':references()}))
 else:main()
