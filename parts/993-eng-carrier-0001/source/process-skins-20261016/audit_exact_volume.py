"""Independent topology and libigl candidate-pair audit of float64 Boolean output.

Candidate contacts must additionally be adjudicated by classify_mesh_contacts.py.
A native Boolean success alone does not admit an envelope.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import time
import numpy as np
import igl
import igl.predicates


def audit(mesh_path,output):
    mesh_path=Path(mesh_path).resolve();output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    source=Path(__file__).resolve();shutil.copy2(source,output/source.name)
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    source_sha=digest(source);input_sha=digest(mesh_path)
    data=np.load(mesh_path);v=np.ascontiguousarray(data['vertices'],dtype=np.float64);f=np.ascontiguousarray(data['faces'],dtype=np.int64)
    if not np.isfinite(v).all() or f.min()<0 or f.max()>=len(v):raise ValueError('Invalid coordinates or face indices')
    edges=np.stack([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]],axis=1).reshape(-1,2)
    unique,inverse,counts=np.unique(np.sort(edges,axis=1),axis=0,return_inverse=True,return_counts=True)
    balance=np.bincount(inverse,weights=np.where(edges[:,0]<edges[:,1],1,-1),minlength=len(unique))
    t=v[f];cross=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);area=np.linalg.norm(cross,axis=1)/2
    volume=float(np.einsum('ij,ij->i',t[:,0],np.cross(t[:,1],t[:,2])).sum()/6)
    started=time.monotonic();found,pairs,_=igl.predicates.find_self_intersections(v,f,False)
    pairs=np.asarray(pairs,dtype=np.int64).reshape(-1,2);np.savez_compressed(output/'pairs.npz',pairs=pairs)
    topology=dict(open_edges=int(np.sum(counts==1)),nonmanifold_edges=int(np.sum(counts>2)),
        inconsistent_edge_orientation=int(np.count_nonzero(balance)),zero_area_faces=int(np.sum(area==0)),
        signed_volume_mm3=volume,surface_area_mm2=float(area.sum()))
    report=dict(status='candidate_pairs_require_exact_adjudication' if len(pairs) else 'passed',
        input=str(mesh_path),input_sha256=input_sha,source_sha256=source_sha,vertices=len(v),triangles=len(f),
        topology=topology,libigl_version=getattr(igl,'__version__','unreported'),raw_pair_count=len(pairs),
        native_elapsed_seconds=time.monotonic()-started,pairs_sha256=digest(output/'pairs.npz'))
    report['topology_passed']=all(topology[k]==0 for k in ['open_edges','nonmanifold_edges','inconsistent_edge_orientation','zero_area_faces']) and volume>0
    if not report['topology_passed']:report['status']='rejected'
    if digest(source)!=source_sha or digest(mesh_path)!=input_sha:raise ValueError('Source/input changed during audit')
    (output/'assessment.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mesh',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();print(json.dumps(audit(a.mesh,a.output)))
