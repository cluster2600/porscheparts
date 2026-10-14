"""Exact endpoint checks for the integer interval kernel, not geometry samples."""
import hashlib,json,math
from fractions import Fraction as F
from pathlib import Path
from bounds import I,Q

checked=0
intervals=[(F(-3),F(2)),(F(1,3),F(2,3)),(F(-5,7),F(-1,7)),(F(1,10**20),F(2,10**20)),(F(0),F(0))]
for a,b in intervals:
 x=I(I(a).lo,I(b).hi,True)
 assert F(x.lo,Q)<=a<=b<=F(x.hi,Q)
 sq=x.sq();assert F(sq.lo,Q)<=min(a*a,b*b) and F(sq.hi,Q)>=max(a*a,b*b)
 root=sq.root();assert F(root.lo,Q)**2<=F(sq.lo,Q) and F(root.hi,Q)**2>=F(sq.hi,Q);checked+=3
 for c,d in intervals:
  y=I(I(c).lo,I(d).hi,True)
  for z,values in ((x+y,[a+c,b+d]),(x-y,[a-d,b-c]),(x*y,[a*c,a*d,b*c,b*d])):
   assert F(z.lo,Q)<=min(values)<=max(values)<=F(z.hi,Q);checked+=1
  if not c<=0<=d:
   z=x/y;values=[a/c,a/d,b/c,b/d];assert F(z.lo,Q)<=min(values)<=max(values)<=F(z.hi,Q);checked+=1
# Check a non-dyadic square root against integer inequalities, no float sqrt.
s=I(2).root();assert s.lo*s.lo<=2*Q*Q<=s.hi*s.hi;checked+=1
w=Path(__file__).parent
out={'exact_endpoint_checks':checked,'kernel_sha256':hashlib.sha256((w/'bounds.py').read_bytes()).hexdigest(),'no_ratio_samples':True}
(w/'arithmetic-readback.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
