"""Independent moments, reduced templates and complementary quotient bounds."""
import gzip,hashlib,importlib.util,json,math,subprocess,time
from pathlib import Path
from fractions import Fraction as F
from collections import defaultdict,Counter
W=Path(__file__).parent
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def module(name,path,digest):
 assert sha(path)==digest
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
h=module('independent_moments',Path('work/bionic-centre-interval-bounds-20261013/verify_centres_v2.py'),'a259f163405dec0cfb4f1b707698249ea9069de9b02a9db1835fb172f1a0b992');g=h.g
k=module('integer192',Path('work/bionic-remaining-cell-bounds-20261013/dyadic192.py'),'f216b134a93a893b0c04bbe47671eb5ba497e4836e0e2a346220f0b14d83ac14');g.R=k.R
R=g.R;Q=2**192;S=F(float('1e-300'));LIMIT=F(float('0.05'))
T=((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7))
def absrange(x):
 if x.a>=0:return x.a,x.b
 if x.b<=0:return -x.b,-x.a
 return F(0),max(-x.a,x.b)
def rational_weight(a,b,c,d):
 lower=min(1-(d+S)/(a+d+S),1-(b+S)/(c+b+S));upper=min(F(1,2),1-(c+S)/(b+c+S),1-(a+S)/(d+a+S))
 return lower,upper
def weight(x,y):
 lower,upper=rational_weight(*absrange(x),*absrange(y))
 return math.floor(lower*Q),math.ceil(upper*Q)
def references():
 assert rational_weight(S,S,S,S)==(F(1,3),F(1,3))
 assert rational_weight(S,S,2*S,2*S)==(F(1,4),F(1,4))
 count=2
 for a,b in [(1,1),(-1,2),(2,-1),(S,S),(S,2*S),(0,1)]:
  expected=min(abs(F(a)),abs(F(b)))/(abs(F(a))+abs(F(b))+S);l,r=weight(R(a),R(b));assert F(l,Q)<=expected<=F(r,Q);count+=1
 assert weight(R(-1,1),R(1))[0]==0;count+=1
 for scale in (F(1),F(1,1000),F(1,1000000)):
  cells=[]
  for shift in (0,1):
   ps=[[R(scale*(x+shift)),R(scale*y),R(scale*z)] for x,y,z in ((0,0,0),(1,0,0),(1,1,0),(0,1,0),(0,0,1),(1,0,1),(1,1,1),(0,1,1))]
   centre,volume,geo=h.moments([[ps[i] for i in f] for f in T]);assert volume.a<=scale**3<=volume.b;cells.append((centre,geo))
  cf,area=cells[0][1][3];x=g.inner(area,g.vsub(cf,cells[0][0]));y=g.inner(area,g.vsub(cells[1][0],cf));l,r=weight(x,y);expected=(scale**3/2)/(scale**3+S);assert F(l,Q)<=expected<=F(r,Q);count+=1
 return count

def main():
 start=time.monotonic();refs=references();report=json.loads((W/'readback.json').read_text());assert sha(W/'weight-bounds.jsonl.gz')==report['bounds_sha256'];dep=json.loads((W/'dependencies.json').read_text());entries=0
 assert dep['anchor_commit']=='efc7b2488dde73e5a1ae21b86fe2347f40d0ab0f'
 for name,digest in dep['manifests'].items():
  p=Path(name);phase=p.parent.name.split('20261013-',1)[1];raw=subprocess.check_output(['git','show',dep['anchor_commit']+':twins/bionic-turbo-f1/evidence/airflow-'+phase+'-20261013/file-manifest.json']);assert hashlib.sha256(raw).hexdigest()==digest==sha(p)
  for row in json.loads(raw)['files']:
   p=Path('work')/row['path'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'];entries+=1
 assert entries==357 and len(dep['manifests'])==15
 src=json.loads(Path('work/bionic-buffered-transition-20261013/construction.json').read_text());sy=json.loads(Path('work/bionic-joint-constraints-20261013/system.json').read_text());bindings={r['point']:r for r in sy['coordinate_bindings']};u=F(sy['archived_regression_point']['u']);boxes=json.loads(Path('work/bionic-angular-independent-bounds-20261013/certificate-readback.json').read_text())['box_results'];domains={r['parent_leaf']:(r['lower'],r['upper']) for r in boxes};domains['envelope']=(boxes[0]['lower'],boxes[-1]['upper']);assert list(domains['envelope'])==report['domain_v']
 fs=[];reg=defaultdict(list);canon=lambda f:min(tuple(f[i:]+f[:i]) for i in range(len(f)))
 for cid,block in enumerate(src['blocks']):
  faces=[]
  for t in T:
   f=[]
   for j in t:
    if not f or f[-1]!=block[j]:f.append(block[j])
   if f[-1]==f[0]:f.pop()
   if len(f)>2:reg[tuple(sorted(f))].append((cid,len(faces)));faces.append(f)
  fs.append(faces)
 keys=sorted(reg);assert len(keys)==18560
 for v in reg.values():
  assert len(v) in (1,2)
  if len(v)==2:
   (a,i),(b,j)=v;assert canon(fs[a][i])==canon(fs[b][j][::-1])
 assert {key for key,v in reg.items() if len(v)==1}=={tuple(sorted(set(f))) for f in src['walls']}
 assert len(src['mrf_faces'])==384 and all(len(reg[tuple(sorted(f))])==2 for f in src['mrf_faces'])
 anchors=[[R(F(x)) for x in src['vertices'][block[0]]] for block in src['blocks']]
 active=None;records=0;bounds=0;counts=Counter();unknown=[];seen=[];singular=0;visited=[]
 with gzip.open(W/'weight-bounds.jsonl.gz','rt') as stream:
  for line in stream:
   dom,rank,data,status=json.loads(line)
   if dom!=active:
    if active is not None:assert seen==(list(range(18560)) if active=='envelope' else unknown)
    visited.append(dom);active=dom;seen=[];cache={};ps=[];v=R(*map(F,domains[dom]))
    for i,p in enumerate(src['vertices']):
     r=bindings.get(i)
     if r:
      t=R(u) if r['variable']=='u' else v;ps.append([R(F(r['x_coefficient']))*t,R(F(r['y_coefficient']))*t,R(F(r['z_exact']))])
     else:ps.append([R(F(x)) for x in p])
   seen.append(rank);incidence=reg[keys[rank]]
   expected='unknown' if data is None else ('positive' if F(data[-2],2**160)>=LIMIT else 'refused' if F(data[-1],2**160)<LIMIT else 'unknown')
   assert status==expected
   if dom=='envelope' and status=='unknown':unknown.append(rank)
   def cell(cid):
    if cid not in cache:
     C,V,geo=h.moments([[g.vsub(ps[i],anchors[cid]) for i in f] for f in fs[cid]]);cache[cid]=(g.vadd(C,anchors[cid]),[(g.vadd(cf,anchors[cid]),area) for cf,area in geo])
    return cache[cid]
   if len(incidence)==1:actual=[Q,Q];assert data==[2**160,2**160]
   elif data is None:
    assert status=='unknown';singular+=1;actual=None
    # Reconstruct only this unresolved trace with the pinned primary moment library.
    c160=module('trace_centred',Path('work/bionic-centre-interval-bounds-20261013/centred.py'),'4f366b9571c931fa8d4bf19e90e94c5bd77d0093c193a1e0de9caf1f3590361b');bb=c160.b;II=bb.I;qq=bb.Q
    vv=II(math.floor(F(domains[dom][0])*qq),math.ceil(F(domains[dom][1])*qq),True);pp=[]
    for label,p in enumerate(src['vertices']):
     binding=bindings.get(label)
     if binding:
      t=II(u) if binding['variable']=='u' else vv;pp.append([II(F(binding['x_coefficient']))*t,II(F(binding['y_coefficient']))*t,II(F(binding['z_exact']))])
     else:pp.append([II(F(x)) for x in p])
    unresolved=False
    for cid,index in incidence:
     anchor=[II(F(x)) for x in src['vertices'][src['blocks'][cid][0]]]
     try:c160.cell([c160.face([bb.minus(pp[i],anchor) for i in f]) for f in fs[cid]])
     except ZeroDivisionError:unresolved=True
    assert unresolved
   else:
    (a,i),(b,j)=incidence;own=cell(a);nei=cell(b);cf,area=own[1][i];x=g.inner(area,g.vsub(cf,own[0]));y=g.inner(area,g.vsub(nei[0],cf));l,r=weight(x,y);actual=[x.lo,x.hi,y.lo,y.hi,l,r]
   if actual is not None:
    assert len(actual)==len(data)
    for i in range(0,len(actual),2):assert F(data[i],2**160)<=F(actual[i],Q)<=F(actual[i+1],Q)<=F(data[i+1],2**160);bounds+=1
    if status=='positive':assert F(actual[-2],Q)>=LIMIT
    if status=='refused':assert F(actual[-1],Q)<LIMIT
   counts[str(dom)+':'+status]+=1;records+=1
 assert seen==(list(range(18560)) if active=='envelope' else unknown)
 assert visited==['envelope']+([r['parent_leaf'] for r in boxes] if unknown else [])
 assert unknown==report['envelope_unknown_ranks'] and dict(counts)==report['counts'] and records==report['records']
 out={'source_sha256':sha(Path(__file__)),'primary_readback_sha256':sha(W/'readback.json'),'references':refs,'manifests_verified':15,'payload_entries_verified':entries,'records_verified':records,'intervals_verified':bounds,'all_bounds_contained':True,'all_claimed_signs_confirmed':True,'singular_primary_records':singular,'domain_v':report['domain_v'],'native_admission':False,'elapsed_s':time.monotonic()-start}
 (W/'independent-readback.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out),flush=True)
if __name__=='__main__':main()
