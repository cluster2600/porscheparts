import hashlib,importlib.util,json
from fractions import Fraction as F
from pathlib import Path
from dyadic192 import R as Fast
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=Path('work/bionic-centre-interval-bounds-20261013/verify_centres_v2.py');assert sha(p)=='a259f163405dec0cfb4f1b707698249ea9069de9b02a9db1835fb172f1a0b992'
spec=importlib.util.spec_from_file_location('reference',p);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h);Slow=h.g.R
pairs=[(-7,-3),(-2,5),(0,0),(1,1),(1,3),(F(1,7),F(3,5)),(F(-1,3),F(-1,9))];count=0
def equal(a,b):
 global count
 assert (a.a,a.b)==(b.a,b.b);count+=1
for scale in (F(1),F(1,1000),F(1,1000000)):
 values=[(a*scale,b*scale) for a,b in pairs]
 for a,b in values:
  x,y=Slow(a,b),Fast(a,b);equal(x,y);equal(-x,-y);equal(x.square(),y.square())
  if b>=0:equal(x.sqrt(),y.sqrt())
  for c,d in values:
   z,t=Slow(c,d),Fast(c,d);equal(x+z,y+t);equal(x-z,y-t);equal(x*z,y*t)
   if not c<=0<=d:equal(x/z,y/t)
templates=((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7));geocount=0
def serial(x):
 if isinstance(x,(Slow,Fast)):return [str(x.a),str(x.b)]
 return [serial(v) for v in x]
for scale in (F(1),F(1,1000),F(1,1000000)):
 for shape in ('cube','pyramid','warped'):
  coords=((0,0,0),(1,0,0),(1,1,0),(0,1,0),(0,0,1),(1,0,1),(1,1,1),(0,1,1)) if shape=='cube' else (((0,0,0),(1,0,0),(1,1,0),(0,1,0),(F(1,2),F(1,2),1)) if shape=='pyramid' else ((-1,-1,1),(1,-1,-1),(1,1,1),(-1,1,-1)))
  fs=templates if shape=='cube' else ((0,3,2,1),(0,1,4),(1,2,4),(2,3,4),(3,0,4))
  results=[]
  for cls in (Slow,Fast):
   h.g.R=cls;points=[[cls(v*scale) for v in q] for q in coords]
   result=h.polygon(points) if shape=='warped' else h.moments([[points[j] for j in f] for f in fs]);results.append(serial(result))
  assert results[0]==results[1];geocount+=1
w=Path(__file__).parent;out=dict(source_sha256=sha(Path(__file__)),kernel_sha256=sha(w/'dyadic192.py'),proof_sha256=sha(w/'representation-proof.md'),arithmetic_exact_endpoint_comparisons=count,geometric_exact_endpoint_comparisons=geocount,fractional_bits=192,geometric_expressions_unchanged=True,new_ratio_point=False)
(w/'representation-readback.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
