"""Consolidate identical float64 XYZ identities; discard only repeated-index faces.

This is an exact representation change, with zero coordinate displacement.
It never removes a triangle with three distinct positions or a finite area.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import numpy as np


def consolidate(mesh_path,output):
    mesh_path=Path(mesh_path).resolve();output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    source=Path(__file__).resolve();shutil.copy2(source,output/source.name)
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    input_sha=digest(mesh_path);source_sha=digest(source);d=np.load(mesh_path)
    v=np.asarray(d['vertices'],dtype=np.float64);f=np.asarray(d['faces'],dtype=np.int64)
    if not np.isfinite(v).all():raise ValueError('Non-finite coordinates')
    vertices,inverse=np.unique(v,axis=0,return_inverse=True);faces=inverse[f]
    keep=(faces[:,0]!=faces[:,1])&(faces[:,1]!=faces[:,2])&(faces[:,2]!=faces[:,0])
    dropped=np.flatnonzero(~keep);t=v[f[dropped]]
    if np.any(np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0])!=0):raise ValueError('A discarded triangle has a nonzero area vector')
    data=dict(vertices=vertices,faces=faces[keep])
    for key in d.files:
        if key in data:continue
        if len(d[key])!=len(f):raise ValueError('Unknown non-face attribute cannot be consolidated implicitly')
        data[key]=d[key][keep]
    np.savez_compressed(output/'result.npz',**data)
    report=dict(status='exact_representation_consolidated_pending_independent_audit',input_sha256=input_sha,
        source_sha256=source_sha,result_sha256=digest(output/'result.npz'),original_vertices=len(v),vertices=len(vertices),
        exactly_equal_vertex_identities_consolidated=len(v)-len(vertices),original_faces=len(f),faces=int(keep.sum()),
        discarded_repeated_position_face_indices=dropped.tolist(),coordinate_displacement_mm=0.,
        discarded_surface_area_mm2=0.,discarded_signed_volume_mm3=0.,retained_face_attributes=list(data.keys())[2:])
    if digest(source)!=source_sha or digest(mesh_path)!=input_sha:raise ValueError('Source/input changed')
    (output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mesh',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();print(json.dumps(consolidate(a.mesh,a.output)))
