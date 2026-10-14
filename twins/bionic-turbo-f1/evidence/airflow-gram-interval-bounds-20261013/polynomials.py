"""Exact polynomial areas and Gram minors; no geometric parameter sampling."""
import hashlib,json,math
from fractions import Fraction as F
from itertools import combinations
from pathlib import Path
from collections import defaultdict

def trim(p):
 p=list(p)
 while len(p)>1 and p[-1]==0:p.pop()
 return tuple(p)
def add(a,b):return trim([(a[i] if i<len(a) else 0)+(b[i] if i<len(b) else 0) for i in range(max(len(a),len(b)))])
def neg(a):return tuple(-x for x in a)
def sub(a,b):return add(a,neg(b))
def mul(a,b):
 r=[F(0)]*(len(a)+len(b)-1)
 for i,x in enumerate(a):
  for j,y in enumerate(b):r[i+j]+=x*y
 return trim(r)
def times(a,c):return trim([x*c for x in a])
def summ(a):
 r=(F(0),)
 for p in a:r=add(r,p)
 return r
def cross(a,b):return [sub(mul(a[(i+1)%3],b[(i+2)%3]),mul(a[(i+2)%3],b[(i+1)%3])) for i in range(3)]
def dot(a,b):return summ(mul(x,y) for x,y in zip(a,b))
def determinant(g):return dot(g[0],cross(g[1],g[2]))
def vector_add(a,b):return [add(x,y) for x,y in zip(a,b)]
def vector_sub(a,b):return [sub(x,y) for x,y in zip(a,b)]
def area(points):
 r=[(F(0),)]*3
 for a,b in zip(points,points[1:]+points[:1]):r=vector_add(r,cross(a,b))
 return [times(x,F(1,2)) for x in r]
def fan_area(points):
 mean=[times(summ(p[i] for p in points),F(1,len(points))) for i in range(3)];r=[(F(0),)]*3
 for a,b in zip(points,points[1:]+points[:1]):r=vector_add(r,cross(vector_sub(b,a),vector_sub(mean,a)))
 return [times(x,F(1,2)) for x in r]
def bernstein(p,a,b):
 n=len(p)-1
 power=[sum((p[j]*math.comb(j,k)*a**(j-k)*(b-a)**k for j in range(k,n+1)),F(0)) for k in range(n+1)]
 return [sum((power[k]*F(math.comb(i,k),math.comb(n,k)) for k in range(i+1)),F(0)) for i in range(n+1)]
def serialize(p):return [str(x) for x in p]
def main():
 w=Path(__file__).parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 manifest=Path('work/bionic-airflow-delivery-20261013-feasibility-bounds/file-manifest.json')
 for r in json.loads(manifest.read_text())['files']:assert sha(Path('work')/r['path'])==r['sha256']
 old=Path('work/bionic-feasibility-bounds-20261013');cert=json.loads((old/'certificate.json').read_text())
 for name,digest in json.loads((old/'readback.json').read_text())['dependencies'].items():
  p=Path(name);assert sha(p)==digest
  for r in json.loads(p.read_text())['files']:assert sha(Path('work')/r['path'])==r['sha256']
 s=json.loads(Path('work/bionic-buffered-transition-20261013/construction.json').read_text());sys=json.loads(Path('work/bionic-joint-constraints-20261013/system.json').read_text())
 u,end=map(F,cert['domain']);binding={b['point']:b for b in sys['coordinate_bindings']}
 points=[]
 for i,p in enumerate(s['vertices']):
  b=binding.get(i)
  if b and b['variable']=='v':points.append([(F(b['x_coefficient'])*u,F(b['x_coefficient'])*(end-u)),(F(b['y_coefficient'])*u,F(b['y_coefficient'])*(end-u)),(F(b['z_exact']),)])
  else:points.append([(F(x),) for x in p])
 fs=[];reg=defaultdict(list)
 for c,b in enumerate(s['blocks']):
  n=4 if s['stages'][c]=='buffer' else 3;lo,hi=b[:n],b[4:4+n]
  faces=[lo[::-1],hi]+[[lo[i],lo[(i+1)%n],hi[(i+1)%n],hi[i]] for i in range(n)]
  fs.append(faces)
  for f in faces:reg[tuple(sorted(f))].append(c)
 models=[];face_checks=0
 for choice in cert['selected'][2:]:
  cell=choice['cell'];faces=[f for f in fs[cell] if len(reg[tuple(sorted(f))])==2];areas=[]
  for f in faces:
   p=[points[i] for i in f];a=area(p);assert a==fan_area(p);areas.append(a);face_checks+=1
  gram=[[summ(mul(a[i],a[j]) for a in areas) for j in range(3)] for i in range(3)]
  minors=[dot(areas[i],cross(areas[j],areas[k])) for i,j,k in combinations(range(len(areas)),3)]
  cb=summ(mul(p,p) for p in minors);direct=determinant(gram);assert direct==cb
  models.append(dict(cell=cell,faces=faces,area_components=[[serialize(p) for p in a] for a in areas],norm_squared=[serialize(dot(a,a)) for a in areas],minors=[serialize(p) for p in minors],gram_determinant=serialize(cb)))
 # Exact scalar examples at three scales, including rank deficiency.
 refs=0
 for vectors in (((1,0,0),(0,1,0),(0,0,1)),((1,2,0),(0,1,3),(2,0,1),(3,-1,2)),((1,0,0),(0,1,0),(1,1,0))):
  for scale in (F(1),F(1,1000),F(1,1000000)):
   a=[[(F(x)*scale,) for x in v] for v in vectors];g=[[summ(mul(v[i],v[j]) for v in a) for j in range(3)] for i in range(3)]
   m=[dot(a[i],cross(a[j],a[k])) for i,j,k in combinations(range(len(a)),3)]
   assert determinant(g)==summ(mul(p,p) for p in m);refs+=1
 out=dict(source_sha256=sha(Path(__file__)),parent_manifest_sha256=sha(manifest),parent_certificate_sha256=sha(old/'certificate.json'),domain=[str(u),str(end)],parameter='v = u + (q_ext-u)*t; u fixed to archived q_m',models=models,identities_verified=dict(native_area_polynomial_equalities=face_checks,gram_polynomial_equalities=len(models),rational_gram_references=refs),no_new_ratio_evaluated=True)
 (w/'models.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out['identities_verified']))
if __name__=='__main__':main()
