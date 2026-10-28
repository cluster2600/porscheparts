"""Map weak Gmsh cells to the exact source rotor facets and prior flip trial."""
import json, hashlib
from pathlib import Path
import gmsh, numpy as np, trimesh
from scipy.spatial import cKDTree
root=Path.cwd()
plc=root/'work/935-cfd-root0p7-20261026-repro/boundary.npz'
mesh=root/'work/935-cfd-root0p7-20261026-repro/gmsh-root0p7-fluid-20261028/fluid.msh'
weak_file=root/'work/935-cfd-root0p7-20261026-repro/gmsh-root0p7-fluid-20261028/weak-cell-localization/weak-cells.npz'
source=root/'work/935-root-quality-local-20261025/analysis-candidate.off'
flips=root/'work/935-cfd-root0p7-20261026-flips/receipt.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(mesh)=='2a7346eb7696b67c59ffd23d791f1d8ddd82f69ab22f87986e1b1ac43b0006e7'
assert sha(plc)=='9fcd93a5c54ebfc98b8cd86d4550e3a416d3e62fb217e5ebfb67eb2f2a9f2085'
assert sha(source)=='5d900f6da900b4bffac2fdacfd6e0a346f8c0259a19299725621d4fd1e48c12a'
assert sha(weak_file)=='bdcfde4eef36e39d9e2efa29c464e3e6ab5d7db8588a4398eb4f02717070f7a4'
assert sha(flips)=='2752d9a624c9d29e59c9c8c3d97d799a08332a291c69b796f98218bef5d979c8'
with np.load(weak_file) as z:ids=z['cell_ids'];ratio=z['mean_ratio']
off=trimesh.load_mesh(source,process=False);sv=np.asarray(off.vertices)*.001;sf=np.asarray(off.faces,dtype=np.int32)
fr=json.loads(flips.read_text());selected=np.array([x['face_ids'] for x in fr['selected']]).ravel()
gmsh.initialize();gmsh.option.setNumber('General.Terminal',0);gmsh.open(str(mesh))
tags,flat,_=gmsh.model.mesh.getNodes();gn=np.full((tags.max()+1,3),np.nan);gn[tags]=flat.reshape(-1,3)
gr=gmsh.model.mesh.getElementsByType(2,4)[1].reshape(-1,3)
tets=gmsh.model.mesh.getElementsByType(4)[1].reshape(-1,4)
weak=tets[ids]
assert len(gr)==len(sf)==878730
# Map Gmsh surface nodes to source mesh vertex identifiers by the preserved exact coordinates.
rnodes=np.unique(gr)
d,sm=cKDTree(sv).query(gn[rnodes],workers=-1)
assert float(d.max())<1e-12
node_to_source=np.full(len(gn),-1,dtype=np.int32);node_to_source[rnodes]=sm
mapped=np.sort(node_to_source[gr],axis=1)
assert np.all(mapped>=0)
ref=np.sort(sf,axis=1)
row=np.dtype((np.void,12))
keys=np.ascontiguousarray(ref).view(row).ravel();order=np.argsort(keys);sorted_keys=keys[order]
queries=np.ascontiguousarray(mapped).view(row).ravel();loc=np.searchsorted(sorted_keys,queries)
assert np.all(loc<len(sorted_keys)) and np.array_equal(sorted_keys[loc],queries)
face_ids=order[loc]
assert len(np.unique(face_ids))==len(sf)
# Recover exactly which boundary face of each weak tetrahedron is a rotor face.
tetfaces=np.stack([weak[:,[1,2,3]],weak[:,[0,3,2]],weak[:,[0,1,3]],weak[:,[0,2,1]]],axis=1).reshape(-1,3)
rfkeys=np.ascontiguousarray(np.sort(gr,axis=1)).view(np.dtype((np.void,gr.dtype.itemsize*3))).ravel()
rorder=np.argsort(rfkeys);rsorted=rfkeys[rorder]
wkeys=np.ascontiguousarray(np.sort(tetfaces,axis=1)).view(rfkeys.dtype).ravel()
where=np.searchsorted(rsorted,wkeys);match=np.zeros(len(where),bool);valid=where<len(rsorted);match[valid]=rsorted[where[valid]]==wkeys[valid]
incident_ids=face_ids[rorder[where[match]]]
match_by_cell=match.reshape(-1,4)
incident_unique=np.unique(incident_ids)
changed_incident=np.intersect1d(incident_unique,selected)
# Count weak tetrahedra whose exact rotor boundary triangle was touched.
face_to_weak=np.full(len(sf),False);face_to_weak[selected]=True
face_occ=np.full(len(match),-1,dtype=np.int32);face_occ[match]=face_ids[rorder[where[match]]]
cell_changed=np.any(face_to_weak[np.maximum(face_occ.reshape(-1,4),0)]&match_by_cell,axis=1)
# Surface quality, measured on the retained source faces.
def quality(f):
 x=sv[f];a,b,c=np.moveaxis(x,1,0);area=np.linalg.norm(np.cross(b-a,c-a),axis=1)/2
 edges=sum(np.einsum('ij,ij->i',x[:,i]-x[:,j],x[:,i]-x[:,j]) for i,j in ((0,1),(1,2),(2,0)))
 return 4*np.sqrt(3)*area/edges
q=quality(sf)
face_q=q[incident_ids]
min_cell_q=np.full(len(ids),np.inf)
for j in range(4):
 validj=match_by_cell[:,j]
 min_cell_q[validj]=np.minimum(min_cell_q[validj],q[face_occ.reshape(-1,4)[validj,j]])
report={'status':'diagnostic_only_rejected_mesh','mesh_sha256':sha(mesh),'plc_sha256':sha(plc),'source_off_sha256':sha(source),'weak_npz_sha256':sha(weak_file),'flip_receipt_sha256':sha(flips),'gmsh_surface_to_source_max_error_m':float(d.max()),'gmsh_rotor_faces_mapped':len(face_ids),'weak_cells':len(ids),'weak_with_rotor_face':int(np.count_nonzero(match_by_cell.any(axis=1))),'weak_with_selected_flip_face':int(cell_changed.sum()),'selected_flip_faces':len(selected),'selected_flip_faces_incident_to_gmsh_weak_cells':len(changed_incident),'unique_rotor_faces_incident_to_gmsh_weak_cells':len(incident_unique),'weak_incident_face_occurrences_lt_0p05':int(np.count_nonzero(face_q<.05)),'weak_incident_face_occurrences_lt_0p1':int(np.count_nonzero(face_q<.1)),'weak_cells_min_rotor_face_q_lt_0p05':int(np.count_nonzero(min_cell_q<.05)),'weak_cells_min_rotor_face_q_lt_0p1':int(np.count_nonzero(min_cell_q<.1)),'weak_cells_no_exact_rotor_face':int(np.count_nonzero(~match_by_cell.any(axis=1))),'weak_cells_mean_ratio_lt_0p001':int(np.count_nonzero(ratio<.001)),'CFD_accepted':False}
np.savez_compressed(mesh.parent/'gmsh-weak-rotor-face-ids.npz', incident_face_ids=incident_unique, incident_face_quality=q[incident_unique], selected_prior_flip_face_ids=selected)
out=mesh.parent/'weak-cell-flip-overlap.json';out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
gmsh.finalize()
