"""Export every source facet to binary STL with a complete rounding bound."""
import argparse
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path
import resource
import signal


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--mesh',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True);resource.setrlimit(resource.RLIMIT_CPU,(120,130));signal.alarm(150)
    import numpy as np
    if float(np.float32(16777217.))!=16777216.:raise ValueError('Expected binary32 rounding control differs')
    with a.mesh.open()as stream:nv,nf=map(int,stream.readline().split());v=np.loadtxt(stream,max_rows=nv);f=np.loadtxt(stream,dtype=np.int64)
    if v.shape!=(nv,3)or f.shape!=(nf,3)or not np.isfinite(v).all():raise ValueError('Whole finite source rosters required')
    rounded=v.astype(np.float32).astype(np.float64);changed=np.flatnonzero(np.any(rounded!=v,axis=1));maximum=max((sum(abs(Q(float(x))-Q(float(y)))for x,y in zip(v[i],rounded[i]))for i in changed),default=Q(0))
    triangles=rounded[f];normal=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]);length=np.linalg.norm(normal,axis=1)
    if not np.all(length>0)or len(np.unique(rounded,axis=0))!=nv:raise ValueError('STL rounding collapses geometry; no silent cleanup allowed')
    dtype=np.dtype([('normal','<f4',(3,)),('points','<f4',(3,3)),('attribute','<u2')]);records=np.zeros(nf,dtype=dtype);records['normal']=normal/length[:,None];records['points']=triangles
    target=a.output/'carrier-study.stl'
    with target.open('wb')as stream:stream.write(b'993 carrier computational study; units mm; not manufacturing release'.ljust(80,b' '));stream.write(int(nf).to_bytes(4,'little'));stream.write(records.tobytes())
    with target.open('rb')as stream:
        header=stream.read(84);readback=np.frombuffer(stream.read(),dtype=dtype)['points']
    if int.from_bytes(header[80:84],'little')!=nf or not np.array_equal(readback.astype(np.float64),triangles):raise ValueError('Complete STL triangle readback differs')
    report=dict(status='complete_binary_STL_export_with_bounded_rounding',vertices=nv,triangles=nf,changed_vertices=len(changed),exact_complete_rounding_L1_bound_mm=str(maximum),complete_rounding_L1_bound_mm=float(maximum),face_roster_and_order_unchanged=True,source_mesh_sha256=hashlib.sha256(a.mesh.read_bytes()).hexdigest(),output_SHA256=hashlib.sha256(target.read_bytes()).hexdigest(),worker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),units='mm',geometry_adopted=False,surface_audit_pending=True)
    (a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');signal.alarm(0);print(json.dumps(report))

if __name__=='__main__':main()
