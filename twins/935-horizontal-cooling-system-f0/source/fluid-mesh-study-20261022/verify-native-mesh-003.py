"""Independently compare every native tetrahedron, point and patch marker to the audited arrays."""
import hashlib,importlib.util,json,re,sys
from pathlib import Path
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy
case,audited,output=map(Path,sys.argv[1:]);sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();proof=json.loads((audited/'assessment.json').read_text());assert sha(audited/'volume.npz')==proof['volume_npz_sha256'];z=np.load(audited/'volume.npz');v=z['vertices'];cells=z['tetrahedra'];boundary=z['boundary'];markers=z['markers']
spec=importlib.util.spec_from_file_location('fluid_mesh_ascii',Path(__file__).with_name('export-fluid-plc-005.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);mesh=case/'constant/polyMesh'
count,body=module.foam_list(mesh/'points');points=np.fromstring(body.replace('(',' ').replace(')',' '),sep=' ').reshape(-1,3);assert count==len(v) and np.array_equal(points,v)
count,body=module.foam_list(mesh/'faces',maximum_count=10_000_000);f=np.fromstring(body.replace('(',' ').replace(')',' '),sep=' ',dtype=np.int64).reshape(-1,4);assert len(f)==count and np.all(f[:,0]==3);f=f[:,1:]
count,body=module.foam_list(mesh/'boundary');blocks=list(re.finditer(r'([A-Za-z][A-Za-z0-9_]*)\s*\{([^{}]*)\}',body));assert count==4 and len(blocks)==4;mapping={'inlet':1,'outlet':2,'duct':3,'rotor':4};bf=[];bm=[]
for match in blocks:
 name=match[1];assert name in mapping;n=int(re.search(r'\bnFaces\s+(\d+)\s*;',match[2])[1]);start=int(re.search(r'\bstartFace\s+(\d+)\s*;',match[2])[1]);kind=re.search(r'\btype\s+(\w+)\s*;',match[2])[1];assert kind==('wall' if name in ['duct','rotor'] else 'patch');bf.extend(f[start:start+n]);bm.extend([mapping[name]]*n)
a=np.sort(boundary,axis=1);b=np.sort(np.array(bf),axis=1);order=lambda x:np.lexsort(tuple(x[:,i] for i in range(x.shape[1]-1,-1,-1)));sa=order(a);sb=order(b);assert np.array_equal(a[sa],b[sb]) and np.array_equal(markers[sa],np.array(bm)[sb])
(case/'verify-003.foam').touch(exist_ok=False);(case/'0').mkdir(exist_ok=True)
r=vtk.vtkOpenFOAMReader();r.SetFileName(str(case/'verify-003.foam'));r.SetCreateCellToPoint(False);r.UpdateInformation();r.DisableAllPatchArrays();r.SetPatchArrayStatus('internalMesh',1);r.Update();grid=r.GetOutput().GetBlock(0);assert grid.GetNumberOfCells()==len(cells) and grid.GetNumberOfPoints()==len(v);types=vtk_to_numpy(grid.GetCellTypesArray());assert np.all(types==vtk.VTK_TETRA);read_cells=vtk_to_numpy(grid.GetCells().GetConnectivityArray()).reshape(-1,4);a=np.sort(cells,axis=1);b=np.sort(read_cells,axis=1);assert np.array_equal(a[order(a)],b[order(b)])
result={'status':'native_mesh_matches_all_audited_coordinates_tetrahedra_and_patch_markers','vertices':len(v),'tetrahedra':len(cells),'boundary_triangles':len(boundary),'VTK_version':vtk.vtkVersion.GetVTKVersion(),'source_sha256':sha(__file__),'volume_audit_sha256':sha(audited/'assessment.json'),'native_mesh_sha256':{n:sha(mesh/n) for n in ['points','faces','boundary','owner','neighbour']},'CFD_accepted':False,'manufacturing_authorized':False}
with output.open('x') as s:json.dump(result,s,indent=2)
print(json.dumps(result),flush=True)
