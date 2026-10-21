"""Small closed-tetrahedron installation/API control; no carrier admission."""
import argparse
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import time


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True);os.chdir(a.output);start=time.monotonic()
    import numpy as np
    import wildmeshing as wm
    vertices=np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]])
    faces=np.array([[0,2,1],[0,1,3],[0,3,2],[1,2,3]],dtype=int)
    settings=dict(max_threads=1,epsilon=.001,edge_length_r=.5,max_its=5,coarsen=False)
    tet=wm.Tetrahedralizer(**settings);tet.set_log_level(1);tet.set_mesh(vertices,faces);tet.tetrahedralize();result=tet.get_tet_mesh();print([getattr(x,'shape',type(x).__name__)for x in result])
    v,t=result[:2];cells=v[t];signed=np.einsum('ij,ij->i',cells[:,1]-cells[:,0],np.cross(cells[:,2]-cells[:,0],cells[:,3]-cells[:,0]))/6
    np.savez_compressed(a.output/'mesh.npz',vertices=v,tetrahedra=t)
    report=dict(status='installation_control_passed'if len(t)>0 and np.isfinite(v).all()and np.all(signed>0)else'installation_control_refused',settings=settings,versions={n:metadata.version(n)for n in ['wildmeshing','numpy','svgwrite']},nodes=len(v),tetrahedra=len(t),minimum_signed_tet_volume_mm3=float(signed.min()),total_volume_mm3=float(signed.sum()),relative_tetrahedron_volume_error=float(signed.sum()/(1/6)-1),stats=tet.get_stats(),elapsed_seconds=time.monotonic()-start,carrier_qualified=False)
    (a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='stats'}))

if __name__=='__main__':main()
