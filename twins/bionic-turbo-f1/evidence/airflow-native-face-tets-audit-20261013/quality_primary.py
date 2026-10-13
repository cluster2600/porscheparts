"""Mathematical source quality, native guard and exact final additive quotient."""
import hashlib,importlib.util,math
from pathlib import Path
from fractions import Fraction as F

def load(name,path,digest):
 with path.open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==digest
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
h=load('tets_native_centred',Path('work/bionic-centre-interval-bounds-20261013/centred.py'),'4f366b9571c931fa8d4bf19e90e94c5bd77d0093c193a1e0de9caf1f3590361b')
b=h.b;I=b.I;Q=b.Q
ROOT=F(float('1e-150'));GREAT=F(float('1e15'));SMALL=F(float('1e-15'))
TOL_REAL=SMALL*SMALL;TOL_RN=F(float(TOL_REAL));TOL=(min(TOL_REAL,TOL_RN),max(TOL_REAL,TOL_RN))
def pair(x):return F(x.lo,Q),F(x.hi,Q)
def interval(a,z):return I(math.floor(a*Q),math.ceil(z*Q),True)
def divide(a,z,c,d):
 assert a<=z and c<=d
 if c<=0<=d:raise ZeroDivisionError('denominator contains zero')
 values=[x/y for x in (a,z) for y in (c,d)]
 return interval(min(values),max(values))
def ratio(x,y,add=F(0)):
 a,z=pair(x);c,d=pair(y);return divide(a,z,c+add,d+add)
def absolute_bounds(a,z):return max(F(0),a,-z),max(abs(a),abs(z))
def guard(a,z):
 lo,hi=absolute_bounds(a,z)
 if hi<ROOT:return 'degenerate'
 if lo>=ROOT:return 'regular'
 return 'unknown'
def clipped_radius(x):
 a,z=pair(x);assert a>=0
 return interval(min(a,GREAT),min(z,GREAT))
SQRT3=I(3).root();COEFFICIENT=ratio(I(8),I(9)*SQRT3)
def quality(points):
 origin,p1,p2,p3=points;a=b.minus(p1,origin);c=b.minus(p3,origin);v=b.minus(p2,origin)
 volume=b.dot(b.cross(a,v),c)*I(F(1,6))
 lam=b.dot(c,c)-b.dot(a,c);mu=b.dot(v,v)-b.dot(a,v)
 ba=b.cross(v,a);ca=b.cross(c,a);num=b.minus(b.mul(ba,lam),b.mul(ca,mu));den=b.dot(c,ba)
 branch=guard(*pair(den))
 if branch=='unknown':return None,branch
 if branch=='degenerate':radius=I(GREAT)
 else:
  correction=[ratio(x,den) for x in num];radius=b.norm(b.mul(b.plus(a,correction),I(F(1,2))))
 radius=clipped_radius(radius);base=COEFFICIENT*radius*radius.sq()
 result=ratio(volume,base,ROOT)
 return (den,volume,radius,result),branch

def classify(bounds,strict=False,tol=TOL):
 if bounds is None:return 'unknown'
 lo,hi=bounds
 if (lo>tol[1] if strict else lo>=tol[1]):return 'positive'
 if (hi<=tol[0] if strict else hi<tol[0]):return 'refused'
 return 'unknown'
