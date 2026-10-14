"""Read-only mapping of cell frame balance on the rejected full turbo mesh 033."""
import collections,json,re,sys,time
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
from audit_diagnostic import ascii_list
from run_case import ascii_faces
from frame_balance_batches import geometry
case=Path('work/bionic-airflow-20261012/baseline-gap-033');mesh=case/'constant/polyMesh';receipt=json.loads((case/'run-mesh.json').read_text());start=time.monotonic()
assert receipt['native_exit_code']==0 and not receipt['mesh_gate_passed']
for n,h in receipt['output_sha256'].items():assert sha(case/n)==h
owner=ascii_list((mesh/'owner').read_text()).astype(int);nei=ascii_list((mesh/'neighbour').read_text()).astype(int);p=ascii_list((mesh/'points').read_text(),True)
m=re.search(r'rotorZone\s*\{.*?cellLabels\s+List<label>\s*(\d+)\s*\((.*?)\)',(mesh/'cellZones').read_text(),re.S);zone=np.fromstring(m[2],sep=' ',dtype=int);assert len(zone)==int(m[1])
count=int(max(owner.max(),nei.max()))+1;rotating=np.zeros(count,bool);rotating[zone]=True;net=np.zeros(count);closure=np.zeros((count,3));interface_cells=np.zeros(count,bool);boxes_low=np.full((count,3),np.inf);boxes_high=-boxes_low
omega=float(re.search(r'omega\s+constant\s+([^;]+)',(case/'constant/MRFProperties').read_text())[1]);groups=collections.defaultdict(list);total=0;maxwarp=0.;maxnormal=0.;seam_count=0
warp_by_kind={k:0. for k in ('interface','other_internal','boundary')}
def consume():
 global total,maxwarp,maxnormal,seam_count
 for size,batch in groups.items():
  ids=np.array([x[0] for x in batch],int);v=p[np.array([x[1] for x in batch],int)];c,s,w=geometry(v);q=np.einsum('ij,ij->i',np.cross([0,0,omega],c),s)
  np.add.at(net,owner[ids],q);np.add.at(closure,owner[ids],s);np.minimum.at(boxes_low,owner[ids],v.min(axis=1));np.maximum.at(boxes_high,owner[ids],v.max(axis=1))
  internal=ids<len(nei);j=ids[internal];np.add.at(net,nei[j],-q[internal]);np.add.at(closure,nei[j],-s[internal]);np.minimum.at(boxes_low,nei[j],v[internal].min(axis=1));np.maximum.at(boxes_high,nei[j],v[internal].max(axis=1))
  seam=np.zeros(len(ids),bool);seam[internal]=rotating[owner[j]]^rotating[nei[j]];interface_cells[owner[ids[seam]]]=True;interface_cells[nei[ids[seam]]]=True
  seam_count+=int(seam.sum());maxwarp=max(maxwarp,float(w.max()))
  for key,selection in (('interface',seam),('other_internal',internal&~seam),('boundary',~internal)):
   if selection.any():warp_by_kind[key]=max(warp_by_kind[key],float(w[selection].max()))
  if seam.any():maxnormal=max(maxnormal,float(np.abs(q[seam]/np.linalg.norm(s[seam],axis=1)).max()))
  total+=len(ids)
 groups.clear()
for i,f in enumerate(ascii_faces((mesh/'faces').read_text())):
 groups[len(f)].append((i,f))
 if (i+1)%20000==0:consume()
consume();assert total==len(owner) and np.isfinite(boxes_low).all()
order=zone[np.argsort(np.abs(net[zone]))[-20:][::-1]]
result=dict(source_sha256=sha(Path(__file__)),geometry_source_sha256=sha(Path('twins/bionic-turbo-f1/cfd/frame_balance_batches.py')),receipt_sha256=sha(case/'run-mesh.json'),all_native_payloads_verified=True,cells=count,faces=total,rotating_cells=len(zone),interface_faces=seam_count,max_interface_normal_m_s=maxnormal,max_face_warp_m=maxwarp,warp_by_kind_m=warp_by_kind,max_area_closure_m2=float(np.linalg.norm(closure,axis=1).max()),max_rotating_cell_geometric_flux_m3_s=float(np.abs(net[zone]).max()),max_rotating_noninterface_cell_geometric_flux_m3_s=float(np.abs(net[rotating&~interface_cells]).max()),worst_cells=[dict(cell=int(j),box_midpoint_mm=((boxes_low[j]+boxes_high[j])*500).tolist(),touches_interface=bool(interface_cells[j]),geometric_frame_flux_m3_s=float(net[j])) for j in order],elapsed_seconds=time.monotonic()-start,solver_launched=False,performance_ranking_authorized=False)
with Path(__file__).with_name('real-balance-033.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result),flush=True)
