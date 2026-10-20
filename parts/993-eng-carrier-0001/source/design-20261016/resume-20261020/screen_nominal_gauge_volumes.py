"""Full-solid nominal clearance tests with exactly postchecked enclosing prisms.

Each smooth circular gauge is enclosed by its actual stored polygon: every
side-plane squared distance is checked as a Fraction. Empty intersections are
scoped numerical volume screens, not unchanged-surface or fitment certificates.
"""
import argparse
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import resource
import signal
import sys
import time
import traceback


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--mesh',type=Path,required=True);p.add_argument('--native-site',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True);start=time.monotonic();report=dict(status='incomplete',tests=[],source_interfaces_unchanged=False,geometry_adopted=False,scope='Nominal full gauge-volume intersections only; not measured fit or all-dimensional CAD equality')
    resource.setrlimit(resource.RLIMIT_CPU,(480,500));signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('180 second clearance worker bound')));signal.alarm(180)
    try:
        sys.path.insert(0,str(a.native_site.resolve()))
        import numpy as np
        import manifold3d as m
        with a.mesh.open()as stream:nv,nf=map(int,stream.readline().split());v=np.loadtxt(stream,max_rows=nv);faces=np.loadtxt(stream,dtype=np.uint64)
        body=m.Manifold(m.Mesh64(v.astype(np.float64),faces))
        if body.status()!=m.Error.NoError or body.num_tri()!=nf:raise ValueError('Whole source Manifold construction differs')
        def gauge(radius,centre,axis,lo,hi):
            n=128;outer=radius/math.cos(math.pi/n)*(1+1e-12);shape=m.Manifold.cylinder(hi-lo,outer,circular_segments=n,center=False)
            if axis==1:shape=shape.rotate((90,0,0)).translate((centre[0],hi,centre[2]));radial=[0,2]
            else:shape=shape.translate((centre[0],centre[1],lo));radial=[0,1]
            vertices=np.asarray(shape.to_mesh64().vert_properties)[:,:3];projected=np.unique(vertices[:,radial],axis=0);points=[[F(float(p[k]))-F(centre[radial[k]])for k in range(2)]for p in projected];points.sort(key=lambda p:math.atan2(float(p[1]),float(p[0])))
            if len(points)!=n:raise ValueError('Expected all polygon vertices')
            minimum=None
            for i,p0 in enumerate(points):
                p1=points[(i+1)%n];u=[p1[j]-p0[j]for j in range(2)];cross=p0[0]*p1[1]-p0[1]*p1[0];norm=sum(x*x for x in u)
                if cross<=0 or not norm:raise ValueError('Nonconvex or incorrectly ordered gauge polygon')
                squared=cross*cross/norm;minimum=squared if minimum is None else min(minimum,squared)
            if minimum<F(radius)**2:raise ValueError('Actual stored polygon fails to enclose the smooth gauge')
            if F(float(vertices[:,axis].min()))>F(lo)or F(float(vertices[:,axis].max()))<F(hi):raise ValueError('Axial gauge coverage differs')
            return shape,dict(radial_axis_indices=radial,centre_mm=centre,target_radius_mm=radius,axial_interval_mm=[lo,hi],polygon_segments=n,minimum_exact_squared_apothem_mm2=str(minimum),true_circular_gauge_enclosed=True)
        def test(name,radius,centre,axis,lo,hi,expected_empty):
            shape,proof=gauge(radius,centre,axis,lo,hi);common=m.Manifold.batch_boolean([body,shape],m.OpType.Intersect);count=common.num_tri();volume=common.volume();row=dict(name=name,expected_empty=expected_empty,result_status=str(common.status()),intersection_triangles=count,intersection_volume_mm3=volume,gauge_proof=proof,passed=common.status()==m.Error.NoError and((count==0)if expected_empty else(count>0 and volume>0)))
            report['tests'].append(row);(a.output/'progress.json').write_text(json.dumps(report,indent=2)+'\n')
            if count:
                mesh=common.to_mesh64();points=np.asarray(mesh.vert_properties)[:,:3];tri=np.asarray(mesh.tri_verts)
                with(a.output/(name+'-intersection.mesh64')).open('w')as stream:stream.write(f'{len(points)} {len(tri)}\n');np.savetxt(stream,points,fmt='%.17g');np.savetxt(stream,tri,fmt='%d')
        test('positive_control_central_annulus',6.,[-50.,-20.,0.],2,-3.5,3.5,False)
        test('positive_control_end_annulus',7.,[-280.,0.,0.],1,-22.,22.,False)
        for i,(x,y)in enumerate([(-50.,-20.),(-50.,20.),(50.,-20.),(50.,20.)]):
            test(f'central_shank_{i}',5.,[x,y,0.],2,-100.,100.,True)
            test(f'tool_column_{i}',12.5,[x,y,0.],2,4.,40.,True)
        for i,x in enumerate([-280.,280.]):test(f'end_shank_{i}',6.5,[x,0.,0.],1,-100.,100.,True)
        passed=all(row['passed']for row in report['tests']);report.update(status='all_nominal_gauge_volume_screens_passed'if passed else'nominal_gauge_volume_screen_refused',source_mesh_sha256=hashlib.sha256(a.mesh.read_bytes()).hexdigest(),worker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),full_source_triangles=nf)
    except BaseException as error:report['failure']=dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc());raise
    finally:signal.alarm(0);report['elapsed_seconds']=time.monotonic()-start;(a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],tests=[dict(name=r['name'],passed=r['passed'],intersection_triangles=r['intersection_triangles'])for r in report['tests']])));return 0 if passed else 2

if __name__=='__main__':raise SystemExit(main())
