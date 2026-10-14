import json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
from audit_diagnostic import ascii_list
from run_case import ascii_faces
root=Path(__file__).parent;case=Path('work/bionic-airflow-20261012/baseline-profile-mesh-031');a=json.loads((root/'interface-audit-031.json').read_text())
for name,h in a['input_mesh_sha256'].items():assert sha(case/'constant/polyMesh'/name)==h
points=ascii_list((case/'constant/polyMesh/points').read_text(),True)
manifest=json.loads((case/'case-manifest.json').read_text());profile=np.array(manifest['rotor_zone']['profile_nodes_mm'])
wanted={r['face']:r for r in a['worst_faces']};rows=[]
for i,face in enumerate(ascii_faces((case/'constant/polyMesh/faces').read_text())):
 if i in wanted:
  p=points[list(face)]*1000;error=np.linalg.norm(p[:,:2],axis=1)-np.interp(p[:,2],profile[:,0],profile[:,1])
  rows.append(wanted[i]|dict(vertices_mm=p.tolist(),vertex_radial_error_mm=error.tolist()))
assert len(rows)==len(wanted)
with (root/'worst-faces-031.json').open('x') as f:json.dump(dict(source_sha256=sha(Path(__file__)),faces=rows,geometry_only=True,performance_ranking_authorized=False),f,indent=2);f.write('\n')
print('Worst interface vertex radial errors (mm):',min(v for r in rows for v in r['vertex_radial_error_mm']),max(v for r in rows for v in r['vertex_radial_error_mm']))
