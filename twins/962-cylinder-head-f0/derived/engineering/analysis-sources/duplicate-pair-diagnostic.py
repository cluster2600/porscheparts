"""Read-only diagnosis; no candidate mesh is written, accepted or repaired."""
import hashlib,json,sys
from pathlib import Path
import numpy as np
root=Path.cwd();sys.path.insert(0,str(root/'twins/962-cylinder-head-f0/source'))
from mesh_head import canonical_oriented
from prepare_head_analysis import compact_unused,edge_diagnostics,validate_surface,polydata
import vtk
folder=Path(__file__).resolve().parent;p=np.load(folder/'analysis-surface.npz');v,f=p['points_mm'],p['triangles'];u,inv,ct=np.unique(np.sort(f,axis=1),axis=0,return_inverse=True,return_counts=True)
rows=[];remove=[]
for duplicate in np.where(ct>1)[0]:
 ids=np.where(inv==duplicate)[0];pair=f[ids];opposite=len(ids)==2 and np.array_equal(canonical_oriented(pair[:1]),canonical_oriented(pair[1:,::-1]))
 rows.append(dict(face_indices=ids.tolist(),oriented_faces=pair.tolist(),exactly_opposite_oriented=opposite));remove.extend(ids)
keep=np.ones(len(f),bool);keep[remove]=False
q,g=compact_unused(v,f[keep]);metrics=validate_surface(q,g);c=vtk.vtkPolyDataConnectivityFilter();c.SetInputData(polydata(q,g));c.SetExtractionModeToAllRegions();c.Update();metrics['connected_components']=c.GetNumberOfExtractedRegions()
r=dict(status='diagnosis_only_no_output_mesh',source_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),input_npz_sha256=hashlib.sha256((folder/'analysis-surface.npz').read_bytes()).hexdigest(),duplicate_pairs=rows,all_pairs_exactly_opposite=all(row['exactly_opposite_oriented'] for row in rows),hypothetical_removed_faces=len(remove),hypothetical_unreferenced_vertices_removed=len(v)-len(q),hypothetical_metrics=metrics,geometric_or_engineering_admission=False,original_and_candidate_meshes_unchanged=True)
with (folder/'duplicate-pair-diagnostic.json').open('x') as stream:json.dump(r,stream,indent=2);stream.write('\n')
print(json.dumps({k:r[k] for k in ('status','all_pairs_exactly_opposite','hypothetical_removed_faces','hypothetical_unreferenced_vertices_removed','hypothetical_metrics')},indent=2))
