"""Independently check exact parent containment, area coverage, and closed topology."""
from fractions import Fraction as F
from pathlib import Path
from collections import Counter
import struct, json, sys, math

def read(path):
    raw=Path(path).read_bytes()
    assert raw[:8]==b'M64TRI1\0'
    nv,nf=struct.unpack_from('<QQ',raw,8)
    assert len(raw)==24+24*(nv+nf)
    points=list(struct.iter_unpack('<ddd',raw[24:24+24*nv]))
    faces=list(struct.iter_unpack('<QQQ',raw[24+24*nv:]))
    return points,faces

def sub(a,b): return tuple(x-y for x,y in zip(a,b))
def cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def dot(a,b): return sum(x*y for x,y in zip(a,b))
def area(a,b,c): return cross(sub(b,a),sub(c,a))

def verify(source,prefix):
    original,parents=read(source); rounded,faces=read(str(prefix)+'.bin')
    original=[tuple(map(F,p)) for p in original]
    lines=Path(str(prefix)+'.exact').read_text().splitlines()
    assert int(lines[0])==len(rounded)==len(lines)-1
    points=[tuple(map(F,line.split())) for line in lines[1:]]
    assert all(len(p)==3 for p in points)
    assert points[:len(original)]==original
    ids=[v[0] for v in struct.iter_unpack('<Q',Path(str(prefix)+'.parents').read_bytes())]
    bounds=list(struct.iter_unpack('<dd',Path(str(prefix)+'.intervals').read_bytes()))
    assert len(ids)==len(faces) and len(bounds)==3*len(points)
    for i,(p,q) in enumerate(zip(points,rounded)):
        for j,(exact,value) in enumerate(zip(p,q)):
            lo,hi=bounds[3*i+j]
            assert all(map(math.isfinite,(lo,hi,value)))
            assert F(lo)<=exact<=F(hi) and lo<=value<=hi
    totals=[[F(0)]*3 for _ in parents]; edges=Counter()
    for face,parent in zip(faces,ids):
        assert 0<=parent<len(parents) and len(set(face))==3
        a,b,c=(original[v] for v in parents[parent]); normal=area(a,b,c)
        assert dot(normal,normal)>0
        triangle=[points[v] for v in face]
        for p in triangle:
            assert dot(sub(p,a),normal)==0
            assert all(dot(area(x,y,p),normal)>=0 for x,y in ((a,b),(b,c),(c,a)))
        child=area(*triangle); assert dot(child,normal)>0
        totals[parent]=[x+y for x,y in zip(totals[parent],child)]
        for u,v in zip(face,face[1:]+face[:1]): edges[u,v]+=1
    assert all(count==1 and edges[v,u]==1 for (u,v),count in edges.items())
    for face,total in zip(parents,totals): assert tuple(total)==area(*(original[v] for v in face))
    return {'vertices':len(points),'triangles':len(faces),'source_triangles':len(parents),'exact_parent_containment':True,'exact_oriented_area_coverage':True,'closed_oriented_edges':True,'rounding_intervals_verified':True}

if __name__=='__main__': print(json.dumps(verify(sys.argv[1],Path(sys.argv[2])),indent=2))
