"""Check exact rotor-face incidence of weak Gmsh fluid tetrahedra."""
import hashlib,json
from pathlib import Path
import sys
import gmsh
import numpy as np
mesh, weak_file, output=map(lambda s:Path(s).resolve(),sys.argv[1:])
if output.exists():raise SystemExit('Output must be fresh')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sha(mesh)!='0f6d5cadd5b48c3345e8440c5a881018ca463b005641c46e0b376d9ecbcd8bb7' or sha(weak_file)!='2a684d5590671a8ed2f866a3193fddb77718b7680a3b3a530f77ec154e6cb2ca':raise SystemExit('Input hash mismatch')
with np.load(weak_file) as z:weak_ids=z['cell_ids'];centres=z['centres_m']
gmsh.initialize();gmsh.option.setNumber('General.Terminal',0);gmsh.open(str(mesh))
tags,flat,_=gmsh.model.mesh.getNodes();nodes=np.full((tags.max()+1,3),np.nan);nodes[tags]=flat.reshape(-1,3)
rotor=gmsh.model.mesh.getElementsByType(2,4)[1].reshape(-1,3)
tets=gmsh.model.mesh.getElementsByType(4)[1].reshape(-1,4)
weak=tets[weak_ids]
row_type=np.dtype((np.void,rotor.dtype.itemsize*3))
keys=np.ascontiguousarray(np.sort(rotor,axis=1)).view(row_type).ravel();order=np.argsort(keys);sorted_keys=keys[order]
if np.any(sorted_keys[1:]==sorted_keys[:-1]):raise SystemExit('Duplicate rotor face')
faces=np.stack([weak[:,[1,2,3]],weak[:,[0,3,2]],weak[:,[0,1,3]],weak[:,[0,2,1]]],axis=1).reshape(-1,3)
queries=np.ascontiguousarray(np.sort(faces,axis=1)).view(row_type).ravel();loc=np.searchsorted(sorted_keys,queries)
match=np.zeros(len(loc),bool);valid=loc<len(sorted_keys);match[valid]=sorted_keys[loc[valid]]==queries[valid]
incident=rotor[order[loc[match]]]
def quality(tri):
 x=nodes[tri];a,b,c=np.moveaxis(x,1,0);area=np.linalg.norm(np.cross(b-a,c-a),axis=1)/2
 edges=sum(np.einsum('ij,ij->i',x[:,i]-x[:,j],x[:,i]-x[:,j]) for i,j in ((0,1),(1,2),(2,0)))
 return 4*np.sqrt(3)*area/edges
allq=quality(rotor);iq=quality(incident)
radius=np.linalg.norm(centres[:,:2],axis=1)
report={'status':'rejected_gmsh_weak_wall_face_incidence','mesh_sha256':sha(mesh),'weak_file_sha256':sha(weak_file),'source_sha256':sha(Path(__file__)),'weak_cells':len(weak),'weak_with_exact_rotor_face':int(np.count_nonzero(match.reshape(-1,4).any(axis=1))),'weak_without_exact_rotor_face':int(np.count_nonzero(~match.reshape(-1,4).any(axis=1))),'incident_rotor_faces':len(incident),'incident_rotor_face_quality_median':float(np.median(iq)),'incident_rotor_face_quality_lt_0p1':int(np.count_nonzero(iq<.1)),'all_rotor_face_quality_median':float(np.median(allq)),'all_rotor_face_quality_lt_0p1':int(np.count_nonzero(allq<.1)),'radial_bins_conditional_mm':{f'{lo}-{hi}':int(np.count_nonzero((radius>=lo/1000)&(radius<hi/1000))) for lo,hi in [(0,30),(30,70),(70,100),(100,150)]},'weak_centres_radius_84_to_86_conditional_mm':int(np.count_nonzero((radius>=.084)&(radius<.086))),'scale_verified':False,'CFD_admitted':False}
output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
gmsh.finalize()
