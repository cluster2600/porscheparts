import json,re,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
import audit_frame_interface as audit
from audit_diagnostic import ascii_list
from run_case import ascii_faces
from prepare_case import sha
case=Path('work/bionic-airflow-20261012/static-mrf-witness-021/aligned-radial-interface')
reference=Path('twins/bionic-turbo-f1/evidence/airflow-aligned-interface-20261012/geometry-021.json')
prior=json.loads(reference.read_text())
for name,digest in prior['input_sha256'].items():assert sha(case/name)==digest
p=ascii_list((case/'constant/polyMesh/points').read_text(),True)
o=ascii_list((case/'constant/polyMesh/owner').read_text()).astype(int)
n=ascii_list((case/'constant/polyMesh/neighbour').read_text()).astype(int)
raw=(case/'constant/polyMesh/cellZones').read_text()
z=re.search(r'rotorZone\s*\{.*?cellLabels\s+List<label>\s*(\d+)\s*\((.*?)\)',raw,re.S)
zone=np.fromstring(z[2],sep=' ',dtype=int);selected=set(np.flatnonzero(np.isin(o[:len(n)],zone)^np.isin(n,zone)))
flux=[];normal=[];centre_error=[];area_error=[]
for i,f in enumerate(ascii_faces((case/'constant/polyMesh/faces').read_text())):
 if i not in selected:continue
 v=p[list(f)];assert v.shape==(4,3) and np.allclose(v[0]+v[2],v[1]+v[3],rtol=0,atol=1e-12)
 cf,sf=audit.face_geometry(v)
 centre_error.append(float(np.linalg.norm(cf-v.mean(axis=0))))
 area_error.append(float(np.linalg.norm(sf-np.cross(v[1]-v[0],v[3]-v[0]))))
 q=abs(float(np.dot(np.cross([0,0,10471.975511966],cf),sf)))
 flux.append(q);normal.append(q/np.linalg.norm(sf))
assert len(flux)==640 and max(centre_error)<1e-14 and max(area_error)<1e-18
assert abs(sum(flux)-prior['gross_geometric_frame_flux_m3_s'])<1e-14
assert abs(max(normal)-prior['max_normal_frame_speed_m_s'])<1e-10
print(json.dumps({'status':'polygon_formula_matches_analytical_parallelograms','faces':len(flux),'max_centroid_error_m':max(centre_error),'max_area_vector_error_m2':max(area_error),'gross_geometric_frame_flux_m3_s':sum(flux),'max_normal_frame_speed_m_s':max(normal),'source_sha256':sha(Path(__file__)),'auditor_source_sha256':sha(Path(audit.__file__)),'reference_sha256':sha(reference),'performance_ranking_authorized':False},indent=2))
