import json,re,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from audit_diagnostic import ascii_list,face_geometry
from run_case import ascii_faces
from prepare_case import sha
case=Path(sys.argv[1]);inputs={}
def read(name):
 p=case/name;inputs[name]=sha(p);return p.read_text()
mesh='constant/polyMesh/'
owner=ascii_list(read(mesh+'owner')).astype(np.int64)
neighbour=ascii_list(read(mesh+'neighbour')).astype(np.int64)
points=ascii_list(read(mesh+'points'),True)
z=re.search(r'rotorZone\s*\{.*?cellLabels\s+List<label>\s*(\d+)\s*\((.*?)\)',read(mesh+'cellZones'),re.S)
assert z
zone=np.fromstring(z[2],sep=' ',dtype=np.int64);assert len(zone)==int(z[1])
oactive=np.isin(owner[:len(neighbour)],zone);nactive=np.isin(neighbour,zone)
interface=set(np.flatnonzero(oactive^nactive));omega=float(re.search(r'omega\s+constant\s+([^;]+)',read('constant/MRFProperties'))[1])
flux=[];normal=[];net=[]
for i,f in enumerate(ascii_faces(read(mesh+'faces'))):
 if i in interface:
  cf,sf=face_geometry(points[list(f)]);q=float(np.dot(np.cross([0,0,omega],cf),sf))
  flux.append(abs(q));normal.append(abs(q)/np.linalg.norm(sf));net.append(q*(1 if oactive[i] else -1))
assert len(flux)==len(interface)
print(json.dumps({'case':case.name,'rotating_cells':len(zone),'internal_frame_interface_faces':len(interface),'gross_geometric_frame_flux_m3_s':sum(flux),'net_outward_geometric_frame_flux_m3_s':sum(net),'max_normal_frame_speed_m_s':max(normal,default=0),'interpretation':'Geometric rotation through frame-interface faces, not physical wall leakage or a performance measurement.','input_sha256':inputs,'source_sha256':sha(Path(__file__))},indent=2))
