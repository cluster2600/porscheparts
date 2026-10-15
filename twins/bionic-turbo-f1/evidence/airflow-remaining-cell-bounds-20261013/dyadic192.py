"""Integer representation of the pinned Fraction-192 operation sequence."""
from fractions import Fraction as F
from math import isqrt
P=1<<192
def ceildiv(a,b):return -((-a)//b)
class R:
 __slots__=('lo','hi')
 def __init__(self,a,b=None):
  a=F(a);b=a if b is None else F(b)
  self.lo=a.numerator*P//a.denominator;self.hi=ceildiv(b.numerator*P,b.denominator);assert self.lo<=self.hi
 @classmethod
 def raw(cls,a,b):
  assert a<=b
  x=cls.__new__(cls);x.lo=a;x.hi=b;return x
 @property
 def a(self):return F(self.lo,P)
 @property
 def b(self):return F(self.hi,P)
 def __add__(x,y):
  y=r(y);return R.raw(x.lo+y.lo,x.hi+y.hi)
 __radd__=__add__
 def __neg__(x):return R.raw(-x.hi,-x.lo)
 def __sub__(x,y):return x+-r(y)
 def __rsub__(x,y):return r(y)+-x
 def __mul__(x,y):
  y=r(y);v=(x.lo*y.lo,x.lo*y.hi,x.hi*y.lo,x.hi*y.hi);return R.raw(min(v)//P,ceildiv(max(v),P))
 __rmul__=__mul__
 def __truediv__(x,y):
  y=r(y);assert not y.lo<=0<=y.hi
  # Reciprocal is rounded BEFORE the multiplication, exactly as in Fraction R.
  return x*R.raw(P*P//y.hi,ceildiv(P*P,y.lo))
 def square(x):
  low=0 if x.lo<=0<=x.hi else min(x.lo*x.lo,x.hi*x.hi);high=max(x.lo*x.lo,x.hi*x.hi)
  return R.raw(low//P,ceildiv(high,P))
 def sqrt(x):
  assert x.hi>=0
  low=isqrt(max(0,x.lo)*P);high=isqrt(x.hi*P)
  return R.raw(low,high+(high*high<x.hi*P))
def r(x):return x if isinstance(x,R) else R(x)
