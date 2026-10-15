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
R=g.R;Q=2**192;S=F(float('1e-150'));LIMIT=F(4)
T=((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7))
def quotient_bounds(a,b,c,d):
 if c<=0<=d:raise ZeroDivisionError('pole')
 reciprocal=(1/d,1/c);v=[x*y for x in (a,b) for y in reciprocal]
 return R(min(v),max(v))
def ratio(x,y,add=F(0)):return quotient_bounds(x.a,x.b,y.a+add,y.b+add)
def magnitude_interval(x):
 if x.a>=0:return x
 if x.b<=0:return -x
 return R(0,max(-x.a,x.b))
def maximum(a,b):return (a+b+abs(a-b))/2
def evaluate_skew(cf,area,owner,neighbour,points):
 offset=g.vsub(cf,owner);area_norm=g.length(area)
 if neighbour is None:
  if area_norm.b<S:normal=[R(0),R(0),R(0)]
  elif area_norm.a>=S:normal=[ratio(x,area_norm) for x in area]
  else:raise ZeroDivisionError('normal branch')
  delta=g.scale(normal,g.inner(normal,offset));alpha=F(float('0.4'))
 else:delta=g.vsub(neighbour,owner);alpha=F(float('0.2'))
 denominator=g.inner(area,delta)
 correction=g.scale(delta,ratio(g.inner(area,offset),denominator,S))
 vector=g.vsub(offset,correction);length=g.length(vector)
 unit=[]
 for value in vector:
  z=ratio(value,length,S);unit.append(R(max(F(-1),z.a),min(F(1),z.b)))
 dnorm=g.length(delta);fd_low=alpha*dnorm.a+S;fd_high=alpha*dnorm.b+S
 for point in points:
  projection=magnitude_interval(g.inner(unit,g.vsub(point,cf)))
  fd_low=maximum(fd_low,projection.a);fd_high=maximum(fd_high,projection.b)
 result=quotient_bounds(length.a,length.b,fd_low,fd_high)
 return [n for v in (area_norm,denominator,length,R(fd_low,fd_high),result) for n in (v.lo,v.hi)]
def references():
 assert quotient_bounds(S,S,2*S,2*S).a==F(1,2)
 assert quotient_bounds(F(0),F(0),S,S).b==0
 try:quotient_bounds(F(1),F(1),F(-1),F(1))
 except ZeroDivisionError:pass
 else:raise AssertionError('pole accepted')
 count=3
 for scale in (F(1),F(1,1000),F(1,1000000)):
  face=[R(scale),R(0),R(0)];owner=[R(0)]*3;neighbour=[R(2*scale),R(0),R(0)];area=[R(scale**2),R(0),R(0)]
  vertices=[[R(scale),R(y*scale),R(z*scale)] for y,z in ((-1,-1),(1,-1),(1,1),(-1,1))]
  for boundary in (False,True):
   data=evaluate_skew(face,area,owner,None if boundary else neighbour,vertices)
   delta=scale if boundary else 2*scale;alpha=F(float('0.4' if boundary else '0.2'))
   expected=scale*S/((scale**2*delta+S)*(alpha*delta+S))
   assert F(data[-2],Q)<=expected<=F(data[-1],Q);count+=1
 data=evaluate_skew([R(1),R(0),R(0)],[R(0)]*3,[R(0)]*3,None,[[R(2),R(0),R(0)]])
 assert F(data[-2],Q)<=1+S<=F(data[-1],Q);count+=1
 return count

def main():
 start=time.monotonic();refs=references();report=json.loads((W/'readback.json').read_text());assert sha(W/'skewness-bounds.jsonl.gz')==report['bounds_sha256'];dep=json.loads((W/'dependencies.json').read_text());entries=0
 assert dep['anchor_commit']=='056526bccf0537fa1992a465c42a4b8c677ec700'
 for name,digest in dep['manifests'].items():
  p=Path(name);phase=p.parent.name.split('20261013-',1)[1];raw=subprocess.check_output(['git','show',dep['anchor_commit']+':twins/bionic-turbo-f1/evidence/airflow-'+phase+'-20261013/file-manifest.json']);assert hashlib.sha256(raw).hexdigest()==digest==sha(p)
  for row in json.loads(raw)['files']:
   p=Path('work')/row['path'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'];entries+=1
 assert entries==379 and len(dep['manifests'])==16
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
 with gzip.open(W/'skewness-bounds.jsonl.gz','rt') as stream:
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
   expected='unknown' if data is None else ('positive' if F(data[-1],2**160)<=LIMIT else 'refused' if F(data[-2],2**160)>LIMIT else 'unknown')
   assert status==expected
   if dom=='envelope' and status=='unknown':unknown.append(rank)
   def cell(cid):
    if cid not in cache:
     C,V,geo=h.moments([[g.vsub(ps[i],anchors[cid]) for i in f] for f in fs[cid]]);cache[cid]=(g.vadd(C,anchors[cid]),[(g.vadd(cf,anchors[cid]),area) for cf,area in geo])
    return cache[cid]
   (a,i)=incidence[0]
   try:
    own=cell(a);nei=cell(incidence[1][0]) if len(incidence)==2 else None;cf,area=own[1][i]
    actual=evaluate_skew(cf,area,own[0],nei[0] if nei else None,[ps[label] for label in fs[a][i]])
   except ZeroDivisionError:
    if data is not None:raise
    actual=None
   if data is None:
    assert status=='unknown';singular+=1
    # Independent diagnostic may be tighter. No finite primary bound is claimed.
    actual=None
   if actual is not None:
    assert len(actual)==len(data)
    for i in range(0,len(actual),2):assert F(data[i],2**160)<=F(actual[i],Q)<=F(actual[i+1],Q)<=F(data[i+1],2**160);bounds+=1
    if status=='positive':assert F(actual[-1],Q)<=LIMIT
    if status=='refused':assert F(actual[-2],Q)>LIMIT
   counts[str(dom)+':'+status]+=1;records+=1
 assert seen==(list(range(18560)) if active=='envelope' else unknown)
 assert visited==['envelope']+([r['parent_leaf'] for r in boxes] if unknown else [])
 assert unknown==report['envelope_unknown_ranks'] and dict(counts)==report['counts'] and records==report['records']
 out={'source_sha256':sha(Path(__file__)),'primary_readback_sha256':sha(W/'readback.json'),'references':refs,'manifests_verified':16,'payload_entries_verified':entries,'records_verified':records,'intervals_verified':bounds,'all_bounds_contained':True,'all_claimed_signs_confirmed':True,'singular_primary_records':singular,'domain_v':report['domain_v'],'native_admission':False,'elapsed_s':time.monotonic()-start}
 (W/'independent-readback.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out),flush=True)
if __name__=='__main__':main()
