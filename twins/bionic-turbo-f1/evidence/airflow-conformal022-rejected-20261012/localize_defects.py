import csv,json,re,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from audit_diagnostic import ascii_list
from audit_frame_interface_v2 import cell_flags
from prepare_case import sha
case=Path('work/bionic-airflow-20261012/baseline-conformal-022')
audit=json.loads(Path('work/bionic-conformal-20261012/interface-audit-022.json').read_text())
receipt=json.loads((case/'write-centres-receipt.json').read_text());assert receipt['native_exit_code']==0
assert sha(case/'0/C')==receipt['outputs']['0/C']
for name,digest in audit['topology']['mesh_sha256'].items():assert sha(case/name)==digest
raw=(case/'0/C').read_text();m=re.search(r'internalField\s+nonuniform\s+List<vector>\s+(\d+)\s*\((.*?)\)\s*;',raw,re.S);assert m
centres=np.fromstring(m[2].translate(str.maketrans('()','  ')),sep=' ').reshape(-1,3)
assert len(centres)==int(m[1])==2489288 and np.isfinite(centres).all()
owner=ascii_list((case/'constant/polyMesh/owner').read_text()).astype(int)
neighbour=ascii_list((case/'constant/polyMesh/neighbour').read_text()).astype(int)
m=re.search(r'rotorZone\s*\{.*?cellLabels\s+List<label>\s*(\d+)\s*\((.*?)\)',(case/'constant/polyMesh/cellZones').read_text(),re.S)
zone=np.fromstring(m[2],sep=' ',dtype=int);assert len(zone)==int(m[1])
rotating=cell_flags(owner,neighbour,zone)
interface=np.flatnonzero(rotating[owner[:len(neighbour)]]^rotating[neighbour]);assert len(interface)==34372
adjacent=np.union1d(owner[interface],neighbour[interface])
patches={name:np.unique(owner[p['start']:p['start']+p['faces']]) for name,p in audit['topology']['patches'].items()}
results={};rows=[]
for name,count in (('concaveCells',6012),('underdeterminedCells',18)):
 path=case/'constant/polyMesh/sets'/name;ids=ascii_list(path.read_text()).astype(int)
 assert len(ids)==count and len(np.unique(ids))==count and ids.min()>=0 and ids.max()<len(centres)
 c=centres[ids];dr=np.linalg.norm(c[:,:2],axis=1)-.038;dz=abs(c[:,2]-.0145)-.0185
 distance=abs(np.linalg.norm(np.maximum(np.column_stack((dr,dz)),0),axis=1)+np.minimum(np.maximum(dr,dz),0))
 results[name]={'cells':len(ids),'sha256':sha(path),'touching_frame_interface':len(np.intersect1d(ids,adjacent)),
   'touching_physical_patches':{name:len(np.intersect1d(ids,values)) for name,values in patches.items()},
   'centre_bounds_m':[c.min(axis=0).tolist(),c.max(axis=0).tolist()],
   'centres_within_distance_of_ideal_interface':{str(d):int(np.count_nonzero(distance<=d)) for d in (.00015,.0003,.0006,.0012)},
   'all_centres_m':c.tolist() if count==18 else None}
 for i,point in zip(ids,c):rows.append([name,int(i),*point.tolist(),bool(rotating[i]),bool(i in adjacent)])
worst=[]
for face in audit['worst_faces']:
 i=face['face'];cells=np.array([owner[i],neighbour[i]])
 worst.append(face|{'owner':int(cells[0]),'neighbour':int(cells[1]),'adjacent_cells_touch_patches':[name for name,values in patches.items() if np.intersect1d(cells,values).size]})
output=Path('work/bionic-conformal-20261012/defect-cell-centres.csv')
with output.open('x') as f:
 w=csv.writer(f);w.writerow(['set','cell','x_m','y_m','z_m','rotating','touches_interface']);w.writerows(rows)
record={'source_sha256':sha(Path(__file__)),'cell_centres_native_sha256':sha(case/'0/C'),'mesh_cells':len(centres),'sets':results,'worst_interface_faces':worst,'csv_sha256':sha(output),'geometry_only':True,'performance_ranking_authorized':False}
Path('work/bionic-conformal-20261012/defect-localization-022.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:{n:v for n,v in d.items() if n!='all_centres_m'} for k,d in results.items()},indent=2))
