"""Verify opposite T6 facet topology as well as node matching before periodic FEM."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from periodic_interface_mesh import EDGES,audit_periodicity,audit_t10


def audit_facets(points,cells):
    local=[[0,1,2,4,5,6],[0,1,3,4,8,7],[0,2,3,6,9,7],[1,2,3,5,9,8]]
    faces=np.concatenate([cells[:,f]for f in local]);_,indices,counts=np.unique(np.sort(faces[:,:3],axis=1),axis=0,return_index=True,return_counts=True)
    if counts.max()>2:raise ValueError('Nonmanifold volume-face incidence')
    boundary=faces[indices[counts==1]];tree=cKDTree(points);rows=[]
    for axis in range(3):
        low=boundary[np.all(abs(points[boundary,axis]+.5)<=1e-8,axis=1)];high=boundary[np.all(abs(points[boundary,axis]-.5)<=1e-8,axis=1)]
        if not len(low)or len(low)!=len(high):raise ValueError('Opposite T6 face counts differ')
        d,ids=tree.query((points[high]-np.eye(3)[axis]).reshape(-1,3))
        if d.max()>1e-8:raise ValueError('Translated T6 nodes exceed the fixed geometric limit')
        left={tuple(x)for x in np.sort(low,axis=1)};right={tuple(x)for x in np.sort(ids.reshape(-1,6),axis=1)}
        if len(left)!=len(low)or left!=right:raise ValueError('Opposite boundary triangulations differ')
        rows.append(dict(axis=axis,opposite_T6_face_pairs=len(low),maximum_translation_error_mm=float(d.max())))
    return dict(total_boundary_T6_faces=len(boundary),opposite_faces=rows)


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--mesh',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists();z=np.load(a.mesh/'transport.npz');points=z['points'];cells=z['cells'];periodic=audit_periodicity(points);geometry=audit_t10(points,cells);facets=audit_facets(points,cells)
    x=points[cells[:,:4]];squared=np.stack([np.sum((x[:,i]-x[:,j])**2,axis=1)for i,j in EDGES],axis=1);J=(x[:,1:]-x[:,0,None,:]).transpose(0,2,1);vol=np.linalg.det(J)/6
    r=dict(status='complete_periodic_T10_nodes_and_T6_facets_passed',tetrahedra=len(cells),nodes=len(points),periodicity=periodic,facets=facets,geometry=geometry,maximum_corner_edge_mm=float(np.sqrt(squared.max())),volume_weighted_RMS_corner_edge_mm=float(np.sqrt(np.sum(squared*vol[:,None])/(6*vol.sum()))),source_sha256={str(f):hashlib.sha256(f.read_bytes()).hexdigest()for f in [Path(__file__),a.mesh/'transport.npz',a.mesh/'cell.step']},carrier_geometry_changed=False)
    a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))


if __name__=='__main__':main()
