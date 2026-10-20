"""Improve union slivers by bounded diagonal flips of convex projected quads.

Both triangulations project onto the same convex quadrilateral. Subtracting
the plane through the first three vertices leaves residual heights 0,0,0,h.
Their height functions therefore differ by at most |h|. Exact rational signs
and residuals give a complete bidirectional L1 surface bound for each flip.
"""
import argparse
from fractions import Fraction as F
import hashlib
import importlib.util
import json
from pathlib import Path
import time


def flip_bound(points):
    a,b,c,d=[tuple(F(float(x))for x in p)for p in points]
    u=[b[i]-a[i]for i in range(3)];v=[c[i]-a[i]for i in range(3)]
    n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];axis=max(range(3),key=lambda i:abs(n[i]))
    if not n[axis]:raise ValueError('Degenerate source face')
    ij=[i for i in range(3)if i!=axis]
    def orient(p,q,r):return(q[ij[0]]-p[ij[0]])*(r[ij[1]]-p[ij[1]])-(q[ij[1]]-p[ij[1]])*(r[ij[0]]-p[ij[0]])
    signs=[orient(a,b,c),orient(a,b,d),orient(c,d,a),orient(c,d,b)]
    if signs[0]*signs[1]>=0 or signs[2]*signs[3]>=0:raise ValueError('Projected diagonals do not cross strictly')
    h=sum(n[i]*(d[i]-a[i])for i in range(3))/n[axis]
    return abs(h),dict(projection_dropped_axis=axis,exact_orientation_determinants=[str(x)for x in signs],exact_fourth_vertex_residual_mm=str(h))


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--mesh',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True);start=time.monotonic()
    import numpy as np
    spec=importlib.util.spec_from_file_location('_flip_geometry',Path(__file__).with_name('certified_patch_collapse.py'));base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
    with a.mesh.open()as stream:nv,nf=map(int,stream.readline().split());v=np.loadtxt(stream,max_rows=nv);f=np.loadtxt(stream,dtype=np.int64)
    if f.shape!=(nf,3):raise ValueError('Input face count differs')
    report=dict(status='incomplete',source_sha256=hashlib.sha256(a.mesh.read_bytes()).hexdigest(),steps=[],scope='Full rounded exact-union mesh; each accepted operation has a complete local surface-displacement bound')
    spent=F(0)
    try:
        while True:
            q=base.ratios(v,f,np);bad=np.flatnonzero(q<.001)
            if not len(bad):break
            edges={tuple(sorted((int(t[j]),int(t[(j+1)%3]))))for t in f[bad]for j in range(3)};needed={x for e in edges for x in e};hit=np.flatnonzero(np.any(np.isin(f,list(needed)),axis=1));adj={x:set()for x in needed}
            for k in hit:
                for x in f[k]:
                    if int(x)in adj:adj[int(x)].add(int(k))
            choice=None
            for x,y in edges:
                ids=sorted(adj[x]&adj[y])
                if len(ids)!=2:continue
                t=f[ids[0]].tolist();a0,b0=x,y
                if t[(t.index(a0)+1)%3]!=b0:a0,b0=b0,a0
                c=next(int(z)for z in f[ids[0]]if z not in[x,y]);d=next(int(z)for z in f[ids[1]]if z not in[x,y])
                if c==d or np.any(np.any(f==c,axis=1)&np.any(f==d,axis=1)):continue
                new=np.array([(c,d,b0),(d,c,a0)]);quality=base.ratios(v,new,np)
                if not np.isfinite(quality).all()or np.any(quality==0):continue
                before=int((q[ids]<.001).sum());after=int((quality<.001).sum())
                if after>=before:continue
                try:cost,proof=flip_bound(v[[a0,b0,c,d]])
                except ValueError:continue
                if spent+cost>F(.06):continue
                score=(cost/F(before-after),cost,len(bad)-before+after,ids)
                if choice is None or score[:3]<choice[0][:3]:choice=(score,new,proof,[a0,b0,c,d])
            if choice is None:report['remaining_needles']=len(bad);break
            (score,new,proof,vertices)=choice;_,cost,count,ids=score;old=f[ids].copy();f[ids]=new;spent+=cost
            report['steps'].append(dict(face_ids=ids,old_triangles=old.tolist(),new_triangles=new.tolist(),quad_vertices=vertices,quad_points_mm=v[vertices].tolist(),proof=proof,L1_bound_mm=str(cost),accumulated_L1_bound_mm=str(spent),needles_after=count))
            (a.output/'progress.json').write_text(json.dumps(report,indent=2)+'\n')
        target=a.output/'union.mesh64'
        with target.open('w')as stream:stream.write(f'{len(v)} {len(f)}\n');np.savetxt(stream,v,fmt='%.17g');np.savetxt(stream,f,fmt='%d')
        report.update(status='all_needles_removed_with_bounded_flips'if not report.get('remaining_needles')else'bounded_flips_partial',flip_L1_bound_mm=str(spent),flip_L1_bound_mm_float=float(spent),output_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),minimum_triangle_ratio=float(base.ratios(v,f,np).min()),independent_full_audit_pending=True)
    finally:report['elapsed_seconds']=time.monotonic()-start;(a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k]for k in ['status','flip_L1_bound_mm_float','minimum_triangle_ratio']}))

if __name__=='__main__':main()
