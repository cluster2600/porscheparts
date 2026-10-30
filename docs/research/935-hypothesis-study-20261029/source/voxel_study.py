"""Explicit voxel analysis discretisation; does not replace the faithful print surface."""
import argparse
import hashlib
import json
import time
from pathlib import Path
import igl
import numpy as np
from scipy import ndimage

p=argparse.ArgumentParser()
p.add_argument('source',type=Path)
p.add_argument('frame',type=Path)
p.add_argument('output',type=Path)
p.add_argument('--pitch',type=float,required=True)
a=p.parse_args();a.output.mkdir();started=time.monotonic()
d=np.load(a.source);v=d['vertices']@np.load(a.frame).T;f=d['triangles'].astype(np.int64)
h=a.pitch
origin=np.floor(v.min(axis=0)/h)*h-h
shape=np.ceil((v.max(axis=0)-origin)/h).astype(int)+1
ijk=np.stack(np.meshgrid(*[np.arange(n) for n in shape],indexing='ij'),axis=-1).reshape(-1,3)
centres=origin+(ijk+.5)*h
w=igl.fast_winding_number(np.ascontiguousarray(v),np.ascontiguousarray(f),centres)
assert np.isfinite(w).all()
inside=(w>.5).reshape(shape)
labels,n=ndimage.label(inside,ndimage.generate_binary_structure(3,1))
sizes=np.bincount(labels.ravel());sizes[0]=0
largest=int(sizes.argmax());kept=labels==largest
cells=np.argwhere(kept)
corners=np.array([[0,0,0],[1,0,0],[1,1,0],[0,1,0],[0,0,1],[1,0,1],[1,1,1],[0,1,1]])
node_ijk,conn=np.unique((cells[:,None,:]+corners).reshape(-1,3),axis=0,return_inverse=True)
nodes=origin+node_ijk*h
hexes=conn.reshape(-1,8)
np.savez_compressed(a.output/'hex.npz',nodes=nodes,hexes=hexes,cell_ijk=cells,origin=origin,pitch=h,occupied=inside,retained=kept)
# deal.II / Adamantine import: Gmsh MSH 2.2 format, hexahedra, material id 0.
with (a.output/'solid-si.msh').open('w') as out:
    out.write('$MeshFormat\n2.2 0 8\n$EndMeshFormat\n$Nodes\n'+str(len(nodes))+'\n')
    for i,q in enumerate(nodes/1000,1):out.write(f'{i} {q[0]:.12g} {q[1]:.12g} {q[2]:.12g}\n')
    out.write('$EndNodes\n$Elements\n'+str(len(hexes))+'\n')
    for i,c in enumerate(hexes+1,1):out.write(f'{i} 5 2 0 1 '+ ' '.join(map(str,c))+'\n')
    out.write('$EndElements\n')
surface_volume=np.einsum('ij,ij->',v[f[:,0]],np.cross(v[f[:,1]],v[f[:,2]]))/6
r={'source_sha256':hashlib.sha256(a.source.read_bytes()).hexdigest(),'purpose':'coarse analysis mesh only; original closed print surface is retained separately','pitch_mm':h,'shape':shape.tolist(),'inside_voxels':int(inside.sum()),'connected_components':n,'retained_voxels':len(cells),'excluded_volume_mm3':float((inside.sum()-len(cells))*h**3),'volume_mm3':float(len(cells)*h**3),'reference_surface_volume_mm3':float(surface_volume),'relative_volume_difference':float((len(cells)*h**3-surface_volume)/surface_volume),'winding_ambiguous_0_4_to_0_6':int(((w>.4)&(w<.6)).sum()),'elapsed_seconds':time.monotonic()-started,'assumptions':['Voxel centre inclusion; no cavity filling operation','Largest face-connected voxel component retained; excluded voxels preserved in hex.npz','Thin walls and passages below pitch are not resolved'],'manufacturing_qualified':False}
(a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
