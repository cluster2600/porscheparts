"""Experimental conforming fluid mesh; preserve rejected runs and require checkMesh."""
import argparse, hashlib
from pathlib import Path
import numpy as np,trimesh,gmsh,json
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('source',type=Path)
p.add_argument('output',type=Path)
p.add_argument('--faces',type=int,default=80000)
args=p.parse_args()
if args.faces<10000: p.error('At least 10000 surface faces required')
out=args.output;out.mkdir(parents=True,exist_ok=False)
rotor=trimesh.load_mesh(args.source,process=True)
assert rotor.is_watertight and rotor.is_winding_consistent and rotor.body_count==1
assert 240<rotor.extents[0]<246, 'This pilot requires the 245 mm rotor, in mm'
small=rotor.simplify_quadric_decimation(face_count=args.faces)
assert small.is_watertight and small.body_count==1 and abs(small.volume/rotor.volume-1)<.002
small.export(out/'rotor.stl')
n=144;theta=np.arange(n)*2*np.pi/n
z=np.linspace(-180,180,37)
points=np.array([[124*np.cos(t),124*np.sin(t),zz] for zz in z for t in theta]);faces=[]
for j in range(len(z)-1):
 for i in range(n):
  a=j*n+i;b=j*n+(i+1)%n;c=b+n;d=a+n;faces.extend([[a,b,c],[a,c,d]])
trimesh.Trimesh(points,faces,process=False).export(out/'duct.stl')
for name,zz,reverse in [('inlet',-180,True),('outlet',180,False)]:
 radii=np.linspace(124/13,124,13)
 p=np.array([[0,0,zz]]+[[rr*np.cos(t),rr*np.sin(t),zz] for rr in radii for t in theta]);f=[]
 for i in range(n):f.append([0,1+i,1+(i+1)%n])
 for j in range(12):
  for i in range(n):
   a=1+j*n+i;b=1+j*n+(i+1)%n;c=b+n;d=a+n;f.extend([[a,b,c],[a,c,d]])
 if reverse:f=np.array(f)[:,::-1]
 trimesh.Trimesh(p,f,process=False).export(out/(name+'.stl'))
gmsh.initialize();gmsh.option.setNumber('General.NumThreads',4)
patches={}
for name in ['rotor','duct','inlet','outlet']:
 before=set(gmsh.model.getEntities(2));gmsh.merge(str(out/(name+'.stl')))
 patches[name]=[t for d,t in set(gmsh.model.getEntities(2))-before]
gmsh.model.mesh.removeDuplicateNodes()
outer=gmsh.model.geo.addSurfaceLoop(patches['duct']+patches['inlet']+patches['outlet'])
inner=gmsh.model.geo.addSurfaceLoop(patches['rotor'])
vol=gmsh.model.geo.addVolume([outer,inner]);gmsh.model.geo.synchronize()
for name,tags in patches.items():gmsh.model.addPhysicalGroup(2,tags,name=name)
gmsh.model.addPhysicalGroup(3,[vol],name='fluid')
gmsh.option.setNumber('Mesh.MeshOnlyEmpty',1);gmsh.option.setNumber('Mesh.Algorithm3D',1)
gmsh.option.setNumber('Mesh.MeshSizeMax',12);gmsh.model.mesh.generate(3)
gmsh.option.setNumber('Mesh.MshFileVersion',2.2)
gmsh.option.setNumber('Mesh.ScalingFactor',.001)
gmsh.write(str(out/'fluid.msh'))
types,tags,_=gmsh.model.mesh.getElements(3)
assert list(types)==[4], 'Expected linear tetrahedra'
quality=gmsh.model.mesh.getElementQualities(tags[0], 'minSICN')
assert np.isfinite(quality).all() and quality.min()>0, 'Inverted or degenerate tetrahedra'
mesh_quality={'tetrahedra':len(tags[0]),'minimum_signed_inverse_condition_number':float(quality.min())}
gmsh.finalize()
(out/'manifest.json').write_text(json.dumps({
 'source_sha256':hashlib.sha256(args.source.read_bytes()).hexdigest(),
 'source_volume_mm3':float(rotor.volume),'meshed_rotor_volume_mm3':float(small.volume),
 'quality':mesh_quality,'surface_faces':len(small.faces),'gmsh_version':gmsh.__version__,
 'method':'Delaunay tetrahedra, preserved discrete surfaces, default Gmsh optimization',
 'duct_radius_mm':124,'duct_length_mm':360,'output_units':'m',
 'alternator_included':False,'wall_layers':False,'manufacturing_authorized':False,
 'status':'mesh_generated_requires_openfoam_extended_check_and_surface_error_audit'
},indent=2)+'\n')
print('DONE')
