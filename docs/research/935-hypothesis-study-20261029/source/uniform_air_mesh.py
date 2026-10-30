"""Conforming, convex Cartesian external-air mesh, with explicit geometric approximation."""
import argparse
import json
from pathlib import Path
import gmsh
import igl
import numpy as np
from scipy import ndimage
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('frame',type=Path);p.add_argument('output',type=Path);p.add_argument('--pitch-mm',type=float,required=True)
a=p.parse_args();a.output.mkdir()
d=np.load(a.source);v=d['vertices']@np.load(a.frame).T;v=(v-v.min(axis=0))/1000;f=d['triangles'].astype(np.int64);h=a.pitch_mm/1000
lo=np.array([-.08,-.08,-.08]);size=np.ceil((v.max(axis=0)+[.24,.08,.08]-lo)/h).astype(int)
ijk=np.indices(size).reshape(3,-1).T
q=lo+(ijk+.5)*h
w=igl.fast_winding_number(np.ascontiguousarray(v),np.ascontiguousarray(f),q)
assert np.isfinite(w).all()
free=(w<.5).reshape(size)
seed=np.zeros_like(free);seed[[0,-1],:,:]=True;seed[:,[0,-1],:]=True;seed[:,:,[0,-1]]=True
outside=ndimage.binary_propagation(seed&free,mask=free)
cell=ijk[outside.ravel()]
corner=np.array([[0,0,0],[1,0,0],[1,1,0],[0,1,0],[0,0,1],[1,0,1],[1,1,1],[0,1,1]])
node_ijk,con=np.unique((cell[:,None,:]+corner).reshape(-1,3),axis=0,return_inverse=True)
x=lo+node_ijk*h;hexa=con.reshape(-1,8)
face_pattern=np.array([[0,3,2,1],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]])
all_faces=hexa[:,face_pattern].reshape(-1,4)
_,idx,count=np.unique(np.sort(all_faces,axis=1),axis=0,return_index=True,return_counts=True)
assert count.max()==2
boundary=all_faces[idx[count==1]]
bary=x[boundary].mean(axis=1);hi=lo+size*h
inlet=np.isclose(bary[:,0],lo[0]);outlet=np.isclose(bary[:,0],hi[0])
farfield=(np.isclose(bary[:,1:],lo[1:])|np.isclose(bary[:,1:],hi[1:])).any(axis=1)
head=~(inlet|outlet|farfield)
assert head.any() and inlet.any() and outlet.any()
gmsh.initialize();gmsh.model.add('uniform_external_air_study')
for tag in range(1,5):gmsh.model.addDiscreteEntity(2,tag)
gmsh.model.addDiscreteEntity(3,1,[1,2,3,4]);gmsh.model.mesh.addNodes(3,1,np.arange(1,len(x)+1),x.ravel())
gmsh.model.mesh.addElementsByType(1,5,np.arange(1,len(hexa)+1),(hexa+1).ravel())
gmsh.model.addPhysicalGroup(3,[1],1,'fluid')
offset=len(hexa)
for tag,(name,mask) in enumerate([('inlet',inlet),('outlet',outlet),('farfield',farfield),('head',head)],1):
    surf=boundary[mask];gmsh.model.mesh.addElementsByType(tag,3,np.arange(offset+1,offset+len(surf)+1),(surf+1).ravel());offset+=len(surf)
    gmsh.model.addPhysicalGroup(2,[tag],tag+1,name)
gmsh.option.setNumber('Mesh.MshFileVersion',2.2);gmsh.option.setNumber('Mesh.Binary',0);gmsh.write(str(a.output/'air.msh'));gmsh.finalize()
(a.output/'report.json').write_text(json.dumps({'pitch_mm':a.pitch_mm,'nodes':len(x),'hexahedra':len(hexa),'head_boundary_faces':int(head.sum()),'head_discrete_area_m2':float(head.sum()*h*h),'fluid_volume_m3':float(len(hexa)*h**3),'closed_fluid_voxels_excluded':int(free.sum()-outside.sum()),'winding_ambiguous_0_4_to_0_6':int(((w>.4)&(w<.6)).sum()),'source_geometry_approximation':'uniform centre-sampled staircase; no adaptive cells or relaxed mesh checks','bounds_m':[lo.tolist(),hi.tolist()],'manufacturing_qualified':False},indent=2)+'\n')
print('Uniform air mesh written',len(hexa),flush=True)
