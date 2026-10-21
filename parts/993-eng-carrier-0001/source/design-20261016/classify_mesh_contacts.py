"""Classify retained triangle-pair reports using exact IEEE754 rational geometry.

This does not replace pair detection. Only the simplex already shared by node
indices can be ignored; adjacent pairs that cross beyond it remain rejected.
"""
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path


def subtract(a,b):return tuple(x-y for x,y in zip(a,b))
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def project(point,axis):return tuple(v for i,v in enumerate(point) if i!=axis)
def orient(a,b,p):return (b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])


def inside(point,triangle):
    normal=cross(subtract(triangle[1],triangle[0]),subtract(triangle[2],triangle[0]))
    axis=max(range(3),key=lambda k:abs(normal[k]))
    vertices=[project(p,axis) for p in triangle];p=project(point,axis)
    orientation=orient(*vertices)
    return all(orient(vertices[i],vertices[(i+1)%3],p)*orientation>=0 for i in range(3))


def clip_coplanar(a,b,axis):
    """Exact Sutherland-Hodgman clipping of two nondegenerate triangles."""
    polygon=[project(p,axis) for p in a];boundary=[project(p,axis) for p in b]
    sign=1 if orient(*boundary)>0 else -1
    for i in range(3):
        result=[];start=polygon[-1] if polygon else None
        for end in polygon:
            ds=sign*orient(boundary[i],boundary[(i+1)%3],start)
            de=sign*orient(boundary[i],boundary[(i+1)%3],end)
            if (de>=0)!=(ds>=0):
                fraction=ds/(ds-de)
                result.append(tuple(x+fraction*(y-x) for x,y in zip(start,end)))
            if de>=0:result.append(end)
            start=end
        polygon=result
    return list(dict.fromkeys(polygon))


def intersection(a,b):
    na=cross(subtract(a[1],a[0]),subtract(a[2],a[0]))
    nb=cross(subtract(b[1],b[0]),subtract(b[2],b[0]))
    if not any(na) or not any(nb):return {'kind':'exact_degenerate_triangle','points':[]}
    if all(dot(na,subtract(p,a[0]))==0 for p in b):
        axis=max(range(3),key=lambda k:abs(na[k]));points=clip_coplanar(a,b,axis)
        area=abs(sum(p[0]*q[1]-p[1]*q[0] for p,q in zip(points,points[1:]+points[:1])))/2 if points else Fraction(0)
        kind='coplanar_area' if area else ('segment' if len(points)>1 else 'point' if points else 'empty')
        return {'kind':kind,'points':points,'projection_axis':axis,'projected_area':area}
    points=[]
    for triangle,other,normal in ((a,b,nb),(b,a,na)):
        for p,q in zip(triangle,triangle[1:]+triangle[:1]):
            dp,dq=dot(normal,subtract(p,other[0])),dot(normal,subtract(q,other[0]))
            if not dp and inside(p,other):points.append(p)
            if dp*dq<0:
                fraction=dp/(dp-dq);point=tuple(x+fraction*(y-x) for x,y in zip(p,q))
                if inside(point,other):points.append(point)
    points=list(dict.fromkeys(points))
    return {'kind':'segment' if len(points)>1 else 'point' if points else 'empty','points':points}


def on_shared_simplex(point,shared):
    if not shared:return False
    if len(shared)==1:return point==shared[0]
    assert len(shared)==2
    a,b=shared;direction=subtract(b,a)
    axis=max(range(len(direction)),key=lambda k:abs(direction[k]))
    if not direction[axis]:return point==a
    fraction=(point[axis]-a[axis])/direction[axis]
    return 0<=fraction<=1 and all(x==start+fraction*d for x,start,d in zip(point,a,direction))


def classify_pair(vertices,face_a,face_b):
    def point(index):
        values=vertices[index]
        if len(values)!=3 or not all(math.isfinite(float(v)) for v in values):raise ValueError('Invalid finite 3D coordinate')
        return tuple(Fraction(float(v)) for v in values)
    a,b=tuple(point(i) for i in face_a),tuple(point(i) for i in face_b)
    report=intersection(a,b);points=report.pop('points')
    shared_ids=sorted(set(face_a)&set(face_b));shared=[point(i) for i in shared_ids]
    if 'projection_axis' in report:shared=[project(p,report['projection_axis']) for p in shared]
    duplicate=len(shared_ids)==3
    allowed=not duplicate and report['kind']!='exact_degenerate_triangle' and all(on_shared_simplex(p,shared) for p in points)
    area=report.pop('projected_area',Fraction(0))
    return {**report,'shared_vertex_ids':[int(i) for i in shared_ids],
            'intersection_only_in_shared_topological_simplex':allowed,
            'duplicate_face':duplicate,'projected_intersection_area_mm2':float(area),
            'projected_area_exact_ratio':[str(area.numerator),str(area.denominator)],
            'intersection_points_float_mm':[[float(v) for v in p] for p in points],
            'intersection_points_exact_ratios':[[[str(v.numerator),str(v.denominator)] for v in p] for p in points]}


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit(mesh_path,pairs_path,output):
    import numpy as np
    mesh_path,pairs_path,output=map(Path,(mesh_path,pairs_path,output))
    assert not output.exists()
    with np.load(mesh_path,allow_pickle=False) as mesh,np.load(pairs_path,allow_pickle=False) as raw:
        vertices,faces,pairs=mesh['vertices'],mesh['faces'],raw['pairs']
        assert vertices.dtype==np.float64 and faces.ndim==2 and faces.shape[1]==3
        assert pairs.ndim==2 and pairs.shape[1]==2
        assert np.issubdtype(faces.dtype,np.integer) and np.issubdtype(pairs.dtype,np.integer)
        assert faces.min()>=0 and faces.max()<len(vertices) and (not len(pairs) or pairs.min()>=0 and pairs.max()<len(faces))
        rows=[{'face_pair':[int(i) for i in pair],**classify_pair(vertices,*faces[pair])} for pair in pairs]
    counts=Counter((row['kind'],row['intersection_only_in_shared_topological_simplex']) for row in rows)
    report={'source_sha256':sha(__file__),'mesh_npz_sha256':sha(mesh_path),'raw_pairs_npz_sha256':sha(pairs_path),
            'raw_detector_pair_count_unchanged':len(rows),
            'arithmetic':'Exact rational values of input IEEE754 float64 coordinates; no epsilon, welding, projection of vertices or mesh changes.',
            'scope':'Classifies only the retained detector pairs, not unreported pairs or global mesh topology.',
            'topological_simplex_only_contacts':sum(row['intersection_only_in_shared_topological_simplex'] for row in rows),
            'remaining_pair_count':sum(not row['intersection_only_in_shared_topological_simplex'] for row in rows),
            'categories':{str(key):value for key,value in counts.items()},'pairs':rows}
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='pairs'}));return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('mesh','pairs','output'):parser.add_argument(name,type=Path)
    args=parser.parse_args();audit(args.mesh,args.pairs,args.output)
