"""Independent sparse verification of shared fans, tetrahedra and volume discrepancy bounds."""
import gzip,hashlib,importlib.util,json,time
from pathlib import Path
from fractions import Fraction as F
from collections import Counter,defaultdict
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
p=Path('work/bionic-gram-interval-bounds-20261013/verify_models.py');assert sha(p)=='1a2c0167b9d76d6f515d20bca1d2f244d172aebdbf49887a8c36f603b891d97c'
spec=importlib.util.spec_from_file_location('pinned_sparse',p);q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
def cycle(face):return min(tuple(face[i:]+face[:i]) for i in range(len(face)))
def main():
 start=time.monotonic();w=Path(__file__).parent;r=json.loads((w/'readback.json').read_text());model=r
 for name,key in [('check_representation.py','source_sha256'),('preflight.md','preflight_sha256'),('derivation.md','derivation_sha256'),('models.jsonl.gz','models_sha256'),('dependencies.json','dependencies_sha256')]:assert sha(w/name)==r[key]
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
 sub=lambda aa,bb:[q.difference(x,y) for x,y in zip(aa,bb)]
 mid=lambda coords:[q.times(q.total(x[k] for x in coords),F(1,len(coords))) for k in range(3)]
 checked=0
 def verify(poly,record):
  nonlocal checked
  assert poly==q.from_strings(record['polynomial'])
  cs=q.restricted(poly,a,b);bb=[min(cs),max(cs)];assert bb==list(map(F,record['bounds']));checked+=1;return bb
 def det(x,y,z):return q.det([x,y,z])
 geometry={};counts=Counter();min_tet=None;min_cell=None;max_error=F(0);ncell=0
 with gzip.open(w/'models.jsonl.gz','rt') as stream:
  for line in stream:
   row=json.loads(line)
   if row['kind']=='face':
    f=row['face'];key=frozenset(f);assert key in reg and key not in geometry
    occurrences=reg[key];expected=[]
    assert tuple(f)==cycle(occurrences[0][1])
    for cid,g in occurrences:
     sg=1 if cycle(g)==tuple(f) else -1;assert sg==1 or cycle(g[::-1])==tuple(f);expected.append([cid,sg])
    assert row['occurrences']==expected
    pts=[points[i] for i in f];c=mid(pts);normal=[];g=[]
    for x,y in zip(pts,pts[1:]+pts[:1]):
     aa=[q.times(z,F(1,2)) for z in q.vector(sub(y,x),sub(c,x))];normal.append(aa);g.append(mid([c,x,y]))
    assert len(row['triangle_area_squared'])==len(row['flux_error_components'])==len(f)
    for aa,entry in zip(normal,row['triangle_area_squared']):assert verify(q.scalar(aa,aa),entry)[0]>0;counts['face_triangles']+=1
    eps=[]
    for k,entry in enumerate(row['flux_error_components']):
     ee=q.total(q.scalar(aa,sub(gg,g[k])) for aa,gg in zip(normal,g));eps.append(verify(ee,entry))
    error=[min(x[0] for x in eps),max(x[1] for x in eps)];assert list(map(F,row['flux_error_bound']))==error
    triple={} if len(f)==3 else det(sub(pts[1],pts[0]),sub(pts[2],pts[0]),sub(pts[3],pts[0]))
    bb=verify(triple,row['coplanarity']);counts['identically_planar' if not triple else 'nonzero_coplanarity_polynomial']+=1
    if triple and (bb[0]>0 or bb[1]<0):counts['strict_nonplanarity_over_domain']+=1
    max_error=max(max_error,*map(abs,error));geometry[key]=(f,c,error)
   else:
    assert row['kind']=='cell' and row['cell']==ncell and len(geometry)==len(reg)
    block=s['blocks'][ncell];seed=mid([points[i] for i in sorted(set(block))]);fs=[]
    for template in templates:
     ff=[]
     for k in template:
      if not ff or ff[-1]!=block[k]:ff.append(block[k])
     if ff[-1]==ff[0]:ff.pop()
     if len(ff)>=3:fs.append(ff)
    total={};err=[F(0),F(0)];index=0
    for face in fs:
     f,c,error=geometry[frozenset(face)];sg=1 if cycle(face)==tuple(f) else -1
     for k,(x,y) in enumerate(zip(f,f[1:]+f[:1])):
      rr=row['tetrahedra'][index];assert rr['face']==f and rr['edge']==k and rr['sign']==sg
      pp=q.times(det(sub(c,seed),sub(points[x],seed),sub(points[y],seed)),F(sg));bb=verify(pp,rr);index+=1
      counts['positive_tetrahedra' if bb[0]>0 else 'negative_tetrahedra' if bb[1]<=0 else 'indeterminate_tetrahedra']+=1
      min_tet=bb[0] if min_tet is None else min(min_tet,bb[0])
      total=q.total([total,q.times(det(c,points[x],points[y]),F(sg,6))])
     signed=error if sg==1 else [-error[1],-error[0]]
     err=[err[j]+signed[j]/3 for j in (0,1)]
    assert index==len(row['tetrahedra']) and err==list(map(F,row['fan_minus_native_volume_bound']))
    bb=verify(total,row['fan_signed_volume']);assert bb[0]>0;min_cell=bb[0] if min_cell is None else min(min_cell,bb[0]);ncell+=1
    if ncell%1024==0:print(json.dumps(dict(cells=ncell,polynomials=checked)),flush=True)
 assert ncell==r['cells']==6144 and len(geometry)==r['faces']==18560 and dict(counts)==r['counts']
 assert min_tet==F(r['minimum_six_volume_bound']) and min_cell==F(r['minimum_cell_fan_volume_bound']) and max_error==F(r['maximum_face_flux_error_bound'])
 result=dict(source_sha256=sha(Path(__file__)),pinned_sparse_sha256=sha(Path('work/bionic-gram-interval-bounds-20261013/verify_models.py')),models_sha256=sha(w/'models.jsonl.gz'),primary_readback_sha256=sha(w/'readback.json'),domain_v=r['domain_v'],faces_verified=len(geometry),cells_verified=ncell,polynomials_and_bounds_verified=checked,all_coefficients_and_bounds_exact=True,counts=counts,nonintersection_proved=False,native_centre_equivalence_claimed=False,elapsed_s=time.monotonic()-start)
 (w/'independent-readback.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
if __name__=='__main__':main()
