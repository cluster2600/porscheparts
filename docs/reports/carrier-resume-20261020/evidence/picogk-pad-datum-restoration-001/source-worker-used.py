"""Restore nominal central pad planes with an explicitly bounded vertex map.

The unchanged face roster gives a continuous piecewise affine correspondence.
Its two-way complete-surface L1 displacement is bounded by the largest exact
vertex displacement. This certifies only this edit, not earlier voxelization.
"""
import argparse
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path
import resource
import signal
import time


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--mesh',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise ValueError('Fresh output required')
    args.output.mkdir(parents=True)
    resource.setrlimit(resource.RLIMIT_CPU,(120,130))
    signal.alarm(150)
    start=time.monotonic()
    import numpy as np
    with args.mesh.open()as stream:
        nv,nf=map(int,stream.readline().split())
        vertices=np.loadtxt(stream,max_rows=nv)
        faces=np.loadtxt(stream,dtype=np.int64)
    if vertices.shape!=(nv,3)or faces.shape!=(nf,3):raise ValueError('Whole input roster differs')
    changed=vertices.copy()
    # C2 quintic falloff around the declared nominal planes and pad X extent.
    def falloff(values,inner,outer):
        t=np.clip((values-inner)/(outer-inner),0.,1.)
        return 1.-t*t*t*(10.+t*(-15.+6.*t))
    delta=vertices[:,2]-np.where(vertices[:,2]>=0.,4.,-4.)
    influence=falloff(np.abs(delta),.005,.015)*falloff(np.abs(vertices[:,0]),65.,67.)
    changed[:,2]-=delta*influence
    ids=np.flatnonzero(changed[:,2]!=vertices[:,2])
    costs=[abs(Q(float(changed[i,2]))-Q(float(vertices[i,2])))for i in ids]
    maximum=max(costs,default=Q(0))
    if maximum>Q(1,100):raise ValueError('Fixed 0.01 mm edit budget exceeded')
    # Refuse rather than drop collapsed images or silently alter face coverage.
    if len(np.unique(changed,axis=0))!=nv:raise ValueError('Projection creates coincident vertices; coverage-preserving weld required')
    triangles=changed[faces]
    normals=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
    if np.any(np.all(normals==0.,axis=1)):raise ValueError('Projection creates a collapsed triangle; no facet may be silently deleted')
    target=args.output/'surface.mesh64'
    with target.open('w')as stream:
        stream.write(f'{nv} {nf}\n');np.savetxt(stream,changed,fmt='%.17g');np.savetxt(stream,faces,fmt='%d')
    ledger=args.output/'changed-vertices.json'
    ledger.write_text(json.dumps([dict(vertex=int(i),before_Z_mm=float(vertices[i,2]),after_Z_mm=float(changed[i,2]),exact_L1_mm=str(cost))for i,cost in zip(ids,costs)],indent=2)+'\n')
    report=dict(status='nominal_pad_vertex_map_completed_surface_checks_pending',source_sha256=hashlib.sha256(args.mesh.read_bytes()).hexdigest(),worker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),output_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),ledger_sha256=hashlib.sha256(ledger.read_bytes()).hexdigest(),vertices=nv,triangles=nf,changed_vertices=len(ids),planes_Z_mm=[-4,4],full_projection_band_mm=.005,zero_projection_band_mm=.015,full_projection_absolute_X_mm=65,zero_projection_absolute_X_mm=67,exact_complete_edit_L1_bound_mm=str(maximum),complete_edit_L1_bound_mm=float(maximum),face_roster_unchanged=True,source_voxelization_error_certified=False,geometry_adopted=False,elapsed_seconds=time.monotonic()-start)
    (args.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n')
    signal.alarm(0)
    print(json.dumps(report))

if __name__=='__main__':main()
