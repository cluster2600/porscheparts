"""Audit the complete rounded CGAL union and bound every coordinate conversion."""
from fractions import Fraction as F
import hashlib
import importlib.util
import json
from pathlib import Path


def main():
    import numpy as np
    import igl.predicates
    exact=Path('/input/union.exact');rounded=Path('/input/union.mesh64');out=Path('/output');maximum=F(0)
    with exact.open()as e,rounded.open()as r:
        header=e.readline();nv,nf=map(int,header.split())
        if r.readline()!=header:raise ValueError('Header differs')
        vertices=[]
        for _ in range(nv):
            q=[F(x)for x in e.readline().split()];v=[float(x)for x in r.readline().split()]
            if len(q)!=3 or len(v)!=3:raise ValueError('Coordinate count differs')
            maximum=max(maximum,sum(abs(a-F(b))for a,b in zip(q,v)));vertices.append(v)
        faces=[]
        for _ in range(nf):
            a=e.readline();b=r.readline()
            if a!=b:raise ValueError('Triangle identity differs')
            faces.append([int(x)for x in b.split()])
        if e.read().strip()or r.read().strip():raise ValueError('Unexpected trailing data')
    v=np.asarray(vertices);f=np.asarray(faces)
    spec=importlib.util.spec_from_file_location('_exact_union_topology','/source/audit.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    topology=m.topology(v,f);found,pairs,_=igl.predicates.find_self_intersections(v,f,False)
    (out/'self-intersection-pairs.json').write_text(json.dumps(np.asarray(pairs).tolist())+'\n')
    failures=[k for k in ['boundary_edges','nonmanifold_edges','inconsistent_orientation_edges','degenerate_triangles','needle_triangles']if topology[k]]
    if found or len(pairs):failures.append('self_intersections')
    if topology['connected_components']!=1:failures.append('connected_components')
    if topology['volume_mm3']<=0:failures.append('nonpositive_volume')
    report=dict(status='rounded_union_surface_screen_passed'if not failures else'rounded_union_surface_screen_refused',topology=topology,self_intersection_pairs=len(pairs),failures=failures,retained_needle_ratio_threshold=.001,exact_to_rounded_complete_surface_L1_bound_mm=str(maximum),exact_to_rounded_complete_surface_L1_bound_mm_float=float(maximum),source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [exact,rounded,Path(__file__),Path('/source/audit.py')]},mechanical_mesh_admitted=False)
    (out/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
