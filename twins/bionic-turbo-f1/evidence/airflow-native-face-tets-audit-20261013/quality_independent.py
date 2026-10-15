"""Independent 192-bit implementation of signed native tetrahedral quality."""
import hashlib,importlib.util
from pathlib import Path
from fractions import Fraction as F

def module(name,path,digest):
 with path.open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==digest
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
h=module('tets_independent_moments',Path('work/bionic-centre-interval-bounds-20261013/verify_centres_v2.py'),'a259f163405dec0cfb4f1b707698249ea9069de9b02a9db1835fb172f1a0b992');g=h.g
k=module('tets_dyadic192',Path('work/bionic-remaining-cell-bounds-20261013/dyadic192.py'),'f216b134a93a893b0c04bbe47671eb5ba497e4836e0e2a346220f0b14d83ac14');g.R=k.R
R=g.R;Q=1<<192;ROOT=F(float('1e-150'));GREAT=F(float('1e15'));SMALL=F(float('1e-15'))
TOL_REAL=SMALL**2;TOL_RN=F(float(TOL_REAL));TOL=tuple(sorted((TOL_REAL,TOL_RN)))
def pair(x):return x.a,x.b
def interval(a,b):return R(a,b)
def divide(a,b,c,d):
 if c<=0<=d:raise ZeroDivisionError('pole')
 assert a<=b and c<=d
 reciprocal=(1/d,1/c);products=[x*y for x in (a,b) for y in reciprocal]
 return R(min(products),max(products))
def ratio(x,y,add=F(0)):return divide(x.a,x.b,y.a+add,y.b+add)
def guard(a,b):
 if a<=0<=b:lo=F(0);hi=max(-a,b)
 elif b<0:lo=-b;hi=-a
 else:lo=a;hi=b
 return 'degenerate' if hi<ROOT else 'regular' if lo>=ROOT else 'unknown'
def clipped_radius(radius):
 assert radius.a>=0
 return R(min(radius.a,GREAT),min(radius.b,GREAT))
SQRT3=R(3).sqrt();COEFFICIENT=ratio(R(8),R(9)*SQRT3)
def quality(points):
 p,q,r,s=points;u=g.vsub(q,p);v=g.vsub(r,p);w=g.vsub(s,p)
 volume=g.inner(g.vectorcross(u,v),w)*R(F(1,6))
 l=g.inner(w,w)-g.inner(u,w);m=g.inner(v,v)-g.inner(u,v)
 vu=g.vectorcross(v,u);wu=g.vectorcross(w,u)
 numerator=g.vsub(g.scale(vu,l),g.scale(wu,m));denominator=g.inner(w,vu)
 kind=guard(denominator.a,denominator.b)
 if kind=='unknown':return None,kind
 if kind=='regular':
  centre_offset=g.scale(g.vadd(u,[ratio(x,denominator) for x in numerator]),R(F(1,2)));radius=g.length(centre_offset)
 else:radius=R(GREAT)
 radius=clipped_radius(radius);product=COEFFICIENT*radius*radius.square();qvalue=ratio(volume,product,ROOT)
 return (denominator,volume,radius,qvalue),kind

def classify(bounds,strict=False,tol=TOL):
 if bounds is None:return 'unknown'
 a,b=bounds
 if strict:
  if a>tol[1]:return 'positive'
  if b<=tol[0]:return 'refused'
 else:
  if a>=tol[1]:return 'positive'
  if b<tol[0]:return 'refused'
 return 'unknown'
