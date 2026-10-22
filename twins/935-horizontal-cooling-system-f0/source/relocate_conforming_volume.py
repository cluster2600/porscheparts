"""Relocate interior tetrahedral nodes with the qualified native Gmsh payload."""
import hashlib,json,sys,time
from pathlib import Path
import gmsh
import numpy as np
sha=lambda p:hashlib.file_digest(Path(p).open('rb'),'sha256').hexdigest()
assert gmsh.__version__=='4.15.2'
assert sha(gmsh.__file__)=='f4b0935cebde899750293d87a643090e5ea33c9b18d249267f507db68a0e01c3'
assert sha(gmsh.lib._name)=='def0f5c10988a986e5e879b3db9669d8fe016a81e2d994bbaf2b8497c6b8a58a'
folder=Path(sys.argv[1]);inp=folder/'input.npz';assert not (folder/'assessment.json').exists()
with np.load(inp,allow_pickle=False) as d:v,c,f=d['vertices'],d['tetrahedra'],d['boundary']
assert c.shape[1]==4 and f.shape[1]==3 and np.isfinite(v).all();boundary_nodes=np.unique(f)
r={'status':'incomplete','source_sha256':sha(__file__),'input_sha256':sha(inp),'optimizer':'Relocate3D','requested_iterations':20,'gmsh_version':gmsh.__version__,'gmsh_module_sha256':sha(gmsh.__file__),'loaded_library_sha256':sha(gmsh.lib._name),'numpy_version':np.__version__,'mechanical_mesh_admitted':False,'manufacturing_authorized':False}
start=time.monotonic();gmsh.initialize(['relocate-935','-nopopup'],readConfigFiles=False,run=False);gmsh.logger.start()
try:
 gmsh.model.add('935_interior_quality_trial');gmsh.model.addDiscreteEntity(2,1);gmsh.model.geo.addSurfaceLoop([1],1);gmsh.model.geo.addVolume([1],1);gmsh.model.geo.synchronize()
 gmsh.model.mesh.addNodes(3,1,np.arange(1,len(v)+1),v.ravel());gmsh.model.mesh.addElementsByType(1,2,np.arange(1,len(f)+1),(f+1).ravel());gmsh.model.mesh.addElementsByType(1,4,np.arange(len(f)+1,len(f)+len(c)+1),(c+1).ravel());gmsh.model.mesh.reclassifyNodes()
 gmsh.option.setNumber('General.NumThreads',2);gmsh.option.setNumber('Mesh.Renumber',0)
 gmsh.model.mesh.optimize('Relocate3D',force=True,niter=20)
 tags,xyz,_=gmsh.model.mesh.getNodes();order=np.argsort(tags);tags=np.asarray(tags)[order];xyz=np.asarray(xyz).reshape(-1,3)[order];assert np.array_equal(tags,np.arange(1,len(v)+1))
 arrays=[]
 for kind,width in [(4,4),(2,3)]:
  etags,nodes=gmsh.model.mesh.getElementsByType(kind,1);eorder=np.argsort(etags);array=np.asarray(nodes).reshape(-1,width)[eorder].astype(np.int64)-1;arrays.append(array)
 assert np.array_equal(arrays[0],c) and np.array_equal(arrays[1],f),'Optimizer changed connectivity'
 assert np.array_equal(xyz[boundary_nodes],v[boundary_nodes]),'Optimizer changed the certified boundary'
 np.savez_compressed(folder/'volume.npz',vertices=xyz,tetrahedra=c,boundary=f)
 r.update(status='interior_relocated_not_audited',vertices=len(v),tetrahedra=len(c),boundary_triangles=len(f),boundary_coordinates_exactly_preserved=True,connectivity_exactly_preserved=True,moved_nodes=int(np.any(xyz!=v,axis=1).sum()),maximum_interior_shift_native_units=float(np.linalg.norm(xyz-v,axis=1).max()),volume_npz_sha256=sha(folder/'volume.npz'))
except Exception as error:r.update(status='failed',error=type(error).__name__+': '+str(error))
finally:
 (folder/'gmsh.log').write_text('\n'.join(gmsh.logger.get())+'\n');gmsh.logger.stop();gmsh.finalize();r['elapsed_s']=time.monotonic()-start;(folder/'assessment.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r),flush=True);raise SystemExit(0 if r['status']=='interior_relocated_not_audited' else 2)
