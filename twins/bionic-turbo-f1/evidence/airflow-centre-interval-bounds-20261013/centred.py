"""Centered native moments, with the immutable 160-bit interval kernel."""
import hashlib, importlib.util
from fractions import Fraction as F
from pathlib import Path
p=Path('work/bionic-feasibility-bounds-20261013/bounds.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='45fc2623585df193957eb9dc876d5f47bccb4e5a3dea0fe5fd5ca552ea67d557'
spec=importlib.util.spec_from_file_location('pinned_dyadic_kernel',p)
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
I=b.I

def face(q):
    seed=b.mean(q);area=[I(0) for _ in range(3)];moment=area[:];weight=I(0)
    for a,c in zip(q,q[1:]+q[:1]):
        cr=b.cross(b.minus(c,a),b.minus(seed,a));mag=b.norm(cr)
        area=b.plus(area,cr);weight+=mag
        offset=b.minus(b.plus(a,c),b.mul(seed,2))
        moment=b.plus(moment,b.mul(offset,mag))
    if weight.lo<=0:raise ZeroDivisionError
    return b.plus(seed,[x/(3*weight) for x in moment]),b.mul(area,F(1,2))

def cell(geoms):
    seed=b.mean([c for c,a in geoms]);vol=I(0);moment=[I(0) for _ in range(3)]
    for c,a in geoms:
        offset=b.minus(c,seed);v=b.dot(a,offset)/3
        vol+=v;moment=b.plus(moment,b.mul(offset,v))
    if vol.lo<=0:raise ZeroDivisionError
    return b.plus(seed,[3*x/(4*vol) for x in moment]),vol
