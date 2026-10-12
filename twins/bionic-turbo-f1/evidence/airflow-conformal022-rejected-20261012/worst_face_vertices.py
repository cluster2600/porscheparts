import json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from audit_diagnostic import ascii_list
from run_case import ascii_faces
from prepare_case import sha
case=Path('work/bionic-airflow-20261012/baseline-conformal-022')
audit=json.loads(Path('work/bionic-conformal-20261012/interface-audit-022.json').read_text())
for name in ('points','faces'):
 assert sha(case/'constant/polyMesh'/name)==audit['input_mesh_sha256'][name]
points=ascii_list((case/'constant/polyMesh/points').read_text(),True)
wanted={r['face'] for r in audit['worst_faces']};found=[]
for i,f in enumerate(ascii_faces((case/'constant/polyMesh/faces').read_text())):
 if i in wanted:
  p=points[list(f)];radial=np.linalg.norm(p[:,:2],axis=1)
  found.append({'face':i,'points':list(f),'vertices_m':p.tolist(),'radial_error_m':(radial-.038).tolist()})
assert len(found)==len(wanted)==20
print(json.dumps({'source_sha256':sha(Path(__file__)),'mesh_points_sha256':audit['input_mesh_sha256']['points'],'mesh_faces_sha256':audit['input_mesh_sha256']['faces'],'faces':found,'geometry_only':True},indent=2))
