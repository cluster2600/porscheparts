from pathlib import Path
import numpy as np,trimesh,gmsh,json
r=Path('/workspace/jobs/fan-airflow-sweep-20260929')
out=r/'tetmesh-control';out.mkdir(exist_ok=False)
rotor=trimesh.load_mesh(r/'geometry/e-control/rotor-mm.stl',process=True)
small=rotor.simplify_quadric_decimation(face_count=80000)
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
gmsh.option.setNumber('Mesh.MeshOnlyEmpty',1);gmsh.option.setNumber('Mesh.Algorithm3D',10)
gmsh.option.setNumber('Mesh.MeshSizeMax',12);gmsh.model.mesh.generate(3)
gmsh.model.mesh.optimize('Netgen');gmsh.option.setNumber('Mesh.MshFileVersion',2.2)
gmsh.option.setNumber('Mesh.ScalingFactor',.001)
gmsh.write(str(out/'fluid.msh'));gmsh.finalize()
print('DONE')
