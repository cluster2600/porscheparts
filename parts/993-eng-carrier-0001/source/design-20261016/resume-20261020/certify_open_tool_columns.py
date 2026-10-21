"""Exact full-facet exclusion from the open nominal tool-column interiors.

Planar contact at Z=4 remains contact, not an empty closed-set intersection.
This independent certificate addresses the open volume 4<Z<40, radius<12.5.
"""
import argparse
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path
import resource
import signal
import time


def clip_above(points,level):
    result=[]
    for p,q in zip(points,points[1:]+points[:1]):
        inside=p[2]>=level;other=q[2]>=level
        if inside:result.append(p)
        if inside!=other:
            t=(level-p[2])/(q[2]-p[2]);result.append(tuple(p[k]+t*(q[k]-p[k])for k in range(3)))
    return result


def squared_distance(polygon):
    # Projection of a convex clipped triangle stays convex, possibly degenerate.
    edges=list(zip(polygon,polygon[1:]+polygon[:1]))
    area=sum(p[0]*q[1]-p[1]*q[0]for p,q in edges)
    crosses=[p[0]*q[1]-p[1]*q[0]for p,q in edges]
    if area and(all(c>=0 for c in crosses)or all(c<=0 for c in crosses)):return Q(0)
    minimum=None
    for p,q in edges:
        u=[q[k]-p[k]for k in range(2)];norm=sum(x*x for x in u)
        t=max(Q(0),min(Q(1),-sum(p[k]*u[k]for k in range(2))/norm))if norm else Q(0)
        value=sum((p[k]+t*u[k])**2 for k in range(2));minimum=value if minimum is None else min(minimum,value)
    return minimum


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--mesh',type=Path,required=True);p.add_argument('--surface-audit',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True);resource.setrlimit(resource.RLIMIT_CPU,(120,130));signal.alarm(150);start=time.monotonic()
    import numpy as np
    audit=json.loads(a.surface_audit.read_text());digest=hashlib.sha256(a.mesh.read_bytes()).hexdigest()
    if audit['status']!='complete_surface_screen_passed'or audit['source_mesh_sha256']!=digest:raise ValueError('Complete matching surface audit required')
    # Analytic controls exercise polygon interior and edge minima, not samples.
    assert squared_distance([(Q(1),Q(-1)),(Q(1),Q(1)),(Q(2),Q(0))])==1
    assert squared_distance([(Q(-1),Q(-1)),(Q(1),Q(-1)),(Q(0),Q(1))])==0
    assert clip_above([(Q(0),Q(0),Q(3)),(Q(2),Q(0),Q(5)),(Q(0),Q(2),Q(5))],Q(4))
    with a.mesh.open()as stream:nv,nf=map(int,stream.readline().split());v=np.loadtxt(stream,max_rows=nv);faces=np.loadtxt(stream,dtype=np.int64)
    if v.shape!=(nv,3)or faces.shape!=(nf,3):raise ValueError('Complete roster differs')
    triangles=v[faces];global_max=float(v[:,2].max())
    if global_max>=40:raise ValueError('Need a separately proved exterior witness above all source geometry')
    results=[];radius=Q(25,2)
    for cx,cy in [(-50,-20),(-50,20),(50,-20),(50,20)]:
        # Coordinate comparisons use exact stored floats and exactly representable thresholds.
        eligible=(triangles[:,:,2].max(1)>4)&(triangles[:,:,0].min(1)<cx+12.5)&(triangles[:,:,0].max(1)>cx-12.5)&(triangles[:,:,1].min(1)<cy+12.5)&(triangles[:,:,1].max(1)>cy-12.5)
        checked=[];failures=[]
        for index in np.flatnonzero(eligible):
            points=[tuple(Q(float(x))for x in point)for point in triangles[index]];clipped=clip_above(points,Q(4));projection=[(point[0]-cx,point[1]-cy)for point in clipped];distance=squared_distance(projection)
            row=dict(triangle=int(index),clipped_polygon_xyz_Q=[[str(x)for x in point]for point in clipped],minimum_squared_radial_distance_mm2_Q=str(distance))
            checked.append(row)
            if distance<radius*radius:failures.append(int(index))
        results.append(dict(centre_XY_mm=[cx,cy],exactly_checked_facets=len(checked),facets=checked,failed_facets=failures,passed=not failures))
    passed=all(r['passed']for r in results)
    report=dict(status='complete_open_tool_column_exclusion_passed'if passed else'open_tool_column_exclusion_refused',source_mesh_sha256=digest,surface_audit_sha256=hashlib.sha256(a.surface_audit.read_bytes()).hexdigest(),worker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),triangles=nf,radius_mm=12.5,open_Z_interval_mm=[4,40],global_maximum_Z_mm=global_max,exterior_witness='Every column contains points above the global source Z maximum; no source facet crosses its connected open interior',planar_contact_allowed=True,original_closed_set_empty_test_reclassified=False,columns=results,elapsed_seconds=time.monotonic()-start)
    (a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');signal.alarm(0);print(json.dumps(dict(status=report['status'],facets=[r['exactly_checked_facets']for r in results],failed_facets=[r['failed_facets']for r in results])));return 0 if passed else 2

if __name__=='__main__':raise SystemExit(main())
