"""Separate sparse polynomial reconstruction from native fan areas."""
import hashlib,json,math
from fractions import Fraction as F
from itertools import permutations
from collections import defaultdict
from pathlib import Path

def total(polys):
 out={}
 for p in polys:
  for k,v in p.items():out[k]=out.get(k,F(0))+v
 return {k:v for k,v in out.items() if v}
def prod(a,b):
 return total([{i+j:x*y} for i,x in a.items() for j,y in b.items()])
def neg(a):return {k:-v for k,v in a.items()}
def difference(a,b):return total([a,neg(b)])
def times(a,c):return {k:v*c for k,v in a.items() if v*c}
def vector(a,b):return [difference(prod(a[(i+1)%3],b[(i+2)%3]),prod(a[(i+2)%3],b[(i+1)%3])) for i in range(3)]
def scalar(a,b):return total(prod(x,y) for x,y in zip(a,b))
def det(matrix):
 terms=[]
 for perm in permutations(range(3)):
  parity=sum(perm[i]>perm[j] for i in range(3) for j in range(i+1,3))
  term={0:F((-1)**parity)}
  for i in range(3):term=prod(term,matrix[i][perm[i]])
  terms.append(term)
 return total(terms)
def dense(p):return [p.get(i,F(0)) for i in range(max(p,default=0)+1)]
def from_strings(p):return {i:F(v) for i,v in enumerate(p) if F(v)}
def controls(p):
 p=dense(p);n=len(p)-1
 return [sum((p[j]*F(math.comb(i,j),math.comb(n,j)) for j in range(i+1)),F(0)) for i in range(n+1)]
def split(b,t):
 left=[b[0]];right=[b[-1]]
 while len(b)>1:
  b=[(1-t)*b[i]+t*b[i+1] for i in range(len(b)-1)];left.append(b[0]);right.append(b[-1])
 return left,right[::-1]
def restricted(p,a,b):
 # Work in normalized [0,1], cut at the upper endpoint, then its lower fraction.
 assert 0<=a<b<=1
 lower,_=split(controls(p),b)
 _,middle=split(lower,a/b)
 return middle

def main():
 w=Path(__file__).parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 model=json.loads((w/'models.json').read_text());old=Path('work/bionic-feasibility-bounds-20261013')
 assert sha(old/'certificate.json')==model['parent_certificate_sha256']
 parent=Path('work/bionic-airflow-delivery-20261013-feasibility-bounds/file-manifest.json')
 assert sha(parent)==model['parent_manifest_sha256']
 for row in json.loads(parent.read_text())['files']:assert sha(Path('work')/row['path'])==row['sha256']
 for path,digest in json.loads((old/'readback.json').read_text())['dependencies'].items():
  path=Path(path);assert sha(path)==digest
  for row in json.loads(path.read_text())['files']:assert sha(Path('work')/row['path'])==row['sha256']
 s=json.loads(Path('work/bionic-buffered-transition-20261013/construction.json').read_text());sy=json.loads(Path('work/bionic-joint-constraints-20261013/system.json').read_text())
 a,b=map(F,model['domain']);assert a==F(sy['archived_regression_point']['u']) and b==F(s['radial_ratios'][-1])
 bindings={x['point']:x for x in sy['coordinate_bindings']};points=[]
 for i,p in enumerate(s['vertices']):
  binding=bindings.get(i)
  if binding and binding['variable']=='v':points.append([{0:F(binding[key])*a,1:F(binding[key])*(b-a)} for key in ('x_coefficient','y_coefficient')]+[{0:F(binding['z_exact'])}])
  else:points.append([{0:F(x)} for x in p])
 templates=((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7));faces=[];reg=defaultdict(list)
 for cell,block in enumerate(s['blocks']):
  fs=[]
  for t in templates:
   f=[]
   for k in t:
    if not f or f[-1]!=block[k]:f.append(block[k])
   if f[-1]==f[0]:f.pop()
   if len(f)<3:continue
   fs.append(f);reg[tuple(sorted(f))].append(cell)
  faces.append(fs)
 verified_faces=0
 for m in model['models']:
  fs=[f for f in faces[m['cell']] if len(reg[tuple(sorted(f))])==2]
  assert {tuple(sorted(f)) for f in fs}=={tuple(sorted(f)) for f in m['faces']}
  got=[]
  for f in fs:
   ps=[points[i] for i in f];seed=[times(total(p[k] for p in ps),F(1,len(ps))) for k in range(3)]
   cr=[]
   for j,p in enumerate(ps):
    nxt=ps[(j+1)%len(ps)]
    cr.append(vector([difference(nxt[k],p[k]) for k in range(3)],[difference(seed[k],p[k]) for k in range(3)]))
   S=[times(total(v[k] for v in cr),F(1,2)) for k in range(3)]
   pos=next(i for i,oldf in enumerate(m['faces']) if set(f)==set(oldf))
   expected=[from_strings(x) for x in m['area_components'][pos]];assert S==expected
   assert scalar(S,S)==from_strings(m['norm_squared'][pos]);got.append(S);verified_faces+=1
  matrix=[[total(prod(S[i],S[j]) for S in got) for j in range(3)] for i in range(3)]
  assert det(matrix)==from_strings(m['gram_determinant'])
 # Exact Bernstein reference p(t)=t(1-t): controls [0,1/2,0].
 assert controls({1:F(1),2:F(-1)})==[0,F(1,2),0]
 assert restricted({1:F(1),2:F(-1)},F(1,4),F(3,4))==[F(3,16),F(5,16),F(3,16)]
 out=dict(source_sha256=sha(Path(__file__)),models_sha256=sha(w/'models.json'),native_fan_area_polynomials_verified=verified_faces,gram_determinant_polynomials_verified=len(model['models']),bernstein_analytic_references=2,source_payloads_verified=True,new_ratio_evaluated=False)
 (w/'models-readback.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
if __name__=='__main__':main()
