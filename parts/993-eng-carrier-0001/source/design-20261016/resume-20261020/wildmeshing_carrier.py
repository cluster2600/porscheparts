"""Bounded-runtime volume-meshing trial on the complete exact-union float64 mesh.

The requested mesher envelope is a setting. Independent boundary, envelope,
protected-interface and mechanical checks remain separate acceptance stages.
"""
import argparse
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import resource
import time
import traceback


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--mesh',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True);start=time.monotonic();report=dict(status='incomplete',mechanical_mesh_admitted=False,source_sha256=hashlib.sha256(a.mesh.read_bytes()).hexdigest(),requested_surface_envelope_mm=.06,requested_ideal_edge_length_mm=9.,scope='Complete 603258-triangle polyhedral union; new C3D4 mesher study, not transfer of prior carrier mechanical results')
    if report['source_sha256']!='4ea8ad2c7fbf999b6f789fbaa8fcf5ba9f1c4fc5fa141f96fbf9a5ed46e435ef':raise ValueError('Exact-union input identity differs')
    resource.setrlimit(resource.RLIMIT_CPU,(590,595))
    for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[name]='1'
    try:
        import numpy as np
        import wildmeshing as wm
        with a.mesh.open()as stream:nv,nf=map(int,stream.readline().split());v=np.loadtxt(stream,max_rows=nv);f=np.loadtxt(stream,dtype=np.int64)
        if v.shape!=(nv,3)or f.shape!=(nf,3):raise ValueError('Complete input counts differ')
        diagonal=float(np.linalg.norm(v.max(axis=0)-v.min(axis=0)))
        settings=dict(max_threads=1,epsilon=.06/diagonal,edge_length_r=9./diagonal)
        report.update(input_nodes=nv,input_triangles=nf,bounding_box_diagonal_mm=diagonal,settings=settings,versions={n:metadata.version(n)for n in ['wildmeshing','numpy','svgwrite']},phase='construct_mesher')
        (a.output/'progress.json').write_text(json.dumps(report,indent=2)+'\n')
        tet=wm.Tetrahedralizer(**settings);tet.set_log_level(1);tet.set_mesh(v,f);report['phase']='tetrahedralize';(a.output/'progress.json').write_text(json.dumps(report,indent=2)+'\n');tet.tetrahedralize()
        vertices,cells,flags=tet.get_tet_mesh();np.savez_compressed(a.output/'mesh.npz',vertices=vertices,tetrahedra=cells,flags=flags)
        t=vertices[cells];det=np.einsum('ij,ij->i',t[:,1]-t[:,0],np.cross(t[:,2]-t[:,0],t[:,3]-t[:,0]));volumes=det/6
        faces=np.concatenate([cells[:,[0,2,1]],cells[:,[0,1,3]],cells[:,[0,3,2]],cells[:,[1,2,3]]]);_,first,inverse,counts=np.unique(np.sort(faces,axis=1),axis=0,return_index=True,return_inverse=True,return_counts=True)
        parity=np.where((faces[:,0]-faces[:,1])*(faces[:,1]-faces[:,2])*(faces[:,2]-faces[:,0])>0,1,-1);orientation=np.bincount(inverse,weights=parity);boundary=faces[first[counts==1]]
        used=np.unique(boundary);mapping=np.full(len(vertices),-1,dtype=np.int64);mapping[used]=np.arange(len(used));boundary=mapping[boundary]
        with (a.output/'boundary.mesh64').open('w')as stream:stream.write(f'{len(used)} {len(boundary)}\n');np.savetxt(stream,vertices[used],fmt='%.17g');np.savetxt(stream,boundary,fmt='%d')
        report.update(phase='mesher_returned',nodes=len(vertices),C3D4_elements=len(cells),boundary_triangles=len(boundary),minimum_determinant_mm3=float(det.min()),nonpositive_tetrahedra=int(np.count_nonzero(det<=0)),volume_mm3=float(volumes.sum()),nonmanifold_volume_faces=int(np.count_nonzero(counts>2)),inconsistent_internal_face_orientation=int(np.count_nonzero((counts==2)&(orientation!=0))),stats=tet.get_stats(),pending=['independent full boundary audit','independent complete surface-envelope proof','all protected interfaces','T10 conversion and mechanical cases'])
        report['status']='mesher_returned_positive_conformal_tetrahedra'if len(cells)>0 and np.isfinite(vertices).all()and np.all(det>0)and not report['nonmanifold_volume_faces']and not report['inconsistent_internal_face_orientation']else'mesher_output_screen_refused'
    except Exception as error:report['failure']=dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc())
    finally:report['elapsed_seconds']=time.monotonic()-start;(a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if k not in ['stats','failure']}));return 0 if report['status']=='mesher_returned_positive_conformal_tetrahedra'else 2

if __name__=='__main__':raise SystemExit(main())
