"""Conservative distance bound for explicitly paired triangular boundary facets."""
import json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
from audit_diagnostic import ascii_list
from run_case import ascii_faces
w=Path(__file__).parent;root=Path('work/bionic-airflow-20261012');parent=root/'radial-isolated-079';case=root/'radial-selective-snap-081'
for c in (parent,case):
 r=json.loads((c/'report.json').read_text());assert all(sha(c/k)==v for k,v in r['output_sha256'].items())
p=ascii_list((parent/'constant/polyMesh/points').read_text(),True);q=ascii_list((case/'constant/polyMesh/points').read_text(),True)
f=list(ascii_faces((parent/'constant/polyMesh/faces').read_text()));g=list(ascii_faces((case/'constant/polyMesh/faces').read_text()));assert f==g
internal=len(ascii_list((parent/'constant/polyMesh/neighbour').read_text()));labels=np.array([np.array(face)[[0,j,j+1]] for face in f[internal:] for j in (1,2)])
a=p[labels];b=q[labels];delta=b-a;bound=np.linalg.norm(delta,axis=2).max(axis=1)
# For any nonnegative barycentric weights summing to one, the same weights in
# the paired triangle give ||sum(w_i*(b_i-a_i))|| <= max_i ||b_i-a_i||.
# This works in both directions and does not require a coplanar source quad.
weights=np.array([[i/4,j/4,1-(i+j)/4] for i in range(5) for j in range(5-i)])
for v in weights:assert np.all(np.linalg.norm(np.einsum('i,kij->kj',v,delta),axis=1)<=bound+1e-18)
i=int(bound.argmax());res=dict(reader_sha256=sha(Path(__file__)),all_payloads_verified=True,paired_triangles=len(labels),triangle_vertex_labels_equal=True,triangulation='fan (v0,v1,v2) and (v0,v2,v3) for each unchanged quad label cycle; analysis only, native quads unchanged',symmetric_hausdorff_upper_bound_m=float(bound.max()),worst_triangle=i,worst_vertex_labels=labels[i].tolist(),worst_source_vertices_m=a[i].tolist(),worst_final_vertices_m=b[i].tolist(),proof='Identical barycentric coordinates in corresponding triangles and triangle inequality. Upper bound only, not the measured Hausdorff distance.',scope='Bound applies to these explicitly paired piecewise-planar boundary surfaces. It does not assert exact target restoration, arbitrary other faceting, unchanged native face normals, or physical clearance.',supersedes_v2_parent_quad_bound_claim=True)
(w/'paired-surface-bound.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res,indent=2))
