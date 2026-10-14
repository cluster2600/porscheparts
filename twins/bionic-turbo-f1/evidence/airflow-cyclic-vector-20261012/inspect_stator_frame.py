"""Read-only exploratory frame-normal map of fixed walls in rejected mesh 033."""
import json,re,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
from audit_diagnostic import ascii_list
from run_case import ascii_faces
from frame_balance_batches import geometry
case=Path('work/bionic-airflow-20261012/baseline-gap-033');mesh=case/'constant/polyMesh';r=json.loads((case/'run-mesh.json').read_text())
assert r['native_exit_code']==0 and not r['mesh_gate_passed']
for name,digest in r['output_sha256'].items():assert sha(case/name)==digest
owner=ascii_list((mesh/'owner').read_text()).astype(int);p=ascii_list((mesh/'points').read_text(),True);text=(mesh/'cellZones').read_text();m=re.search(r'cellLabels\s+List<label>\s+(\d+)\s*\((.*?)\)',text,re.S);zone=np.fromstring(m[2],sep=' ',dtype=int);assert len(zone)==int(m[1]);rotating=np.zeros(owner.max()+1,bool);rotating[zone]=True
boundary=(mesh/'boundary').read_text();m=re.search(r'stator\s*\{.*?nFaces\s+(\d+);\s*startFace\s+(\d+);',boundary,re.S);count,start=map(int,m.groups());selected=[]
for i,f in enumerate(ascii_faces((mesh/'faces').read_text())):
 if start<=i<start+count and rotating[owner[i]]:selected.append((i,f))
assert i+1==len(owner)
omega=float(re.search(r'omega\s+constant\s+([^;]+)',(case/'constant/MRFProperties').read_text())[1]);records=[];total=0.
for length in sorted(set(len(f) for _,f in selected)):
 group=[(i,f) for i,f in selected if len(f)==length];v=p[np.array([f for _,f in group])];c,s,w=geometry(v);q=np.einsum('ij,ij->i',np.cross([0,0,omega],c),s);normal=q/np.linalg.norm(s,axis=1);total+=float(np.abs(q).sum())
 records += [dict(face=i,owner=int(owner[i]),native_formula_face_centre_mm=(centre*1000).tolist(),normal_frame_speed_m_s=float(speed),geometric_frame_flux_m3_s=float(flux),warp_m=float(warp)) for (i,_),centre,speed,flux,warp in zip(group,c,normal,q,w)]
records.sort(key=lambda x:abs(x['normal_frame_speed_m_s']),reverse=True)
result=dict(source_sha256=sha(Path(__file__)),receipt_sha256=sha(case/'run-mesh.json'),all_native_payloads_verified=True,stator_faces=count,stator_faces_owned_by_rotating_cells=len(selected),geometric_abs_frame_flux_m3_s=total,worst_faces=records[:20],scope='Exploration only on rejected 033. Not physical air flow, not proof all fixed walls must leave MRF. No solver or mesh modification.')
with Path(__file__).with_name('stator-frame-exploration.json').open('x') as out:json.dump(result,out,indent=2)
print(json.dumps({k:v for k,v in result.items() if k!='worst_faces'}));print(records[0])
