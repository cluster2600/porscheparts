"""Independent numerical audit of the private Gmsh exploratory fluid mesh."""
import hashlib
import json
from pathlib import Path
import sys
import gmsh
import numpy as np
from scipy.spatial import cKDTree

source, mesh, output = map(lambda s: Path(s).resolve(), sys.argv[1:])
if output.exists(): raise SystemExit('Output must be fresh')
sha=lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
if sha(source) not in {
    '9fcd93a5c54ebfc98b8cd86d4550e3a416d3e62fb217e5ebfb67eb2f2a9f2085',
    '9dcfef8c123e63016271e3977fdd2d01b21997a94c3343e5e2d6f79198794c8a',
    'e71fc12382db13129166d4a37cc006a45238134ceaf4d32e3873b44b23d611f5',
    '7bb4f474ff0423747784c258dab79ab01e917b648c137654d335e381ce195936',
    '35e1427ed6cfdd858cca31803525a23bb65efa2258e349f06cc9bc7ab2bf7509',
}:
    raise SystemExit('Source hash mismatch')
with np.load(source) as p:
    original_vertices=p['vertices'].copy(); original_faces=p['triangles'].copy(); markers=p['markers'].copy()
gmsh.initialize()
gmsh.option.setNumber('General.Terminal',0)
gmsh.open(str(mesh))
node_tags, flat_coords, _=gmsh.model.mesh.getNodes()
coords=flat_coords.reshape(-1,3)
if len(node_tags)!=len(np.unique(node_tags)): raise SystemExit('Duplicate node tag')
indexed=np.full((node_tags.max()+1,3), np.nan)
indexed[node_tags]=coords
surface_refs=[]
for marker in range(1,5):
    surface_refs.append(gmsh.model.mesh.getElementsByType(2,marker)[1])
surface_tags=np.unique(np.concatenate(surface_refs))
surface_distances, surface_ids=cKDTree(original_vertices).query(indexed[surface_tags],workers=-1)
surface_map=np.full(len(indexed),-1,dtype=np.int64)
surface_map[surface_tags]=surface_ids
face_checks={}
for marker in range(1,5):
    element_tags, node_refs=gmsh.model.mesh.getElementsByType(2,marker)
    original_indices=np.flatnonzero(markers==marker)
    expected=np.sort(original_faces[original_indices],axis=1)
    actual=np.sort(surface_map[node_refs.reshape(-1,3)],axis=1)
    row_sort=lambda x:np.lexsort((x[:,2],x[:,1],x[:,0]))
    equal=(len(element_tags)==len(original_indices) and
           np.array_equal(actual[row_sort(actual)],expected[row_sort(expected)]))
    face_checks[str(marker)]={'elements':len(element_tags),'original_triangle_coordinate_set_preserved':bool(equal)}

element_tags, flat_tets=gmsh.model.mesh.getElementsByType(4)
tets=flat_tets.reshape(-1,4)
quality=np.empty(len(tets)); signed6=np.empty(len(tets))
for start in range(0,len(tets),100000):
    end=min(start+100000,len(tets)); x=indexed[tets[start:end]]
    a,b,c,d=np.moveaxis(x,1,0)
    six=np.einsum('ij,ij->i',b-a,np.cross(c-a,d-a))
    edges=sum(np.einsum('ij,ij->i',x[:,i]-x[:,j],x[:,i]-x[:,j]) for i,j in ((0,1),(0,2),(0,3),(1,2),(1,3),(2,3)))
    signed6[start:end]=six
    quality[start:end]=12*(np.abs(six)/2)**(2/3)/edges
report={'status':'exploratory_gmsh_volume_audited_not_CFD_admitted','source_sha256':sha(source),'mesh_sha256':sha(mesh),'audit_source_sha256':sha(Path(__file__)),'gmsh_version':gmsh.option.getString('General.Version'),'nodes':len(node_tags),'tetrahedra':len(tets),'boundary':face_checks,'surface_node_count':len(surface_tags),'surface_node_to_original_distance_max':float(surface_distances.max()),'surface_node_to_original_distance_p95':float(np.quantile(surface_distances,.95)),'surface_node_to_original_match_at_1e_minus_12':bool(np.all(surface_distances<1e-12)),'tet_signed_six_volume_positive':int(np.count_nonzero(signed6>0)),'tet_signed_six_volume_zero':int(np.count_nonzero(signed6==0)),'tet_signed_six_volume_negative':int(np.count_nonzero(signed6<0)),'tet_quality_min':float(np.min(quality)),'tet_quality_p01':float(np.quantile(quality,.01)),'tet_quality_median':float(np.median(quality)),'tet_quality_lt_0p01':int(np.count_nonzero(quality<.01)),'tet_quality_lt_0p05':int(np.count_nonzero(quality<.05)),'tet_quality_lt_0p1':int(np.count_nonzero(quality<.1)),'signed_volume_sum':float(signed6.sum()/6),'absolute_volume_sum':float(np.abs(signed6).sum()/6),'CFD_admitted':False,'manufacturing_authorized':False}
output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
gmsh.finalize()
