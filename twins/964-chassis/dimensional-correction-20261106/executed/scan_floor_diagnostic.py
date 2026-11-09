"""Read-only, unfiltered original-face floor-candidate diagnostics; no CAD."""
from pathlib import Path
import hashlib,json,sys,time,resource
import numpy as np
ROOT=Path('/repo');OUT=Path('/out');started=time.monotonic()
V_PATH=ROOT/'work/964-model-year-review-20261029/replay-001/verts_vehicle.npy'
F_PATH=ROOT/'work/964-model-year-review-20261029/replay-001/faces.npy'
B=ROOT/'work/964-observed-boundaries-20261029/review-001'
sha=lambda p:hashlib.file_digest(Path(p).open('rb'),'sha256').hexdigest()
expected={V_PATH:'201787314680bcd60fb5f9b8910e28b0025d60c380dc77fa458a41bb17942bc9',F_PATH:'271c4f04717be91babfebeb809de485c940dc909ec981acd857693969563b484',B/'source_open_edges.npz':'22fa12246c7bce2f092d370d77208f317761a74af4b525eeb75afcf11d4618c2'}
for p,h in expected.items():
 if sha(p)!=h:raise ValueError('Immutable source hash mismatch: '+str(p))
V=np.load(V_PATH,mmap_mode='r');F=np.load(F_PATH,mmap_mode='r')
labels=np.load(B/'source_face_components.npy',mmap_mode='r')
opens=np.load(B/'source_open_edges.npz')['source_vertex_ids'].astype(np.int64)
openkeys=np.sort(opens[:,0]*len(V)+opens[:,1]);counts_expected={'FloorLeftSearch':175467,'FloorRightSearch':174553,'CentralRouteSearch':157129}
bounds={'FloorLeftSearch':[-1650,-500,150,520,0,900],'FloorRightSearch':[-1650,-500,-520,-150,0,900],'CentralRouteSearch':[-1650,-500,-150,150,0,900]}
public=json.loads((ROOT/'twins/964-chassis/monocoque/scan-coverage-20261029/run.json').read_text())

def inspect(name,ids,window,role):
 ids=np.asarray(ids,dtype=np.int32);faces=np.asarray(F[ids]);points=np.asarray(V[faces],dtype=np.float64)
 vertex_ids=np.unique(faces);vertices=np.asarray(V[vertex_ids],dtype=np.float64);origin=vertices.mean(axis=0);p=points-origin
 areas=.5*np.linalg.norm(np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]),axis=1)
 if not np.isfinite(p).all() or np.any(areas<=0):raise ValueError('Nonfinite or degenerate source patch; do not silently discard')
 sums=p.sum(axis=1);mu=(areas[:,None]*sums/3).sum(axis=0)/areas.sum()
 second=(np.einsum('ni,nj->nij',sums,sums)+np.einsum('nki,nkj->nij',p,p))/12
 covariance=(areas[:,None,None]*second).sum(axis=0)/areas.sum()-np.outer(mu,mu)
 values,vectors=np.linalg.eigh(covariance);n=vectors[:,0]
 if n[2]<0:n=-n
 centre=origin+mu;distance=(vertices-centre)@n;centroid_dist=(points.mean(axis=1)-centre)@n
 # Exact original shared-edge incidence. Crop cuts remain selected-mask edges.
 edges=np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]).astype(np.int64)
 edges.sort(axis=1);keys=edges[:,0]*len(V)+edges[:,1];owners=np.tile(np.arange(len(ids)),3)
 order=np.argsort(keys,kind='stable');sortedkeys=keys[order];own=owners[order]
 unique,first,counts=np.unique(sortedkeys,return_index=True,return_counts=True)
 if np.any(counts>2):raise ValueError('Unexpected original nonmanifold edge')
 parent=np.arange(len(ids));size=np.ones(len(ids),dtype=np.int32)
 def find(a):
  while parent[a]!=a:
   parent[a]=parent[parent[a]];a=int(parent[a])
  return a
 for start in first[counts==2]:
  a,b=find(int(own[start])),find(int(own[start+1]))
  if a!=b:
   if size[a]<size[b]:a,b=b,a
   parent[b]=a;size[a]+=size[b]
 roots=np.array([find(i) for i in range(len(ids))]);_,component_counts=np.unique(roots,return_counts=True)
 frontier=unique[counts==1];is_open=np.isin(frontier,openkeys)
 global_ids,global_counts=np.unique(labels[ids],return_counts=True)
 target=OUT/(name+'.npz');np.savez_compressed(target,source_face_ids=ids,source_vertex_ids=vertex_ids,
    edge_connected_local_face_labels=roots,selected_frontier_vertex_pairs=np.column_stack([frontier//len(V),frontier%len(V)]),
    frontier_is_original_open=is_open)
 return {'name':name,'role':role,'selection_bounds_provisional_frame_mm':window,'source_face_count':len(ids),
 'source_vertex_count':len(vertex_ids),'source_face_ids_i32_sha256':hashlib.sha256(ids.astype('<i4').tobytes()).hexdigest(),
 'id_archive':target.name,'id_archive_sha256':sha(target),'bounds_min_mm':vertices.min(axis=0).tolist(),
 'bounds_max_mm':vertices.max(axis=0).tolist(),'observed_triangle_area_mm2_provisional_scale':float(areas.sum()),
 'edge_connected_selected_surface_components':len(component_counts),'selected_component_face_counts_descending':sorted(component_counts.tolist(),reverse=True),
 'original_source_component_membership':[{'id':int(i),'faces':int(c)} for i,c in zip(global_ids,global_counts)],
 'selected_frontier_edges':len(frontier),'original_open_edges':int(is_open.sum()),'artificial_crop_edges':int((~is_open).sum()),
 'plane_diagnostic':{'method':'Exact area-integrated triangle covariance; least orthogonal squared-distance plane. Every selected positive-area original triangle participates; no RANSAC, clipping or residual rejection.',
 'normal_in_provisional_frame':n.tolist(),'point_on_plane_provisional_frame_mm':centre.tolist(),'offset_d_in_n_dot_p_plus_d_equals_zero':float(-n@centre),
 'area_weighted_RMS_orthogonal_residual_mm':float(np.sqrt(max(values[0],0))),
 'all_original_vertex_absolute_residual_quantiles_mm':{str(q):float(np.percentile(abs(distance),q)) for q in (0,50,95,99,100)},
 'all_original_vertex_signed_residual_range_mm':[float(distance.min()),float(distance.max())],
 'plane_tilt_from_provisional_XY_deg':float(np.degrees(np.arccos(np.clip(n[2],-1,1)))),
 'plane_is_original_interior_floor_or_body_datum':False,'scanner_or_source_uncertainty_mm':None,
 'maximum_planarity_tolerance_mm':None,'accepted_planar_geometry':False}}

results=[];all_floor_ids=[];crop_floor_ids=[]
for name in bounds:
 a=np.load(B/(name+'.npz'));ids=a['source_face_ids'].astype(np.int32)
 if len(ids)!=counts_expected[name] or hashlib.sha256(ids.astype('<i4').tobytes()).hexdigest()!=public['groups'][name]['source_face_ids_sha256']:raise ValueError('Existing region membership changed')
 # Recompute actual original-window inclusion, never use the model name as identity.
 lo=np.array(bounds[name])[::2];hi=np.array(bounds[name])[1::2];tri=np.asarray(V[F[ids]])
 if not ((tri>=lo)&(tri<=hi)).all():raise ValueError('Retained IDs outside original window')
 results.append(inspect(name,ids,bounds[name],'existing_exact_search_window; floor/cover identity remains conditional'))
 if name!='CentralRouteSearch':
  all_floor_ids.append(ids)
  tile=[-1400,-700,200,450,0,900] if 'Left' in name else [-1400,-700,-450,-200,0,900]
  lo=np.array(tile)[::2];hi=np.array(tile)[1::2];take=((tri>=lo)&(tri<=hi)).all(axis=(1,2))
  crop_floor_ids.append(ids[take])
  results.append(inspect(name+'InteriorInspectionCrop',ids[take],tile,'fixed anatomy-context exterior candidate crop; not an interior skin or physical part perimeter'))
results.append(inspect('CombinedFloorSearch',np.sort(np.concatenate(all_floor_ids)),[bounds['FloorRightSearch'],bounds['FloorLeftSearch']],'combined unchanged floor-search windows; centre excluded'))
results.append(inspect('CombinedExteriorInspectionCrops',np.sort(np.concatenate(crop_floor_ids)),[[-1400,-700,-450,-200,0,900],[-1400,-700,200,450,0,900]],'combined fixed exterior-candidate crops; no inferred surface between them'))
# Replay the legacy mode once without interpreting it as a plane or a part.
mask=(V[:,0]>-1400)&(V[:,0]<-200)&(abs(V[:,1])<450);z=np.asarray(V[mask,2]);h,e=np.histogram(z,bins=200);mode=float((e[h.argmax()]+e[h.argmax()+1])/2)
for p,hx in expected.items():
 if sha(p)!=hx:raise ValueError('Source changed during inspection')
report={'classification':'read_only_original_triangle_exterior_candidate_diagnostics_not_registered_reconstruction',
 'source_input_sha256':{str(p.relative_to(ROOT)):h for p,h in expected.items()},'code_sha256':sha(__file__),
 'original_obj_sha256':'f397909141e5af2529db961641c7699d39d40c355e05245cfb1573a2974c8dc5',
 'original_component_labels_sha256':sha(B/'source_face_components.npy'),
 'units':'original retained scan scale interpreted as mm; independent scanner calibration unestablished',
 'frame':'Existing tyre/symmetry provisional Xforward,Yleft,Zup; not registered to documentary body datums',
 'legacy_histogram_replay':{'selection':'X(-1400,-200),absY<450; all vertices, 200bins over actual min/maxZ','vertices':len(z),'mode_Z_mm':mode,
 'Z_p5_p95_mm':np.percentile(z,[5,95]).tolist(),'matches_271_7_at_one_decimal':round(mode,1)==271.7,'plane_or_component_identity_established':False},
 'patches':results,'full_geometry_changed':False,'new_geometry_or_repair_created':False,
 'new_floor_plane_accepted':False,'body_datum_registration_admitted':False,'interior_surface_or_thickness_inferred':False,
 'runtime_seconds':time.monotonic()-started,'peak_RSS_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
 'python':sys.version,'numpy':np.__version__}
(OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'runtime':report['runtime_seconds'],'legacy':report['legacy_histogram_replay'],'patches':[{k:p[k] for k in ('name','source_face_count','edge_connected_selected_surface_components')}|{'RMS':p['plane_diagnostic']['area_weighted_RMS_orthogonal_residual_mm'],'max':p['plane_diagnostic']['all_original_vertex_absolute_residual_quantiles_mm']['100'],'tilt':p['plane_diagnostic']['plane_tilt_from_provisional_XY_deg']} for p in results]},indent=2))
