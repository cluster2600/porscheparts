"""Full all-facet libigl audit of a specified float64 indexed surface mesh."""
import hashlib
import importlib.util
import json
from pathlib import Path


def main():
    import numpy as np
    import igl.predicates
    mesh=Path('/input/mesh.mesh64');out=Path('/output')
    with mesh.open()as stream:nv,nf=map(int,stream.readline().split());v=np.loadtxt(stream,max_rows=nv);f=np.loadtxt(stream,dtype=np.int64)
    if v.shape!=(nv,3)or f.shape!=(nf,3)or not np.isfinite(v).all():raise ValueError('Mesh format differs')
    spec=importlib.util.spec_from_file_location('_mesh64_topology','/source/audit.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    topology=m.topology(v,f);found,pairs,_=igl.predicates.find_self_intersections(v,f,False)
    (out/'self-intersection-pairs.json').write_text(json.dumps(np.asarray(pairs).tolist())+'\n')
    triangles=v[f];twice=np.linalg.norm(np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]),axis=1);longest=np.max(np.sum((triangles-np.roll(triangles,-1,axis=1))**2,axis=2),axis=1)
    failures=[k for k in ['boundary_edges','nonmanifold_edges','inconsistent_orientation_edges','degenerate_triangles','needle_triangles']if topology[k]]
    if found or len(pairs):failures.append('self_intersections')
    if topology['connected_components']!=1:failures.append('connected_components')
    if topology['volume_mm3']<=0:failures.append('nonpositive_volume')
    report=dict(status='complete_surface_screen_passed'if not failures else'complete_surface_screen_refused',topology=topology,self_intersection_pairs=len(pairs),failures=failures,retained_needle_ratio_threshold=.001,full_needle_triangle_indices=np.flatnonzero(twice/longest<.001).tolist(),source_mesh_sha256=hashlib.sha256(mesh.read_bytes()).hexdigest(),mechanical_mesh_admitted=False)
    (out/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(status=report['status'],topology=topology,failures=failures)))

if __name__=='__main__':main()
