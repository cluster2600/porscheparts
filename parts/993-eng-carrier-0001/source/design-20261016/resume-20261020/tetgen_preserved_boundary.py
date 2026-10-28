"""Mesh the complete audited PLC with the pinned libigl TetGen backend.

No quality flag or automatic surface remeshing is requested. The returned
boundary must retain every input coordinate and unoriented triangle exactly.
This is a volume-mesh experiment, not mechanical admission.
"""
import hashlib
import json
from pathlib import Path
import time


def boundary_identity(v, f, vertices, boundary, np):
    lookup = {tuple(p): i for i, p in enumerate(vertices)}
    if len(lookup) != len(vertices):
        raise ValueError('Coincident separately indexed output vertices')
    mapped = np.array([lookup[tuple(p)] for p in v], dtype=np.int64)
    expected = np.sort(mapped[f], axis=1)
    observed = np.sort(boundary, axis=1)
    def rows(a):
        return a[np.lexsort((a[:, 2], a[:, 1], a[:, 0]))]
    return np.array_equal(rows(expected), rows(observed))


def main():
    import numpy as np
    from igl.copyleft.tetgen import tetrahedralize
    out = Path('/output')
    start = time.monotonic()
    flags = 'pYMQ'
    v0 = np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]])
    f0 = np.array([[0,2,1],[0,1,3],[0,3,2],[1,2,3]], dtype=np.int64)
    cv, ct, cf, *rest = tetrahedralize(v0, f0, flags=flags)
    det = np.linalg.det(np.stack([cv[ct[:,j]]-cv[ct[:,0]] for j in (1,2,3)], axis=2))
    control = dict(flags=flags, vertices=len(cv), tetrahedra=len(ct), boundary_faces=len(cf),
                   positive_determinants=bool(np.all(det > 0)), volume=float(det.sum()/6),
                   exact_boundary_identity=boundary_identity(v0,f0,cv,cf,np), backend_status=int(rest[-1]))
    control['passed'] = (control['backend_status']==0 and control['positive_determinants']
                         and control['exact_boundary_identity'] and control['volume']==1/6)
    (out/'analytic-control.json').write_text(json.dumps(control,indent=2)+'\n')
    if not control['passed']:
        raise ValueError('Analytic tetrahedron control failed')
    mesh = Path('/input/mesh.mesh64')
    with mesh.open() as stream:
        nv,nf = map(int,stream.readline().split())
        v = np.loadtxt(stream,max_rows=nv)
        f = np.loadtxt(stream,dtype=np.int64)
    if v.shape!=(nv,3) or f.shape!=(nf,3) or not np.isfinite(v).all():
        raise ValueError('Input counts or coordinates differ')
    (out/'progress.json').write_text(json.dumps(dict(phase='tetrahedralize',flags=flags,
        input_vertices=nv,input_triangles=nf,source_sha256=hashlib.sha256(mesh.read_bytes()).hexdigest()),indent=2)+'\n')
    tv,tt,tf,*rest = tetrahedralize(v,f,flags=flags)
    np.savez_compressed(out/'volume.npz',vertices=tv,tetrahedra=tt,boundary=tf)
    same = boundary_identity(v,f,tv,tf,np)
    det = np.linalg.det(np.stack([tv[tt[:,j]]-tv[tt[:,0]] for j in (1,2,3)],axis=2))
    used = np.unique(tf)
    compact = np.full(len(tv),-1,dtype=np.int64)
    compact[used] = np.arange(len(used))
    target=out/'boundary.mesh64'
    with target.open('w') as stream:
        stream.write(f'{len(used)} {len(tf)}\n')
        np.savetxt(stream,tv[used],fmt='%.17g')
        np.savetxt(stream,compact[tf],fmt='%d')
    report=dict(status='preserved_boundary_volume_checkpoint' if same and np.all(det>0) and rest[-1]==0 else 'volume_checkpoint_refused',
        flags=flags,backend_status=int(rest[-1]),vertices=len(tv),tetrahedra=len(tt),boundary_faces=len(tf),
        exact_input_boundary_identity=bool(same),minimum_float_determinant_mm3=float(det.min()),
        positive_float_determinants=bool(np.all(det>0)),volume_mm3=float(det.sum()/6),
        elapsed_seconds=time.monotonic()-start,source_sha256=hashlib.sha256(mesh.read_bytes()).hexdigest(),
        output_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [out/'volume.npz',target]},
        mechanical_mesh_admitted=False,pending=['exact cell orientation and indexed connectivity','mechanical cases and refinement'])
    (out/'assessment.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
    return 0 if report['status']=='preserved_boundary_volume_checkpoint' else 2

if __name__=='__main__':
    raise SystemExit(main())
