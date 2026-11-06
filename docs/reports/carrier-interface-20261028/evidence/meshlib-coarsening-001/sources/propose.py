"""MeshLib optimized proposal, restoring retained coordinates where identifiable."""
from pathlib import Path
import numpy as np,json,time,hashlib,struct,importlib.metadata
from meshlib import mrmeshpy as mr,mrmeshnumpy as mn
def propose(v,f,budget,deleted):
 center=(v.min(0)+v.max(0))/2
 q=np.ascontiguousarray((v-center).astype(np.float32))
 keys=q.view('V12').ravel();order=np.argsort(keys);sorted_keys=keys[order]
 assert not np.any(sorted_keys[1:]==sorted_keys[:-1]),'float32 input collision'
 mesh=mn.meshFromFacesVerts(np.asarray(f,dtype=np.int32),q,duplicateNonManifoldVertices=False)
 assert np.array_equal(mn.getNumpyFaces(mesh.topology),f),'intake changed triangle inventory'
 s=mr.DecimateSettings();s.maxError=budget;s.maxDeletedFaces=deleted;s.optimizeVertexPos=True;s.packMesh=True;s.subdivideParts=1;s.maxAngleChange=-1;s.stabilizer=0
 start=time.monotonic();result=mr.decimateMesh(mesh,s);native_result={k:getattr(result,k)for k in dir(result)if not k.startswith("_")and isinstance(getattr(result,k),(int,float,bool))}
 out_f=mn.getNumpyFaces(mesh.topology);assert len(out_f)==len(f)-result.facesDeleted,'deleted faces remain in export';assert np.all(out_f[:,0]!=out_f[:,1])and np.all(out_f[:,1]!=out_f[:,2])and np.all(out_f[:,0]!=out_f[:,2]),'collapsed face in export';used,inv=np.unique(out_f,return_inverse=True)
 out_q=np.ascontiguousarray(mn.getNumpyVerts(mesh)[used].astype(np.float32))
 out_keys=out_q.view('V12').ravel();positions=np.searchsorted(sorted_keys,out_keys)
 positions=np.minimum(positions,len(keys)-1);matched=sorted_keys[positions]==out_keys
 out_v=out_q.astype(np.float64)+center;out_v[matched]=v[order[positions[matched]]];out_f=inv.reshape(-1,3)
 return out_v,out_f,dict(meshlib_version=importlib.metadata.version('meshlib'),native_result=native_result,input_faces=len(f),output_faces=len(out_f),seconds=time.monotonic()-start,retained_coordinates_exact=True,new_coordinates_count=int(np.count_nonzero(~matched)),estimated_error_setting_mm=budget,maximum_requested_deleted_faces=deleted,center_mm=center.tolist(),optimize_vertex_position=True,pack_mesh=True,subdivide_parts=1,angle_change_setting=-1,stabilizer=0,geometric_distance_certified=False)
def save(path,v,f):
 with open(path,'wb')as stream:
  stream.write(struct.pack('<QQ',len(v),len(f)));v.astype('<f8').tofile(stream);f.astype('<u8').tofile(stream)
if __name__=='__main__':
 r=Path(__file__).resolve().parent;w=r.parent;selection=json.loads((w/'fast-quadric-coarsening-001/selected-eight-voids.json').read_text());item=next(x for x in selection['rows']if x['void']=='r3-positive');source=w/item['private_case_path']/'decoded-001/candidate.npz'
 assert hashlib.sha256(source.read_bytes()).hexdigest()==item['npz_sha256']
 z=np.load(source);v,f,receipt=propose(z['vertices'],z['triangles'],.0009,len(z['triangles'])//2);save(r/'candidate.meshbin',v,f);np.savez(r/'candidate.npz',vertices=v,triangles=f)
 receipt.update(status='unaccepted_meshlib_proposal',input_sha256=item['npz_sha256'],candidate_sha256=hashlib.sha256((r/'candidate.meshbin').read_bytes()).hexdigest(),maximum_additional_certification_budget_mm=.001,composed_bound_if_certified_mm=.004430795134873041)
 (r/'proposal.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
