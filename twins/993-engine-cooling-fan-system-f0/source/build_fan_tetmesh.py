"""Experimental conforming fluid mesh; preserve rejected runs and require checkMesh."""
import argparse, hashlib
from pathlib import Path
import numpy as np,trimesh,gmsh,json
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('source',type=Path)
p.add_argument('output',type=Path)
p.add_argument('--faces',type=int,default=80000)
p.add_argument('--preserve-surface',action='store_true',help='Keep an independently remeshed surface without decimation')
p.add_argument('--optimize-netgen',action='store_true',help='Optimize volume tetrahedra while retaining the boundary surface')
p.add_argument('--resolve-gap',action='store_true',help='Resolve the duct wall opposite the 1.5 mm blade-tip clearance')
p.add_argument('--graded-interior',action='store_true',help='Use 2 mm near-rotor and configurable far-field target sizes')
p.add_argument('--algorithm',type=int,choices=(1,10),default=1,help='Gmsh Delaunay (1) or HXT (10)')
p.add_argument('--far-wall-step',type=int,choices=(1,5),default=5,help='Axial duct surface spacing in mm outside the rotor band')
p.add_argument('--far-field-size',type=float,default=12,help='Far-field volume mesh size in mm')
p.add_argument('--threads',type=int,default=4)
p.add_argument('--refinement-centres',type=Path,help='JSON array of local refinement centres in mm')
args=p.parse_args()
if not 1 <= args.far_field_size <= 12 or not 1 <= args.threads <= 64: p.error('Invalid mesh size or thread count')
if args.faces<10000: p.error('At least 10000 surface faces required')
out=args.output;out.mkdir(parents=True,exist_ok=False)
rotor=trimesh.load_mesh(args.source,process=True)
assert rotor.is_watertight and rotor.is_winding_consistent and rotor.body_count==1
assert 240<rotor.extents[0]<246, 'This pilot requires the 245 mm rotor, in mm'
small=rotor.copy() if args.preserve_surface else rotor.simplify_quadric_decimation(face_count=args.faces)
assert small.is_watertight and small.body_count==1 and abs(small.volume/rotor.volume-1)<.002
small.export(out/'rotor.stl')
n=768 if args.resolve_gap else 144;theta=np.arange(n)*2*np.pi/n
z=(np.unique(np.concatenate((np.arange(-180,-40,args.far_wall_step),np.arange(-40,41),
                            np.arange(40+args.far_wall_step,181,args.far_wall_step))))
   if args.resolve_gap else np.linspace(-180,180,37))
points=np.array([[124*np.cos(t),124*np.sin(t),zz] for zz in z for t in theta]);faces=[]
for j in range(len(z)-1):
 for i in range(n):
  a=j*n+i;b=j*n+(i+1)%n;c=b+n;d=a+n;faces.extend([[a,b,c],[a,c,d]])
trimesh.Trimesh(points,faces,process=False).export(out/'duct.stl')
for name,zz,reverse in [('inlet',-180,True),('outlet',180,False)]:
 if args.resolve_gap:
  from scipy.spatial import Delaunay
  grid=np.array([(x,y) for x in np.arange(-116,117,4) for y in np.arange(-116,117,4)
                 if x*x+y*y<118**2])
  rings=np.array([[rr*np.cos(t),rr*np.sin(t)] for rr in (120,122,124) for t in theta])
  xy=np.vstack((grid,rings));p=np.column_stack((xy,np.full(len(xy),zz)))
  f=Delaunay(xy).simplices
 else:
  radii=np.linspace(124/13,124,13)
  p=np.array([[0,0,zz]]+[[rr*np.cos(t),rr*np.sin(t),zz] for rr in radii for t in theta]);f=[]
  for i in range(n):f.append([0,1+i,1+(i+1)%n])
  for j in range(12):
   for i in range(n):
    a=1+j*n+i;b=1+j*n+(i+1)%n;c=b+n;d=a+n;f.extend([[a,b,c],[a,c,d]])
 if reverse:f=np.array(f)[:,::-1]
 trimesh.Trimesh(p,f,process=False).export(out/(name+'.stl'))
outer_mesh=trimesh.util.concatenate([trimesh.load_mesh(out/(name+'.stl')) for name in ('duct','inlet','outlet')])
outer_mesh.merge_vertices()
assert outer_mesh.is_watertight and outer_mesh.is_winding_consistent, 'Invalid duct boundary'
gmsh.initialize();gmsh.option.setNumber('General.NumThreads',args.threads)
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
gmsh.option.setNumber('Mesh.MeshOnlyEmpty',1);gmsh.option.setNumber('Mesh.Algorithm3D',args.algorithm)
if args.graded_interior:
 gmsh.option.setNumber('Mesh.MeshSizeExtendFromBoundary',0)
 field=gmsh.model.mesh.field.add('Box')
 for key,value in {'VIn':2,'VOut':args.far_field_size,'XMin':-130,'XMax':130,'YMin':-130,'YMax':130,
                   'ZMin':-45,'ZMax':45,'Thickness':20}.items():
  gmsh.model.mesh.field.setNumber(field,key,value)
 gmsh.model.mesh.field.setAsBackgroundMesh(field)
if args.refinement_centres:
 centres=np.asarray(json.loads(args.refinement_centres.read_text()),dtype=float)
 assert args.graded_interior and centres.ndim==2 and centres.shape[1]==3 and len(centres)<=100
 assert np.isfinite(centres).all() and (np.abs(centres)<180).all()
 fields=[field]
 for x,y,z in centres:
  ball=gmsh.model.mesh.field.add('Ball')
  for key,value in {'VIn':.35,'VOut':args.far_field_size,'XCenter':x,'YCenter':y,'ZCenter':z,'Radius':2,'Thickness':3}.items():
   gmsh.model.mesh.field.setNumber(ball,key,value)
  fields.append(ball)
 combined=gmsh.model.mesh.field.add('Min')
 gmsh.model.mesh.field.setNumbers(combined,'FieldsList',fields)
 gmsh.model.mesh.field.setAsBackgroundMesh(combined)
gmsh.option.setNumber('Mesh.MeshSizeMax',args.far_field_size);gmsh.model.mesh.generate(3)
if args.optimize_netgen: gmsh.model.mesh.optimize('Netgen',force=True,niter=3)
gmsh.option.setNumber('Mesh.MshFileVersion',2.2)
gmsh.option.setNumber('Mesh.ScalingFactor',.001)
gmsh.write(str(out/'fluid.msh'))
types,tags,_=gmsh.model.mesh.getElements(3)
assert list(types)==[4], 'Expected linear tetrahedra'
quality=gmsh.model.mesh.getElementQualities(tags[0], 'minSICN')
assert np.isfinite(quality).all() and quality.min()>0, 'Inverted or degenerate tetrahedra'
mesh_quality={'tetrahedra':len(tags[0]),'minimum_signed_inverse_condition_number':float(quality.min())}
node_tags,node_xyz,_=gmsh.model.mesh.getNodes()
order=np.argsort(node_tags);node_tags=np.asarray(node_tags)[order]
node_xyz=np.asarray(node_xyz).reshape(-1,3)[order]
rotor_faces=[]
for tag in patches['rotor']:
 surface_types,_,surface_nodes=gmsh.model.mesh.getElements(2,tag)
 assert list(surface_types)==[2], 'Expected triangular rotor boundary'
 rotor_faces.extend(np.searchsorted(node_tags,np.asarray(surface_nodes[0]).reshape(-1,3)))
conforming=trimesh.Trimesh(node_xyz,np.asarray(rotor_faces),process=True)
conforming.remove_unreferenced_vertices()
assert conforming.is_watertight and conforming.is_winding_consistent and conforming.body_count==1
conforming.export(out/'rotor-conforming-mm.stl')
gmsh.finalize()
(out/'manifest.json').write_text(json.dumps({
 'source_sha256':hashlib.sha256(args.source.read_bytes()).hexdigest(),
 'source_volume_mm3':float(rotor.volume),'meshed_rotor_volume_mm3':float(small.volume),
 'quality':mesh_quality,'surface_faces':len(small.faces),'gmsh_version':gmsh.__version__,
 'method':'Conforming tetrahedra with preserved discrete surfaces',
 'surface_decimation_skipped':args.preserve_surface,'netgen_optimization':args.optimize_netgen,
 'duct_gap_refinement':args.resolve_gap,'duct_circumferential_segments':n,
 'graded_interior':args.graded_interior,
 'local_refinement_centres_mm':centres.tolist() if args.refinement_centres else [],
 'algorithm_3d':args.algorithm,'far_field_size_mm':args.far_field_size,'threads':args.threads,
 'far_wall_step_mm':args.far_wall_step if args.resolve_gap else 10,
 'duct_radius_mm':124,'duct_length_mm':360,'output_units':'m',
 'alternator_included':False,'wall_layers':False,'manufacturing_authorized':False,
 'status':'mesh_generated_requires_openfoam_extended_check_and_surface_error_audit'
},indent=2)+'\n')
print('DONE')
