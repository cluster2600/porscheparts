"""Read-only full indexed connectivity and exact rational C3D4 orientation audit."""
import argparse
from fractions import Fraction as F
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import signal
import time
import traceback


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--mesh',type=Path,required=True);p.add_argument('--boundary',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True);start=time.monotonic();root=Path(__file__).resolve().parents[5];helper=root/'twins/m64-cylinder-head/source/wholebody/audit_indexed_tetrahedra.py'
    report=dict(status='incomplete',source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [a.mesh,a.boundary,helper,Path(__file__)]},mechanical_mesh_admitted=False)
    resource.setrlimit(resource.RLIMIT_CPU,(140,145));signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('150 second bound')));signal.alarm(150)
    try:
        import numpy as np
        with np.load(a.mesh,allow_pickle=False)as data:v=data['vertices'].copy();cells=data['tetrahedra'].copy()
        with a.boundary.open()as stream:nv,nf=map(int,stream.readline().split());bv=np.loadtxt(stream,max_rows=nv);bf=np.loadtxt(stream,dtype=np.int64)
        if bv.shape!=(nv,3)or bf.shape!=(nf,3):raise ValueError('Boundary count differs')
        pointmap={tuple(p):i for i,p in enumerate(v)}
        if len(pointmap)!=len(v):raise ValueError('Coincident separately indexed volume vertices')
        stored=np.array([[pointmap[tuple(bv[j])]for j in face]for face in bf],dtype=np.int64)
        spec=importlib.util.spec_from_file_location('_carrier_full_indexed_volume',helper);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        metrics=module.connectivity_metrics(v,cells,stored);report['indexed_connectivity']=metrics
        exact=[tuple(F(float(x))for x in p)for p in v];minimum=None;negative=zero=0;volume=F(0)
        for i,cell in enumerate(cells):
            a0,b,c,d=[exact[j]for j in cell];u=[b[j]-a0[j]for j in range(3)];w=[c[j]-a0[j]for j in range(3)];z=[d[j]-a0[j]for j in range(3)]
            det=u[0]*(w[1]*z[2]-w[2]*z[1])-u[1]*(w[0]*z[2]-w[2]*z[0])+u[2]*(w[0]*z[1]-w[1]*z[0])
            minimum=det if minimum is None else min(minimum,det);negative+=int(det<0);zero+=int(det==0);volume+=det/6
            if (i+1)%5000==0:
                report['exact_progress']=dict(tetrahedra=i+1,negative=negative,zero=zero);(a.output/'progress.json').write_text(json.dumps(report,indent=2)+'\n')
        report['exact_orientation']=dict(tetrahedra=len(cells),negative=negative,zero=zero,minimum_signed_determinant_mm3=str(minimum),total_signed_volume_mm3=str(volume),total_signed_volume_mm3_float=float(volume),coordinate_semantics='Exact dyadic Fractions of every stored binary64 coordinate')
        passed=(not negative and not zero and metrics['tetra_connected_components']==1 and metrics['boundary_matches']and metrics['repeated_node_tetrahedra']==0)
        report['status']='full_exact_orientation_and_indexed_volume_screens_passed'if passed else'volume_screen_refused'
        report['pending']=['global surface-envelope distance','complete protected-interface validation','T10 conversion and mechanical cases']
    except Exception as error:report['failure']=dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc())
    finally:signal.alarm(0);report['elapsed_seconds']=time.monotonic()-start;(a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report));return 0 if report['status']=='full_exact_orientation_and_indexed_volume_screens_passed'else 2

if __name__=='__main__':raise SystemExit(main())
