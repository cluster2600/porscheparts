"""Read-only native boundary equality and location of residual vertex offsets."""
import json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
from uniform_interface_projection import read_mesh
from audit_diagnostic import ascii_list
w=Path(__file__).parent;root=Path('work/bionic-airflow-20261012');p,f,mid,n=read_mesh(root/'full-collar-063');a,_,_,_=read_mesh(root/'connected-snap-074');b,_,_,_=read_mesh(root/'connected-nosmooth-075');boundary=np.unique(np.concatenate(f[n:]));manifest=json.loads((w/'connected-snap-074-inputs/manifest.json').read_text());outer=np.array(manifest['outer_point_labels'])
assert np.array_equal(a[boundary],b[boundary])
error=np.linalg.norm(b[outer]-p[outer],axis=1);worst=outer[np.argmax(error)];ends=(p[outer,2]==p[:,2].min())|(p[outer,2]==p[:,2].max())
assert ends.sum()==256
initial=ascii_list((w/'connected-snap-074-inputs/constant/polyMesh/points').read_text(),True)
results=dict(source_sha256=sha(Path(__file__)),boundary_coordinates_identical_074_075=True,boundary_points=len(boundary),outer_points=len(outer),outer_end_points=int(ends.sum()),worst_vertex_label=int(worst),source_vertex_m=p[worst].tolist(),final_vertex_m=b[worst].tolist(),maximum_source_vertex_distance_m=float(error.max()),maximum_source_vertex_distance_excluding_ends_m=float(error[~ends].max()),minimum_actual_motion_excluding_ends_m=float(np.linalg.norm(b[outer[~ends]]-initial[outer[~ends]],axis=1).min()),limitation='Distance to same labelled source vertex is not distance to target surface. Shared lateral/end vertices may remain on end surfaces. No exact recovery of the whole target boundary is claimed.')
with (w/'motion-scope.json').open('x') as out:json.dump(results,out,indent=2)
print(json.dumps(results,indent=2))
