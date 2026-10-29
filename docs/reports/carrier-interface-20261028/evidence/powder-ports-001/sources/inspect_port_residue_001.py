import json,time
from pathlib import Path
import numpy as np
import manifold3d as mf
import igl
w=Path('work/carrier-interface-20261028');out=w/'ported-residue-001';assert not out.exists();out.mkdir()
b=np.load(w/'full-reconstructed-p10-001/candidate.npz');c=np.load(w/'ported-carrier-001/candidate.npz');bv,bf=b['vertices'],b['triangles'];cv,cf=c['vertices'],c['triangles'];before=mf.Manifold(mf.Mesh64(bv,bf));after=mf.Manifold(mf.Mesh64(cv,cf));added=after-before;mesh=added.to_mesh64();av=np.array(mesh.vert_properties)[:,:3];af=np.array(mesh.tri_verts,dtype=np.uint64);np.savez_compressed(out/'added.npz',vertices=av,triangles=af)
a=np.ascontiguousarray(bv.copy());a[a==0]=0;cc=np.ascontiguousarray(cv.copy());cc[cc==0]=0;isnew=~np.isin(cc.view('V24').ravel(),a.view('V24').ravel());newids=np.flatnonzero(isnew);d,fi,closest=igl.point_mesh_squared_distance(cv[newids],bv,bf.astype(np.int64));distance=np.sqrt(np.maximum(d,0));np.savez_compressed(out/'new-vertices.npz',indices=newids,distances=distance,closest_faces=fi,closest_points=closest)
report=dict(added_status=str(added.status()),added_is_empty=added.is_empty(),added_volume_mm3=added.volume(),added_vertices=len(av),added_triangles=len(af),added_component_volumes_mm3=[x.volume()for x in added.decompose()],added_bounds_mm=[av.min(0).tolist(),av.max(0).tolist()]if len(av)else None,new_vertices=len(newids),seam_vertices_below_1e_7_mm=int((distance<1e-7).sum()),seam_max_distance_mm=float(distance[distance<1e-7].max()),manufacturing_authorized=False);(out/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
with(out/'ported.mesh64').open('w')as stream:
 stream.write(f'{len(cv)} {len(cf)}\n');np.savetxt(stream,cv,fmt='%.17g');np.savetxt(stream,cf,fmt='%d')
