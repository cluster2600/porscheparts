"""Shared fan tetrahedra and native-volume discrepancy; no embedding claim."""
import gzip,hashlib,importlib.util,json,subprocess,time
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
 w=Path(__file__).parent;start=time.monotonic();base='28f6b174d61906e27bfd407c58e3992e9a6ef881';e='twins/bionic-turbo-f1/evidence/airflow-parametric-boundary-20261013/'
 deps=json.loads(subprocess.check_output(['git','show',base+':'+e+'dependencies.json']))['manifests'];receipt=json.loads(subprocess.check_output(['git','show',base+':'+e+'archive-receipt.json']));deps['work/bionic-airflow-delivery-20261013-parametric-boundary/file-manifest.json']=receipt['manifest_sha256'];entries=0
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
 reg=defaultdict(list);cellfaces=[]
 for cid,block in enumerate(s['blocks']):
  n=4 if s['stages'][cid]=='buffer' else 3;lo=block[:n];hi=block[4:4+n]
  fs=[lo[::-1],hi]+[[lo[i],lo[(i+1)%n],hi[(i+1)%n],hi[i]] for i in range(n)];cellfaces.append(fs)
  for f in fs:reg[tuple(sorted(f))].append((cid,f))
 mean=lambda vv:[p.times(p.summ(x[k] for x in vv),F(1,len(vv))) for k in range(3)]
 minus=p.vector_sub
 bound=lambda x:[min(p.bernstein(x,a,b)),max(p.bernstein(x,a,b))]
 def item(poly):return dict(polynomial=p.serialize(poly),bounds=list(map(str,bound(poly))))
 faces={};counts=Counter();maxerr=F(0);tetminimum=None;cellminimum=None;worstface=None
 with gzip.open(w/'models.jsonl.gz','wt',compresslevel=3) as out:
  def emit(x):out.write(json.dumps(x,separators=(',',':'))+'\n')
  for key,occ in reg.items():
   f=list(canonical(occ[0][1]));signs=[]
   for cid,g in occ:
    sign=1 if canonical(g)==tuple(f) else -1
    assert sign==1 or canonical(g[::-1])==tuple(f);signs.append([cid,sign])
   assert len(occ)==1 or signs[0][1]==-signs[1][1]
   pts=[points[i] for i in f];c=mean(pts);areas=[];centres=[];norms=[]
   for x,y in zip(pts,pts[1:]+pts[:1]):
    aa=[p.times(z,F(1,2)) for z in p.cross(minus(x,c),minus(y,c))];gg=mean([c,x,y]);areas.append(aa);centres.append(gg)
    norm=p.dot(aa,aa);assert bound(norm)[0]>0;norms.append(item(norm));counts['face_triangles']+=1
   S=[p.summ(v[k] for v in areas) for k in range(3)];assert S==p.area(pts)
   flux=p.summ(p.dot(aa,minus(g,c)) for aa,g in zip(areas,centres))
   ep=[p.sub(flux,p.dot(S,minus(g,c))) for g in centres];eb=[bound(z) for z in ep];err=[min(z[0] for z in eb),max(z[1] for z in eb)]
   triple=(F(0),) if len(f)==3 else p.dot(minus(pts[1],pts[0]),p.cross(minus(pts[2],pts[0]),minus(pts[3],pts[0])))
   zero=all(z==0 for z in triple);counts['identically_planar' if zero else 'nonzero_coplanarity_polynomial']+=1
   bb=bound(triple)
   if not zero and (bb[0]>0 or bb[1]<0):counts['strict_nonplanarity_over_domain']+=1
   if max(map(abs,err))>maxerr:maxerr=max(map(abs,err));worstface=f
   faces[key]=(f,c,areas,centres,S,err)
   emit(dict(kind='face',face=f,occurrences=signs,coplanarity=item(triple),triangle_area_squared=norms,flux_error_components=[item(z) for z in ep],flux_error_bound=list(map(str,err))))
  for cid,fs in enumerate(cellfaces):
   seed=mean([points[i] for i in sorted(set(s['blocks'][cid]))]);vol=(F(0),);area_sum=[(F(0),)]*3;errs=[F(0),F(0)];tets=[]
   for face in fs:
    f,c,areas,centres,S,err=faces[tuple(sorted(face))];sgn=1 if canonical(face)==tuple(f) else -1
    for k,aa in enumerate(areas):
     six=p.times(p.dot(aa,minus(c,seed)),F(2*sgn));bb=bound(six)
     counts['positive_tetrahedra' if bb[0]>0 else 'negative_tetrahedra' if bb[1]<=0 else 'indeterminate_tetrahedra']+=1
     tetminimum=bb[0] if tetminimum is None else min(tetminimum,bb[0]);vol=p.add(vol,p.times(six,F(1,6)))
     tets.append(dict(face=f,edge=k,sign=sgn,**item(six)))
    area_sum=p.vector_add(area_sum,[p.times(z,F(sgn)) for z in S])
    oriented=err if sgn==1 else [-err[1],-err[0]]
    for j in (0,1):errs[j]+=oriented[j]/3
   assert all(all(z==0 for z in x) for x in area_sum)
   vb=bound(vol);cellminimum=vb[0] if cellminimum is None else min(cellminimum,vb[0]);assert vb[0]>0
   emit(dict(kind='cell',cell=cid,tetrahedra=tets,fan_signed_volume=item(vol),fan_minus_native_volume_bound=list(map(str,errs))))
   if cid%1024==0:print(json.dumps(dict(cell=cid,counts=counts)),flush=True)
 result=dict(source_sha256=sha(Path(__file__)),preflight_sha256=sha(w/'preflight.md'),derivation_sha256=sha(w/'derivation.md'),dependencies_sha256=sha(w/'dependencies.json'),models_sha256=sha(w/'models.jsonl.gz'),domain_v=domain,normalized_t=list(map(str,(a,b))),faces=len(faces),cells=len(cellfaces),counts=counts,minimum_six_volume_bound=str(tetminimum),minimum_cell_fan_volume_bound=str(cellminimum),maximum_face_flux_error_bound=str(maxerr),worst_flux_error_face=worstface,nonintersection_proved=False,native_centre_equivalence_claimed=False,native_executed=False,new_ratio_point=False,elapsed_s=time.monotonic()-start)
 (w/'readback.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
if __name__=='__main__':main()
